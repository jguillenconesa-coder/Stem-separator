"""Separation pipeline, independent of the desktop UI."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import gc
import json
import os
import sys
import shutil
import subprocess
import tempfile
import threading
from datetime import datetime, timezone

STEMS = {
    "drums": "Batería", "bass": "Bajo", "vocals": "Voz principal",
    "backing_vocals": "Coros (experimental)", "guitar": "Guitarra",
    "piano": "Piano", "other": "Otros",
}
MODEL = "htdemucs_6s.yaml"
VOCAL_MODEL = "UVR_MDXNET_KARA_2.onnx"


class Cancelled(Exception):
    pass


@dataclass(frozen=True)
class Job:
    source: Path
    destination: Path
    stems: tuple[str, ...]
    format: str = "wav"
    split_vocals: bool = True

    def validate(self):
        if not self.source.is_file() or self.source.suffix.lower() not in {".wav", ".mp3", ".flac", ".mp4"}:
            raise ValueError("Selecciona un archivo WAV, MP3, FLAC o MP4 existente.")
        if not self.stems or len(set(self.stems)) != len(self.stems) or set(self.stems) - STEMS.keys():
            raise ValueError("Selecciona al menos un stem válido, sin duplicados.")
        if self.format not in {"wav", "mp3"}:
            raise ValueError("El formato de salida debe ser WAV o MP3.")
        if "backing_vocals" in self.stems and not self.split_vocals:
            raise ValueError("Activa la separación de coros para exportarlos.")


def data_dir() -> Path:
    if os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "StemSeparator"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "StemSeparator"
    return Path.home() / ".cache" / "StemSeparator"


def cache_dir() -> Path:
    return data_dir() / "models"


def ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _write_float_wav(path: Path, samples, rate: int):
    """Preserve stereo layout and floating-point precision between model stages."""
    import numpy as np
    import soundfile as sf
    samples = np.asarray(samples, dtype=np.float32)
    if samples.ndim != 2 or samples.shape[1] != 2 or not np.isfinite(samples).all():
        raise RuntimeError("El modelo ha devuelto audio estéreo inválido.")
    peak = float(np.max(np.abs(samples))) if samples.size else 0
    if peak > 1:
        samples = samples / peak
    sf.write(path, samples, rate, subtype="FLOAT")


def convert(source: Path, target: Path, *, stereo=False):
    args = [ffmpeg(), "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source)]
    # Select the first audio stream explicitly; MP4 video is never passed to the model.
    args += ["-map", "0:a:0", "-vn"]
    if stereo:
        args += ["-ac", "2", "-ar", "44100"]
    args += ["-c:a", "libmp3lame", "-b:a", "320k"] if target.suffix == ".mp3" else ["-c:a", "pcm_s24le"]
    result = subprocess.run(args + [str(target)], capture_output=True, text=True,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        raise RuntimeError("FFmpeg no pudo leer el audio. Si es un vídeo MP4, debe contener una pista de audio. " + result.stderr[-2000:])


def _make_separator(directory: Path):
    # Imports remain lazy so validation and the UI can run without loading ML libraries.
    # audio-separator invokes "ffmpeg" by name, while imageio uses a versioned name.
    tools = directory / "tools"
    tools.mkdir()
    executable = tools / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    shutil.copy2(ffmpeg(), executable)
    previous_path = os.environ.get("PATH", "")
    os.environ["PATH"] = str(tools) + os.pathsep + previous_path
    try:
        from audio_separator.separator import Separator
        class FloatWavSeparator(Separator):
            def setup_torch_device(self, system_info):
                # Consistent CPU operation on Windows and both Mac architectures.
                import torch
                self.torch_device_cpu = torch.device("cpu")
                self.torch_device = self.torch_device_cpu
                self.torch_device_mps = None
                self.onnx_execution_provider = ["CPUExecutionProvider"]

            def separate(self, audio_file_path, custom_output_names=None):
                # Route by stem label, supporting both the Intel 0.24 API and
                # 0.30 on ARM/Windows, without changing dependency source files.
                names = {key.lower(): value for key, value in (custom_output_names or {}).items()}
                original = self.model_instance.final_process
                def finish(stem_path, samples, stem_name):
                    destination = Path(names[stem_name.lower()] + ".wav")
                    _write_float_wav(destination, samples, self.sample_rate)
                    return {stem_name: samples}
                self.model_instance.final_process = finish
                try:
                    return super().separate(audio_file_path)
                finally:
                    self.model_instance.final_process = original

        return FloatWavSeparator(model_file_dir=str(cache_dir()), output_dir=str(directory),
                         output_format="WAV", use_soundfile=True,
                         normalization_threshold=1.0, amplification_threshold=0.0,
                         demucs_params={"segment_size": "Default", "shifts": 1,
                                        "overlap": 0.25, "segments_enabled": True})
    finally:
        os.environ["PATH"] = previous_path


def _separate(directory: Path, source: Path, model: str, names: dict[str, str], factory):
    directory.mkdir(parents=True)
    separator = factory(directory)
    separator.load_model(model_filename=model)
    # In audio-separator 0.30.x the SoundFile writer ignores output_dir.
    # Absolute custom names keep every intermediate inside this job's workspace.
    separator.separate(str(source), custom_output_names={
        stem: str((directory / name).resolve()) for stem, name in names.items()
    })
    del separator
    gc.collect()
    paths = {name: directory / (name + ".wav") for name in names.values()}
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise RuntimeError("El modelo no ha generado los stems esperados: " + ", ".join(missing))
    return paths


def run(job: Job, status: Callable[[str], None] = print,
        cancel: threading.Event | None = None, factory=None) -> Path:
    job.validate()
    cancel = cancel or threading.Event()
    factory = factory or _make_separator

    def check():
        if cancel.is_set():
            raise Cancelled("Separación cancelada; no se han publicado resultados parciales.")

    check()
    job.destination.mkdir(parents=True, exist_ok=True)
    # Temporary output on the destination filesystem permits atomic publication.
    with tempfile.TemporaryDirectory(prefix=".stem-work-", dir=job.destination) as temporary:
        work = Path(temporary)
        decoded = work / "input.wav"
        status("Decodificando audio estéreo…")
        convert(job.source, decoded, stereo=True)
        check()
        status("Separando seis instrumentos; la primera ejecución descarga los modelos…")
        names = {k: k for k in ["drums", "bass", "vocals", "guitar", "piano", "other"]}
        paths = _separate(work / "instruments", decoded, MODEL, names, factory)
        check()
        if job.split_vocals and {"vocals", "backing_vocals"}.intersection(job.stems):
            status("Separando voz principal y coros (experimental)…")
            vocal_paths = _separate(work / "voices", paths["vocals"], VOCAL_MODEL,
                                   {"Vocals": "lead", "Instrumental": "backing"}, factory)
            paths["vocals"] = vocal_paths["lead"]
            paths["backing_vocals"] = vocal_paths["backing"]
        check()
        result = work / "result"
        result.mkdir()
        for key in job.stems:
            check()
            status(f"Exportando {STEMS[key]}…")
            convert(paths[key], result / f"{key}.{job.format}")
        (result / "separation.json").write_text(json.dumps({
            "app_version": "0.3.0", "input": job.source.name,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "stems": job.stems, "format": job.format,
            "model": MODEL, "vocal_model": VOCAL_MODEL if job.split_vocals and
            {"vocals", "backing_vocals"}.intersection(job.stems) else None,
            "vocals_content": "lead" if job.split_vocals else "all vocals",
            "sample_rate": 44100, "channels": 2,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        check()
        # Reserve a unique name; never overwrite a previous run.
        for index in range(1, 100000):
            final = job.destination / f"{job.source.stem}_stems_{index:03d}"
            try:
                final.mkdir()
            except FileExistsError:
                continue
            try:
                for item in result.iterdir():
                    shutil.move(str(item), final / item.name)
            except BaseException:
                shutil.rmtree(final)
                raise
            break
        else:
            raise RuntimeError("No se pudo reservar una carpeta de salida.")
    status(f"Completado: {final}")
    return final

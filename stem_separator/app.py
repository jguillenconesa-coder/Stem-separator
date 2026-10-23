"""Native Windows-friendly Tk UI; inference runs outside Tk's main thread."""
import logging
import os
from pathlib import Path
import queue
import threading
import subprocess
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .engine import STEMS, Cancelled, Job, ffmpeg, run


class Application:
    def __init__(self, root):
        self.root = root
        root.title("Stem Separator")
        root.geometry("960x900")
        root.minsize(840, 850)
        root.configure(background="#202126")
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.running = False
        self.output = None
        self.preview_directory = tempfile.TemporaryDirectory(prefix="stem-preview-")
        self.track_files = {}
        self.track_canvases = {}
        self.track_buttons = {}
        self.preview_loading = False
        self.source = tk.StringVar()
        self.destination = tk.StringVar(value=str(Path.home() / "Music" / "Stem Separator"))
        self.format = tk.StringVar(value="wav")
        self.split = tk.BooleanVar(value=True)
        self.selected = {key: tk.BooleanVar(value=True) for key in STEMS}
        self.controls = []
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#202126")
        style.configure("TLabel", background="#202126", foreground="#eceef4", font=("Segoe UI", 10))
        style.configure("TCheckbutton", background="#202126", foreground="#eceef4", font=("Segoe UI", 10))
        style.map("TCheckbutton", background=[("active", "#30323a")], foreground=[("disabled", "#7e8390")])
        style.configure("TRadiobutton", background="#202126", foreground="#eceef4")
        style.map("TRadiobutton", background=[("active", "#30323a")])
        style.configure("TEntry", fieldbackground="#30323a", foreground="#ffffff", insertcolor="#ffffff")
        style.configure("TButton", background="#393c46", foreground="#ffffff", padding=(10, 6))
        style.map("TButton", background=[("active", "#515665")], foreground=[("disabled", "#858a97")])
        style.configure("TProgressbar", background="#73cf8c", troughcolor="#30323a")
        viewport = tk.Canvas(root, background="#202126", highlightthickness=0)
        scrollbar = ttk.Scrollbar(root, orient="vertical", command=viewport.yview)
        scrollbar.pack(side="right", fill="y")
        viewport.pack(side="left", fill="both", expand=True)
        viewport.configure(yscrollcommand=scrollbar.set)
        panel = ttk.Frame(viewport, padding=24)
        window = viewport.create_window((0, 0), window=panel, anchor="nw")
        panel.bind("<Configure>", lambda _: viewport.configure(scrollregion=viewport.bbox("all")))
        viewport.bind("<Configure>", lambda event: viewport.itemconfigure(window, width=event.width))
        root.bind("<MouseWheel>", lambda event: viewport.yview_scroll(-int(event.delta / 120), "units"))
        ttk.Label(panel, text="STEM SEPARATOR", font=("Segoe UI", 23, "bold")).pack(anchor="w")
        ttk.Label(panel, text="SEPARACIÓN LOCAL  /  7 STEMS  /  WAV + MP3", foreground="#a9afbc").pack(anchor="w", pady=(0, 18))
        for title, variable, command in [
            ("Audio de entrada · WAV / MP3", self.source, self.pick_source),
            ("Carpeta de exportación", self.destination, self.pick_destination),
        ]:
            ttk.Label(panel, text=title).pack(anchor="w")
            row = ttk.Frame(panel)
            row.pack(fill="x", pady=(4, 12))
            entry = ttk.Entry(row, textvariable=variable)
            entry.pack(side="left", fill="x", expand=True)
            button = ttk.Button(row, text="Examinar…", command=command)
            button.pack(side="right", padx=(8, 0))
            self.controls.extend([entry, button])
        ttk.Label(panel, text="Stems que quieres exportar", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(4, 8))
        grid = ttk.Frame(panel)
        grid.pack(fill="x")
        grid.columnconfigure(2, weight=1)
        colors = ["#e4b564", "#8bacef", "#b48ce3", "#dc91b7", "#7bc695", "#72c7d4", "#a4a9b6"]
        for i, ((key, label), color) in enumerate(zip(STEMS.items(), colors)):
            tk.Frame(grid, background=color, width=5, height=39).grid(row=i, column=0, padx=(0, 9), pady=3)
            check = ttk.Checkbutton(grid, text=label, variable=self.selected[key], width=23)
            check.grid(row=i, column=1, sticky="w", padx=(0, 12), pady=3)
            self.controls.append(check)
            canvas = tk.Canvas(grid, height=39, background="#2c2e35", highlightthickness=0)
            canvas.grid(row=i, column=2, sticky="ew", pady=3)
            canvas.create_text(12, 19, anchor="w", text="Sin audio generado", fill="#858b99")
            self.track_canvases[key] = (canvas, color)
            button = ttk.Button(grid, text="▶ Escuchar", command=lambda stem=key: self.preview(stem), state="disabled")
            button.grid(row=i, column=3, padx=(10, 0))
            self.track_buttons[key] = button
        split = ttk.Checkbutton(panel, text="Distinguir voz principal y coros (segunda etapa experimental)", variable=self.split)
        split.pack(anchor="w", pady=(12, 4))
        self.controls.append(split)
        ttk.Label(panel, text="Desactívalo para exportar todas las voces juntas en vocals.\nLos coros pueden contener voz principal residual y reverberación.").pack(anchor="w")
        row = ttk.Frame(panel)
        row.pack(fill="x", pady=14)
        ttk.Label(row, text="Formato de salida:").pack(side="left")
        for value, label in [("wav", "WAV · 24 bits"), ("mp3", "MP3 · 320 kbps")]:
            radio = ttk.Radiobutton(row, text=label, value=value, variable=self.format)
            radio.pack(side="left", padx=12)
            self.controls.append(radio)
        row = ttk.Frame(panel)
        row.pack(fill="x")
        self.start = ttk.Button(row, text="Separar y exportar", command=self.begin)
        self.start.pack(side="left")
        self.stop = ttk.Button(row, text="Cancelar", state="disabled", command=self.request_cancel)
        self.stop.pack(side="left", padx=8)
        self.open_button = ttk.Button(row, text="Abrir resultados", command=self.open_result, state="disabled")
        self.open_button.pack(side="left")
        ttk.Button(row, text="■ Detener", command=self.stop_preview).pack(side="left", padx=8)
        ttk.Button(row, text="Créditos", command=self.credits).pack(side="right")
        self.progress = ttk.Progressbar(panel, mode="indeterminate")
        self.progress.pack(fill="x", pady=(16, 8))
        self.status = tk.StringVar(value="Listo. La primera separación necesita Internet para descargar los modelos.")
        ttk.Label(panel, textvariable=self.status, wraplength=690).pack(anchor="w")
        ttk.Label(panel, text="Procesamiento local · CPU · Salida estéreo a 44,1 kHz\nPuede tardar varios minutos. Se calculan seis pistas y solo se exportan las elegidas.", foreground="#a9afbc").pack(anchor="w", pady=(12, 0))
        root.after(100, self.poll)

    def pick_source(self):
        path = filedialog.askopenfilename(filetypes=[("Audio", "*.wav *.mp3"), ("WAV", "*.wav"), ("MP3", "*.mp3")])
        if path:
            self.source.set(path)

    def pick_destination(self):
        path = filedialog.askdirectory()
        if path:
            self.destination.set(path)

    def begin(self):
        self.stop_preview()
        try:
            if not self.destination.get().strip():
                raise ValueError("Selecciona una carpeta de exportación.")
            job = Job(Path(self.source.get()), Path(self.destination.get()),
                      tuple(k for k, v in self.selected.items() if v.get()), self.format.get(), self.split.get())
            job.validate()
        except ValueError as error:
            messagebox.showerror("Revisa la selección", str(error))
            return
        self.cancel.clear()
        self.running = True
        for canvas, _ in self.track_canvases.values():
            canvas.delete("all")
            canvas.create_text(12, 19, anchor="w", text="En espera de resultados", fill="#858b99")
        for control in self.controls + [self.start, self.open_button] + list(self.track_buttons.values()):
            control.configure(state="disabled")
        self.stop.configure(state="normal")
        self.progress.start()
        threading.Thread(target=self.worker, args=(job,), daemon=True).start()

    def worker(self, job):
        try:
            path = run(job, lambda text: self.events.put(("status", text)), self.cancel)
            self.events.put(("done", path))
        except Cancelled as error:
            self.events.put(("cancelled", str(error)))
        except Exception as error:
            logging.exception("Separation failed")
            self.events.put(("error", str(error)))

    def request_cancel(self):
        self.cancel.set()
        self.stop.configure(state="disabled")
        self.status.set("Cancelación solicitada. Esperando a que termine la etapa actual…")

    def poll(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "preview":
                    self.preview_loading = False
                    self.start.configure(state="normal")
                    if data:
                        self.status.set(data)
                    continue
                if kind == "waveforms":
                    for key, peaks in data.items():
                        canvas, color = self.track_canvases[key]
                        canvas.delete("all")
                        width = max(canvas.winfo_width(), 50)
                        for index, peak in enumerate(peaks):
                            x = index * width / len(peaks)
                            canvas.create_line(x, 20 - peak * 17, x, 20 + peak * 17, fill=color)
                    continue
                if kind == "status":
                    if not self.cancel.is_set():
                        self.status.set(data)
                    continue
                self.running = False
                self.progress.stop()
                for control in self.controls + [self.start]:
                    control.configure(state="normal")
                self.stop.configure(state="disabled")
                if kind == "done":
                    self.output = data
                    self.track_files = {key: next(iter(data.glob(key + ".*")), None) for key in STEMS}
                    for key, button in self.track_buttons.items():
                        button.configure(state="normal" if self.track_files[key] and os.name == "nt" else "disabled")
                    threading.Thread(target=self.waveforms, daemon=True).start()
                    self.open_button.configure(state="normal")
                    self.status.set(f"Completado: {data}")
                else:
                    self.status.set(data)
                    if kind == "error":
                        messagebox.showerror("No se pudo completar", data + "\n\nConsulta el registro en %LOCALAPPDATA%\\StemSeparator\\app.log.")
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def open_result(self):
        if self.output and os.name == "nt":
            os.startfile(self.output)

    def stop_preview(self):
        if os.name == "nt":
            import winsound
            winsound.PlaySound(None, 0)

    def preview(self, key):
        if self.preview_loading or self.running or not self.track_files.get(key):
            return
        self.stop_preview()
        self.preview_loading = True
        self.start.configure(state="disabled")
        self.status.set(f"Preparando escucha: {STEMS[key]}…")
        def play():
            try:
                import winsound
                target = Path(self.preview_directory.name) / 'listen.wav'
                result = subprocess.run([ffmpeg(), '-nostdin', '-hide_banner', '-loglevel', 'error', '-y',
                    '-i', str(self.track_files[key]), '-c:a', 'pcm_s16le', str(target)], capture_output=True,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                if result.returncode:
                    raise RuntimeError('No se pudo preparar la escucha.')
                winsound.PlaySound(str(target), winsound.SND_FILENAME | winsound.SND_ASYNC)
                self.events.put(('preview', f"Escuchando: {STEMS[key]}"))
            except Exception as error:
                self.events.put(('preview', f"Error de escucha: {error}"))
        threading.Thread(target=play, daemon=True).start()

    def waveforms(self):
        import numpy as np
        import soundfile as sf
        peaks = {}
        for key, path in self.track_files.copy().items():
            if path:
                try:
                    with sf.SoundFile(path) as audio:
                        blocksize = max(1, (len(audio) + 399) // 400)
                        values = [float(np.max(np.abs(block))) for block in audio.blocks(blocksize=blocksize)]
                        maximum = max(values, default=0) or 1
                        peaks[key] = [value / maximum for value in values]
                except Exception:
                    logging.exception('Waveform unavailable for %s', key)
        self.events.put(('waveforms', peaks))

    def credits(self):
        messagebox.showinfo("Créditos y licencias", "Stem Separator 0.1.0 · jguillenconesa-coder\n\n"
            "Demucs / htdemucs_6s: Meta Research y colaboradores (MIT).\n"
            "audio-separator: Andrew Beveridge / Nomad Karaoke (MIT).\n"
            "UVR / Karaoke 2: Anjok07, TRvlvr y colaboradores UVR.\n"
            "PyTorch, ONNX Runtime, NumPy, SoundFile y FFmpeg.\n\n"
            "Consulta THIRD_PARTY_NOTICES.md y las licencias incluidas.\n"
            "Los pesos se descargan aparte; sus términos son independientes.")

    def close(self):
        if self.running or self.preview_loading:
            messagebox.showinfo("Separación en curso", "Pulsa Cancelar y espera a que termine la etapa actual antes de cerrar.")
            return
        self.stop_preview()
        self.preview_directory.cleanup()
        self.root.destroy()


def main():
    directory = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".cache")) / "StemSeparator"
    directory.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=directory / "app.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    root = tk.Tk()
    Application(root)
    root.mainloop()

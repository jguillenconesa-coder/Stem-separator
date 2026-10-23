from pathlib import Path
import json
import threading

import numpy as np
import pytest
import soundfile as sf

from stem_separator.engine import Cancelled, Job, convert, run


@pytest.fixture
def audio(tmp_path):
    path = tmp_path / 'mezcla estéreo.wav'
    t = np.arange(4410) / 44100
    sf.write(path, np.column_stack([.1 * np.sin(440 * 2 * np.pi * t), .1 * np.sin(660 * 2 * np.pi * t)]), 44100)
    return path


class FakeSeparator:
    """Only replaces inference; real audio decoding and exports still run."""
    def __init__(self, directory):
        self.directory = directory

    def load_model(self, model_filename):
        pass

    def separate(self, source, custom_output_names):
        data, rate = sf.read(source)
        for name in custom_output_names.values():
            sf.write(self.directory / (name + '.wav'), data * .5, rate)


@pytest.mark.parametrize('input_format,output_format', [('wav', 'wav'), ('wav', 'mp3'), ('mp3', 'wav'), ('mp3', 'mp3')])
def test_selected_exports_and_audio_roundtrip(audio, tmp_path, input_format, output_format):
    if input_format == 'mp3':
        converted = tmp_path / 'entrada.mp3'
        convert(audio, converted)
        audio = converted
    job = Job(audio, tmp_path / 'exports', ('bass', 'vocals', 'backing_vocals'), output_format)
    result = run(job, lambda _: None, factory=FakeSeparator)
    assert {p.name for p in result.iterdir()} == {f'bass.{output_format}', f'vocals.{output_format}', f'backing_vocals.{output_format}', 'separation.json'}
    for stem in job.stems:
        decoded = tmp_path / f'{stem}_decoded.wav'
        convert(result / f'{stem}.{output_format}', decoded)
        data, rate = sf.read(decoded)
        assert data.shape == (4410, 2)
        assert rate == 44100
        assert np.isfinite(data).all() and np.max(np.abs(data)) > 0
    assert json.loads((result / 'separation.json').read_text())['vocal_model']
    second = run(job, lambda _: None, factory=FakeSeparator)
    assert result != second and result.is_dir()
    assert not list(job.destination.glob('.stem-work-*'))


def test_cancel_does_not_publish(audio, tmp_path):
    stop = threading.Event()
    def status(text):
        if text.startswith('Separando seis'):
            stop.set()
    destination = tmp_path / 'exports'
    with pytest.raises(Cancelled):
        run(Job(audio, destination, ('drums',)), status, stop, FakeSeparator)
    assert not list(destination.iterdir())


def test_inference_failure_cleans_up(audio, tmp_path):
    class Broken(FakeSeparator):
        def separate(self, *args, **kwargs):
            raise RuntimeError('inference failed')
    destination = tmp_path / 'exports'
    with pytest.raises(RuntimeError, match='inference failed'):
        run(Job(audio, destination, ('piano',)), factory=Broken)
    assert not list(destination.iterdir())


def test_combined_vocals_skips_second_model(audio, tmp_path):
    models = []
    class Spy(FakeSeparator):
        def load_model(self, model_filename):
            models.append(model_filename)
    run(Job(audio, tmp_path / 'exports', ('vocals',), split_vocals=False), factory=Spy)
    assert models == ['htdemucs_6s.yaml']


@pytest.mark.parametrize('stems,split', [((), True), (('unknown',), True), (('bass', 'bass'), True), (('backing_vocals',), False)])
def test_invalid_selection(audio, tmp_path, stems, split):
    with pytest.raises(ValueError):
        Job(audio, tmp_path, stems, split_vocals=split).validate()


def test_corrupt_audio_fails_without_results(tmp_path):
    audio = tmp_path / 'bad.mp3'
    audio.write_bytes(b'not audio')
    output = tmp_path / 'exports'
    with pytest.raises(RuntimeError, match='FFmpeg'):
        run(Job(audio, output, ('drums',)), factory=FakeSeparator)
    assert not list(output.iterdir())

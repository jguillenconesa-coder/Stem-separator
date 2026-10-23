"""Integration diagnostics shared by source and installed executable."""
from pathlib import Path
import tempfile


def check_models():
    """Exercise real inference; synthetic input does not measure musical quality."""
    import numpy as np
    import soundfile as sf
    from .engine import Job, STEMS, run, convert
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        t = np.arange(44100 * 4) / 44100
        signal = .12 * np.sin(2 * np.pi * 220 * t) + .04 * np.sin(2 * np.pi * 880 * t)
        source = root / 'smoke.wav'
        sf.write(source, np.column_stack([signal, signal * .8]), 44100)
        result = run(Job(source, root / 'exports', tuple(STEMS)))
        for key in STEMS:
            data, rate = sf.read(result / f'{key}.wav')
            if rate != 44100 or data.shape != (len(t), 2) or not np.isfinite(data).all():
                raise RuntimeError(f'Invalid audio output: {key}, {data.shape}, {rate}')
        encoded = root / 'smoke.mp3'
        convert(result / 'vocals.wav', encoded)
        decoded = root / 'roundtrip.wav'
        convert(encoded, decoded)
        data, rate = sf.read(decoded)
        if data.shape != (len(t), 2) or rate != 44100:
            raise RuntimeError('MP3 roundtrip failed')
        print('PASS: real Demucs + Karaoke inference, seven stereo WAV exports, MP3 roundtrip')


def check_desktop():
    import tkinter as tk
    from .app import Application
    root = tk.Tk()
    root.withdraw()
    app = Application(root)
    root.update()
    app.close()
    print('PASS: desktop initialization')

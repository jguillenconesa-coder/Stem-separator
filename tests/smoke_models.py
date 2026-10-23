"""Real weights/inference smoke test. Requires network on first run.

Synthetic stereo audio tests execution, not musical separation quality.
"""
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import soundfile as sf
from stem_separator.engine import Job, STEMS, run

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    t = np.arange(44100 * 4) / 44100
    signal = .12 * np.sin(2 * np.pi * 220 * t) + .04 * np.sin(2 * np.pi * 880 * t)
    source = root / 'smoke.wav'
    sf.write(source, np.column_stack([signal, signal * .8]), 44100)
    result = run(Job(source, root / 'exports', tuple(STEMS)))
    for key in STEMS:
        data, rate = sf.read(result / f'{key}.wav')
        assert rate == 44100 and data.shape == (len(t), 2), (key, data.shape)
        assert np.isfinite(data).all(), key
    print('PASS: real Demucs + Karaoke inference, seven stereo WAV exports')

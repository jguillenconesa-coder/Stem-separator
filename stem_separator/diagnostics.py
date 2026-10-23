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
        # Exercise newly supported containers using the FFmpeg binary in the package.
        import subprocess
        from .engine import ffmpeg
        from .playback import prepare_audio
        for suffix, codec in [('flac', 'flac'), ('mp4', 'aac')]:
            media = root / ('import.' + suffix)
            args = [ffmpeg(), '-nostdin', '-loglevel', 'error', '-y']
            if suffix == 'mp4':
                args += ['-f', 'lavfi', '-i', 'color=c=black:s=16x16:r=25:d=4']
            args += ['-i', str(source)]
            if suffix == 'mp4':
                args += ['-map', '0:v:0', '-map', '1:a:0', '-c:v', 'mpeg4', '-shortest']
            args += ['-c:a', codec, str(media)]
            subprocess.run(args, check=True, capture_output=True,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            imported = root / (suffix + '.wav')
            convert(media, imported, stereo=True)
            data, rate = sf.read(imported)
            if rate != 44100 or data.ndim != 2 or data.shape[1] != 2 or not np.max(np.abs(data)) > 0:
                raise RuntimeError(f'{suffix} audio extraction failed')
            preview = prepare_audio(media, root / (suffix + '-preview.wav'))
            if sf.info(preview).subtype != 'PCM_16':
                raise RuntimeError('Seekable playback preparation failed')
        print('PASS: real Demucs + Karaoke inference, seven stereo WAV exports, MP3 roundtrip')
        print('PASS: FLAC and MP4 video audio import, seekable preview preparation')


def check_desktop():
    import tkinter as tk
    from .app import Application
    root = tk.Tk()
    root.withdraw()
    app = Application(root)
    root.update()
    app.track_durations.update(drums=30.0, bass=30.0)
    app.track_peaks['drums'] = [.2, .8, .4]
    app.draw_track('drums')
    width = max(app.track_canvases['drums'][0].winfo_width() - 1, 1)
    app.seek_track('drums', width / 2, start=True)
    if app.track_positions['drums'] != 15.0:
        raise RuntimeError('Waveform seeking failed')
    app.nudge_track('drums', 5)
    if app.track_positions['drums'] != 20.0 or app.track_positions['bass'] != 0:
        raise RuntimeError('Independent track cursors failed')
    if not app.track_canvases['drums'][0].find_withtag('playhead'):
        raise RuntimeError('Playback cursor was not drawn')
    app.close()
    print('PASS: desktop initialization, waveform seeking and independent cursors')

from pathlib import Path
import numpy as np
import pytest
import soundfile as sf

from stem_separator.playback import WindowsPlayer, clamp_position, prepare_audio


class Device:
    """MCI command transport without requiring an audio device on CI servers."""
    def __init__(self):
        self.commands = []
        self.offset = 0
        self.mode = 'stopped'

    def __call__(self, command):
        self.commands.append(command)
        if command.endswith(' length'):
            return '10000'
        if command.endswith(' position'):
            return str(self.offset)
        if command.endswith(' mode'):
            return self.mode
        if command.startswith('seek '):
            self.offset = int(command.rsplit(' ', 1)[1])
        if command.startswith('play '):
            self.mode = 'playing'
        if command.startswith('stop '):
            self.mode = 'stopped'
        return ''


def test_native_seek_reuses_open_file_and_reports_real_position(tmp_path):
    device = Device()
    player = WindowsPlayer(device)
    path = tmp_path / 'pista estéreo.wav'
    player.play(path, 3.25)
    assert player.position() == 3.25 and player.playing()
    player.stop()
    assert not player.playing() and player.position() == 3.25
    player.play(path, 7.5)
    assert player.position() == 7.5
    assert sum(command.startswith('open ') for command in device.commands) == 1
    player.play(tmp_path / 'other.wav', 1)
    assert 'close stem_separator_preview' in device.commands
    player.close()
    assert player.path is None


def test_seek_clamps_to_track_bounds_and_does_not_play_past_end(tmp_path):
    device = Device()
    player = WindowsPlayer(device)
    player.play(tmp_path / 'audio.wav', -5)
    assert player.position() == 0
    before = sum(command.startswith('play ') for command in device.commands)
    player.play(tmp_path / 'audio.wav', 500)
    assert player.position() == 10
    assert sum(command.startswith('play ') for command in device.commands) == before


@pytest.mark.parametrize('value,duration', [(float('nan'), 4), (3, float('inf')), (2, -1)])
def test_invalid_cursor_values(value, duration):
    with pytest.raises(ValueError):
        clamp_position(value, duration)


def test_preview_decode_preserves_stereo_timing_and_content(tmp_path):
    rate = 44100
    source = tmp_path / 'source.flac'
    t = np.arange(rate) / rate
    original = np.column_stack([.2 * np.sin(2*np.pi*220*t), .1 * np.sin(2*np.pi*440*t)])
    sf.write(source, original, rate)
    target = prepare_audio(source, tmp_path / 'preview.wav')
    decoded, actual_rate = sf.read(target)
    assert actual_rate == rate and decoded.shape == original.shape
    assert sf.info(target).subtype == 'PCM_16'
    # A seek to 0.6 s must point to that region, with distinct left/right channels.
    np.testing.assert_allclose(decoded[int(.6*rate):], original[int(.6*rate):], atol=1e-4)


def test_failed_prepare_removes_partial_preview(tmp_path):
    source = tmp_path / 'invalid.mp3'
    source.write_bytes(b'bad audio')
    destination = tmp_path / 'preview.wav'
    destination.write_bytes(b'old preview')
    with pytest.raises(RuntimeError):
        prepare_audio(source, destination)
    assert not destination.exists()


class MacAudio:
    def __init__(self):
        self.time = 0.0
        self.active = False
        self.closed = False
    def duration(self): return 10.0
    def currentTime(self): return self.time
    def setCurrentTime_(self, value): self.time = value
    def play(self): self.active = True; return True
    def pause(self): self.active = False
    def isPlaying(self): return self.active
    def stop(self): self.active = False; self.closed = True


def test_mac_seek_pause_resume_and_switch_tracks(tmp_path):
    from stem_separator.playback import MacPlayer
    created = []
    def factory(path):
        audio = MacAudio()
        created.append(audio)
        return audio
    player = MacPlayer(factory)
    path = tmp_path / 'pista estéreo.wav'
    player.play(path, 3.25)
    assert player.playing() and player.position() == 3.25
    player.stop()
    assert not player.playing() and player.position() == 3.25
    player.play(path, 8)
    assert len(created) == 1 and player.position() == 8
    player.play(path, 500)
    assert player.position() == 10 and not player.playing()
    player.play(tmp_path / 'other.wav', -2)
    assert created[0].closed and player.position() == 0
    player.close()
    assert created[1].closed and player.path is None

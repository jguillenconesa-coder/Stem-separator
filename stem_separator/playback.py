"""Seekable Windows WAV playback, using the OS multimedia API (no extra player)."""
from pathlib import Path
import math
import subprocess

from .engine import ffmpeg


def clamp_position(seconds: float, duration: float) -> float:
    if not math.isfinite(seconds) or not math.isfinite(duration) or duration < 0:
        raise ValueError('Posición o duración inválida.')
    return min(max(0.0, seconds), duration)


def format_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f'{seconds // 60:02d}:{seconds % 60:02d}'


def prepare_audio(source: Path, destination: Path):
    """Decode once per stem; subsequent seeks use native playback, not re-encoding."""
    result = subprocess.run([ffmpeg(), '-nostdin', '-hide_banner', '-loglevel', 'error', '-y',
        '-i', str(source), '-map', '0:a:0', '-vn', '-ac', '2', '-ar', '44100',
        '-c:a', 'pcm_s16le', str(destination)], capture_output=True, text=True,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        destination.unlink(missing_ok=True)
        raise RuntimeError('No se pudo preparar la escucha: ' + result.stderr[-1000:])
    return destination


class WindowsPlayer:
    """All methods must run on the UI thread, which owns the MCI device."""
    def __init__(self, command=None):
        self._command = command or self._native_command
        self.path = None
        self.alias = 'stem_separator_preview'
        self.duration = 0.0

    @staticmethod
    def _native_command(command):
        import ctypes
        from ctypes import wintypes
        winmm = ctypes.WinDLL('winmm')
        send = winmm.mciSendStringW
        send.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.UINT, wintypes.HWND]
        send.restype = wintypes.DWORD
        buffer = ctypes.create_unicode_buffer(1024)
        error = send(command, buffer, len(buffer), None)
        if error:
            describe = winmm.mciGetErrorStringW
            describe.argtypes = [wintypes.DWORD, wintypes.LPWSTR, wintypes.UINT]
            describe.restype = wintypes.BOOL
            describe(error, buffer, len(buffer))
            raise RuntimeError('No se pudo reproducir el audio: ' + buffer.value)
        return buffer.value

    def play(self, path: Path, seconds: float):
        path = path.resolve()
        if self.path != path:
            self.close()
            if '"' in str(path):
                raise ValueError('Ruta de reproducción inválida.')
            self._command(f'open "{path}" type waveaudio alias {self.alias}')
            self.path = path
            try:
                self._command(f'set {self.alias} time format milliseconds')
                self.duration = int(self._command(f'status {self.alias} length')) / 1000
            except Exception:
                self.close()
                raise
        offset = round(clamp_position(seconds, self.duration) * 1000)
        self._command(f'stop {self.alias}')
        self._command(f'seek {self.alias} to {offset}')
        if offset < round(self.duration * 1000):
            self._command(f'play {self.alias} from {offset}')

    def position(self):
        return int(self._command(f'status {self.alias} position')) / 1000 if self.path else 0.0

    def playing(self):
        return self.path is not None and self._command(f'status {self.alias} mode').strip() == 'playing'

    def stop(self):
        if self.path:
            self._command(f'stop {self.alias}')

    def close(self):
        if self.path:
            try:
                self._command(f'close {self.alias}')
            finally:
                self.path = None
                self.duration = 0.0


class MacPlayer:
    """Native AVAudioPlayer transport with the same per-track seek semantics."""
    def __init__(self, factory=None):
        self._factory = factory or self._native_player
        self._player = None
        self.path = None
        self.duration = 0.0

    @staticmethod
    def _native_player(path):
        from AVFoundation import AVAudioPlayer
        from Foundation import NSURL
        player, error = AVAudioPlayer.alloc().initWithContentsOfURL_error_(
            NSURL.fileURLWithPath_(str(path)), None)
        if player is None:
            raise RuntimeError(f'No se pudo abrir el audio: {error}')
        player.prepareToPlay()
        return player

    def play(self, path: Path, seconds: float):
        path = path.resolve()
        if self.path != path:
            self.close()
            player = self._factory(path)
            duration = float(player.duration())
            clamp_position(0, duration)
            self._player, self.path, self.duration = player, path, duration
        self._player.pause()
        position = clamp_position(seconds, self.duration)
        self._player.setCurrentTime_(position)
        if position < self.duration and not self._player.play():
            raise RuntimeError('macOS no ha podido iniciar la reproducción de audio.')

    def position(self):
        return float(self._player.currentTime()) if self._player else 0.0

    def playing(self):
        return bool(self._player and self._player.isPlaying())

    def stop(self):
        if self._player:
            self._player.pause()

    def close(self):
        if self._player:
            self._player.stop()
        self._player = None
        self.path = None
        self.duration = 0.0


def playback_supported():
    import sys
    return sys.platform in {'win32', 'darwin'}


def make_player():
    import sys
    return MacPlayer() if sys.platform == 'darwin' else WindowsPlayer()

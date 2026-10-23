"""Collect the native Mac dylib, excluding the wheel's other architectures."""
from pathlib import Path
from PyInstaller.utils.hooks import get_module_file_attribute

package = Path(get_module_file_attribute('samplerate')).parent
binaries = [(str(package / '_samplerate_data' / 'libsamplerate.dylib'), 'samplerate/_samplerate_data')]
hiddenimports = ['_cffi_backend', 'samplerate._src']

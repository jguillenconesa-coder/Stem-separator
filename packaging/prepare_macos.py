"""Use the checksum-verified Homebrew libsamplerate for the current architecture."""
import importlib.util
from pathlib import Path
import shutil
import subprocess

package = Path(importlib.util.find_spec('samplerate').origin).parent
prefix = Path(subprocess.check_output(['brew', '--prefix', 'libsamplerate'], text=True).strip())
source = prefix / 'lib' / 'libsamplerate.dylib'
if not source.is_file():
    raise RuntimeError('Homebrew libsamplerate dylib is missing')
shutil.copy2(source, package / '_samplerate_data' / 'libsamplerate.dylib')
print('Prepared native libsamplerate:', source.resolve())

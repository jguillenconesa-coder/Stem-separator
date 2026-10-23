"""Mount, install and launch a DMG with bounded operations and startup diagnostics."""
from pathlib import Path
import shutil
import subprocess
import tempfile


def execute(*command, timeout=180):
    print('STAGE:', command, flush=True)
    subprocess.run(command, check=True, timeout=timeout)


root = Path(__file__).resolve().parents[1]
dmg = next((root / 'dist' / 'installer').glob('*.dmg'))
mount = Path(tempfile.mkdtemp())
installed = Path(tempfile.mkdtemp())
try:
    execute('hdiutil', 'attach', str(dmg), '-nobrowse', '-readonly', '-mountpoint', str(mount))
    execute('ditto', str(mount / 'Stem Separator.app'), str(installed / 'Stem Separator.app'), timeout=300)
    execute('hdiutil', 'detach', str(mount))
    marker = installed / 'self-test.json'
    execute(str(installed / 'Stem Separator.app' / 'Contents' / 'MacOS' / 'Stem Separator'),
            '--self-test', str(marker), timeout=300)
    if not marker.is_file():
        raise RuntimeError('Installed application did not produce its success marker')
    print(marker.read_text())
except BaseException:
    directory = Path.home() / 'Library' / 'Application Support' / 'StemSeparator'
    for name in ['runtime.log', 'self-test.log']:
        path = directory / name
        if path.is_file():
            print(name, path.read_text(errors='replace')[-16000:], flush=True)
    raise
finally:
    subprocess.run(['hdiutil', 'detach', str(mount), '-force'], timeout=30, check=False)
    shutil.rmtree(mount, ignore_errors=True)
    shutil.rmtree(installed, ignore_errors=True)

#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
version=$(python -c 'from stem_separator import __version__; print(__version__)')
architecture=$(uname -m)
uvr=$(python -c "import audio_separator, pathlib; print(pathlib.Path(audio_separator.__file__).parent / 'separator' / 'uvr_lib_v5')")
python -m PyInstaller --noconfirm --clean --onedir --windowed --name 'Stem Separator' \
  --osx-bundle-identifier io.github.jguillenconesa.stemseparator \
  --additional-hooks-dir packaging/hooks \
  --collect-all audio_separator --collect-all imageio_ffmpeg --collect-all onnxruntime \
  --collect-all librosa --collect-all torch --collect-all torchaudio --collect-all torchvision \
  --collect-all onnx2torch --collect-all scipy --collect-all sklearn --collect-all soxr \
  --collect-all AVFoundation --collect-all Foundation --collect-all objc \
  --hidden-import AppKit --hidden-import CoreMedia \
  --recursive-copy-metadata audio-separator --copy-metadata tqdm --copy-metadata rotary-embedding-torch \
  --add-data "$uvr:audio_separator/separator/uvr_lib_v5" \
  --add-data 'LICENSE:.' --add-data 'THIRD_PARTY_NOTICES.md:.' run_app.py
app='dist/Stem Separator.app'
python packaging/collect_licenses.py "$app/Contents/Resources/licenses"
cp packaging/libsamplerate-LICENSE.txt "$app/Contents/Resources/licenses/libsamplerate-LICENSE.txt"
python - "$app" "$version" <<'PY'
from pathlib import Path
import plistlib, sys
path = Path(sys.argv[1]) / 'Contents' / 'Info.plist'
with path.open('rb') as file:
    info = plistlib.load(file)
info.update(CFBundleShortVersionString=sys.argv[2], CFBundleVersion=sys.argv[2],
            LSMinimumSystemVersion='15.0', NSHighResolutionCapable=True)
with path.open('wb') as file:
    plistlib.dump(info, file)
PY
codesign --force --deep --sign - "$app"
codesign --verify --deep --strict "$app"
mkdir -p dist/installer
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
ditto "$app" "$stage/Stem Separator.app"
ln -s /Applications "$stage/Applications"
hdiutil create -volname 'Stem Separator' -srcfolder "$stage" -ov -format UDZO \
  "dist/installer/StemSeparator-${version}-macOS-${architecture}.dmg"
(cd dist/installer && shasum -a 256 ./*.dmg > "SHA256-macOS-${architecture}.txt")

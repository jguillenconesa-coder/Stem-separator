$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
function Check-Exit { if ($LASTEXITCODE -ne 0) { throw "Command failed: $LASTEXITCODE" } }
python -m PyInstaller --noconfirm --clean --onedir --windowed --name StemSeparator `
  --collect-all audio_separator --collect-all imageio_ffmpeg --collect-all onnxruntime `
  --collect-all librosa --collect-all torch --collect-all torchaudio --collect-all torchvision `
  --collect-all onnx2torch --collect-all scipy --collect-all sklearn `
  --copy-metadata audio-separator --copy-metadata tqdm --copy-metadata rotary-embedding-torch `
  --add-data 'LICENSE;.' --add-data 'THIRD_PARTY_NOTICES.md;.' run_app.py
Check-Exit
$licenses = 'dist/StemSeparator/licenses'
New-Item -ItemType Directory -Force $licenses | Out-Null
python packaging/collect_licenses.py $licenses
Check-Exit
$iscc = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
if (-not $iscc) { $iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
if (-not (Test-Path $iscc)) { throw 'Install Inno Setup 6 to generate the installer.' }
& $iscc packaging/windows.iss
Check-Exit
Get-FileHash dist/installer/*.exe -Algorithm SHA256 | Format-List | Out-File dist/installer/SHA256.txt

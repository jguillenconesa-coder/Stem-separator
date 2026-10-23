#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
dmg=$(find dist/installer -name '*.dmg' -print -quit)
mount=$(mktemp -d)
installed=$(mktemp -d)
trap 'hdiutil detach "$mount" >/dev/null 2>&1 || true; rm -rf "$mount" "$installed"' EXIT
hdiutil attach "$dmg" -nobrowse -readonly -mountpoint "$mount"
ditto "$mount/Stem Separator.app" "$installed/Stem Separator.app"
hdiutil detach "$mount"
marker="$installed/self-test.json"
if ! "$installed/Stem Separator.app/Contents/MacOS/Stem Separator" --self-test "$marker"; then
  cat "$HOME/Library/Application Support/StemSeparator/runtime.log" 2>/dev/null || true
  exit 1
fi
test -s "$marker"
cat "$marker"

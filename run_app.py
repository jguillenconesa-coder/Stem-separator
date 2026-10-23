"""Frozen executable entry point, including installed-runtime diagnostics."""
import json
import os
from pathlib import Path
import sys
import traceback


def bootstrap():
    from stem_separator.engine import data_dir
    directory = data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    # Windowed executables have no console. ML libraries still write progress.
    stream = None
    if sys.stdout is None or sys.stderr is None:
        stream = open(directory / 'runtime.log', 'a', encoding='utf-8', buffering=1)
        sys.stdout = sys.stdout or stream
        sys.stderr = sys.stderr or stream
    if len(sys.argv) == 3 and sys.argv[1] == '--self-test':
        marker = Path(sys.argv[2])
        marker.unlink(missing_ok=True)
        try:
            from stem_separator.diagnostics import check_desktop, check_models
            check_desktop()
            check_models()
            marker.write_text(json.dumps({'desktop': 'passed', 'real_models': 'passed', 'mp3': 'passed'}), encoding='utf-8')
        except Exception:
            traceback.print_exc()
            raise SystemExit(1)
    else:
        from stem_separator.app import main
        main()


if __name__ == '__main__':
    bootstrap()

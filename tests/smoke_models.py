"""Real weights/inference check. Requires network on the first run."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stem_separator.diagnostics import check_models
import traceback

try:
    check_models()
except Exception:
    # Make model failures visible in public CI annotations, without API credentials.
    detail = traceback.format_exc().replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print('::error title=Real model smoke test::' + detail)
    raise

"""Real weights/inference check. Requires network on the first run."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stem_separator.diagnostics import check_models

check_models()

"""Ensure the project root is importable for `common`, `agents`, etc.,
regardless of whether pytest is invoked as `pytest` or `python -m pytest`.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

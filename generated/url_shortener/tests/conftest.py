"""
conftest.py

Ensures generated/url_shortener/ (this directory's parent) is on sys.path
so tests can `import app.*` regardless of where pytest is invoked from.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


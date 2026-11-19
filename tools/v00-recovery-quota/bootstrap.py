"""Reuse the pinned, isolated email profile; no installation or network effects."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v00-upstream-auth"))

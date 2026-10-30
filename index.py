"""Vercel entry point: the FastAPI app from backend/ (see vercel.json for the routes it serves)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.main import app  # noqa: E402

__all__ = ["app"]

"""So `uvicorn main:app` works from this folder, as well as `uvicorn app.main:app`."""

from app.main import app

__all__ = ["app"]

"""Vercel Services entrypoint for the package-based FastAPI application."""

import sys
from pathlib import Path


repository_root = str(Path(__file__).resolve().parent.parent)
if repository_root not in sys.path:
    sys.path.insert(0, repository_root)

from api.main import app

__all__ = ["app"]

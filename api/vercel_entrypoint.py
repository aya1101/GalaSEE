"""Vercel Services entrypoint for the package-based FastAPI application."""

import sys
import types
from pathlib import Path


service_root = Path(__file__).resolve().parent
repository_root = service_root.parent
for import_root in (service_root, repository_root):
    import_root_string = str(import_root)
    if import_root_string not in sys.path:
        sys.path.insert(0, import_root_string)


def load_app():
    """Load the app in both repo-preserving and flattened Vercel layouts."""
    try:
        from api.main import app
    except ModuleNotFoundError as error:
        if error.name != "api":
            raise

        # A Vercel service can be materialized with its configured root as the
        # module root. In that layout the sibling modules still use package
        # relative imports, so provide the package namespace explicitly.
        package = types.ModuleType("api")
        package.__path__ = [str(service_root)]
        package.__package__ = "api"
        sys.modules["api"] = package
        from api.main import app
    return app


app = load_app()

__all__ = ["app"]

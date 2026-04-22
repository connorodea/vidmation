"""Jinja2 templates instance — extracted to break the circular import.

``web/app.py`` imports route modules, which need ``get_templates``.
Putting ``get_templates`` here means routes can import it without
triggering the partially-initialised ``web.app`` error.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).parent / "templates"


def get_templates() -> Jinja2Templates:
    """Get Jinja2 templates instance."""
    return Jinja2Templates(directory=str(TEMPLATES_DIR))

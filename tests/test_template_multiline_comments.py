"""Django {# #} comments must be single-line; multi-line ones render as literal text."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"node_modules", "staticfiles", ".git", "venv", ".venv"}
OPEN_WITHOUT_CLOSE = re.compile(r"\{#(?!.*#\})")


def _templates():
    for path in ROOT.rglob("templates/**/*"):
        if path.is_file() and path.suffix in {".html", ".txt"} and not SKIP_DIRS.intersection(path.parts):
            yield path


def test_no_multiline_django_comments():
    offenders = []
    for path in _templates():
        for n, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if OPEN_WITHOUT_CLOSE.search(line):
                offenders.append(f"{path.relative_to(ROOT)}:{n}")
    assert not offenders, "Use {% comment %} for multi-line comments:\n" + "\n".join(offenders)

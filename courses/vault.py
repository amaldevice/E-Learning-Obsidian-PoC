import os
import re
import tempfile
from pathlib import Path

import frontmatter
from django.conf import settings
from filelock import FileLock

SAFE_SLUG = re.compile(r"[^a-z0-9_-]+")
VAULT_ROOT = Path(settings.BASE_DIR) / "vaults"


def _safe(s: str) -> str:
    return SAFE_SLUG.sub("-", s.lower()).strip("-") or "untitled"


def vault_rel_path(vpath: Path) -> str:
    """Return vault path relatif to BASE_DIR for DB storage (portable)."""
    try:
        return str(vpath.resolve().relative_to(Path(settings.BASE_DIR).resolve()))
    except ValueError:
        return str(vpath)


def _safe(s: str) -> str:
    return SAFE_SLUG.sub("-", s.lower()).strip("-") or "untitled"


def vault_path(username: str, course_slug: str, lesson_slug: str) -> Path:
    p = VAULT_ROOT / _safe(username) / _safe(course_slug) / f"{_safe(lesson_slug)}.md"
    # Guard traversal: resolved path must be inside VAULT_ROOT
    try:
        p.resolve().relative_to(VAULT_ROOT.resolve())
    except ValueError:
        raise ValueError("Invalid vault path: traversal detected")
    return p


def read_note(path: Path) -> tuple[dict, str]:
    if not path.exists():
        return {}, ""
    post = frontmatter.load(str(path))
    return post.metadata, post.content


def write_note_atomic(path: Path, metadata: dict, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(content, **metadata)
    # Use mkstemp-style tmp to avoid .md.tmp double-ext artifacts on crash
    tmp_fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    os.close(tmp_fd)
    tmp = Path(tmp_name)
    lock = FileLock(str(path) + ".lock")
    try:
        tmp.write_text(frontmatter.dumps(post), encoding="utf-8")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass

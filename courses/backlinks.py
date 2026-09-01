import re
from pathlib import Path

from .vault import VAULT_ROOT, _safe

WIKILINK_RE = re.compile(r"(!?)\[\[([^|\]#]+)(?:#([^|\]]+))?(?:\|([^\]]+))?\]\]")
# Also used by courses/views.py for tag extraction on save
TAG_RE = re.compile(r"(?<![\w/])#([a-zA-Z0-9/_-]+)")

def _strip_for_scan(text: str) -> str:
    # strip frontmatter at start: --- ... --- (handle \r\n and optional trailing newline)
    text = re.sub(r"^---\r?\n.*?\r?\n---\r?\n?", "", text, flags=re.DOTALL)
    # strip fenced code blocks
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # strip inline code
    text = re.sub(r"`[^`]*`", "", text)
    return text


def _normalize_target(target: str) -> str:
    """Normalize wikilink target for comparison: lowercase, strip, safe each segment."""
    target = target.strip().lower()
    # split by / to preserve path separator, safe each segment
    parts = target.split("/")
    safe_parts = [_safe(p) for p in parts]
    return "/".join(safe_parts)


def get_backlinks(username: str, target_lesson_slug: str, course_slug: str) -> list[dict]:
    """
    Scan vaults/<username>/**/*.md on-demand, return list of source notes
    that contain a wikilink to target_lesson_slug (or course_slug/target_lesson_slug).

    Isolation: only scans vault of given username.
    Stripping: frontmatter, fenced code, inline code removed before scan.
    Returns: list of dicts with keys course_slug, lesson_slug, path
    """
    safe_user = _safe(username)
    user_vault = VAULT_ROOT / safe_user
    if not user_vault.exists():
        return []

    # normalized variants to match
    target_lesson_norm = _normalize_target(target_lesson_slug)
    course_norm = _safe(course_slug.lower())
    target_with_course = f"{course_norm}/{target_lesson_norm}"
    variants = {target_lesson_norm, target_with_course}

    results: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for md_path in user_vault.rglob("*.md"):
        # derive source course/lesson from relative path
        try:
            rel = md_path.relative_to(user_vault)
        except ValueError:
            continue
        parts = rel.parts
        if len(parts) < 1:
            continue
        # vault layout is vaults/<user>/<course>/<lesson>.md
        # handle both 2-part and deeper nesting
        if len(parts) == 1:
            # file directly under user vault — skip (no course)
            continue
        src_course = parts[0]
        # lesson is stem of last part
        src_lesson = Path(parts[-1]).stem

        # skip self-reference (the target note itself)
        if _safe(src_course.lower()) == course_norm and _safe(src_lesson.lower()) == target_lesson_norm:
            continue

        try:
            text = md_path.read_text(encoding="utf-8")
        except Exception:
            continue

        stripped = _strip_for_scan(text)

        found = False
        for m in WIKILINK_RE.finditer(stripped):
            raw_target = m.group(2).strip()
            norm = _normalize_target(raw_target)
            if norm in variants:
                found = True
                break

        if found:
            key = (src_course, src_lesson)
            if key not in seen:
                seen.add(key)
                results.append(
                    {
                        "course_slug": src_course,
                        "lesson_slug": src_lesson,
                        "path": str(md_path),
                        "source": f"{src_course}/{src_lesson}",
                    }
                )

    return results

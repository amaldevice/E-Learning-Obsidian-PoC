import json
import re
from datetime import datetime, timezone

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .backlinks import TAG_RE, get_backlinks
from .markdown import render_markdown
from .models import Course, Lesson, Note
from .vault import read_note, vault_path, vault_rel_path, write_note_atomic


def _parse_json_body(request) -> dict:
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _extract_tags(content: str) -> list[str]:
    # Strip frontmatter + code before extracting #tag (reuse backlinks TAG_RE)
    stripped = re.sub(r"^---\r?\n.*?\r?\n---\r?\n", "", content, flags=re.DOTALL)
    stripped = re.sub(r"```.*?```", "", stripped, flags=re.DOTALL)
    stripped = re.sub(r"`[^`]*`", "", stripped)
    return sorted(set(TAG_RE.findall(stripped)))


def _youtube_embed_url(url: str) -> str:
    if not url:
        return ""
    if "youtube.com/embed/" in url or "youtu.be" in url:
        if "youtu.be" in url:
            m = re.search(r"youtu\.be/([^?&]+)", url)
            if m:
                return f"https://www.youtube.com/embed/{m.group(1)}"
        return url
    m = re.search(r"[?&]v=([^&]+)", url)
    if m:
        return f"https://www.youtube.com/embed/{m.group(1)}"
    return url


@login_required
def course_list(request):
    courses = Course.objects.all().order_by("title")
    return render(request, "courses/course_list.html", {"courses": courses})


@login_required
def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug)
    lessons = course.lessons.all()
    return render(
        request, "courses/course_detail.html", {"course": course, "lessons": lessons}
    )

@login_required
def lesson_detail(request, course_slug, lesson_slug):
    course = get_object_or_404(Course, slug=course_slug)
    lesson = get_object_or_404(Lesson, course=course, slug=lesson_slug)

    is_fetch = request.headers.get("X-Requested-With") == "fetch" or "application/json" in request.headers.get("Accept", "")

    # Handle POST save (supports both form POST and fetch JSON/form)
    if request.method == "POST":
        # Support JSON body for fetch autosave
        if request.content_type == "application/json":
            data = _parse_json_body(request)
            content = data.get("content", "")
        else:
            content = request.POST.get("content", "")
        # Derive vault path from authenticated user + course/lesson slugs (IDOR guard: never trust client path)
        try:
            vpath = vault_path(request.user.username, course.slug, lesson.slug)
        except ValueError:
            if is_fetch or request.content_type == "application/json":
                return JsonResponse({"ok": False, "error": "Invalid path."}, status=400)
            messages.error(request, "Invalid path.")
            return redirect("lesson-detail", course_slug=course.slug, lesson_slug=lesson.slug)

        now = datetime.now(timezone.utc).isoformat()
        # Try to preserve created from existing file
        existing_meta, _ = read_note(vpath)
        created = existing_meta.get("created", now)
        tags = _extract_tags(content)
        # Merge with existing tags if content has no tags (preserve manual tags)
        if not tags and existing_meta.get("tags"):
            tags = existing_meta["tags"]
        metadata = {
            "title": lesson.title,
            "course": course.slug,
            "lesson": lesson.slug,
            "created": created,
            "updated": now,
            "tags": tags,
        }
        write_note_atomic(vpath, metadata, content)
        Note.objects.update_or_create(
            user=request.user,
            lesson=lesson,
            defaults={"vault_path": vault_rel_path(vpath)},
        )
        if is_fetch or request.content_type == "application/json":
            return JsonResponse({"ok": True, "updated": now})
        messages.success(request, "Catatan tersimpan.")
        return redirect(
            "lesson-detail", course_slug=course.slug, lesson_slug=lesson.slug
        )

    content_html = render_markdown(lesson.content_md)
    youtube_embed = _youtube_embed_url(lesson.youtube_url)

    lessons = list(course.lessons.all())
    idx = next((i for i, ls in enumerate(lessons) if ls.pk == lesson.pk), None)
    prev_lesson = lessons[idx - 1] if idx is not None and idx > 0 else None
    next_lesson = (
        lessons[idx + 1] if idx is not None and idx < len(lessons) - 1 else None
    )
    # Load existing note for this user+lesson
    try:
        vpath = vault_path(request.user.username, course.slug, lesson.slug)
    except ValueError:
        vpath = None
    note_content = ""
    note_updated = None
    if vpath is not None and vpath.exists():
        meta, note_content = read_note(vpath)
        note_updated = meta.get("updated")

    # Backlinks: notes in this user's vault linking to this lesson
    try:
        backlinks = get_backlinks(request.user.username, lesson.slug, course.slug)
    except Exception:
        backlinks = []

    return render(
        request,
        "courses/lesson_detail.html",
        {
            "course": course,
            "lesson": lesson,
            "content_html": content_html,
            "youtube_embed": youtube_embed,
            "prev_lesson": prev_lesson,
            "next_lesson": next_lesson,
            "note_content": note_content,
            "note_updated": note_updated,
            "backlinks": backlinks,
        },
    )

@login_required
def lesson_preview(request, course_slug, lesson_slug):
    """POST JSON {content: str} -> {html: str} sanitized via markdown.py (nh3)."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    get_object_or_404(Course, slug=course_slug)
    get_object_or_404(Lesson, course__slug=course_slug, slug=lesson_slug)
    data = _parse_json_body(request)
    content = data.get("content", "")
    if not content and request.POST.get("content"):
        content = request.POST.get("content", "")
    html = render_markdown(content)
    return JsonResponse({"html": html})


# --- Vault views (T5) ---
def _user_vault(request) -> tuple[str, "Path"]:
    from .vault import VAULT_ROOT, _safe

    safe_user = _safe(request.user.username)
    return safe_user, VAULT_ROOT / safe_user


@login_required
def vault_list(request):
    from pathlib import Path

    from django.urls import reverse

    safe_user, user_vault = _user_vault(request)
    entries = []
    if user_vault.exists():
        for md_path in sorted(user_vault.rglob("*.md")):
            # Symlink guard: skip symlinks to avoid leaking outside vault
            if md_path.is_symlink():
                continue
            try:
                rel = md_path.relative_to(user_vault)
            except ValueError:
                continue
            parts = rel.parts
            if len(parts) < 2:
                continue
            course_slug = parts[0]
            lesson_slug = Path(parts[-1]).stem
            lesson_url = ""
            try:
                course = Course.objects.get(slug=course_slug)
                lesson = Lesson.objects.get(course=course, slug=lesson_slug)
                lesson_url = reverse(
                    "lesson-detail",
                    kwargs={"course_slug": course.slug, "lesson_slug": lesson.slug},
                )
            except Exception:
                pass
            meta: dict = {}
            try:
                meta, _ = read_note(md_path)
            except Exception:
                pass
            entries.append(
                {
                    "course_slug": course_slug,
                    "lesson_slug": lesson_slug,
                    "vault_path": str(rel),
                    "title": meta.get("title") or lesson_slug,
                    "lesson_url": lesson_url,
                }
            )
    return render(request, "vault/list.html", {"entries": entries, "username": request.user.username})


@login_required
def vault_download(request):
    import io
    import zipfile
    from datetime import date

    from django.http import FileResponse, HttpResponse

    safe_user, user_vault = _user_vault(request)
    files: list = []
    if user_vault.exists():
        files = [p for p in user_vault.rglob("*.md") if not p.is_symlink()]
    # Guard: max 1000 files
    if len(files) > 1000:
        return HttpResponse("Vault terlalu besar: melebihi 1000 file.", status=400)
    # Guard: max 50MB total
    total = 0
    for p in files:
        try:
            total += p.stat().st_size
        except OSError:
            continue
        if total > 50 * 1024 * 1024:
            return HttpResponse("Vault terlalu besar: melebihi 50MB.", status=400)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for md_path in files:
            try:
                arcname = md_path.relative_to(user_vault)
            except ValueError:
                continue
            zf.write(md_path, arcname)
    buf.seek(0)
    filename = f"vault-{safe_user}-{date.today().isoformat()}.zip"
    return FileResponse(buf, as_attachment=True, filename=filename, content_type="application/zip")

import re
from datetime import datetime, timezone

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .markdown import render_markdown
from .models import Course, Lesson, Note
from .vault import read_note, vault_path, write_note_atomic


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

    # Handle POST save
    if request.method == "POST":
        content = request.POST.get("content", "")
        # Derive vault path from authenticated user + course/lesson slugs (IDOR guard: never trust client path)
        try:
            vpath = vault_path(request.user.username, course.slug, lesson.slug)
        except ValueError:
            messages.error(request, "Invalid path.")
            return redirect("lesson-detail", course_slug=course.slug, lesson_slug=lesson.slug)

        now = datetime.now(timezone.utc).isoformat()
        # Try to preserve created from existing file
        existing_meta, _ = read_note(vpath)
        created = existing_meta.get("created", now)
        metadata = {
            "title": lesson.title,
            "course": course.slug,
            "lesson": lesson.slug,
            "created": created,
            "updated": now,
            "tags": existing_meta.get("tags", []),
        }
        write_note_atomic(vpath, metadata, content)
        # Upsert Note metadata
        Note.objects.update_or_create(
            user=request.user,
            lesson=lesson,
            defaults={"vault_path": str(vpath)},
        )
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
        },
    )

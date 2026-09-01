import re

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .markdown import render_markdown
from .models import Course, Lesson


def _youtube_embed_url(url: str) -> str:
    if not url:
        return ""
    # Already embed URL
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
    content_html = render_markdown(lesson.content_md)
    youtube_embed = _youtube_embed_url(lesson.youtube_url)

    lessons = list(course.lessons.all())
    idx = next((i for i, ls in enumerate(lessons) if ls.pk == lesson.pk), None)
    prev_lesson = lessons[idx - 1] if idx is not None and idx > 0 else None
    next_lesson = (
        lessons[idx + 1] if idx is not None and idx < len(lessons) - 1 else None
    )

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
        },
    )

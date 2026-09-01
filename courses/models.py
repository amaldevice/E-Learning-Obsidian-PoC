from django.db import models


class Course(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.title


class Lesson(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="lessons"
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField()
    order = models.PositiveIntegerField(default=0)
    content_md = models.TextField(blank=True)
    youtube_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("course", "slug")]
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return f"{self.course.slug}/{self.slug}"

from django.contrib import admin

from .models import Course, Lesson


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "course", "order")
    list_filter = ("course",)
    prepopulated_fields = {"slug": ("title",)}

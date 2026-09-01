from django.urls import path

from . import views

urlpatterns = [
    path("", views.course_list, name="course-list"),
    path("<slug:slug>/", views.course_detail, name="course-detail"),
    path(
        "<slug:course_slug>/lessons/<slug:lesson_slug>/",
        views.lesson_detail,
        name="lesson-detail",
    ),
]

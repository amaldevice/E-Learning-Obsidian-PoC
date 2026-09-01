from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Course, Lesson

User = get_user_model()


class CourseLessonTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="poc12345")
        self.course = Course.objects.create(
            title="Python Dasar", slug="python-dasar", description="Belajar Python"
        )
        self.lesson1 = Lesson.objects.create(
            course=self.course,
            title="Intro",
            slug="lesson-01",
            order=1,
            content_md="# Intro\nHello **world**",
            youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
        self.lesson2 = Lesson.objects.create(
            course=self.course,
            title="Variabel",
            slug="lesson-02",
            order=2,
            content_md="No video here",
        )
        self.lesson3 = Lesson.objects.create(
            course=self.course,
            title="Fungsi",
            slug="lesson-03",
            order=3,
            content_md="Third",
            youtube_url="https://youtu.be/abc123",
        )

    # --- auth ---

    def test_anon_redirect_to_login(self):
        for url in ["/courses/", f"/courses/{self.course.slug}/", f"/courses/{self.course.slug}/lessons/{self.lesson1.slug}/"]:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302)
            self.assertIn("/accounts/login/", resp["Location"])

    def test_login_works(self):
        resp = self.client.post(
            "/accounts/login/", {"username": "alice", "password": "poc12345"}
        )
        self.assertEqual(resp.status_code, 302)

    # --- course list ---

    def test_course_list_shows_courses(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get("/courses/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Python Dasar")
        self.assertContains(resp, "Belajar Python")

    def test_root_redirects_to_courses(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/courses/", resp["Location"])

    # --- course detail ---

    def test_course_detail_lists_lessons_in_order(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get(f"/courses/{self.course.slug}/")
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        # order: lesson-01 before lesson-02 before lesson-03
        self.assertLess(content.index("lesson-01"), content.index("lesson-02"))
        self.assertLess(content.index("lesson-02"), content.index("lesson-03"))

    # --- lesson detail ---

    def test_lesson_detail_renders_markdown(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get(
            f"/courses/{self.course.slug}/lessons/{self.lesson1.slug}/"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "<h1>Intro</h1>")
        self.assertContains(resp, "<strong>world</strong>")

    def test_lesson_detail_youtube_embed(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get(
            f"/courses/{self.course.slug}/lessons/{self.lesson1.slug}/"
        )
        self.assertContains(resp, "youtube.com/embed/dQw4w9WgXcQ")
        self.assertContains(resp, "<iframe")

    def test_lesson_detail_youtu_be_embed(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get(
            f"/courses/{self.course.slug}/lessons/{self.lesson3.slug}/"
        )
        self.assertContains(resp, "youtube.com/embed/abc123")

    def test_lesson_detail_no_youtube_no_iframe(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get(
            f"/courses/{self.course.slug}/lessons/{self.lesson2.slug}/"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "<iframe")

    def test_lesson_detail_xss_sanitized(self):
        self.lesson1.content_md = '<script>alert(1)</script> hello'
        self.lesson1.save()
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get(
            f"/courses/{self.course.slug}/lessons/{self.lesson1.slug}/"
        )
        self.assertNotContains(resp, "<script>")
        self.assertContains(resp, "hello")

    def test_lesson_prev_next(self):
        self.client.login(username="alice", password="poc12345")
        # middle lesson has both prev and next
        resp = self.client.get(
            f"/courses/{self.course.slug}/lessons/{self.lesson2.slug}/"
        )
        self.assertContains(resp, "lesson-01")
        self.assertContains(resp, "lesson-03")
        # first lesson has no prev
        resp = self.client.get(
            f"/courses/{self.course.slug}/lessons/{self.lesson1.slug}/"
        )
        self.assertNotContains(resp, "lesson-01.*←", html=False)
        self.assertContains(resp, "lesson-02")
        # last lesson has no next beyond
        resp = self.client.get(
            f"/courses/{self.course.slug}/lessons/{self.lesson3.slug}/"
        )
        self.assertContains(resp, "lesson-02")

    # --- model constraints ---

    def test_lesson_unique_together(self):
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            Lesson.objects.create(
                course=self.course, title="Dup", slug="lesson-01", order=99
            )

    def test_lesson_ordering(self):
        slugs = list(
            Course.objects.get(slug="python-dasar").lessons.values_list(
                "slug", flat=True
            )
        )
        self.assertEqual(slugs, ["lesson-01", "lesson-02", "lesson-03"])

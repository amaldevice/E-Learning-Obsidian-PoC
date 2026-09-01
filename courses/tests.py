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


class NoteVaultTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="poc12345")
        self.budi = User.objects.create_user(username="budi", password="poc12345")
        self.course = Course.objects.create(title="Python Dasar", slug="python-dasar")
        self.lesson = Lesson.objects.create(
            course=self.course, title="Intro", slug="lesson-01", order=1
        )

    def _lesson_url(self):
        return f"/courses/{self.course.slug}/lessons/{self.lesson.slug}/"

    def test_save_and_load_note(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.post(self._lesson_url(), {"content": "# Hello\nMy note"})
        self.assertEqual(resp.status_code, 302)
        # Reload should show saved content in textarea
        resp = self.client.get(self._lesson_url())
        self.assertContains(resp, "# Hello")
        self.assertContains(resp, "My note")

    def test_isolation_alice_budi(self):
        self.client.login(username="alice", password="poc12345")
        self.client.post(self._lesson_url(), {"content": "alice note"})
        self.client.logout()
        self.client.login(username="budi", password="poc12345")
        resp = self.client.get(self._lesson_url())
        self.assertNotContains(resp, "alice note")
        # budi saves different note
        self.client.post(self._lesson_url(), {"content": "budi note"})
        resp = self.client.get(self._lesson_url())
        self.assertContains(resp, "budi note")
        # alice still sees her note
        self.client.logout()
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get(self._lesson_url())
        self.assertContains(resp, "alice note")
        self.assertNotContains(resp, "budi note")

    def test_anon_cannot_save(self):
        resp = self.client.post(self._lesson_url(), {"content": "evil"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp["Location"])

    def test_note_model_unique_together(self):
        from django.db import IntegrityError

        from .models import Note

        Note.objects.create(
            user=self.alice, lesson=self.lesson, vault_path="vaults/alice/x.md"
        )
        with self.assertRaises(IntegrityError):
            Note.objects.create(
                user=self.alice, lesson=self.lesson, vault_path="vaults/alice/y.md"
            )

    def test_frontmatter_roundtrip(self):
        self.client.login(username="alice", password="poc12345")
        self.client.post(self._lesson_url(), {"content": "frontmatter test"})
        from .vault import read_note, vault_path

        vpath = vault_path("alice", self.course.slug, self.lesson.slug)
        meta, content = read_note(vpath)
        self.assertEqual(meta["course"], "python-dasar")
        self.assertEqual(meta["lesson"], "lesson-01")
        self.assertEqual(content.strip(), "frontmatter test")
        self.assertIn("tags", meta)


class VaultHelperTests(TestCase):
    def test_vault_path_sanitasi(self):
        from .vault import vault_path

        p = vault_path("Alice", "Python Dasar", "Lesson 01: Intro!")
        self.assertIn("alice", str(p))
        self.assertIn("python-dasar", str(p))
        self.assertIn("lesson-01-intro", str(p))

    def test_vault_path_traversal_guard(self):
        from .vault import vault_path

        # Username with traversal attempt should be sanitized, not escape
        p = vault_path("../../etc", "course", "lesson")
        # Should not escape vault root
        from django.conf import settings
        from pathlib import Path

        vault_root = Path(settings.BASE_DIR) / "vaults"
        self.assertTrue(str(p.resolve()).startswith(str(vault_root.resolve())))

    def test_write_read_atomic(self):
        import tempfile
        from pathlib import Path

        from .vault import read_note, write_note_atomic

        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "test.md"
            write_note_atomic(p, {"title": "T", "tags": ["a"]}, "hello world")
            meta, content = read_note(p)
            self.assertEqual(meta["title"], "T")
            self.assertEqual(content.strip(), "hello world")
            # Overwrite
            write_note_atomic(p, {"title": "T2", "tags": []}, "updated")
            meta, content = read_note(p)
            self.assertEqual(meta["title"], "T2")
            self.assertEqual(content.strip(), "updated")

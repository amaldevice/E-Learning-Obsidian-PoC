import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from .models import Course, Lesson

User = get_user_model()


class TempVaultMixin:
    """Isolate filesystem vault per test: override settings.VAULT_ROOT with a temp dir.

    Prevents tests from touching the dev vault at <BASE_DIR>/vaults.
    vault/backlinks/views read the root live via courses.vault.get_vault_root().
    """

    def _enter_vault_override(self):
        self._vault_tmp = tempfile.TemporaryDirectory(prefix="test-vaults-")
        self._vault_override = override_settings(VAULT_ROOT=self._vault_tmp.name)
        self._vault_override.enable()
        self.addCleanup(self._vault_override.disable)
        self.addCleanup(self._vault_tmp.cleanup)

    def setUp(self):
        super().setUp()
        self._enter_vault_override()
class CourseLessonTests(TempVaultMixin, TestCase):
    def setUp(self):
        super().setUp()
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

    def test_logout(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get("/courses/")
        self.assertEqual(resp.status_code, 200)
        # Logout via POST (Django 5+ requires POST)
        resp = self.client.post("/accounts/logout/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp["Location"])
        # After logout, anon should be redirected
        resp = self.client.get("/courses/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp["Location"])
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


class NoteVaultTests(TempVaultMixin, TestCase):
    def setUp(self):
        super().setUp()
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


class VaultHelperTests(TempVaultMixin, TestCase):
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

        vault_root = Path(settings.VAULT_ROOT)
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

    def test_vault_rel_path_is_relative(self):
        from .vault import vault_path, vault_rel_path

        vpath = vault_path("alice", "python-dasar", "lesson-01")
        rel = vault_rel_path(vpath)
        self.assertFalse(rel.startswith("/"))
        self.assertIn("alice", rel)
        self.assertTrue(rel.endswith("python-dasar/lesson-01.md"))
    def test_tags_extracted_on_save(self):
        # Tags #python etc should be extracted from content into frontmatter
        from django.contrib.auth import get_user_model as _GU

        User = _GU()
        alice = User.objects.create_user(username="alice2", password="poc12345")
        course = Course.objects.create(title="C", slug="c-tags")
        lesson = Lesson.objects.create(course=course, title="L", slug="l1", order=1)
        self.client.login(username="alice2", password="poc12345")
        self.client.post(f"/courses/{course.slug}/lessons/{lesson.slug}/", {"content": "Hello #python and #django here"})
        from .vault import read_note, vault_path

        vpath = vault_path("alice2", course.slug, lesson.slug)
        meta, _ = read_note(vpath)
        self.assertIn("python", meta.get("tags", []))
        self.assertIn("django", meta.get("tags", []))

class BacklinksTests(TempVaultMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.alice = User.objects.create_user(username="alice", password="poc12345")
        self.budi = User.objects.create_user(username="budi", password="poc12345")
        self.course = Course.objects.create(title="Python Dasar", slug="python-dasar")
        self.lesson1 = Lesson.objects.create(course=self.course, title="Intro", slug="lesson-01", order=1)
        self.lesson2 = Lesson.objects.create(course=self.course, title="Variabel", slug="lesson-02", order=2)
        self.lesson3 = Lesson.objects.create(course=self.course, title="Fungsi", slug="lesson-03", order=3)

    def _lesson_url(self, lesson):
        return f"/courses/{self.course.slug}/lessons/{lesson.slug}/"

    def _save_note(self, username, lesson, content):
        from datetime import datetime, timezone

        from .vault import vault_path, write_note_atomic

        vpath = vault_path(username, self.course.slug, lesson.slug)
        now = datetime.now(timezone.utc).isoformat()
        write_note_atomic(vpath, {"title": lesson.title, "course": self.course.slug, "lesson": lesson.slug, "created": now, "updated": now, "tags": []}, content)

    def test_backlinks_shows_sources(self):
        # 2 notes linking to lesson-01, GET lesson-01 shows backlinks
        self._save_note("alice", self.lesson2, "See [[lesson-01]] for intro")
        self._save_note("alice", self.lesson3, "Ref [[python-dasar/lesson-01|Intro]]")
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get(self._lesson_url(self.lesson1))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        # should list both sources
        self.assertIn("lesson-02", html)
        self.assertIn("lesson-03", html)
        # panel heading present
        self.assertIn("Backlinks", html)

    def test_backlinks_isolation(self):
        # budi's notes not in alice's backlinks
        self._save_note("budi", self.lesson2, "Budi links [[lesson-01]]")
        self._save_note("alice", self.lesson3, "Alice links [[lesson-01]]")
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get(self._lesson_url(self.lesson1))
        html = resp.content.decode()
        self.assertIn("lesson-03", html)
        from .backlinks import get_backlinks

        alice_bl = get_backlinks("alice", "lesson-01", "python-dasar")
        budi_bl = get_backlinks("budi", "lesson-01", "python-dasar")
        self.assertEqual(len(alice_bl), 1)
        self.assertEqual(alice_bl[0]["lesson_slug"], "lesson-03")
        self.assertEqual(len(budi_bl), 1)
        self.assertEqual(budi_bl[0]["lesson_slug"], "lesson-02")

    def test_backlinks_strips_frontmatter_and_code(self):
        # wikilink in fenced code and inline code should not count
        self._save_note("alice", self.lesson2, "```\n[[lesson-01]]\n```\nAlso `[[lesson-01]]` inline")
        # frontmatter wikilink: write raw file where frontmatter contains wikilink but content does not
        from pathlib import Path

        from .vault import vault_path, write_note_atomic
        from datetime import datetime, timezone

        vpath = vault_path("alice", self.course.slug, self.lesson3.slug)
        now = datetime.now(timezone.utc).isoformat()
        # frontmatter title contains wikilink, content clean
        write_note_atomic(vpath, {"title": "[[lesson-01]]", "course": self.course.slug, "lesson": self.lesson3.slug, "created": now, "updated": now, "tags": []}, "No link here")
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get(self._lesson_url(self.lesson1))
        html = resp.content.decode()
        self.assertIn("Tidak ada backlink", html)
        from .backlinks import get_backlinks

        bl = get_backlinks("alice", "lesson-01", "python-dasar")
        self.assertEqual(bl, [])

    def test_backlinks_regex_variants(self):
        # alias, heading, embed variants — single source file with multiple links should count as 1 backlink
        self._save_note("alice", self.lesson2, "Link [[lesson-01#heading]] and [[lesson-01|Alias]] and ![[lesson-01]]")
        from .backlinks import get_backlinks

        bl = get_backlinks("alice", "lesson-01", "python-dasar")
        self.assertEqual(len(bl), 1)
        self.assertEqual(bl[0]["lesson_slug"], "lesson-02")


class VaultListDownloadTests(TempVaultMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.alice = User.objects.create_user(username="alice", password="poc12345")
        self.budi = User.objects.create_user(username="budi", password="poc12345")
        self.course = Course.objects.create(title="Python Dasar", slug="python-dasar")
        self.course2 = Course.objects.create(title="Web Dasar", slug="web-dasar")
        self.lesson1 = Lesson.objects.create(course=self.course, title="Intro", slug="lesson-01", order=1)
        self.lesson2 = Lesson.objects.create(course=self.course, title="Variabel", slug="lesson-02", order=2)
        self.lesson_w1 = Lesson.objects.create(course=self.course2, title="HTML", slug="lesson-01-html", order=1)

    def _save_note(self, username, course_slug, lesson_slug, title, content):
        from datetime import datetime, timezone

        from .vault import vault_path, write_note_atomic

        vpath = vault_path(username, course_slug, lesson_slug)
        now = datetime.now(timezone.utc).isoformat()
        write_note_atomic(
            vpath,
            {"title": title, "course": course_slug, "lesson": lesson_slug, "created": now, "updated": now, "tags": []},
            content,
        )

    def test_vault_list_requires_login(self):
        resp = self.client.get("/vault/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp["Location"])

    def test_vault_download_requires_login(self):
        resp = self.client.get("/vault/download/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp["Location"])

    def test_vault_list_shows_own_files_and_links(self):
        self._save_note("alice", "python-dasar", "lesson-01", "Intro", "alice note 1")
        self._save_note("alice", "web-dasar", "lesson-01-html", "HTML", "alice note 2")
        self._save_note("budi", "python-dasar", "lesson-01", "Intro", "budi note")
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get("/vault/")
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        # alice sees her two notes
        self.assertIn("lesson-01", html)
        self.assertIn("lesson-01-html", html)
        # link to lesson present
        self.assertIn("/courses/python-dasar/lessons/lesson-01/", html)
        # budi's file must not leak via isolation — check entries count in context
        entries = resp.context["entries"]
        self.assertEqual(len(entries), 2)
        slugs = {(e["course_slug"], e["lesson_slug"]) for e in entries}
        self.assertIn(("python-dasar", "lesson-01"), slugs)
        self.assertIn(("web-dasar", "lesson-01-html"), slugs)

    def test_vault_list_isolation(self):
        self._save_note("alice", "python-dasar", "lesson-01", "Intro", "alice")
        self.client.login(username="budi", password="poc12345")
        resp = self.client.get("/vault/")
        self.assertEqual(resp.status_code, 200)
        entries = resp.context["entries"]
        self.assertEqual(len(entries), 0)

    def test_vault_download_zip_structure(self):
        self._save_note("alice", "python-dasar", "lesson-01", "Intro", "hello alice")
        self._save_note("alice", "python-dasar", "lesson-02", "Variabel", "second note")
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get("/vault/download/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/zip")
        self.assertIn("vault-alice-", resp["Content-Disposition"])
        self.assertIn(".zip", resp["Content-Disposition"])
        import io
        import zipfile

        data = b"".join(resp.streaming_content) if hasattr(resp, "streaming_content") else resp.content
        zf = zipfile.ZipFile(io.BytesIO(data))
        names = sorted(zf.namelist())
        self.assertIn("python-dasar/lesson-01.md", names)
        self.assertIn("python-dasar/lesson-02.md", names)
        # content preserved
        self.assertIn("hello alice", zf.read("python-dasar/lesson-01.md").decode())

    def test_vault_download_isolation(self):
        self._save_note("alice", "python-dasar", "lesson-01", "Intro", "alice secret")
        self._save_note("budi", "python-dasar", "lesson-01", "Intro", "budi secret")
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get("/vault/download/")
        import io
        import zipfile

        data = b"".join(resp.streaming_content) if hasattr(resp, "streaming_content") else resp.content
        zf = zipfile.ZipFile(io.BytesIO(data))
        content = zf.read("python-dasar/lesson-01.md").decode()
        self.assertIn("alice secret", content)
        self.assertNotIn("budi secret", content)
        # budi's download is separate
        self.client.logout()
        self.client.login(username="budi", password="poc12345")
        resp = self.client.get("/vault/download/")
        data = b"".join(resp.streaming_content) if hasattr(resp, "streaming_content") else resp.content
        zf = zipfile.ZipFile(io.BytesIO(data))
        content = zf.read("python-dasar/lesson-01.md").decode()
        self.assertIn("budi secret", content)
        self.assertNotIn("alice secret", content)

    def test_vault_download_empty_vault(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get("/vault/download/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/zip")
        import io
        import zipfile

        data = b"".join(resp.streaming_content) if hasattr(resp, "streaming_content") else resp.content
        zf = zipfile.ZipFile(io.BytesIO(data))
        self.assertEqual(zf.namelist(), [])

    def test_vault_download_guard_too_many_files(self):
        from unittest.mock import MagicMock, patch

        self.client.login(username="alice", password="poc12345")
        fake_files = []
        for i in range(1001):
            m = MagicMock()
            m.is_symlink.return_value = False
            m.relative_to.return_value = f"course/lesson-{i}.md"
            fake_files.append(m)
        with patch("courses.views._user_vault") as mock_user_vault:
            mock_vault = MagicMock()
            mock_vault.exists.return_value = True
            mock_vault.rglob.return_value = fake_files
            mock_user_vault.return_value = ("alice", mock_vault)
            resp = self.client.get("/vault/download/")
            self.assertEqual(resp.status_code, 400)
    def test_vault_download_guard_too_large(self):
        from unittest.mock import MagicMock, patch

        self.client.login(username="alice", password="poc12345")
        # 2 files each claiming 30MB -> total >50MB
        p1 = MagicMock()
        p1.stat.return_value.st_size = 30 * 1024 * 1024
        p1.relative_to.return_value = "python-dasar/lesson-01.md"
        p1.is_symlink.return_value = False
        p2 = MagicMock()
        p2.stat.return_value.st_size = 30 * 1024 * 1024
        p2.relative_to.return_value = "python-dasar/lesson-02.md"
        p2.is_symlink.return_value = False
        fake_files = [p1, p2]
        with patch("courses.views._user_vault") as mock_user_vault:
            mock_vault = MagicMock()
            mock_vault.exists.return_value = True
            mock_vault.rglob.return_value = fake_files
            mock_user_vault.return_value = ("alice", mock_vault)
            resp = self.client.get("/vault/download/")
            self.assertEqual(resp.status_code, 400)

    def test_vault_list_empty(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get("/vault/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Belum ada catatan")

    def test_header_vault_links_visible_when_logged_in(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get("/courses/")
        self.assertContains(resp, 'href="/vault/"')
        self.assertContains(resp, 'href="/vault/download/"')

class SeedPocTests(TempVaultMixin, TestCase):
    def test_seed_idempotent(self):
        from django.core.management import call_command

        call_command("seed_poc", verbosity=0)
        from django.contrib.auth import get_user_model as GU
        from courses.models import Course

        User = GU()
        count_users_1 = User.objects.filter(username__in=["alice", "budi", "citra", "dewi", "admin"]).count()
        count_courses_1 = Course.objects.count()
        call_command("seed_poc", verbosity=0)
        count_users_2 = User.objects.filter(username__in=["alice", "budi", "citra", "dewi", "admin"]).count()
        count_courses_2 = Course.objects.count()
        self.assertEqual(count_users_1, 5)
        self.assertEqual(count_users_2, 5)
        self.assertEqual(count_courses_1, count_courses_2)

    def test_seed_reset_cleans_vault(self):
        from django.core.management import call_command
        from pathlib import Path
        from django.conf import settings
        from courses.vault import _safe, vault_path, write_note_atomic

        call_command("seed_poc", verbosity=0)
        # Create a vault file
        vpath = vault_path("alice", "python-dasar", "lesson-01")
        write_note_atomic(vpath, {"title": "T", "tags": []}, "before reset")
        self.assertTrue(vpath.exists())
        call_command("seed_poc", "--reset", verbosity=0)
        # Vault should be cleaned
        self.assertFalse(vpath.exists())
        # Users and courses still exist after reset
        from django.contrib.auth import get_user_model as GU

        User = GU()
        self.assertTrue(User.objects.filter(username="alice").exists())

    def test_seed_creates_expected_courses_lessons(self):
        from django.core.management import call_command

        call_command("seed_poc", verbosity=0)
        from courses.models import Course

        self.assertTrue(Course.objects.filter(slug="python-dasar").exists())
        self.assertTrue(Course.objects.filter(slug="web-dasar").exists())
        py = Course.objects.get(slug="python-dasar")
        self.assertEqual(py.lessons.count(), 4)
        web = Course.objects.get(slug="web-dasar")
        self.assertEqual(web.lessons.count(), 3)


class HardeningTests(TempVaultMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.alice = User.objects.create_user(username="alice", password="poc12345")
        self.course = Course.objects.create(title="Python Dasar", slug="python-dasar")
        self.lesson = Lesson.objects.create(course=self.course, title="Intro", slug="lesson-01", order=1)

    def test_toast_timestamp_after_save(self):
        self.client.login(username="alice", password="poc12345")
        url = f"/courses/{self.course.slug}/lessons/{self.lesson.slug}/"
        resp = self.client.post(url, {"content": "hello"}, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Catatan tersimpan")
        resp = self.client.get(url)
        self.assertContains(resp, "Terakhir:")
    def test_traversal_via_slug_sanitized(self):
        # Even if someone crafts a request with traversal-like slug, vault_path sanitizes
        from courses.vault import vault_path

        p = vault_path("alice", "../../etc", "../../../passwd")
        from django.conf import settings
        from pathlib import Path

        vault_root = Path(settings.VAULT_ROOT)
        self.assertTrue(str(p.resolve()).startswith(str(vault_root.resolve())))
        self.assertNotIn("..", str(p))
    def test_symlink_skipped_in_vault_list(self):
        from pathlib import Path
        from unittest.mock import MagicMock, patch

        self.client.login(username="alice", password="poc12345")
        # Create real temp files to avoid MagicMock sorting issues
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "vault"
            vault.mkdir()
            (vault / "python-dasar").mkdir()
            (vault / "python-dasar" / "normal.md").write_text("---\ntitle: Normal\n---\nhello")
            # Symlink that should be skipped
            evil_target = vault / "python-dasar" / "evil.md"
            evil_target.symlink_to(vault / "python-dasar" / "normal.md")
            with patch("courses.views._user_vault", return_value=("alice", vault)):
                resp = self.client.get("/vault/")
                html = resp.content.decode()
                # normal should appear, evil symlink should be skipped
                self.assertIn("normal", html.lower())
                self.assertNotIn("evil", html)
        import threading
        from pathlib import Path

        from courses.vault import read_note, write_note_atomic

        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "concurrent.md"
            errors = []

            def writer(n):
                try:
                    write_note_atomic(p, {"title": f"T{n}", "tags": []}, f"content {n}")
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.assertEqual(errors, [])
            self.assertTrue(p.exists())
            meta, content = read_note(p)
            self.assertIn("content", content)

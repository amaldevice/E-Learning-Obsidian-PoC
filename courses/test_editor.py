import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Course, Lesson

User = get_user_model()


class EditorLessonTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="poc12345")
        self.course = Course.objects.create(title="Python Dasar", slug="python-dasar")
        self.lesson = Course.objects.get(slug="python-dasar").lessons.create(
            title="Intro", slug="lesson-01", order=1, content_md="Hello **world**"
        ) if False else None
        # Create lessons directly to avoid manager confusion
        self.lesson = Lesson.objects.create(
            course=self.course, title="Intro", slug="lesson-01", order=1, content_md="Hello **world**"
        )

    def _url(self):
        return f"/courses/{self.course.slug}/lessons/{self.lesson.slug}/"

    def _preview_url(self):
        return f"/courses/{self.course.slug}/lessons/{self.lesson.slug}/preview/"

    # --- editor UI present ---

    def test_lesson_page_shows_editor_split_view(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        # Split view structure
        self.assertIn('class="wrap"', html)
        self.assertIn('class="materi"', html)
        self.assertIn('class="editor"', html)
        # Tabs Edit/Preview
        self.assertIn('id="tab-edit"', html)
        self.assertIn('id="tab-preview"', html)
        self.assertIn('id="pane-edit"', html)
        self.assertIn('id="pane-preview"', html)
        # CodeMirror 6 via ESM CDN
        self.assertIn("codemirror", html.lower())
        self.assertIn("importmap", html)
        self.assertIn("@codemirror/view", html)
        self.assertIn("@codemirror/lang-markdown", html)
        # Custom extension highlight classes
        self.assertIn("hl-wikilink", html)
        self.assertIn("hl-tag", html)
        # Save + autosave + toast
        self.assertIn('id="btn-save"', html)
        self.assertIn("Autosave", html)
        self.assertIn('id="toast"', html)
        # Responsive CSS
        self.assertIn("@media(max-width:900px)", html)
        # Preview endpoint URL present
        self.assertIn("/preview/", html)

    def test_lesson_page_no_js_fallback_form(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get(self._url())
        self.assertIn("<noscript>", resp.content.decode())

    # --- save via fetch JSON + form POST still works ---

    def test_save_via_fetch_json(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.post(
            self._url(),
            data=json.dumps({"content": "# via fetch\nhello"}),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="fetch",
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["ok"])
        self.assertIn("updated", data)
        # Verify persisted
        resp2 = self.client.get(self._url())
        self.assertContains(resp2, "# via fetch")

    def test_save_via_fetch_json_without_x_requested_with(self):
        # Should also return JSON when content_type is json
        self.client.login(username="alice", password="poc12345")
        resp = self.client.post(
            self._url(),
            data=json.dumps({"content": "json content type only"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["ok"])

    def test_save_via_form_post_still_works(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.post(self._url(), {"content": "form save"})
        self.assertEqual(resp.status_code, 302)
        resp2 = self.client.get(self._url())
        self.assertContains(resp2, "form save")

    def test_save_isolation_fetch(self):
        self.client.login(username="alice", password="poc12345")
        self.client.post(
            self._url(),
            data=json.dumps({"content": "alice fetch"}),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="fetch",
        )
        self.client.logout()
        budi = User.objects.create_user(username="budi", password="poc12345")
        self.client.login(username="budi", password="poc12345")
        resp = self.client.get(self._url())
        self.assertNotContains(resp, "alice fetch")

    # --- preview endpoint ---

    def test_preview_renders_markdown(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.post(
            self._preview_url(),
            data=json.dumps({"content": "Hello **world**"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIn("<strong>world</strong>", data["html"])

    def test_preview_xss_sanitized(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.post(
            self._preview_url(),
            data=json.dumps({"content": '<script>alert(1)</script> hello <img src=x onerror=alert(1)>'}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertNotIn("<script", data["html"])
        # html:false escapes raw HTML, so <img> becomes &lt;img — no executable tag
        self.assertNotIn("<img", data["html"])
        self.assertIn("hello", data["html"])

    def test_preview_requires_login(self):
        resp = self.client.post(
            self._preview_url(),
            data=json.dumps({"content": "hello"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp["Location"])

    def test_preview_get_not_allowed(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get(self._preview_url())
        self.assertEqual(resp.status_code, 405)

    def test_preview_empty_content(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.post(
            self._preview_url(),
            data=json.dumps({"content": ""}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIn("html", data)

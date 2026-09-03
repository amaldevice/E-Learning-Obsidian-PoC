# Notes Guide Inline Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a collapsible "Panduan" help panel inside the lesson note editor teaching `[[wikilink]]`/`#tag` syntax and cross-course linking practices.

**Architecture:** Single-template static HTML change in `templates/courses/lesson_detail.html` (native `<details>`, no JS, no view/model changes), plus one test method in `courses/test_editor.py`. Follows existing inline-style pattern of the template.

**Tech Stack:** Django templates, existing CodeMirror 6 page, Django TestCase.

---

### Task 1: Failing test for the guide panel

**Files:**
- Modify: `courses/test_editor.py:62-65` (insert after `test_lesson_page_no_js_fallback_form`)

- [ ] **Step 1: Write the failing test**

Insert after line 65 (`self.assertIn("<noscript>", resp.content.decode())`), before line 67 (`# --- save via fetch JSON + form POST still works ---`):

```python
    def test_lesson_page_shows_notes_guide(self):
        self.client.login(username="alice", password="poc12345")
        resp = self.client.get(self._url())
        html = resp.content.decode()
        self.assertIn('id="notes-guide"', html)
        self.assertIn("[[", html)
        self.assertIn("#tag", html)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python manage.py test courses.test_editor.EditorLessonTests.test_lesson_page_shows_notes_guide -v 2`
Expected: FAIL with `AssertionError: 'id="notes-guide"' not found in ...`

- [ ] **Step 3: Commit the failing test**

```bash
git add courses/test_editor.py
git commit -m "test: add failing notes-guide panel assertion"
```

---

### Task 2: Add the guide panel markup

**Files:**
- Modify: `templates/courses/lesson_detail.html:58-63` (insert `<details>` between `<div class="tabs">` block end at line 56 and `<div id="pane-edit"` at line 58)

- [ ] **Step 1: Write minimal implementation**

Insert before line 58 (`<div id="pane-edit" class="pane active">`):

```html
    <details id="notes-guide" style="margin:0 12px 8px;border:1px solid #e5e7eb;border-radius:8px;background:#f9fafb;padding:8px 12px;font-size:13px">
      <summary style="cursor:pointer;font-weight:600">Panduan mencatat &amp; menghubungkan</summary>
      <div style="margin-top:8px;line-height:1.6">
        <p style="margin:0 0 6px"><strong>Sintaks:</strong></p>
        <ul style="margin:0 0 8px;padding-left:18px">
          <li><code>[[lesson-slug]]</code> — tautan ke lesson di course yang sama.</li>
          <li><code>[[course-slug/lesson-slug|Teks bacaan]]</code> — tautan antar course dengan alias.</li>
          <li><code>[[lesson-slug#judul-bagian]]</code> — akhiran heading diterima; tercatat sebagai backlink ke lesson tersebut (tanpa lompat bagian, dan tautan <code>[[...]]</code> tampil apa adanya di preview).</li>
          <li><code>#tag</code> / <code>#topik/subtopik</code> — tag; tersimpan ke frontmatter saat Save.</li>
        </ul>
        <p style="margin:0 0 6px"><strong>Contoh (salin-tempel):</strong></p>
        <ul style="margin:0 0 8px;padding-left:18px">
          <li><code>[[{{ course.slug }}/{{ lesson.slug }}|catatanku]]</code></li>
          <li><code>[[nama-course/lesson-02|konsep terkait]]</code></li>
        </ul>
        <p style="margin:0 0 6px"><strong>Kebiasaan:</strong></p>
        <ul style="margin:0;padding-left:18px">
          <li>Satu catatan, satu ide per lesson.</li>
          <li>Saat konsep muncul lagi di course lain, tautkan dengan <code>[[course/lesson|alias]]</code>.</li>
          <li>Beri 2–4 tag topik saja. Setelah menyimpan, cek panel Backlinks di bawah — tautanmu muncul di lesson tujuan.</li>
        </ul>
      </div>
    </details>
```

Notes for the engineer: `{{ course.slug }}` / `{{ lesson.slug }}` are already in template context from `courses/views.py:lesson_detail` (lines 143-144). The literal `[[...]]` text needs no escaping in Django templates. The second example uses placeholder slugs intentionally (no DB query for other courses — spec decision).

- [ ] **Step 2: Run the new test to verify it passes**

Run: `uv run python manage.py test courses.test_editor.EditorLessonTests.test_lesson_page_shows_notes_guide -v 2`
Expected: PASS (OK)

- [ ] **Step 3: Run the full editor + backlinks suites to verify nothing breaks**

Run: `uv run python manage.py test courses.test_editor courses.tests -v 1`
Expected: PASS (all OK)

- [ ] **Step 4: Commit**

```bash
git add templates/courses/lesson_detail.html courses/test_editor.py
git commit -m "feat: add inline notes-guide panel to lesson editor"
```

---

### Task 3: Manual verification in the browser

**Files:** none (verification only)

- [ ] **Step 1: Start the dev server and open a lesson page**

Run: `uv run python manage.py runserver`
Then open: `http://127.0.0.1:8000/courses/python-dasar/lessons/lesson-01/` (adjust slugs to local fixtures; log in first).
Expected: editor shows a closed "Panduan mencatat & menghubungkan" toggle above the editor.

- [ ] **Step 2: Expand the panel and check examples**

Click the toggle. Expected: syntax list, two copy-paste examples (first uses the current page's real `course/lesson` slugs), three practice bullets — all readable, no broken layout at desktop and narrow widths.

- [ ] **Step 3: Confirm the backlink loop still works**

In the editor, type `[[<other-lesson-slug>]]`, Save, open the target lesson page.
Expected: Backlinks panel on the target lists the source note (existing behavior, unchanged).

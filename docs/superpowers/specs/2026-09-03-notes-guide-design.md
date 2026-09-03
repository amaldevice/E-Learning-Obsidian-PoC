# Design: Panduan Catatan Inline (Notes Help Panel)

> Date: 2026-09-03 · Status: proposed · Scope: `templates/courses/lesson_detail.html` only

## Goal

Help users manage notes and link them across courses, taught exactly where they write:
a collapsible "Panduan" panel inside the note editor on lesson pages.

## Non-goals

- No graph view, no new endpoint/view/model/dependency.
- No interactive walkthrough or sample-note seeding (deferred; cheat-sheet + practices only).
- No change to backlink engine (`courses/backlinks.py`), vault I/O, or markdown rendering.

## Design

Single change in `templates/courses/lesson_detail.html`, editor section, above `#editor`:

- Native `<details id="notes-guide">` + `<summary>Panduan mencatat & menghubungkan</summary>`,
  closed by default. Zero JS, no-JS safe, no styling system beyond existing inline styles.
- Content (static HTML, Indonesian, matching UI language):
  1. `[[lesson-slug]]` — link to a lesson in the same course.
  2. `[[course-slug/lesson-slug|Teks bacaan]]` — link across courses with alias.
  3. `[[lesson-slug#judul-bagian]]` — link to a section (heading anchor).
  4. `#tag` / `#topik/subtopik` — tags; extracted on save into frontmatter.
  5. Two copy-paste examples using real slugs from the current page context
     (e.g. `[[{{ course.slug }}/{{ lesson.slug }}|catatanku]]` pattern + one cross-course example).
  6. Three practice bullets: one idea per note; link when a concept recurs in another
     course; tag sparingly (2–4 topic tags). Pointer: "link something, then check the
     Backlinks panel below — your link appears on the target lesson."
- Backlinks panel stays the live proof; no wiring between guide and panel.

## Alternatives considered

- Dedicated help page: keeps editor clean but removes help from the writing flow. Rejected.
- Guided tour overlay: better onboarding, but dismissable-once and more JS/state. Rejected for PoC.

## Verification

- `uv run python manage.py test courses.test_editor` passes.
- New assertion: lesson GET HTML contains the guide (e.g. `id="notes-guide"`,
  `[[` syntax sample, `#tag` sample).
- Manual: open a lesson page, expand Panduan, confirm examples render; save a note with
  `[[...]]` and confirm backlink appears on target lesson (existing behavior, unchanged).

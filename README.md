# E-Learning Obsidian PoC

PoC website E-Learning Django — Course → Lesson (teks + YouTube) + catatan belajar markdown per user yang disimpan sebagai vault Obsidian (`vaults/<username>/<course>/<lesson>.md`).

## Quick Start (uv)

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py seed_poc          # idempoten: 4 siswa + admin, 2 courses (4+3 lessons)
uv run python manage.py runserver
```

Buka http://127.0.0.1:8000/ — redirect ke `/courses/` (login required).

## Demo Accounts

Password semua: `poc12345`

| Username | Role |
|----------|------|
| alice | siswa |
| budi | siswa |
| citra | siswa |
| dewi | siswa |
| admin | superuser (Django admin di `/admin/`) |

## Seed

```bash
uv run python manage.py seed_poc --help   # lihat opsi
uv run python manage.py seed_poc          # idempoten — aman dijalankan berulang
uv run python manage.py seed_poc --reset  # hapus & buat ulang bersih
```

2 courses: `python-dasar` (4 lesson) + `web-dasar` (3 lesson) dengan `content_md` + `youtube_url` contoh.

## Alur Demo (3–5 user)

1. Login sebagai `alice` → buka Course → Lesson → lihat materi + video + Prev/Next
2. Di panel kanan lesson: ketik catatan markdown → **Save** (atau autosave 30s) → reload → catatan masih ada
3. Logout → login sebagai `budi` → buka lesson yang sama → catatan `alice` tidak terlihat → `budi` bisa buat catatan terpisah
4. Panel **Backlinks** di bawah editor: menampilkan catatan lain yang link via `[[wikilink]]`
5. Header → **Vault** (`/vault/`) → daftar semua catatan milik user → **Download .zip** (`/vault/download`) → buka di Obsidian desktop

## Vault

- Path: `vaults/<username>/<course>/<lesson>.md` — sanitasi `SAFE_SLUG` + traversal guard
- Frontmatter: `title, course, lesson, created, updated, tags` (array, Obsidian-compatible)
- File = source of truth, DB `Note` hanya metadata (`unique_together user+lesson`)
- Tanpa folder `.obsidian/` — kumpulan `.md` polos sudah valid vault

## Tech

- Django 6.1, SQLite, `markdown-it-py` + `nh3` (sanitasi), `python-frontmatter`, `filelock`
- Editor: CodeMirror 6 (ESM CDN) + highlight `[[wikilink]]`/`#tag`, Edit/Preview tabs (server render), autosave
- Test: `uv run python manage.py test courses --verbosity=2` (47 tests, HTTP seam + vault helper seam)

## Docs

- `CONTEXT.md` — glossary domain
- `docs/adr/` — 0001 vault layout, 0002 model domain, 0003 editor
- `docs/research-editor-vault.md` — research editor & vault I/O
- `docs/prototype/lesson.html` — prototype split view

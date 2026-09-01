# CONTEXT.md — PoC E-Learning + Catatan Obsidian per User

> Sumber kebenaran istilah domain untuk PoC ini. Dipakai oleh semua ADR, model, dan tiket wayfinder.

## Glossary

| Istilah | Definisi | Catatan |
|---------|----------|---------|
| **Course** | Kumpulan Lesson yang membentuk satu topik belajar (mis. "Python Dasar") | Model `Course`; slug unik; tanpa Enrollment untuk PoC (akses terbuka). |
| **Lesson** | Unit materi dalam Course: teks markdown (`content_md`) + opsional video YouTube (`youtube_url`), berurutan (`order`) | Model `Lesson`; `unique_together (course, slug)`; `ordering ["order"]`. |
| **Note** | Catatan belajar: 1 file markdown per user per lesson di Vault | Model `Note` hanya metadata (`user FK`, `lesson FK`, `vault_path`, timestamps); konten di file; `unique_together (user, lesson)` — lihat ADR 0001 & 0002. |
| **Vault** | Folder `vaults/<username>/` per user — kumpulan file Note yang valid sebagai Obsidian vault | Bukan model DB; file `.md` di `vaults/<user>/<course>/<lesson>.md` dengan frontmatter `title/course/lesson/created/updated/tags`; tanpa `.obsidian/` — lihat ADR 0001. |
| **Frontmatter** | Blok YAML di awal file Note (`--- ... ---`) dengan `title, course, lesson, created, updated, tags` | Ditulis/dibaca via `python-frontmatter`. |

## Model Ringkas

```
User (auth) ──< Note >── Lesson ──< Course
                   (vault_path → file di Vault)
```

- **Course**: `title, slug (unique), description, created_at, updated_at`
- **Lesson**: `course FK, title, slug, order, content_md, youtube_url, created_at, updated_at`
- **Note**: `user FK, lesson FK, vault_path, created_at, updated_at` — tanpa `content` TextField (file = source of truth)
- **Tags**: di frontmatter file saja, tanpa model Tag terpisah

## Aturan

- Tanpa Enrollment — semua user login bisa akses semua Course/Lesson (PoC 3–5 user).
- Satu Note per `(user, lesson)` — tidak ada banyak catatan per lesson untuk PoC.
- Vault I/O: `pathlib` + `python-frontmatter` + `os.replace` atomik + `filelock`; sanitasi slug + traversal guard — lihat `docs/research-editor-vault.md` §2 dan ADR 0001.
- Rendering markdown: `markdown-it-py` + `nh3` (jangan `bleach`) — lihat `docs/research-editor-vault.md` §3.
- Editor: CodeMirror 6 (EasyMDE fallback) — lihat `docs/research-editor-vault.md` §1.

## Referensi

- ADR 0001 — Vault Layout: `docs/adr/0001-vault-layout-per-user.md`
- ADR 0002 — Model Domain: `docs/adr/0002-model-domain.md`
- Research Editor & Vault I/O: `docs/research-editor-vault.md`

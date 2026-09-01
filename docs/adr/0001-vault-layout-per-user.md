# ADR 0001 — Struktur Vault & Penyimpanan File .md per User

Tanggal: 2026-09-01
Status: Accepted
Tiket: [#2 — 01 Struktur Vault & Penyimpanan File .md per User](https://github.com/amaldevice/E-Learning-Obsidian-PoC/issues/2)

## Konteks

PoC butuh catatan belajar markdown yang ter-embed di halaman Lesson dan disimpan sebagai vault Obsidian per user (`vaults/<username>/`) yang bisa di-zip dan dibuka di Obsidian desktop. Keputusan ini memblokir model domain (Tiket #4) dan editor embed (Tiket #3).

Research [#6](https://github.com/amaldevice/E-Learning-Obsidian-PoC/issues/6) merekomendasikan `pathlib` + `python-frontmatter` + `os.replace` atomik + `nh3` dan CodeMirror 6.

## Keputusan

1. **Path & penamaan:** `vaults/<username>/<course-slug>/<lesson-slug>.md`
   - Contoh: `vaults/alice/python-dasar/lesson-01-intro.md`
   - Tree contoh:
     ```
     vaults/
       alice/
         python-dasar/
           lesson-01-intro.md
           lesson-02-variabel.md
         web-dasar/
           lesson-01-html.md
       budi/
         python-dasar/
           lesson-01-intro.md
     ```
   - Slug disanitasi: `SAFE_SLUG = re.compile(r"[^a-z0-9_-]+")`, lowercase, `strip("-")`, fallback `untitled`. Cegah traversal: `assert VAULT_ROOT in p.resolve().parents`.
   - Trade-off: rename course/lesson = rename file/folder (acceptable untuk PoC; stabilitas UUID tidak sepadan dengan hilangnya readability di Obsidian).

2. **Kardinalitas:** Satu catatan per `(user, lesson)` — `unique_together (user, lesson)`.
   - UX: buka lesson → langsung edit satu file itu (tidak ada daftar catatan per lesson).
   - Banyak catatan per lesson ditunda (butuh UI penamaan + listing, out of scope PoC).

3. **Frontmatter YAML minimal (Obsidian-compatible):**
   ```yaml
   ---
   title: "Intro Python"
   course: "python-dasar"
   lesson: "lesson-01-intro"
   created: 2026-09-01T10:00:00+07:00
   updated: 2026-09-01T10:30:00+07:00
   tags: [python, dasar]
   ---
   ```
   - Field: `title`, `course`, `lesson`, `created`, `updated`, `tags`. Tidak perlu `lesson_id` numerik untuk PoC.
   - Ditulis/dibaca via `python-frontmatter` (`frontmatter.load` / `frontmatter.Post` + `frontmatter.dumps`).

4. **Source of truth:** File `.md` adalah source of truth; DB `Note` hanya metadata.
   - `Note` simpan: `user FK`, `lesson FK`, `vault_path` (relatif `vaults/...`), `updated_at` (untuk optimistic locking / index). Tidak duplikat `content` di `TextField`.
   - I/O: `pathlib` langsung (bukan `default_storage`), tulis atomik `tmp → os.replace`, `utf-8` selalu, `filelock` untuk konkuren multi-process. Lihat `docs/research-editor-vault.md` §2 untuk snippet `vault_path()` / `write_note_atomic()`.

5. **Folder `.obsidian/`:** Tidak dibuat. Kumpulan `.md` polos sudah valid vault Obsidian; `.obsidian/` hanya untuk settings/plugins, tidak perlu untuk PoC.

6. **Isolasi & keamanan:** View catatan hanya melayani `vaults/<request.user.username>/`; sanitasi slug + traversal guard di atas; tidak ada akses silang user.

## Konsekuensi

- Model `Note` (Tiket #4) harus enforce `unique_together (user, lesson)` dan simpan `vault_path`.
- Editor (Tiket #3) cukup load/save satu file per lesson per user.
- Export vault `.zip` (fog) kini specifiable: zip `vaults/<user>/` langsung valid di Obsidian.
- Jika rename slug diperlukan nanti, migrasi = `os.rename` file/folder + update `Note.vault_path`.

## Alternatif yang dipertimbangkan

- Flat `vaults/<user>/<lesson>.md` — ditolak, berantakan saat banyak course.
- UUID `vaults/<user>/<id>.md` — ditolak, tidak readable di Obsidian.
- Duplikat DB+file — ditolak, risiko drift.

# ADR 0003 — Editor Ter-Embed di Halaman Lesson + Backlinks Panel

Tanggal: 2026-09-01
Status: Accepted
Tiket: [#3 — 02 Editor Markdown Ter-Embed di Halaman Lesson + Graph/Backlinks Panel](https://github.com/amaldevice/E-Learning-Obsidian-PoC/issues/3)
Depends on: [ADR 0001](0001-vault-layout-per-user.md), [Research Editor & Vault I/O](../research-editor-vault.md)

## Konteks

PoC butuh catatan yang ter-embed langsung di halaman Lesson — disimpan sebagai `vaults/<user>/<course>/<lesson>.md` (ADR 0001, 1 file per `(user, lesson)`). Research #6 merekomendasikan CodeMirror 6 + `markdown-it-py`+`nh3` + regex wikilink.

## Keputusan

1. **Layout:** Split view — materi kiri, editor kanan.
   - Kiri: `Lesson.content_md` dirender server (`markdown-it-py` + `nh3`) + YouTube iframe (`Lesson.youtube_url`, disembunyikan jika kosong) + navigasi Prev/Next (`order`).
   - Kanan: editor + preview + actions + backlinks (stack vertikal).
   - Responsive: `<900px` stack vertikal (materi atas, editor bawah).
   - Alternatif tab/sidebar ditolak — split paling natural untuk "catatan sambil belajar".

2. **Editor:** CodeMirror 6 (primary), EasyMDE fallback.
   - CM6 via ESM CDN (`esm.sh`/`cdnjs`) atau vendored static, tanpa build SPA. `@codemirror/lang-markdown` untuk markdown.
   - Wikilink `[[...]]` & `#tag` highlight via custom CM6 Extension/Decoration (~30 LOC) — lihat research §1 & §4.
   - Preview bukan built-in editor — render via server (`markdown-it-py html:false → nh3.clean → |safe`) di tab Preview.

3. **Fitur editor PoC:** Ketik markdown + preview tab + Save + wikilink/#tag highlight.
   - Tanpa toolbar formatting untuk PoC (bisa tambah pasca-PoC).
   - Tab Edit/Preview di panel kanan; highlight demo `[[wikilink]]` (ungu) & `#tag` (hijau).

4. **Graph/Backlinks:** Backlinks panel saja untuk PoC — tanpa graph visual.
   - Panel "Backlinks" di bawah editor: daftar catatan lain yang link ke lesson ini.
   - Sumber: scan `vaults/<user>/**/*.md` on-demand via regex wikilink `(!?)\[\[([^|\]#]+)(?:#([^|\]]+))?(?:\|([^\]]+))?\]\]` + `TAG_RE` (research §4), strip frontmatter/code block dulu.
   - Graph force-directed (vis-network/D3) ditunda — tambah JS & kompleksitas, tidak perlu untuk PoC minimal.

5. **Save:** Tombol Save eksplisit + autosave 30s sebagai safety.
   - Save: `fetch(saveUrl, {method:"POST", body: view.state.doc.toString()})` + CSRF.
   - Autosave: `setInterval(..., 30000)` — safety net, tidak ganti tombol Save.
   - Feedback: toast "Tersimpan ✓" + timestamp `updated` (frontmatter + `Note.updated_at`).

## Prototype

- File: `docs/prototype/lesson.html` (static, tanpa backend) — split view, tab Edit/Preview, highlight demo, backlinks list, toast, responsive.
- Commit: lihat `docs/prototype/lesson.html` di repo.

## Konsekuensi

- View Lesson: `GET /courses/<course>/lessons/<lesson>/` — load materi + load/create file vault + render backlinks.
- POST save: tulis via `vault_path()` + `write_note_atomic()` (ADR 0001) + update `Note` metadata.
- Tidak ada endpoint graph JSON untuk PoC — hanya backlinks list.

## Alternatif yang dipertimbangkan

- Tab Materi|Catatan|Preview — ditolak, tidak bisa lihat materi & catatan bersamaan.
- EasyMDE saja — fallback valid jika butuh 1-hari, tapi CM6 lebih future-proof.
- Backlinks + graph vis-network — ditunda untuk PoC.

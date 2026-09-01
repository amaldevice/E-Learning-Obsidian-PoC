# Research: Pilihan Editor Markdown & Vault I/O — Ticket 05

> Tanggal: 2026-09-01 · Untuk Tiket 01 & 02 · Stack PoC: Django templates + JS ringan, `vaults/<user>/`, SQLite

## 1. Editor Markdown untuk Django Templates (tanpa SPA)

### Tabel Perbandingan

| Kriteria | **CodeMirror 6** | **EasyMDE** (fork SimpleMDE) | **Toast UI Editor** | **CodeMirror 5** |
|---|---|---|---|---|
| **Bundle size** | Modular tree-shakable. Core `@codemirror/view` ~77 kB min+gzip; setup markdown minimal ~150–200 kB total (tergantung extension) | ~250–280 kB minified (bundel CM5 di dalam) | ~496 kB (v3, ProseMirror) — paling besar | ~200 kB+ (legacy bundle, tidak tree-shakable) |
| **Markdown preview** | Tidak built-in — render terpisah via `markdown-it-py`/`marked` di JS atau server | Built-in: preview, side-by-side, fullscreen (pakai `markdown` internal) | Built-in dual mode: Markdown + WYSIWYG, preview sinkron | Tidak built-in |
| **Wikilink `[[` / `#tag` highlight** | Sangat fleksibel — custom `Extension`/`Decoration` untuk highlight & autocomplete (perlu tulis ~30 LOC) | Bisa via CodeMirror mode overlay, tapi API CM5 terbatas | Sulit — harus plugin ProseMirror kustom | Sama seperti EasyMDE (overlay) |
| **Autosave** | Tidak built-in — `setInterval` + `fetch` POST mudah ditambah | Built-in `autosave` ke `localStorage` (opsi `autosave: {enabled:true}`) | Tidak built-in autosave ke server | Tidak built-in |
| **Lisensi** | MIT | MIT | MIT | MIT |
| **Maintenance (2026)** | **Aktif** — rewrite TS/ESM oleh Marijn Haverbeke, rilis berkelanjutan 2025–2026 | **Aktif** — EasyMDE 2.21.0 Mei 2026; SimpleMDE asli deprecated sejak 2016 | **Tidak maintained** — rilis terakhir Feb 2023, issue #3297 komunitas sarankan hindari untuk proyek baru | **Legacy / low maintenance** — hanya bug-fix signifikan, tidak ada fitur baru |
| **Cocok untuk Django template?** | Ya — ES module via CDN/bundler ringan, tanpa asumsi SPA | Ya — drop-in paling mudah (`new EasyMDE(textarea)`) | Kurang — berat, asumsi bundler modern, risiko sekuriti tanpa patch | Bisa tapi utang teknis |

**Sumber:** CodeMirror 6 status & MIT — [codemirror.net](https://codemirror.net) · [@codemirror/view di bundlephobia](https://bundlephobia.com/package/@codemirror/view) · [npm codemirror](https://www.npmjs.com/package/codemirror) · [discuss.codemirror.net — CM6 status](https://discuss.codemirror.net/t/codemirror-6-status-update/2792) · EasyMDE size/maintenance — [npm easymde](https://www.npmjs.com/package/easymde) · [github Ionaru/easymde](https://github.com/Ionaru/easymde) · Toast UI stalled — [tui.editor #3297](https://github.com/nhn/tui.editor/issues/3297) · [@toast-ui/editor versions](https://www.npmjs.com/package/@toast-ui/editor?activeTab=versions) · CM5 maintenance — [discuss.codemirror.net — CM5 maintenance](https://discuss.codemirror.net/t/how-long-do-you-plan-to-maintain-codemirror-v5/5594)

### Rekomendasi Editor: **CodeMirror 6** (primary) — EasyMDE sebagai fallback

**Pilih CodeMirror 6** untuk PoC karena:
- Satu-satunya yang **aktif + modular + ringan** — bayar hanya fitur yang dipakai, ideal untuk `textarea → CM6` di Django template tanpa SPA.
- Wikilink/tag highlight & autocomplete bisa ditambah sebagai extension kecil (lebih future-proof daripada overlay CM5).
- Preview ditangani server-side (lihat §3) atau `markdown-it` JS ringan untuk live preview — tidak perlu editor yang bundel preview berat.
- MIT, aksesibilitas & mobile support terbaik.

**Kapan pakai EasyMDE:** Jika ingin PoC 1-hari tanpa tulis extension — `EasyMDE` adalah jalan pintas valid (preview + autosave gratis). Trade-off: bundel lebih besar, utang CM5, kustomisasi wikilink terbatas. **Hindari Toast UI & CM5 baru** — Toast UI unmaintained & paling berat; CM5 hanya untuk legacy.

> Implementasi minimal CM6 di Django template: `<textarea>` + `import {EditorView, basicSetup} from "codemirror"` + `@codemirror/lang-markdown` via CDN ESM (esm.sh/cdnjs) atau vendored static — tanpa build step SPA. Autosave: `setInterval(() => fetch(saveUrl, {method:"POST", body: view.state.doc.toString()}), 30000)` + tombol Save eksplisit.

---

## 2. Django I/O untuk `vaults/<user>/*.md`

### `pathlib` vs `default_storage`

| Pendekatan | Kegunaan | Kelebihan PoC | Kekurangan |
|---|---|---|---|
| **`pathlib.Path` + `open()` langsung** | Manipulasi path lokal, baca/tulis file vault | Sederhana, eksplisit, cocok untuk `vaults/` di filesystem lokal; `BASE_DIR / "vaults" / username / slug` readable | Tidak abstrak ke S3/GCS; harus handle sanitasi & atomic write sendiri |
| **`default_storage` / `FileSystemStorage`** | Abstraksi storage Django (lokal ↔ S3 via `django-storages`) | Portabel ke cloud tanpa ubah logic; sanitasi path bawaan | Overkill untuk PoC lokal; API (`storage.save/open`) kurang natural untuk operasi `*.md` + frontmatter |

**Rekomendasi PoC: `pathlib` langsung.** Vault adalah file lokal yang harus kompatibel Obsidian (zip-able), bukan media upload abstrak. `default_storage` baru relevan jika PoC naik ke S3 — saat itu bungkus helper `vault_path()` agar migrasi mudah.

**Sumber:** [Django Storage API vs pathlib](https://docs.djangoproject.com/en/stable/ref/files/storage/) · [pathlib docs](https://docs.python.org/3/library/pathlib.html)

### Pola aman yang direkomendasikan

```python
from pathlib import Path
from django.conf import settings
import re, os, frontmatter

VAULT_ROOT = Path(settings.BASE_DIR) / "vaults"
SAFE_SLUG = re.compile(r"[^a-z0-9_-]+")

def vault_path(username: str, course_slug: str, lesson_slug: str) -> Path:
    # sanitasi: lowercase, ganti karakter aneh, cegah traversal
    def safe(s): return SAFE_SLUG.sub("-", s.lower()).strip("-") or "untitled"
    p = VAULT_ROOT / safe(username) / safe(course_slug) / f"{safe(lesson_slug)}.md"
    # guard traversal
    assert VAULT_ROOT in p.resolve().parents or p.resolve() == VAULT_ROOT
    return p

def read_note(path: Path):
    post = frontmatter.load(path)  # YAML frontmatter + content
    return post.metadata, post.content

def write_note_atomic(path: Path, metadata: dict, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(content, **metadata)
    tmp = path.with_suffix(".md.tmp")
    tmp.write_text(frontmatter.dumps(post), encoding="utf-8")
    os.replace(tmp, path)  # atomic di POSIX
```

- **Encoding:** Selalu `utf-8`.
- **Concurrency:** `os.replace(tmp, path)` atomik — pembaca tidak pernah lihat setengah tulis. Untuk read-modify-write konkuren (dua tab save bersamaan) tambah `filelock`:
  ```python
  from filelock import FileLock
  with FileLock(str(path) + ".lock"):
      write_note_atomic(path, meta, content)
  ```
  `threading.Lock` tidak cukup untuk multi-process (Gunicorn). Alternatif: simpan `updated_at` di frontmatter/DB dan tolak save jika stale (optimistic locking).
- **Frontmatter:** Pakai `python-frontmatter` (`pip install python-frontmatter`) — parse/dump YAML/JSON/TOML frontmatter, API `load`/`dumps`/`Post`. Stabil & kecil; alternatif manual `yaml.safe_load` split `---` rawan edge case. **Sumber:** [pypi python-frontmatter](https://pypi.org/project/python-frontmatter/) · [github eyeseast/python-frontmatter](https://github.com/eyeseast/python-frontmatter) · [filelock pypi](https://pypi.org/project/filelock/)

---

## 3. Markdown → HTML yang Aman (Sanitasi XSS)

| Stack | Parser | Sanitizer | Catatan 2026 |
|---|---|---|---|
| **`markdown` + `bleach`** | `Python-Markdown` (extensible, tidak strict CommonMark) | `bleach` whitelist-based | **Jangan pakai `bleach` baru** — deprecated Jan 2023, rilis final 6.4.0 Jun 2026, tanpa patch sekuriti lagi (bergantung `html5lib` unmaintained) |
| **`markdown`/`markdown-it-py` + `nh3`** | `markdown-it-py` (100% CommonMark, port JS `markdown-it`) atau `Python-Markdown` | `nh3` (binding Rust Ammonia) ~20× lebih cepat, actively maintained | **Rekomendasi** — `nh3.clean(html)` sebagai drop-in `bleach` |
| **`mistune`** | `mistune` (pure-Python, cepat, **tidak** CommonMark) | Harus sanitasi terpisah juga | Cepat tapi ada CVE XSS 2026 (59929, 44896), perilaku edge case mengejutkan |

**Aturan emas:** Sanitise **HTML output**, bukan markdown source. Markdown bisa sembunyikan HTML di blockquote/image.

```python
from markdown_it import MarkdownIt
import nh3

md = MarkdownIt("commonmark", {"html": False})  # tolak raw HTML di parser
# atau MarkdownIt("js-default") untuk preset aman
html = md.render(untrusted_markdown)
safe_html = nh3.clean(html, tags={"p","a","h1","h2","h3","ul","ol","li","code","pre","blockquote","em","strong","hr","br"}, attributes={"a": {"href"}})
# di template: {{ safe_html|safe }} — hanya setelah nh3.clean
```

Jika tetap pakai `Python-Markdown`: `markdown.markdown(text, extensions=["extra","codehilite"])` lalu `nh3.clean`.

**Sumber:** [bleach deprecated — readthedocs](https://bleach.readthedocs.io/) · [bleach 6.4.0 final — bluesock.org](https://bluesock.org/~willkg/blog/dev/bleach_6_4_0_final_release.html) · [nh3 pypi](https://pypi.org/project/nh3/) · [Django + nh3 — adamj.eu](https://adamj.eu/tech/2023/12/13/django-sanitize-incoming-html-nh3/) · [markdown-it-py](https://github.com/executablebooks/markdown-it-py) · [mistune](https://github.com/lepture/mistune)

### Rekomendasi: **`markdown-it-py` + `nh3`** (alternatif: `Python-Markdown` + `nh3`)

Pilih `markdown-it-py` jika ingin CommonMark strict + ekosistem plugin (`mdit-py-plugins` untuk frontmatter/tasklist/footnote). `Python-Markdown` juga valid jika tim sudah familiar — yang penting **sanitizer-nya `nh3`, bukan `bleach`**.

---

## 4. Parsing Wikilinks `[[...]]` & `#tag` untuk Backlinks/Graph

**Regex cukup untuk PoC** — tidak perlu library.

```python
import re

# Wikilink: [[target]], [[target#heading]], [[target|alias]], ![[embed]]
WIKILINK_RE = re.compile(r'(!?)\[\[([^|\]#]+)(?:#([^|\]]+))?(?:\|([^\]]+))?\]\]')

# Tag: #tag, #tag/subtag — hindari # di heading markdown & URL fragment
# Abaikan code block & frontmatter dulu (strip sebelum scan)
TAG_RE = re.compile(r'(?<![\w/])#([a-zA-Z0-9/_-]+)')

def extract_links(text: str):
    # strip frontmatter + fenced code agar tidak false positive
    text = re.sub(r'^---\n.*?\n---\n', '', text, flags=re.DOTALL)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`[^`]*`', '', text)
    links = [(m.group(2).strip(), m.group(3), m.group(4), bool(m.group(1)))
             for m in WIKILINK_RE.finditer(text)]
    tags = TAG_RE.findall(text)
    return links, tags
```

- **Backlinks:** Saat save, scan semua `vaults/<user>/**/*.md`, bangun index `target → [source files]`. Untuk PoC cukup scan on-demand atau cache di DB (`Note.links_to` JSON).
- **Graph:** Dari index yang sama, emit nodes/edges JSON untuk `vis-network`/`D3` force-directed (scope opsional — backlinks panel saja sudah cukup wow-factor PoC).
- **Kapan butuh parser full:** Jika perlu handle `[[path/to/note]]` dengan `|` di tabel atau nested `[[...[[...]]...]]` — regex gagal. Saat itu pakai plugin `markdown-it-py` kustom atau `remark-wiki-link`.

**Sumber pola regex:** Komunitas Obsidian & plugin Regex Pipeline — pola `(!?)\[\[([^|\]#]+)(?:#([^|\]]+))?(?:\|([^\]]+))?\]\]` adalah konsensus.

---

## 5. Rekomendasi Stack PoC (1 Editor + 1 Vault Stack)

### Editor: **CodeMirror 6** (+ fallback EasyMDE jika butuh cepat)

### Vault/Markdown Stack:
- **I/O:** `pathlib` + `python-frontmatter` + atomic `os.replace` (+ `filelock` jika perlu) — `VAULT_ROOT = BASE_DIR / "vaults"`
- **Render:** `markdown-it-py` (CommonMark, `html: False`) → `nh3.clean` → `|safe` di Django template
- **Wikilink/tag:** Regex di atas, index backlinks sederhana per user

### Dependensi `requirements.txt` minimal

```
markdown-it-py>=3.0
mdit-py-plugins  # opsional: frontmatter, tasklists
nh3>=0.2
python-frontmatter>=1.0
filelock>=3.0    # opsional untuk concurrency
```

### Contoh file vault (Obsidian-compatible)

```markdown
---
title: "Intro to Python"
course: "python-dasar"
lesson: "lesson-01"
created: 2026-09-01T10:00:00+07:00
tags: [python, dasar]
---

# Intro to Python

Catatan untuk [[python-dasar/lesson-02|Lesson 2]] dan #python.

Lihat juga [[lesson-02]].
```

Tree: `vaults/alice/python-dasar/lesson-01.md` — langsung valid vault Obsidian tanpa `.obsidian/` (cukup kumpulan `.md` polos).

---

## Sumber Utama

- CodeMirror 6 — https://codemirror.net · https://github.com/codemirror/dev · https://www.npmjs.com/package/codemirror
- EasyMDE — https://github.com/Ionaru/easymde · https://www.npmjs.com/package/easymde
- Toast UI — https://github.com/nhn/tui.editor · https://www.npmjs.com/package/@toast-ui/editor
- CM5 maintenance — https://discuss.codemirror.net/t/how-long-do-you-plan-to-maintain-codemirror-v5/5594
- Bleach EOL — https://bleach.readthedocs.io/ · https://bluesock.org/~willkg/blog/dev/bleach_6_4_0_final_release.html
- nh3 — https://pypi.org/project/nh3/ · https://github.com/messense/nh3
- markdown-it-py — https://github.com/executablebooks/markdown-it-py
- mistune — https://github.com/lepture/mistune
- python-frontmatter — https://pypi.org/project/python-frontmatter/ · https://github.com/eyeseast/python-frontmatter
- filelock — https://pypi.org/project/filelock/
- Django Storage — https://docs.djangoproject.com/en/stable/ref/files/storage/

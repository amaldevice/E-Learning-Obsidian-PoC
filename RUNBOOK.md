# RUNBOOK — E-Learning Obsidian PoC (Lokal)

Langkah demi langkah untuk menjalankan dan menguji aplikasi di lokal (macOS/Linux, Python 3.12).

## 1. Prasyarat

- **uv** terinstall: https://docs.astral.sh/uv/ (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Python 3.12 (uv akan mengunduh otomatis jika belum ada)
- Git

## 2. Clone & Install

```bash
git clone https://github.com/amaldevice/E-Learning-Obsidian-PoC.git
cd E-Learning-Obsidian-PoC
# Jika repo ini adalah folder PoC/ di zenithera-research, langsung:
# cd /path/to/PoC

uv sync
```

## 3. Migrasi & Seed

```bash
uv run python manage.py migrate
uv run python manage.py seed_poc
```

Output yang diharapkan:

```
Created user: alice
Created user: budi
Created user: citra
Created user: dewi
Created user: admin
Created course: python-dasar
  Created lesson: pengenalan-python
  ...
Seed selesai. Login: alice/budi/citra/dewi/admin — password: poc12345
```

Idempoten — aman dijalankan berulang. Untuk reset bersih:

```bash
uv run python manage.py seed_poc --reset
```

`--reset` menghapus Course/Lesson/User seed + `vaults/<user>/` di disk, lalu membuat ulang.

## 3b. Seed Demo Notes (opsional)

```bash
uv run python manage.py seed_demo_notes
```

Mengisi 1 catatan per (siswa, lesson) — 4 siswa × 7 lesson = 28 notes — dengan
`[[wikilink]]` antar lesson dan antar course plus `#tag`, untuk mendemokan
Backlinks, panduan mencatat, dan toggle sidebar. Idempoten (aman diulang;
`created` dipertahankan). `--reset` menghapus vault seed users dulu.

## 4. Jalankan Server

```bash
uv run python manage.py runserver
# atau port custom:
uv run python manage.py runserver 127.0.0.1:8765
```

Buka http://127.0.0.1:8000/ — redirect ke `/courses/` (login required).

## 5. Akun Demo

| Username | Password   | Role      |
|----------|------------|-----------|
| alice    | poc12345   | siswa     |
| budi     | poc12345   | siswa     |
| citra    | poc12345   | siswa     |
| dewi     | poc12345   | siswa     |
| admin    | poc12345   | superuser |

Admin panel: http://127.0.0.1:8000/admin/

## 6. Uji Manual (5 Langkah)

1. **Login** sebagai `alice` → buka **Course** → **Lesson** (mis. `Python Dasar` → `Pengenalan Python`) — cek materi, video YouTube embed, Prev/Next.
2. **Catatan**: di panel kanan lesson, ketik markdown (mis. `# Catatan\nHello #python [[variabel-tipe-data]]`) → klik **Save** (atau tunggu autosave 30s) → reload → catatan masih ada, badge `Terakhir: ...` muncul.
3. **Isolasi**: logout → login sebagai `budi` → buka lesson yang sama → catatan `alice` tidak terlihat → `budi` bisa buat catatan terpisah.
4. **Backlinks**: di `fungsi` buat catatan `Link to [[pengenalan-python]]` → buka `pengenalan-python` → panel **Backlinks** menampilkan `fungsi`.
5. **Vault**: header → **Vault** (`/vault/`) → daftar catatan → **Download .zip** (`/vault/download`) → buka zip di Obsidian desktop (struktur `course/lesson.md` + frontmatter valid).

## 7. Uji Otomatis

```bash
# Full suite (56 tests, ~20 detik)
uv run python manage.py test courses --verbosity=2

# Single file / single test
uv run python manage.py test courses.tests.CourseLessonTests --verbosity=2
uv run python manage.py test courses.tests.VaultHelperTests.test_tags_extracted_on_save --verbosity=2

# Django check
uv run python manage.py check

# Lint (opsional)
uv run ruff check courses/
```

## 8. E2E via Script (Tanpa Browser)

Server harus jalan di `127.0.0.1:8765`:

```bash
# Terminal 1
uv run python manage.py runserver 127.0.0.1:8765

# Terminal 2 — jalankan skrip E2E (urllib, tanpa browser)
# Contoh ada di commit history / bisa copy dari RUNBOOK ini
python3 - <<'PY'
import http.cookiejar, urllib.request, urllib.parse, re, json, pathlib, zipfile, io
BASE="http://127.0.0.1:8765"
def make_opener():
    cj=http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj)),cj
def get(opener, path):
    req=urllib.request.Request(BASE+path)
    with opener.open(req) as r: return r.read().decode()
def post(opener, path, data):
    body=urllib.parse.urlencode(data).encode()
    req=urllib.request.Request(BASE+path, data=body)
    with opener.open(req) as r: return r.read().decode()
def extract_csrf(html):
    import re; m=re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
    return m.group(1) if m else ""
opener,cj=make_opener()
html=get(opener,"/accounts/login/")
csrf=extract_csrf(html)
post(opener,"/accounts/login/",{"username":"alice","password":"poc12345","csrfmiddlewaretoken":csrf,"next":""})
html=get(opener,"/courses/")
assert "Python Dasar" in html
print("E2E OK: login + course list")
PY
```

Untuk E2E browser (opsional): gunakan `playwright-cli` atau `agent-browser` dengan `obscura serve` (lihat skill `obscura`).

## 9. Vault di Disk

- Lokasi: `vaults/<username>/<course>/<lesson>.md`
- Frontmatter: `title, course, lesson, created, updated, tags` (array)
- File = source of truth, DB `Note` hanya metadata (`vaults/...` relatif)
- Tanpa folder `.obsidian/` — kumpulan `.md` polos sudah valid vault Obsidian
- Lihat langsung: `cat vaults/alice/python-dasar/pengenalan-python.md`

## 10. Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `No module named 'courses'` saat `startapp` | Hapus folder `courses/` kosong lalu `uv run python manage.py startapp courses` |
| `DisallowedHost: testserver` | Normal di test, tidak di runserver. Jika di runserver, set `ALLOWED_HOSTS = ["*"]` di `config/settings.py` (dev only) |
| Port 8000 dipakai | `uv run python manage.py runserver 127.0.0.1:8765` |
| Vault tidak muncul setelah save | Cek `vaults/` ada, `uv run python manage.py check`, lihat `courses/vault.py` |
| Preview tidak render | Pastikan `markdown-it-py` + `nh3` terinstall (`uv sync`) |

## 11. Struktur Penting

```
PoC/
├── config/           # Django settings, urls
├── courses/          # App: models, views, vault.py, backlinks.py, management/commands/seed_poc.py
├── templates/        # base.html, courses/*, vault/*, registration/login.html
├── vaults/           # (gitignored) file .md per user
├── docs/adr/         # ADR 0001-0003
├── CONTEXT.md        # Glossary
└── README.md         # Ringkas
```

## 12. Hentikan Server

`Ctrl+C` di terminal runserver, atau:

```bash
pkill -f "manage.py runserver"
```

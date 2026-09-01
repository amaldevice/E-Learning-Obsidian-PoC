# ADR 0002 — Model Domain Course / Lesson / Note & Relasi ke User

Tanggal: 2026-09-01
Status: Accepted
Tiket: [#4 — 03 Model Domain Course / Lesson / Note & Relasi ke User](https://github.com/amaldevice/E-Learning-Obsidian-PoC/issues/4)
Depends on: [ADR 0001 — Vault Layout](0001-vault-layout-per-user.md)

## Konteks

PoC butuh model Django untuk E-Learning (Course → Lesson) + catatan belajar per user yang disimpan sebagai file vault (ADR 0001: `vaults/<user>/<course>/<lesson>.md`, 1 file per `(user, lesson)`, file=source of truth). Keputusan ini memblokir Tiket #5 (Auth & Seed).

## Keputusan

### 1. Enrollment: Tidak ada — akses terbuka

Semua user yang login bisa membuka semua Course/Lesson dan menulis catatan. Tanpa model `Enrollment`. Alasan: PoC 3–5 user uji, tidak perlu gate. Enrollment (M2M User–Course) bisa ditambah nanti tanpa migrasi berat.

### 2. Entitas & Relasi

```
User (django.contrib.auth) ──< Note >── Lesson ──< Course
                              (FK user, FK lesson)
```

- **Course**: kumpulan Lesson.
- **Lesson**: unit materi (teks markdown + opsional YouTube embed), FK ke Course, berurutan.
- **Note**: catatan belajar per user per lesson — 1 baris per `(user, lesson)`, FK ke keduanya, metadata vault.
- **Vault**: bukan model DB — folder `vaults/<username>/` di filesystem (ADR 0001).

### 3. Field per Model

**Course**
| Field | Type | Keterangan |
|-------|------|------------|
| `title` | CharField(200) | Nama course |
| `slug` | SlugField(unique) | URL, mis. `python-dasar` |
| `description` | TextField(blank) | Deskripsi singkat |
| `created_at` | DateTimeField(auto_now_add) | |
| `updated_at` | DateTimeField(auto_now) | |

**Lesson**
| Field | Type | Keterangan |
|-------|------|------------|
| `course` | FK(Course, related_name=lessons, CASCADE) | |
| `title` | CharField(200) | |
| `slug` | SlugField | Unik per course (`unique_together (course, slug)`) |
| `order` | PositiveIntegerField(default=0) | Urutan dalam course, `ordering = ["order", "id"]` |
| `content_md` | TextField(blank) | Materi teks markdown |
| `youtube_url` | URLField(blank) | Opsional, embed iframe |
| `created_at` | DateTimeField(auto_now_add) | |
| `updated_at` | DateTimeField(auto_now) | |

**Note** (metadata saja — konten di file)
| Field | Type | Keterangan |
|-------|------|------------|
| `user` | FK(User, CASCADE) | Pemilik catatan |
| `lesson` | FK(Lesson, CASCADE) | Lesson yang dicatat |
| `vault_path` | CharField(500) | Relatif, mis. `vaults/alice/python-dasar/lesson-01.md` |
| `created_at` | DateTimeField(auto_now_add) | |
| `updated_at` | DateTimeField(auto_now) | Untuk optimistic locking / index |

Constraints:
- `Note: unique_together (user, lesson)` — satu catatan per user per lesson (konsisten ADR 0001).
- `Lesson: unique_together (course, slug)` + `ordering ["order"]`.

### 4. Tags

Tidak ada model `Tag` terpisah. Tags disimpan sebagai list di frontmatter file (`tags: [python, dasar]`) — lihat ADR 0001. Query tags via scan file atau index sederhana; M2M Tag ditunda (overkill PoC).

### 5. Ubiquitous Language

| Istilah | Arti |
|---------|------|
| **Course** | Kumpulan Lesson (mis. "Python Dasar") |
| **Lesson** | Unit materi: teks markdown + opsional video YouTube |
| **Note** | Catatan belajar: 1 file markdown per user per lesson di Vault |
| **Vault** | Folder `vaults/<username>/` per user — kumpulan file Note yang valid sebagai Obsidian vault |

Dipakai konsisten di code (`models.py`), `CONTEXT.md` glossary, dan ADR.

### 6. Contoh `models.py` (sketsa)

```python
class Course(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200)
    slug = models.SlugField()
    order = models.PositiveIntegerField(default=0)
    content_md = models.TextField(blank=True)
    youtube_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = [("course", "slug")]
        ordering = ["order", "id"]

class Note(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    vault_path = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = [("user", "lesson")]
```

Vault I/O tetap via `pathlib` + `python-frontmatter` + `os.replace` atomik (ADR 0001, `docs/research-editor-vault.md` §2).

## Konsekuensi

- Tiket #5 (Auth & Seed) kini unblocked — seed 3–5 user + 1–2 Course dengan 3–5 Lesson tiap course bisa dibuat via fixtures/management command.
- Tiket #3 (Editor) konsisten: load/save satu file per lesson per user, tanpa daftar catatan per lesson.
- Fog "Pencarian & organisasi catatan" dan "Enrollment & navigasi" kini terjawab — tidak perlu tiket tambahan untuk PoC minimal; pencarian lintas catatan bisa jadi enhancement pasca-PoC.

## Alternatif yang dipertimbangkan

- Enrollment eksplisit (M2M) — ditolak untuk PoC, tambah model/view/UX tanpa nilai demo.
- Banyak Note per (user, lesson) — ditolak, butuh UI penamaan/listing (scope lebih besar, konsisten ADR 0001).
- Model Tag M2M — ditolak, tags di frontmatter cukup untuk PoC.

"""Seed demo notes: 1 note per (student, lesson) with wikilinks across courses.

Usage: uv run python manage.py seed_demo_notes [--reset]

Idempotent: overwrites note content for seed users, preserves created timestamps.
--reset: delete seed users' vault dirs first (same as seed_poc --reset scope).

Personas (each links differently so backlinks/tags demo well):
- alice: the connector — links within python-dasar + across to web-dasar.
- budi: python-focused — chains python-dasar lessons forward.
- citra: web-focused — chains web-dasar lessons + one link back to python-dasar.
- dewi: the tagger — sparse links, rich #tags per topic.
"""
import shutil
from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from courses.models import Course, Lesson, Note
from courses.vault import (
    _safe,
    read_note,
    vault_path,
    vault_rel_path,
    write_note_atomic,
)
from courses.views import _extract_tags

User = get_user_model()

STUDENTS = ["alice", "budi", "citra", "dewi"]

# (course_slug, lesson_slug) -> {student: content}
NOTES: dict[tuple[str, str], dict[str, str]] = {
    ("python-dasar", "pengenalan-python"): {
        "alice": (
            "# Pengenalan Python\n\n"
            "Python itu bahasa yang bersih dan mudah dibaca.\n\n"
            "Rencana belajar: [[variabel-tipe-data]] lalu [[fungsi|Fungsi]], "
            "dan nanti bandingkan dengan [[web-dasar/js-dasar|JavaScript]].\n\n"
            "#python #pemula"
        ),
        "budi": (
            "# Pengenalan Python\n\n"
            "Mulai dari sini. Target minggu ini: [[variabel-tipe-data]].\n\n"
            "#python"
        ),
        "citra": (
            "# Pengenalan Python\n\n"
            "Mampir dari Web Dasar — ingin tahu Python sebelum "
            "[[web-dasar/js-dasar|belajar JS]].\n\n"
            "#python #web"
        ),
        "dewi": (
            "# Pengenalan Python\n\n"
            "Catatan ringkas: sintaks bersih, banyak library, cocok untuk pemula.\n\n"
            "#python #pemula #ringkasan"
        ),
    },
    ("python-dasar", "variabel-tipe-data"): {
        "alice": (
            "# Variabel dan Tipe Data\n\n"
            "`int`, `str`, `list`, `dict` — mirip tipe di "
            "[[web-dasar/js-dasar|JavaScript]] tapi sintaks beda.\n\n"
            "Lanjutan dari [[pengenalan-python]]. Berikutnya: [[fungsi]].\n\n"
            "#python #dasar"
        ),
        "budi": (
            "# Variabel dan Tipe Data\n\n"
            "`x = 10`, `y = \"hello\"`. Sudah paham dari [[pengenalan-python]].\n"
            "Lanjut ke [[fungsi]].\n\n"
            "#python"
        ),
        "citra": (
            "# Variabel dan Tipe Data\n\n"
            "Beda dengan `let`/`const` di [[web-dasar/js-dasar|JS]].\n\n"
            "#python #perbandingan"
        ),
        "dewi": (
            "# Variabel dan Tipe Data\n\n"
            "Ringkasan tipe: int, str, list, dict, tuple, set.\n\n"
            "#python #dasar #ringkasan"
        ),
    },
    ("python-dasar", "fungsi"): {
        "alice": (
            "# Fungsi\n\n"
            "`def sapa(nama)` — sama idenya dengan `function` di "
            "[[web-dasar/js-dasar|JavaScript]]. Lihat juga [[oop-dasar|OOP]] "
            "untuk method.\n\n"
            "#python #fungsi"
        ),
        "budi": (
            "# Fungsi\n\n"
            "Fungsi merapikan kode. Dipakai lagi di [[oop-dasar]] sebagai method.\n\n"
            "#python #fungsi"
        ),
        "citra": (
            "# Fungsi\n\n"
            "Analogi: seperti function di [[web-dasar/js-dasar|JS]].\n\n"
            "#python #fungsi"
        ),
        "dewi": (
            "# Fungsi\n\n"
            "Parameter, return value, scope. Contoh: `def sapa(nama)`.\n\n"
            "#python #fungsi #ringkasan"
        ),
    },
    ("python-dasar", "oop-dasar"): {
        "alice": (
            "# OOP Dasar\n\n"
            "Class `Kucing` — method itu [[fungsi]] di dalam class. "
            "Pola class juga ada di [[web-dasar/js-dasar|JS modern]].\n\n"
            "#python #oop"
        ),
        "budi": (
            "# OOP Dasar\n\n"
            "Puncak python-dasar. Merangkum [[pengenalan-python]], "
            "[[variabel-tipe-data]], dan [[fungsi]].\n\n"
            "#python #oop"
        ),
        "citra": (
            "# OOP Dasar\n\n"
            "Class di Python vs class di [[web-dasar/js-dasar|JS]] — mirip.\n\n"
            "#python #oop #perbandingan"
        ),
        "dewi": (
            "# OOP Dasar\n\n"
            "Class, object, __init__, self. Selesai python-dasar.\n\n"
            "#python #oop #ringkasan"
        ),
    },
    ("web-dasar", "html-dasar"): {
        "alice": (
            "# HTML Dasar\n\n"
            "Struktur halaman. Nanti dihias [[css-dasar]] dan "
            "dihidupkan [[js-dasar]].\n\n"
            "#web #html"
        ),
        "budi": (
            "# HTML Dasar\n\n"
            "Mampir dari Python — struktur `<html><body>`. Mirip konsep "
            "[[python-dasar/pengenalan-python|intro Python]]: mulai dari dasar.\n\n"
            "#web"
        ),
        "citra": (
            "# HTML Dasar\n\n"
            "Fondasi web. Lanjut [[css-dasar]] lalu [[js-dasar|JavaScript]].\n\n"
            "#web #html"
        ),
        "dewi": (
            "# HTML Dasar\n\n"
            "Tag, elemen, atribut. Struktur dokumen.\n\n"
            "#web #html #ringkasan"
        ),
    },
    ("web-dasar", "css-dasar"): {
        "alice": (
            "# CSS Dasar\n\n"
            "`body { font-family: sans-serif; }` — menghias [[html-dasar]]. "
            "Analogi: seperti formatting output di "
            "[[python-dasar/fungsi|Fungsi Python]].\n\n"
            "#web #css"
        ),
        "budi": (
            "# CSS Dasar\n\n"
            "Tampilan halaman [[html-dasar|HTML]].\n\n"
            "#web"
        ),
        "citra": (
            "# CSS Dasar\n\n"
            "Selector, properti, box model. Dari [[html-dasar]], ke [[js-dasar]].\n\n"
            "#web #css"
        ),
        "dewi": (
            "# CSS Dasar\n\n"
            "Warna, layout, responsif. Ringkas dan rapi.\n\n"
            "#web #css #ringkasan"
        ),
    },
    ("web-dasar", "js-dasar"): {
        "alice": (
            "# JavaScript Dasar\n\n"
            "`console.log` vs `print` di [[python-dasar/pengenalan-python|Python]]. "
            "Fungsi JS mirip [[python-dasar/fungsi|Fungsi Python]]. Penutup: "
            "[[html-dasar]], [[css-dasar]], [[js-dasar|JS]] satu paket web.\n\n"
            "#web #js #perbandingan"
        ),
        "budi": (
            "# JavaScript Dasar\n\n"
            "`let`/`const` vs variabel [[python-dasar/variabel-tipe-data|Python]]. "
            "Fungsi JS vs [[python-dasar/fungsi|Fungsi Python]].\n\n"
            "#web #perbandingan"
        ),
        "citra": (
            "# JavaScript Dasar\n\n"
            "Puncak web-dasar: [[html-dasar]] + [[css-dasar]] + JS. "
            "Bandingkan dengan [[python-dasar/oop-dasar|OOP Python]].\n\n"
            "#web #js"
        ),
        "dewi": (
            "# JavaScript Dasar\n\n"
            "DOM, event, fetch. Selesai web-dasar.\n\n"
            "#web #js #ringkasan"
        ),
    },
}


class Command(BaseCommand):
    help = "Seed demo notes: 4 students x 7 lessons with cross-course wikilinks. Idempotent; --reset wipes seed vaults first."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Hapus vault seed users lalu seed ulang.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            vault_root = Path(settings.BASE_DIR) / "vaults"
            for username in STUDENTS:
                user_vault = vault_root / _safe(username)
                if user_vault.exists():
                    shutil.rmtree(user_vault)
                    self.stdout.write(f"  Cleaned vault: {user_vault}")

        now = datetime.now(UTC).isoformat()
        count = 0
        for (course_slug, lesson_slug), per_student in NOTES.items():
            try:
                course = Course.objects.get(slug=course_slug)
                lesson = Lesson.objects.get(course=course, slug=lesson_slug)
            except (Course.DoesNotExist, Lesson.DoesNotExist):
                self.stderr.write(f"  SKIP (no lesson): {course_slug}/{lesson_slug}")
                continue
            for username, content in per_student.items():
                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    self.stderr.write(f"  SKIP (no user): {username}")
                    continue
                vpath = vault_path(username, course.slug, lesson.slug)
                existing_meta, _ = read_note(vpath)
                created = existing_meta.get("created", now)
                tags = _extract_tags(content)
                metadata = {
                    "title": lesson.title,
                    "course": course.slug,
                    "lesson": lesson.slug,
                    "created": created,
                    "updated": now,
                    "tags": tags,
                }
                write_note_atomic(vpath, metadata, content)
                Note.objects.update_or_create(
                    user=user,
                    lesson=lesson,
                    defaults={"vault_path": vault_rel_path(vpath)},
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Seed demo notes selesai: {count} notes."))

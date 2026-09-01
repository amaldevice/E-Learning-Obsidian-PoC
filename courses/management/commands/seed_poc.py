from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from courses.models import Course, Lesson

User = get_user_model()

PASSWORD = "poc12345"

USERS = [
    ("alice", "alice@example.com", False),
    ("budi", "budi@example.com", False),
    ("citra", "citra@example.com", False),
    ("dewi", "dewi@example.com", False),
    ("admin", "admin@example.com", True),
]

COURSES = [
    {
        "title": "Python Dasar",
        "slug": "python-dasar",
        "description": "Belajar Python dari nol — variabel, fungsi, dan OOP dasar.",
        "lessons": [
            {
                "title": "Pengenalan Python",
                "slug": "pengenalan-python",
                "order": 1,
                "content_md": "# Pengenalan Python\n\nPython adalah bahasa pemrograman yang mudah dipelajari.\n\n- Sintaks bersih\n- Banyak library\n- Cocok untuk pemula",
                "youtube_url": "https://www.youtube.com/watch?v=rfscVS0vtbw",
            },
            {
                "title": "Variabel dan Tipe Data",
                "slug": "variabel-tipe-data",
                "order": 2,
                "content_md": "# Variabel dan Tipe Data\n\n```python\nx = 10\ny = \"hello\"\n```\n\nPelajari `int`, `str`, `list`, `dict`.",
                "youtube_url": "https://www.youtube.com/watch?v=LHBE6Q9XlzI",
            },
            {
                "title": "Fungsi",
                "slug": "fungsi",
                "order": 3,
                "content_md": "# Fungsi\n\n```python\ndef sapa(nama):\n    return f\"Halo {nama}\"\n```\n\nFungsi membantu mengorganisir kode.",
                "youtube_url": "",
            },
            {
                "title": "OOP Dasar",
                "slug": "oop-dasar",
                "order": 4,
                "content_md": "# OOP Dasar\n\nClass dan object di Python:\n\n```python\nclass Kucing:\n    def __init__(self, nama):\n        self.nama = nama\n```",
                "youtube_url": "https://www.youtube.com/watch?v=JeznW_7DlB0",
            },
        ],
    },
    {
        "title": "Web Dasar",
        "slug": "web-dasar",
        "description": "Dasar-dasar pengembangan web — HTML, CSS, dan JavaScript.",
        "lessons": [
            {
                "title": "HTML Dasar",
                "slug": "html-dasar",
                "order": 1,
                "content_md": "# HTML Dasar\n\nStruktur HTML:\n\n```html\n<html>\n  <body><h1>Hello</h1></body>\n</html>\n```",
                "youtube_url": "https://www.youtube.com/watch?v=qz0aGYrrlhU",
            },
            {
                "title": "CSS Dasar",
                "slug": "css-dasar",
                "order": 2,
                "content_md": "# CSS Dasar\n\n```css\nbody { font-family: sans-serif; }\n```\n\nAtur tampilan halaman.",
                "youtube_url": "",
            },
            {
                "title": "JavaScript Dasar",
                "slug": "js-dasar",
                "order": 3,
                "content_md": "# JavaScript Dasar\n\n```js\nconsole.log(\"Hello\");\n```\n\nInteraktivitas di browser.",
                "youtube_url": "https://www.youtube.com/watch?v=W6NZfCO5SIk",
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Seed PoC: 4 siswa + admin (poc12345), 2 courses (4+3 lessons). Idempoten; --reset untuk hapus & buat ulang."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Hapus semua Course/Lesson/User (kecuali superuser lain) lalu seed ulang.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write("Reset: menghapus Course, Lesson, dan user seed...")
            Lesson.objects.all().delete()
            Course.objects.all().delete()
            User.objects.filter(username__in=[u[0] for u in USERS]).delete()
            # Also clean vault files for seed users
            import shutil
            from pathlib import Path

            from django.conf import settings

            from courses.vault import _safe

            vault_root = Path(settings.BASE_DIR) / "vaults"
            for username, *_ in USERS:
                user_vault = vault_root / _safe(username)
                if user_vault.exists():
                    shutil.rmtree(user_vault)
                    self.stdout.write(f"  Cleaned vault: {user_vault}")
        # Users
        for username, email, is_staff in USERS:
            user, created = User.objects.get_or_create(
                username=username, defaults={"email": email}
            )
            user.email = email
            if is_staff:
                user.is_staff = True
                user.is_superuser = True
            user.set_password(PASSWORD)
            user.save()
            self.stdout.write(f"  {'Created' if created else 'Updated'} user: {username}")

        # Courses + Lessons
        for c in COURSES:
            course, created = Course.objects.get_or_create(
                slug=c["slug"],
                defaults={"title": c["title"], "description": c["description"]},
            )
            if not created:
                course.title = c["title"]
                course.description = c["description"]
                course.save()
            self.stdout.write(f"  {'Created' if created else 'Updated'} course: {course.slug}")
            for ls in c["lessons"]:
                lesson, lc = Lesson.objects.get_or_create(
                    course=course,
                    slug=ls["slug"],
                    defaults={
                        "title": ls["title"],
                        "order": ls["order"],
                        "content_md": ls["content_md"],
                        "youtube_url": ls["youtube_url"],
                    },
                )
                if not lc:
                    lesson.title = ls["title"]
                    lesson.order = ls["order"]
                    lesson.content_md = ls["content_md"]
                    lesson.youtube_url = ls["youtube_url"]
                    lesson.save()
                self.stdout.write(f"    {'Created' if lc else 'Updated'} lesson: {lesson.slug}")

        self.stdout.write(self.style.SUCCESS("Seed selesai. Login: alice/budi/citra/dewi/admin — password: poc12345"))

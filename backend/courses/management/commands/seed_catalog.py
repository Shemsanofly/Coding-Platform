from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from courses.catalog_seed import seed_basic_catalog
from courses.models import Course


class Command(BaseCommand):
    help = "Seed starter courses so students see catalog content after login."

    def add_arguments(self, parser):
        parser.add_argument(
            "--admin-email",
            help="Admin account that owns the seeded courses (defaults to the first admin user).",
        )
        parser.add_argument(
            "--skip-enroll",
            action="store_true",
            help="Do not auto-enroll existing student accounts.",
        )
        parser.add_argument(
            "--create-demo-admin",
            action="store_true",
            help="Create a demo admin (admin@learncode.test / Admin2026!) if none exists.",
        )

    def handle(self, *args, **options):
        if options.get("create_demo_admin"):
            demo_admin, created = User.objects.get_or_create(
                email="admin@learncode.test",
                defaults={"role": User.Role.ADMIN, "is_active": True},
            )
            if demo_admin.role != User.Role.ADMIN:
                demo_admin.role = User.Role.ADMIN
            if not demo_admin.is_active:
                demo_admin.is_active = True
            demo_admin.set_password("Admin2026!")
            demo_admin.save(update_fields=["password", "role", "is_active"])
            creator = demo_admin
            self.stdout.write(
                self.style.WARNING(
                    "Demo admin ready: admin@learncode.test / Admin2026! "
                    "(password reset; change before deploying)."
                )
            )
        elif options.get("admin_email"):
            creator = User.objects.filter(email=options["admin_email"], role=User.Role.ADMIN).first()
            if not creator:
                raise CommandError(f"No admin user found for email: {options['admin_email']}")
        else:
            creator = User.objects.filter(role=User.Role.ADMIN).order_by("pk").first()

        if not creator:
            raise CommandError(
                "No admin user found. Register an admin account first, then run: "
                "python manage.py seed_catalog"
            )

        before_count = Course.objects.filter(status__in=[Course.Status.READY, Course.Status.PUBLISHED]).count()
        result = seed_basic_catalog(creator, enroll_students=not options["skip_enroll"])
        after_count = Course.objects.filter(status__in=[Course.Status.READY, Course.Status.PUBLISHED]).count()

        self.stdout.write(
            self.style.SUCCESS(
                f"Catalog ready: created {result['created_count']} course(s); "
                f"visible courses {before_count} -> {after_count}."
            )
        )
        if result["created_ids"]:
            self.stdout.write(f"New course IDs: {', '.join(str(i) for i in result['created_ids'])}")
        else:
            self.stdout.write("Starter courses already existed — no new courses were created.")

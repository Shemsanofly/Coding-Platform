from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Set password for a user by email (development / recovery utility)."

    def add_arguments(self, parser):
        parser.add_argument("email", type=str)
        parser.add_argument("password", type=str)

    def handle(self, *args, **options):
        User = get_user_model()
        email = options["email"].strip()
        password = options["password"]
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise CommandError(f"No user with email {email!r}.")
        user.set_password(password)
        user.save(update_fields=["password"])
        self.stdout.write(self.style.SUCCESS(f"Password updated for {user.email}"))

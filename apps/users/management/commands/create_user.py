import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.users.client_hash import derive_client_hash


class Command(BaseCommand):
    help = "Create a regular user (no admin/staff). Use instead of `createsuperuser`."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("--username", default=None)
        parser.add_argument("--password", default=None,
                            help="Plaintext password (testing only). Otherwise prompted.")

    def handle(self, *args, **opts):
        User = get_user_model()
        email = opts["email"].strip().lower()
        username = (opts.get("username") or email.split("@")[0]).strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError(f"User with email {email} already exists.")
        if User.objects.filter(username__iexact=username).exists():
            raise CommandError(f"Username {username} already taken.")

        plaintext = opts.get("password")
        if not plaintext:
            plaintext = getpass.getpass("Password: ")
            confirm = getpass.getpass("Confirm: ")
            if plaintext != confirm:
                raise CommandError("Passwords do not match.")

        client_hash = derive_client_hash(plaintext, email)
        user = User(username=username, email=email, is_active=True, is_staff=False, is_superuser=False)
        user.set_password(client_hash)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Created {email} (username={username})"))

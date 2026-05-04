import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.users.client_hash import derive_client_hash


class Command(BaseCommand):
    help = "Reset a user's password and force them to change it on next login."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("--password", default=None,
                            help="Plaintext temp password (testing only). Otherwise prompted.")

    def handle(self, *args, **opts):
        User = get_user_model()
        email = opts["email"].strip().lower()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise CommandError(f"No user with email {email}.")
        plaintext = opts.get("password")
        if not plaintext:
            plaintext = getpass.getpass("Temp password: ")
            confirm = getpass.getpass("Confirm: ")
            if plaintext != confirm:
                raise CommandError("Passwords do not match.")
        client_hash = derive_client_hash(plaintext, user.email)
        user.set_password(client_hash)
        user.save()
        try:
            profile = user.profile
        except Exception:
            from apps.directory.models import Profile
            profile, _ = Profile.objects.get_or_create(user=user)
        profile.must_change_password = True
        profile.save(update_fields=["must_change_password"])
        self.stdout.write(self.style.SUCCESS(f"Password reset for {email}; must_change_password=True"))

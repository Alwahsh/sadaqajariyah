from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Toggle Profile.is_verified for a user (default flips True; --unverify flips False)."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("--unverify", action="store_true")

    def handle(self, *args, **opts):
        User = get_user_model()
        email = opts["email"].strip().lower()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise CommandError(f"No user with email {email}.")
        try:
            profile = user.profile
        except Exception:
            from apps.directory.models import Profile
            profile, _ = Profile.objects.get_or_create(user=user)
        profile.is_verified = not opts["unverify"]
        profile.save(update_fields=["is_verified"])
        flag = "True" if profile.is_verified else "False"
        self.stdout.write(self.style.SUCCESS(f"is_verified set to {flag} for {email}"))

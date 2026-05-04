from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailAuthBackend(ModelBackend):
    """Authenticate by email (case-insensitive) instead of username.

    Username remains on the User row (used for profile URL routing) but is not
    a credential.
    """

    def authenticate(self, request, email=None, password=None, username=None, **kwargs):
        # The Django `authenticate()` machinery passes `username` from many call
        # sites; treat that purely as a no-op for compatibility — v1's login
        # form sends `email` and that's the only key we honour.
        if email is None:
            return None
        if password is None:
            return None
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(email__iexact=email.strip().lower())
        except UserModel.DoesNotExist:
            # Run the default password hasher to even out timing.
            UserModel().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

User = get_user_model()


@receiver(pre_save, sender=User)
def lowercase_user_identity(sender, instance, **kwargs):
    """Always store username and email lowercased.

    Load-bearing for case-insensitive username lookup and the lower(email)
    unique index. Runs on every write path (form, shell, management command).
    """
    if instance.username:
        instance.username = instance.username.strip().lower()
    if instance.email:
        instance.email = instance.email.strip().lower()


@receiver(post_save, sender=User)
def create_profile_for_user(sender, instance, created, **kwargs):
    """Create a Profile row whenever a new User is created.

    Guarded on `created` — re-saving an existing User must not create a duplicate.
    Profile creation is centralised here so every account-creation path
    (form, management command, shell, raw `User().save()`) gets a profile.
    """
    if not created:
        return
    from apps.directory.models import Profile
    Profile.objects.get_or_create(user=instance)

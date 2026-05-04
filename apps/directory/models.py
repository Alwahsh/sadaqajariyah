import re

from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import Q
from django.utils.html import strip_tags


def _collapse_singleline(value):
    if not value:
        return ""
    return re.sub(r"\s+", " ", strip_tags(value)).strip()


def _sanitize_bio(value):
    """Collapse spaces+tabs into single space, preserve newlines (cap to 2),
    strip HTML, trim. Used by Profile.clean for the bio field.
    """
    if not value:
        return ""
    txt = strip_tags(value)
    # Normalise newlines.
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse runs of 3+ newlines to exactly 2.
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    # Per-line: collapse spaces+tabs to a single space.
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in txt.split("\n")]
    return "\n".join(lines).strip()


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    first_name = models.CharField(max_length=60, blank=True, default="")
    last_name = models.CharField(max_length=60, blank=True, default="")
    bio = models.TextField(blank=True, default="")
    scheduling_url = models.URLField(max_length=500, blank=True, default="")
    feedback_url = models.URLField(max_length=500, blank=True, default="")
    is_verified = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    services = models.ManyToManyField(
        "directory.ServiceCategory",
        through="directory.ProviderService",
        related_name="profiles",
        blank=True,
    )

    @property
    def display_name(self):
        return (self.first_name + " " + self.last_name).strip()

    def clean(self):
        # Sanitize text fields.
        self.first_name = _collapse_singleline(self.first_name)
        self.last_name = _collapse_singleline(self.last_name)
        self.bio = _sanitize_bio(self.bio)
        super().clean()

    def __str__(self):
        return self.display_name or self.user.username


class ServiceCategory(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    sort_order = models.IntegerField(default=0)
    is_other_freetext = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["is_other_freetext", "sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_other_freetext"],
                condition=Q(is_other_freetext=True),
                name="uniq_service_category_is_other_freetext_true",
            ),
        ]

    def __str__(self):
        return self.name


class ProviderService(models.Model):
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="providerservice_set",
    )
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,
        related_name="provider_services",
    )
    is_freetext = models.BooleanField(default=False)
    custom_description = models.CharField(max_length=280, blank=True, default="")

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(is_freetext=False) | ~Q(custom_description=""),
                name="freetext_requires_description",
            ),
            models.UniqueConstraint(
                fields=["profile", "category"],
                condition=Q(is_freetext=False),
                name="uniq_profile_category_nonfreetext",
            ),
        ]

    def clean(self):
        # Mirror is_freetext from category; sanitize description.
        if self.category_id:
            self.is_freetext = bool(self.category.is_other_freetext)
        self.custom_description = _collapse_singleline(self.custom_description)
        super().clean()

    def save(self, *args, **kwargs):
        if self.category_id:
            self.is_freetext = bool(self.category.is_other_freetext)
        super().save(*args, **kwargs)

    @property
    def display_label(self):
        if self.is_freetext:
            return self.custom_description or "Other"
        return self.category.name

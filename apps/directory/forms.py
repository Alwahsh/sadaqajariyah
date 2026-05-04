import re

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.forms.models import inlineformset_factory
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _

from .models import Profile, ProviderService, ServiceCategory
from .validators import validate_outbound_https_url


def _collapse_singleline(value):
    if not value:
        return ""
    return re.sub(r"\s+", " ", strip_tags(value)).strip()


def _sanitize_bio(value):
    if not value:
        return ""
    txt = strip_tags(value).replace("\r\n", "\n").replace("\r", "\n")
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in txt.split("\n")]
    return "\n".join(lines).strip()


class ProfileEditForm(forms.ModelForm):
    """Edit form for the current user's profile.

    Deliberately does NOT bind `username`, `email`, or `is_verified` — submitting
    those keys is a no-op (IDOR resistance for the privileged fields).
    """

    first_name = forms.CharField(max_length=60, required=True, validators=[MinLengthValidator(1)])
    last_name = forms.CharField(max_length=60, required=False)
    bio = forms.CharField(
        required=True,
        validators=[MinLengthValidator(20)],
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    scheduling_url = forms.CharField(max_length=500, required=False)
    feedback_url = forms.CharField(max_length=500, required=False)

    class Meta:
        model = Profile
        fields = ["first_name", "last_name", "bio", "scheduling_url", "feedback_url"]

    def clean_first_name(self):
        v = _collapse_singleline(self.cleaned_data.get("first_name", ""))
        if not v:
            raise ValidationError(_("Enter your first name."))
        return v

    def clean_last_name(self):
        return _collapse_singleline(self.cleaned_data.get("last_name", ""))

    def clean_bio(self):
        v = _sanitize_bio(self.cleaned_data.get("bio", ""))
        if len(v) < 20:
            raise ValidationError(_("Bio must be at least 20 characters."))
        if len(v) > 1000:
            raise ValidationError(_("Bio must be at most 1000 characters."))
        return v

    def clean_scheduling_url(self):
        v = (self.cleaned_data.get("scheduling_url") or "").strip()
        if not v:
            return ""
        validate_outbound_https_url(v)
        return v

    def clean_feedback_url(self):
        v = (self.cleaned_data.get("feedback_url") or "").strip()
        if not v:
            return ""
        validate_outbound_https_url(v)
        return v


class ProviderServiceForm(forms.ModelForm):
    custom_description = forms.CharField(
        max_length=280, required=False,
        widget=forms.TextInput(attrs={"placeholder": "Optional — describe your specific offering"}),
    )

    class Meta:
        model = ProviderService
        fields = ["category", "custom_description"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit category choices to active categories.
        self.fields["category"].queryset = ServiceCategory.objects.filter(is_active=True)

    def clean_custom_description(self):
        return _collapse_singleline(self.cleaned_data.get("custom_description") or "")

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get("category")
        desc = cleaned.get("custom_description") or ""
        if category and category.is_other_freetext and not desc:
            raise ValidationError({"custom_description": _("Required for 'Other' — name your service.")})
        # Sync is_freetext on the instance.
        if category is not None:
            self.instance.is_freetext = bool(category.is_other_freetext)
        return cleaned


def make_provider_service_formset(*, extra=3):
    """Build the inline formset class for editing a profile's services.

    `extra` controls how many blank rows are appended for adding new services.
    The settings view passes a higher value when the profile has no services
    yet, so a fresh account always sees inputs to fill in.
    """
    return inlineformset_factory(
        Profile,
        ProviderService,
        form=ProviderServiceForm,
        extra=extra,
        max_num=12,
        validate_max=True,
        absolute_max=12,
        can_delete=True,
    )

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .forms import ProfileEditForm, make_provider_service_formset
from .models import Profile, ServiceCategory
from .validators import is_known_scheduling_host

User = get_user_model()


def _base_directory_qs():
    return (
        Profile.objects.filter(user__is_active=True)
        .exclude(scheduling_url="")
        .select_related("user")
        .prefetch_related("providerservice_set__category")
        .order_by("-created_at", "id")
    )


def directory_view(request):
    qs = _base_directory_qs()
    raw_q = (request.GET.get("q") or "").strip()
    truncated_q = raw_q[:80]
    category_slug = (request.GET.get("category") or "").strip()

    filtered = qs
    if truncated_q:
        filtered = filtered.filter(
            Q(first_name__icontains=truncated_q)
            | Q(last_name__icontains=truncated_q)
            | Q(bio__icontains=truncated_q)
            | Q(providerservice_set__custom_description__icontains=truncated_q)
        ).distinct()

    if category_slug and category_slug != "all":
        filtered = filtered.filter(services__slug=category_slug).distinct()

    paginator = Paginator(filtered, 20)
    raw_page = request.GET.get("page", "1")
    try:
        page_obj = paginator.page(raw_page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages or 1)

    # Category chips with counts (count uses base qs filtered by current search if any).
    chip_base = qs
    if truncated_q:
        chip_base = chip_base.filter(
            Q(first_name__icontains=truncated_q)
            | Q(last_name__icontains=truncated_q)
            | Q(bio__icontains=truncated_q)
            | Q(providerservice_set__custom_description__icontains=truncated_q)
        ).distinct()
    categories = list(
        ServiceCategory.objects.filter(is_active=True)
        .annotate(profile_count=Count(
            "provider_services__profile",
            filter=Q(provider_services__profile__in=chip_base),
            distinct=True,
        ))
        .order_by("is_other_freetext", "sort_order", "name")
    )
    total_count = chip_base.count()

    context = {
        "page_obj": page_obj,
        "paginator": paginator,
        "profiles": page_obj.object_list,
        "categories": categories,
        "selected_category": category_slug if category_slug and category_slug != "all" else "",
        "q": raw_q,
        "total_count": total_count,
        "filtered_count": filtered.count(),
    }
    return render(request, "directory/list.html", context)


def home_view(request):
    """The home page — hero band and 'how it works' over the directory listing.

    The directory listing itself is at the same URL when the user scrolls/clicks
    'Browse the directory →' (which is just an anchor or a call to /directory/).
    For simplicity we render two views: home_view for `/` and the directory at `/directory/`.
    """
    visible_count = _base_directory_qs().count()
    return render(request, "pages/home.html", {"visible_count": visible_count})


def public_profile_view(request, username):
    # Case-insensitive username lookup.
    try:
        user = User.objects.select_related("profile").get(username__iexact=username)
    except User.DoesNotExist:
        raise Http404
    is_owner = request.user.is_authenticated and request.user.pk == user.pk

    if not user.is_active and not is_owner:
        raise Http404

    try:
        profile = user.profile
    except Profile.DoesNotExist:
        raise Http404

    has_scheduling = bool(profile.scheduling_url)

    if not has_scheduling and not is_owner:
        raise Http404

    services = list(
        profile.providerservice_set.select_related("category").all()
    )

    show_scheduling_caution = bool(profile.scheduling_url) and not is_known_scheduling_host(profile.scheduling_url)
    show_feedback_caution = bool(profile.feedback_url)

    context = {
        "profile_user": user,
        "profile": profile,
        "services": services,
        "is_owner": is_owner,
        "has_scheduling": has_scheduling,
        "show_scheduling_caution": show_scheduling_caution,
        "show_feedback_caution": show_feedback_caution,
    }
    return render(request, "directory/profile.html", context)


@login_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def profile_edit_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        # On POST, derive extra from the management form so it matches what
        # the rendered form told the browser. Validation does not depend on
        # extra at all, but rendering errors back to the user does.
        try:
            total = int(request.POST.get("providerservice_set-TOTAL_FORMS", "0"))
            initial = int(request.POST.get("providerservice_set-INITIAL_FORMS", "0"))
            extra = max(0, total - initial)
        except ValueError:
            extra = 1
        Formset = make_provider_service_formset(extra=extra)
        form = ProfileEditForm(request.POST, instance=profile)
        formset = Formset(request.POST, instance=profile)
        if form.is_valid() and formset.is_valid():
            # Capture the persisted bio + verified state BEFORE saving so we
            # can detect a real bio change. Verified status is invalidated by
            # bio edits — the operator vouches for what's there at verify time.
            persisted = Profile.objects.only("bio", "is_verified").get(pk=profile.pk)
            bio_changed = form.cleaned_data.get("bio", "") != persisted.bio
            was_verified = persisted.is_verified

            form.save()
            formset.save()
            profile.refresh_from_db()

            warned = False
            if bio_changed and was_verified:
                profile.is_verified = False
                profile.save(update_fields=["is_verified"])
                messages.warning(
                    request,
                    "Your verified badge has been removed because you changed your bio. "
                    "The operator will re-verify your account when they review the new bio.",
                )
                warned = True
            if profile.scheduling_url and not is_known_scheduling_host(profile.scheduling_url):
                messages.warning(
                    request,
                    "We don't recognize this scheduling tool — make sure the link works for visitors.",
                )
                warned = True
            if not warned:
                messages.success(request, "Profile saved.")
            return redirect("/settings/")
    else:
        # Render existing rows; users with no services see 1 blank row to start.
        # Additional rows are added on demand via the Add Another button (JS),
        # up to the formset's max_num=12 cap.
        existing = profile.providerservice_set.count()
        blank = 1 if existing == 0 else 0
        Formset = make_provider_service_formset(extra=blank)
        form = ProfileEditForm(instance=profile)
        formset = Formset(instance=profile)

    return render(
        request,
        "directory/settings.html",
        {
            "form": form,
            "formset": formset,
            "profile": profile,
            "username": request.user.username,
        },
    )

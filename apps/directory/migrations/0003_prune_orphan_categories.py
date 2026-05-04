"""Forward-compatible cleanup for environments that ran an earlier seed list.

The set of seeded categories changed in `0002_seed_categories.py`. Because that
migration uses `update_or_create` keyed on `slug`, re-running it on a DB seeded
with the old list will *update* the new slugs but leave any old, no-longer-seeded
slugs (e.g., `mentoring`, `counseling`) sitting in the table. This migration
removes those orphans so the dropdown matches the canonical list.

ProviderService.category is `on_delete=PROTECT`, so before deleting the orphan
ServiceCategory rows we hard-delete any provider services referencing them.
This is acceptable because:
  - In dev environments the data is throwaway.
  - In production the operator hasn't seeded yet (v1 launches with empty DB).
"""
from django.db import migrations


# Canonical v1 seed list. Keep this in sync with 0002_seed_categories.CATEGORIES.
# Because Django only runs each migration once, editing 0002 after deploys does
# not re-seed; this migration both prunes orphans AND idempotently re-applies
# the canonical list via `update_or_create`.
CATEGORIES = [
    ("arabic-language", "Arabic Language", 10, False),
    ("mock-interview", "Mock Interview", 20, False),
    ("quran-revising", "Quran Revising", 30, False),
    ("other", "Other", 999, True),
]
KEEP_SLUGS = {c[0] for c in CATEGORIES}


def prune(apps, schema_editor):
    ServiceCategory = apps.get_model("directory", "ServiceCategory")
    ProviderService = apps.get_model("directory", "ProviderService")
    # Drop any provider services that reference categories outside the canonical list,
    # then drop the orphan categories themselves (PROTECT would otherwise block them).
    orphans = ServiceCategory.objects.exclude(slug__in=KEEP_SLUGS)
    ProviderService.objects.filter(category__in=orphans).delete()
    orphans.delete()
    # Idempotently apply the canonical list (creates anything missing, updates
    # name/sort_order/is_other_freetext/is_active for existing).
    for slug, name, sort_order, is_other in CATEGORIES:
        ServiceCategory.objects.update_or_create(
            slug=slug,
            defaults={"name": name, "sort_order": sort_order,
                     "is_other_freetext": is_other, "is_active": True},
        )


def unprune(apps, schema_editor):
    """No-op: we cannot recover the canonical names of pruned categories
    without reading the old seed list. If a downgrade is needed, re-run
    a fresh seed migration."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("directory", "0002_seed_categories"),
    ]
    operations = [
        migrations.RunPython(prune, reverse_code=unprune),
    ]

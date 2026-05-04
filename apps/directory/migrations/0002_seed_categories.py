from django.db import migrations


CATEGORIES = [
    ("arabic-language", "Arabic Language", 10, False),
    ("mock-interview", "Mock Interview", 20, False),
    ("quran-revising", "Quran Revising", 30, False),
    ("other", "Other", 999, True),
]


def seed(apps, schema_editor):
    ServiceCategory = apps.get_model("directory", "ServiceCategory")
    for slug, name, sort_order, is_other in CATEGORIES:
        ServiceCategory.objects.update_or_create(
            slug=slug,
            defaults={"name": name, "sort_order": sort_order, "is_other_freetext": is_other, "is_active": True},
        )


def unseed(apps, schema_editor):
    ServiceCategory = apps.get_model("directory", "ServiceCategory")
    ServiceCategory.objects.filter(slug__in=[c[0] for c in CATEGORIES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("directory", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(seed, reverse_code=unseed),
    ]

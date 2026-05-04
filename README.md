# Sadaqa Jariyah

A community directory of members offering mentorship, counsel, and quiet hours of their time. Each member publishes a profile that links out to their own scheduling tool (Calendly, Cal.com, etc.) — the platform itself does not host bookings.

- Domain: `sadaqajariyah.online`
- Stack: Django 5 + Tailwind + WhiteNoise (Postgres in prod, SQLite in dev)
- Source of truth for behavior: [`.thoughts/plan.md`](.thoughts/plan.md) and [`.thoughts/specs.md`](.thoughts/specs.md)

> **No outbound email.** v1 sends zero email — no signup confirmation, no password-reset link. Forgot-password is operator-only via a management command (see below).

---

## Local development

```sh
git clone <repo>
cd sadaqajariyah
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
DJANGO_SETTINGS_MODULE=config.settings.dev .venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

Then open http://127.0.0.1:8000/.

`manage.py` defaults `DJANGO_SETTINGS_MODULE` to `config.settings.dev`, so subsequent commands can omit the env var.

### Run the test suite

```sh
.venv/bin/pytest
```

208 tests cover all 16 spec sections (URL validation, auth, anti-bot, signals, DB constraints, directory search/filter/pagination, profile page, badge rendering, accessibility, security headers, outbound-link safety, password change, must-change-password redirect, operator workflows, end-to-end smoke).

---

## Walkthrough — what to try

1. **Sign up** at `/accounts/signup/`. The browser hashes your password with PBKDF2-SHA256 (email as salt) before submit — open DevTools → Network → request payload to confirm the wire value is a 64-char hex hash, not plaintext.
2. **Edit your profile** at `/settings/`:
   - First name (required), last name (optional), bio (20–1000 chars).
   - **Scheduling URL** — try `https://calendly.com/me/30` (allowlisted, saves cleanly). Then try `https://my-tool.example.com/` (non-allowlisted, fires a yellow warning banner and a public visitor caution panel on your profile page).
   - **Anonymous feedback URL** (optional) — any `https://` URL.
   - **Services you offer** — pick a category (Arabic Language, Mock Interview, Quran Revising) from the dropdown and optionally describe your specific offering. Pick "Other" for anything not in the predefined list (description required there). The form always renders 12 rows total — a mix of your saved services plus blank rows, up to the 12-service cap. Saving with some rows blank just skips them.
3. **Public profile** at `/p/<your-username>/`:
   - Owner self-view shows a banner if scheduling URL is empty.
   - Visitors see the dark sticky CTA card with "Schedule with me →" and (if set) "Send anonymous feedback →" — both open in new tabs with `noopener noreferrer` and `referrerpolicy="no-referrer"`.
   - Yellow caution panels render for non-allowlisted scheduling hosts and for any feedback URL.
4. **Browse directory** at `/directory/`:
   - Search by name, bio, or per-service description (case-insensitive substring; truncated server-side to 80 chars).
   - Category chips (counts shown). Empty filter → all profiles. Unknown slug → empty state, not 404.
5. **Static pages:** `/privacy/`, `/terms/`, `/robots.txt`.

> Username lookups are case-insensitive: `/p/Alice/` and `/p/alice/` resolve to the same profile.

---

## Operator console reference

> v1 has **no Django admin**. `/admin/` returns 404. Every operator action runs through `manage.py` from a shell on the server (Render's "Shell" tab in production, your local terminal in dev).

All examples assume you're in the project root with the venv activated. In dev, prefix commands with `.venv/bin/python`. In production on Render, the shell already has Django on PATH.

### Create the operator's account

> **Do not use `createsuperuser`** — it stores a hash of plaintext, which the client-side-hashing login form can never match.

```sh
python manage.py create_user operator@example.com
# Prompts twice for a password (getpass).
# For tests/automation, --password=<plaintext> can be passed inline.

python manage.py verify_user operator@example.com
```

The first command creates a regular user (no `is_staff`, no `is_superuser`) with the password derived using the same algorithm the browser uses. The operator can log in via `/accounts/login/` immediately.

The second command flips the verified badge on so the operator's profile shows "✓ Verified" in the directory.

### Verify (publish) a member

```sh
python manage.py verify_user member@example.com
```

The "✓ Verified" pill appears next to the member's name in the directory and on their profile on the next page load. Verification does **not** gate directory inclusion — unverified profiles are listed too, just without the badge.

To unverify:

```sh
python manage.py verify_user member@example.com --unverify
```

### Reset a forgotten password

```sh
python manage.py reset_password member@example.com
# Prompts for a temporary plaintext password.
```

Then communicate the temp value to the user **out-of-band** (WhatsApp, in person, etc.) — the platform never sends email.

The user logs in at `/accounts/login/` with the temp password. Their profile's `must_change_password` flag is `True`, so every authenticated page (other than `/settings/password/` and `/accounts/logout/`) redirects them to the change-password form until they pick a new one.

### Deactivate an account

Logs the user out on their next request and removes them from the directory:

```sh
python manage.py shell -c "from django.contrib.auth import get_user_model; get_user_model().objects.filter(email__iexact='member@example.com').update(is_active=False)"
```

To re-activate:

```sh
python manage.py shell -c "from django.contrib.auth import get_user_model; get_user_model().objects.filter(email__iexact='member@example.com').update(is_active=True)"
```

### Hard-delete an account

Removes the user, their profile, and all their service rows (FK cascades). The username becomes available for re-registration.

```sh
python manage.py shell -c "from django.contrib.auth import get_user_model; get_user_model().objects.filter(email__iexact='member@example.com').delete()"
```

> Privacy notice obligates the operator to deactivate immediately and hard-delete within 30 days when a member requests it.

### Service categories

Categories are **seeded by data migrations**. Running `manage.py migrate` on a fresh database installs the canonical v1 list automatically:

| Slug | Name | `is_other_freetext` |
|---|---|---|
| `arabic-language` | Arabic Language | False |
| `mock-interview` | Mock Interview | False |
| `quran-revising` | Quran Revising | False |
| `other` | Other | True (the singleton free-text bucket) |

You should not need to create categories manually — every member's `/settings/` page renders all four as options in the category dropdown for each service row, and the directory page renders them as filter chips.

#### Re-seeding after a manual delete

```sh
python manage.py migrate directory 0002 && python manage.py migrate
```

The first command rolls back to migration `0002`, the second re-applies `0003_prune_orphan_categories` which idempotently re-creates anything missing via `update_or_create`.

#### Editing the category list

Two migrations own this list:

- `apps/directory/migrations/0002_seed_categories.py` — initial seed.
- `apps/directory/migrations/0003_prune_orphan_categories.py` — prunes any category whose slug is no longer in the list, then re-applies the canonical list. Required because Django runs each migration only once, so editing `0002` after deploys does **not** re-seed.

To change the categories on an existing DB:

1. Edit the `CATEGORIES` list in **both** `0002_seed_categories.py` and `0003_prune_orphan_categories.py` (keep them in sync).
2. To force the prune migration to re-run, roll back and re-apply:
   ```sh
   python manage.py migrate directory 0002
   python manage.py migrate
   ```

To add a new category **without disturbing existing data** (production-style), write a fresh data migration that only inserts:

```python
# apps/directory/migrations/0004_add_legal_advice.py
from django.db import migrations


def add(apps, schema_editor):
    ServiceCategory = apps.get_model("directory", "ServiceCategory")
    ServiceCategory.objects.update_or_create(
        slug="legal-advice",
        defaults={"name": "Legal Advice", "sort_order": 80, "is_other_freetext": False, "is_active": True},
    )


def remove(apps, schema_editor):
    ServiceCategory = apps.get_model("directory", "ServiceCategory")
    ServiceCategory.objects.filter(slug="legal-advice").delete()


class Migration(migrations.Migration):
    dependencies = [("directory", "0003_prune_orphan_categories")]
    operations = [migrations.RunPython(add, reverse_code=remove)]
```

Then `python manage.py migrate`.

> Categories are immutable once any provider selects them. `ProviderService.category` uses `on_delete=PROTECT`, so deleting an in-use category raises an error. To retire one without breaking existing rows, set `is_active=False` (filters it out of forms and chips) rather than deleting.
>
> The singleton `is_other_freetext=True` row is locked: a partial unique constraint rejects a second one. Don't write a migration that creates another `Other`.

### Inspect a profile

```sh
python manage.py shell
```

```python
from apps.directory.models import Profile
p = Profile.objects.get(user__email__iexact="member@example.com")
print(p.display_name, p.is_verified, p.scheduling_url, p.feedback_url)
print([(s.category.name, s.custom_description) for s in p.providerservice_set.all()])
```

### Raw DB access

```sh
python manage.py dbshell
```

Tables you'll care about: `auth_user`, `directory_profile`, `directory_servicecategory`, `directory_providerservice`. Read-only queries (e.g. `SELECT count(*) FROM directory_profile WHERE is_verified = false;`) are safe; UPDATEs bypass model `clean()` and form-layer sanitization — prefer `manage.py shell` for writes.

---

## Project layout

| App | Path | Owns |
|---|---|---|
| `users` | `apps/users/` | Auth backend, peppered hasher, registration / login / change-password forms & views, signals, three management commands, client-side `auth-hash.js` |
| `directory` | `apps/directory/` | `Profile` / `ServiceCategory` / `ProviderService` models, URL validators + scheduling-host allowlist, profile-edit at `/settings/`, public profile at `/p/<username>/`, directory list |
| `security_app` | `apps/security/` | CSP middleware, no-index header middleware, must-change-password redirect middleware, honeypot + signed-timestamp helpers, `robots.txt` view |
| `pages` | `apps/pages/` | Home, privacy, terms, custom 404/500, base template |
| `config` | `config/` | Django project package: settings split, root urls, wsgi |

Settings:

- `config.settings.dev` — local SQLite, `DEBUG=True`
- `config.settings.test` — in-memory SQLite, used by pytest
- `config.settings.prod` — Postgres via `DATABASE_URL`, `DEBUG=False`, full security headers
- `config.settings.base` — shared

---

## Production environment variables

Set in the Render dashboard (or the equivalent on whichever host):

| Var | Notes |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` |
| `SECRET_KEY` | 64+ urlsafe chars; rotating logs everyone out |
| `PEPPER` | 64+ urlsafe chars; rotating invalidates **every** stored password |
| `DATABASE_URL` | Auto-injected by Render's linked Postgres |
| `ALLOWED_HOSTS` | Comma-separated, e.g. `sadaqajariyah.online,www.sadaqajariyah.online,<service>.onrender.com` |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated `https://...` origins |
| `SITE_IS_PRODUCTION` | `1` in prod (drives robots.txt + drops the `X-Robots-Tag: noindex` header) |
| `OPERATOR_CONTACT_EMAIL` | Rendered into the privacy notice as the deletion / verification / forgot-password contact channel |
| `SECURE_HSTS_SECONDS` | `60` for the first week, then bump to `31536000` |

Generate `SECRET_KEY` and `PEPPER` with:

```sh
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

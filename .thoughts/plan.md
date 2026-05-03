# Sadaqa Jariyah — v1 Project Plan

## Overview

**Sadaqa Jariyah** (صدقة جارية, "ongoing charity") is a web platform for an Islamic center community where members publish a public profile listing the services they offer along with a **link to their own scheduling tool** (Calendly, Cal.com, SavvyCal, Google appointment scheduling, etc.). The site itself does **not** handle slot creation, availability, or bookings — it is a directory that hands the visitor off to the provider's chosen scheduling service.

Built in **Python with Django**, deployed on a free tier. **Domain: `sadaqajariyah.online`** (already purchased).

> **Booking is intentionally out of scope for v1.** All slot, booking, cancellation, and notification logic — along with the matching technical decisions — has been moved to `.thoughts/deferred_plan-v2-booking.md` and may be picked up later if the directory-only model proves insufficient. **Anything resembling a slot, calendar, availability window, in-site booking confirmation, or per-booking email belongs in v2 — do not let it leak into v1.**

---

## Design Reference

The visual design has been mocked up in HTML/CSS/JS and exported into `.thoughts/design/`. **Read `.thoughts/design/design-notes.md` first** — it's a distilled spec of palette, type, screen-by-screen layouts, and exact copy. The full prototype is alongside it:

- `.thoughts/design/design-notes.md` — distilled implementation reference (start here)
- `.thoughts/design/Sadaqa Jariyah - Final.html` — runnable prototype (open locally; loads `data.js`, `design-canvas.jsx`, `final.jsx` via relative `<script>` tags)
- `.thoughts/design/final.jsx` — the 8 screen components (Home, Directory, Profile, Signup, Login, Edit, Owner-empty, Privacy)
- `.thoughts/design/data.js` — `window.SJ_DATA` with sample categories, members, and approved copy strings (`tagline`, `sub`, `cta`, `browse`, `join`)
- `.thoughts/design/design-canvas.jsx` — the design-canvas chrome (artboard wrapper; not part of the production UI)
- `.thoughts/design/BUNDLE-README.md` — the original design-bundle README from claude.ai/design
- `.thoughts/design/chat-transcript.md` — the design conversation, useful when intent is ambiguous

Direction the user landed on: **"Communal" structure (DM Sans, dense list directory, dark sticky CTA card on the profile page) wearing the "Garden" warm-sand + sage palette.**

When the design and this plan disagree: **plan.md wins for behavior, design-notes.md wins for visual treatment.**

---

## Core Features

### User Accounts (Providers)

- Single account type (free for all). No profile photos in v1 (avoids media-storage complexity).
- Profile fields: name, bio, services offered, **scheduling link** (Calendly etc.), and an optional **anonymous feedback link** (see "URL Field Validation" below). All editable any time from account settings.

**Login**
- Login uses **email + password** — NOT username. Username is publicly visible in profile URLs (`/p/<username>/`); using it as the login identifier would mean every directory profile is half a credential pair. Email is private. This also matches design-notes §4.5.
- Login is **case-insensitive on email**: `Ahmed@Example.com` and `ahmed@example.com` resolve to the same account.
- Implementation: a custom `EmailAuthBackend` at `apps/users/backends.py` does `User.objects.get(email__iexact=email.strip().lower())` then `check_password()`. Replace Django's default `ModelBackend` in `AUTHENTICATION_BACKENDS` (single-entry list — see "Required Django settings"). The login form has an `email` field (not `username`) and calls `authenticate(request, email=..., password=...)`.
- The form's `clean_email` lowercases input; combined with the `pre_save` signal that lowercases `User.email` on every write path (see "Username storage normalization"), the `lower(email)` unique index never trips a duplicate `IntegrityError` from a normal flow.
- **Passwords are hashed client-side before transit.** The "password" submitted by the form is already a derived value, never plaintext. See "Security → Password hashing" for the full scheme.

**Registration**
- Email/password registration via Django built-in auth, using the **client-side-hashed password** ("Security → Password hashing").
- **Single-step — no email at all.** No verification email, no welcome email, no any email. The platform sends zero outbound mail (see "Notifications — none"). The user is logged in immediately on submit; the registration view calls `django.contrib.auth.login(request, user)` after `form.save()`. v1 sets `AUTHENTICATION_BACKENDS = ["apps.users.backends.EmailAuthBackend"]` (single backend), so `login()` resolves the backend without needing `user.backend = "..."` set explicitly. If a second backend is ever added, set `user.backend` before `login()` to avoid Django's "multiple backends, can't pick" `ValueError`.
- The new account starts with `Profile.is_verified = False`. The profile **is visible** in the public directory as soon as the user fills in their profile and a scheduling URL — verification only controls whether a "Verified" badge renders next to their name (see "Verified status — badge-only"). The user can complete their profile at `/settings/` immediately and will appear in the directory on the next page load; the badge is added later when an operator flips the flag.
- **Email is required and unique.** Django's `User.email` is not unique by default. Enforce via:
  1. Custom registration form `clean_email` that:
     - strips and lowercases (`email = email.strip().lower()`),
     - then runs a `User.objects.filter(email__iexact=email).exists()` check and raises `ValidationError("An account with this email already exists.")` if true.
     Both steps are required: without lowercasing, the case-insensitive duplicate check still runs (`__iexact`) but the lowercased value is also what gets stored, keeping the DB invariant clean. Without the existence check, the user hits the DB unique index and sees an `IntegrityError`-induced 500 instead of a clean form error.
  2. DB-level unique index on `lower(email)` as defense-in-depth (and for non-form write paths like `createsuperuser`). Add via a `migrations.RunSQL` migration in **`apps/users/migrations/`** (the users app, even though the table is `auth_user` — Django allows cross-app schema migrations and this keeps the constraint with the rest of the user-app rules). The migration depends on `("auth", "__latest__")` (or pin a specific auth migration if `__latest__` ever causes ordering issues). SQL: `CREATE UNIQUE INDEX uniq_auth_user_email_lower ON auth_user (lower(email));` with matching `DROP INDEX uniq_auth_user_email_lower;` as the reverse. (Cleanest way without adopting a custom `AUTH_USER_MODEL`.)
- v1 launches with an empty DB, so no email-dedupe data migration is needed.

**Username constraints**
- Chosen at registration, **immutable in v1** (changing breaks inbound links). Becomes part of the profile URL.
- The profile-edit form does **not** include `username` — not even as a disabled input. A crafted POST with `username=...` must not rename the account. Same rule for `email`: not exposed in edit (email change in v1 = ask the operator).
- Validation rules:
  - ASCII-only, lowercased on save, regex `^[a-z0-9][a-z0-9_-]{2,29}$` (3–30 chars). No Unicode/IDN — keeps URLs unambiguous and avoids homoglyph impersonation.
  - Form `clean_username` lowercases input before regex-checking, so typing `Ahmed` doesn't return a confusing "must start with a-z" error.
  - **Reserved-words list** rejected at form level. Kept as a Python frozenset `RESERVED_USERNAMES` in the user app, matched case-insensitively after the lowercase step. Representative subset (auth/route/admin/system terms — see the constant in code for the authoritative list):
    ```
    admin  administrator  login   logout    signup    register
    auth   accounts       account password  settings  me
    p      profile        profiles directory category categories
    api    static         media   about     contact   terms
    privacy help          search  feedback  support   moderator
    root   system         users   home      www       mail
    ```
    Plus reserved infra/sentinel names: `robots`, `sitemap`, `health`, `status`, `security`, `null`, `undefined`. Adding a new top-level URL prefix means adding its label here in the same PR.
  - **Case-insensitive uniqueness** is achieved by storage normalization (option (a) below): every write path lowercases `username` before save, so Django's default `unique=True` on `User.username` already prevents `Ahmed` and `ahmed` both registering. **No extra DB constraint (CITEXT / `lower(username)` index) is needed for v1** — that would only be required under option (b) where mixed-case usernames are tolerated on disk.

**Username storage normalization (load-bearing for case-insensitive usernames)**
v1 ships **option (a)**: usernames are stored already-lowercased on every write path. Implementation:
- Registration form `clean_username` lowercases.
- A `pre_save` signal on `User` lowercases — **this is the load-bearing piece**. Without it, shell writes (`User.objects.create_user(...)`, `manage.py shell` updates, the operator's management commands) could leave mixed-case usernames on disk, unreachable by canonical lowercase profile URLs and lookups.
- The login form `clean_email` lowercases input, and `EmailAuthBackend` uses `email__iexact` lookups, so email login is case-insensitive.

The same `pre_save` handler **also lowercases `User.email`** so the `lower(email)` unique index can never trip an `IntegrityError` from a non-form write path (`manage.py shell`, `User.objects.create`, the operator's management commands). The lowercasing keeps the unique-index invariant regardless of how the row is written.

(Option (b) — a custom auth backend doing `username__iexact` and skipping storage normalization — was rejected as more code paths to maintain.)

The reserved-words check is form-only: `manage.py create_user --username admin` (or a manual `User.objects.create(username="admin")` from the shell) will succeed and is not blocked. That is operator discipline, not a code gate — pick a non-reserved username when running `create_user` for the operator's account. The Phase 1 README documents this.

### Public Profiles & Discovery

**Outbound link rules (used by both `scheduling_url` and `feedback_url` rendering)**
Every outbound link to a user-supplied URL must render with these three attributes together:
```
target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer"
```
The link-level `referrerpolicy="no-referrer"` is in addition to the site-wide `SECURE_REFERRER_POLICY = "same-origin"` — belt-and-braces because some browsers honor the link attribute differently than the response header. The point is to avoid leaking the visiting profile URL to the third-party tool's analytics. For feedback links this is especially load-bearing — "anonymous" feedback that arrives stamped with the originating profile URL defeats the feature. **Never auto-fetch, preview, or unfurl** these URLs server-side; we don't want an SSRF surface.

**Profile page**
- Stable URL: `/p/<username>/` — i.e., `https://sadaqajariyah.online/p/<username>/`.
- Prominent **"Schedule with me"** CTA linking the provider's scheduling URL. No embedded widget in v1 (third-party JS would complicate CSP for marginal gain).
- If `feedback_url` is set, render a secondary "Send anonymous feedback →" button under the schedule CTA in the sticky sidebar (design-notes §4.3). Helper text below: `Opens an anonymous form in a new tab`.
- **Render the feedback button only if `feedback_url` is non-empty** — never show an empty/disabled placeholder.
- **Visitor-facing feedback caution.** Whenever the feedback button renders, render a caution panel adjacent to it (immediately below the helper line, outside the dark sticky CTA card so the warm-yellow palette stays readable). Approved copy, verbatim: `This feedback form should be anonymous — it should not ask for your name, email, or any other personal details. Sadaqa Jariyah cannot verify what the form requests, so please check before submitting.` Use the same warm-yellow caution palette as the scheduling caution (`#FBF1D6` bg, `#E8D58A` border, `#6B5418` body, `#3F3208` heading-text where applicable). A `⚠` glyph on the leading line is decorative (`aria-hidden="true"`). Unlike the scheduling caution, this one is **unconditional on host** — every feedback URL is a third-party form we cannot inspect, so the warning fires whenever the button does. The caution is informational, NOT an interstitial; the button still opens the URL in a new tab when clicked. The caution does NOT render when `feedback_url` is blank (since the button itself does not render).

**Browse / search**
- Categories:
  - **Predefined service categories** (e.g., Mentoring, Counseling, Islamic Education, Career Advice, Quran Tutoring).
  - **"Other" category** with free-text description for custom services.
- Search matches `first_name`, `last_name`, `bio`, and the `custom_description` of every service row (per design-notes §4.2 — broadened in v1 since per-service descriptions are now optional on every category, not just "Other"). Implementation:
  ```python
  Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(bio__icontains=q) | Q(providerservice__custom_description__icontains=q)
  ```
  Terminate the queryset with `.distinct()` — multi-match via joins on `providerservice` will otherwise duplicate rows. Acceptance test: a profile with three matching service descriptions appears once.
- **Feedback URL is NOT searched** — it's a destination, not searchable content.
- **Predefined category names are NOT searched.** A search for `"Mentoring"` won't return profiles whose only mentoring affiliation is the predefined `Mentoring` category — visitors filter by category via the chip row instead. The categories are the chip filter; the free-text fields (name, bio, per-service description) are the search corpus.
- Search input is **trimmed and silently truncated** to 80 chars server-side before `icontains`. A 5MB query against three `ILIKE %...%` clauses is trivial DoS; capping removes it. Truncating instead of rejecting avoids hostile errors on legitimate long pastes. Document in the runbook so it's not mistaken for a bug.
- An empty/whitespace-only `q` (after trim) **skips the search filter entirely** — do not apply the triple-OR `Q(...)` against `""`, since `icontains=""` matches every row but issues an unnecessary join. Just don't add the filter when `q` is empty.
- **Search performance for v1 scale.** Triple-OR `icontains` uses no index and seq-scans. Fine for the expected low-hundreds row count. If the directory passes ~10k rows or queries slow, switch to Postgres trigram (`pg_trgm` + `GinIndex(opclasses=["gin_trgm_ops"])`) or full-text search (`SearchVector`/`SearchQuery`). Not v1 work — measure first.

**Text sanitization on save**
- **Where it runs:** in the model's `clean()` method (called automatically by `ModelForm.full_clean()`), NOT in `save()`. Putting it in `clean()` means the sanitized value goes into the profile-edit form path and surfaces length-limit errors to the user *after* sanitization (so a bio of 1000 `<b>` tags doesn't pass `max_length` and then get stripped to 6 chars). Bare `Profile.objects.create(bio="...")` from `manage.py shell` or a test bypasses `clean()` — that's acceptable because shell writes are operator-trusted; tests assert sanitization through the form path.
- All free-text fields (`first_name`, `last_name`, `bio`, `custom_description`) are stripped of HTML via `django.utils.html.strip_tags` (or bleach with no allowed tags). `strip_tags` is HTML-syntactic stripping, **not** XSS sanitization — never `mark_safe` user input. Templates rely on Django's auto-escape; `strip_tags` exists so directory cards don't render literal `<b>my</b>` text after escaping.
- Whitespace handling:
  - `first_name`: collapse all whitespace runs (including newlines) to single space, trim. `min_length=1`, `max_length=60`. Required at the form layer.
  - `last_name`: same collapse/trim; `max_length=60`. **Optional** — a member who doesn't want to publish a last name leaves it blank, and the public profile renders just `first_name` (no trailing space).
  - `bio`: collapse spaces and tabs but keep `\n`; cap consecutive newlines at two; trim. Templates render with `linebreaksbr`. `min_length=20`, `max_length=1000`.
  - `custom_description`: collapse all whitespace to single space, trim. `max_length=280`. Optional on every service row; required only when `is_freetext=True` (the "Other" category needs a label).

**Public display name**
- Computed as `(first_name + " " + last_name).strip()` so a missing last name doesn't leave a trailing space. Add a `Profile.display_name` property and use it in templates and `Profile.__str__` (visible from `manage.py shell` listings) instead of building the string ad-hoc — keeps the trim rule in one place.

**Directory inclusion**
- A profile appears in the directory if `user.is_active=True` AND `scheduling_url != ""`. Both filters apply **before** any search/category narrowing. **`is_verified` does NOT gate inclusion** — it only controls whether the "Verified" badge renders on the card. See "Verified status — badge-only".

**Robots / SEO**
- Production `robots.txt`: Allow `/` and `/p/<username>/`. Disallow `/accounts/` (login, signup) and `/settings/`. **No `/admin/` entry** — there is no Django admin in v1 (see "No Django admin (operator workflow)").
- The robots.txt paths are **load-bearing on the URL layout**. `config/urls.py` MUST mount:
  - Auth URLs at `/accounts/` (only the four routes v1 uses — `login/`, `logout/`, `signup/`, plus the in-app change-password at `/settings/password/`; do **not** `include("django.contrib.auth.urls")` wholesale, see "Notifications — none")
  - Profile-edit at `/settings/`
  Move either, update the robots.txt template in the same PR. There is no `/admin/` mount.
- Non-production deploys (preview/staging) must serve `Disallow: /` AND an `X-Robots-Tag: noindex` header, gated on the `SITE_IS_PRODUCTION` env flag.
- No sitemap in v1.

### URL Field Validation (`scheduling_url` and `feedback_url`)

Both fields are `URLField(max_length=500)` (Django's default 200 isn't enough for some Calendly/Google links with query params). Validation is mostly shared, with one scheduling-only addition.

**Shared hard-block validation** — extract into `validate_outbound_https_url(url)` in a shared module, called from both `clean_scheduling_url` and `clean_feedback_url`. Raises `ValidationError` if any of (checked in this order — the IP check assumes host is non-empty):
1. URL begins with `javascript:`, `data:`, or `file:` (case-insensitive scheme check, since `urlparse("JavaScript:...")` returns scheme `"javascript"` already lowercased, but a safer `url.strip().lower().startswith(...)` short-circuit avoids any urlparse quirks on malformed input).
2. scheme is not `https` (after the first check).
3. host is missing — i.e., `urlparse(url).hostname` is `None` or `""`. Reject before the IP check, because `ipaddress.ip_address(None)` raises `TypeError` (uncaught → 500), and `ipaddress.ip_address("")` raises `ValueError` which is the success-by-exception path we depend on.
4. host is an IP literal. Take `urlparse(url).hostname` (NOT `.netloc` — that includes port and IPv6 brackets; `.hostname` lowercases and strips brackets), then `ipaddress.ip_address(host)` inside `try/except ValueError` — if it returns successfully (no `ValueError`), reject. This catches `https://[::1]/` correctly.

The IP-literal block isn't SSRF protection (we never fetch the URL); it's that no legitimate scheduling/form tool publishes raw-IP links — they're a phishing signal.

**Scheduling-only soft warning (host allowlist)**
- `KNOWN_SCHEDULING_HOSTS` is a settings constant: `calendly.com`, `cal.com`, `savvycal.com`, `calendar.google.com`, `calendar.app.google`, `koalendar.com`, `tidycal.com`, `youcanbook.me`, `zcal.co`. Updating the list is a config change.
- Match by host suffix on a label boundary: `host == allowed or host.endswith("." + allowed)`. Never a bare `endswith` — `evil-calendly.com` would match.
- Compute `host` from `urlparse(url).hostname` (lowercased, IPv6-bracket-stripped) then strip a leading `www.`.
- If the host isn't in the allowlist, **save the profile anyway** but set a Django `messages.warning` on the response: "We don't recognize this scheduling tool — make sure the link works for visitors." (Implementation note: this is a view-layer side effect after `form.save()`, not something `clean_*` can do — `clean_*` raises errors, it doesn't issue warnings. Concretely: extract a small helper `is_known_scheduling_host(url) -> bool` in the same module as `validate_outbound_https_url`, call it from the view's `form_valid()` after `form.save()`, and call `messages.warning(request, "...")` if it returns False. Do not duplicate the host-parsing logic between `clean_scheduling_url` and the view.)
- **Also surface a visitor-facing caution on the public profile** when the host is non-allowlisted. Render a small caution panel adjacent to (e.g., directly below) the "Schedule with me →" CTA in the sticky sidebar, only when `is_known_scheduling_host(profile.scheduling_url)` returns False. Approved copy: `Sadaqa Jariyah doesn't recognize this scheduling tool. Be cautious on the linked site and never share confidential information there.` The same `is_known_scheduling_host` helper drives both the operator-side `messages.warning` (above) and this public caution — the rule is defined once and read from the public-profile view (or a `{% load %}` template tag that delegates to the helper) so both surfaces stay in sync. Visual treatment: warm-yellow caution palette (the same `#FBF1D6` / `#E8D58A` / `#6B5418` triplet used for the profile-edit warning banner) rendered as a compact panel, NOT inside the dark `sageDeep` sticky card (color contrast). Heading row uses a `⚠` glyph (decorative — `aria-hidden="true"`) plus the leading sentence; the cautionary instruction renders as the body. The caution is read by every viewer of `/p/<username>/`, including the owner — that's intentional, since the owner already sees the operator-side warning at save time and a permanent reminder doesn't hurt.
- The caution does NOT block the click. The "Schedule with me →" button still renders and still opens the third-party URL in a new tab with the standard outbound-link attributes. The caution is informational, not an interstitial.
- The caution does **not** apply to `feedback_url` — feedback is intentionally allowlist-free (the user asked for "any link") and visitors are already framed by the page that the form is anonymous third-party-hosted feedback.

**Feedback URL has no allowlist** — the user explicitly wants "any other link" supported. Helper text on the form is the only guardrail:
> `Optional. A Google Form, Microsoft Form, or any link where people can send you anonymous feedback. Visitors will see a "Send anonymous feedback" button on your public profile. Must start with https://`

**Profile-edit form ordering:** feedback link sits **directly under** the scheduling link, since the two are conceptually paired (booking vs. feedback contact).

**Empty `feedback_url` is fine** — it's optional and does NOT affect directory inclusion (`scheduling_url` does).

> **Site-level feedback (out of v1 scope).** The user's wording — "where people can submit anonymous feedback to him" — naturally reads as per-profile since "him" varies. If they later clarify they wanted a single site-wide feedback link in the footer, it's a ~30-minute add (a `SiteSettings` singleton with a `feedback_url` and a conditional footer link). Confirm with the user before building both.

### Notifications — none

**v1 sends ZERO outbound email.** No booking notifications (offloaded to Calendly etc.). No signup confirmation. No welcome mail. No password reset email. No 500-error notification to `ADMINS`. Nothing. The decision is explicit and load-bearing: it removes an entire class of deploy-day failure (deliverability, DKIM/SPF/DMARC, sender-domain alignment, spam-classification at iCloud) and an entire class of code path (template rendering, SMTP config, retry semantics).

**Defensive email backend.** Set `EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"` in **every** settings module (base, dev, prod, test). The locmem backend silently captures into `django.core.mail.outbox` instead of sending. If a future code path or third-party package accidentally calls `mail.send_mail(...)`, it fails closed (memory-only) instead of going out. A Phase 1 test asserts `len(mail.outbox) == 0` after registration, login, profile save, and the operator's `reset_password` command — proves no surprise email-sending code paths exist.

**No email-related URL patterns.** Do not include `django.contrib.auth.urls` wholesale (it ships `password_reset/`, `password_reset/done/`, `reset/<uidb64>/<token>/`, `reset/done/`). Mount only the four routes v1 actually needs: `login/`, `logout/`, `signup/` (custom view), and that's it. No `password_reset` URL — there is no self-serve recovery path.

**Forgot-password recovery is operator-only.** A member who forgets their password contacts the operator out-of-band (the channel is whatever the community uses — WhatsApp, in person, etc.; documented in the privacy notice). The operator runs the `reset_password` management command (see "Operator README"). The user receives a temporary plaintext password from the operator out-of-band, logs in with it, and is prompted to set a new one on next visit (the "force password change" prompt is a `Profile.must_change_password` boolean cleared after the next successful change-password POST — see "Database Models").

### Verified status — badge-only

**`Profile.is_verified`** is a boolean (default `False`) controlled exclusively by an operator with database/admin access. Members cannot self-verify. The flag controls **only the rendering of a "Verified" badge** next to the member's name in the directory card and on the public profile page. It does **NOT** gate directory inclusion, profile-page visibility, or anything else — an unverified profile with a scheduling URL is publicly listed exactly like a verified one, just without the badge.

**Why a manual flag.** A community directory of real people benefits from a lightweight signal that the operator has personally vouched for a member's identity and scope-fit. Visitors browsing the directory can see at a glance which providers carry that endorsement and which do not, without anyone being hidden from view. v1 keeps this lightweight (no review queue, no audit log, no automated approval workflow) — just a flag the operator flips.

**How to flip the flag.** Two equivalent paths, documented in `README.md` (see "Operator README"). v1 has **no Django admin** (see "No Django admin" under Security) — every operator action runs through `manage.py`:
1. **Management command** (preferred): `python manage.py verify_user <email>` (toggles to `True`; pass `--unverify` to flip back).
2. **Django shell:** `python manage.py shell -c "from directory.models import Profile; Profile.objects.filter(user__email__iexact='...').update(is_verified=True)"`. Or `manage.py dbshell` for a raw SQL update on `directory_profile`.

**Visibility behavior.**

| State | Public directory | `/p/<username>/` (logged-out viewer) | `/p/<username>/` (owner viewing self) |
|---|---|---|---|
| `is_verified=False`, no scheduling URL | hidden | 404 | 200 + banner: *"Add a scheduling link to appear in the directory."* |
| `is_verified=False`, scheduling URL set | listed (no badge) | 200 (no badge) | 200 (no badge) |
| `is_verified=True`, no scheduling URL | hidden | 404 | 200 + banner: *"Add a scheduling link to appear in the directory."* |
| `is_verified=True`, scheduling URL set | listed (badge) | 200 (badge) | 200 (badge, no banner) |

The 404 path for profiles with no scheduling URL still applies — there's no useful page to render without a "Schedule with me" target — and never reveals that an account exists at that username (same enumeration-resistance as before, narrower in scope now).

**Verified badge rendering.** A small pill — *"✓ Verified"* (or equivalent SVG icon + label) — sits next to `display_name` on:
- Each directory card (right of the name, above the bio snippet).
- The public profile page header (right of the `<h1>` `display_name`).
Render only when `profile.is_verified=True`. Unverified profiles render the name with no badge and no placeholder — no "Unverified" or "Pending" text anywhere visitor-facing; absence is the signal. A `tooltip`/`title` on the badge reads *"Identity verified by the operator."* Style is a low-key positive accent (e.g., emerald-50 background, emerald-700 text) — readable but not loud, since the directory aim is to surface everyone equally.

**Owner self-view.** Verified or not, the profile page renders for the owner with the same content the public sees. There is no "your profile is awaiting verification" banner — the absence of the badge is the signal, and verification is operator-discretionary, not a step the user "completes." The only owner-banner case left is the no-scheduling-link case (covered in the table above and in the Phase 2 owner-exception logic). If the user later asks for a richer "how to request verification" affordance, the natural place is the `/settings/` page — out of v1 scope.

---

## Technical Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5.x (Python 3.12+) |
| Database | PostgreSQL (production), SQLite (local dev) |
| Frontend | Django templates + Tailwind CSS — built via the **standalone Tailwind CLI binary** at deploy time (no Node.js in runtime or build image) |
| Static files | **WhiteNoise** (compressed + far-future-cached, runs in the web process) — no S3/CDN needed on Render free |
| Auth | Django built-in auth (`django.contrib.auth`) + custom `EmailAuthBackend` + custom `PepperedPBKDF2Hasher`; client-side password hashing on registration & login forms (see "Security → Password hashing") |
| Email | **None.** `EMAIL_BACKEND = locmem` everywhere as a defensive no-op (see "Notifications — none"). v1 sends zero outbound email. |
| Forms | `django-crispy-forms` + `crispy-tailwind` (see "Forms setup" below) |

**No email backend.** v1 ships with `EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"` set in `settings/base.py` (inherited everywhere — base, dev, prod, test). The backend silently captures any `mail.send_mail()` calls into in-memory `mail.outbox` instead of sending. Rationale and the test that asserts `mail.outbox` stays empty in normal flows are in "Notifications — none". Do **not** override this to `smtp.EmailBackend` in `prod.py` — there is no outbound mail in v1.

**Forms setup** — `django-crispy-forms` does NOT ship the Tailwind pack on its own:
```bash
pip install django-crispy-forms crispy-tailwind
```
```python
INSTALLED_APPS = [..., "crispy_forms", "crispy_tailwind"]
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"
```

### Why this stack
- Django gives you auth, ORM, forms, management commands out of the box — fast to ship. (v1 deliberately omits Django's admin; see "No Django admin (operator workflow)".)
- HTMX was in the prior plan to power booking interactions; with booking gone, the directory is essentially static pages plus a search form, so HTMX is **not** included in v1. Add it later only if directory filtering needs to feel live.
- PostgreSQL is free on most hosts and handles the simple directory queries easily

### Things deliberately removed from v1 (compared to the prior plan)
These are all genuinely unnecessary once scheduling is offloaded; they are listed so the change is auditable and so v2 can pick them back up:

- `zoneinfo`-based slot scheduling and the site-wide ET render layer (Calendly shows times in the visitor's own zone)
- DB-backed email outbox and `flush_email_outbox` management command
- Render Cron Job / external pinger for outbox flushes

### Project layout (Django apps)

Authoritative mapping so every reference in this plan resolves to a real path. All app code lives under `apps/` (Python package with `__init__.py`); add `BASE_DIR / "apps"` to `sys.path` in `settings/base.py` so app labels stay short:

| App label | Path | Owns |
|---|---|---|
| `users` | `apps/users/` | `RESERVED_USERNAMES`, registration form & view, login form (email-based) & `EmailAuthBackend` (`backends.py`), custom password hasher `PepperedPBKDF2Hasher` (`hashers.py`), client-side hashing JS module (`apps/users/static/users/auth-hash.js`), `pre_save` signal lowercasing `username`/`email`, `post_save` signal creating `Profile`. `AppConfig.ready()` imports both signal modules. Management commands under `apps/users/management/commands/`: `create_user.py` (account bootstrap with client-side hashing applied; replaces `createsuperuser`), `reset_password.py` (operator forgot-password recovery), `verify_user.py` (toggle `Profile.is_verified`). **No `admin.py` files anywhere** — v1 has no Django admin (see "No Django admin (operator workflow)"). |
| `directory` | `apps/directory/` | `Profile`, `ServiceCategory`, `ProviderService` models; profile-edit view at `/settings/`; public profile view at `/p/<username>/`; directory list view; category-seed data migration; URL validators (`validate_outbound_https_url`, scheduling-host allowlist check). |
| `security` | `apps/security/` | `middleware.NoIndexHeaderMiddleware`, `middleware.CSPMiddleware`, honeypot mixin, signed-timestamp helper, `robots.txt` view + templates. |
| `pages` | `apps/pages/` | Static templates: home (if it's not the directory itself), privacy, terms, custom `404.html` / `500.html`, and the shared `base.html` other apps' templates extend. All under `apps/pages/templates/`. |
| `config` | `config/` (NOT under `apps/`) | Django project package: `settings/{base,dev,prod,test}.py`, root `urls.py`, `wsgi.py`, `asgi.py`. |

The "user app" referenced throughout this plan is `apps.users`. The "security app" referenced under "Middleware order" is `apps.security`. Anywhere this plan says `apps.<x>.<y>`, that path is canonical — do not relocate without updating every cross-reference.

---

## Security

This section is the single source of truth for the v1 attack surface and the protections applied. URL-validator and outbound-link rules live with their fields under "Public Profiles & Discovery"; everything else lives here.

### Middleware order (canonical)

`MIDDLEWARE` in `settings/base.py`, in this exact order. WhiteNoise's docs are explicit that it runs immediately after `SecurityMiddleware`; the custom CSP middleware runs **last** so it sees every response (including WhiteNoise's static-file responses and Django's auth redirects):

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.security.middleware.NoIndexHeaderMiddleware",  # only effective when SITE_IS_PRODUCTION is unset
    "apps.security.middleware.CSPMiddleware",
]
```

Notes:
- `WhiteNoiseMiddleware` MUST be in slot 2, immediately after `SecurityMiddleware`. WhiteNoise's docs are explicit: anything earlier means `SECURE_SSL_REDIRECT` doesn't apply to static-file requests; anything later means request-processing middleware runs for static-file URLs (wasted work, and `CommonMiddleware`'s `APPEND_SLASH` can mangle static paths). Compression itself is governed by the `STORAGES["staticfiles"]["BACKEND"]` setting (`CompressedManifestStaticFilesStorage`), not the middleware position.
- `CSPMiddleware` is last so the `Content-Security-Policy` header is attached to every response — including WhiteNoise's static-file responses, the auth-redirect 302s, and Django's debug-disabled 404/500 pages.
- `NoIndexHeaderMiddleware` is the non-prod `X-Robots-Tag: noindex, nofollow` setter (see "Robots / SEO"); it short-circuits to a no-op when `SITE_IS_PRODUCTION=1`.

### Public POST endpoints (and how they're protected)

Registration and login are the only unauthenticated POST endpoints in v1 (no password-reset URL — operators handle forgot-password via management command, see "Notifications — none"). v1 protects them with honeypot + signed-timestamp, not full rate-limiting middleware.

**Per-endpoint protection matrix**

| Endpoint | Honeypot | Min-submission-time (signed timestamp) | Notes |
|---|---|---|---|
| Registration | yes | yes (≥2s, ≤1 day) | |
| Login | yes | **no** | A returning user with autofill submits in <1s; rejecting is hostile. No `django-axes` either — per-email lockouts can be weaponized to lock out real users. |

**Honeypot implementation**

- **Field name:** non-semantic, e.g. `nickname_confirm` or `extra_info`. **Do NOT use `website`/`homepage`** — Chrome and Safari autofill these from the user's profile and would trip the trap for real users.
- **Visual hiding:** a `.honeypot` class in the compiled Tailwind stylesheet:
  ```css
  position: absolute; left: -10000px; width: 1px; height: 1px; opacity: 0;
  ```
  Keep this in the external stylesheet so the strict CSP (`style-src 'self' ...`, no `'unsafe-inline'`) doesn't have to allow inline styles.
- **Accessibility approach (v1 ships option a):**
  - **Option (a) — what v1 ships.** Attributes on the input: `autocomplete="off"`, plus a visible `<label>` reading `Leave this field empty.` Do **not** set `aria-hidden`. Do **not** set `tabindex="-1"`. The field stays in the tab order and the screen-reader tree; a real user who reaches it reads the label, leaves it blank, and tabs past. (Confirmed downstream by the focus-ring note under "Accessibility": "The honeypot input itself stays focusable (no `tabindex='-1'` per option (a))".)
  - **Option (b) — rejected.** `aria-hidden="true"` + `tabindex="-1"` + `autocomplete="off"` + no label. Removes from the accessibility tree entirely; rejected because option (a) is already adequate without surprising AT users.
  - **Do not mix:** `aria-hidden="true"` + a screen-reader-visible label is contradictory.
- **Min-submission-time:** server-issues a `django.core.signing`-signed timestamp into a hidden field on GET. On POST, decode and reject if elapsed time is `< 2s` or `> 1 day`. Never trust a client-side timer.
- **Rejection policy:** if the honeypot is non-empty OR the timestamp is out of bounds, reject. Same field name and rules everywhere so the test helper is a one-liner. **What "reject" looks like:** raise a generic `ValidationError` attached to a non-field error (`form.add_error(None, "...")`) with deliberately bland copy — e.g., `"Submission could not be processed. Please try again."` Do **not** name the honeypot field, do **not** mention the timer, do **not** return a different status code than a normal validation failure. The whole point is that a bot can't tell its trap-tripping submissions apart from a regular validation error; revealing the trip rate-limits us instead of the bot.

**If real abuse appears post-launch**, add `django-ratelimit` with the DB cache backend. Intentionally not a v1 dep.

### Content Security Policy (CSP)

v1 keeps CSP minimal and does **not** install `django-csp` — instead, set CSP via a single custom response middleware (`apps/security/middleware.py:CSPMiddleware`) that sets `response["Content-Security-Policy"]` on every response unless one is already set. Position is fixed by the middleware-order list above (last). Auditable in one place; ~15 lines. The policy:

```
default-src 'self';
img-src 'self' data:;
style-src 'self' https://fonts.googleapis.com;
font-src 'self' https://fonts.gstatic.com;
script-src 'self';
connect-src 'self';
frame-ancestors 'none';
form-action 'self';
base-uri 'self';
```

Rationale: design loads fonts from Google Fonts (`fonts.googleapis.com` for the CSS and `fonts.gstatic.com` for the woff2 files); everything else is same-origin. **No `'unsafe-inline'`** — the Tailwind compiled stylesheet is fetched as a same-origin file, not inlined. If a future feature genuinely needs an inline `<style>` or `<script>`, switch to per-request nonces rather than allowing `'unsafe-inline'` blanket. `frame-ancestors 'none'` is redundant with `X_FRAME_OPTIONS = "DENY"` but defense-in-depth.

### Password hashing (client-side + server pepper)

User-supplied passwords are **never sent to the backend in plaintext**. The registration and login forms hash the password in the browser before submit; the server then re-hashes that value with a secret pepper before storing/comparing. Two layers, two distinct secrets.

**Tradeoff acknowledgment.** Under TLS, plaintext-over-the-wire is already protected from a passive network attacker, so client-side hashing is debated as "adds complexity for marginal gain" by some. The user explicitly asked for it, and it does provide genuine defense-in-depth: a TLS-terminating proxy compromise, a misconfigured upstream that logs request bodies, or an XSS-injected script that grabs form values pre-submit all see only the derived value. The **server-side pepper** is the layer with the largest measurable benefit — a database compromise that doesn't also leak the pepper makes offline cracking effectively infeasible.

**Client side — `apps/users/static/users/auth-hash.js`**

A small ES module loaded on registration, login, and change-password pages. On form submit:
1. Read the password input value and the email input value (lowercased + trimmed) — email is the per-user salt.
2. Compute `clientHash = PBKDF2-SHA256(password, salt=utf8(email), iterations=100000, dkLen=32)` via `window.crypto.subtle.deriveBits` / `importKey` (Web Crypto API; ships with every modern browser, no library needed).
3. Hex-encode the 32 output bytes.
4. Replace the password input's value with the hex string.
5. Submit the form.

The plaintext never leaves `auth-hash.js`'s scope. The form's `name="password"` field carries the hex hash. The CSP allows this script because it's loaded from `'self'`. **Browsers without Web Crypto are not supported** (this is every browser since ~2017; degrade-gracefully is not a v1 concern).

**Server-side hash shape validation.** For registration and change-password forms, reject any submitted password value that does not match `^[a-f0-9]{64}$` with a clean form error. For login, treat non-matching values as invalid credentials (same generic error). This prevents plaintext submissions when JS hashing is bypassed or disabled.

**Salt = email rationale.** A static salt would let pre-computation attacks build rainbow tables once. A server-issued salt requires an extra round-trip and creates an email-enumeration oracle (different responses for known/unknown emails). Using `email.toLowerCase().trim()` as the per-user salt requires no extra request and binds the hash to the email — sufficient for v1 since emails don't change post-registration. If email-change is ever added, all client hashes for that user invalidate at the same time the email does (acceptable: forced re-login).

**Server side — `apps/users/hashers.py:PepperedPBKDF2Hasher`**

```python
import hmac, hashlib
from django.contrib.auth.hashers import PBKDF2PasswordHasher
from django.conf import settings

class PepperedPBKDF2Hasher(PBKDF2PasswordHasher):
    algorithm = "peppered_pbkdf2_sha256"

    def encode(self, password, salt, iterations=None):
        peppered = hmac.new(settings.PEPPER.encode(), password.encode(), hashlib.sha256).hexdigest()
        return super().encode(peppered, salt, iterations)

    def verify(self, password, encoded):
        peppered = hmac.new(settings.PEPPER.encode(), password.encode(), hashlib.sha256).hexdigest()
        return super().verify(peppered, encoded)
```

Wired in `settings/base.py`:

```python
PASSWORD_HASHERS = ["apps.users.hashers.PepperedPBKDF2Hasher"]
```

**`PEPPER` is a 64+ char env var.** Generate via `python -c "import secrets; print(secrets.token_urlsafe(64))"`. Set in the Render dashboard. Startup assertion in `prod.py`: `len(PEPPER) >= 32` and not equal to the dev placeholder. **Rotating `PEPPER` invalidates every stored password** — every user must go through the operator forgot-password flow. Treat it as a one-time-set value; document in the runbook.

**Compatibility with Django's auth machinery.** `User.set_password()`, `check_password()`, and `authenticate()` all delegate to `PASSWORD_HASHERS[0]` — no other code changes needed. `createsuperuser` and `User.objects.create_user(password=...)` would store the peppered hash of *the value passed in*, which is plaintext — **use `manage.py create_user` instead** (see below). v1 has no admin password-change form to worry about.

**Why every account-creation path goes through `manage.py create_user`.** The login form sends `clientHash`. If an account's stored password was hashed from *plaintext* (because someone ran `User.objects.create_user(password="temp")` directly in a shell or `set_password("temp")`), then `check_password(clientHash, stored_hash)` fails — the values don't match. Fix: `apps/users/management/commands/create_user.py` reads plaintext from a `getpass()` prompt, applies the same PBKDF2-SHA256 derivation as the JS (using the email as salt), then calls `user.set_password(client_hash)`. The result is consistent with what the public form would store. Same pattern for `reset_password.py`. Note that `createsuperuser` is **not used in v1** (there is no Django admin to make a superuser of); the README documents `manage.py create_user` as the only account-creation tool.

**No Django admin.** v1 ships with **no Django admin panel**. `django.contrib.admin` is not in `INSTALLED_APPS`; no `/admin/` URL is mounted. There is no `/admin/login/` form to harden against the plaintext-vs-client-hash mismatch — the problem doesn't exist because the form doesn't exist. All operator actions (verify a user, deactivate, hard-delete, inspect data) run through `manage.py shell`, `manage.py dbshell`, or the three custom management commands (`create_user`, `verify_user`, `reset_password`). See "No Django admin" under Security → Operator workflow, and the README's operator quick reference.

**Password change (in-app).** A logged-in user changing their password posts to `/settings/password/`. The form has `current_password` and `new_password` inputs; `auth-hash.js` hashes both before submit (using the user's email as salt for both — same algorithm as login/registration). Server checks `user.check_password(current_hash)`, then calls `user.set_password(new_hash)`. Clears `Profile.must_change_password` if it was set by an operator reset.

### No Django admin (operator workflow)

v1 deliberately omits Django's admin. Rationale:
- Removes the `/admin/login/` plaintext-password surface (the form posts plaintext directly to `authenticate()`, which is incompatible with v1's client-side-hashing rule without a custom hashing-aware admin form — extra code, extra chance of a divergent code path that silently ships plaintext).
- Removes the `staff_required` / `is_superuser` permission cliff that's easy to misconfigure.
- Operator actions in v1 are few and infrequent enough that a CLI is fine. Adding admin back is a later option (track as Future Considerations).

**Operator-only access path:** Render's web shell (or any other shell tunneled into the running container). Render authenticates this at the platform level (the operator's Render account). From the shell, every operator action reduces to one of these:

| Operator action | Command |
|---|---|
| Create the operator's own account | `python manage.py create_user <email>` (interactive plaintext prompt; never `createsuperuser`) |
| Verify a user (publish to directory) | `python manage.py verify_user <email>` (or `--unverify` to hide) |
| Reset a forgotten password | `python manage.py reset_password <email>` (interactive prompt) |
| Deactivate an account | `python manage.py shell -c "from django.contrib.auth import get_user_model; get_user_model().objects.filter(email__iexact='...').update(is_active=False)"` |
| Hard-delete an account | `python manage.py shell -c "from django.contrib.auth import get_user_model; get_user_model().objects.filter(email__iexact='...').delete()"` (FK cascades to Profile + ProviderService) |
| Inspect a profile | `python manage.py shell` then `Profile.objects.get(user__email__iexact='...')` — pretty-print fields, services, etc. |
| Browse data | `python manage.py dbshell` for raw SQL against `directory_profile` / `directory_providerservice` / `auth_user` |

The README publishes these commands verbatim so the operator does not improvise.

**`is_staff` and `is_superuser` are unused in v1.** They remain on `auth.User` (Django default) but no view, decorator, or middleware checks them. Every authenticated user is a regular member. If admin is ever re-introduced, the operator account flips `is_staff=True` via shell at that point.

---

## Accessibility

A directory of community members will be read by people on phones, on screen readers, and on low-contrast displays. v1 doesn't need a full WCAG audit, but the following are non-negotiable from launch:

- **Color contrast (warm-sand palette).** The Garden palette pairs `ink` `#1F2A24` on `bg` `#F5EFE3` (passes WCAG AA for normal text). Watch the soft tokens:
  - `inkSoft` `#5C6660` on `bg` `#F5EFE3` — passes AA for normal text. Use for secondary copy.
  - `inkMute` `#8B928C` on `bg` `#F5EFE3` — fails AA at body size (~3.4:1). Use **only** for large/bold meta text (≥18px or ≥14px bold), never for paragraph copy or form labels.
  - The dark sticky CTA card (`sageDeep` `#3F5D4A` bg, `bgCard` text) passes AA comfortably.
  - The warning banner (`#FBF1D6` bg, `#6B5418` body, `#3F3208` heading) passes AA.
  - When in doubt, run the foreground/background pair through a contrast checker before merging.
- **Focus rings on every interactive element.** Tailwind's default `focus:outline-none` strips the browser ring; if you use it, **must** be paired with `focus-visible:ring-2 focus-visible:ring-sage-deep focus-visible:ring-offset-2`. Applies to: links, buttons, form fields, category chips, and pagination links. The honeypot input itself stays focusable (no `tabindex="-1"` per option (a)) but is positioned off-screen — it does not need a styled ring, and a real screen-reader user reaching it will hear the "Leave this field empty" label and tab past. Keyboard-only navigation through every screen is a Phase 2 acceptance check.
- **Alt text policy.**
  - The wordmark SVG logo: `aria-label="Sadaqa Jariyah"` on the `<svg>`, decorative inner shapes get `aria-hidden="true"`.
  - Avatar tiles in the directory (color-block + initials, no photos in v1) are decorative — wrap in `aria-hidden="true"` and rely on the adjacent name text.
  - No user-uploaded images in v1, so no per-record alt-text fields are needed.
- **Form semantics.** Every input has a visible `<label>` (no placeholder-only inputs). Errors render adjacent to the field with `aria-describedby` wiring crispy-tailwind already produces — don't override the template pack to remove it. Required fields are marked with both `required` and a visible `*` (the asterisk gets an `aria-hidden="true"` so screen readers don't say "star"). crispy-tailwind's default field template already inserts an asterisk for required fields — do not add a second one in the surrounding template; if its asterisk lacks `aria-hidden`, override that single template snippet rather than wrapping the whole field.
- **Motion / language.** No autoplay/animation in v1 beyond CSS hover transitions. Set `<html lang="en">` on the base template; the Arabic wordmark line gets its own `lang="ar" dir="rtl"` wrapper (per design-notes §3).
- **Skip link.** A visually-hidden-until-focused `Skip to main content` anchor at the top of the base template, jumping to `#main`. Tailwind utilities: `sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 ...`.

These are template-level concerns; the Phase 2 styling pass is the right time to audit them.

---

## Database Models

### Schema

```
User (Django built-in)
  ├── username  CITEXT/lower-indexed, see "User Accounts"; stored already-lowercased
  ├── email     required, unique on lower(email); stored already-lowercased
  ├── password, is_active
  └── one-to-one → Profile (created via post_save signal; related_name="profile")

Profile
  ├── user                  OneToOneField(User, on_delete=CASCADE, related_name="profile")
  ├── first_name            CharField(max_length=60, blank=True, default=""); form-level required, min_length=1; sanitized on save
  ├── last_name             CharField(max_length=60, blank=True, default=""); OPTIONAL — form-level not required; sanitized on save
  ├── bio                   TextField(blank=True, default=""); form-level min_length=20, max_length=1000; sanitized on save
  ├── scheduling_url        URLField(max_length=500, blank=True, default=""); non-empty required for directory inclusion
  ├── feedback_url          URLField(max_length=500, blank=True, default=""); OPTIONAL, does not affect directory
  ├── is_verified           BooleanField(default=False); operator-controlled, badge-only (see "Verified status — badge-only")
  ├── must_change_password  BooleanField(default=False); set by operator's reset_password command, cleared on next successful change-password POST
  ├── created_at, updated_at  (auto_now_add / auto_now)
  └── services              M2M(ServiceCategory, through="ProviderService", related_name="profiles")

ServiceCategory
  ├── name              unique, max 60
  ├── slug              unique, max 60
  ├── sort_order        int, default 0 (admin-editable directory ordering)
  └── is_other_freetext boolean, default False; exactly one row True (constraints below)

ProviderService (M2M through table)
  ├── profile             FK Profile, on_delete=CASCADE
  ├── category            FK ServiceCategory, on_delete=PROTECT
  ├── is_freetext         boolean, default False; denormalized copy of category.is_other_freetext
  └── custom_description  CharField, max 280, blank=True; required iff is_freetext=True; OPTIONAL elaboration on every other row
```

### Field-level rules and rationale

**`Profile.user` cascade:** deleting the user removes the profile and (via the FK on `ProviderService.profile`) all its services.

**`Profile.first_name` / `last_name`** live on `Profile` rather than `User.first_name/last_name` so all sanitization, length, and display rules sit beside the bio/services on the same model. `last_name` is **optional** — a member who prefers not to publish a last name leaves it blank; the public profile renders just `first_name`. `display_name` (computed property: `(first_name + " " + last_name).strip()`) is the only thing templates and admin `__str__` should call — no ad-hoc f-strings that risk a trailing space.

**All four free-text fields are `blank=True` at the model layer** (`first_name`, `last_name`, `bio`, plus the URLs and `custom_description`) so the `post_save` signal can call `Profile.objects.create(user=instance)` without an `IntegrityError` on registration. The "required" / min-length requirements are enforced at the **form layer only** (`MinLengthValidator(1)` on `first_name`, `MinLengthValidator(20)` on `bio`, both also `required=True` in the `ModelForm`; `last_name` stays `required=False`). A freshly-registered user has an empty profile until they save the edit form — that is intentional and matches design-notes §4.7 (the "Owner — empty" screen). The directory queryset implicitly excludes empty profiles via `scheduling_url != ""` (the form requires `first_name` and `bio` whenever it accepts `scheduling_url`, so a non-empty `scheduling_url` implies a non-empty `first_name` and `bio`).

**`Profile.is_verified` defaults to `False`** at the model layer. Only operator paths (`verify_user` management command, `manage.py shell`, `manage.py dbshell`) can flip it. No view writes to this field. A Phase 1 test asserts the profile-edit form has no `is_verified` field on its rendered output and rejects a crafted POST that includes `is_verified=true`.

**`Profile.must_change_password`** is set by the operator's `reset_password` command and cleared by the user's next successful change-password POST. When `True`, the `/settings/` view (and any other authenticated view) redirects to `/settings/password/` until cleared. Implementation: a thin middleware (or a request-decorator on the relevant views) that short-circuits to the change-password page if `request.user.is_authenticated and request.user.profile.must_change_password and request.path != "/settings/password/" and not request.path.startswith("/accounts/logout")`.

**`Profile.scheduling_url` length:** Django's `URLField` default of 200 isn't enough for some Calendly/Google links with query params; we use 500. Same length on `feedback_url` for consistency.

**`Profile.created_at`** is rendered as the directory's "Member since" date (design-notes §4.3).

**`User → Profile` post_save signal**
- Both signal modules (the `pre_save` lowercaser from "Username storage normalization" and this `post_save` profile-creator) MUST be imported from the user app's `AppConfig.ready()` — a signal defined but never imported is silently dead, and the first sign is a `RelatedObjectDoesNotExist` on `user.profile` after `manage.py create_user`, or a mixed-case username sneaking through. Phase 1 has regression tests for both.
- The handler must guard on `if created:` — `post_save` fires on every update too, and unguarded `Profile.objects.create(user=instance)` raises `IntegrityError` on the OneToOne the second time the user is saved.
- Profiles are NEVER created by explicit `Profile.objects.create(...)` calls in view code or registration form `save()` — always via the `post_save` signal triggered by `User.save()`. This way `manage.py create_user`, shell `User.objects.create(...)`, and any other backdoor write path all get a Profile too. (The signal does fire during the registration request cycle — that's intended; the rule is just "don't duplicate the create call in the view.")

**`ServiceCategory.is_other_freetext` — exactly one True row, enforced three ways:**
1. Partial `UniqueConstraint` so the DB rejects a second `True` row:
   ```python
   UniqueConstraint(
       fields=["is_other_freetext"],
       condition=Q(is_other_freetext=True),
       name="uniq_service_category_is_other_freetext_true",
   )
   ```
   Same partial-index portability caveat as `ProviderService` — see "Constraint portability (Postgres vs SQLite)" below; tests for this constraint are Postgres-only in CI.
2. Seed data migration creates the singleton "Other" row (`slug="other"`, `name="Other"`, `is_other_freetext=True`).
3. v1 has no admin or write-form for `ServiceCategory` (see "No Django admin (operator workflow)"). New categories ship as data migrations; the singleton row is created by the seed migration and never modified. If admin is ever re-introduced, the future form must prevent toggling another row `True` while one already exists, prevent toggling the singleton `False`, and prevent deleting it.

**`ProviderService.is_freetext`** is denormalized from `category.is_other_freetext`. We denormalize because Postgres CHECK constraints and partial unique indexes can only reference columns of the same row. Sync via:
- A `ProviderService.save()` override that copies the flag from the selected category. It does **not** clear `custom_description` — the field is optional on every row and the user's text is preserved across category changes.
- A data migration that backfills it (no-op on first deploy).

**`ProviderService.custom_description` semantics**

The field is **optional on every row**. For predefined categories (Mentoring, Counseling, etc.) it's an *elaboration* — the provider describes their flavor of that service so visitors deciding whether to book understand more (e.g., "I mentor early-career engineers preparing for system-design interviews"). For "Other" rows it's the *de-facto title* of the custom service (since "Other" is just a bucket).

Enforced at two layers (model `clean()` + form `clean()`) and one DB `CheckConstraint`:

```python
CheckConstraint(
    check=Q(is_freetext=False) | ~Q(custom_description=""),
    name="freetext_requires_description",
)
```

This is the only constraint — there is **no** `non_freetext_forbids_description` constraint, because non-freetext rows are now allowed (and encouraged) to carry descriptions. A previous draft of this plan had that second constraint; it has been deliberately removed.

The Q form is portable across Postgres and SQLite. **Limitation:** `~Q(custom_description="")` only catches the empty string, not whitespace-only (`"   "`). Whitespace is handled at the form layer (`clean_custom_description` strips and re-validates) and by the standard text-sanitization rules (collapse + trim). By the time an "Other" row reaches the DB, whitespace-only is already `""` — and the form-layer required check rejects it before then with a clean error. A `length(trim(custom_description)) > 0` CHECK would be more defensive but doesn't run on SQLite, so v1 stays portable.

**`ProviderService` uniqueness — predefined categories: at most one per profile; "Other": multiple allowed**

```python
UniqueConstraint(
    fields=["profile", "category"],
    condition=Q(is_freetext=False),
    name="uniq_profile_category_nonfreetext",
)
```

Do NOT use `Meta.unique_together` — it can't be made conditional.

### Constraint portability (Postgres vs SQLite)

Django translates partial `UniqueConstraint` to a Postgres partial index. On SQLite the same expression compiles to an unconditional unique index — fine for v1 tests since no fixture creates two rows for the same predefined category, but **partial-condition constraint behavior differs**.

Implications:
- The test suite runs on **Postgres in CI** (see "CI") so the Phase 1 `IntegrityError` tests reflect production behavior.
- Local SQLite dev is fine for everything except the partial-constraint tests, which are skipped via `@pytest.mark.skipif(connection.vendor != "postgresql", ...)`.

### Service category lifecycle

- **Seeded via a data migration** (not a fixture) so production deploys auto-create them on first `migrate`.
- Migration is **idempotent**: use `update_or_create` keyed on `slug`. Re-running on an existing DB doesn't crash; adding a new category is just another data migration.
- **Categories are immutable in v1.** Never rename, never delete from the DB. If one becomes obsolete, add an `is_active=False` flag (schema change deferred until needed) and filter it out of form choices. `DELETE FROM servicecategory` would cascade-fail anyway because `ProviderService.category` is `PROTECT`.
- **The `is_other_freetext` row is locked:** once seeded, admin form prevents deleting it AND prevents toggling the flag off.

---

## Hosting & Deployment

### Recommended: **Render.com** (free tier)

- Independent platform (no defense industry ties).
- Free web service: sleeps after ~15 min idle; first visitor waits ~30s for cold start. Acceptable for a low-traffic directory.
- Auto-deploys from GitHub.
- Free Let's Encrypt SSL.

**The operator runbook**

Several items below (and in Phase 1 / Phase 3) reference "the runbook." This is a single Markdown file at `docs/RUNBOOK.md` in the repo, written during Phase 3, owned by the operator. It captures the things that are situational or sensitive enough not to belong in this plan: live values (DB-expiry window, provider SMTP creds-management approach), exact shell recipes for hard-delete and `pg_dump`/`pg_restore`, calendar-reminder schedule, the superuser-bootstrap procedure, and the search-input truncation behavior so it isn't mistaken for a bug. Plan describes what; runbook describes how-and-when.

**Free PostgreSQL — destroyed after a fixed period**

Render's free Postgres has a hard expiry. The exact window has changed over time (advertised as ~30 days at writing; was 90 days earlier). **Read it off Render's pricing page at deploy time and write the verified number into the runbook** — do not trust this document for the value.

The runbook MUST include:

1. **Calendar reminders** — at least 7 days before expiry, plus a second reminder at ~50% of the cycle as a backstop. (For a 30-day cycle: day 15 and day 23. For 90-day: day 45 and day 83.) One forgotten reminder must not cost the DB.
2. **`pg_dump` / `pg_restore` recipes** stored alongside the deploy docs. Use Render's **external** connection string (it's run from a laptop, not the internal one). Verified once by hand before launch — do not discover the restore command works during an outage.
3. **A decision point when the reminder fires:** upgrade to paid tier (~$7/mo) or rotate the free DB by restoring the dump into a fresh free instance. Either is fine as long as it's chosen, not stumbled into.

### Required Django settings for production

Every item below is non-optional. A junior dev should be able to copy this list straight into `settings/prod.py`.

**Core**
- `DEBUG = False`. Env-driven; default `False` so a missing env var doesn't ship a debug server.
- `SECRET_KEY` from env. Startup assertion in `settings/prod.py`: `len(SECRET_KEY) >= 50` and not equal to the placeholder used in `settings/dev.py`. Generate via `python -c "import secrets; print(secrets.token_urlsafe(64))"` (yields ~86 chars, comfortably above the 50-char floor); set in the Render dashboard; never commit. Rotating it logs everyone out (sessions are signed with it) — do it intentionally.
- `PEPPER` from env. Startup assertion in `settings/prod.py`: `len(PEPPER) >= 32` and not equal to the dev placeholder. Generate the same way as `SECRET_KEY`. **Rotating `PEPPER` invalidates every stored password** — every member must go through the operator forgot-password flow. Treat as one-time-set; document in the runbook. Read by `apps.users.hashers.PepperedPBKDF2Hasher`.
- `PASSWORD_HASHERS = ["apps.users.hashers.PepperedPBKDF2Hasher"]`. Single-entry list — no fallback hashers (legacy hashers would silently bypass the pepper on existing rows; v1 launches with empty DB so there are no legacy rows to migrate).
- `AUTHENTICATION_BACKENDS = ["apps.users.backends.EmailAuthBackend"]`. Single-entry list — replaces Django's default `ModelBackend` so the entire app authenticates by email rather than username.
- `ALLOWED_HOSTS = [".onrender.com", "sadaqajariyah.online", "www.sadaqajariyah.online"]`. Both apex and `www` are listed (both must accept requests); apex is canonical and `www` 301s to it (Phase 3). Set via env (comma-split) so the same code ships to staging.
- `CSRF_TRUSTED_ORIGINS = ["https://sadaqajariyah.online", "https://www.sadaqajariyah.online", "https://<service>.onrender.com"]`.

**Proxy / TLS**
- `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`. Render terminates TLS at the edge. **Only set this in `prod.py`** — in dev, Django thinks every request is HTTPS (breaks local dev) and on a misconfigured proxy chain it's spoofable via a request header.
- `SECURE_SSL_REDIRECT = True`
- `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`
- `SESSION_COOKIE_HTTPONLY = True` (Django default; assert it stays True)
- `CSRF_COOKIE_HTTPONLY = False` (Django default; must stay False so the CSRF token can be read for AJAX later)
- `SESSION_COOKIE_SAMESITE = "Lax"`, `CSRF_COOKIE_SAMESITE = "Lax"` (Django defaults; called out so they're not changed without thought — `Strict` would break inbound community links that POST through forms after a third-party-site click)

**HSTS (two-step rollout — both steps required)**
- **Day-one launch:** `SECURE_HSTS_SECONDS = 60`. The short value gives you a remote-clearable escape hatch if HTTPS misconfigures (cert renewal failure, mistaken redirect, anything). Setting `31536000` on day one and then misconfiguring HTTPS means browsers that saw the header refuse to load the site over HTTP for up to a year, with no remote clear.
- **One week post-launch:** raise to `SECURE_HSTS_SECONDS = 31536000` with `SECURE_HSTS_INCLUDE_SUBDOMAINS = True` and `SECURE_HSTS_PRELOAD = True`. Calendar reminder is in the Phase 3 acceptance criteria — do not skip.

**Other security headers**
- `SECURE_CONTENT_TYPE_NOSNIFF = True`
- `SECURE_REFERRER_POLICY = "same-origin"`
- `X_FRAME_OPTIONS = "DENY"`

**Static files**
- `STORAGES["staticfiles"]["BACKEND"] = "whitenoise.storage.CompressedManifestStaticFilesStorage"`. Django 5.x uses the `STORAGES` dict, NOT the deprecated `STATICFILES_STORAGE` string. Don't copy older snippets.

**Logging / errors**
- `LOGGING` with at least an `ERROR`-level handler to stderr so Render's log viewer captures tracebacks. Set `propagate=False` on the `django.security.DisallowedHost` logger to suppress noise from scanners hitting the IP with spoofed Host headers (not actionable).
- **No `ADMINS` mail handler.** Django emails `ADMINS` on uncaught 500s only if email actually sends; with `EMAIL_BACKEND = locmem`, those mails go nowhere. Crash visibility in v1 = **Render's log viewer + a daily check by the operator**. Document the daily-check reminder in the runbook.
- **Sentry is the v1.x add** if log-viewer-only proves insufficient. Sentry's free tier integrates with one env var (`SENTRY_DSN`) plus 5 lines in `prod.py`; it doesn't depend on the email backend, so it works under v1's no-email rule. Track as Future Considerations.

**Settings layout**
- Split: `settings/base.py`, `settings/dev.py`, `settings/prod.py`, `settings/test.py`.
- Render's start command sets `DJANGO_SETTINGS_MODULE=config.settings.prod`.
- `pytest` defaults to `config.settings.test` via a `pytest.ini` (or `[tool.pytest.ini_options]` in `pyproject.toml`) entry: `DJANGO_SETTINGS_MODULE = config.settings.test`. `manage.py test` reads `DJANGO_SETTINGS_MODULE` from the environment — set it in the developer shell or a `Makefile` target; do not let it fall through to `config.settings.dev` or `prod`.
- `manage.py` itself sets a default of `config.settings.dev` so local `runserver` works without an explicit env var.
- Avoids the "one giant settings.py with `if DEBUG:` everywhere" footgun where prod-only blocks silently run in tests.

**Pre-deploy gate**
- `python manage.py check --deploy` runs in CI on every PR and during the Render build (after `collectstatic`, so storage-related misconfigs surface too — see Phase 3).
- Fails the build on any `WARNING`-level finding not in `SILENCED_SYSTEM_CHECKS`. During the first week, `SILENCED_SYSTEM_CHECKS = ["security.W004"]` (the `SECURE_HSTS_SECONDS` warning fired because the value is 60 instead of ≥31536000). **Remove that entry from `SILENCED_SYSTEM_CHECKS` in the same PR that bumps HSTS to one year** so a future regression on the long value re-fires the warning.

**Auth redirects** (set all three; Django's defaults point at URLs that don't exist in v1)
- `LOGIN_URL = "/accounts/login/"` (Django default; confirm it stays)
- `LOGIN_REDIRECT_URL = "/settings/"` — fresh login lands on the profile-edit form. (The "Owner — empty" screen at design-notes §4.7 is a separate page rendered at `/p/<username>/` when the owner views their own profile and `scheduling_url` is unset; that screen is reached by navigation, not the login redirect. Login → `/settings/` regardless of profile state.)
- `LOGOUT_REDIRECT_URL = "/"` — logout returns home.
- Not setting these causes a 404 immediately after the very first login (Django default is `/accounts/profile/`, which doesn't exist).

### Environment variables (Render dashboard)
Junior dev checklist — every var below is set in the Render service's environment section. None are committed to the repo:

| Var | Value | Notes |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` | Render's start command relies on it |
| `DEBUG` | `False` | Default in `prod.py` is False; the env var is for explicit override |
| `SECRET_KEY` | `<64+ urlsafe chars>` | Generate per the recipe in "Required Django settings"; rotating logs everyone out |
| `PEPPER` | `<64+ urlsafe chars>` | Read by `PepperedPBKDF2Hasher`. **Rotating invalidates every stored password** — treat as one-time-set. Generate the same way as `SECRET_KEY`. |
| `DATABASE_URL` | `postgres://...` | Render auto-injects for the linked free Postgres instance; parse via `dj-database-url` |
| `ALLOWED_HOSTS` | `sadaqajariyah.online,www.sadaqajariyah.online,<service>.onrender.com` | Comma-split in settings |
| `CSRF_TRUSTED_ORIGINS` | `https://sadaqajariyah.online,https://www.sadaqajariyah.online,https://<service>.onrender.com` | Comma-split |
| `SITE_IS_PRODUCTION` | `1` (prod) / unset elsewhere | Drives `robots.txt` template choice and the `X-Robots-Tag: noindex` middleware in non-prod |
| `OPERATOR_CONTACT_EMAIL` | operator's address | Rendered in the privacy notice (deletion path). **Not** used to send mail (v1 sends none) — it's a public-facing label so members know how to contact the operator out-of-band for password reset and deletion requests. |
| `CANONICAL_HOST` | `sadaqajariyah.online` | Used if the www→apex 301 is handled in Django middleware (option b) rather than Render rewrites (option a, preferred). Not needed for any email path since v1 sends no email. |

### Required Python dependencies (`requirements.in` → `requirements.txt`)
Pin all of these with `==` in `requirements.txt`. The starting set:

- `Django` (5.x)
- `gunicorn` — production WSGI server (referenced in the Render start command in Phase 3)
- `psycopg[binary]` — Postgres driver (the modern psycopg 3 binary build; do NOT use the unmaintained `psycopg2-binary` for new projects)
- `dj-database-url` — parses `DATABASE_URL` into Django's `DATABASES` dict
- `whitenoise` — static file serving
- `django-crispy-forms` + `crispy-tailwind`
- `python-dotenv` — only loaded in `dev.py` so a `.env` file works locally; **not** imported in `prod.py` (Render injects env vars directly)
- Dev/test only: `pytest`, `pytest-django`, `pip-tools`

### Alternative: **Railway** or **Fly.io**
- Both ethical, both Django-friendly
- Railway has a $5/month free trial credit
- Fly.io has a free allowance for small apps

### Domain
**Already purchased: `sadaqajariyah.online`** — used everywhere in design copy and in `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` above. **Canonical host: `sadaqajariyah.online` (apex)**; `www.sadaqajariyah.online` 301s to it. Render's free tier provisions Let's Encrypt certs automatically; both apex and `www` must be added as custom domains in the Render dashboard so the cert covers both. The 301 itself is configured in Phase 3.

---

## Development Phases

Each phase ends with explicit acceptance criteria. A phase is not done until every box is checked.

### Phase 1: Foundation (Days 1–3)

**Build**

- **Django project setup, models, migrations.** Include the partial unique indexes and CHECK constraints described under "Database Models". Pin every dependency with `==` in `requirements.txt`, generated via `pip-tools`/`pip-compile` from `requirements.in` so transitive pins are reproducible. Unpinned deps break Render builds on transient upstream releases.
- **Auth flows.** Registration, login, change-password (logged-in only). **No password-reset URL** — operators handle forgot-password via the `reset_password` management command (per "Notifications — none"). Honeypot + min-submission-time on registration; honeypot only (no timer) on login. Per "Public POST endpoints (and how they're protected)". The registration view explicitly calls `auth_login(request, user)` after `form.save()` and returns `redirect("/settings/")` on success — `LOGIN_REDIRECT_URL` is consulted by `LoginView`, not by a custom registration view, so the redirect target is hard-coded (or read from `settings.LOGIN_REDIRECT_URL`) in the view itself.
- **Email-based login.** `apps/users/backends.py:EmailAuthBackend` is the only entry in `AUTHENTICATION_BACKENDS`. The login form has an `email` field (not `username`), and `clean_email` lowercases input. There is no `/admin/login/` to harden — Django admin is not mounted in v1 (see "No Django admin (operator workflow)").
- **Client-side password hashing.** `apps/users/static/users/auth-hash.js` runs on registration, login, and change-password. Computes PBKDF2-SHA256 of the password using the lowercased+trimmed email as salt; replaces the field value before submit. Server-side: `PepperedPBKDF2Hasher` HMACs the received value with `settings.PEPPER` then delegates to Django's stock PBKDF2 hashing. Wire `PASSWORD_HASHERS` per "Required Django settings". See "Security → Password hashing" for the full scheme.
- **Profile creation/edit view at `/settings/`:**
  - Decorated with `@login_required`. Operates only on `request.user.profile` — never accept a profile pk from URL or POST body (that's an IDOR). Always load `request.user.profile`, save to it, full stop.
  - Form includes `scheduling_url` (with soft-warning host check) and `feedback_url` (no allowlist) directly below it.
  - Service editing uses a Django **inline formset** (`inlineformset_factory(Profile, ProviderService, ...)`). The default M2M widget can't be used because `Profile.services` has an explicit `through="ProviderService"`.
  - The formset MUST be instantiated with `instance=request.user.profile` so its underlying queryset is restricted to that profile's existing `ProviderService` rows. Django then rejects any submitted `providerservice_set-N-id` that doesn't belong to that queryset — closes the IDOR where an attacker swaps in another profile's service-row PK to hijack/edit a row.
  - `custom_description` is a `ProviderService` column, edited inside the formset row. **Render the field on every row** (not just "Other" rows) — it's an optional elaboration on every category. UX hint text varies by category state: "Optional — describe your specific offering" for predefined; "Required — name your service" for "Other". The `ProviderService` ModelForm's `clean()` (i.e., the formset's child form, **not** the parent `Profile` form) handles only one rule:
    - Whenever the selected category has `is_other_freetext=True`, sanitize+collapse the description and re-validate that the result is non-empty (raise `ValidationError` if it is). Without this step, a description of `"   "` collapses to `""` after the standard whitespace pass and trips the `freetext_requires_description` CHECK constraint at INSERT — user sees a 500 instead of a clean form error.
    - There is **no** "clear `custom_description` when `is_freetext=False`" step (a previous draft had one). Non-freetext rows are now allowed to carry descriptions and the `non_freetext_forbids_description` CHECK constraint has been removed — see "Database Models → ProviderService".
  - Cap the formset at 12 rows. **`max_num=12` alone is not enough** — Django's default `absolute_max = max_num + 1000` means a crafted POST with `providerservice_set-TOTAL_FORMS=1012` is still accepted by the management form. Pass all three flags together:
    ```python
    inlineformset_factory(
        Profile, ProviderService,
        max_num=12, validate_max=True, absolute_max=12,
        ...
    )
    ```
    Without `validate_max=True` the limit is advisory; without lowering `absolute_max` to match, the management form silently accepts up to 1012.
- **No Django admin in v1.** `django.contrib.admin` is **not** in `INSTALLED_APPS`; `/admin/` is not mounted; no `ModelAdmin` classes are written. All operator actions run through `manage.py shell`, `manage.py dbshell`, or the three custom management commands below. Rationale: removes the `/admin/login/` plaintext-password surface and the staff-permission cliff, and v1's operator actions are few enough that a CLI is fine. See "No Django admin (operator workflow)" under Security for the canonical command list.
- **Operator management commands.** Three commands under `apps/users/management/commands/`:
  - `create_user.py <email>`: prompts for plaintext password via `getpass()`, applies the same PBKDF2-SHA256 derivation as the JS (using the email as salt), then calls `user.set_password(client_hash)`. **This is the only account-creation tool used in v1** — `createsuperuser` would store a hash of the plaintext, which the client-side-hashing login form can never match. Creates a regular user (not staff/superuser) since v1 has no admin and `is_staff` / `is_superuser` are unused. The operator runs `verify_user` separately to surface their own profile in the directory.
  - `reset_password.py <email>`: prompts for a new plaintext password, applies the JS-equivalent client-side hash, calls `user.set_password(...)`, and sets `Profile.must_change_password=True` so the user is forced to change it on next login. Operator tells the user the temp plaintext out-of-band; the user types it on the login form, JS hashes to the same value, server matches, then `/settings/` middleware redirects them to `/settings/password/` until they pick a new one.
  - `verify_user.py <email> [--unverify]`: flips `Profile.is_verified` to `True` (or `False` with `--unverify`). Trivial wrapper around the QuerySet update — exists so the operator has an explicit, scriptable command rather than a shell one-liner that's easy to typo.
- **Project README.** A `README.md` at the repo root, written in Phase 1 and updated as the implementation lands. Required content (terse — this is operator-facing, not marketing):
  - One-line project summary + link to `.thoughts/plan.md` and `docs/RUNBOOK.md`.
  - **Local dev setup**: `git clone`, `python -m venv .venv`, `pip install -r requirements.txt`, `cp .env.example .env`, `python manage.py migrate`, `python manage.py runserver`.
  - **Operator quick reference** (the section the user explicitly asked for). v1 has **no Django admin** — every operator action runs from a shell on the running container (Render's "Shell" tab):
    - *Creating the operator's account:* `python manage.py create_user operator@example.com` (NOT `createsuperuser` — see "No Django admin (operator workflow)"). Then `python manage.py verify_user operator@example.com` to surface the operator's profile in the directory.
    - *Verifying a user* (publishing them to the directory): `python manage.py verify_user member@example.com`. Pass `--unverify` to flip back.
    - *Resetting a forgotten password:* `python manage.py reset_password member@example.com`. The command prompts for a new plaintext password; communicate it to the user out-of-band (WhatsApp, in person, etc.); the user logs in with it and is forced to change it on first request.
    - *Deactivating an account:* `python manage.py shell -c "from django.contrib.auth import get_user_model; get_user_model().objects.filter(email__iexact='member@example.com').update(is_active=False)"`. Logs the user out on their next request (Django's `AuthenticationMiddleware` rejects `is_active=False` users) and excludes them from the directory.
    - *Re-activating an account:* same recipe with `is_active=True`.
    - *Hard-deleting an account* (privacy-notice 30-day obligation): `python manage.py shell -c "from django.contrib.auth import get_user_model; get_user_model().objects.filter(email__iexact='member@example.com').delete()"`. FK cascades handle `Profile` and `ProviderService`.
    - *Inspecting a profile:* `python manage.py shell` → `from directory.models import Profile; p = Profile.objects.get(user__email__iexact='member@example.com'); print(p.display_name, p.is_verified, p.scheduling_url)`.
    - *Raw DB access:* `python manage.py dbshell` opens a `psql` session. The relevant tables are `auth_user`, `directory_profile`, `directory_servicecategory`, `directory_providerservice`. Read-only queries (e.g., `SELECT count(*) FROM directory_profile WHERE is_verified = false;`) are safe; UPDATEs bypass model `clean()` and the form-layer sanitization rules — prefer `manage.py shell` for writes.
  - **What this README is NOT:** the deployment runbook (`docs/RUNBOOK.md`) covers Render setup, DB rotation, `pg_dump`/`pg_restore`, calendar reminders, and HSTS bump.
- **Data migration** seeding predefined `ServiceCategory` rows from `data.js`'s category list (slugs and names verbatim — see `.thoughts/design/design-notes.md` §5), including the single `is_other_freetext=True` row.
- **No self-serve account deletion in v1.** Operator-only deactivation (`User.is_active=False`) and hard-delete via `manage.py shell` recipes in the README; no cleanup machinery needed since there are no slots/bookings. FK cascades handle `Profile` and `ProviderService`.
- **Deactivation effectively logs the user out on their next request.** Django's `AuthenticationMiddleware` calls `ModelBackend.get_user(user_id)`, which returns `None` for `is_active=False` users (via `user_can_authenticate`). So a user deactivated mid-session becomes `AnonymousUser` on the next request; `@login_required` redirects them to login, and login itself rejects an inactive account. Combined with the `user__is_active=True` filter on the directory queryset, deactivation is effectively immediate for v1's surfaces — no session-purge step needed. If the project ever switches to a custom auth backend, audit that backend's `get_user` for the same `is_active` check.

**Phase 1 minimum test suite**

Use `pytest-django` (parametrize is much cleaner than `unittest` for the URL-validator matrix). Group the tests as below. The `locmem` email backend is set globally (per "Notifications — none"); tests assert `mail.outbox` stays empty in normal flows.

*URL validation*
- `scheduling_url` rejects junk schemes (`javascript:`, `data:`, `file:`, non-https), missing host, and IP literals (incl. `https://[::1]/`).
- `feedback_url` rejects the same set, via the shared `validate_outbound_https_url` helper (parametrized).
- `feedback_url` accepts blank (it's optional) and accepts an `https://` URL on a host NOT in the scheduling allowlist (no soft warning fires, since the allowlist is scheduling-only).
- `scheduling_url` on a non-allowlisted host saves successfully and triggers a `messages.warning`.

*Username & email rules*
- Registration rejects every entry in `RESERVED_USERNAMES` (parametrized).
- Registration rejects mixed-case duplicate usernames (`Ahmed` after `ahmed`) and mixed-case duplicate emails.
- Registration lowercases both username and email before save.
- `User.objects.create_user(username="MixedCase", email="Mixed@Example.com", ...)` is stored as `mixedcase` / `mixed@example.com` (regression test for the `pre_save` signal — covers non-form paths for both fields).

*Password hashing (client-side + pepper)*
- The peppered hasher round-trips: `set_password("clienthashvalue")` then `check_password("clienthashvalue", user.password)` returns `True`.
- The peppered hasher rejects mismatches: `check_password("wrongvalue", user.password)` returns `False`.
- Changing `settings.PEPPER` at runtime invalidates an existing hash (regression on the pepper actually being used).
- `manage.py create_user foo@example.com` (with stubbed `getpass()`) creates a regular user whose stored password matches what the JS would produce client-side for the same plaintext + email salt — i.e., a subsequent `client.post("/accounts/login/", {"email": "foo@example.com", "password": <client_hash>})` succeeds. (The JS-equivalent derivation lives in a test helper; `auth-hash.js` and `create_user.py` both reference the same parameters: PBKDF2-SHA256, 100k iterations, 32 byte output, hex.)
- `manage.py reset_password member@example.com` (with stubbed `getpass()`) sets `Profile.must_change_password=True`, the user can log in with the temp value, and any authenticated request other than `/settings/password/` redirects to `/settings/password/` until they POST a new password successfully (which clears the flag).
- The URL `/admin/` returns 404 (or is otherwise unrouted) — `django.contrib.admin` is not in `INSTALLED_APPS`, no admin URL is mounted. Regression for "No Django admin (operator workflow)".

*Profile lifecycle*
- Creating a `User` row produces a `Profile` row via the `post_save` signal (regression test for `AppConfig.ready()` wiring).
- Saving an existing `User` (e.g., `user.is_active = False; user.save()`) does **not** raise — guards the `if created:` branch in the signal handler.
- New profiles default to `is_verified=False`.
- Profile-edit page saves a valid scheduling URL.
- Profile-edit form rejects a POST containing `username=...`, `email=...`, or `is_verified=true` — none of those fields are editable through the form even when crafted into the request body.
- Profile-edit formset rejects a POST whose `providerservice_set-N-id` references another profile's service-row PK (IDOR regression).
- Profile-edit formset rejects a POST claiming `TOTAL_FORMS=13` (regression for `validate_max=True` + `absolute_max=12` — without both flags the management form silently accepts up to ~1012 rows).
- `first_name` is required at the form level; submitting it blank rejects with a clean form error.
- `last_name` blank is accepted; the rendered profile and `display_name` show only `first_name` with no trailing space.
- Bio under 20 chars is rejected.
- Bio with HTML tags is sanitized on save (tags stripped). Same for `first_name` and `last_name`.
- A predefined-category service row with `custom_description="I mentor early-career engineers"` saves successfully (regression on per-service descriptions being allowed for non-freetext rows).
- An "Other"-category service row with `custom_description="   "` (whitespace-only) raises a clean form error, not a `CHECK`-constraint `IntegrityError` (regression for the form-level non-empty check after sanitize).
- A predefined-category service row saved with `custom_description=""` (no description) is accepted — descriptions are optional on every row.

*Auth flows*
- Registration response leaves the new user logged in (assert `client.session[SESSION_KEY]` set; redirect lands on `/settings/`).
- Login is case-insensitive on email (register `Foo@Example.com`, log in as `foo@example.com` succeeds; the form sends client-hashed password).
- Login by username does NOT work (POST `{"username": "...", "password": ...}` to `/accounts/login/` returns 200 with the form re-rendered, not a session).
- Logout clears the session.
- **No outbound email** in any normal flow: assert `mail.outbox == []` after registration, login, logout, profile save, password change, and `manage.py reset_password`. Regression for "Notifications — none".

*Verified status*
- The `verify_user` management command flips `is_verified` to `True`; `--unverify` flips back.
- A Django shell update (`Profile.objects.filter(...).update(is_verified=True)`) is equivalent to the management command — the field has no model-level write restriction (the protection against client-side writes lives in the form-layer "is_verified is not in the rendered profile-edit form" rule, asserted in the Profile lifecycle test group).
- The verified flag does NOT affect directory inclusion or profile-page visibility (regression for "Verified status — badge-only"). The badge-rendering tests live in Phase 2 alongside the directory/profile templates.

*Anti-bot*
- Honeypot field rejects a non-empty submission.
- Signed-timestamp rejects a `<2s` submission and a `>1 day` submission.

*DB constraints* (use `assertRaises(IntegrityError)` inside `transaction.atomic()`)
- Exactly-one `is_other_freetext=True` constraint rejects a second such row.
- `freetext_requires_description` CHECK rejects an `is_freetext=True` row with empty `custom_description`.
- A non-freetext row with non-empty `custom_description` saves successfully (regression that the previously-existing `non_freetext_forbids_description` CHECK has been removed).
- Partial `uniq_profile_category_nonfreetext` index rejects two predefined-category rows for the same profile, but allows two `is_freetext=True` rows with different descriptions. **Postgres-only**, skipped on SQLite (per "Database Models").

**Acceptance criteria for Phase 1**

- `python manage.py migrate` on an empty DB produces a working schema with seeded categories, including exactly one `is_other_freetext=True` row.
- Re-running `migrate` on an already-migrated DB is a no-op (data migration is idempotent).
- A new user can register (sending a client-hashed password, never plaintext), log in, log out, log back in (case-insensitively on email), and set a profile with first name (required), optional last name, bio, scheduling URL, optional feedback URL, and per-service descriptions on any number of services.
- The `manage.py create_user` command produces a regular user who can log in via `/accounts/login/` (proving client-side hashing parity between the JS module and the Python helper).
- The `manage.py reset_password` command produces a working temp-password handoff: operator runs the command, communicates the temp value out-of-band, the user logs in with it, and is redirected to the change-password page until they pick a new one.
- The `manage.py verify_user` command flips a profile to `is_verified=True`. (Badge-rendering checks live in Phase 2 alongside the directory and profile-page templates.)
- `/admin/` is unrouted (no Django admin in v1); a request to it returns 404. Regression for "No Django admin (operator workflow)".
- The operator can deactivate a user via the README's `manage.py shell` recipe (`User.objects.filter(...).update(is_active=False)`). The test that verifies the directory excludes deactivated users belongs in Phase 2.
- `mail.outbox` is empty after every test in the auth-flows group (proves no surprise email-sending paths exist).
- `README.md` is committed with the operator quick-reference (create_user, verify_user, reset_password, deactivate, hard-delete) and the local dev setup recipe.
- `python manage.py check --deploy` runs cleanly under prod settings (expected dev warnings are silenced via `SILENCED_SYSTEM_CHECKS`).
- All tests above pass in CI. CI is Phase 1 work (see "CI" below) — set it up alongside the test suite, not at the end of the phase.

### Phase 2: Public Directory (Days 4–6)

**Build**

- **Home page** (if it is separate from the directory listing): render the hero band, primary/ghost CTAs, and a live member-count pill showing the count of directory-visible profiles (active users with non-empty `scheduling_url`, regardless of verification).
- **Public profile page at `/p/<username>/`** with the "Schedule with me" CTA.
  - Returns 404 for unknown, inactive, or no-scheduling-link users. Never reveal which of those is the case — same enumeration-resistance reason in every direction. **`is_verified` is NOT a 404 condition** — unverified profiles render the same as verified ones, just without the badge.
  - Username lookup is case-insensitive: `User.objects.get(username__iexact=...)`. Sharing `/p/Mahmoud` and `/p/mahmoud` both resolve to the same profile.
  - **Owner exception (no scheduling link):** a logged-in owner viewing their own URL with no scheduling URL gets 200 + a yellow banner: *"Add a scheduling link to appear in the directory."* Check is `request.user.is_authenticated and request.user.pk == resolved_user.pk` (DB-row PK, not stringified username, so case/unicode-fold edges can't sneak past). A deactivated user can't log in so can't trigger this. There is no owner-banner for the unverified case — see "Verified status — badge-only" for rationale.
  - **Verified badge** renders next to `display_name` in the profile header iff `profile.is_verified=True` (see "Verified status — badge-only" for styling and rendering rules).
- **Directory page** at `/` (or wherever home renders the listing) with category filter and search.
  - Base queryset (filters applied **before** any narrowing):
    ```python
    Profile.objects.filter(user__is_active=True).exclude(scheduling_url="")
    ```
    Note `is_verified` is **not** in the filter — both verified and unverified profiles are listed; the badge is the only difference (see "Verified status — badge-only").
  - Search adds `Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(bio__icontains=q) | Q(providerservice__custom_description__icontains=q)` followed by `.distinct()`.
  - When `q` is non-empty, render a visible "Clear" button that removes `q` (preserve `category` if present).
  - Eager-load to avoid N+1: `select_related("user")` and `prefetch_related("providerservice_set__category")`. **Prefetch the through-model, not `services`** — the listing renders each "Other" row's `custom_description`, which lives on `ProviderService`, so prefetching `services` still issues one extra query per row. (`providerservice_set` is Django's default reverse manager name; if you set `ProviderService.Meta.default_related_name`, update this prefetch and the search Q-clause.)
- **Category filter logic.**
  - Chip row sends `?category=<slug>` (no param = "All"). Filter is `.filter(services__slug=category_slug).distinct()`.
  - The "Other" chip (`is_other_freetext=True` row) surfaces every profile with any "Other" service, regardless of `custom_description` content.
  - Unknown/nonexistent slug → empty queryset, NOT a 404. Show the empty-state copy from design-notes §4.2.
  - Each category chip displays a count of matching profiles.
- **Default ordering** (pick one, document): `Profile.objects.order_by("-created_at", "id")`. Newest joined surface first; `id` tiebreaker is **required** for stable pagination — without it, two rows sharing `created_at` to the second can shuffle between page loads.
- **Category chip ordering:** `.order_by("is_other_freetext", "sort_order", "name")`. `False` sorts before `True`, so the "Other" row pins last regardless of `sort_order`.
- **Pagination:** Django's `Paginator`, 20 per page. Page links must preserve active filters: `?q=...&category=...&page=2`. The paginator footer shows "Showing X of Y" plus prev/next links. Wrap `paginator.page(n)` in a try/except: catch `PageNotAnInteger` → return page 1; catch `EmptyPage` → return the last page. Otherwise `?page=abc` and `?page=999` return a 500.
- **`robots.txt` view:** a `TemplateView` that picks one of two templates based on `SITE_IS_PRODUCTION`. Set `Cache-Control: public, max-age=3600`. In non-production, also set `X-Robots-Tag: noindex, nofollow` on every page via middleware (covers any future page added without an explicit robots entry).
- **Tailwind styling pass** on: home, directory (incl. verified-badge pill), profile (incl. verified-badge pill in the header), login, register, change-password (logged-in `/settings/password/`), profile-edit, **owner-empty** (logged-in own-profile view with no scheduling link — see "Verified status — badge-only"), privacy, terms, **and the 404/500 error templates**. The 404 / 500 templates live at `apps/pages/templates/404.html` and `500.html` (per "Project layout"); Django auto-picks them up by name when `DEBUG=False` provided `apps.pages` is in `INSTALLED_APPS` and `APP_DIRS=True` in the templates loader. Don't ship Django's debug 404/500 styling to production.

**Phase 2 test suite**

*Directory inclusion*
- Excludes inactive users.
- Excludes users with `scheduling_url=""`.
- **Includes** users with `is_verified=False` (regression for "Verified status — badge-only"): a fresh, unverified profile with `scheduling_url` set appears on the directory listing. Flipping `is_verified=True` does NOT change inclusion — only whether the badge renders on the card.

*Verified badge rendering*
- Directory card renders the "✓ Verified" pill next to `display_name` iff `profile.is_verified=True`.
- Directory card omits the pill (and any placeholder text) iff `profile.is_verified=False`.
- Profile page header renders the "✓ Verified" pill next to `display_name` iff `profile.is_verified=True`; omits it otherwise.
- Flipping `is_verified` via `verify_user` and reloading the directory + profile page toggles the badge in both places (regression that both templates read the same field).

*Search*
- Matches `first_name`, `last_name`, `bio`, and `custom_description` (across all service rows, not just "Other").
- Matches `custom_description` on a predefined-category service row (regression that the search corpus was broadened from "Other-only" to all rows).
- Does NOT match `feedback_url`: set `feedback_url="https://forms.example.com/secret-thing"`, search "secret-thing", assert zero results.
- Deduplicates a profile with multiple matching service descriptions.
- Input over 80 chars is silently truncated server-side; search runs against the truncated string.
- When `q` is non-empty, the "Clear" button is visible and removes `q` (preserving `category` if present).

*Filter*
- Category filter works on its own.
- Category filter combined with search applies both (intersection, not union).
- Pagination preserves `q` and `category` in page-2 links.
- Category chips render counts that match the base queryset (and the current search filter if `q` is present).
- Paginator footer shows "Showing X of Y" plus prev/next links.

*Profile page*
- Owner exception (no scheduling): logged-in owner viewing their own `/p/<username>/` with no scheduling URL gets 200 + the "add a scheduling link" banner. Applies regardless of `is_verified`.
- Unverified, scheduling set, public viewer: logged-out viewer of an unverified profile with a scheduling URL gets **200** (regression for "Verified status — badge-only" — the page is publicly visible without the badge).
- Unverified, scheduling set, owner self-view: logged-in owner with `is_verified=False` and a scheduling URL gets 200 with **no banner** (the absence of the badge is the only signal).
- Public 404: a profile with no scheduling URL (or an inactive user) returns 404 to any non-owner viewer; `is_verified=False` is NOT a 404 condition.
- Case-insensitive lookup: registering as `Mahmoud` and visiting `/p/mahmoud/` returns 200 (when scheduling URL is set).
- Public profile renders `display_name` (first + last), or just first when last is blank — assert no trailing space.
- Renders the per-service description text under each service row when set; omits it when blank.
- Renders "Send anonymous feedback →" when `feedback_url` is set.
- Omits the feedback button entirely when `feedback_url` is blank (no empty/disabled placeholder).
- Both outbound buttons render with `target="_blank"`, `rel="noopener noreferrer"`, and `referrerpolicy="no-referrer"`.
- Public visitor caution renders next to the Schedule CTA when `scheduling_url`'s host is non-allowlisted (e.g., `https://my-tool.example.com/...`); the panel contains the approved copy `Sadaqa Jariyah doesn't recognize this scheduling tool. Be cautious on the linked site and never share confidential information there.`
- Public visitor caution does NOT render when `scheduling_url`'s host is on the allowlist (e.g., `calendly.com`, `cal.com`, a `*.calendly.com` subdomain, etc.).
- Public visitor caution renders for any viewer of `/p/<username>/` — anonymous, other logged-in members, AND the profile owner self-viewing — when the host is non-allowlisted (regression that the helper is read by the public-profile view, not gated on viewer identity).
- Public visitor caution does NOT render based on `feedback_url` host — the scheduling allowlist applies only to scheduling.
- Feedback visitor caution renders on `/p/<username>/` whenever the "Send anonymous feedback →" button renders (i.e., whenever `feedback_url` is non-empty), regardless of host. The panel contains the approved copy `This feedback form should be anonymous — it should not ask for your name, email, or any other personal details. Sadaqa Jariyah cannot verify what the form requests, so please check before submitting.`
- Feedback visitor caution does NOT render when `feedback_url` is blank (the button is also absent; no empty caution placeholder).
- Feedback visitor caution renders for any viewer — anonymous, other logged-in members, and the profile owner self-viewing — whenever the feedback button is present.
- Feedback visitor caution renders independently of the scheduling caution: a profile with an allowlisted scheduling host AND a `feedback_url` set shows only the feedback caution; a profile with both a non-allowlisted scheduling host AND a `feedback_url` set shows both cautions.

**Acceptance criteria for Phase 2**

- Logged-out visitor can browse the directory, filter by category, search by first/last name, bio, and any per-service description, and click into any profile.
- The directory lists every active profile with a scheduling URL, verified or not. Running `manage.py verify_user member@example.com` does NOT change inclusion — it only makes the "✓ Verified" badge appear next to that member's name in the directory card and on their profile page on the next load.
- "Schedule with me" opens the scheduling URL in a new tab with `noopener noreferrer` and `referrerpolicy="no-referrer"`.
- "Send anonymous feedback →" appears only when `feedback_url` is set, with the same outbound-link attributes.
- A profile with no scheduling URL (or an inactive user) returns 404 from `/p/<username>/` for logged-out visitors and any non-owner logged-in visitor; the owner sees their own profile with the "add a scheduling link" banner per "Verified status — badge-only". An unverified profile with a scheduling URL is publicly visible (200) without a badge.
- `/p/<MixedCaseUsername>/` resolves identically to the lowercase form.
- A 404 page rendered under `DEBUG=False` uses the styled custom template.
- **Keyboard accessibility spot-check:** Tab through home → directory (chips, search, profile cards, pagination) → profile page (Schedule + Feedback buttons) → login → register → profile-edit. Every interactive element shows a visible `focus-visible` ring; the skip-link appears on first Tab and jumps to `#main`. Per the Accessibility section.
- All Phase 2 tests pass.

### Phase 3: Deploy (Days 7–8)

**Build**

- **Set up Render + PostgreSQL (free tier).**

- **Render build command** (Linux x86_64). In order:
  1. Download the matching standalone Tailwind CLI release for the arch. **Pin a specific Tailwind v3.x version** (e.g., `v3.4.x`) — never `latest`, and **not v4**. Tailwind v4 dropped `tailwind.config.js` for CSS-first config, removed the `@tailwind base/components/utilities` directives, and the standalone CLI invocation differs; this plan is written against v3.
  2. Verify the binary against `tailwind-v<version>.sha256` checked into the repo: `curl` the binary, compute `sha256sum`, `diff` against the expected file. **Fail the build on mismatch.** Fetching a versioned URL without a hash is a supply-chain weak spot — "we'll add the hash later" never happens. The `.sha256` file is generated once per Tailwind version bump by downloading the binary on a trusted local machine, running `sha256sum tailwindcss-linux-x64 > tailwind-v<version>.sha256`, and committing the result. Cross-check the hash against Tailwind's GitHub release page before committing.
  3. Run `tailwindcss -i ./static/src/input.css -o ./static/dist/styles.css --minify`. Input file contains the `@tailwind base/components/utilities` directives plus the `.honeypot` class definition. `tailwind.config.js` lists in `content`:
     - `./apps/**/templates/**/*.html` (covers `apps/<label>/templates/` for every app — `pages` (base.html, 404.html, 500.html, privacy, terms, home), `users` (registration, login, change-password), `directory` (profile, directory list, settings), `security` (robots templates))
     - `./.venv/lib/python*/site-packages/crispy_tailwind/**/*.html` (or wherever the venv lives — `crispy-tailwind` ships its own form templates with Tailwind classes; without scanning them, Tailwind purges the form-input/error classes and the rendered forms look unstyled in production. If the venv path varies between dev and Render, set `TAILWIND_CRISPY_TEMPLATES_PATH` in `tailwind.config.js` from an env var the Render build sets, or copy the vendor templates into the repo at build time.)
  4. `python manage.py collectstatic --noinput`. `STATICFILES_DIRS = [BASE_DIR / "static"]` includes both `src/` and `dist/`. Templates reference `{% static 'dist/styles.css' %}`.
  5. `python manage.py check --deploy`. **Run after `collectstatic`** so storage misconfigurations surface. Fail the build on any unexpected warning.
  - **Do NOT run `migrate` in the build command.** The build phase runs even for builds that ultimately fail health checks; on a paid plan with multiple instances it can also race the previous instance still serving traffic.

- **Migrations on free tier (where v1 lives):** Render's **pre-deploy command** is the right place for `migrate --noinput`, but it's **paid-plan-only**. On free tier, prepend migrate to the start command:
  ```
  python manage.py migrate --noinput && gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 30 --access-logfile -
  ```
  - `$PORT` is auto-injected by Render.
  - `--workers 2` is sensible for free-tier CPU; tune after observing real load.
  - `--access-logfile -` sends access logs to stdout so Render's log viewer captures them (Django's request logger only logs warnings+).
  - Free tier runs a single web instance, so the migrate-race issue doesn't apply.
  - **On upgrade to paid plan:** move `migrate` out of the start command and into pre-deploy.

- **WhiteNoise wiring.** Use the Django 5.x `STORAGES` setting (see "Required Django settings for production"). `MIDDLEWARE` order is fixed by the canonical list under "Security → Middleware order" — do not improvise.

- **DEBUG smoke check.** Apply all "Required Django settings for production". Confirm `DEBUG=False` in the deployed app: curl an intentionally-broken URL and confirm the response is the bare 500 page, NOT the yellow Django debug traceback.

- **Connect domain + SSL.** Update `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`. Add both `sadaqajariyah.online` and `www.sadaqajariyah.online` as custom domains in Render so Let's Encrypt issues certs for both.

- **Configure the www → apex 301 redirect.** Render does not auto-redirect between custom domains. Canonical: `sadaqajariyah.online` (apex). Two options:
  - **(a, preferred)** Add a redirect rule in Render's Redirects/Rewrites: `www.sadaqajariyah.online` → `https://sadaqajariyah.online`, status 301. Doesn't burn a Python request cycle.
  - **(b)** Django middleware 301'ing when `request.get_host() != CANONICAL_HOST`.
  - Verify: `curl -I https://www.sadaqajariyah.online` returns `301 Location: https://sadaqajariyah.online/...`.

- **No email setup at deploy time.** v1 sends zero outbound mail (per "Notifications — none"). Skip SPF, DKIM, DMARC, and any email-provider account creation entirely. The DNS-propagation, deliverability-test, and iCloud-strictness items that were here in earlier drafts have been removed deliberately — there is nothing to deliver.

- **Operator bootstrap on Render.** Open Render's "shell" tab and run `python manage.py create_user <operator-email>` to create the first account, then `python manage.py verify_user <operator-email>` to give it the verified badge in the directory. **Do NOT use `createsuperuser`** — it stores a hash of plaintext, which the client-side-hashing login form can never match (see "Security → Password hashing"). The `create_user` command handles the JS-equivalent client-side derivation; the operator can log in via `/accounts/login/` immediately after. v1 has no admin to make staff/superuser of, so the account stays a regular user.

- **Production smoke test.** Walk through, in order:
  1. Signup (auto-login, no email-confirmation step). Verify the `password` form field's value in the network tab is the hex client-hash, NOT the plaintext (proves `auth-hash.js` is loaded and runs).
  2. Logout.
  3. Re-login using the email in mixed case (verifies case-insensitive email-based login).
  4. Profile edit:
     - Set first name and (optionally skip or fill) last name; bio.
     - Set scheduling URL on an allowlisted host.
     - Set scheduling URL on a non-allowlisted host and confirm the operator-side `messages.warning` fires on save AND that visiting `/p/<username>/` (both logged-in and logged-out) shows the public visitor caution panel next to the Schedule CTA. Then switch back to an allowlisted host (e.g., `calendly.com`) and confirm the public caution panel disappears on the next load.
     - Add a predefined-category service with a custom description (e.g., "Mentoring — focused on early-career engineers").
     - Add an "Other"-category service with its required description.
     - Set `feedback_url` to a valid `https://` link **and leave it set for the outbound-click check below**.
  5. Visit own `/p/<username>/` while logged in (scheduling URL set, unverified): confirm the page renders 200 with **no** badge and **no** banner (per the Visibility behavior table). Visit while logged out: also 200, no badge.
  6. Confirm the directory listing already shows the test profile — without a badge — even though the operator hasn't verified it yet (regression for "Verified status — badge-only").
  7. Operator: run `python manage.py verify_user <member-email>` against the test account. Reload the directory and `/p/<username>/`: the "✓ Verified" badge now renders next to the name in both places. Inclusion was unchanged — only the badge appeared.
  8. Search matching first name, last name, bio, predefined-category description, and "Other" description.
  9. Category filter.
  10. Outbound click to scheduling link: verify new tab + `noopener noreferrer` + `referrerpolicy="no-referrer"`.
  11. Outbound click to feedback link (still set from step 4): same checks. Confirm the feedback caution panel renders adjacent to the button with the approved copy (`This feedback form should be anonymous — ...`), and that it shows for both logged-in and logged-out viewers.
  12. Return to profile edit and unset `feedback_url`; reload `/p/<username>/` and confirm the feedback button AND the feedback caution panel are both gone (no empty placeholder for either).
  13. Forgot-password operator flow: `python manage.py reset_password <member-email>` → operator records the temp plaintext → log out → log in with the temp value → confirm redirect to `/settings/password/` → set a new password → confirm redirect away from the change-password page after success.
  14. Operator deactivation via shell: visit `/admin/` and confirm 404 (no admin in v1). Open Render's web shell and run `python manage.py shell -c "from django.contrib.auth import get_user_model; get_user_model().objects.filter(email__iexact='<member-email>').update(is_active=False)"`. Confirm the directory excludes the test user, and `/p/<test-username>/` returns 404 to a logged-out visitor. Re-activate by running the same command with `is_active=True`.
  15. Confirm `mail.outbox` analogue in production: spot-check Render's log viewer for any SMTP attempts during the smoke test (there should be none — every flow sets `EMAIL_BACKEND = locmem`).

- **Backup pre-launch.** Run `pg_dump` against production DB. Confirm the dump file is non-empty. **Test-restore into a throwaway local Postgres** — discovering the restore command is wrong during a real outage is the failure mode the runbook exists to prevent.

- **Recurring backups (post-launch).** Weekly calendar reminder for the operator to run the documented `pg_dump` and store the file in encrypted cloud storage. Free Render Postgres has no automated backup; "I dumped it before launch" is not a backup strategy. Reminder is in the runbook from day one.

**Acceptance criteria for Phase 3**

- Site is reachable over HTTPS at the custom domain with a valid certificate and `Strict-Transport-Security: max-age=60` (short value — see post-launch task below; do NOT ship `31536000` on day one).
- `www.sadaqajariyah.online` returns `301` to `sadaqajariyah.online`.
- The full smoke-test sequence (signup → directory listing without badge → operator verify → badge appears → operator forgot-password → admin deactivate) completes end-to-end with no errors.
- The `password` form field carries a hex client-hash on the wire — verified in the browser network tab during signup. No plaintext password ever appears in a request body.
- Render's log viewer shows zero SMTP-attempt log lines during the smoke test (regression check on the no-email rule).
- `/robots.txt` returns the production response (allow `/`, `/p/<username>/`; disallow `/accounts/`, `/settings/` — no `/admin/` entry, the URL doesn't exist).
- `/admin/` returns 404 in production (regression check that `django.contrib.admin` was not silently re-added to `INSTALLED_APPS`).
- Render's log viewer shows no `ERROR`-level entries from the smoke-test run.
- A `pg_dump` of the production DB exists locally, **has been test-restored into a throwaway Postgres**, and the free-DB-rotation calendar reminders are set (primary + mid-cycle backstop, per Hosting section).
- `README.md` at the repo root documents the operator quick-reference (`create_user`, `verify_user`, `reset_password`, deactivate, hard-delete) and a junior dev can follow it to verify a user end-to-end.
- The one-week-post-launch calendar reminder to bump `SECURE_HSTS_SECONDS` from `60` to `31536000` (+ `INCLUDE_SUBDOMAINS`, `PRELOAD`) is set.
- The weekly `pg_dump` calendar reminder is set.
- The daily Render-log-viewer check reminder (the v1 substitute for ADMINS-emails-on-500) is set.

Total: roughly **1.5–2 weeks** of focused work, including the test suite and deploy-time hardening. The earlier "1–1.5 weeks" estimate skipped the security/test work; including it pushes the realistic range up by a few days.

### CI (cross-cutting, Phase 1 onward)

GitHub Actions workflow at `.github/workflows/test.yml` (~40 lines). Set up in Phase 1; catches regressions before Phase 3.

**Jobs**
- Run `pytest` (or `manage.py test`) on every push and PR.
- **Use a Postgres service container, not SQLite.** The partial-condition constraints in `ProviderService` behave differently on SQLite (see "Constraint portability"); the `IntegrityError` regression tests require Postgres to be meaningful.
- Run `python manage.py check --deploy` against the prod settings module as a separate job step.

**Branch protection (one-time, takes 30 seconds, biggest bang-for-buck safeguard)**
- Render auto-deploys from `main` on push, so a failing test that lands on `main` ships to production.
- Add a GitHub branch protection rule on `main` requiring the CI status check to pass before merge.
- Disallow direct pushes to `main`.

**No CD to Render.** Render's auto-deploy from `main` on green is enough.

---

## Resolved Decisions

- **Scheduling is offloaded.** The site does not store slots or bookings. Each provider supplies a single scheduling URL that the directory links out to.
- **No outbound email.** v1 sends zero email — no signup confirmation, no welcome mail, no password reset, no admin-error notifications. Forgot-password recovery is operator-only via the `reset_password` management command. See "Notifications — none".
- **Login uses email + password, not username.** Username is publicly visible in the profile URL; making it the login identifier would be a credential-leak. Login is case-insensitive on email. See "User Accounts → Login".
- **Passwords never travel in plaintext.** The browser hashes the password client-side (PBKDF2-SHA256 with the email as salt) before submit; the server re-hashes that value with a secret pepper before storing/comparing. See "Security → Password hashing".
- **Verified status is badge-only.** All profiles (with a scheduling URL) are publicly listed in the directory. The operator-controlled `Profile.is_verified` flag only renders a "✓ Verified" badge next to the member's name in the directory and on the profile page. Members cannot self-verify. See "Verified status — badge-only".
- **Last name is optional.** A member who prefers not to publish a last name leaves it blank; the public profile renders just the first name.
- **Per-service descriptions are optional on every category.** Predefined categories (Mentoring etc.) accept an optional elaboration the provider writes; "Other" rows still require their description as the de-facto title. See "Database Models → ProviderService".
- **No site-wide timezone problem.** Whatever scheduling tool the provider uses handles the visitor's local-time rendering. `USE_TZ = True` and `TIME_ZONE = "UTC"` are set, but no view formats wall-clock times in v1. The "Member since" copy on the profile sticky CTA renders only a date (e.g., "May 2026"), so timezone is irrelevant.
- **Profile URLs use `username`,** not the user PK, to avoid leaking user counts. Username is required at registration, immutable in v1, and validated against the constraints under "User Accounts".
- **Scope guard.** See the Overview blockquote — slot/availability/in-site-booking/calendar-export/per-booking-email work belongs in `.thoughts/deferred_plan-v2-booking.md`. If a v1 ticket starts requiring any of those, stop and reread that doc.
- **Feedback is also offloaded.** Each member optionally publishes a third-party form URL (Google Forms, Microsoft Forms, anything). The site does not host, store, or proxy form responses; it only renders an outbound link. No host allowlist applies — the user's wording was "any other link" — but the same hard-block validation as `scheduling_url` is enforced (https only, no IP literals, no `javascript:`/`data:`/`file:`).
- **Domain is settled.** `sadaqajariyah.online` is purchased and is the canonical domain.

---

## Privacy & Legal Minimums

A directory of real people in a community context needs the following before launch. These are 30-minute static pages, not a real legal review, but they cannot be skipped.

**Privacy notice** at `/privacy/`. The Privacy page in the prototype (`.thoughts/design/final.jsx` `Privacy()`) covers most of this; **add the feedback paragraph as a sixth section** per design-notes §4.8. Required content:
- What's collected at signup: email, peppered password hash, username. IPs are visible only in Render's transient access-log viewer; NOT stored in the application database.
- What's shown publicly: `first_name` (always), `last_name` (only if the member fills it in), `bio`, services with their per-service descriptions, `scheduling_url`, optional `feedback_url`, and a "✓ Verified" badge if the operator has flipped the verification flag for that account. All profiles with a scheduling URL are publicly listed; the badge is the only difference between a verified and an unverified profile.
- The platform sends **no outbound email**. Members who forget their password or want their account deleted contact the operator out-of-band at `OPERATOR_CONTACT_EMAIL` (rendered into the privacy notice and the verification banner from the env var). The operator handles password reset via a management command (the user receives a temporary plaintext password out-of-band and is forced to change it on next login).
- Clicking a **scheduling link** hands the visitor off to a third-party tool, whose own privacy policy applies.
- Submitting via a member's **anonymous-feedback link** delivers the response to that third-party form provider — Sadaqa Jariyah neither stores nor sees it.
- Cookies section (see below).

**Terms of use** at `/terms/`. Required content:
- Providers attest they are who they say they are.
- No commercial spam.
- Platform provided as-is.
- Operator can deactivate accounts at their discretion.

**Footer link to both, on every page, from launch.**

**Nav and footer links the design references but v1 does not implement.** Design-notes §3 shows an `About` link in the top nav and `Contact` in the footer. v1 does **not** ship either of those pages — when building the templates, **omit those links** rather than letting them 404. If the operator wants an About page later it's a static template; "Contact" in v1 is covered by the operator email listed in the privacy notice's deletion-path paragraph. Track both as Future Considerations work.

**Public-content notice at the point of input.** The bio and "Other" description fields show small helper text marking them as **public, world-readable**.

**Data subject access / deletion path** (sufficient for v1 under GDPR-like regimes — the obligation is a working path, not a self-serve UI):
- Privacy notice states: "To delete your account, contact the operator at `<OPERATOR_CONTACT_EMAIL>`. We will deactivate immediately and hard-delete within 30 days." (Same address used for verification requests and forgot-password recovery — one channel, three flows.)
- Operator README contains the exact hard-delete shell recipe (`User.objects.filter(email__iexact=...).delete()`). FK cascades handle `Profile` and `ProviderService`; no booking data, so no scrubbing pass needed.

**Cookies — no banner in v1.** Only two cookies are set: Django session (on login) and CSRF (on first form view). Both are strictly necessary for site function and exempt from cookie-banner requirements under typical ePrivacy interpretations. The privacy notice has a one-sentence "Cookies" section listing both, their purpose, and that no third-party/analytics cookies are set. **Adding analytics later triggers the banner** — track as a v2 concern.

**No analytics or tracking pixels in v1.** Plausible, Fathom, GA, Hotjar — all out. Each adds CSP entries, possibly a cookie-banner obligation, and another data processor to enumerate. If interest data becomes useful post-launch, start with a privacy-first option (e.g., Plausible self-hosted).

---

## Future Considerations (post-launch)

- **Bring scheduling in-house (v2):** the full slot/booking/cancellation system is specified in `.thoughts/deferred_plan-v2-booking.md`. Reach for it only if the Calendly-link approach proves insufficient — for example, if many providers are uncomfortable signing up for a third-party tool, or if the community wants per-booking analytics the site itself can show.
- **Moderation UI:** v1 ships the badge-flipping *flow* (operator flips `is_verified` per profile) but no UI — it's a CLI workflow. Adding a small staff-only review screen (a list of unverified profiles + one-click verify) becomes worthwhile if the unverified-queue grows past what a CLI workflow handles comfortably. Bringing back `django.contrib.admin` is one path; a custom staff-only view is another. Either way, the client-side-hashing rule has to extend to whatever login form the new path uses (see "Security → Password hashing").
- **Stricter verification gate (if needed post-launch):** v1 makes verification a badge-only signal, deliberately keeping the directory inclusive. If spam or impersonation pressure grows, the natural escalation is to gate directory inclusion on `is_verified=True` (revert to the earlier moderation model). Implementation is a one-line addition to the directory queryset and a re-introduction of the "awaiting verification" owner banner — no schema change needed, since the field is already in place.
- **Re-introduce Django admin** (if/when the moderation UI lands): the gates are (a) a hashing-aware admin login form (or keep the public login as the entry path), (b) `is_staff` provisioning via the operator's shell, (c) updated robots.txt to disallow `/admin/`, (d) updated CSP middleware coverage for admin pages.
- **Languages:** Arabic / Urdu / other community languages alongside English
- **Self-serve account deletion:** v1 has no account deletion path; if added, the policy is trivial (delete `User` + `Profile` + `ProviderService`) since no booking data exists. A "request deletion by emailing the operator" line in the privacy notice is enough until self-serve is built.
- **Username changes:** requires a redirect table from old → new username so inbound community links don't 404. Out of scope for v1; designing the redirect table is the bulk of the work.
- **Embedded scheduler widget:** if the click-out friction proves too high, embed Calendly's inline widget on the profile page; defer until v1 ships and that friction is actually observed
- **Periodic scheduling-URL link-check:** a low-priority background job that flags 404/timeout scheduling URLs in the admin so operators can nudge providers. Not v1 — measure first.

---

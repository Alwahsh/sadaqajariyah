# Sadaqa Jariyah — End-to-End Scenarios (specs.md)

This file is the **behavioral acceptance specification** for v1, derived from `.thoughts/plan.md`. Each bullet is a single user-facing scenario stated as a story or expectation — readable top-to-bottom by a human reviewer to confirm "yes, that is what the site should do," and consumable by a downstream agent that will write end-to-end browser tests against a running Django app. The site is not considered complete until every scenario below passes.

Conventions:
- "Anonymous visitor" = a browser session with no auth cookies.
- "Member" = an authenticated regular user.
- "Operator" = a person with shell access to the running container (Render's web shell).
- A scenario phrased as "the page renders X" implies X appears in the DOM; phrased as "returns 404" means the HTTP status is 404 and the styled custom 404 template is rendered.
- "Outbound link attributes" = `target="_blank"`, `rel="noopener noreferrer"`, and `referrerpolicy="no-referrer"`, all three present.

---

## 1. Public discovery — anonymous visitors

### 1.1 Home page (`/`)

- As an anonymous visitor I can load the home page over HTTPS and see the wordmark, the hero band, the tagline, the live member-count pill, the "Browse the directory →" primary CTA, and the "Offer your time" ghost CTA.
- As an anonymous visitor clicking "Browse the directory →" on the home page I land on the directory listing.
- As an anonymous visitor clicking "Offer your time" on the home page I land on the registration page.
- As an anonymous visitor I see the three "how it works" cards (`01` Browse, `02` Read, `03` Schedule) on the home page.
- As an anonymous visitor I see the top nav (Home, Directory) and the footer (Privacy, Terms) on every page; the design's `About` and `Contact` links from the prototype are intentionally not rendered in v1 and do not produce 404s.
- As an anonymous visitor the live count pill in the hero shows the count of profiles currently visible in the directory (active users with a non-empty `scheduling_url`), regardless of whether they are verified.

### 1.2 Directory listing (`/` directory view or its dedicated path)

- As an anonymous visitor I can load the directory page and see one row per profile that meets the inclusion rule: `user.is_active=True` AND `scheduling_url` is non-empty.
- As an anonymous visitor I see profiles with `is_verified=False` listed in the directory exactly like verified profiles, with the only visual difference being the absence of the "✓ Verified" badge next to the name.
- As an anonymous visitor I see profiles with `is_verified=True` listed with a visible "✓ Verified" pill next to the member's name on each card.
- As an anonymous visitor I do NOT see profiles whose owner is `is_active=False` (deactivated).
- As an anonymous visitor I do NOT see profiles whose `scheduling_url` is empty.
- As an anonymous visitor I see the directory rows ordered newest-first by `created_at` with a stable secondary sort by `id` so the same query produces the same order on every page load.
- As an anonymous visitor I see the category chip row with "All" first, then every active predefined category in `sort_order` then alphabetical order, then the single "Other" chip pinned last regardless of its `sort_order`.
- As an anonymous visitor each category chip displays a count of matching profiles.
- As an anonymous visitor I see each directory row's avatar (color-block + initials, no photos in v1), display name (first + last, or just first when last is blank with no trailing space), bio snippet (clamped to two lines), up to two service tags, and a "View →" action.
- As an anonymous visitor for service rows whose category is "Other" I see the row's `custom_description` rendered as the tag label rather than the literal word "Other".
- As an anonymous visitor when zero profiles match my current filters I see the styled empty state with the copy `No one matches that search yet.` instead of an error or a 404.

### 1.3 Search

- As an anonymous visitor typing a query in the search box and submitting, I see only profiles whose `first_name`, `last_name`, `bio`, or any `ProviderService.custom_description` (across both predefined and "Other" categories) contains my query (case-insensitive substring).
- As an anonymous visitor searching for text that appears only in a profile's `feedback_url` I do NOT see that profile in the results — feedback URLs are destinations, not searchable content.
- As an anonymous visitor searching for the literal name of a predefined category (e.g., "Mentoring") I do NOT get profiles back simply because they are tagged with that category — categories are filtered via chips, not searched.
- As an anonymous visitor searching with a query of more than 80 characters, the server silently truncates my input to 80 characters before searching and returns whatever the truncated query matches, instead of returning an error.
- As an anonymous visitor searching with an empty or whitespace-only query, the search filter is skipped entirely and I see the unfiltered directory listing.
- As an anonymous visitor searching for a query that matches multiple service rows of the same profile, I see that profile listed exactly once (no duplicates).
- As an anonymous visitor I can clear the search via the visible "Clear" button when my query is non-empty.

### 1.4 Category filter

- As an anonymous visitor clicking a category chip I see only profiles offering that service category; the URL reflects `?category=<slug>`.
- As an anonymous visitor with no `category` query param (or "All" selected) I see the unfiltered directory.
- As an anonymous visitor clicking the "Other" chip I see every profile with at least one "Other" service row, regardless of what their `custom_description` text says.
- As an anonymous visitor passing an unknown category slug in the URL (`?category=does-not-exist`) I see the empty-state copy and a 200 response — NOT a 404.
- As an anonymous visitor combining a search query and a category filter I see the intersection of both filters (AND, not OR).
- As an anonymous visitor my `q` and `category` query params persist across pagination links.

### 1.5 Pagination

- As an anonymous visitor on a directory with more than 20 visible profiles I see at most 20 rows per page and a paginator footer showing "Showing X of Y" plus prev/next links.
- As an anonymous visitor requesting `?page=abc` (non-integer) I am served page 1 instead of a 500 error.
- As an anonymous visitor requesting `?page=999999` (beyond the last page) I am served the last page instead of a 500 error.
- As an anonymous visitor navigating to page 2 with active filters, the page-2 link preserves both `q=` and `category=` and the listing reflects the same filter intersection on page 2.

### 1.6 Public profile page (`/p/<username>/`)

- As an anonymous visitor I can load `/p/<username>/` for any active user whose `scheduling_url` is non-empty and see their display name, bio, service tags, "Member since" date, and a sticky right-column CTA card titled "Schedule a session".
- As an anonymous visitor visiting `/p/<username>/` for a username that does not exist, an inactive user, or a user with no `scheduling_url` set, I receive a 404 — the response never reveals which of those three conditions applies.
- As an anonymous visitor I can visit `/p/<MixedCaseUsername>/` (any casing) and reach the same profile that `/p/<lowercase>/` resolves to.
- As an anonymous visitor I see a "✓ Verified" pill rendered next to the member's display name in the profile header iff `is_verified=True`; nothing (no placeholder, no "Unverified", no "Pending" text) renders when `is_verified=False`.
- As an anonymous visitor I see the member's display name rendered as `first_name` only (no trailing space) when `last_name` is blank, and as `first_name + " " + last_name` when both are set.
- As an anonymous visitor I see each predefined service's optional `custom_description` rendered under (or alongside) its service tag when set, and nothing when blank.
- As an anonymous visitor I see each "Other" service rendered with its `custom_description` as the tag label.
- As an anonymous visitor clicking the primary "Schedule with me →" CTA opens the member's `scheduling_url` in a new browser tab; the link carries `target="_blank"`, `rel="noopener noreferrer"`, and `referrerpolicy="no-referrer"`.
- As an anonymous visitor I see a secondary "Send anonymous feedback →" outline button beneath the schedule CTA iff `feedback_url` is set, with helper text "Opens an anonymous form in a new tab" beneath it.
- As an anonymous visitor I do NOT see any "Send anonymous feedback" button (no disabled placeholder, no empty rendering) when the profile's `feedback_url` is blank.
- As an anonymous visitor clicking the feedback button opens the `feedback_url` in a new browser tab with the same outbound-link attributes as the scheduling button.
- As an anonymous visitor I see a `← Back to directory` crumb at the top of the profile page that navigates back to the directory listing.
- As an anonymous visitor on a profile whose `scheduling_url` host is in `KNOWN_SCHEDULING_HOSTS` (e.g., `https://calendly.com/...`, `https://team.calendly.com/...`, `https://cal.com/...`, `https://savvycal.com/...`), I do NOT see a public visitor caution panel.
- As an anonymous visitor on a profile whose `scheduling_url` host is NOT on the allowlist (e.g., `https://my-tool.example.com/...`), I see a visible caution panel rendered adjacent to the "Schedule with me →" CTA, in a warm-yellow palette (matching the profile-edit warning banner), containing exactly: `Sadaqa Jariyah doesn't recognize this scheduling tool. Be cautious on the linked site and never share confidential information there.`
- As an anonymous visitor on a profile whose host suffix-matches an allowlisted entry on a label boundary (e.g., `https://calendly.com/...` or `https://team.calendly.com/...`) I do NOT see the caution panel; on a profile whose host LOOKS allowlisted by bare-suffix tricks (e.g., `https://evil-calendly.com/...`) I DO see the caution panel.
- As an anonymous visitor seeing the caution panel, the "Schedule with me →" button is still rendered and still functional — the caution is informational, NOT an interstitial that blocks the click.
- As an anonymous visitor I see the public visitor caution regardless of whether the profile's `feedback_url` is set; the caution is driven only by `scheduling_url`'s host.
- As a logged-in member viewing my own profile whose `scheduling_url` host is non-allowlisted, I see the same public visitor caution panel that anonymous visitors see — the caution is not gated on viewer identity.
- As a logged-in member viewing another member's profile whose `scheduling_url` host is non-allowlisted, I see the same public visitor caution panel.
- As an anonymous visitor on a profile with `feedback_url` set, I see a feedback caution panel rendered adjacent to the "Send anonymous feedback →" button, in a warm-yellow palette, containing exactly: `This feedback form should be anonymous — it should not ask for your name, email, or any other personal details. Sadaqa Jariyah cannot verify what the form requests, so please check before submitting.`
- As an anonymous visitor on a profile with `feedback_url` blank, I see neither the feedback button nor any feedback caution panel (no empty placeholder for either).
- As an anonymous visitor the feedback caution panel renders for every value of `feedback_url` regardless of host (Google Forms, Microsoft Forms, Typeform, a self-hosted form, anything) — the caution is unconditional whenever the button is present.
- As an anonymous visitor seeing the feedback caution, the "Send anonymous feedback →" button is still rendered and still functional — the caution is informational, NOT an interstitial that blocks the click.
- As a logged-in member (owner self-view OR another member) viewing a profile with `feedback_url` set, I see the same feedback caution panel that anonymous visitors see — the caution is not gated on viewer identity.
- As an anonymous visitor on a profile with an allowlisted `scheduling_url` AND a non-empty `feedback_url`, I see the feedback caution but NOT the scheduling caution.
- As an anonymous visitor on a profile with a non-allowlisted `scheduling_url` AND a non-empty `feedback_url`, I see BOTH cautions — the scheduling caution next to the Schedule CTA and the feedback caution next to the feedback button.
- As an anonymous visitor on a profile with a non-allowlisted `scheduling_url` AND `feedback_url` blank, I see ONLY the scheduling caution.

### 1.7 Static informational pages

- As an anonymous visitor I can load `/privacy/` and read the privacy notice, including the dedicated section on anonymous-feedback links.
- As an anonymous visitor I can load `/terms/` and read the terms of use page.
- As an anonymous visitor every page renders a footer linking to `/privacy/` and `/terms/`.
- As an anonymous visitor in production I can load `/robots.txt` and see `Allow: /`, `Allow: /p/<username>/`, `Disallow: /accounts/`, `Disallow: /settings/`, and no `/admin/` entry.
- As an anonymous visitor on a non-production deploy (preview/staging) `/robots.txt` returns `Disallow: /` and every page response includes `X-Robots-Tag: noindex, nofollow`.

### 1.8 Error pages

- As an anonymous visitor hitting any unrouted URL under `DEBUG=False` I see the styled custom 404 template (not Django's debug 404 or the default empty 404).
- As an anonymous visitor encountering a 500 error in production I see the styled custom 500 template (not Django's debug yellow traceback).
- As an anonymous visitor visiting `/admin/` I receive a 404 — there is no Django admin panel mounted in v1.

---

## 2. Registration (`/accounts/signup/`)

### 2.1 Successful registration

- As a new visitor I can submit the registration form with a fresh email, a unique username, and a password (already hashed in the browser by `auth-hash.js` to a hex string before submission), and the server creates a `User`, a corresponding `Profile` (via the `post_save` signal), automatically logs me in, and redirects me to `/settings/`.
- After a successful registration my new `Profile` exists with `is_verified=False`, `must_change_password=False`, an empty `bio`, an empty `scheduling_url`, and an empty `feedback_url`.
- After a successful registration my account is immediately able to load `/settings/` (login is established before the redirect).
- After a successful registration `mail.outbox` is empty — no welcome email, no verification email, no any email.

### 2.2 Username rules

- As a new visitor submitting the registration form with a username that matches the regex `^[a-z0-9][a-z0-9_-]{2,29}$` (3–30 chars), my registration succeeds.
- As a new visitor submitting `Ahmed` (mixed case) for username, my account is created with the username stored as `ahmed`.
- As a new visitor submitting a username already taken in any case (e.g., `AHMED` after `ahmed` exists) I see a clean form error, not an `IntegrityError` 500.
- As a new visitor submitting any reserved word (e.g., `admin`, `login`, `signup`, `auth`, `accounts`, `password`, `settings`, `me`, `profile`, `directory`, `privacy`, `feedback`, `support`, `robots`, `sitemap`, `health`, `null`) as my username, I see a clean "username is reserved" form error and my account is not created.
- As a new visitor submitting a username with non-ASCII characters (e.g., `أحمد`, `naïve`) I see a clean form error rather than the system creating a confusable account.
- As a new visitor submitting a username shorter than 3 chars or longer than 30 chars I see a clean form error.
- As a new visitor submitting a username starting with `_` or `-` I see a clean form error (regex requires the first char to be `[a-z0-9]`).

### 2.3 Email rules

- As a new visitor submitting an email already used by another account in any case (e.g., `Foo@Example.com` after `foo@example.com`) I see a clean form error, not an `IntegrityError` 500.
- As a new visitor submitting `Foo@Example.com` for email, my account is stored with email `foo@example.com` (lowercased).
- As a new visitor I am never sent a confirmation email after registration; my account is usable immediately.

### 2.4 Password rules

- As a new visitor inspecting the network request from a registration submission, the `password` form field carries a hex-encoded PBKDF2 hash, never the plaintext password.
- As a new visitor disabling JavaScript in my browser and submitting the registration form, the registration does not silently succeed by sending plaintext — the form requires the JS hashing step (or the server rejects a value that does not look like a hash).

### 2.5 Anti-bot guards on registration

- As a new visitor submitting the registration form within less than 2 seconds of the form GET (signed timestamp), my submission is rejected with the bland generic copy `Submission could not be processed. Please try again.` — the rejection does not name the timer, the honeypot, or any other anti-bot mechanism.
- As a new visitor submitting the registration form more than 1 day after the form GET (stale signed timestamp), my submission is rejected with the same bland copy.
- As a bot-style submitter filling the hidden honeypot field (e.g., `nickname_confirm`) with any non-empty value, my submission is rejected with the same bland copy.
- As a real user with a screen reader tabbing into the honeypot field, I hear the visible label `Leave this field empty.` and tab past without filling it; the field is focusable (no `tabindex="-1"`) and has no `aria-hidden`.
- As a bot probing for which validations failed, I cannot distinguish honeypot/timestamp rejection from a normal field-validation rejection by status code, redirect, or response copy.

---

## 3. Login (`/accounts/login/`)

- As a registered member I can log in by submitting my email (in any casing) and my password, and I land on `/settings/` (or whichever page I came from if `next=` was set).
- As a registered member I can register as `Foo@Example.com` and later log in as `foo@example.com` and `FOO@EXAMPLE.COM` — both succeed because email matching is case-insensitive.
- As a registered member submitting my plaintext password through DevTools (bypassing `auth-hash.js`), my login fails — the server compares the hex-hashed value, not the plaintext.
- As an attacker submitting `{"username": "...", "password": ...}` (username instead of email) to `/accounts/login/`, my login fails: the form re-renders 200 with no session set.
- As a deactivated member (`is_active=False`) attempting to log in, my login fails — Django's auth machinery rejects inactive users.
- As a member who fails login I see a generic "incorrect email or password" form error that does NOT reveal whether the email exists in the database.
- As a member submitting a login form less than 2 seconds after page load, my login still succeeds — login is NOT timer-protected (returning users with autofill submit fast and rejecting them is hostile).
- As a bot filling the honeypot on the login form, my submission is rejected with the same bland copy as registration.
- As a member I can click "Log out" / submit the logout form and my session cookie is cleared; I am redirected to `/` and subsequent requests behave as anonymous.
- As a member I do NOT see a "Forgot your password?" link that initiates a self-serve reset flow — the link in the design is omitted in v1.

---

## 4. Profile editing (`/settings/`)

### 4.1 Access control

- As an anonymous visitor visiting `/settings/`, I am redirected to `/accounts/login/`.
- As a member I can load `/settings/` and edit my own profile only — the form always operates on `request.user.profile` and never accepts a `profile` PK from URL or POST.
- As an attacker crafting a POST to `/settings/` containing `providerservice_set-N-id=<another-profile's-service-pk>`, my submission is rejected because the formset's queryset is restricted to my own profile's service rows.

### 4.2 Form fields & required/optional split

- As a member I can save my profile with a non-empty `first_name`; submitting a blank `first_name` produces a clean form error.
- As a member I can save my profile leaving `last_name` blank; the public profile and `display_name` then render only my first name with no trailing space.
- As a member I can save my profile with a `bio` between 20 and 1000 characters; bios under 20 chars or over 1000 chars produce clean form errors.
- As a member I can save my profile with a non-empty `scheduling_url`; saving with an empty `scheduling_url` is allowed but my profile then disappears from the directory listing.
- As a member I can save my profile with `feedback_url` blank — it is optional and does not affect directory inclusion.

### 4.3 Text sanitization on save

- As a member submitting a `bio` containing HTML tags (e.g., `<b>kind</b> mentor`) the saved value has the tags stripped (e.g., `kind mentor`), via `strip_tags`, before storage.
- As a member submitting `first_name` or `last_name` with internal newlines or runs of whitespace, the saved value collapses all whitespace to a single space and is trimmed.
- As a member submitting a `bio` with multi-line whitespace, internal `\n` characters are preserved (max two consecutive newlines), tabs and runs of spaces collapse to single spaces, and the field is trimmed.
- As a member submitting a `custom_description` with whitespace runs, the saved value collapses all whitespace to a single space and is trimmed.

### 4.4 Service rows (formset)

- As a member I can add a `ProviderService` row in a predefined category (e.g., Mentoring) without filling in `custom_description`, and the row saves successfully.
- As a member I can add a `ProviderService` row in a predefined category and write an elaboration in `custom_description` (e.g., `I mentor early-career engineers`); the saved row carries that text and the public profile and search both reflect it.
- As a member adding a `ProviderService` row in the "Other" category, `custom_description` is required; submitting blank or whitespace-only `custom_description` produces a clean form error and the row is not saved.
- As a member I can add multiple "Other" rows on a single profile (each with its own `custom_description`); the formset accepts more than one `is_freetext=True` row.
- As a member I cannot add two rows for the same predefined category to my profile — the second row is rejected at save with a clean error (or constraint violation that is caught and surfaced as a clean form error).
- As a member I can add up to 12 service rows on my profile.
- As a member crafting a POST with `providerservice_set-TOTAL_FORMS=13` (or any value above 12), my submission is rejected — the formset is configured with `max_num=12`, `validate_max=True`, and `absolute_max=12`.
- As a member I can change a service row's category from a predefined one to "Other" or back; the `is_freetext` flag is updated to match the chosen category and my existing `custom_description` text is preserved across the change.

### 4.5 Scheduling URL validation

- As a member saving my profile with a `scheduling_url` whose host is in `KNOWN_SCHEDULING_HOSTS` (e.g., `https://calendly.com/me/30min`, `https://cal.com/me`, `https://savvycal.com/me`, `https://calendar.google.com/...`, `https://calendar.app.google/...`), the save succeeds with no warning.
- As a member saving with a `scheduling_url` on a host suffix-matching an allowlisted host (e.g., `https://team.calendly.com/...`), the save succeeds with no warning (label-boundary suffix match).
- As a member saving with a `scheduling_url` on an unrecognized host (e.g., `https://my-tool.example.com/...`), the save succeeds AND a yellow `messages.warning` banner displays on the next member-facing page render with the copy `We don't recognize this scheduling tool — make sure the link works for visitors.`
- As a member saving with a `scheduling_url` on an unrecognized host, my public profile page subsequently renders a visitor-facing caution panel adjacent to the "Schedule with me →" CTA with the approved copy `Sadaqa Jariyah doesn't recognize this scheduling tool. Be cautious on the linked site and never share confidential information there.`
- As a member saving with a `scheduling_url` whose host LOOKS allowlisted by bare-suffix tricks (e.g., `https://evil-calendly.com/`), the save still succeeds (since the URL passes the hard-block validation) but the warning fires (since the host does not match on a label boundary).
- As a member saving with a `scheduling_url` starting with `javascript:`, `data:`, or `file:` (any case), the save is rejected with a clean form error.
- As a member saving with a `scheduling_url` whose scheme is not `https` (e.g., `http://...`, `ftp://...`), the save is rejected with a clean form error.
- As a member saving with a `scheduling_url` whose host is an IP literal (e.g., `https://127.0.0.1/`, `https://[::1]/`), the save is rejected with a clean form error.
- As a member saving with a `scheduling_url` longer than 500 characters, the save is rejected with a clean form error.

### 4.6 Feedback URL validation

- As a member I can save my profile with `feedback_url` set to any `https://` URL, regardless of host (no allowlist). Google Forms, Microsoft Forms, Typeform, a self-hosted form — all accepted.
- As a member I can save my profile with `feedback_url` blank (the field is optional).
- As a member saving `feedback_url` with `javascript:`, `data:`, `file:`, a non-`https` scheme, an IP literal, or a length over 500 characters, the save is rejected with a clean form error — the same hard-block rules as `scheduling_url`.
- As a member saving an unfamiliar but valid `https://` host in `feedback_url`, NO soft-warning banner fires — the host allowlist is scheduling-only.

### 4.7 Field exposure / IDOR-resistant editing

- As a member viewing the rendered profile-edit form, the form does NOT contain a `username` input (not even disabled).
- As a member viewing the rendered profile-edit form, the form does NOT contain an `email` input.
- As a member viewing the rendered profile-edit form, the form does NOT contain an `is_verified` input.
- As an attacker crafting a POST to `/settings/` containing `username=newname`, `email=new@example.com`, or `is_verified=true`, the submitted values are ignored — these fields are not bound by the form.

### 4.8 URL preview & form ordering

- As a member I see the URL preview line `What appears at sadaqajariyah.online/p/<my-username>` rendered above the form, with my actual lowercase username.
- As a member viewing the profile-edit form, the `feedback_url` field appears immediately below the `scheduling_url` field (the two are conceptually paired).

### 4.9 Save flow

- As a member after a successful save I see a success toast/message, the form re-renders with my saved values, and the "View public profile" ghost button takes me to `/p/<my-username>/`.
- As a member with no `scheduling_url` set, my profile is NOT in the directory until I save a `scheduling_url`; the change takes effect on the next directory page load (no manual reindex required).

---

## 5. Public profile owner self-view

- As a logged-in member visiting my own `/p/<username>/` while my `scheduling_url` is empty, I receive a 200 (not 404) and see a yellow banner reading `Add a scheduling link to appear in the directory.` with body copy directing me to `/settings/` to add a scheduling link.
- As a logged-in member visiting my own `/p/<username>/` while my `scheduling_url` is empty, I see the dashed-border "Add a scheduling link to publish" placeholder card with the primary "Add a scheduling link" button linking to `/settings/`.
- As a logged-in member visiting my own `/p/<username>/` while my `scheduling_url` is set AND my `is_verified=False`, I receive a 200, see no badge, and see no owner banner — the absence of the badge is the only visual signal of unverified status.
- As a logged-in member visiting my own `/p/<username>/` while my `scheduling_url` is set AND my `is_verified=True`, I receive a 200 and see the "✓ Verified" badge in the header.
- As a logged-in member visiting another member's `/p/<username>/` whose scheduling URL is empty or whose account is inactive, I receive a 404 just like any anonymous visitor — owner exception applies only to my own profile, identified by `request.user.pk == resolved_user.pk`.

---

## 6. Password change (`/settings/password/`)

- As a logged-in member I can load `/settings/password/`, submit `current_password` and `new_password` (both client-side hashed by `auth-hash.js` before submit), and on success my session remains valid and my password is changed (next login uses the new password).
- As a logged-in member submitting an incorrect `current_password`, my submission is rejected with a clean form error and the password is unchanged.
- As a logged-in member submitting a `new_password` that fails Django's password validators (e.g., too short — though after client-side hashing the wire value is fixed-length, so the validation is on the pre-hash plaintext in the browser), the form rejects locally before submit OR the server rejects on length grounds.
- As a logged-in member after a successful password change, `Profile.must_change_password` is cleared (set to `False`) if it was previously `True`.
- As an anonymous visitor visiting `/settings/password/`, I am redirected to `/accounts/login/`.
- As a member after a password change, `mail.outbox` is empty — no notification email is sent.

---

## 7. Forgot-password operator flow

- As a member who forgets my password, the platform does NOT offer me a self-serve reset link; I see no `/accounts/password_reset/` URL.
- After the operator runs `python manage.py reset_password <my-email>` and communicates the temp plaintext to me out-of-band, I can log in at `/accounts/login/` with my email and the temp password.
- After logging in with a temp password (where `Profile.must_change_password=True`), every authenticated request I make other than `/settings/password/` and `/accounts/logout/` redirects me to `/settings/password/` until I successfully change my password.
- After I submit a new password successfully on `/settings/password/`, my next request to any other authenticated page (e.g., `/settings/`) loads normally — `must_change_password` was cleared.
- After I successfully change my password from a temp password, I am NOT able to reuse the temp password for future logins (it has been replaced).
- After the operator's `reset_password` run completes, `mail.outbox` is empty — the temp password is communicated out-of-band, never via email.

---

## 8. Verified status

- As an operator running `python manage.py verify_user <member-email>` on a profile with `is_verified=False`, the profile flips to `is_verified=True`, the directory listing for that member starts rendering the badge on the next load, and the public profile page header starts rendering the badge — directory inclusion is unchanged (the profile was visible before and is still visible).
- As an operator running `python manage.py verify_user <member-email> --unverify` on a verified profile, the badge disappears from the directory card and profile header on the next load; the profile remains in the directory listing.
- As an operator using `python manage.py shell` and updating `Profile.is_verified` directly via a `QuerySet.update(...)`, the result is identical to running the management command.
- As a member I cannot self-verify my own profile through any view, form, or API — `is_verified` is not editable through the profile-edit form (see 4.7) and there is no other writable surface for it.
- The "✓ Verified" badge tooltip (`title` attribute) reads `Identity verified by the operator.` when present.

---

## 9. Operator workflows (shell-based; no Django admin)

- As an operator running `python manage.py create_user <email>`, the command interactively prompts for a plaintext password, applies the same PBKDF2-SHA256 derivation as `auth-hash.js` (using the lowercased email as salt, 100,000 iterations, 32-byte output, hex-encoded), calls `user.set_password(client_hash)`, and creates a regular user — `is_staff=False` and `is_superuser=False`.
- After `create_user` runs, the resulting user can log in via the public `/accounts/login/` form using the same plaintext password the operator typed (proving the JS-side and Python-side derivations are byte-for-byte identical).
- As an operator running `python manage.py reset_password <email>`, the user's password is updated to a hash derived from the typed temp plaintext, and `Profile.must_change_password` is set to `True`.
- As an operator running `python manage.py verify_user <email>` (or with `--unverify`), only `Profile.is_verified` toggles; no other field is mutated and `mail.outbox` stays empty.
- As an operator running the documented deactivation recipe `python manage.py shell -c "from django.contrib.auth import get_user_model; get_user_model().objects.filter(email__iexact='member@example.com').update(is_active=False)"`, the directory immediately stops listing the user, `/p/<their-username>/` returns 404 to anonymous visitors, and any active session for that user is rejected on the next request (`AuthenticationMiddleware` rejects `is_active=False`).
- As an operator re-activating a user with `is_active=True`, the user's profile reappears in the directory if their `scheduling_url` is set.
- As an operator running the documented hard-delete recipe `python manage.py shell -c "from django.contrib.auth import get_user_model; get_user_model().objects.filter(email__iexact='member@example.com').delete()"`, the `User`, the `Profile`, and all related `ProviderService` rows are removed via FK cascade; the username becomes available for re-registration.
- As an operator visiting `/admin/` in any environment, I receive a 404 — `django.contrib.admin` is not installed and no admin URL is mounted.
- As an operator I do NOT have a `createsuperuser` workflow in v1 — the README documents `manage.py create_user` as the only account-creation tool, because `createsuperuser` would store a hash of plaintext that the client-side-hashing login form can never match.

---

## 10. Data integrity & signals

- After a user is created by any path (registration form, `create_user` management command, `User.objects.create_user(...)` in shell, raw `User(...).save()`), a corresponding `Profile` row exists at the end of the request, populated via the `post_save` signal — never via an explicit `Profile.objects.create(...)` call in view code.
- Saving an existing user (`user.is_active = False; user.save()`) does NOT raise an `IntegrityError` and does NOT create a duplicate `Profile` — the `post_save` handler guards on `if created:`.
- A `User` row created with mixed-case username and email via any path (form, shell, management command) is stored with both fields lowercased — the `pre_save` signal normalizes both.
- Exactly one `ServiceCategory` row has `is_other_freetext=True` after the seed migration runs; attempting to insert a second `is_other_freetext=True` row (via raw SQL or shell ORM) is rejected by the partial unique constraint (Postgres).
- Inserting a `ProviderService` row with `is_freetext=True` and an empty `custom_description` is rejected at the DB layer by the `freetext_requires_description` CHECK constraint.
- Inserting a `ProviderService` row with `is_freetext=False` and a non-empty `custom_description` is accepted at the DB layer (the previously planned `non_freetext_forbids_description` CHECK has been deliberately removed).
- Inserting two `ProviderService` rows on the same profile with the same predefined `category` and both `is_freetext=False` is rejected by the partial `uniq_profile_category_nonfreetext` index (Postgres-only behavior).

---

## 11. Outbound link safety

- Every rendering of a user-supplied URL (`scheduling_url`, `feedback_url`) on the public profile page carries `target="_blank"`, `rel="noopener noreferrer"`, and `referrerpolicy="no-referrer"` together — verifiable in the served HTML.
- The site never auto-fetches, previews, or unfurls a member's `scheduling_url` or `feedback_url` server-side (no SSRF surface).
- Site-wide referrer policy `same-origin` is set via the `SECURE_REFERRER_POLICY` response header; clicks to outbound links additionally honor the per-link `referrerpolicy="no-referrer"` for browsers that prioritize the link attribute.

---

## 12. Security headers & transport

- Every response under production settings carries a `Content-Security-Policy` header containing `default-src 'self'; img-src 'self' data:; style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self';` — including 302 redirects, 404s, 500s, and WhiteNoise static-file responses.
- Every production response carries `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, and `Referrer-Policy: same-origin`.
- A request to `http://sadaqajariyah.online/...` is 301'd to `https://sadaqajariyah.online/...` (HTTPS redirect via `SECURE_SSL_REDIRECT`).
- A request to `https://www.sadaqajariyah.online/<path>` is 301'd to `https://sadaqajariyah.online/<path>` (canonical-host redirect, preferred at the platform layer in Render).
- Production responses carry `Strict-Transport-Security: max-age=60` on day one (short HSTS for the rollback window) and `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload` after the one-week post-launch bump.
- The session cookie is set with `Secure`, `HttpOnly`, and `SameSite=Lax`; the CSRF cookie is set with `Secure` and `SameSite=Lax` (and is not `HttpOnly` so AJAX can read it).
- Form-based POSTs without a valid CSRF token are rejected with the standard CSRF failure response.

---

## 13. No outbound email (defensive)

- After every normal flow — registration, login, logout, profile save (success and failure), password change, `verify_user`, `reset_password`, `create_user`, hard-delete, deactivation — `mail.outbox` is empty (the locmem email backend captures any accidental `send_mail` call to memory, never the network).
- Production logs show zero SMTP-attempt entries during a full smoke-test run (regression check on the no-email rule).
- No `/accounts/password_reset/`, `/accounts/password_reset/done/`, `/accounts/reset/<uidb64>/<token>/`, or `/accounts/reset/done/` URLs are mounted; requesting them returns 404.
- The `OPERATOR_CONTACT_EMAIL` value renders into the privacy notice as a plain string for human-readable contact, but the platform itself never sends mail to it.

---

## 14. Accessibility expectations

- Every page sets `<html lang="en">` on the root element; the Arabic wordmark line is wrapped in `<span lang="ar" dir="rtl">`.
- Every page exposes a "Skip to main content" link as the first focusable element; pressing Tab once on a fresh page makes the skip link visible (`:focus-visible`) and Enter jumps to `#main`.
- Every interactive element (links, buttons, form inputs, category chips, pagination links) shows a visible focus ring when reached via keyboard navigation.
- Every form input has a visible `<label>` (no placeholder-only inputs).
- Required fields are marked with both the `required` HTML attribute and a visible `*` whose `aria-hidden="true"` keeps screen readers from reading "star".
- Form errors render adjacent to their fields and are linked via `aria-describedby` (crispy-tailwind default).
- The wordmark `<svg>` carries `aria-label="Sadaqa Jariyah"`; decorative inner shapes carry `aria-hidden="true"`.
- Avatar tiles in directory rows are `aria-hidden="true"` (decorative) and the adjacent name text serves as the accessible label.
- The honeypot input has `autocomplete="off"`, a visible label `Leave this field empty.`, no `aria-hidden`, no `tabindex="-1"`; it is in the tab order but positioned off-screen.
- No page autoplays audio, video, or scrolling animation; only CSS hover transitions are present.

---

## 15. Privacy & legal page contents

- The privacy notice lists what is collected at signup (email, peppered password hash, username; IPs only in transient logs, not the DB).
- The privacy notice lists what is shown publicly: `first_name` (always), `last_name` (only when filled in), `bio`, services with their per-service descriptions, `scheduling_url`, optional `feedback_url`, and a "✓ Verified" badge if the operator has verified the account.
- The privacy notice states the platform sends no outbound email and explains that members contact the operator out-of-band at the configured `OPERATOR_CONTACT_EMAIL` for password resets, deletion, and verification requests.
- The privacy notice's anonymous-feedback section explains that submissions go directly to the third-party form provider and Sadaqa Jariyah does not see them.
- The privacy notice's cookies section names the only two cookies set (Django session, CSRF) and confirms no third-party/analytics cookies are used.
- The privacy notice states the deletion path: "contact the operator; deactivate immediately; hard-delete within 30 days."
- The terms page covers: providers attest to their identity, no commercial spam, platform is provided as-is, operator can deactivate at their discretion.
- Both `/privacy/` and `/terms/` are linked from the footer of every page.
- Bio and "Other"-description form helper text marks those fields as `World-readable.` (or equivalent visible warning) at the point of input.

---

## 16. End-to-end smoke flow (composite scenario)

This is the canonical end-to-end happy path the deployer walks through pre-launch. Each step is its own scenario and must pass independently.

1. As a new member I sign up with `Foo@Example.com` and a fresh username, the network request shows a hex client-hash in the `password` field (not plaintext), and I am auto-logged-in and landed on `/settings/`.
2. I log out and am redirected to `/`.
3. I log back in using `FOO@EXAMPLE.COM` (mixed case) and my plaintext password — login succeeds (case-insensitive email + client-side hashing parity).
4. On `/settings/` I save my first name, leave last name blank, write a 100-char bio, set a `scheduling_url` on `calendly.com` — the save succeeds with no warning banner.
5. I change `scheduling_url` to a non-allowlisted `https://my-tool.example.com/...` host — the save succeeds AND a yellow `messages.warning` banner displays. Visiting `/p/<username>/` (logged in and logged out) shows the public visitor caution panel next to the Schedule CTA. Switching back to `https://calendly.com/me/30min` and reloading removes the caution panel.
6. I add one predefined-category service (Mentoring) with `custom_description="early-career engineers"`, and one "Other" service with `custom_description="System design office hours"` — both save successfully.
7. I set `feedback_url` to a Google Forms URL — the save succeeds with no warning.
8. I visit my own `/p/<username>/` while logged in: the page renders 200 with no badge (I am unverified) and no owner banner (my scheduling URL is set).
9. I log out and visit `/p/<username>/`: the page renders 200, still no badge.
10. I visit `/` (directory) and see my profile listed (without a badge) — verification was not required to appear.
11. The operator runs `python manage.py verify_user foo@example.com`. I reload the directory and `/p/<username>/`: a "✓ Verified" badge now renders next to my name on both pages. Inclusion did not change.
12. The operator runs `python manage.py verify_user foo@example.com --unverify`. The badge disappears from both pages. Inclusion is still unchanged.
13. I (as anonymous visitor) search the directory for `engineers` and my profile appears (matching the per-service `custom_description`).
14. I (as anonymous visitor) click the "Mentoring" chip and my profile appears in the filtered list.
15. I (as anonymous visitor) click "Schedule with me →" on my profile: the link opens in a new tab pointing at the `scheduling_url`, with `noopener noreferrer` and `referrerpolicy="no-referrer"` set.
16. I (as anonymous visitor) click "Send anonymous feedback →": the link opens in a new tab pointing at the `feedback_url`, with the same outbound attributes. The feedback caution panel renders adjacent to the button with the approved copy (`This feedback form should be anonymous — ...`).
17. I log back in and unset `feedback_url` on `/settings/`. I visit `/p/<username>/`: the feedback button AND the feedback caution panel are both gone, with no empty placeholder for either.
18. The operator runs `python manage.py reset_password foo@example.com` and shares the temp plaintext out-of-band. I log out, log in with the temp password, and any request other than `/settings/password/` redirects me to `/settings/password/`. I submit a new password successfully and my next request to `/settings/` loads normally (`must_change_password` cleared).
19. I visit `/admin/` — 404 (no Django admin in v1).
20. The operator deactivates my account via the documented shell recipe. I (as anonymous visitor) try to load `/p/<username>/` — 404. The directory listing no longer includes me. My next request as a logged-in user (if my session is still in flight) bounces me to login because `AuthenticationMiddleware` rejected the inactive user.
21. The operator re-activates my account; my profile re-appears in the directory.
22. The operator hard-deletes my account via the documented shell recipe. The username becomes available; the `Profile` and all `ProviderService` rows for my account are gone (FK cascades).
23. Throughout the entire flow above, `mail.outbox` (locally) and Render's log viewer (in production) show zero SMTP-attempt log lines.
24. Throughout the entire flow above, no request body ever carries a plaintext password — every password field on every form arrives as a hex hash.

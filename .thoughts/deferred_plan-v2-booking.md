# v2 — Bringing Scheduling In-House

## Why This Plan Exists

v1 (`.thoughts/plan.md`) ships a directory of providers, each linking out to their own scheduling tool (Calendly, Cal.com, etc.). This v2 plan describes what it would take to bring that scheduling layer **into the site itself** — slot creation, public booking, cancellation, and the related notifications.

**Do not start this plan until v1 has shipped and the directory has been live for long enough to know whether offloaded scheduling is actually a problem worth solving.** Strong signals to revisit:

- A meaningful share of providers refuse to sign up for a third-party scheduler
- Community wants per-booking analytics, audit trails, or admin oversight that Calendly can't provide
- Cross-provider availability or shared calendars are needed
- The community's privacy expectations don't fit handing booker email addresses to a third party

If none of those land, leave this plan on the shelf.

---

## Scope

In v2, in addition to everything from v1, the site:

- Lets providers create one-time and weekly-recurring consultation slots
- Lets visitors book a slot **without an account**, providing only name + email
- Sends transactional email to booker and provider on booking and cancellation
- Provides a stateless cancel link in the booker's confirmation email
- Hides past, cancelled, and booked slots from public listings automatically
- Cleans up future slots when a provider's account is deactivated

The `scheduling_url` field on `Profile` from v1 stays — providers may still prefer to link out — but is now optional: a provider with at least one upcoming slot is shown with the in-site booking flow; otherwise the legacy "Schedule with me" link is used.

---

## Core Features

### Consultation Slots
- Providers create slots with:
  - Date and start time
  - Duration (custom per slot, bounded **15 minutes minimum, 4 hours maximum** — server-side validator on the form)
  - **One-time** OR **weekly recurring with end date** (v2 supports weekly only — same day-of-week and time each week)
- Recurring slots are **eagerly generated** at creation time: one `Slot` row per occurrence between the start date and end date, all linked back to a parent slot
- **Maximum recurrence span: 52 weeks** (server-side validator) to keep row counts bounded
- **DST handling:** each weekly occurrence is computed in `America/New_York` local time first (`zoneinfo`-aware datetime + `timedelta(weeks=1)` on the local datetime), then converted to UTC for storage. Computing in UTC and adding 7 days would silently shift wall-clock times by an hour twice a year.
- Booking one occurrence only removes that single instance from listings
- Booked slots automatically disappear from public listings
- **Past slots auto-hide:** public listings filter to `start_datetime__gt=now()` so expired slots disappear without any provider action or background job
- Providers can cancel any individual occurrence, or cancel a whole recurring series
  - **Cancel series semantics:** wrap the whole operation in `transaction.atomic()` and `select_for_update()` the parent row + all child rows up front, then bulk-mark unbooked children `is_cancelled=True` and run the per-occurrence cancel flow on already-booked children (notifies the booker; nothing is freed because the slot is being cancelled, not released). The row-level lock closes the race where a booking attempt lands on a child mid-cancel.
- **Editing a booked slot:** time and duration changes are blocked — provider must cancel-and-rebook (with auto-notify to the booker). Meeting-link / scheduling-link edits are allowed and trigger an "updated meeting details" email to the booker.

### Booking (Public, No Account Required)
- Visitors view a provider's profile and see their available slots
- To book: provide name + email only
- **Booking cutoff:** new bookings are accepted only up to the **end of the day before the slot's start date** (site timezone). Same-day bookings are rejected by a server-side validator on the booking form, with a clear error message
- Providers booking their own slots is allowed — no special restriction in v2
- **Per-IP rate limiting** on the booking endpoint to prevent spam/abuse (e.g., max N bookings per IP per hour, using `django-ratelimit` backed by Django's database cache). Client IP resolved via **`django-ipware`** configured for one trusted proxy hop (Render), so the rate-limit key is the real client IP and isn't spoofable by a client-supplied `X-Forwarded-For` header
- **Honeypot field** on the booking form alongside the rate limit — near-zero cost, catches dumb bots
- **Concurrency safety:** `Booking.slot` is a `OneToOneField(unique=True)`, so two simultaneous booking attempts on the same slot will fail with `IntegrityError` for the second writer — caught and shown as "slot just got booked, please pick another"
- Confirmation email is **queued to the email outbox** via `transaction.on_commit(...)`, not sent inline. The booking confirmation page tells the booker the email is on its way (rather than asserting it has already arrived), so a transient email-provider outage doesn't fail the booking. The confirmation page also displays the full booking details (provider, time, meeting link, cancel link) so the booker has everything even if the email never arrives. Email contents:
  - Slot date/time
  - Provider name
  - Meeting link
  - Provider contact info
  - **Cancel link** — stateless `django.core.signing` token over the booking PK in the URL (no DB column, no account needed). The cancel endpoint refuses with a friendly "this slot has already happened" page if `slot.start_datetime <= now()`, regardless of token validity, so leaked links can't be used after the fact
- **"I lost my email" recovery:** a small lookup-by-email endpoint (rate-limited, same outbox) re-sends the confirmation for any active bookings on that address. Without this, a lost email means a booker has no path to cancel.

### Notifications
- **Booker:** confirmation email immediately upon booking (includes meeting link + cancel link)
- **Provider:** notification email when someone books their slot
- **Provider cancels a booked slot:** booker is auto-notified by email
- **Booker cancels via cancel link:** provider is auto-notified, slot returns to public listings (the `Booking` row is **deleted**, not soft-deleted — `is_available` derives from "no related Booking", so a soft-delete would leave the slot permanently unbookable; if an audit trail is needed, copy the row to a `BookingArchive` table inside the same transaction)

### Provider Deactivation Cleanup
- When an admin sets `User.is_active=False`, an `auto_cancel_future_slots` action runs that cancels every unfinished slot owned by that user and emails any affected bookers via the per-occurrence cancel flow
- Implemented as a custom `ModelAdmin` action **plus** a `pre_save` signal that captures the prior `is_active` value and a `post_save` signal that fires the cleanup only on the `True → False` transition. Using `post_save` alone would mis-fire on every routine profile edit.

---

## Technical Stack (additions over v1)

| Layer | Technology |
|-------|-----------|
| Frontend | HTMX added on top of v1's templates + Tailwind for the slot-management UI and booking flow |
| Email | Inline SMTP backend replaced by a **DB-backed outbox table**; a `manage.py flush_email_outbox` command sends via Resend or Brevo. The booking transaction commits without waiting for SMTP. |
| Outbox scheduler | **External pinger** (cron-job.org) hitting a signed webhook that triggers `flush_email_outbox`, every 1–2 minutes. Render Cron Jobs are a paid add-on so we skip them and stay on cron-job.org from day one for fewer config branches. |
| Rate limiting | `django-ratelimit` backed by Django's database cache (`django.core.cache.backends.db.DatabaseCache`) — works on Render free tier without extra infra. Run `manage.py createcachetable` as part of v2 migrations or `django-ratelimit` silently no-ops. |
| IP resolution | `django-ipware`, configured for one trusted proxy hop |
| Timezone | `zoneinfo` (stdlib) for slot scheduling. Slot times stored as timezone-aware UTC in the DB and **always rendered in Eastern Time (`America/New_York`)** — the site-wide display timezone. `TIME_ZONE = "America/New_York"` and `USE_TZ = True` in settings; every slot listing, booking confirmation page, and confirmation email shows the time with a visible **"ET"** label so there is no ambiguity for visitors in other regions. The `"ET"` suffix is rendered literally — EST/EDT are not distinguished. |
| Email auth | **Configure SPF, DKIM, and DMARC DNS records** on the chosen domain so booking confirmation emails don't land in spam. With outbox volume now load-bearing (a missing confirmation breaks the user flow), this is no longer optional. |

---

## Database Models (additions over v1)

```
Slot
  ├── provider → User
  ├── start_datetime, duration_minutes
  ├── parent_slot (self-FK, nullable; set on each weekly occurrence pointing at the series parent)
  ├── recurrence_end_date (only set on the parent of a recurring series; max 52 weeks from start)
  ├── is_cancelled (bool, default False)
  │    — booked-ness is derived from the presence of a related Booking, not stored here
  └── is_available (property + queryset annotation: not is_cancelled AND no related Booking)
       — exposed both ways so templates and list views avoid manual joins

Booking
  ├── slot → Slot (OneToOneField, unique=True — DB-level guard against double-booking)
  ├── booker_name, booker_email
  └── created_at
       — no cancel_token column; the cancel URL carries a stateless django.core.signing token over the booking PK
       — cancellation deletes the row; optionally archived to BookingArchive in the same transaction

EmailOutbox
  ├── to_address, subject, body, template_name
  ├── created_at, sent_at (nullable), attempts, last_error
  └── flushed in batches by `manage.py flush_email_outbox` with retry/backoff
```

`Profile.scheduling_url` from v1 stays in place. A provider with at least one upcoming `Slot` row gets the in-site booking UI; a provider with none falls back to the v1 "Schedule with me" link.

---

## Migration from v1

This is the part that doesn't exist in a from-scratch plan, and is the main reason this is a separate document rather than an edit to v1.

1. **Add the new tables (`Slot`, `Booking`, `EmailOutbox`) in a single migration.** No data migration needed — every existing provider starts with zero slots and continues using their `scheduling_url`.
2. **Ship slot creation behind a feature flag** so a small group of providers can opt in and try it before the whole community sees the new UI.
3. **Profile page rendering:** if the provider has any future, available slots, show the booking UI; otherwise show the v1 "Schedule with me" button. This is a single template branch, not a global cutover.
4. **Re-enable transactional email infrastructure:** add the outbox model, the `flush_email_outbox` command, the cron-job.org webhook, and the SPF/DKIM/DMARC records before the first slot is created (otherwise the first booking sends nothing and looks broken).
5. **Add `manage.py createcachetable`** to the deploy step before any rate-limited endpoint goes live.
6. **Run end-to-end booking smoke tests** before removing the feature flag: concurrent booking on the same slot, cancel-link signing/expiry, recurring-series generation across a DST boundary, and series-cancel race with simultaneous booking. These are the four places this plan's correctness arguments actually live, so they're the four that need real tests.

---

## Future Considerations (post-v2)

- **Calendar integration:** "Add to Google Calendar" / `.ics` attachment on the confirmation email
- **Languages:** Arabic / Urdu / other community languages alongside English
- **Self-serve account deletion:** v2 should add one with a defined policy for what happens to the user's existing slots and any active bookings on them
- **Booker data retention:** add a scheduled job that deletes `Booking` rows (and their `booker_email` / `booker_name` PII) some interval after the slot end-time, with the retention window made configurable. v2's privacy notice should state the current retention behavior even before the job exists.

---

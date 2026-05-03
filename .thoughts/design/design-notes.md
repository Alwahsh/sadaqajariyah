# Sadaqa Jariyah — Design Notes (Distilled)

This file is the **implementer's reading copy** of the design bundle. The full prototype lives alongside it (`Sadaqa Jariyah - Final.html`, `final.jsx`, `data.js`, `design-canvas.jsx`); read this file first, then open the prototype only if you need to verify a detail. The user's chat with the design assistant is in `chat-transcript.md` if intent is unclear.

> **Direction the user landed on:** Communal's structure (DM Sans, dense list directory, dark sticky CTA card on the profile page) wearing Garden's warm sand + sage palette. Domain: **sadaqajariyah.online**.

---

## 1. Visual tokens

Pull these straight into your CSS/Tailwind config. They're sourced from `final.jsx` lines 8–32.

### Color
| Token | Hex | Use |
|-------|-----|-----|
| `bg` | `#F5EFE3` | page background (warm sand) |
| `bgCard` | `#FBF7EE` | card / input surfaces |
| `bgSoft` | `#EFE8D8` | hero band, signup band — slight layering |
| `ink` | `#1F2A24` | headings, body text |
| `inkSoft` | `#5C6660` | secondary text |
| `inkMute` | `#8B928C` | tertiary / footer / meta |
| `rule` | `#E2D9C5` | borders, dividers |
| `ruleSoft` | `#EBE3D1` | between-row dividers in the directory list |
| `sage` | `#6B8E73` | the live dot, accents |
| `sageDeep` | `#3F5D4A` | **primary CTA bg**, accent text on cream |
| `sageSoft` | `#D9E4D6` | service tags, selected category chips |
| `clay` | `#C28E5C` | numbered-step labels (`01`, `02`, `03`) on the home page |
| `amber` | `#B87333` | reserved warm accent (currently unused) |

Warning banner (used on Profile-edit and Owner-empty screens) is **not** part of the main palette — it's a one-off pair: bg `#FBF1D6`, border `#E8D58A`, text `#6B5418`, heading text `#3F3208`.

### Type
- Sans (everything default): **DM Sans**, weights 400/500/600/700
- Display (sparingly — body warmth, page titles can use sans, see screen specs): **Fraunces**, opsz 9..144, weights 400/500
- Mono (meta lines, URL previews, step numbers): **DM Mono**, 400/500
- Arabic (wordmark only): **Noto Naskh Arabic**, 400/500

Load via Google Fonts:
```
https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500&family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&family=Noto+Naskh+Arabic:wght@400;500&display=swap
```

Type rules from the prototype:
- Hero h1: 60px / line-height 1.05 / weight 600 / letter-spacing −0.035em / `text-wrap: balance`
- Page h1 (Directory, Profile-edit): 32–36px / weight 600 / letter-spacing −0.025…−0.03em
- Section h2: 19px / weight 600 / letter-spacing −0.02em
- Body: 14–17px / line-height 1.5–1.6 / `inkSoft`
- Eyebrow / uppercase labels: 11.5–12px / weight 600 / letter-spacing 0.06–0.08em / `inkMute` or `sageDeep`
- Mono meta lines (city · languages, URL previews): 11.5–13px

### Geometry
- Border radius: **10** for buttons & inputs, **12** for the directory list container, **14** for cards & sticky CTA
- Avatar: **rounded-12** square (not a circle), background pulled from a 4-palette rotation hashed off the name
- Buttons: 8/11/14 px vertical padding for sm/md/lg, font-size 13/14/15
- Standard page max-width: 980 px (home, profile, privacy), 1080 px (directory), 720 px (signup, login, edit, owner)

---

## 2. Brand mark

`Mark()` in `final.jsx` lines 35–43. An 8-pointed star inscribed in a `sageDeep` filled circle, the star path drawn in `bgCard` at 95% opacity. SVG viewBox 0 0 28 28; the path is:

```
M14 6 C 16 10, 18 12, 22 14 C 18 16, 16 18, 14 22 C 12 18, 10 16, 6 14 C 10 12, 12 10, 14 6 Z
```

The wordmark pairs the SVG with two stacked lines: "Sadaqa Jariyah" (DM Sans 16, weight 600, ink, tracking −0.02em) over "صدقة جارية" (Noto Naskh Arabic, sageDeep, RTL, ~12px). 12-px gap between mark and text.

---

## 3. Shared chrome

### Nav (top of every screen)
- Padding: 18px 36px, border-bottom: 1px solid `rule`, background `bg`
- Left: wordmark
- Right: links `Home`, `Directory`, `About` — active is `ink` weight 600, others `inkSoft` weight 500, gap 28
- Logged-out: "Log in" link + primary "Offer your time" sm button
- Logged-in: "Settings" link + 32-px Avatar of the user

### Footer
- Padding: 24px 36px, border-top: 1px solid `rule`, background `bg`
- 12.5px / `inkMute`
- Left: `© 2026 Sadaqa Jariyah · sadaqajariyah.online · Run by community volunteers`
- Right: `Privacy`, `Terms`, `Contact` (gap 20). After the feedback feature is added, also include a "Feedback" link here pointing at the operator's site-level feedback URL if configured (see plan.md for the full feature spec).

---

## 4. Screens (8 total)

The prototype renders each at 1100×720 in the design canvas, but every layout is fluid; reproduce them as responsive pages. Every screen has Nav above and Footer below.

### 4.1 Home (`F.Home`)
1. **Hero band** (background `bgSoft`, padding 64/36/56, border-bottom `rule`):
   - "Live count" pill: `bgCard`, border `rule`, padding 5×12, radius 999, 12.5px `sageDeep` weight 500, with a 6-px sage circle dot. Text: `{N} members offering their time`.
   - h1: `Find someone in your community to help.`
   - Sub: `A directory of community members offering mentorship, counsel, and quiet hours of their time — in the spirit of *sadaqa jariyah*, a charity that keeps flowing.` ("sadaqa jariyah" is italic + sageDeep.)
   - CTAs: primary lg `Browse the directory →`, ghost lg `Offer your time`.
2. **3-up "how it works"** grid (max-w 980, 22-px gap, padding 50/36/30):
   - `01` Browse · `02` Read · `03` Schedule. Each card: `bgCard`, border `rule`, radius 14, padding 24. Number in DM Mono 12px `clay`. Title 18px weight 600. Body 13.5px `inkSoft`.

### 4.2 Directory (`F.Directory`) — interactivity required
- Title: "Directory" / "{N} members offering their time. Search and filter to find the right person."
- Search box: full width, `bgCard`, border `rule`, radius 10, padding 12×16, with a 16-px magnifier (stroke `inkSoft`) and a "Clear" button visible only when q has content.
- Category chips row (wrap, 6-px gap):
  - All + each category from `data.js`. Each chip: 6×12 padding, radius 8, border `rule` (selected: `sageDeep`), bg `bgCard` (selected: `sageSoft`), text `inkSoft` (selected: `sageDeep`), 13px weight 500. Each chip ends with a small count.
- Listing: single rounded-12 `bgCard` panel with hairline `ruleSoft` between rows.
  - Row grid: `52px 1fr 220px auto`, gap 18, padding 18×20.
  - Avatar 44 / name 16 weight 600 / 2-line clamped bio (13/inkSoft) / mono meta line "city · languages".
  - Tag column: up to 2 service tags (`sageSoft` bg, `sageDeep` text, 11.5px weight 500, 6-radius). For an "Other" service render `m.otherText` instead of the literal "Other".
  - Action: ghost sm "View →" button.
- Empty state: padding 60, centered, Fraunces italic 17 `inkSoft`, copy: `No one matches that search yet.`
- Pagination footer: "Showing X of Y" left; `← 1 2 →` right (1 active = ink weight 600).

**Filter logic** (mirror in your backend queryset, not just JS):
- Match `q` (case-insensitive) against `name`, `bio`, and the free-text `otherText`.
- Match category by slug; treat the slug as a substring match against each service name slug-ified.

### 4.3 Public profile (`F.Profile`)
- Top crumb: small `← Back to directory` (13/inkSoft).
- Two-column grid: `1fr 320px`, gap 40, items-start.
- **Left column:**
  - Avatar 68 + name (display 34/600, tracking −0.025em) + meta mono "city · lang · lang".
  - Bio paragraph (17/1.6, max 580).
  - "Glad to help with" eyebrow (uppercase 11.5/600 inkMute tracking 0.06em) followed by service tags (sageSoft chips, 13/500, padding 7×14, radius 8). For "Other" entries render the custom description instead of the word "Other".
  - "How scheduling works." callout: `bgCard` panel, border `rule`, radius 10, padding 14×18, 13/inkSoft. Copy: `Booking happens on {firstName}'s {tool}. Sadaqa Jariyah doesn't see your appointment, your name, or your reason for booking.`
- **Right column (sticky CTA, top 20):**
  - `sageDeep` bg, `bgCard` text, padding 24, radius 14.
  - Eyebrow `Schedule a session` (sageSoft, uppercase, 11.5/600, tracking 0.06em).
  - Headline: `Book directly with {firstName}.` (display 22/600/-0.02em).
  - Primary action button: full-width, `bgCard` bg, `ink` text, 14 padding, 10 radius, 15/600. Label `Schedule with me →`. Beneath: `Opens {tool} in a new tab` (11.5/0.7-opacity cream).
  - Divider: 1px `rgba(251,247,238,0.18)` margin-top 22 / padding-top 18.
  - Three rows ("Member since", "Languages", "Tool") rendered with `Row({k, v})` — k is 60% cream, v is `bgCard` weight 500.

> **New for v1 (per user request — see plan.md §"Anonymous Feedback Link"):** under the primary CTA, render a secondary outline button `Send anonymous feedback →` that opens the profile owner's `feedback_url` in a new tab. Only render if the field is non-empty. Match the visual language of the sticky CTA card: transparent bg, 1.5px `rgba(251,247,238,0.4)` border, `bgCard` text, 14 padding, 10 radius, 14/500. Helper line under it: `Opens an anonymous form in a new tab` (11.5/0.7 cream).

### 4.4 Sign up (`F.Signup`)
- Top band: bgSoft, padding 40/36, border-bottom rule. Centered max-w 480.
  - h1 "Offer your time" (display 38/600).
  - Sub "Three minutes to set up. Free for the community, always."
- Form column: max-w 480, padding 36, gap 16.
  - Fields: Full name, Username (helper `Your profile lives at sadaqajariyah.online/p/[username]. Case-insensitive, 3–30 characters.`), Email, Password (helper `Minimum 10 characters. We never see your password — it's hashed before storage.`).
  - Terms checkbox row (13.5/inkSoft, accent `sageDeep`, default checked) — copy: `I agree to the Terms and Privacy notice.` ("Terms" and "Privacy notice" are sageDeep weight 600).
  - lg primary `Create my account`.
  - Footer line: `Already a member? Log in →` (link sageDeep weight 600, centered).

### 4.5 Log in (`F.Login`)
- Centered card, 380 wide, on bgSoft bg.
- Card: bgCard, radius 14, padding 32, border rule.
- Mark (size 36) → h1 "Welcome back" (display 26/600) → sub "Log in to update your profile or scheduling link."
- Fields: Email, Password.
- Right-aligned `Forgot your password?` (12.5/sageDeep weight 600).
- lg primary `Log in`.
- Bottom rule + centered link `New here? Offer your time →`.

### 4.6 Profile edit (`F.Edit`) — logged-in
- Crumb: `Settings · Profile`.
- h1 "Your profile" (32/600).
- URL preview line: `What appears at sadaqajariyah.online/p/ibrahim-s` — domain in mono `sageDeep`.
- Soft validation banner (yellow) appears when scheduling host isn't on the allowlist. Copy: `We don't recognize this scheduling tool — make sure the link works for visitors.`
- Form, gap 20:
  - Full name input (defaulted)
  - Bio textarea (4 rows, multiline). Helper: `World-readable. 20–1000 characters.`
  - Scheduling link input. Helper: `Calendly, Cal.com, SavvyCal, Google appointments — any tool. Must start with https://`
  - **New for v1:** Anonymous feedback link input (optional). Placeholder `https://forms.google.com/...`. Helper: `Optional. A Google Form, Microsoft Form, or any link where people can send you anonymous feedback. Visitors will see a "Send anonymous feedback" button on your public profile. Must start with https://`
  - "Services you offer" chip selector: same chip styling as the directory filter; click toggles selection. When `other` is selected, a 140-char description input appears below.
  - Footer row: primary `Save changes` + ghost `View public profile` (border-top 1px `rule`, padding-top 22, gap 10).

### 4.7 Owner — empty (`F.Owner`)
- Logged-in nav.
- Yellow banner (the same warning palette, larger): heading `Your profile is hidden from the directory` (weight 600, color `#3F3208`), body `Add a scheduling link in settings to publish it. Only you can see this page right now.` ("settings" is underlined, cursor pointer).
- Then the same profile header (Avatar 68 + name + mono meta) and bio as the public profile, but with no service tags and no sticky CTA.
- Below: a 1.5px-dashed border placeholder card (`bgCard`, radius 12, padding 24, centered).
  - 16/600 "Add a scheduling link to publish"
  - Body 13.5/inkSoft, max-w 360, centered: `Once you link Calendly, Cal.com, or any scheduling tool, your profile will appear in the directory.`
  - Primary `Add a scheduling link`.

### 4.8 Privacy notice (`F.Privacy`)
- Top band: bgSoft, padding 40/36, border-bottom rule. Max-w 680.
  - Eyebrow: `PRIVACY NOTICE` (uppercase, sageDeep, 12/600/0.08em).
  - h1: `What we hold, and what we don't.` (display 40/600/-0.03em, line-height 1.1).
  - Date line: `Last updated 3 May 2026` (mono 13 inkMute).
- Content section (max-w 680, padding 40/36/50):
  - 5 H2 + paragraph blocks separated by 1-px `rule` dividers (paddingBottom/marginBottom 22). H2 is display 19/600/-0.02em; body 14.5/1.6/inkSoft.
  - Headings + bodies are listed verbatim in `final.jsx` lines 754–771 — copy them as-is. The fifth block ("Account deactivation") references emailing the operator; keep the copy.
  - **Add a sixth block for the feedback feature:** heading `Anonymous feedback links`, body `Some members publish a third-party form (Google Forms, Microsoft Forms, etc.) for anonymous feedback. Submissions go to that form's owner under the form provider's privacy policy — Sadaqa Jariyah does not see the responses.`

The prototype does not draw the **Terms** page. Mirror the privacy page's frame and produce a short Terms page covering the bullets in `plan.md` §"Privacy & Legal Minimums".

---

## 5. Sample directory data

`data.js` exports `window.SJ_DATA` with `categories`, `members`, and `copy`. **Use these strings verbatim in any seed data, fixtures, or empty-state copy** — the user reviewed and approved them.

Categories (slug → name):
- `mentoring` → Mentoring (14)
- `counseling` → Counseling (9)
- `islamic-education` → Islamic Education (22)
- `quran-tutoring` → Qurʼan Tutoring (18)
- `career-advice` → Career Advice (11)
- `arabic-language` → Arabic Language (7)
- `marriage-guidance` → Marriage Guidance (5)
- `other` → Other (13) ← this is the `is_other_freetext=True` row

The 9 sample members are realistic, name-diverse, and have hand-written bios — keep them as fixtures for the staging environment, but **do not seed them into production**. Counts in the chips are illustrative; let the live counts come from the DB.

`copy.tagline`, `copy.sub`, `copy.cta`, `copy.browse`, `copy.join`, `copy.scheduling_note` are the canonical strings.

---

## 6. Implementation hand-offs

The user wants this built per `.thoughts/plan.md` (Django + Tailwind, deployed on Render). This design notes file is purely a visual/copy reference; the technical contract is in plan.md. Cross-references to keep tight:

| Plan section | Design touchpoint |
|---|---|
| §"User Accounts" — username rules | Profile-edit "What appears at sadaqajariyah.online/p/[username]" preview |
| §"Public Profiles & Discovery" — directory page | Directory list-row design (4.2) and the empty-state Fraunces italic copy |
| §"Scheduling Link Validation" — soft warning | Profile-edit yellow banner copy (verbatim) |
| §"Anonymous Feedback Link" *(new)* | Public-profile secondary CTA + Profile-edit form field + Privacy notice block |
| §"Profile Owner exception" (Phase 2) | Owner — empty screen (4.7) — same banner palette |
| §"Privacy & Legal Minimums" | Privacy page (4.8) — copy is approved, lift it directly |

If you find a contradiction between this file and `plan.md`, **plan.md wins for behavior; this file wins for visual treatment**.

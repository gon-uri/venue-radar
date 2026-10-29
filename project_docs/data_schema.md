# Conference Data Reference

Reviewed against the implementation: 2026-10-29.

The validators in `scripts/validate.py`, `scripts/catalog_metadata.py` and
`scripts/conference_scopes.py` are the executable contract. This guide explains
how to author correct data, including editorial rules stricter than validation.
It does not replace [the addition checklist](adding_conferences.md) or
[the refresh workflow](data_maintenance.md).

## Editions And Series

`data/conferences.yml` is a YAML list: one record per edition, not per deadline.
The exact `series` string joins families, scopes, ranks and rates. A new annual
edition gets a new `id` and year while retaining its series identity. Keep past
editions; do not overwrite last year's record with next year's dates.

### Required Edition Fields

| Field | Authoring rule |
| --- | --- |
| `id` | Unique lowercase letters/numbers/hyphens, normally series slug plus year. Immutable once published. |
| `series` | Stable exact series key, reused in all series-level mappings. |
| `year` | Integer identifying the edition, even if submission happens in the preceding year. |
| `title` | Full official conference name. |
| `short_title` | Display acronym/name plus edition year. |
| `website` | Official edition/organizer URL. |
| `conference_start`, `conference_end` | ISO dates, with end on/after start. Dates are required; `TBA`/null is not valid here. |
| `topics` | One to four distinct central leaves from `data/topics.yml`; the cap is not a target. |
| `size` | `S`, `M`, `L`, `XL` or `XXL`; qualitative scale, not an attendance guarantee. |
| `submission_type` | Descriptive text about contribution/publication format, not the status/actionability switch. |
| `deadlines` | List of milestone mappings; `[]` is valid when no reliable submission date is known. |
| `last_checked` | ISO date of actual source review, not merely the edit/build date. |
| `confidence` | Meeting-date evidence; use `confirmed` or `estimated` for new ordinary records. |

### Recommended Edition Fields

| Field | Authoring rule |
| --- | --- |
| `cfp_url`, `source_urls` | Direct CFP/date/source pages. Every new record should have evidence; confirmed meeting dates require a nonempty `source_urls` list. |
| `location` | Clear city/country string, or `To be announced`; add its exact alias to `data/cities.yml` when confirmed. |
| `mode` | Existing conventions: `in-person`, `hybrid`, `online`. Online meetings do not enter the map. |
| `timezone` | IANA meeting-location zone, not a replacement for each deadline's explicit UTC offset. |
| `relevance` | Optional `high`, `medium`, `low` or `watch`; not an acceptance prediction. |
| `notes` | Evidence conflicts, estimation basis, special eligibility, scope/publication caveats and size basis. |

The schema also accepts legacy `announced_no_deadlines`, `not_yet_announced`
and `stale` meeting states. Do not bulk-normalize existing records. Prefer a
confirmed meeting plus `deadlines: []` for a known meeting with an unknown call;
this avoids conflating meeting certainty with submission evidence.

If no next meeting date or defensible recurrence proxy exists, keep the latest
verified historical edition and document the missing next announcement. Do not
invent dates just to satisfy the required fields or make a row appear upcoming.

## Milestone Fields

| Field | Requirement and meaning |
| --- | --- |
| `type` | Required unique stable type within this edition; its slug forms the event UID. Actionability requires a supported type below. |
| `label` | Required human-readable track/action, distinguishing abstracts, papers and production steps. |
| `datetime` | Required ISO datetime. Author new cutoffs with an explicit UTC offset; do not rely on the execution machine's zone. |
| `source_url` | Direct supporting page. Required by validation for confirmed editions; supply it for every new milestone, including estimates. |
| `confidence` | Optional `confirmed`/`estimated` override; otherwise inherits the edition's confidence. |
| `time_precision` | Optional `exact` (default) or `date` for a known day with an unknown cutoff hour. |
| `gate_for` | Exact type of another, later supported submission in this edition; only when that earlier step is mandatory. |
| `opens_at` | Published opening datetime for this action, with offset and supporting evidence; never a guessed opening. |
| `open_observed_on` | ISO day when this action's live submission portal was actually verified open. |
| `cutoff_note` | Optional, at most 200 characters, only when official sources state conflicting cutoffs. `datetime` then holds the earliest stated instant. The page shows an asterisk and the note; ICS adds it to the description. |

Quote dates/datetimes in YAML for consistency. Use `-12:00` only for explicit
Anywhere on Earth evidence or a documented provisional assumption, not as the
default for every exact cutoff. When official sources state conflicting
cutoffs (for example "Pacific Time (GMT-8)" in a PDT month, or two pages with
different hours), store the earliest stated instant and explain the conflict in
`cutoff_note` (ADR-040); keep longer evidence in `notes`. Never convert silently.

### Four Independent Questions

1. Is the meeting timing confirmed? Set edition `confidence` from meeting evidence.
2. Is this deadline date confirmed? Override the milestone confidence when it
   differs, including a confirmed call on an otherwise estimated meeting.
3. Is its cutoff hour known? For a known day without an hour, use
   `time_precision: date` and a documented provisional end-of-day datetime.
   The site shows `(time est.)`; ICS exports an all-day event. When that
   datetime is 23:59 AoE and the host city's `tz` (or a real edition
   `timezone`) is known, the countdown and closing use 23:59 in that zone on
   the same day, which is never later than AoE (ADR-040).
4. Is this action's portal known to be open? Record `opens_at` only for an exact
   published opening, or `open_observed_on` after checking the live portal.
   If only an opening day is published, retain it in notes until its precise
   time or actual opening can be verified; do not fabricate midnight.

Estimated dates stay estimated even with exact-looking timestamps. Do not
mark a known deadline day estimated just because its hour is unknown.

### Supported New-Contribution Types

Only the following `SUBMISSION_TYPES` in `scripts/validate.py` can become
terminal new-contribution opportunities:

```text
full_paper regular_paper short_paper workshop_paper special_session_paper
abstract late_abstract extended_abstract poster
journal_paper discussion_paper resource_paper
```

The contribution must actually be available to fresh submissions. Restricted
invited revisions, paper updates, ARR commitments, camera-ready uploads,
notifications, registration/payment and workshop/minisymposium proposals use
descriptive schedule-only types. A real workshop *paper* can be actionable;
organizing a workshop is not the same thing. A `poster` means a new poster
contribution, not uploading artwork for an already accepted presentation.

Important: validation permits custom type strings for schedule details, but
the website will not recognize `main_full_paper` or `full_paper_round_3` as a
submission merely because its name contains "paper". Types must be unique
within an edition, including after slug normalization. Use an appropriate
existing supported type for each independent route. If the current vocabulary
cannot represent a call faithfully, seek a scoped schema/UI decision and tests;
do not silently use an unsupported custom type or redefine a published type.

### Mandatory Gates And Independent Tracks

An abstract required before a paper needs `gate_for: full_paper` (or its exact
supported target type). Its date must precede the target. The gate is not a
separate terminal opportunity: once it expires, fresh submissions to that
route close even if the paper deadline remains ahead.

An independent presentation abstract or alternate paper track has no
`gate_for` unless it genuinely gates another contribution. Do not link an
optional abstract to the main paper. Keep independent tracks distinct, as in
AAMAS main/Blue Sky or WACV rounds. With multiple mandatory steps, each points
directly to the terminal route; the display uses the earliest required action.
Put opening evidence on that action, not only on its eventual paper deadline.

## Public Status Contract

Status, countdown and collapsed milestone use the same next eligible route
and required author action. See ADR-032 and the browser route fixtures.

| Evidence | Public state | In submission-options filter? |
| --- | --- | --- |
| Confirmed future action, opening verified | Green `Open ... submissions` | Yes |
| Confirmed action, explicit future opening | Green `Scheduled submission` | Yes |
| Confirmed action, opening unverified | Green `Submission opportunity` | Yes |
| Estimated action or mandatory eligibility | Yellow `Submission opportunity (estimated)` | Yes |
| Only expired/blocked supported routes | Red `Closed to new submissions`; Time left says `Closed` | No |
| No supported submission deadline recorded | Grey `Deadline unannounced`; no submission countdown | No |

Opening dates, organizer proposals and production deadlines remain expanded
schedule details, never submission countdown targets. Closed/unannounced rows
retain their next chronological schedule milestone when showing all. At
conference start the edition leaves Upcoming Deadlines and joins the separate
ongoing/past conference section. The client re-evaluates these states each minute.

Abstract-only formats remain documented in `submission_type`, labels, notes
and evidence documents. An abstract book is not a full-paper proceedings claim.
Do not add a publication column, badge or change to status behavior without
approval; current abstract labels/status already indicate the contribution.

## Companion Files And Stable Identity

- `conference_families.yml`: mandatory one-to-three central family IDs per exact
  series, not inferred from the presence of a generic ML leaf.
- `conference_scopes.yml`: optional sourced profile, zero-to-six additional
  leaves and at most 1,200 characters of characteristic prose. New series should
  receive a reviewed profile where evidence exists; absent is better than guessed.
  See [the exact five-field schema](conference_scopes.md).
- `cities.yml`: exact location aliases, approximate city centers and a valid
  IANA `tz` per city (used for day-only cutoffs); distinguish different cities
  sharing a name. Confirmed/announced, mapped, non-online future
  meetings appear on the map; estimated dates do not.
- `icore_rankings.yml`: release, review date, official source and exact-series
  `rank`/`portal_id` mapping. `ccf_rankings.yml` additionally separates catalog
  PDF/page evidence from its official navigation `page_url`.
- `acceptance_rates.yml`: historical `year`, `track`, HTTPS source and `percent`
  on a 0-100 scale; use `approximate` for rough published evidence. Qualitative-only
  entries require a supported `band` and sourced `basis`. Missing stays Unknown;
  neither ranks nor abstract acceptance are proxies for full-paper selectivity.
- `metadata.yml`: `last_updated` is a dataset-review date, not a build timestamp.
  Update it before generating reviewed data, not for a documentation-only change.

UIDs are `<id>-conference@scientific-conference-calendar` and
`<id>-deadline-<type-slug>@scientific-conference-calendar`. Correct dates, labels
and sources in place; preserve IDs/types and the historical namespace after
rebrands. Topic feeds use stable leaf slugs; series feeds (`docs/series/`) use
the slug of the exact `series` key, so changing a series key moves its feed. A genuinely new route needs its own
unique type; changing a type is an identity migration, not cosmetic cleanup.

CI's identity check (`scripts/check_identity.py`) fails when a published event
UID or edition ID disappears. An intentional, reviewed removal needs an entry
(`id`, `reason`, ISO `date`) in `data/retired_identities.yml`; a retired edition
ID also covers its generated UIDs. Never reuse a retired ID.

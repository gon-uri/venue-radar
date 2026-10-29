# Data Maintenance

Last synchronized: 2026-10-08.

Use this guide to refresh tracked information. For a new series/edition use
[adding conferences](adding_conferences.md); for fields and submission semantics
use [data schema](data_schema.md). [Development](development.md) owns build,
workbook, browser and publication commands. The database is canonical YAML;
the website never refreshes organizer information automatically.

## Monthly Refresh Checklist

1. Check the working tree and current project state. Run the read-only report
   from the repository root; use an explicit review date when reproducibility
   or the execution host's timezone matters:

   ```sh
   python3 scripts/maintenance_report.py --as-of YYYY-MM-DD --max-age-days 30
   ```

   Replace `YYYY-MM-DD` with the actual review date. Omitting `--as-of` uses
   the host's current date, which is not necessarily the user's local date.
2. Review the edition, acceptance and scope queues using official sources.
   Check current CFP/date pages even when a plausible proxy already exists.
   Recheck final extensions, cutoff zones, mandatory gates, opening evidence,
   meeting/location changes and production steps. An aggregator is discovery
   evidence, not a substitute for the official edition's instructions.
3. Correct the owning YAML file, preserving published edition IDs, deadline
   types and series keys. Record direct evidence and uncertainty notes. Change
   confirmed/estimated flags per fact, not with a blanket confidence promotion.
4. Update `last_checked` only for edition sources actually reviewed; separately
   update `scope_last_checked` after scope review and rank/rate `checked_on`
   after reviewing that evidence. A failed fetch is not proof the old facts are
   still correct; record the failed attempt/conflict in notes and retain uncertainty.
   Do not bulk-stamp untouched records as fresh.
5. Set `data/metadata.yml`'s `last_updated` to the dataset-review date **before**
   rebuilding. This describes the published dataset review, not a claim that
   every tracked source was checked that day. Documentation-only changes do
   not advance it.
6. Synchronize the XLSX mirror if exported latest-series fields, vocabulary,
   profiles, ranks or rates changed. Validate/test/build, inspect the affected
   public behavior/feeds and update project documentation. Follow
   [development's release checklist](development.md#publication-checklist)
   when publishing is requested.

### What The Queues Do And Do Not Prove

- Edition queue: provisional/estimated upcoming records, stale reviews, empty
  deadline lists and latest past editions with no tracked successor. The
  special joint IJCAI-ECAI series does not demand a same-name successor.
- Acceptance queue: missing sourced evidence or evidence more than two years
  old. It does not infer a rate or selectivity band.
- Scope queue: missing/stale profiles and profiles based on an earlier edition;
  an edition review does not silently refresh scope evidence.
- These are advisory checks, not scrapers. They do not validate URL reachability,
  resolve conflicting official pages, detect every missing submission in a
  nonempty schedule-only list, or verify historical statistics. Review those
  cases editorially and never claim that an empty queue proves data accuracy.

## Estimates And Next Editions

Preview supported recurrence without changing files:

```sh
python3 scripts/rollover_editions.py --as-of YYYY-MM-DD
```

The helper considers each series' latest tracked edition only after it has
ended. `CADENCE_YEARS` is an explicit allowlist, not a recurrence guesser:
annual, biennial and IFAC SYSID's triennial patterns are configured separately.
It skips already tracked next editions, advances by that cadence, and accounts
for leap-day shifts. Irregular/joint/workshop series require individual review.

Only after checking cadence and official sources, append reviewed drafts with:

```sh
python3 scripts/rollover_editions.py --as-of YYYY-MM-DD --write
```

Important: `--write` appends **all** candidates in the preview, not a selected
series, and writes canonical YAML. It never overwrites an existing edition ID.
If only a subset is approved, add those reviewed records manually instead.
Inspect the diff immediately, validate it and do not publish untouched drafts.

The helper copies prior fields/milestones, shifts timing, marks estimates,
sets location unannounced, removes `open_observed_on`, and may shift prior
`opens_at`. That shifted opening is a proxy, not observed or confirmed evidence.
Review/remove unsupported opening/track/publication assumptions, extensions,
timezones and obsolete milestones; replace prior-edition links where a current
call exists. Its automatic review date is not a substitute for actual review.
Shared scope/rank/family mappings are not duplicated into the edition.

A defensible proxy can remain useful with estimated confidence. If recurrence
or next-edition timing cannot be supported, keep the latest historical edition
and its review item instead of inventing future dates or an annual pattern.

## Deadline And Opening Review

Follow [the field and status contract](data_schema.md#milestone-fields).
Meeting confidence, individual deadline certainty, cutoff precision and portal
opening evidence are independent. In particular:

- A confirmed meeting can have an estimated paper deadline or no known call.
- A known deadline day with an unknown hour uses `time_precision: date`; it is
  not an inferred day. Document the provisional ordering timestamp.
- A day-only opening stays in notes until an exact published time or live
  portal can be verified. Do not manufacture midnight `opens_at`.
- Mandatory abstract/registration gates close fresh submission routes when
  they pass. Independent abstracts do not gate unrelated papers.
- Open/Scheduled/Submission opportunity are evidenced green states; unknown
  opening is the honest Submission opportunity fallback, not an Open claim.
- Workshop proposals, commitments, revisions and camera-ready dates remain
  schedule details, not fresh research-contribution countdowns.
- Abstract books/archives are not full-paper proceedings. Keep format caveats
  in labels, descriptive metadata and project notes; current UI stays intact.

## Topics, Profiles And Locations

Use [topic audit](topic_audit.md) and [scope curation](conference_scopes.md).
Keep the eight agreed families and stable leaf slugs. Whole-family filters use
central series identities, not any incidental ML method; individual leaves
use the curated primary/additional union. Main tags cap at four, extras at six;
these are limits, not targets. Never import an exhaustive CFP inventory.

Only confirmed cities get exact `location` aliases and approximate centers in
`data/cities.yml`. Distinguish homonymous cities; do not guess hosts, silently
geocode ambiguous strings or claim venue-level accuracy. Future confirmed/
announced non-online meetings appear on the map; estimates and ongoing/past
meetings do not. The submission-options filter is deadlines-only.

The workbook is a review mirror of each series' latest edition, not a second
source to import silently. Its three tables are catalog, vocabulary and scopes.
Date-only/meeting dates are not separate workbook columns; a date-only correction
may leave mirrored values unchanged. Follow [workbook synchronization](development.md#workbook-synchronization)
for export, native-table preservation, visual/error checks and re-import.

## Ranking And Acceptance Evidence

Match exact main-track series to the configured official releases. Never
borrow a rank from a parent workshop venue, joint edition, homonymous acronym
or old ranking list. Missing mappings show a dash/Unranked filter state, not C.
Keep CCF PDF/page provenance separate from the public navigation webpage.

Re-audit ranks when the publisher changes its list; a new release also requires
updating the validator's release rules, metadata, links, tests and mirror.
A review-date edit alone does not migrate a ranking release.

Historical acceptance evidence must retain year, actual track/population,
source and any approximation. Abstract acceptance is not full-paper selectivity.
The numerical bands, implemented in `validate.acceptance_band`, are:

| Band | Historical rate |
| --- | --- |
| Very low | under 20% |
| Low | 20% to under 30% |
| Moderate | 30% to under 40% |
| High | 40% to under 60% |
| Very high | 60% or above |

A sourced qualitative-only entry needs `band` and `basis` and displays
`(estimated)`. Otherwise leave the series absent/Unknown. Do not derive rates
from rankings, the retired Difficulty field, reputation or accepted-only lists.

## Evidence Follow-Ups

Consult the dated records rather than maintaining a second competing list:

- [Candidate backlog](conference_candidates.md): approval/aliases and deferred
  venues; candidates are not confirmed calendar data.
- [AI/vision expansion](vision_ai_expansion.md): FG/IJCB extensions/openings,
  conflicting ICCV dates, biennial editions and rate limitations.
- [Language/robotics expansion](nlp_robotics_expansion.md): ARR versus commitments,
  RSS gates, proposed SIGIR/SMC dates and irregular NAACL/COLING/IJCNLP cadence.
- [Complex-systems/neuroscience expansion](dynamics_neuroscience_expansion.md):
  abstract-only evidence, ICCN conflicts, BioCAS route and unannounced regional calls.

These are dated review priorities. Recheck against current sources; do not
interpret an older phrase such as "upcoming" or "closed" as today's live status.

## Project Services

### Community Setup

Giscus is optional public GitHub Discussions integration. The owner of a fork
must enable Discussions, install the [Giscus app](https://github.com/apps/giscus)
for that repository, choose a category and verify the rendered live widget.
The maintained configuration lives in `assets/site.js`. It uses repository ID
`R_kgDOTQKmZg`, Announcements ID `DIC_kwDOTQKmZs4DHLTi`, and specific mapping term
`Venue Radar community` for this repository. Preserve that mapping during
routine edits; changing it can create a new comment thread. GitHub sign-in is
required. The direct Discussions link and request form work independently.
Existing setup verification is a historical baseline, not something rechecked
by a build. Recheck the official configuration when changing these services;
private session notes are not required for that workflow.

### Repository Rename

Current repository: https://github.com/gon-uri/venue-radar
Current Pages site: https://gon-uri.github.io/venue-radar/

A future rename requires updating public links, Giscus's repository name,
regression expectations and Git origin, then checking Pages configuration/live
comments/downloads. Preserve Giscus IDs/mapping and the historical
`scientific-conference-calendar` UID namespace. Download paths remain relative;
subscribers must update obsolete absolute feed URLs. A repository redirect
is not a Pages/feed redirect. Use the release checklist, not a blind global
replacement of every historical namespace or dated evidence record.

# Architecture

Last synchronized: 2026-10-29.

## System In Brief

Venue Radar is versioned YAML plus Python generators and a self-contained static
HTML page. GitHub Pages publishes committed `docs/` from `main`. There is no
SQL database, backend, paid hosting or OpenAI API dependency. Python/PyYAML are
the required build tools. CI also runs Node's built-in test runner on the client
logic; optional Node tools support workbook/branding/browser QA.

Repository: https://github.com/gon-uri/venue-radar
Website: https://gon-uri.github.io/venue-radar/

```text
reviewed YAML + local assets
        -> validate.py + Python tests
        -> build_all.py
        -> committed docs/index.html + ICS feeds
        -> GitHub Pages (main/docs)

YAML -> export_catalog.py -> sync_workbook.mjs -> review-only XLSX mirror
```

Organizer pages are reviewed by maintainers, not fetched by the website.
No map tiles, geocoder or organizer API is called at runtime. The optional,
lazily loaded Giscus client uses public GitHub Discussions; it is not a project
backend. No calendar/ranking/filter feature depends on it.

## Source Ownership

| Path | Owns |
| --- | --- |
| `data/conferences.yml` | Edition identities, meeting dates, milestones, evidence, confidence, main display topics. |
| `data/topics.yml` | Stable controlled leaf vocabulary. |
| `data/topic_families.yml` | Eight-family IDs/names/order, leaf ownership and compact display labels. |
| `data/conference_families.yml` | One-to-three central family identities per exact series. |
| `data/conference_scopes.yml` | Sourced series prose, curated extra leaves and independent review date/year. |
| `data/cities.yml` | Exact location aliases, approximate city centers and each city's IANA time zone (`tz`). |
| `data/icore_rankings.yml` | Direct current-release series ranks and official portal IDs/evidence. |
| `data/ccf_rankings.yml` | Direct series ranks, PDF/page evidence and separate navigation webpage. |
| `data/acceptance_rates.yml` | Historical track/year/percentage or sourced qualitative-only bands. |
| `data/metadata.yml` | Published dataset review date. |
| `data/retired_identities.yml` | Reviewed list of intentionally retired edition IDs or event UIDs (normally empty). |
| `data/core_conferences_normalized_tags.xlsx` | Latest-series catalog, vocabulary and scope review mirror; not canonical data. |
| `assets/` | Embedded site CSS/JS, logos, favicon, font, map geometry, link-preview card and vendor notices. |
| `docs/` | Generated public HTML and ICS only; never edit by hand. |
| `project_docs/` | Public handbook, source evidence and technical decisions. |
| `private_notes/` | Optional gitignored working logs, brainstorming and design/copy history; not a build input. |
| `.github/ISSUE_TEMPLATE/` | Public conference request and correction forms. |
| `.github/workflows/build.yml` | CI: validation, Python and Node unit tests, build, then docs-drift, inline-script and identity checks. Never commits. |
| `.github/workflows/maintenance-report.yml` | Weekly rewrite of the single "Review queue" issue. Never commits. |
| `.github/pull_request_template.md` | Publication checklist for pull requests. |

Each record is an edition; shared maps join by exact `series`. Ranks/rates/scopes
are not copied into each edition. See [data schema](data_schema.md) for fields
and [adding conferences](adding_conferences.md) for all companion updates.

## Code Ownership

| Module | Responsibility |
| --- | --- |
| `scripts/validate.py` | Edition/rank/rate validation, date parsing, slugs, supported submission types and acceptance bands. Its CLI also validates families/cities/scopes. |
| `scripts/catalog_metadata.py` | Family/city and complete series-family validation; confirmed-city event payload. |
| `scripts/conference_scopes.py` | Profile validation, deduplicated topic union and missing/stale/prior-edition scope queue. |
| `scripts/build_ics.py` | Escaped/folded VCALENDAR output, stable ordering/UIDs, exact and all-day deadline events. |
| `scripts/build_site.py` | HTML/table/milestone generation, head metadata, icon sprite, evidence lines and host-zone cutoff instants. Embeds the assets below and a small JSON config. |
| `assets/logic.js` | Pure client logic: search normalization, countdown text, UTC/local clocks and submission-route state. Unit-tested in `tests/js/`. |
| `assets/core.js` | Page wiring: filters, URL state and deep links, starring, row ordering, next-step/successor lines, empty states and the minute refresh. |
| `assets/site.js` | Mobile cards, family/leaf matching, calendar menu, offline map and optional Giscus loading. |
| `assets/base.css`, `assets/site.css` | Base tokens and layout, then brand/mobile/feature styling; embedded in that order. |
| `scripts/build_all.py` | Validate source data, build ICS and standalone HTML. Run the standalone validator too; do not skip registry checks. |
| `scripts/maintenance_report.py` | Read-only edition queue with urgency tiers, advisory checks, and acceptance/scope backlogs (text, markdown or JSON). |
| `scripts/source_check.py` | Manual, networked check of cited URLs and successor pages. Report-only; never run in CI. |
| `scripts/check_identity.py` | Fails when a published UID or edition ID disappears without a retirement entry. |
| `scripts/release_check.py` | Local release gate: validation, tests, build, determinism, docs drift, whitespace, private notes and dataset freshness. |
| `scripts/rollover_editions.py` | Preview or explicitly append cadence-based estimates; never overwrites existing edition IDs. |
| `scripts/export_catalog.py` | JSON export of each series' latest edition, ranks/rates, vocabulary and profiles. |
| `scripts/sync_workbook.mjs` | Optional artifact-tool workbook synchronization, table/style preservation, checks and previews. |
| `scripts/recolor_logo.mjs`, `scripts/build_readme_banner.mjs`, `scripts/build_social_card.mjs` | Optional tools deriving brand outputs from immutable sources and the real title font. |
| `tests/test_*.py` | Unit/data/rendering/workflow/documentation regressions. |
| `tests/js/*.test.mjs` | Node built-in-runner tests for `assets/logic.js`. |
| `tests/browser_smoke.mjs` and imported suites | Interactive desktop/mobile, route, map and overflow regressions using a frozen reference date. |

Client code lives in `assets/` (ADR-040). Pure functions that need no page go
in `logic.js` with a unit test; code that reads or changes the page goes in
`core.js` or `site.js`. The generator emits markup, the `#venue-config` JSON and
the asset contents in this order: map data and site.js, config, logic.js and
core.js, then Leaflet. Prefer these boundaries; a documentation cleanup is not a
reason to move behavior.

## Generated Outputs And Identity

- `docs/index.html`: standalone HTML with embedded local logo, radar favicon,
  Audiowide font, CSS/JS, pinned Leaflet and Natural Earth land geometry. Its
  link-preview image is `assets/branding/social-card.png`, served from the
  repository's `main` branch because `docs/` holds only generated output.
- `docs/calendar-all.ics`: meeting dates plus recorded deadlines.
- `docs/deadlines.ics`: recorded deadlines, including schedule-only steps.
- `docs/conferences.ics`: meeting dates only.
- `docs/submissions.ics`: supported fresh-submission deadlines and their mandatory gates.
- `docs/tags/<leaf-slug>.ics`: topic-union events, not broad central-family feeds.
- `docs/conferences/<edition-id>.ics`: one edition's meeting and milestones.
- `docs/series/<series-key-slug>.ics`: every edition of one series; subscriptions
  roll forward as new editions are added. Keyed by the exact `series` value.

Every feed asks clients to refresh daily (REFRESH-INTERVAL/X-PUBLISHED-TTL).
The header's Subscribe to calendar menu offers Google/Apple/copy-link/download
for the aggregate, topic and series feeds (ADR-039).

All recorded milestones can enter ICS even if they are not fresh-submission
opportunities. The website's opportunities checkbox does not rewrite downloads.
Date-only cutoffs export all-day events. A `cutoff_note` is added to the event
description. UTF-8 line folding and CRLF are
intentional; do not trim folded content spaces as cosmetic whitespace fixes.

Published edition IDs/deadline types determine UIDs. Keep the historical
`scientific-conference-calendar` namespace despite the repository rename.
Correct timing/source/labels in place without creating duplicate subscription
identities. Topic slugs and Giscus IDs/mapping are similarly durable.

## Current Browser Contracts

- Shared search, sizes, independent ICORE/CCF ranks, acceptance bands and topics
  filter both tabs and the map. OR applies within each metadata group; separate
  metadata groups combine with AND.
- Whole-family selection matches curated central identities; partial leaf
  selection matches the primary/additional union with OR within a family and
  ANY/ALL across selected families. Selecting every child equals the parent.
  Tables show at most four main topics; scope prose is searchable.
- Status, countdown and collapsed milestone share the same next required author
  action. Mandatory gates precede paper deadlines and can close that route.
  Organizer proposals, openings and production dates stay schedule-only.
  Exact status/evidence rules are in [data schema](data_schema.md#public-status-contract).
- Show submission options only defaults checked and includes open, scheduled,
  confirmed opening-unverified and estimated routes. It is deadlines-only.
  Clear filters removes every restriction, including that checkbox.
- At meeting start, the edition leaves Upcoming Deadlines and the future table;
  ongoing/past editions remain in a separate collapsible conference table.
  Map markers require confirmed/announced, mapped, non-online future meetings.
- Mobile is up to 760px: compact cards put the name and countdown (or dates)
  on the first row with status and next step below, plus independent More info
  disclosures. Desktop keeps all columns under a sticky header, with topics on
  one wrapped line. Filters start collapsed only on mobile. Resizing
  preserves the user's disclosure choices; no-JS retains full metadata access.
- Abstract-only publication formats use existing milestone/status wording and
  documented notes, not a new column or filter (ADR-036).
- Confirmed exact cutoffs show their stored clock ("23:59 AoE", "20:00 UTC")
  and the viewer's local time; estimated/date-only ones never show an hour.
  Mobile cards repeat the counted-down action under Time left (ADR-039).
- Search is accent-insensitive and requires every word; short words match word
  starts. Empty views explain hidden closed/unannounced matches; closed rows
  link to a tracked successor edition. Re-renders never move focused rows.
- A day-only cutoff stored as 23:59 AoE counts down to 23:59 in the host city's
  zone (cities.yml `tz`, else a real edition `timezone`) on that day, never
  later than AoE; the tooltip names the zone. A cutoff with a `cutoff_note`
  shows an asterisk and the note (ADR-040).
- Rows have stable anchors: `#<edition-id>` opens that edition and
  `#<series-slug>` the series' next edition, revealing it if filters hide it.
  Filters, search, match mode, tab and toggles live in the query string; a
  followed hash is dropped once the visitor changes the view. Series
  can be starred per browser (localStorage `venue-radar:starred`), with a
  Starred only filter and feed shortcuts. Expanded schedules and mobile More
  info show an evidence line: sources, review date, Copy link and a prefilled
  correction form.

UI dimensions/colors and their approved history are covered by source assets,
regression tests and ADR-022/024/025/032-036, not repeated in every handbook file.
Selected copy lives in [site copy](site_copy.md) and [sharing](sharing.md);
selected assets/provenance in [branding](branding.md).
Licensing: MIT code, CC BY 4.0 original content/artwork, preserved vendor notices.
Both licenses permit commercial reuse with their respective notices/attribution.

## Change And Publication Boundaries

Maintainers review official sources, edit owning YAML, update actual review
dates, synchronize mirrored fields, validate/test/build, inspect results and
commit source/output together when publishing. CI validates, runs the Python
and Node unit tests and rebuilds. It fails when committed `docs/` differ from
the fresh build, when an inline script has a syntax error, or when a published
identity disappears without a retirement entry. It does not scrape sources,
refresh evidence, enforce freshness, or commit its build output. Pages serves
the committed files, not CI's working copy.

Use [data maintenance](data_maintenance.md), [adding conferences](adding_conferences.md)
and [development](development.md) for commands and acceptance criteria. Current
state and release verification belong in [implementation status](implementation_status.md),
future work in [roadmap](roadmap.md), and technical rationale in [decisions](decisions.md).
Detailed working logs stay local under the [documentation policy](documentation_policy.md);
private notes are never a required input for agents, contributors or builds. Follow
[AGENTS.md](../AGENTS.md) and the [documentation index](README.md), not a requirement
to read every historical proposal before a small change.

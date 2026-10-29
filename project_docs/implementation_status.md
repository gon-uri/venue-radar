# Implementation Status

Last synchronized: 2026-10-29. This is the current-state summary, not a release
history. Start with [the documentation index](README.md); technical history
remains in [decisions](decisions.md). Detailed local working notes follow the
[documentation policy](documentation_policy.md) and are not required to onboard.

## Current Snapshot

| Item | Current state |
| --- | --- |
| Repository | `gon-uri/venue-radar`; GitHub Pages publishes `main/docs`. |
| Website | https://gon-uri.github.io/venue-radar/ |
| Architecture | Reviewed YAML + Python generators + standalone static HTML/ICS; no backend or SQL database. |
| Catalog | 198 edition records across 130 distinct series, including 30 next editions added 2026-10-29 (28 estimated; ICDM 2027 and ACC 2028 confirmed), the user-requested AIiH 2027 and SD4H 2026 as TS4H's successor. Website row counts refer to editions, not unique series. |
| Topics | Eight unchanged families; 43 controlled leaves; one-to-three central identities per series. |
| Detailed scopes | 80 reviewed profiles; 50 series still lack a reviewed profile. |
| Evidence maps | 66 direct ICORE 2026 ranks, 55 direct CCF 2026 ranks, 34 historical rate/qualitative-band entries. |
| Public feeds | 375 ICS files: four aggregates (including submissions-only), 43 leaf-topic, 198 edition and 130 series feeds. |
| Review mirror | XLSX catalog/vocabulary/scope tables synchronized from YAML. |
| Licensing | MIT code, CC BY 4.0 original content/artwork, preserved third-party notices. |

Counts are a dated catalog snapshot. Recompute them from canonical files after
additions, not from an older session entry or a filtered website screenshot.

## Implemented Behavior

- Two views: Upcoming Deadlines and Conferences & Map, with future editions
  ordered by meeting date and ongoing/past editions separately accessible.
- Status, countdown and collapsed milestone identify the same next eligible
  contribution action, including mandatory abstract/registration gates.
  Open, scheduled and confirmed opening-unverified opportunities are green;
  estimated opportunities yellow, closed red, unannounced grey. Closed rows
  say Closed, not time until camera-ready. Expanded schedules retain other steps.
- Show submission options only defaults checked, is deadlines-only and includes
  the four eligible states. Clear filters removes all restrictions, even when
  the panel is collapsed. See [the status contract](data_schema.md#public-status-contract).
- Shared topics, search, sizes, independent ICORE/CCF and acceptance filters
  affect both views/map. Whole families use central identities; individual
  leaves use curated main/additional topics. Tables keep four main tags.
- Historical rates have source/year/track context and five bands. Missing
  evidence remains Unknown; ranks are independent, not predicted acceptance.
- Confirmed/announced future, non-online meetings in known cities appear on an
  offline Leaflet/Natural Earth map. Estimates remain in tables, not the map.
- Filters open by default above 760px and close initially on mobile. Compact
  mobile cards put the name and countdown on one row with status and next step
  below, and independently expand More info; desktop tables stay complete
  under a sticky header. Disclosure state survives filters/tabs/resizing; no-JS keeps
  full metadata accessible. Mobile visual refinement is covered by ADR-035.
- Venue Radar branding uses the selected Audiowide title, four-color calendar/
  radar PNG, radar-only favicon, restrained teal styling and semibold names.
  Source assets, notices and optical-alignment regressions are maintained.
- Header actions are Share on X, Star the repo and a Subscribe to calendar menu
  (Google/Apple/copy-link/download for submissions, all events, conference
  dates, any topic or series), with its caption below. Neither social action
  posts/stars automatically. Per-edition downloads and a Series feed link stay
  in Conferences & Map, not deadline rows.
- Confirmed exact cutoffs show their clock ("23:59 AoE") and the viewer's local
  time; mobile cards repeat the counted-down action under Time left. Closed or
  unannounced rows link to a tracked successor edition. Empty views explain
  hidden closed/unannounced matches; an active-filter badge shows on the panel.
- Day-only cutoffs count down to 23:59 in the host city (never later than AoE).
  When official sources disagree, the earliest cutoff is stored and shown with
  an asterisk and a note (12 deadlines on 2026-10-29). Rows have deep links
  (`#<edition-id>`, `#<series>`), filters live in the URL, series can be
  starred per browser, and expanded rows show an evidence line with Copy link
  and a prefilled correction form. A status guide explains the pills; link
  previews use a 1200x630 card (ADR-040).
- Search is accent-insensitive and matches every word. Re-renders keep keyboard
  focus. Tablet tables wrap between words; focus outlines, captions, a skip
  link and reduced motion are in place; no-JS shows every table and milestone.
- Giscus uses verified repository/category IDs and the stable discussion term;
  GitHub issue links work independently. Public README stays nontechnical,
  credits Gonzalo Uribarri and includes the personal-project clarification.
  It now presents the site with two generated screenshots (desktop/phone hero
  and host-city map, `assets/readme/`), the eight families, feed links, a trust
  section and help links (ADR-041). The README test checks local links/images
  and keeps "130+ conference series" within the catalog. Verified with
  GitHub's markdown renderer and github-markdown-css at desktop and 390px in
  light and dark themes; GitHub's dark themes show a transparent dark banner.
  The site subtitle (also README's) is now "Find where to submit next:
  conference deadlines for machine learning and AI, neuroscience, healthcare,
  complex systems, and control."

Exact selected wording is owned by [site copy](site_copy.md) and
[sharing](sharing.md); field semantics by [data schema](data_schema.md), not
historical prose in a design proposal.

## Maintenance Is Ready, Not Automatic

[Data maintenance](data_maintenance.md) explains the read-only monthly edition,
rate and scope queues, official-source review and confidence handling.
Cadence-aware rollover previews estimates for an explicit allowlist once a
series' submission routes close; `--write` (optionally `--series`) requires
review, keeps the prior review date and never overwrites existing editions. There is no unattended
source scraping, freshness enforcement or automatic data promotion. The report
tiers the queue by urgency and lists advisory checks; a weekly workflow rewrites
one "Review queue" issue; `scripts/source_check.py` checks cited links by hand.
CI fails on docs drift, inline-script syntax errors and removed published
identities, and runs Node unit tests for the client logic.

[Adding conferences](adding_conferences.md) covers identity/approval, all owning
files, taxonomy, dates, publication caveats and verification. [Development](development.md)
covers Python setup, standalone validation, tests, builds, XLSX synchronization,
browser checks and publication. Optional Node tools are not website/build dependencies.

The onboarding audit added a task index, field/addition guides and six automated
documentation checks; its 87-test baseline and rebuild changed no public
artifact or canonical/mirrored data. The public/private documentation split
adds ignore/tracking checks and keeps onboarding independent of private notes.

## Open Editorial Work

- Review future estimates and stale checks against current official CFPs about
  monthly. Validation confirms structure/provenance presence, not factual accuracy.
- Complete the 50 missing scope profiles gradually; curate characteristic
  categories, never exhaustive CFP inventories or guessed specialist coverage.
- Add rank/rate mappings only from direct supported evidence. Workshops, joint
  editions and similarly named conferences must not inherit a different venue's rank.
- Resolve ICCN's conflicting 2026 dates and the next NODYCON/Dynamics Days
  Asia-Pacific/Dynamics Days CAC announcements. Their gaps are deliberately
  retained in the review queue rather than converted into false future dates.
  On 2026-10-28 iccn2026.jp no longer resolved (registry status Suspended), so
  the estimated ICCN record now rests on unverifiable evidence. The owner
  decided on 2026-10-29 to keep it.
- Owner decisions of 2026-10-29: IAPR's first virtual ICPR (ICPRv, Oct 4-15,
  2027) is not tracked; Structured Data for Health (SD4H, ICML 2026, Seoul) is
  tracked as TS4H's successor under the TS4H series key. SIGIR 2027's draft
  Perspectives track still awaits a final call and a suitable archival type.
- ACPR 2027's acpr2027.com is still a draft site that IAPR does not list, so its
  Suzhou dates stay estimated and off the map until the organizer confirms them.
- Revisit unannounced ALIFE/BCI/SfN calls and BioCAS's exact paper route;
  preserve abstract-only versus full-paper publication notes without changing UI.
- Keep the original AI Deadlines backlog dated: 42 approved additions, 15 still
  deferred, and future-only ICWM separate. Candidates are not approved calendar data.
- Refresh ranking release schemas and evidence together if publishers issue a
  new list. Expand rate evidence only with defensible historical track statistics.

Detailed edition caveats are in [the evidence documents](README.md#evidence-and-design-records)
and [roadmap](roadmap.md). Further venue additions and UI/taxonomy changes still
follow the user's approved scope.

## Verification Baseline

Catalog release `8b351a3` passed 81 Python tests, the full browser suite at
1440/1051/1050/768/390/320px, workbook re-import/render checks, deterministic
builds and ICS CRLF/folding/UID checks. Every existing event in the prior 187
feeds and all 144 prior edition records stayed unchanged. Build `37794093622`
and Pages `37794090302` passed; live HTML and all 28 aggregate/new feeds matched
local output and live browser smoke passed. Documentation follow-up `63ccda5`
changed no data, assets, scripts, tests or generated outputs.

Documentation release `eddd814` passed all 87 Python tests, Build `37841704695`
and Pages `37841704129`; canonical data, workbook, assets and generated outputs
were unchanged. The documentation split likewise changes no conference or UI
behavior: all 89 Python tests pass, 166 records validate, local documentation
links resolve, private notes are ignored/untracked, and a full rebuild leaves
all data, workbook, assets, scripts, public README and HTML/212 feeds unchanged.
No new browser check, source refresh or publication is claimed for this local
documentation split. Record new material checks/limitations here and detailed
working logs locally; do not infer a fresh source review from these baselines.

The 2026-10-28 monthly refresh reviewed all 83 queued editions against official
organizer pages (aggregators used only for discovery), each change re-checked
independently. 76 records advanced `last_checked`; seven (BIOMAG, Dynamics
Days Europe, EUVIP, ICANN, ICCN, S+SSPR, UAI) had no readable official source
for the tracked edition, so they record that in notes and keep their old date. Material
corrections include BCI Winter 2027 (paper deadline Nov 15, not Dec 15), KR 2027
(Buenos Aires, Sep 21-24; April deadlines), NetSci 2027 (Dec 1 abstracts), IDA,
COLT, GECCO, CCN, AIS, OHBM, SIGGRAPH and ICPR 2028 official dates, ICASSP's Sep
23 extension and SSCI's moved site and extensions. ESANN's "before 18.11.2026"
is stored as Nov 17 (Bruges end of day), IEEE CDC 2027's day-only Jan 8 portal
opening moved from a fabricated midnight `opens_at` into notes, and a dead
EUVIP 2024 link was dropped. New supported routes (CHI
posters, WSDM short papers, ICASSP satellite workshops, ICONIP extended
abstracts, SSCI late-breaking abstracts, BHI late abstracts) raise the default
opportunity view from 81 to 87 rows on 2026-10-28. The edition queue fell from
83 to 50 items, all estimates awaiting official calls. A Gran Canaria
island-level city alias maps ITISE and CNS*. Catalog counts and all 212 feeds
are unchanged in number; no existing event UID changed and 49 milestone events
were added. Snapshot fixtures that pinned the earlier review state were updated
to the newly verified facts. Checks: standalone validation, 89 Python tests,
two byte-identical builds, the non-ICS whitespace check and the full browser
suite at 1440/1051/1050/768/390/320px (93 opportunities at its frozen date).
The 12 changed workbook catalog cells were patched in place without the
optional artifact tool. All other workbook parts are byte-identical, and a
re-import matches all 129 exported rows. No visual render of the workbook was
performed. Committed as 5e3b262 on branch `oct-2026-refresh-and-features`;
not published.

The 2026-10-29 feature release (ADR-039; committed as d5285e4 and 1bab28a on
the same branch, not published) adds
exact cutoff clocks with local time, the subscribe menu and submissions/series
feeds, earlier successor tracking with 30 officially reviewed estimated next
editions (ICDM 2027 Brisbane and ACC 2028 San Francisco have official dates),
normalized search, empty states and the focus, tablet and accessibility fixes.
An adversarial review then fixed 18 issues (menu focus/Escape and restored
picker state, successor month/hidden rows, tablet overlaps, no-JS columns) and
found IFAC SYSID 2027's Nov 15 extension and day-only June 1 opening; ACC
2028's conflicting notification/final dates are now estimated. Validation
now rejects deadline or opening times without an explicit UTC offset.
AIiH (International Conference on AI in Healthcare) was added on request:
AIiH 2027 in Oxford, Sep 1-3, with independent Apr 9 paper/abstract routes
and a Jul 2 late-breaking/STARS route (published as "11.59PM Pacific Time
(GMT-8)"; since ADR-040 stored at the earlier PDT instant with a cutoff note),
a healthcare identity, a sourced scope profile, an Oxford alias and annual
cadence. No ICORE/CCF rank is mapped (the ICORE portal refused automated
access; CCF predates the 2024 series). The workbook gained its catalog and
scope rows (tables extended in place; 130 catalog rows re-import exactly).
Checks: validation of 196 records, 99 Python tests, deterministic builds,
no removed UID versus HEAD, the non-ICS whitespace check, and the full browser
suite at 1440/1051/1050/768/390/320px including tests/venue_features.mjs (123
opportunities at its frozen date). The workbook's 21 changed Source cells
were patched in place and all 129 rows re-import. Calendar-app behavior of the
Google/Apple subscribe links is untested here (no signed-in client).

The 2026-10-29 ADR-040 round (committed on the same branch, not published)
records the owner decisions and implements the remaining proposals: earliest
cutoff plus `cutoff_note` on 12 deadlines, SD4H 2026 as TS4H's successor
(workbook TS4H row updated; 130 rows re-import exactly), ISBI 2027's Nov 2
extension, host-zone day-only countdowns, the client-code split, deep links
and URL state, starring, evidence lines with a correction form, compact cards,
link previews and the maintenance/CI tooling. An adversarial review confirmed
21 findings and a second agent pass verified their fixes and found 13 smaller
follow-ups, all fixed. Checks: validation of 198 records, 157 Python and 32
Node tests, deterministic builds, the identity check (658 -> 661 UIDs, 197 ->
198 edition IDs, none removed), the non-ICS whitespace check and the full
browser suite at 1440/1051/1050/768/390/320px (124 opportunities at its frozen
date). Not verified: the new GitHub workflows (they have not run on GitHub),
link previews on real platforms (the card is served from `main`), Giscus
sign-in with the new URL handling, and calendar-app behavior of subscriptions.

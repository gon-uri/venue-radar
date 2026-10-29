# Architecture Decision Records

Last synchronized: 2026-10-29

This is a dated decision history, not the current operating manual. Later
explicit refinements take precedence. Current rules live in
[architecture](architecture.md), [data schema](data_schema.md) and the
[task guides](README.md); older catalog counts remain historical snapshots.

## Current Decision Map

| Area | Active decisions and refinements |
| --- | --- |
| Static architecture, YAML ownership, committed outputs | ADR-001/002/003/005/007 |
| Stable identities, joint editions, renames | ADR-004/009/019/026 |
| Agent handbook and documentation ownership | ADR-038 refines ADR-006/008/037; private working logs are optional |
| Reviewed evidence, date-only precision, conservative recurrence | ADR-011/015/017/024/031/036 |
| Direct ranks and historical rates | ADR-012/014/018/025 |
| Eight central families and curated leaves/scopes | ADR-028/030/036; ADR-020's earlier seven-family matching is superseded |
| Submission action/status/countdown/ordering | ADR-032 refines ADR-013 and supersedes the relevant parts of ADR-016 |
| Offline confirmed-city map | ADR-021; tab naming refined by ADR-034 |
| Brand, licensing, copy and community | ADR-022/023/026/034; ADR-041 (README showcase, dark banner and the current subtitle; refines ADR-034) |
| Filters and default opportunities | ADR-025/033; responsive defaults refined by ADR-035 |
| Mobile cards and visual hierarchy | ADR-035 and its approved 36px refinement; ADR-039 adds the mobile next-step line |
| Cutoff clocks, subscriptions, successors, search and empty states | ADR-039 (refines ADR-017, ADR-024 display and ADR-034's header action) |
| Conflicting cutoffs, date-only countdowns, deep links, starring, compact cards, code layout | ADR-040 (refines ADR-024, ADR-027's MLSys choice, ADR-035 and ADR-039) |

## ADR-001: Keep the Project Static

- Date: 2026-07-08
- Context: The calendar needs to be public, cheap to host, easy to inspect, and maintainable without operational infrastructure.
- Decision: Use a static repository with YAML data, Python generation scripts, committed `docs/` outputs, and GitHub Pages hosting.
- Alternatives considered: Backend service with a database; scheduled hosted job; external calendar API integration.
- Consequences: Hosting and operations stay simple. Generated files must be rebuilt and committed when data changes.

## ADR-002: Use YAML as the Canonical Data Source

- Date: 2026-07-08
- Context: Conference metadata needs to be human-editable and reviewable in pull requests.
- Decision: Treat `data/conferences.yml` as the canonical source of truth, with `data/topics.yml` as the controlled topic vocabulary and `data/metadata.yml` for site-level metadata.
- Alternatives considered: CSV spreadsheet only; JSON; SQLite; remote database.
- Consequences: YAML supports nested deadline records and source URLs cleanly. Validation is required to prevent schema drift.

## ADR-003: Validate Before Generating Outputs

- Date: 2026-07-08
- Context: Published calendar feeds and the website should not be regenerated from malformed or misleading data.
- Decision: Run `scripts/validate.py` before `scripts/build_ics.py` and `scripts/build_site.py`; CI also validates before building.
- Alternatives considered: Let builders fail ad hoc; rely on manual review only.
- Consequences: Data errors fail early with specific messages. Builders can assume required fields and normalized topics exist.

## ADR-004: Use Deterministic Calendar UIDs

- Date: 2026-07-08
- Context: Calendar subscribers need stable events across rebuilds.
- Decision: Derive UIDs from conference `id` and event type using the `scientific-conference-calendar` UID domain.
- Alternatives considered: Random UUIDs; timestamp-based UIDs; generated hash values.
- Consequences: Rebuilds do not create duplicate calendar events. Conference IDs and deadline types must remain stable once published.

## ADR-005: Commit Generated Public Outputs

- Date: 2026-07-08
- Context: GitHub Pages can serve static files directly from the `docs/` folder.
- Decision: Write and commit generated `.html` and `.ics` files under `docs/`.
- Alternatives considered: Generate during deployment; serve from a separate build artifact branch.
- Consequences: The published site does not need a runtime build step. Maintainers must regenerate outputs after source data changes.

## ADR-006: Maintain Persistent Project-State Documentation

- Date: 2026-07-08
- Refinement: ADR-038 keeps public project state self-contained while moving
  detailed session diaries to optional ignored local notes.
- Context: Codex chat context may expire, but future sessions must be able to continue from repository state alone.
- Decision: Maintain `project_docs/implementation_status.md`, `project_docs/roadmap.md`, `project_docs/architecture.md`, `project_docs/decisions.md`, and `project_docs/session_log.md` as required project-state files.
- Alternatives considered: Rely on chat history; keep notes outside the repo; use only `README.md`.
- Consequences: Every coding session must read these docs first, update affected docs after changes, and append a session log entry before ending.

## ADR-007: Separate Project-State Docs from Public Generated Outputs

- Date: 2026-07-08
- Context: The `docs/` directory is both the GitHub Pages publishing root and the generated output target for HTML and ICS files. Keeping maintained project-state Markdown files there makes the directory harder to reason about.
- Decision: Move maintained project-state files to `project_docs/` and reserve `docs/` for generated public site and calendar artifacts.
- Alternatives considered: Keep the Markdown files in `docs/`; move generated site outputs to another folder; store project-state docs in hidden metadata directories.
- Consequences: `docs/` has one clear meaning as public generated output. `project_docs/` has one clear meaning as maintained project memory. Existing GitHub Pages publishing can remain configured to serve `/docs`.

## ADR-008: Keep AGENTS.md as a Lightweight Entrypoint

- Date: 2026-07-08
- Context: `AGENTS.md` is useful because coding agents discover it automatically, but the previous version duplicated details now maintained in `project_docs/`.
- Decision: Keep `AGENTS.md`, reduce it to concise onboarding instructions, and point agents to `project_docs/` for durable status, roadmap, architecture, decisions, and session history.
- Alternatives considered: Delete `AGENTS.md`; keep the full duplicated project specification in `AGENTS.md`.
- Consequences: Future agents still get immediate repository-specific guidance, while long-lived project knowledge has a single maintained home in `project_docs/`.

## ADR-009: Represent Joint Conference Editions Once

- Date: 2026-08-20
- Context: IJCAI and ECAI are holding a joint 2026 event. Separate records would create duplicate public site and calendar entries for the same dates and venue.
- Decision: Model the edition as one `ijcai-ecai-2026` conference record, retaining both organizations in its name, sources, topics, and search coverage.
- Alternatives considered: Duplicate the joint event as individual IJCAI and ECAI records; omit one conference from the catalog.
- Consequences: Subscribers receive one accurate event. Future editions can use individual records when the conferences resume separate schedules.

## ADR-010: Add a Dedicated NLP and LLM Topic

- Date: 2026-08-31
- Context: EACL is a core computational-linguistics venue. The controlled vocabulary had no topic that could accurately represent NLP and language-model research.
- Decision: Add `Natural Language Processing & LLMs` to `data/topics.yml` and the synchronized workbook vocabulary, then tag EACL with it alongside its relevant ML and responsible-AI topics.
- Alternatives considered: Tag EACL only as generic machine learning; add an EACL-specific tag; defer EACL until a later taxonomy revision.
- Consequences: The public site and generated ICS feeds gain a focused NLP/LLM subscription filter while retaining reusable, controlled taxonomy terms.

## ADR-011: Do Not Publish Unverified Workshop Editions as Current Events

- Date: 2026-10-05
- Context: The TS4H site still documents its 2025 workshop, and the official NeurIPS 2026 workshop list does not include TS4H. FMTS 2026 is on that list but its one-day slot is still either Dec 11 or Dec 12.
- Decision: Keep TS4H as a documented 2025 edition instead of a fabricated 2026 event. Track FMTS 2026 using Dec 11 as an explicitly estimated one-day calendar placeholder until NeurIPS assigns the exact day.
- Alternatives considered: Retain the unsupported TS4H 2026 dates; represent FMTS as a two-day event even though it lasts one day.
- Consequences: Calendar subscribers are not shown a false TS4H 2026 workshop. FMTS remains discoverable with visible date uncertainty and must be revisited when the day is announced.

## ADR-012: Source ICORE Ranks by Conference Series

- Date: 2026-10-06
- Context: The user selected ICORE for a webpage rank column. The official ICORE 2026 export provides ranks for selected computing venues but does not assign a rank to every tracked series or to satellite workshops.
- Decision: Keep a separate, validated series-level mapping of A*/A/B/C ranks and ICORE portal IDs in `data/icore_rankings.yml`. Show linked ranks in both website tables; use a dash when no direct rank is mapped. Do not transfer constituent ranks to the joint IJCAI-ECAI edition or a parent rank to a workshop.
- Alternatives considered: Duplicate ranks in every edition record; infer ranks from acronym similarities; treat unlisted venues as C or Unranked.
- Consequences: Rank provenance is auditable, edition data remains canonical for conference facts, and missing ranks do not imply low quality. The mapping and workbook require review when ICORE releases new rankings.

## ADR-013: Determine Open Submissions From Actionable Paper Routes

- Date: 2026-10-06
- Context: A future camera-ready, workshop-proposal, or commitment deadline can make a conference appear open even when a new paper can no longer be submitted. A past mandatory abstract or registration gate can also close a paper route ahead of its paper deadline.
- Decision: Keep one compact expandable deadline row per edition, but derive submission status from future paper/abstract/poster routes. Link mandatory earlier steps to their target with `gate_for`. Retain passed milestones in the expanded list with muted red-grey styling. The later opportunities filter includes confirmed and estimated future routes; a portal is Open now only with evidence of its opening.
- Visual refinement (2026-10-07): Open abstract/paper statuses use bold green text and a pale green background without a decorative leading dot. Status wording and eligibility logic are unchanged.
- Alternatives considered: Show every milestone as a separate top-level row; use the chronologically next milestone as the countdown; hide all passed milestones.
- Consequences: Users can quickly identify where a paper can still go. Maintainers must record mandatory gates accurately, and unknown/estimated routes never masquerade as confirmed openings.

## ADR-014: Keep Rankings And Historical Rates As Separate Evidence Maps

- Date: 2026-10-06
- Context: Subjective Difficulty labels were opaque, while ICORE does not cover every tracked computing venue. CCF provides complementary direct coverage, and acceptance rates must not be invented from a rank or a subjective label.
- Decision: Add an independently sourced CCF 2026 map beside ICORE 2026. Replace Difficulty with sourced historical acceptance rates and five fixed percentage-derived bands. Store year, track, URL, and approximation flag in `data/acceptance_rates.yml`; show Unknown when evidence is insufficient. The ICORE filter remains separate and simple.
- Alternatives considered: Blend ICORE and CCF into one score; inherit ranks from parent conferences; convert old Difficulty labels into unsourced percentages; show a numeric estimate for every venue.
- Consequences: The page gains useful coverage and clearer selectivity context without implying precision it does not have. Historical figures must be refreshed and read in their edition/track context.

## ADR-015: Use An Editorial Review Queue, Not Automatic Scraping

- Date: 2026-10-06
- Context: Organizer pages change format and publish provisional schedules, so unattended scraping could silently turn a placeholder into a misleading confirmed deadline.
- Decision: Add `scripts/maintenance_report.py` with distinct edition and acceptance-evidence queues, plus `project_docs/data_maintenance.md`. A maintainer checks official sources, edits YAML, validates, rebuilds, reviews, and commits.
- Alternatives considered: Live browser scraping on page load; a backend database; automatic scheduled mutations.
- Consequences: The static architecture and reviewable provenance remain intact. Regular manual review is still required.

## ADR-016: Order Milestones Chronologically And Separate Past Editions

- Date: 2026-10-06
- Status: Countdown, summary selection, opportunity labels and eligible-row
  ordering superseded by ADR-032. Past-edition separation and chronological
  schedule fallback for closed rows remain in effect.
- Context: A closed paper route may still have a future camera-ready date, while another conference has a later paper deadline. Submission status and time ordering need to answer different questions.
- Decision: Order deadline-table rows by the next future milestone, including the conference start. Show submission status independently as Open, Upcoming, Upcoming (estimated), Closed to new submissions, or Deadline unannounced. Remove the redundant Confidence column and label estimated dates in the milestone itself. Keep the expanded deadline list for details. Move ongoing and past meetings into a separate conferences table.
- Alternatives considered: Sort by only actionable paper deadlines; hide all rows with closed submissions; keep a Confidence column and a separate countdown.
- Consequences: A camera-ready milestone can place a closed edition among upcoming events without suggesting new submissions are possible. The submission-opportunities checkbox includes open, upcoming, and estimated paper routes and removes closed editions.

## ADR-017: Project Recurring Editions Conservatively

- Date: 2026-10-06
- Context: Once a conference passes, the calendar should surface its next annual or biennial opportunity even if the organizer has not published exact dates.
- Decision: Materialize a next edition only for explicitly supported recurring series, preserving the established cadence and prior lead times. Set projected meeting and deadline dates to estimated, leave unknown locations unannounced, and keep deadline-level confidence separate from meeting confidence when only one has been confirmed. The projection tool is idempotent and does not overwrite reviewed editions.
- Alternatives considered: Add one year to every record; leave all unannounced future editions absent; present inferred dates as confirmed.
- Consequences: The static site remains useful between organizer announcements. Monthly source reviews must compare every estimate with official CFPs and revise dates without changing stable event identifiers.

## ADR-018: Allow Sourced Qualitative Acceptance Estimates

- Date: 2026-10-06
- Context: Many smaller conferences and workshops lack a recent published acceptance percentage, but some have reliable historical evidence supporting a selectivity band.
- Decision: Keep sourced numeric historical rates when available. Permit a qualitative-only band marked `(estimated)` when direct organizer or proceedings evidence supports it; otherwise show Unknown. Never infer a band from ICORE, CCF, or the retired Difficulty field.
- Alternatives considered: Fill every missing rate from rank or reputation; leave all qualitative gaps blank.
- Consequences: Coverage improves without fabricating numerical precision, and each estimated band remains auditable from its source.

## ADR-019: Preserve Series Identity Across A Rename And A Joint Edition

- Date: 2026-10-06
- Context: The LOD organizer renamed its annual conference AIS in 2026, while IJCAI-ECAI 2026 was a joint edition followed by separate IJCAI and ECAI events in 2027.
- Decision: Keep the existing `lod-2026` ID and `LOD` series key for stable calendar subscriptions and workbook continuity, but display the official AIS name and use organizer-confirmed 2026 facts. Add a distinct estimated AIS 2027 edition under that series. Add IJCAI and ECAI 2027 under their own series, with directly sourced ranks; do not transfer those ranks to the joint 2026 event.
- Alternatives considered: Silently keep the outdated LOD title and dates; rename the existing edition ID; treat the joint and standalone IJCAI editions as one series with inherited ranks.
- Consequences: Search for LOD still finds the successor, existing subscriptions keep their UIDs, and ranking provenance stays accurate.

## ADR-020: Derive Seven Topic Families From Central Subtopics

- Date: 2026-10-06
- Status: Family count and parent matching superseded by ADR-030; stable leaves
  and curated display-topic limits remain. Do not implement the old model.
- Context: Added dynamics/control venues and responsible-AI coverage made a flat
  topic list harder to scan, while overly broad tags obscured conference scope.
- Decision: Store up to four central leaves per edition. A validated registry
  assigns each leaf exactly one family and a compact display label. Family
  checkboxes select their children; use OR within a family and selectable
  ANY/ALL across families. Keep stable topic/feed keys. Federated learning is
  an ML leaf, not automatically an ethics/privacy classification.
- Consequences: No redundant per-edition parent metadata; partial family
  selections are indeterminate. Taxonomy edits require source review and rebuild.

## ADR-021: Add An Offline Confirmed-City Map To Conferences

- Date: 2026-10-06
- Context: The second table's main extra value is dates/location, not submission
  status. A geographic overview helps planning without crowding deadlines.
- Decision: Rename the tab Conferences, remove submission status there, and add
  a Leaflet/Natural Earth map with one marker per explicitly mapped city. Only
  officially announced future meeting dates appear; estimates remain in tables.
  Shared filters apply to map/table; submission opportunities applies only to
  deadlines. Provide hover, click, keyboard popups and city-link alternatives.
- Consequences: No external tile/geocoder dependency or new backend; coordinates
  represent approximate city centers, not exact venues. Past editions stay separate.

## ADR-022: Use Venue Radar And Split Code/Content Licenses

- Date: 2026-10-06
- Context: The user selected Venue Radar, a calendar/radar symbol, a sober visual
  refinement, and permissive code/content licensing after discussing restrictions.
- Decision: Initially keep repository/Pages URLs and UID domain unchanged (the
  later user-requested repository migration is recorded in ADR-026). Use a refined
  transparent PNG mark, neutral surfaces, teal accents, and semantic status colors.
  MIT licenses code; CC BY 4.0 licenses original editorial content/artwork. Preserve
  third-party notices and do not claim ownership of conference facts/rankings.
- Consequences: Both selected licenses allow commercial reuse with required
  attribution/notices; neither imposes a noncommercial restriction. README stays
  simple, with development/maintenance details in project_docs.
- 2026-10-07 typography refinement: enlarge the title proportionally more than
  the mark, but keep its font family unchanged pending approval. Compare five
  actual font files at equal size/color/mark dimensions; preview fonts must not
  become public runtime dependencies. Preserve native filter disclosure
  semantics while explicitly controlling its indicator size and text spacing.
- 2026-10-07 selection: the user chose Audiowide. Embed its Latin WOFF2 only
  for the title, using native weight 400 without synthetic bold and preserving
  the original OFL notice. Keep body/table fonts and existing brand colors.
  Apply small optical vertical offsets and allow word wrapping on narrow
  mobile screens. No external font service becomes a runtime dependency.
- 2026-10-07 palette refinement: the user approved direct pixel recoloring
  after generated edits introduced subtle shape/color drift. Preserve every
  original foreground pixel's alpha; map both blues to #38A6B0, the location
  dot to #C85C62, and the border to #263238. Fill only the calendar interior
  white and retain exterior transparency. A browser-rendered white README
  banner uses the real Audiowide font, avoiding generated lettering. Keep the
  pre-recolor source and original generation unchanged for provenance.
- 2026-10-07 table hierarchy refinement: make conference-name links semibold
  at weight 600 in both tables and archived editions. Scope the rule to their
  existing Conference cells, keeping inherited size/color and other link
  weights unchanged. Check wrapping and cell bounds on desktop and mobile.

## ADR-023: Use Optional Giscus For Community Requests

- Date: 2026-10-06
- Context: Users need to request conferences and corrections on a static site.
- Decision: Lazily load Giscus backed by public GitHub Discussions with a stable
  specific discussion term. Also provide a structured issue form and direct
  Discussions link independent of the widget. Enable Discussions; owner installs
  the Giscus app for this repository only.
- Consequences: No project backend, but comments require GitHub sign-in and an
  optional external service. Do not claim activation until live widget verification.

## ADR-024: Keep Published Deadline Days Separate From Unknown Hours

- Date: 2026-10-06
- Context: Several new official CFPs announce a day without a cutoff hour. A
  synthetic exact AoE timestamp would overstate evidence; date-level uncertainty
  would also misrepresent the published day.
- Decision: Use time_precision: date, note provisional ordering assumptions,
  label the site cutoff as time-estimated, and emit all-day ICS deadlines. Keep
  UID keys stable when an exact hour is later confirmed. Extend rollover with
  explicitly sourced triennial SYSID cadence, not a blanket annual assumption.
- Consequences: Calendar clients do not receive a fabricated hour. Editorial
  reviews still must check organizer portals for precise timezone/cutoff updates.
- Same-day display refinement: put `(time est.)` under the next-milestone
  countdown in Time left, and preserve explanatory tooltips on date-only dates
  in Next milestone. Do not change estimated-date labels, cutoff assumptions,
  calendar exports, or submission-opportunity semantics.

## ADR-025: Separate Rank Navigation From Evidence And Group Filters

- Date: 2026-10-06
- Context: Users requested compact expandable filtering, complementary CCF
  selection, and ranking webpages instead of direct PDF downloads.
- Decision: Keep all controls in one initially collapsed native disclosure.
  Add independent CCF A/B/C/Unranked matching alongside ICORE, using OR within
  a group and AND across groups. Preserve CCF PDF/page provenance and validate
  a separate official `page_url` for filter headings and table-score links.
- Consequences: Both tables and the confirmed-city map share the added filter;
  the opportunities checkbox remains deadlines-only. Rank scores and calendar
  data do not change, and workshops remain unranked. Disclosure state survives
  viewport changes without an extra UI dependency.
- Same-day placement refinement: keep shared metadata controls and Clear
  filters in Filters & search, but move the deadline-only opportunities
  checkbox outside beside the tabs. Align Search after Acceptance rate and
  expose native topic-family disclosure markers alongside plus/minus signs.
  This supersedes only the original all-controls-inside placement, not any
  ranking or submission-matching semantics.
- 2026-10-07 default refinement: Filters & search starts expanded at all
  viewport widths using the native open attribute. Users can collapse it;
  resizing preserves their selection, and Clear filters does not change it.
  This supersedes only the original initially collapsed default.
- Later responsive refinement: ADR-035 keeps that expanded default only above
  760px; mobile starts collapsed. State preservation and clearing are unchanged.

## ADR-026: Migrate Repository URLs Without Changing Stable Identities

- Date: 2026-10-07
- Context: The user renamed the repository to gon-uri/venue-radar. Repository
  redirects do not cover the old GitHub Pages site or calendar-feed URLs.
- Decision: Use https://github.com/gon-uri/venue-radar and
  https://gon-uri.github.io/venue-radar/ for maintained public references and
  local Git origin. Keep relative calendar download paths, the published
  scientific-conference-calendar UID namespace, existing Giscus repository
  and category IDs, and its specific discussion term unchanged.
- Consequences: The new site, request links, attribution, and comments follow
  the rename without creating new event identities. Existing calendar
  subscribers must update their feed address. The old Pages address is not
  retained; no second repository or custom-domain infrastructure is introduced.

## ADR-027: Preserve A Dated Candidate Backlog And Track Independent Routes

- Date: 2026-10-07
- Context: AI Deadlines retained 2025-2026 entries identify 57 untracked series;
  the user approved 11 additions and asked to retain the other candidates.
- Decision: Keep 11 sourced additions in canonical YAML and preserve the 46
  remaining candidates, all original names/links, and retrospective scope
  limitations in project_docs/conference_candidates.md, linked from AGENTS.
  ICWM's future-only listing is separate. Add three focused leaves within
  existing families for evolutionary computation, cognition, and ML systems.
  Use independent gated routes for AAMAS main and Blue Sky papers; revisions,
  paper updates, and camera-ready events never become new-paper opportunities.
- Evidence: Unannounced AutoML/ProbML 2027 schedules and GECCO/CogSci submission
  dates remain estimates. Official date-only ICIP/Interspeech cutoffs remain
  all-day ICS events. Prefer explicit MLSys CFP UTC times over its conflicting
  homepage conversion and flag the discrepancy for review. Do not infer ranks
  for unmatched series or rates from accepted-only paper lists.
- Consequences: The catalog expands without silently broadening its approved
  scope or overstating date/rank/rate confidence; monthly reviews include the
  additions and explicitly configured annual recurrence.

## ADR-028: Curate Series Scope Separately From Four Display Topics

- Date: 2026-10-07
- Context: Four visible tags are useful for scanning, but insufficient for
  detailed venue discovery. Organizer CFPs can list many incidental areas;
  blindly copying them would make filters less useful.
- Decision: Store optional profiles by exact series in conference_scopes.yml,
  with zero to six characteristic additional controlled leaves, concise prose,
  official evidence URLs/year, and an independent review date. The cap is a
  guardrail, not a target. Prioritize defining research categories; do not infer
  specialist coverage from incidental applications or individual workshops.
- Matching: join profiles at build time. Keep four primary display topics;
  search, filters, map matching, and topic feeds use the deduplicated union.
  Search also uses detailed prose. ICS descriptions retain the evidence year
  and review date, without changing dates, UIDs, or submission semantics.
- Maintenance: add a third missing/stale/prior-edition review queue and a
  separate workbook mirror sheet. The canonical edition data remains unchanged.
  Missing profiles fall back to primary topics, rather than guessed detail.
- Coverage: initially 30 of 82 series, including all 11 approved additions;
  the 52 missing profiles remain explicit editorial work. Do not report this
  initial pass as a complete scope review of all tracked conferences.
- Consequences: richer discovery without a wider table or a backend. Profiles
  describe series using dated sources, not exact historical-edition CFPs.
  Monthly source checks remain necessary, particularly when a new CFP appears.

## ADR-029: Distinguish AI, Multimedia And Biometrics Communities

- Date: 2026-10-07
- Context: The user approved EuroGP/KR/ICAPS, broadened vision additions to all
  vision/imaging/multimedia candidates, and requested all dedicated biometrics
  candidates from the original remaining 46.
- Decision: Add 15 series and 18 editions with independently curated profiles.
  FG and IJCB already cover the two dedicated biometrics candidates; do not
  count them twice or split IJCB into incorporated BTAS/ICB predecessor rows.
  Extend the existing seven families with five focused leaves for reasoning,
  planning, graphics, multimedia retrieval, and biometric/human sensing. Tables
  still display at most four primary leaves; curated detail drives discovery.
- Evidence: Keep direct ICORE/CCF matches independent; 3DV has CCF-only coverage.
  Preserve Unknown for ten unsourced acceptance rates. ECCV/ICCV are biennial;
  other additions follow documented recent annual recurrence. Store estimates
  independently from confirmed hosts/meetings and keep date-only cutoffs honest.
  The named-venue ICCV homepage takes precedence over conflicting generic
  Dates text, with an explicit reconciliation task. WACV's two new-paper rounds
  have separate enrollment gates; camera-ready/checksum/presentation uploads
  cannot open a new submission route.
- Consequences: The catalog is 97 series / 122 editions, detailed profiles
  45 / 97, and the original backlog 31 untracked candidates. Evidence and monthly
  follow-ups are maintained in vision_ai_expansion.md. This is targeted expansion,
  not a claim of a complete refresh of every previously tracked edition.

## ADR-030: Separate Eight Central Families From Specific Scope Matching

- Date: 2026-10-07
- Refinement: ADR-033 removes the duplicate Time series shortcut. The normal
  leaf, curated union matching and all eight families remain unchanged.
- Context: The user wants eight intuitive topics, preserving healthcare,
  neuroscience, complex systems/time series and responsible AI while adding
  established language, agents, retrieval and robotics communities. Generic
  ML tags should not flood broad-family searches with every specialist venue.
- Decision: Keep 40 stable leaves in eight families. Store one to three central
  identities for every series in conference_families.yml, validated for complete
  coverage. Whole-family selection matches those identities. Partial child
  selections match the curated primary/additional union, OR within a family
  and ANY/ALL across selected groups. Selecting all children is equivalent to
  selecting the parent. The Time series shortcut contributes that leaf as
  another selected group; Clear filters resets it too.
- Editorial structure: NLP/agents/retrieval and RL/robotics/control are separate;
  biometrics belongs with healthcare. Graphs, nonlinear dynamics, complex
  systems, time series and signals share the complex-systems family. Human-AI
  interaction sits with responsible AI. Keep four visible main tags and up to
  six genuinely characteristic extra tags, not blanket CFP inventories.
- Consequences: Specific deep-learning searches can find MICCAI without
  labeling it a general ML venue. LoG is centrally ML and graph/complex systems;
  L4DC is centrally control/dynamics. Existing leaf feeds remain union-based;
  family filters intentionally need not equal the union of all leaf feeds.
  Preserve full one-line family labels via layout and narrow-screen spacing.

## ADR-031: Preserve Eligibility, Provisional Dates And Irregular Recurrence

- Date: 2026-10-07
- Decision: Add the approved 13 language/retrieval/web series plus ICRA, RSS
  and SMC. Keep stable WWW and IJCNLP aliases; ISWC is Semantic Web, never
  Wearable Computers. ARR commitment deadlines are non-submission milestones.
  RSS's six-page stage 1 gates invited stage 2. ECIR resource papers get their
  own archival submission type, independent of the other abstract gates.
- Evidence: SIGIR explicitly labels its future deadlines PROPOSED, so confirmed
  meeting dates do not promote those deadlines to confirmed. SMC's proposal-
  only dates stay estimated; conflicting 2026 camera-ready blocks are omitted.
  Preserve literal ICRA PST and flag the civil-time discrepancy for review.
  LREC is biennial; NAACL/COLING/IJCNLP remain outside automatic annual rollover.
- Consequences: 113 series / 144 editions; 63 reviewed profiles; 66 ICORE,
  55 CCF and 34 acceptance mappings. Twelve new rates remain Unknown. The original
  57-candidate gap is now 42 added / 15 deferred, with ICWM separate. Deferred
  does not mean all venues are minor. Sources, workbook, tests and publication
  documentation remain synchronized; event UIDs and old date fields are stable.

## ADR-032: Align Submission Status, Countdown And Required Author Action

- Date: 2026-10-07
- Context: AAMAS 2027's closed main-track paper cutoff was counting down while
  status referred to its independent Blue Sky track; MLSys 2027 counted down to
  its portal opening rather than paper submission. Missing opening evidence
  also incorrectly suggested a known future opening.
- Decision: Define eligibility by enabling a new research contribution. Select
  the earliest required action of the next eligible route, including mandatory
  abstract/registration gates, and use that same track/action for countdown,
  collapsed milestone and eligible-row ordering. An expired mandatory gate
  closes the route to fresh submissions. Keep all other schedule milestones
  expanded, including organizer proposals, openings and camera-ready dates.
- Evidence and colors: confirmed routes are Open with recorded opening evidence,
  Scheduled submission with an explicit future opening, or Submission opportunity
  when opening is unverified. All three are green. Submission opportunity
  (estimated) is yellow, Closed to new submissions red, Deadline unannounced
  grey. Estimated prerequisites or terminal deadlines make the route estimated;
  no inferred opening becomes Open. Status explains the evidence in a tooltip.
- Closed rows: Time left says Closed, not time until a production deadline.
  Retain the next future schedule milestone as their summary and sorting key
  when showing all conferences; do not force closed rows to the bottom.
  Unannounced rows use a dash instead of a non-submission countdown.
- Consequences: AAMAS on Oct 7 targets Nov 5's mandatory Blue Sky abstract
  deadline, with opening-unverified status. MLSys targets Oct 30 and switches
  from Scheduled to Open at its published Oct 10 20:00 UTC opening. Existing
  dates, expanded schedules, YAML schema and all calendar feeds remain unchanged.

## ADR-033: Keep Clearing Accessible And Default To Submission Options

- Date: 2026-10-07
- Decision: Remove the duplicate Time series shortcut, keeping the subtopic
  inside its existing family. Give the topic tree a 20rem maximum height so
  eight collapsed families fit; expanded children scroll internally. Move
  Clear filters outside native details into the heading row so it is visible
  when collapsed, without nesting an interactive button inside summary.
- Default: Show submission options only starts checked, retaining ADR-032's
  four eligible states. Unchecking reveals closed/unannounced rows. Clear
  filters still means remove every restriction, including this checkbox,
  rather than silently restoring it to checked. It never opens the panel;
  focus stays on Clear filters when Search is hidden.
- Sharing: Group calendar download, Share on X and Star the repo in the header.
  Use a prefilled X draft with approved text and the canonical site URL, and
  a repository link for starring. Neither publishes or mutates an account
  automatically; no third-party widget script is required. Preserve Lucide
  release/license provenance and use safe new-tab relationships.
- Branding: A simple radar-only SVG with opaque white background is the favicon.
  The selected PNG logo, README banner and font remain unchanged. Copy choices
  are recorded in sharing.md. No conference data, calendar feeds or UIDs change.

## ADR-034: Keep Header Actions And Public Attribution Compact

- Date: 2026-10-07
- Decision: Order header actions Share on X, Star the repo, All events (.ics),
  with Download calendar below the last button. Align buttons at the top on
  desktop and preserve last/rightmost download placement while wrapping mobile.
  Remove the redundant On the map heading but keep the count and accessible
  map-section label. Shorten website attribution to the author's name and
  preserve all profile/license links; README affiliation remains plain text
  without the redundant department hyperlink.
- Copy: Three introduction alternatives, Conferences & Map as the recommended
  tab label, and a README-only personal-project clarification are proposals
  awaiting user selection. Current introduction/tab text stay unchanged until
  approved; site_copy.md preserves the exact choices.
- Approved follow-up: the user selected Conferences & Map and the disclaimer,
  placed at the end of README's final licensing paragraph. Only the introduction
  is pending; five new ML/AI-first alternatives highlight neuroscience,
  healthcare, complex systems and control as fields or applications.
- Final copy selection: use Find your next conference in machine learning and
  AI, or explore related opportunities in neuroscience, healthcare, complex
  systems, and control. This replaces only the website subtitle; README and
  X sharing descriptions remain independent. No copy choice remains pending.
  The user also requested ML, AI, neuroscience, and related fields in the X
  draft's opening; retain all other wording and the canonical website URL.
- Consequences: No changes to conference facts, filters, submission routes,
  map eligibility, artwork, fonts, calendar downloads or event UIDs.

## ADR-035: Compact Mobile Cards With Independent Details

- Date: 2026-10-07
- Context: Eight stacked fields make every mobile conference card too tall
  for scanning, while desktop tables still benefit from all columns.
- Decision: At widths up to 760px, initially show Conference, Submission status
  and Time left for deadlines; show Conference, Dates and Location for the map
  tab. Keep the five other cells in the same row and reveal them with an
  independent More info / Less info button. Include archived conference cards.
  Preserve the existing nested milestone arrow and all submission semantics.
- Accessibility: Native buttons have 44px minimum tap targets, aria-expanded,
  per-row aria-controls IDs, conference-specific labels and a pinned Lucide
  chevron. Only enable hiding after handlers initialize; without JavaScript
  full metadata stays visible and inert controls stay hidden.
- State: Card expansion survives sorting, filtering, tab changes, minute
  refreshes and resizing. Desktop ignores the collapsed presentation and always
  shows all original columns. Filters & search initially closes on mobile and
  opens above 760px; later resizing preserves the user's current state. Clear
  filters does not change filter or card disclosure states.
- Consequences: No data, metadata matching, calendar feeds, event UIDs, desktop
  column order, brand assets or map eligibility changes. Browser regressions
  cover both tabs, the breakpoint, keyboard, persistence and no-JS behavior.
- Approved visual refinement: reduce the full-width disclosure from 44px to
  36px with 4px vertical padding and a white resting background. Increase all
  mobile field labels to .8125rem (13px at the default root size), retaining
  bold weight and using darker grey #526267. Give the Conference row a pale
  teal #edf5f5 background, strengthen the existing 1px outline to #bdc9cc and
  increase card gaps from 10px to 14px. Avoid thick borders and shadows.
  The smaller target is an explicit compactness tradeoff from the original
  44px control, still above WCAG 2.2 AA's 24px target-size minimum:
  https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html.
  Apply the same refinement to both tabs and archived cards, never desktop.

## ADR-036: Respect Abstract-Based Venues Without Changing The Interface

- Date: 2026-10-08
- Context: Add 16 respected complex-systems/neuroscience series, including all
  five regional Dynamics Days branches, AREADNE and SfN. Some publish papers,
  some accept only abstracts, and historical proceedings are not promises for
  the current edition. The user explicitly wants the existing website intact.
- Decision: Record publication formats and caveats in edition metadata and
  dynamics_neuroscience_expansion.md. Reuse existing abstract contribution
  types, milestone labels and submission statuses. Add no publication UI,
  status type, CSS or behavior change. Preserve all eight family IDs/names/order;
  add only three characteristic leaves for artificial life, neuromorphic
  computing and systems/experimental neuroscience.
- Evidence: Meeting and deadline confidence stay independent. Confirmed host
  dates do not confirm a proxy CFP. Date-only cutoffs remain all-day events.
  Independent abstract tracks do not gate full papers. NODYCON's presented-work
  journal manuscript step is not a fresh conference submission. A preliminary
  IEEE BioCAS abstract date is not renamed as a paper deadline or a gate.
- Recurrence: SAB/AREADNE/LAC use verified biennial cadence; Europe/US and other
  verified annual series use annual cadence. No automatic projection for
  NODYCON's changed cadence, irregular CAC, missing-next-edition DDAP or ICCN's
  unresolved date conflict. The maintenance queue preserves these gaps.
- Consequences: Sixteen series/22 editions and profiles are added; old records,
  UIDs and public semantics remain stable. The workbook and generated feeds
  mirror canonical YAML. Missing ranks/rates stay unknown, not inferred from
  loosely matching acronyms or abstract acceptance.

## ADR-037: Separate Current Guides From Historical Project Memory

- Date: 2026-10-08
- Refinement: ADR-038 replaces tracked session/design diaries with local private
  notes; source evidence, current guides and technical rationale stay public.
- Context: A new agent had to reconstruct a conference update from lengthy
  status, architecture, maintenance and history files. No complete addition
  checklist or field guide explained the cross-file requirements and traps.
- Decision: Keep AGENTS.md lightweight and add a documentation index, an
  edition/deadline schema reference and a conference-addition checklist.
  Shorten status to the current snapshot and architecture to file/code ownership
  and stable contracts. Data maintenance owns refresh procedure; development
  owns executable verification/workbook/publication commands. Link to detail.
- History: Preserve dated ADRs, source audits, proposals and session entries;
  clearly distinguish them from current requirements. New session entries go
  at the top in reverse chronological order. Label superseded decisions.
- Authoring corrections: Do not fabricate a midnight opens_at from a day-only
  opening announcement. Run standalone registry validation as well as the
  build. Update dataset review metadata before generation, not after it.
  Rollover writes estimates only after review and can shift old opening metadata;
  its output is not fresh evidence. Arbitrary custom milestone types are
  schedule-only, even if validation accepts them.
- Consequences: Documentation-only work must preserve conference YAML, XLSX,
  website sources, artwork, public copy and generated output. Documentation
  tests check local links, guide coverage and executable schema examples.

## ADR-038: Keep Working Notes Local And Public Guides Self-Contained

- Date: 2026-10-08
- Decision: Ignore the root `private_notes/` directory. Put detailed session
  diaries, brainstorming, unfinished plans, personal preferences and rejected
  design/copy options there. Keep AGENTS, the handbook, evidence, current
  requirements, material release verification and technical decisions public.
- Maintenance: Private notes are optional, never an onboarding/build/CI
  dependency. Update current public guides before relying on a new local note;
  never force-add the private directory. The public documentation policy owns
  this boundary; concise branding/copy guides retain implemented choices.
- Consequences: A fresh clone remains maintainable. Private notes need separate
  backup and are not secured by Gitignore. The move removes current tracked
  diaries/proposals, not previously published Git history; no history rewrite
  is performed. ADR-006/008/037's public session-log requirements are superseded.

## ADR-039: Show Exact Cutoffs, Subscribe To Feeds, Track Successors Early

- Date: 2026-10-29
- Context: The owner approved the top five improvement proposals plus bug
  fixes after a review. Researchers could not see cutoff hours (274 of 396
  deadlines are exact), downloaded calendars never received corrections, 29 of
  129 series had no future deadline (searching "neurips" showed nothing by
  default), filtered views went blank without explanation, and re-rendering
  dropped keyboard focus every minute.
- Display: a milestone shows its clock only when it is confirmed and has an
  exact hour (`time_precision` not `date`): "20:00 UTC", "23:59 AoE" or
  "UTC-5" style offsets taken from the stored datetime, never guessed zone
  abbreviations. Estimated and date-only cutoffs keep the date with "(est.)" or
  "(time est.)" (ADR-024 unchanged). The browser adds "Your time: ..." when the
  viewer's offset differs. Recorded openings are exact and no longer inherit a
  cutoff's date-only precision. Milestone rows show date and clock above the
  label. Up to 760px the Time left cell also shows the counted-down action's
  date and label, refining ADR-035; desktop keeps the Next milestone column.
- Subscriptions: the header's rightmost action is a native "Subscribe to
  calendar" disclosure (refines ADR-034) with Google (render?cid=webcal),
  Apple (webcal), Copy link and Download for submissions.ics, calendar-all.ics
  and conferences.ics, plus topic and series pickers. Outlook has no documented
  deep link, so the menu explains Subscribe from web with a copied link. New
  permanent paths: docs/submissions.ics (supported submission types and their
  gates) and docs/series/<series-key-slug>.ics (every edition of one series,
  keyed by the exact series key so renamed editions such as LOD/AIS stay in one
  feed). Both reuse the existing VEVENT code, so UIDs are identical to the other
  feeds. Every feed carries X-WR-CALDESC, REFRESH-INTERVAL and X-PUBLISHED-TTL
  (P1D). Download links stay relative (ADR-026); subscribe links and feed
  descriptions use SITE_URL, now defined once in scripts/build_ics.py and passed
  to the client as data-site-url on the calendar menu.
- Successors (refines ADR-017): rollover may propose the next edition once all
  fresh-submission routes of the latest edition have closed, not only after the
  meeting. CADENCE_YEARS gains 32 annual and 4 biennial established series;
  irregular, joint, one-off workshop and renamed-ID series stay out. AALTD is a
  reviewed exception: an annual ECML PKDD workshop since 2015. Drafts keep the
  prior edition's last_checked (never stamped as reviewed), drop shifted
  opens_at, and --series limits --write. Thirty successors were then reviewed
  against official future-meeting pages and fact-checked: they stay estimated
  unless an official next-edition source supports a field. Closed or
  unannounced rows link to the successor ("Next: NeurIPS 2027 · ~May 2027 (est.)").
- Search and empty states: search folds accents and punctuation, requires every
  word, matches one- and two-letter words at word starts, and no longer indexes
  source URLs. Filter selections are computed once per pass. When a view is
  empty the page explains how many matching rows are closed or unannounced and
  offers Show them, Clear filters and Request a conference; a "Show N closed or
  unannounced" link and an "N active" badge on the filter summary keep hidden
  restrictions visible. Clear filters keeps ADR-033 semantics.
- Fixes: rows are moved only when out of order and focus is restored, so
  toggles and the minute refresh keep keyboard focus. Tablet tables (761-1099px)
  wrap between words with rebalanced columns. Accessibility: visible
  focus-visible outlines, 3.4:1 control borders, table captions and column
  scopes, a skip link, Home/End on the tablist, aria-controls on milestone
  toggles, reduced motion for CSS and Leaflet. Without JavaScript the conference
  table, every milestone and a short note are visible instead of "Checking...".
  The filter panel's responsive default runs inline before first paint; map and
  Giscus failures show fallbacks.
- Consequences: catalog 196 editions across 129 series; feeds grow to four
  aggregates, 43 topic, 196 edition and 129 series files. No existing UID,
  edition ID, deadline type, topic slug or status semantics changed. Browser
  regressions live in tests/venue_features.mjs.

## ADR-040: Owner Decisions And The Remaining Improvement Proposals

- Date: 2026-10-29
- Owner decisions: (1) IAPR's virtual ICPRv 2027 is not tracked. (2) The
  ICCN 2026 record is kept although its domain is suspended. (3) Structured
  Data for Health (SD4H, ICML 2026) is tracked as TS4H's successor under the
  stable TS4H series key (as LOD/AIS in ADR-019). (4) When official sources
  state conflicting cutoffs for one deadline, store the earliest stated
  instant and record an optional `cutoff_note`; the page shows an asterisk
  after the time plus the note, and calendars add it to the description. This
  supersedes "conflicts stay provisional" for cutoffs and ADR-027's preference
  for MLSys's CFP time. (5) The remaining ranked proposals were approved.
- Date-only cutoffs (refines ADR-024): a published day without an hour is still
  stored as 23:59 AoE, which drives ICS and the maintenance report. When the
  host city (cities.yml `tz`) or a real edition time zone is known, the page's
  countdown, closing and row order use 23:59 in that zone on the same day,
  which is never later than AoE; an unannounced host ("To be announced") has
  no zone. The tooltip names the zone; ICS stays all-day; explicit organizer
  offsets are kept.
- Interface: compact mobile cards put name and countdown (or dates) on the
  first row with status, next step and successor below (refines ADR-035).
  Desktop tables keep a sticky header and show topics as one wrapped line. An
  evidence line (call, dates source, review date, mode, estimate, Copy link,
  Report outdated info -> correction issue form) appears with the expanded
  schedule and in mobile More info; prior-edition links say "Previous call".
  Rows have stable anchors: #<edition-id> opens that edition and #<series-slug>
  its next edition, revealing it (clearing filters, Starred only and, for a
  past edition, opening the archive) if filters hide it. Filters, search, match
  mode, tab and toggles are kept in the query string (q, topics, families,
  size, icore, ccf, acc, match, all, starred, tab); other parameters (such as
  Giscus's sign-in return) are left alone, and starred=1 applies only where
  this browser has stars. A followed hash stays in the address bar until the
  visitor changes the view, so a reload keeps their newer filters; Back and
  Forward restore the controls from the URL; #deadline-<id> and
  #conference-<id> links are rewritten to #<id>. Clear filters resets search, filters, match mode and toggles
  (the URL then keeps all=1, because every row is shown) and removes the hash;
  the active tab is kept. Series can be starred per browser (localStorage, series key),
  with a Starred only filter and feed shortcuts. A status guide explains pills
  and markers; countdowns have screen-reader text.
- Discoverability: search-intent title/description, canonical, Open Graph and
  X card tags with a 1200x630 card (assets/branding/social-card.png, generated
  by scripts/build_social_card.mjs) served from the repository because docs/
  holds only generated output; README mentions subscriptions.
- Performance and code layout: icons come from one inline sprite, conference
  rows omit deadline JSON, land geometry is rounded to 3 decimals and Leaflet
  loads after the page logic, saving roughly 270 KB that the evidence lines,
  star buttons and status guide largely spend again (net 2.62 -> 2.61 MB,
  339 -> 336 KB gzipped, against the ADR-039 page). Client logic moved out of the Python template into
  assets/logic.js (pure, unit-tested with node:test in tests/js/) and
  assets/core.js; generator CSS moved to assets/base.css with one merged token
  set (zero computed-style differences across 18,418 elements at three widths).
- Tooling (report-only, ADR-015 unchanged): urgency-tiered maintenance report
  with markdown/json output and advisory checks, a networked source checker run
  by hand, a weekly workflow that rewrites one "Review queue" issue, and CI
  guardrails (docs drift, inline-script syntax check, pinned PyYAML,
  release_check.py, PR template). A published UID or edition ID may disappear
  only through a reviewed entry in data/retired_identities.yml; CI's identity
  check enforces this (refines ADR-004).
- Review: an adversarial review confirmed 21 findings (none high), all fixed:
  deep links into the archive or past Starred only, malformed hashes, stale
  hashes overriding newer filters, rows without a toggle hiding their evidence
  line, rollover copying cutoff notes into projections, prior-host zones on
  unannounced editions, sticky headers covering keyboard focus, an unfillable
  sprite star and a changing star label, the clipped asterisk, compact-card
  highlight and contrast, an upcoming edition without a call being tiered
  successor-missing (new call-unannounced tier), and the weekly workflow
  adopting anyone's "Review queue" issue (now limited to its own).
- Consequences: no published UID, edition ID, deadline type or topic slug
  changed. Browser regressions: tests/venue_more.mjs; Python: test_page_features.

## ADR-041: A Researcher-Facing README With Generated Screenshots

- Date: 2026-10-29
- Context: The owner asked for a README that looks professional on GitHub,
  often the first page a researcher sees. The earlier README (ADR-022/034) was
  a few plain paragraphs.
- Decision: Keep the approved pieces (banner first, the Open Venue Radar
  heading, plain-text affiliation, the final licensing paragraph with the
  personal-project clarification) and add a centred hero (subtitle, three
  badges, a short facts line, a linked screenshot) plus short sections on
  deadlines, coverage, calendar feeds, how dates are checked and how to help.
  It stays nontechnical; maintainers get one link to the documentation index.
  Screenshots are WebP files rendered from the committed page by
  scripts/build_readme_images.mjs: offline, with the clock pinned to noon UTC
  on last_updated, each on a light-teal card (the hero puts the desktop and
  phone views on one card) so they read as deliberate panels in GitHub's dark
  theme. The website subtitle now also heads README, refining ADR-034's note
  that README's description stays independent; the X draft remains
  independent. Exact structure and wording rules live in site_copy.md.
- Subtitle: the owner replaced ADR-034's final copy selection with "Find where
  to submit next: conference deadlines for machine learning and AI,
  neuroscience, healthcare, complex systems, and control." It names the task
  and what the site lists, keeps machine learning and AI first, and is shorter.
- Dark banner: at the owner's request a `<picture>` source shows a transparent
  1400x175 banner in GitHub's dark themes. Its mark is an exact palette swap of
  the current logo (border to #E6EDF3, white interior back to transparent,
  alpha unchanged) and its title is #E6EDF3. The white banner is unchanged.
  GitHub's markdown renderer moves the image out of a `<picture>` wrapped in a
  link (checked with its API), so the banner is a bare `<picture>` and is no
  longer a link; the "Open Venue Radar" heading and hero image link to the site.
- Alternatives considered: plain screenshots (white slabs in dark mode);
  side-by-side phone and menu screenshots (illegible at phone width); a table
  of families (half-width on desktop, tall cells on phones); license and
  catalog-count badges (developer noise, stale numbers); moving project_docs
  and AGENTS.md out of the repository (the owner kept them tracked).
- Consequences: Catalog size appears only as "130+ conference series", and a
  test fails if that exceeds the series count, if a README image or local link
  is missing, if assets/readme holds an unused image, or if a badge label gains
  a number. Screenshots are illustrations, refreshed when the page's look
  changes rather than on every data update. README's family labels, status
  wording, feed names, menu steps and issue-form links change together with
  the site. No data, feed or UID changes; the generated page changes only in
  its subtitle. Rerunning build_readme_banner.mjs rewrites both banners, and
  antialiasing can differ between Chrome versions, so keep the committed white
  banner unless it is intentionally refreshed.

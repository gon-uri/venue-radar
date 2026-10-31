# Roadmap

Last synchronized: 2026-10-30

Current implementation is summarized in [implementation status](implementation_status.md).
Use [the documentation index](README.md) for procedures; the completed milestones
below are history, not instructions to reimplement old designs.

## Venue Radar Redesign

- Completed: refined calendar/radar identity, simple README, MIT/CC BY licensing,
  author/social links, five normalized sizes, eight hierarchical topic families,
  offline city map plus conference tables, the initial eight dynamics/control series, and
  synchronized catalog workbook with repeatable maintenance tooling.
- Completed community setup: Giscus prerequisites verified through its official
  checker; the live comments widget, Discussions, and request form are ready.
- Completed usability polish: single collapsible filter panel expanded by default
  on desktop and collapsed on mobile, narrower topics,
  independent CCF filter, linked rank headings/webpage scores, larger branding,
  header calendar action, more evident tab selection, inline Search, clearer
  topic/subtopic disclosure cues, and an always-visible deadline opportunities
  checkbox outside the filter panel. Larger title/logo and filter-disclosure
  sizing accompany the selected, locally embedded Audiowide title. Selected
  typography and asset provenance are documented in [branding](branding.md).
  Conference names now use semibold weight 600 without increasing font size
  or changing color in either table, including past editions.
- Completed mobile scanning: cards show only their first three fields initially,
  with independent More info / Less info controls for the rest. Desktop tables
  stay complete. Expansion survives filtering, tab switches and resizing;
  keyboard controls, archived editions and the no-JavaScript fallback are tested.
  Mobile refinement adds a quiet 36px white disclosure row, 13px field labels,
  pale teal conference headers, stronger 1px outlines and 14px card spacing.
- Completed branding refinement: four-color, geometry-preserving logo recolor
  and a full-width white Audiowide/logo banner at the beginning of README.
- Completed filter/sharing polish: always-visible Clear filters aligned with
  the disclosure heading, an eight-family topic viewport, removal of the
  duplicate Time series shortcut, default-selected Show submission options only,
  header X draft/repository-star actions and a simple white radar favicon.
- Completed header/attribution polish: rightmost calendar action with its
  caption below, no redundant map heading, shorter website attribution and
  plain-text README department name, approved Conferences & Map label and
  personal-project clarification at the end of README's final paragraph.
  The selected ML/AI-first introduction highlights neuroscience, healthcare,
  complex systems and control. Exact current copy is in site_copy.md;
  rejected alternatives remain optional local working history.
- Completed README showcase (ADR-041): centred hero with a desktop/phone
  screenshot, coverage with the eight families and host-city map, feed links,
  a trust section with short answers, and help links. Screenshots are rendered
  from the committed page by `scripts/build_readme_images.mjs`; a transparent
  dark banner serves GitHub's dark themes. The owner also chose the subtitle
  "Find where to submit next: conference deadlines for machine learning and
  AI, neuroscience, healthcare, complex systems, and control."
- Completed repository migration: gon-uri/venue-radar with updated public
  links, Giscus name, attribution, and Git origin. Preserve all published event
  UIDs and the existing community mapping; old feed subscriptions need new URLs.
- Deferred: user accounts, live scraping, custom backend, and map tile services
  are deliberately outside the static architecture.

## Milestones

### AI Deadlines Coverage

- Completed: the 11 approved additions (AutoML, LoG, CoRL, GECCO, SaTML, ProbML,
  AAMAS, MLSys, CogSci, ICIP, Interspeech), including three focused new subtopics.
- Completed: EuroGP, KR, ICAPS and all 12 vision/imaging/multimedia candidates,
  including both dedicated biometrics venues FG/IJCB. Five additional leaves
  distinguish reasoning, planning, graphics, multimedia, and biometrics;
  recurrence and source limitations are documented in vision_ai_expansion.md.
- Completed: the 13 language/retrieval/web selections plus ICRA, RSS and SMC,
  with five focused new leaves, eight-topic filters, central family identities,
  and curated Time series subtopic matching. Evidence is in nlp_robotics_expansion.md.
- Backlog: [conference_candidates.md](conference_candidates.md) preserves all
  57 originally missing series: 42 added and 15 still untracked, plus future-only
  ICWM separately. Further additions require approval and official-source review.

### Baseline Static Calendar

- Goal: Maintain a public static conference calendar with committed HTML and ICS outputs.
- Priority: High
- Dependencies: Valid conference YAML data, Python build scripts, GitHub Pages configuration.
- Estimated complexity: Medium
- Completion status: Completed

### Data Quality and Freshness

- Goal: Compare all provisional meeting and submission dates with current organizer schedules about monthly, preserving uncertainty until evidence is published.
- Priority: High
- Dependencies: `data/conferences.yml`, official conference pages, validation rules.
- Estimated complexity: Ongoing
- Completion status: In Progress

### Topic Coverage

- Goal: Maintain eight broad families: ML & Data Science; NLP, Agents & Retrieval; Vision & Multimedia; RL, Robotics & Control; Complex Systems, Time Series & Signals; Healthcare & Biometrics; Neuroscience & Neurotechnology; Responsible & Trustworthy AI. Central identities keep generic ML methods from overwhelming specialist searches; individual subtopics retain broader sourced scope matching.
- Priority: Medium
- Dependencies: `data/topics.yml`, validation, per-topic ICS generation.
- Estimated complexity: Low
- Completion status: In Progress

### Detailed Conference Scopes

- Goal: Keep useful, curated series profiles beyond the four visible main
  topics, avoiding indiscriminate import of expansive CFP inventories.
- Completed: sourced profile schema, primary/additional matching in search,
  filters and topic feeds, scope evidence in calendar descriptions (removed
  from ICS by ADR-044; profiles are not displayed on the site), a separate
  workbook sheet, and a missing/stale/prior-edition review queue.
- Current coverage: 124 of 175 series, including all 42 AI Deadlines additions,
  all 16 complex-systems/neuroscience additions and all 44 related-venue
  additions (2026-10-31).
- Remaining work: curate the 51 missing profiles from official sources and
  review existing profiles about monthly. Prior-edition evidence stays dated.
- Guidance: [conference_scopes.md](conference_scopes.md).

### Complex Systems And Neuroscience Expansion

- Completed: 16 approved series, 22 sourced edition records, scope profiles,
  central identities, three focused leaves and confirmed-city aliases.
- Preserve: all eight family names/order and the existing website's layout,
  status behavior and abstract submission indications.
- Ongoing: compare estimated calls with official CFPs monthly; resolve ICCN's
  date conflict and the unannounced NODYCON/DDAP/DDCAC next editions. Preserve
  publication/abstract-only distinctions in notes, without a public UI feature
  until the Archival Option Tag And Filter milestone has an ADR the owner
  has approved.
- Guidance: [dynamics_neuroscience_expansion.md](dynamics_neuroscience_expansion.md).

### Related-Venue Expansion

- Completed (2026-10-31): a vetted search of 198 related venues and the
  owner's selection of 44 series (60 edition records: 45 confirmed meetings,
  15 estimated), each drafted from official pages and re-checked by an
  independent verifier, with families, scope profiles, 26 host cities,
  17 ICORE and 12 CCF ranks, 15 sourced acceptance rates and cadences.
- Open: whether to track IEEE ASLI, the 2027 successor of ASRU and SLT; the
  owner's two "maybe" venues (SIGGRAPH Asia, VSS) and 148 further candidates,
  preserved for later rounds; showing edition Notes on the site (ADR-045).
- Guidance: [candidate backlog](conference_candidates.md#related-venue-search-2026-10-3031).

### Website Usability

- Goal: Keep the static site easy to scan, search, filter, and subscribe to.
- Priority: Medium
- Dependencies: `scripts/build_site.py`, generated `docs/index.html`, committed ICS feeds.
- Estimated complexity: Medium
- Completion status: Completed for current scope. ADR-039 added cutoff clocks,
  subscriptions, series/submission feeds, successor links, empty states and
  accessibility/tablet fixes. ADR-040 added compact mobile cards, deep links
  and URL state, evidence lines with a correction form, starred series, a
  status guide, link previews, host-zone day-only cutoffs, conflicting-cutoff
  notes and the client-code split.
- Later ideas, not approved: dark mode, deadline-window planning filters, an
  extensions field, CITATION.cff and month dividers in long tables.

### Conference Ranking Column

- Goal: Show independent sourced ICORE and CCF rankings without implying that workshops or unlisted venues inherit a parent conference's rank.
- Priority: Medium
- Dependencies: ICORE 2026 portal export, official CCF 2026 catalog; series-level mapping, source/year metadata, and a blank state for uncovered venues.
- Estimated complexity: Medium
- Completion status: Completed with ICORE and CCF 2026; refresh when either publisher releases a new list.

### Submission Opportunities And Acceptance Evidence

- Goal: Show whether a new research contribution can still be submitted, align countdown and collapsed track/action with prerequisite gates, distinguish evidenced opening from confirmed opening-unverified opportunities, and retain historical acceptance bands and source-linked percentages when available.
- Priority: High
- Dependencies: `gate_for` deadline metadata, historical rate evidence, site generation, validation, browser checks.
- Estimated complexity: Medium
- Completion status: Completed for current catalog; rate coverage expands only as reliable sources are found.
- Completed correction: green Open/Scheduled/Submission opportunity states,
  yellow estimates, red closed routes, submission-action countdowns and Closed
  time-left labels. Expanded schedules and chronological closed-row placement
  remain available; AAMAS/MLSys transitions are covered by browser regressions.

### Archival Option Tag And Filter

- Goal: Tag each conference with whether it has an archival option, and add a
  filter for it. "Has an archival option" means at least one track for new
  work publishes accepted papers in archival proceedings or a journal (for
  example the ACM Digital Library, IEEE Xplore, PMLR or Springer LNCS). It
  does not mean every track is archival. Requested by the owner on 2026-10-30
  after asking whether WSDM is archival. The same day the owner chose this
  per-conference tag over marking each track, for simplicity.
- Priority: Medium (proposed; the owner has not set a priority)
- Dependencies: a sourced value per series, validation, the filter panel and
  URL state, owner-approved public copy recorded in site_copy.md, the
  maintenance report and the workbook mirror. If calendar event descriptions
  carry the tag, they need the same definition and caution, because each
  event is one track's deadline.
- Estimated complexity: Low to medium for code: one filter group and a small
  tag, with no change to statuses or countdowns. Data is the larger part: in
  the 2026-10-30 review about 85 of 130 series had no usable evidence, but one
  confirmed archival track settles Yes, usually from one sentence of the main
  call for papers.
- Completion status: Not started. The owner chose the direction (a
  per-conference tag). First step: a new ADR with the details and the public
  wording, approved by the owner; only then change data or code. Until then
  these rules still apply: ADR-036's "Add no publication UI", the AGENTS.md
  rule that abstract-only caveats stay in notes/docs, and the data schema's
  "Do not add a publication column, badge or change to status behavior
  without approval". That ADR must also update the matching no-UI statements
  in architecture.md, data_maintenance.md, conference_scopes.md,
  implementation_status.md and dynamics_neuroscience_expansion.md.
- Values: Yes (at least one track for new work is archival); No (only
  abstract-book, archived-abstract or non-archival tracks, such as
  abstract-only meetings and non-archival workshops); Not checked yet (the
  default, never shown or filtered as No). Never infer it from the free-text
  `submission_type` (such as "Paper-based"), ranks or OpenReview use.
- Proposed storage: one value per series, like acceptance rates, with a
  source URL and the edition year it was checked from, shown with the tag.
  Past proceedings are not promises for later editions (ADR-036), so take
  the value from the latest edition with a published call and have the
  maintenance report queue it again when a newer call appears, as it does
  for scope profiles.
- Open for the ADR: whether a track whose publication is opt-in or opt-out
  (such as WSDM Findings) counts; whether only tracks of a supported
  new-contribution type count, so that a doctoral consortium abstract or
  NODYCON's optional paper for an already presented abstract cannot settle
  Yes alone; and whether the filter matches a value checked from an older
  edition.
- Wording requirement (owner, 2026-10-30): the tag's tooltip and the filter
  section's description must say exactly what "has an archival option"
  means, and add a very brief caution to check which track is still open,
  because the deadline shown may belong to a track that is not archival.
  Tooltips (`title`) do not appear on phones, so the filter description must
  be visible text in the filter section; filter groups have only a heading
  and options today. Drafts, not approved. Tag tooltip, with the year
  checked: "Archival option (2027 edition): at least one track publishes
  accepted papers in archival proceedings or a journal. Other tracks may
  not; check which track is still open." Filter description: "Yes: at least
  one track publishes accepted papers in archival proceedings or a journal.
  Other tracks may not; check which is still open. Not checked yet means
  unknown, not No."
- Known limitation, accepted: the tag describes the conference, not the next
  deadline. With the filter on, WSDM 2027 still appears after its Nov 17
  short-paper deadline and counts down to the Nov 30 WSDM Day abstract. That
  track is in the proceedings but welcomes work under review elsewhere, and
  its call never says archival. The deadline label names the track.
  Per-track values can be added later without changing the tag.
- Evidence (manual repository review on 2026-10-30; counts approximate):
  repository text points to Yes for about 25 series and to No for about 20
  (abstract-only venues such as SfN, AREADNE, NetSci and Dynamics Days, and
  non-archival workshops such as TS4H), some only from a prior edition or
  the abstract-only format. WSDM 2027 is Yes: full and short papers are
  published in the ACM Digital Library
  ([full](https://www.wsdm-conference.org/2027/cffp.html) and
  [short](https://www.wsdm-conference.org/2027/cfsp.html) paper calls),
  although its WSDM Day, doctoral, Industry Day and workshop tracks differ.
- Before shipping: fill in every series with an open or upcoming submission
  deadline (119 on 2026-10-30), starting with those without evidence; the
  site collects no visit data to rank them by. When the filter shows only
  Yes, say how many conferences are hidden as not checked yet. Once
  released, the filter's query-string key must keep its name, because shared
  links depend on it (ADR-040). Calendar event UIDs must not change.
  Proposed, not decided: put the tag in an existing cell rather than a new
  column, which would change ADR-035's mobile cards.

### Repeatable Data Refresh

- Goal: Keep actionable monthly source-linked queues for edition reviews, historical acceptance evidence, and curated conference scopes, plus cadence-aware next-edition projections that never imply official confirmation.
- Priority: High
- Dependencies: `scripts/maintenance_report.py`, `scripts/rollover_editions.py`, official organizer pages, documented review procedure.
- Estimated complexity: Ongoing
- Completion status: Completed tooling and procedure; reviews remain recurring work. ADR-040 added urgency tiers, advisory checks, a weekly Review queue issue and a manual source checker. ADR-042 added the pre-deadline recheck tier, the midnight-opening advisory, future review-day checks, `tls-error` reporting and a pinned Python 3.12.

### Calendar Feed Reliability

- Goal: Preserve deterministic calendar UIDs, stable sorting, standards-compliant escaping, and useful feed variants.
- Priority: High
- Dependencies: `scripts/build_ics.py`, `scripts/validate.py`, data schema.
- Estimated complexity: Medium
- Completion status: Completed for current scope. ADR-044 (2026-10-31)
  shortened titles to `<short title> (est.) · <label>`, moved topics to
  CATEGORIES, dropped scope and other row details from descriptions (keeping
  the format line and Notes, and adding a link to the edition row) and added
  a 1 MB size test. `calendar-all.ics` went from 1.06 MB (above the roughly
  1 MB community reports give for Google Calendar URL feeds; not an official
  figure) to 735 KB, with UIDs unchanged. ADR-045 (2026-10-31) keeps it under
  the limit after the 44-venue addition by putting each edition's Notes only
  on its meeting event (864 KB). Next levers, if the catalog keeps growing:
  drop CATEGORIES or prune past editions from the aggregate feeds (owner
  decisions). The owner's Google subscription to the 1.06 MB
  feed still worked on 2026-10-31. Real-app checks of the new titles are
  pending.

### Regression Testing Improvements

- Goal: Add targeted tests or checks for ICS formatting, generated-output drift, and static site behavior.
- Priority: Medium
- Dependencies: Existing build scripts, selected test framework or script conventions.
- Estimated complexity: Medium
- Completion status: In Progress; targeted metadata/ICS tests, Node unit tests for the client logic, repeatable browser smoke checks and CI drift/identity/inline-script guardrails cover the site. Screenshot-baseline comparisons remain future work.

### Persistent Project State Documentation

- Goal: Make the repository self-documenting for future Codex sessions without relying on conversation history.
- Priority: High
- Dependencies: AGENTS.md, the documentation index, current status/architecture,
  field reference, addition/maintenance/development guides and technical ADRs.
- Estimated complexity: Low
- Completion status: Completed
- Completed onboarding audit: task-based navigation, complete addition checklist,
  schema examples, current-versus-historical separation and link/example regressions.
  Keep these guides synchronized as schema or workflow changes.
- Completed documentation boundary: gitignored local session/design/copy notes,
  self-contained public handbook, current-branding guide and ignore/tracking
  regressions. Detailed working logs are not required for a fresh clone.

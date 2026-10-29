# Roadmap

Last synchronized: 2026-10-08

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
  filters and topic feeds, scope evidence in calendar descriptions, a separate
  workbook sheet, and a missing/stale/prior-edition review queue.
- Current coverage: 79 of 129 series, including all 42 AI Deadlines additions
  and all 16 complex-systems/neuroscience additions.
- Remaining work: curate the 50 missing profiles from official sources and
  review existing profiles about monthly. Prior-edition evidence stays dated.
- Guidance: [conference_scopes.md](conference_scopes.md).

### Complex Systems And Neuroscience Expansion

- Completed: 16 approved series, 22 sourced edition records, scope profiles,
  central identities, three focused leaves and confirmed-city aliases.
- Preserve: all eight family names/order and the existing website's layout,
  status behavior and abstract submission indications.
- Ongoing: compare estimated calls with official CFPs monthly; resolve ICCN's
  date conflict and the unannounced NODYCON/DDAP/DDCAC next editions. Preserve
  publication/abstract-only distinctions without adding a public UI feature.
- Guidance: [dynamics_neuroscience_expansion.md](dynamics_neuroscience_expansion.md).

### Website Usability

- Goal: Keep the static site easy to scan, search, filter, and subscribe to.
- Priority: Medium
- Dependencies: `scripts/build_site.py`, generated `docs/index.html`, committed ICS feeds.
- Estimated complexity: Medium
- Completion status: Completed for current scope; ADR-039 added cutoff clocks,
  subscriptions, series/submission feeds, successor links, empty states and
  accessibility/tablet fixes. Remaining ranked ideas (compact mobile cards,
  shareable links, evidence display, link previews, safer date-only cutoffs,
  maintenance triage/CI guardrails) await approval.

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

### Repeatable Data Refresh

- Goal: Keep actionable monthly source-linked queues for edition reviews, historical acceptance evidence, and curated conference scopes, plus cadence-aware next-edition projections that never imply official confirmation.
- Priority: High
- Dependencies: `scripts/maintenance_report.py`, `scripts/rollover_editions.py`, official organizer pages, documented review procedure.
- Estimated complexity: Ongoing
- Completion status: Completed tooling and procedure; reviews remain recurring work.

### Calendar Feed Reliability

- Goal: Preserve deterministic calendar UIDs, stable sorting, standards-compliant escaping, and useful feed variants.
- Priority: High
- Dependencies: `scripts/build_ics.py`, `scripts/validate.py`, data schema.
- Estimated complexity: Medium
- Completion status: Completed for current scope

### Regression Testing Improvements

- Goal: Add targeted tests or checks for ICS formatting, generated-output drift, and static site behavior.
- Priority: Medium
- Dependencies: Existing build scripts, selected test framework or script conventions.
- Estimated complexity: Medium
- Completion status: In Progress; targeted metadata/ICS tests and repeatable browser smoke checks cover the redesign. Screenshot-baseline comparisons remain future work.

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

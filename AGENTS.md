# AGENTS.md

Venue Radar is a static conference calendar. The "database" is versioned YAML,
not a server or SQL database. Recover project state from this repository, not
chat history. Start with [the documentation index](project_docs/README.md).

## Before Making Changes

Read these files before changing anything:

- [Current status](project_docs/implementation_status.md)
- [Roadmap](project_docs/roadmap.md)
- [Architecture and file ownership](project_docs/architecture.md)
- [Technical decisions](project_docs/decisions.md), respecting later refinements
- [Public/private documentation policy](project_docs/documentation_policy.md)

Then reconstruct the current project state from the repository. If the docs and
code disagree, update the docs before implementing new work.

Optional local context may exist in `private_notes/README.md` and
`private_notes/session_log.md`. Read it only when useful; a fresh clone without
private notes must be fully maintainable. Current source/public guides take
precedence over historical notes. Never force-add or publish this directory.

## Choose The Workflow

- Update dates or review missing information:
  [data maintenance](project_docs/data_maintenance.md).
- Add a series or edition:
  [conference-addition checklist](project_docs/adding_conferences.md).
- Check fields, confidence, gates and supported deadline types:
  [data schema](project_docs/data_schema.md).
- Change topics/profiles: [topic audit](project_docs/topic_audit.md) and
  [scope curation](project_docs/conference_scopes.md).
- Build, inspect, synchronize the workbook or publish:
  [development](project_docs/development.md).

## Project Constraints

- The calendar is intentionally static: no backend server, database, paid
  hosting, or OpenAI API dependency.
- `data/conferences.yml` is the canonical conference data source.
- The XLSX workbook is a review mirror, never an independent source of truth.
  Series-keyed ranks, rates, families and scopes must use exact `series` names.
- `data/conference_scopes.yml` holds complementary, sourced series profiles.
  Read `project_docs/conference_scopes.md` before editing them. Keep extra topics
  characteristic and curated; never import an exhaustive CFP topics list.
- `data/conference_families.yml` assigns every tracked series one to three
  central identities in the eight-family taxonomy. Broad family filters use
  these identities; individual subtopics use the curated topic union.
  Consult `project_docs/topic_audit.md` when adding or retagging a series.
- `docs/` is reserved for generated GitHub Pages outputs: `index.html` and
  `.ics` feeds.
- `project_docs/` contains maintained project-state documentation.
- `private_notes/` is gitignored local working history: detailed session logs,
  brainstorming, personal preferences, unfinished plans and rejected designs.
  Public requirements, source evidence and maintenance procedures stay in
  `project_docs/`; do not put credentials or sensitive material in local notes.
- `project_docs/conference_candidates.md` preserves the dated AI Deadlines
  comparison and untracked candidate backlog. Consult it before expanding the
  catalog; candidates are not approved additions or confirmed calendar data.
- Use `estimated` for inferred or placeholder dates. Do not make uncertain data
  look confirmed. Meeting dates, deadline confidence, cutoff precision and
  portal-opening evidence are different facts; see the schema guide.
- Only supported submission types enable new-contribution opportunities.
  Arbitrary custom types may validate but are schedule-only. Mandatory gates
  must use `gate_for`; organizer proposals and production steps are not submissions.
- Preserve the eight agreed topic families and public submission semantics.
  Abstract-only publication caveats belong in notes/docs, not a new UI feature.
- Calendar event UIDs must be deterministic and stable. Never use random values
  for calendar UIDs. Preserve published edition IDs, deadline types, topic slugs,
  and the historical `scientific-conference-calendar` UID namespace.
- Do not edit generated files by hand, stamp unreviewed sources as fresh, or
  publish candidate-backlog entries without approval and official-source review.

## Local Commands

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Validate data:

```bash
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
node --test tests/js/*.test.mjs
```

Build all generated outputs:

```bash
python3 scripts/build_all.py
```

Before committing a release, run the combined check and the identity check:

```bash
python3 scripts/release_check.py
python3 scripts/check_identity.py --base origin/main
```

## After Changes

- Update affected files in `project_docs/`.
- Record important technical decisions in `project_docs/decisions.md`.
- Keep detailed session entries in `private_notes/session_log.md`, newest first;
  create the ignored directory/log locally if needed. Public status/guides must
  still contain material outcomes, evidence gaps and verification limitations.
- Verify source changes and generated outputs together; include browser checks
  for affected data/UI behavior and workbook checks when the mirror changes.
- Follow the development guide's publication checklist when publishing is
  requested; record checks actually performed and any remaining limitations.
- Check that no private notes are staged; Git does not back them up or erase
  their previously published history.
- Keep changes small and reviewable.

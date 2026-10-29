# Project Documentation

Reviewed: 2026-10-08.

Venue Radar tracks scientific conferences through reviewed YAML and publishes
static HTML/calendar feeds. There is no backend database. The public
[repository README](../README.md) is intentionally short and nontechnical;
this directory is the maintainer/agent handbook.

## Start Here

1. Read [AGENTS.md](../AGENTS.md), [current status](implementation_status.md),
   [roadmap](roadmap.md) and [architecture](architecture.md).
2. Read [technical decisions](decisions.md) for the invariants and relevant ADRs,
   and [documentation policy](documentation_policy.md) for the public/private split.
3. Check `git status --short`; preserve unrelated local changes. Choose the
   task guide below and inspect the relevant source files before editing.

Current guides describe the implemented behavior. ADRs are dated technical
history: older counts and superseded designs are not current requirements.
Follow an explicitly superseding ADR, not an earlier alternative.
If code and current guidance disagree, investigate and correct the documentation
before new implementation work. Do not silently change code to match old prose.

## Find The Right Guide

| Task or question | Maintained reference |
| --- | --- |
| What is implemented, and what still needs work? | [Implementation status](implementation_status.md), [roadmap](roadmap.md) |
| Where does a fact or piece of code belong? | [Architecture](architecture.md) |
| Refresh dates, missing calls or historical evidence | [Data maintenance](data_maintenance.md) |
| Add a conference series or its next edition | [Adding conferences](adding_conferences.md) |
| Required fields, confidence, time precision, opening evidence, deadline types, gates, stable IDs | [Data schema](data_schema.md) |
| Assign central families or consider a new subtopic | [Topic audit](topic_audit.md) |
| Write characteristic scope prose and extra topics | [Conference scopes](conference_scopes.md) |
| Set up Python, build/test, preview, synchronize XLSX, publish | [Development and publication](development.md) |
| Configure Giscus or migrate repository URLs | [Data maintenance: project services](data_maintenance.md#project-services) |
| Find deferred conference candidates | [Candidate backlog](conference_candidates.md) |
| Understand a technical tradeoff | [Decisions](decisions.md) |
| Check release verification | [Current status](implementation_status.md), relevant tests, commits and CI results |
| Decide what is public documentation or a local working note | [Documentation policy](documentation_policy.md) |
| Maintain the selected logo, font, banner and provenance | [Current branding](branding.md) |

## Evidence And Design Records

These are useful supporting references, not alternative catalogs or automatic
approval to add venues:

- [AI/vision expansion](vision_ai_expansion.md): edition evidence, identity and
  acceptance-rate caveats for that batch.
- [Language/robotics expansion](nlp_robotics_expansion.md): ARR, staged papers,
  proposed dates and irregular recurrence.
- [Complex-systems/neuroscience expansion](dynamics_neuroscience_expansion.md):
  abstract-only formats, regional Dynamics Days, date conflicts and follow-ups.
- [Site copy](site_copy.md) and [sharing](sharing.md): selected public wording.
- [Current branding](branding.md): selected assets, typography and provenance.

Detailed session logs, font/logo explorations and rejected copy drafts live
in the ignored `private_notes/` folder when available locally. They are optional
context, not linked dependencies or part of a fresh clone. The public handbook
retains everything needed to understand and maintain the project.

## Keep The Handbook Useful

- Put current behavior in status/architecture and task procedures in their
  owning guide. Link to detail rather than repeat it across every file.
- Record material technical rationale in the next numbered ADR. Keep detailed
  working history in local private notes; promote requirements, evidence,
  follow-ups and important verification results into their public owning guide.
- Update the index when adding a maintained guide. Counts in dated audit
  snapshots are historical; current catalog counts belong in status/topic audit.
- Record what was actually verified. Structural validation does not prove an
  organizer date is correct, a portal is open, or a deployment succeeded.
- Technical-only documentation changes must not modify conference YAML, XLSX,
  brand assets or generated `docs/` output. Rebuilds can verify this invariance.

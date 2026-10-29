# Adding Conferences And Editions

Reviewed: 2026-10-08. Use this checklist for additions; use
[data maintenance](data_maintenance.md) to refresh existing records and
[data schema](data_schema.md) for field/type rules.

## 1. Check Identity And Approval

Confirm the user's approved scope. Search the catalog, series-level mappings
and [candidate backlog](conference_candidates.md) before adding anything:

```sh
rg -n -i 'ACRONYM|full conference name|known alias' data project_docs/conference_candidates.md
```

Check organizer/association identity, not just the acronym. Complex Systems
CCS is not ACM CCS; ICCN Cognitive Neurodynamics is not clinical neurophysiology.
AutoML/AUTOMLCONF, LoG/LOG and SaTML/SATML are aliases. LOD/AIS retains its
published series key. Do not duplicate joint editions or merged predecessors
such as IJCB/BTAS/ICB. Preserve existing IDs, types and exact series strings.

A new *edition* of an existing series normally needs only a new edition record,
not duplicate family/scope/rank mappings. A genuinely new series needs the
multi-file work below. Keep historical editions; do not recycle their IDs.

## 2. Review Official Evidence

Read the edition's official CFP/date page, organizer/association announcement
and submission instructions. Discovery aggregators help find candidates but
are not sufficient evidence to confirm dates. Record direct source URLs and
the actual review day. Check:

- Main meeting range versus workshops/tutorials, location, mode and recurrence.
- Deadline date, cutoff hour, timezone, extensions and independent tracks.
- Mandatory abstract/registration stages and actual portal-opening evidence.
- Whether a contribution is a new paper/abstract/poster, or a restricted
  revision, organizer proposal or production step.
- Full-paper proceedings, abstract book, archived abstracts or selected journal
  publication; do not promise a publication format from an unrelated edition.
- Central scientific scope, supported rank identity and historical rate evidence.

Use documented estimates only when there is a defensible timing/cadence basis.
Keep confirmed meeting dates separate from proxy deadlines. If no trustworthy
next-edition timing exists, track the latest verified historical edition and
queue the next call instead of fabricating an upcoming row. Empty deadlines
are valid. Conflicting organizer dates stay provisional pending reconciliation.

## 3. Edit The Owning Files

| File | New series | Next edition of an existing series |
| --- | --- | --- |
| `data/conferences.yml` | Add at least one sourced edition record with up to four central leaves. | Add a new stable ID/year; preserve prior editions. |
| `data/conference_families.yml` | Add one-to-three central IDs from the agreed eight families. | Reuse the exact series key; change identity only with scope evidence. |
| `data/conference_scopes.yml` | Add a curated sourced profile if evidence supports it. | Review the existing profile; keep its actual evidence year until a new CFP is reviewed. |
| `data/cities.yml` | Add a confirmed city or exact alias if missing. | Add the newly confirmed location; do not guess an unannounced host. |
| `data/icore_rankings.yml`, `data/ccf_rankings.yml` | Add only direct, verified current-release identities. | Reuse series-level ranks, not invented edition-level duplicates. |
| `data/acceptance_rates.yml` | Add only supported historical rates/bands; otherwise leave absent. | Refresh evidence only after checking new statistics. |
| `data/topics.yml`, `data/topic_families.yml` | Usually unchanged; add a justified reusable leaf only if approved/needed. | Normally unchanged. Preserve eight family IDs/names/order and leaf slugs. |
| `scripts/rollover_editions.py` | Add to `CADENCE_YEARS` only for verified recurrence. | Recheck cadence; irregular/joint series stay outside automatic projection. |
| `data/metadata.yml` | Update actual dataset-review date before rebuilding. | Same rule. |
| `data/core_conferences_normalized_tags.xlsx` | Synchronize from YAML; verify the appended series. | Synchronize if its latest-edition mirrored fields change. |
| `project_docs/` | Update current status/topic counts, sources/caveats and material verification; resolve any candidate-backlog change. | Record verified changes and outstanding review items. |
| `tests/` and generated `docs/` | Cover changed behavior/identity risks; update catalog-specific browser expectations and rebuild. | Same verification rule; existing event IDs must stay stable. |

Read [topic audit](topic_audit.md) and [scope curation](conference_scopes.md)
before tagging. A conference using ML is not automatically centrally ML.
Keep characteristic scope rather than importing the complete CFP topic list.
When adding a leaf, supply its exact vocabulary entry, one family and compact
label; also add its definition to the workbook helper's definition map if needed.

## 4. Use A Valid Record Shape

The following is a **fictional schema example**, not an approved conference or
real CFP. Replace every identity/date/source with verified evidence; do not
append this example to the catalog.

```yaml
- id: example-conf-2027
  series: Example Conference
  year: 2027
  title: Example Conference on Machine Learning
  short_title: EXCONF 2027
  website: https://example.org/conference/2027/
  cfp_url: https://example.org/conference/2027/cfp/
  source_urls:
  - https://example.org/conference/2027/dates/
  location: To be announced
  mode: in-person
  topics:
  - Machine Learning
  size: M
  submission_type: Full papers with mandatory abstract registration
  deadlines:
  - type: abstract
    label: Main-track mandatory abstract registration
    datetime: '2026-11-20T23:59:00-12:00'
    source_url: https://example.org/conference/2027/cfp/
    gate_for: full_paper
  - type: full_paper
    label: Main-track full-paper submission
    datetime: '2026-11-27T23:59:00-12:00'
    source_url: https://example.org/conference/2027/cfp/
  conference_start: '2027-06-14'
  conference_end: '2027-06-16'
  last_checked: '2026-10-08'
  confidence: confirmed
  notes: Fictional example. Real dates, AoE evidence and size basis must be checked.
```

The mandatory abstract gate closes the route to fresh submissions after
November 20, even though its paper date is later. No opening is asserted here;
with a future confirmed gate the existing fallback is Submission opportunity.
An independent talk abstract would omit `gate_for` and describe that route.

The companion family mapping would use the same exact series key:

```yaml
Example Conference:
  - ml-ai
```

Do not use two `full_paper` entries or invent a custom "paper" type and assume
it is actionable. Read the [supported types and gates](data_schema.md#supported-new-contribution-types).
For a confirmed day with an unknown cutoff hour, add `time_precision: date`
and explain the provisional ordering timestamp. For a proxy date, explicitly
set `confidence: estimated` on that milestone even if the meeting is confirmed.

## 5. Verify And Publish

Follow [development](development.md) for workbook synchronization and the exact
validation/test/build/publication commands. Verify at least:

- Correct status, countdown and collapsed track/action before/after gates;
  production deadlines must not make a closed conference look open.
- Submission-only default includes open/scheduled/confirmed opening-unverified
  and estimated opportunities, but not closed/unannounced ones.
- Whole-family and individual-subtopic filters, characteristic scope search,
  rankings/rates, map inclusion/exclusion and mobile card details.
- Recurrence, archive placement, new feed links and unchanged published UIDs.
- Latest-series workbook fields, all native tables and re-imported values.

Tests should scale with the change. Existing browser fixtures use a frozen date
and catalog-specific expected counts; update those from the built data, never
change website behavior merely to make an outdated fixture pass. Add targeted
tests for unusual gates, identity collisions or recurrence/evidence conflicts.

Commit source and generated output together when publishing is requested.
Verify Build, Pages and live outputs before claiming publication. Document
unresolved calls/ranks/rates honestly; missing evidence is not a task failure
and is never permission to fill fields with unsourced guesses.

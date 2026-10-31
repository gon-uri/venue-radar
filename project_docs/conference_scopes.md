# Curated Conference Scopes

Reviewed: 2026-10-08

This guide owns profile curation. See [adding conferences](adding_conferences.md)
for the multi-file checklist, [data schema](data_schema.md) for edition/deadline
fields, and [development](development.md#workbook-synchronization) for mirror checks.

The table's up-to-four main topics are a compact description, not an exhaustive
list. `data/conference_scopes.yml` adds a more detailed, source-grounded profile
by exact conference series. Current coverage is 80 of 131 series, including all
42 AI Deadlines additions, CIKM/WSDM and the 16 complex-systems/neuroscience
additions. The other 51 are explicitly queued for review;
an absent profile is not replaced by guessed information.

The new batch's publication formats and abstract-only caveats are documented in
`dynamics_neuroscience_expansion.md`; no new public column or behavior is added.

## Data Ownership

`data/conferences.yml` remains authoritative for editions, dates, locations,
submission routes, and the main display topics. The separate scope mapping owns:

| Field | Meaning |
| --- | --- |
| `additional_topics` | Zero to six unique, characteristic leaves from `data/topics.yml`. |
| `scope_summary` | A concise editorial description of the defining research areas and contribution focus; at most 1,200 characters. |
| `scope_source_urls` | Official CFP, scope, or organizer mission pages supporting the profile. |
| `scope_last_checked` | ISO date of the actual source review, independent of date/rate reviews. |
| `source_year` | Edition of the reviewed evidence, not every edition using the profile. |

Profiles join by exact `series` at build time, like rankings and rates. They are
not copied into every edition or duplicated during rollover. The profile
describes a series using dated evidence; it is not a claim that every historical
edition had an identical CFP. Recheck edition-specific changes and special
themes during monthly maintenance. Primary/additional overlap across editions
is allowed and deduplicated when matching; additional lists themselves are unique.

### Profile Shape

This fictional companion to the addition guide's example illustrates the exact
five fields. It is not a real conference profile and must not enter the catalog:

```yaml
Example Conference:
  additional_topics:
  - Learning Theory & Statistical Foundations
  scope_summary: General machine-learning methods with a characteristic learning-theory strand. Fictional schema example, not a suitability claim.
  scope_source_urls:
  - https://example.org/conference/2027/scope/
  scope_last_checked: '2026-10-08'
  source_year: 2027
```

All five fields are required; `additional_topics: []` is valid. Do not invent
extra profile keys or refresh its evidence year without reviewing a new source.

## Editorial Rules

1. Read the official scope and identify the research communities and problems
   that actually characterize the venue. Prefer main research categories and
   recurring themes over a catch-all applications list.
2. Keep the four display topics central. Add only meaningful omissions to the
   profile, not every topic that could conceivably produce an accepted paper.
3. Do not infer specialist coverage from an incidental example, invited talk,
   single workshop, acronym, or the mere use of ML. A broad ML venue does not
   automatically become a healthcare or neuroscience venue.
4. Put useful finer distinctions in prose rather than proliferating global
   tags: Bayesian optimization for AutoML, graph kernels for LoG, or speech
   synthesis for Interspeech. Add a controlled leaf only when multiple tracked
   venues need that distinction and the taxonomy remains useful.
5. Do not force a target count. Zero additional topics is valid. Six is a
   guardrail, not a goal. When a CFP is enormous, prioritize the defining scope.
6. Record what was reviewed. A prior-edition CFP can support a series profile,
   but keep its actual year and queue a current-edition check. Do not fabricate
   detail when the available official overview is short.

Examples: CoRL requires substantive robot-learning relevance; COLT prioritizes
learning theory; AAMAS focuses on agents and their interactions; MIDL remains
grounded in medical imaging. ICIP's many imaging applications do not each become
an additional specialist tag. MLSys's incidental fairness/interpretability
entries were not promoted to defining tags. NeurIPS retains methodological
coverage without blanket application-domain labels.

## Public Behavior

- Tables still show only the edition's main topics, with no new column.
- Text search also matches the scope summary, additional leaves, compact topic
  labels, and central family names.
- Whole-family checkboxes match curated central identities in
  `data/conference_families.yml`. Individual subtopics match the deduplicated
  primary/additional union. Time series uses the same leaf union inside its
  complex-systems family; its duplicate standalone shortcut has been removed.
  Subtopics within a family use OR, and selected groups use ANY/ALL. Selecting
  every child switches to whole-family matching, just like its parent checkbox.
  Size/rank/rate filters and opportunity status are independent.
- Both tabs and the confirmed-city map use the same expanded matching. Scope
  metadata does not make an estimated meeting eligible for the map.
- Topic ICS feeds use the same union. Since ADR-044, event descriptions no
  longer carry the scope summary, additional topics or scope evidence. The
  site does not display profiles either: they live in this YAML file, where
  they drive search and topic matching.
  Existing feed names, event UIDs, dates, and deadline gates remain unchanged.
- Without a reviewed profile, a conference falls back to its main topics and
  existing search data. Missing profiles are legal but visible in maintenance.
- The workbook has a separate **Conference Scope** sheet; the main catalog
  keeps the four display topics. YAML, not the workbook, is authoritative.

## Regular Review

`python scripts/maintenance_report.py --max-age-days 30` includes a third queue
for missing profiles, stale reviews, and profiles based on a prior edition.
Review the linked official sources about monthly. Update only the relevant
scope profile after actual review; do not refresh its date just because calendar
dates were checked. Add new profiles gradually, starting with missing profiles
and venues with changing scope. Never bulk-import an uncurated CFP inventory.

After edits, run validation, Python tests, and the full build. Synchronize the
workbook when profiles change, then inspect/re-import it. Check representative
summary search, additional-topic filtering, both tabs, map matching, and topic
feed membership. Preserve conference IDs and calendar UIDs. See
[data_maintenance.md](data_maintenance.md) and [development.md](development.md)
for commands and publication checks.

## Evidence Limitations

Some 2027 profiles use the last published 2026 CFP and remain queued for a new
CFP check. GECCO's 2027 URL currently serves a 2026 call: the profile deliberately
records `source_year: 2026`. AISTATS and Interspeech currently offer short
overviews, so no unsupported extra tags were filled in. Scope descriptions are
editorial summaries grounded in those sources, not guarantees of suitability
or substitutes for the organizer's current submission requirements.

# Monthly Review: November 2026

Reviewed: 2026-11-07. This is dated source evidence, not a replacement for the
[maintenance procedure](data_maintenance.md).

## Scope And Changes

The 30-day report identified 131 of 260 editions: seven act-now, four pre-deadline
rechecks, eight soon, 90 later, 13 schedule-only and nine successor-missing.
Official edition/series pages and likely next-edition pages were checked across
that queue, with an editorial focus on changed facts and available submissions.
Five records have source-backed corrections; no series or edition IDs change.
Only these edited records advance `last_checked`; this is not a full factual
recertification of every field in all 260 records.

| Edition | Verified change | Official evidence |
| --- | --- | --- |
| ICML 2027 | Riocentro, Rio de Janeiro, July 31-August 6. Meeting confirmed; January/February submission proxies stay estimated because the call is coming soon. | [Conference](https://icml.cc/Conferences/2027), [dates](https://icml.cc/Conferences/2027/Dates), [pending CFP](https://icml.cc/Conferences/2027/CallForPapers) |
| SIGIR 2027 | Main-paper dates are no longer proposed: mandatory abstract January 14, paper January 21, camera-ready April 30. Keep unknown clock precision and opening evidence separate. | [Full-paper call](https://sigir2027.org/pages/submit-full.html) |
| IEEE NER 2027 | Replace 2025-based proxies with March 15 papers and June 2 independent abstracts. Both are date-only. The repeated 2022 template and its PST clock are not evidence for the 2027 schedule. | [2027 schedule](https://neuro.embs.org/2027/) |
| NAACL 2027 | Add an independent Industry Track paper route due November 13, 23:59 AoE. Its explicit extension and homepage supersede the old October 31 table, rather than reopening ARR submissions. | [Industry call](https://2027.naacl.org/calls/industry_track/), [homepage](https://2027.naacl.org/) |
| COLING 2027 | Add independent Industry Track papers due November 30, 23:59 AoE, without the expired ARR prerequisite. Academic authors with appropriate deployed-system work are eligible. | [Industry call](https://2027.coling-iccl.org/calls/industry_track/) |

The new industry routes use the existing supported `regular_paper` type with
specific labels. ARR event IDs and commitments remain untouched. No portal
opening, unsupported demonstration type or new publication UI is invented.
Main-meeting windows for WACV and SaTML are retained: their notes already
distinguish the extra workshop days shown in the overall event banners.

## Retained Uncertainty And Follow-Ups

- ICML's current call is still a placeholder. KDD's published call remains
  cycle 1 only; no confirmed cycle-2 dates were found. ENOC publishes January
  without a day, CNS CogNeuro marks the late-poster timetable tentative, and
  WASPAA labels its whole schedule tentative. Do not promote those estimates.
- Many later-edition sites are absent, redirect to prior years or have no
  readable current call, including UAI, MICCAI, ICMNS, RLC, COLM, ICDL, ICMLA,
  AALTD and several 2028 projections. Preserve their proxies and old review days.
  A failed fetch is not evidence of cancellation or proof that an estimate is right.
- ICCN remains unreachable; NODYCON's JavaScript-only page did not expose a
  readable next call. No new Dynamics Days CAC/Asia-Pacific announcement was
  verified. Keep their outstanding review items rather than invent recurrence.
- The optional whole-catalog HTTP checker was stopped after 30 of 204 selected
  editions because repeated host waits/timeouts made it unsuitable for this
  bounded pass. Direct official-page checks supplied the facts above; the
  limited five-record rerun is an additional URL check, not a complete audit.
  It completed with all 16 cited URLs reachable (no dead/TLS/blocked results).
- Rollover preview proposes MLSys 2028, ECIR 2028, NetSci-X 2028, ACM FAccT
  2028 and IEEE BHI 2027. Their prospective sites did not provide a verified
  new announcement. No drafts were written or published in this pass.
- ACML and RecSys's official statistics still support the stored 2025 figures.
  No trustworthy newer rate was established for the checked gaps, including
  LoG; acceptance and ranking maps are unchanged. This is not a review of all
  132 acceptance-backlog entries or the separate scope/archival backlog.

## Workbook Mirror

The bundled artifact tool is available again. The maintained synchronization
helper restored the mirror from canonical YAML, including the previously
missing ECC/related-venue/ASLI rows and ICML's new website. The saved file was
re-imported: 176 catalog rows, 43 vocabulary rows and 125 scope profiles match
the exporter, three sheets/native tables remain, and no formula errors were
found. All three sheets were rendered and inspected before and after the
update. Empty additional-topic strings re-import as blank/null cells, not zero.
No series, ranking, acceptance-rate or topic assignments changed in YAML.

Verification results belong in [current status](implementation_status.md).
Detailed working notes remain local, not part of the public handbook.

The post-review edition queue has 127 items; remaining estimates and source
gaps still need organizer announcements or another editorial pass. Separate
queues contain 132 acceptance, 143 scope and 37 archival review items.

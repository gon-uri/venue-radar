# Mid-Month Review: 2026-11-14

Reviewed: 2026-11-14. This is dated source evidence, not a replacement for the
[maintenance procedure](data_maintenance.md).

## Method

The 30-day report listed 141 of 260 editions: seven act-now, 14 pre-deadline
rechecks, ten soon, 87 later, 16 schedule-only and seven successor-missing.
Twelve more editions were flagged only by old-year-URL advisories. All 153 were
reviewed in batches of five: one agent read the official pages and proposed
changes; an independent agent re-opened every cited page and tried to refute
each proposal. Each confirmed deadline due within 21 days was re-read by both.
The verifiers accepted 108 proposals, corrected 19 and rejected one (an HTTP-only
archival source the validator would reject). They also added eight changes the
first pass missed.

`last_checked` advances only for the 133 editions whose own official pages were
read. Not advanced: 17 estimated future editions with no edition page yet (UAI,
COLM, NeurIPS-style proxies, 2028 projections and others), and four the agents
could not check. NODYCON and ICCN have no readable or resolving site. ICDL 2027
and IJCB 2027 are behind a Cloudflare bot check that was not bypassed.

## Changes

| Edition | Verified change | Official evidence |
| --- | --- | --- |
| ESANN 2027 | Paper deadline extended Nov 17 to Nov 25 (date only, Bruges time). | [Homepage news, 12.11.2026](https://www.esann.org/) |
| IEEE CEC 2027 | Session/workshop proposals extended to Nov 29; the revised CFP removes the Nov 15 vs Nov 29 conflict. | [Revised CFP PDF](https://confcats-siteplex.s3.amazonaws.com/ieeecec/files/cec27-cfp_web-16-(1).pdf) |
| ICML 2027 | The call is out: abstract (mandatory gate) Jan 14 and full paper Jan 22, 2027, 23:59 AoE, confirmed. The workshop date stays estimated. | [CFP](https://icml.cc/Conferences/2027/CallForPapers), [Dates](https://icml.cc/Conferences/2027/Dates) |
| CogSci 2027 | Papers due Feb 1, 2027 at midnight UTC-11, with AoE grace (cutoff note). Member abstracts are discontinued. | [Submissions](https://cognitivesciencesociety.org/submissions/) |
| CNS CogNeuro 2027 | Late-breaking posters Jan 19, 2027 AoE are now confirmed by the poster page, not extended. | [Submit a poster](https://www.cogneurosociety.org/submit-a-poster/) |
| ECAF 2027 | Papers, posters and interactive sessions all due Mar 25, 2027 AoE; notifications May 5. Four old-year sources were dropped. | [Call for papers](https://2027.ecafconference.org/callForPapers) |
| ICIP 2027 | 2027 call: regular and special-session papers Mar 31, plus a new OJ-SP journal route (`journal_paper`, 8+1 pages), satellite-workshop papers Aug 11, decisions Aug 6 and final papers Aug 11. | [CFP](https://2027.ieeeicip.org/call-for-papers/) |
| IEEE BioCAS 2027 | Host timeline adds regular papers on Jun 11, 2027. The SSCS-only May 7 abstract date conflicts with it and is now an estimate. | [Host site](https://2027.ieee-biocas.org/) |
| IEEE EMBC 2027 | All deadlines are 11:59 PM AoE, so the stored clocks are exact. Adds the Apr 16 paper notification. | [Papers](https://embc.embs.org/2027/papers/) |
| IEEE ICMLA 2027 | Meeting confirmed Dec 14-16, 2027, University of Miami (Coral Gables). Papers May 15, 11:59 PM PT, confirmed. | [Key dates](https://www.icmla-conference.org/icmla27/keydates.html) |
| ISWC 2027 | Meeting confirmed Oct 24-28, 2027 in Montevideo; deadlines remain one-year proxies. | [Save the date](https://iswc2027.semanticweb.org/) |
| ACM MM 2027 | Meeting confirmed Nov 8-12, 2027, AsiaWorld-Expo, Hong Kong; deadlines remain proxies. | [ACM MM 2027](https://2027.acmmm.org/) |
| RLC 2027 | Two confirmed sites: Providence Aug 2-6 and Nyborg (with EWRL) Aug 22-25. RLJ acceptance by May 1 is confirmed; the paper cutoff stays estimated (rolling RLJ submissions). | [RLC 2027](https://rl-conference.cc/2027/index.html) |
| IROS 2027 | IEEE RAS calendar gives Mar 1, 2027 for papers; kept estimated until the call is out. | [RAS event](https://www.ieee-ras.org/event/call-for-papers-paper-submission-deadline-iros-2027-ieee-rsj-international-conference-on-intelligent-robots-and-systems-iros-27403-0/) |
| AREADNE 2028 | Preliminary 2028 table: abstracts close Jan 28, notifications Feb 29. It copies 2026's "(delayed)" notes, so both stay estimated. Time zone set to Athens. | [Important dates](https://areadne.org/2028/important-dates.html) |
| ICDM 2027 | New official site, icdm2027.org; tentative AoE dates (Jun 6 papers, Aug 20 workshops) stay estimated. | [Dates](https://icdm2027.org/dates/) |
| ML4H 2026 | Camera-ready moved to Nov 13 (no longer tentative). | [CFP](https://ml4h.ahli.cc/submit/call-for-papers/) |
| Schedule details | Added notifications for IJCAI, COLT, ICRA and ECAI 2027. Added organizer proposals: EUSIPCO special sessions Dec 1 and tutorials Mar 1, AIME workshops and tutorials, and the RLDM workshop call (Jan 8, 23:59 UTC). Also the past ACC+L-CSS joint route (Sep 11) and an estimated ACC 2028 late-breaking poster. | Each record's source URL |
| Sources and notes | Neural Interfaces 2027 guidelines PDF (call opens Nov 16; Central-time note). NER 2027 call page. ICAPS, RSS, SfN, ACPR, AIME, EUSIPCO, ICMNS (biennial after Shanghai 2028), UAI, ADMA, 3DV, COMPLEX NETWORKS, ML4H and ICRA 2028 notes. | Each record |

Archival values now read from 2027 calls: ICML, IEEE EMBC, RLC, ICIP and IEEE
ICMLA, all still Yes. Two new city aliases: Montevideo and Miami.

## Owner Decisions (2026-11-14)

- **RLC 2027 abstract step: removed.** The 2027 page publishes no abstract
  step, and RLJ takes rolling submissions. The published event
  `rlc-2027-deadline-abstract@scientific-conference-calendar` is retired in
  `data/retired_identities.yml`, so subscribed calendars drop it.
- **CogSci: non-archival.** The 2027 call publishes papers in the Society's
  online proceedings but says the volume "is not considered archival" for later
  journal submission. The owner ruled that a call declaring its own proceedings
  non-archival settles No (ADR-047 refinement). The value is now No, read from
  the 2027 call.

## Retained Uncertainty

- KDD's February cycle has no dates, and MICCAI's paper page is still under
  construction. ENOC's January deadline has no day.
- WASPAA's whole schedule is tentative, and CHIL's meeting is marked tentative.
- NeurIPS, UAI and CIKM 2027 claims seen only on aggregators were not used.
- Recheck after Nov 15-17, when closing deadlines may be extended: BCI Winter,
  IFAC SYSID, CLeaR, EuroGP and WSDM.
- RLC 2027's two-city location has no single city alias. It is intentionally
  off the map, and the advisory will keep listing it.

## Workbook Mirror

Synchronized from canonical YAML with the maintained helper. A re-import
showed exactly five changed catalog rows: ICDM, ACM MM, ISWC, SfN and RLC
sources, plus RLC's submission type. Vocabulary and scope sheets are
unchanged, and previews were inspected.

After the review the edition queue holds 97 items (three act-now, four soon,
83 later, seven successor-missing). The separate backlogs hold 132 acceptance,
150 scope and 36 archival items.

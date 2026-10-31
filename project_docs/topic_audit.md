# Topic And New-Series Audit

Use [adding conferences](adding_conferences.md) for the complete addition
procedure and [conference scopes](conference_scopes.md) for extra-topic curation.
The current model below takes precedence over the explicitly historical audit.

## Current Eight-Family Model

Reviewed: 2026-10-31, after adding 44 owner-approved related venues (see the
[candidate backlog](conference_candidates.md#related-venue-search-2026-10-3031)).
These counts use explicit central series identities, not the presence of any
generic method tag. There are 175 series, 43 leaves and 124 reviewed
profiles; 51 profiles remain queued. No family or leaf was added or renamed.

| Family | Central series | Subtopics |
| --- | --- | --- |
| ML & Data Science | 52 | Machine learning; deep learning; theory; probabilistic/causal ML; distributed/federated learning; evolutionary optimization; ML systems; reasoning; data mining |
| NLP, Agents & Retrieval | 29 | NLP/LLMs; autonomous/multiagent systems; LLM agents/tool use; information retrieval/RAG; recommenders |
| Vision & Multimedia | 21 | Vision/pattern recognition; graphics/visualization; multimedia/retrieval |
| RL, Robotics & Control | 19 | Reinforcement learning; control/robotics; planning/search |
| Complex Systems, Time Series & Signals | 40 | Nonlinear dynamics; complex systems/networks; graphs/graph learning; system identification; time series; signals; artificial life/adaptive systems |
| Healthcare & Biometrics | 19 | Healthcare/clinical AI; biomedical imaging; biometrics/human sensing |
| Neuroscience & Neurotechnology | 27 | Computational neuroscience; EEG/MEG; BCI; neuroimaging; computational cognition; neuromorphic/brain-inspired computing; systems/experimental neuroscience |
| Responsible & Trustworthy AI | 9 | Fairness/accountability; explainability; ethics/governance; privacy; robustness/safety; human-AI interaction |

Counts overlap: a genuinely cross-field series may have one to three central
identities. Whole-family selection uses these curated identities; individual
subtopics match broader source-grounded main/additional tags. For example, MICCAI
is a healthcare venue, but is discoverable through its deep-learning subtopic;
L4DC is control/dynamics, not automatically general ML. LoG bridges ML and graphs.
Graphs belong in the complex-systems family but are distinct from nonlinear dynamics.
AAMAS's agent tag does not make it an LLM-only venue. Time series is available
inside the complex-systems family and still matches the curated leaf union,
including general ML and sequential recommendation. Its duplicate shortcut
was removed in the 2026-10-07 filter polish.
Selecting every child activates central-family matching, as selecting the parent does.

Four main tags remain visible. Curated profiles capture actual characteristic
scope, not enormous incidental CFP inventories. Stable leaf slugs remain intact.
The long complex-systems label is untruncated and one line, including at 320px.
README order follows central coverage broadly, while the filter keeps the agreed
family order. See nlp_robotics_expansion.md for the earlier 16 additions and
dynamics_neuroscience_expansion.md for the 16 complex-systems/neuroscience series of 2026-10-08, focused new leaves,
abstract-only formats, source caveats and monthly follow-up. No existing family
or leaf name is renamed by this batch.

## Earlier Audit Snapshot

The following records describe the earlier seven-family layout before this
restructuring. Their dated counts are historical, not the current filter model.

Reviewed 2026-10-06. Topic assignments describe central advertised scope, not
every paper that could conceivably be accepted. Up to four unique main leaves
are displayed. Parents are derived; a series may appear in multiple families.

2026-10-07 extension: 45 of 97 series now have curated detailed profiles in
`data/conference_scopes.yml`, with at most six characteristic additional leaves
and sourced prose. Filter/search/feed matching uses their union; display remains
main-only. The 52 missing profiles are queued, not guessed. See
[conference_scopes.md](conference_scopes.md). The historical counts below are
main-topic coverage, not expanded profile matching counts.

Historical main-topic coverage by distinct series, using each latest edition
(not mutually exclusive): ML & AI 86; Data & Time Series 35;
Signals, Vision & Multimedia 30; Responsible & Trustworthy AI 22;
Healthcare & Biomedical AI 14; Dynamics, Complex Systems & Control 14;
Neuroscience & Neurotechnology 13. README subject order follows these counts.

The second AI Deadlines batch adds five leaves: Knowledge Representation &
Reasoning and Planning & Search (ML & AI), plus Computer Graphics & Visualization,
Multimedia Learning & Retrieval, and Biometrics & Human Sensing (signals/vision).
FG/IJCB are directly filterable as dedicated biometrics venues; broad vision
venues match the additional leaf only when their sourced scope has a substantial
human/biometric-analysis strand. See vision_ai_expansion.md for evidence.

## Responsible And Trustworthy AI

- [FAccT CFP](https://facctconference.org/2026/cfp.html): fairness, accountability,
  societal impacts, governance, and interpretability support central tags.
- [AIES CFP](https://www.aies-conference.com/2026/call-for-papers/): ethics,
  social impacts, accountability, and deployment are central, not incidental.
- [ACML CFP](https://www.acml-conf.org/2026/calls/papers/): explicitly includes
  trustworthy ML, explainability, fairness, privacy, robustness, and safety.
- [ICLR CFP](https://iclr.cc/Conferences/2026/CallForPapers): broad representation
  learning and responsible/robust AI scope; keep only four central leaves.
- [KDD research CFP](https://kdd2027.kdd.org/research-track-call-for-papers/):
  federated/distributed learning is systems scope, not automatically ethics.

The stable Fairness & Responsible AI key now displays Fairness & accountability;
ethics/governance, privacy, and robustness have separate leaves. Existing tag
feed slugs remain unchanged. Federated/distributed ML belongs to ML & AI.
Broad ML, data, and vision venues were retagged to remove peripheral healthcare
or neural-signal labels and add central vision/distributed/robustness leaves.
Older and projected editions of a series were kept consistent where scope is
unchanged. Official websites/source_urls in canonical records are the entrypoint
for later scope review; labels must not be inferred solely from acronyms.

## Added Series And Timing Evidence

| Series | Official source | Editorial distinction |
| --- | --- | --- |
| L4DC | https://l4dc2027.control.ee.ethz.ch/home | 2027 Stockholm and regular papers announced; late-breaking eligibility not yet counted as an unrestricted route. |
| IFAC SYSID | https://conferences.ifac-control.org/sysid2027/participate/ | Regular/journal/discussion routes distinguished; triennial recurrence. |
| ACC | https://acc2027.a2c2.org/ | Extended Oct 2 regular-paper deadline has passed; tutorial invited papers and workshop proposals are not general opportunities. |
| IEEE CDC | https://cdc2027.ieeecss.org/authors/call-for-papers | 2026 and confirmed 2027 tracked; regular and L-CSS journal routes differ. |
| NOLTA | https://nolta2026.org/ | Final extended paper deadline, Grenoble meeting, annual series. |
| SIAM DS | https://www.siam.org/conferences-events/siam-conferences/ds27/submissions/ | Biennial; presentation abstracts/minisymposia are not archival full papers; exact Eastern cutoff sourced. |
| CCS | https://cssociety.org/ccs/ | 2026 main meeting excludes warm-up; 2027 published week retained with scope note; 2027 abstract deadline estimated from prior lead time. |
| NetSci | https://netsci2027.github.io/ | Dresden meeting confirmed; abstract date explicitly estimated from 2026. |

Full source URLs, review dates, uncertainty notes, route types, and opening
evidence are stored beside each record in conferences.yml. These new series have
no invented acceptance rates or inherited ranks. In particular, Complex Systems
CCS is not ACM CCS, and CDC's removed historical CORE entry is not an ICORE 2026
rank. CCS 2027's published week is not a fabricated main/satellite split.

## Existing Day-Only Deadlines

Rechecked [ECAI](https://ecai2027.org/),
[EUSIPCO](https://eusipco2027.de/), and
[EMBC](https://embc.embs.org/2027/important-dates/): their published deadline
days are confirmed, while cutoff hours remain unannounced. Applied date-only
precision instead of mislabeling the whole deadline as inferred. ITISE's
official source still labels its timeline provisional, so estimated confidence
is retained even though January 15 is currently listed. Hour precision and
provisional-date confidence are distinct.

# Public Introduction And Attribution

Reviewed: 2026-10-29. This records current copy, not rejected alternatives.

## Introduction

Find where to submit next: conference deadlines for machine learning and AI,
neuroscience, healthcare, complex systems, and control.

Selected by the owner on 2026-10-29 (ADR-041). It names the task and what the
site lists, keeping machine learning and AI first. This is the website
subtitle. README repeats it under its heading;
[the Share on X draft](sharing.md) remains independent. These describe the
project's focus rather than exhaustive coverage; the eight families retain
the detailed topic structure.

## Tab Name

Conferences & Map identifies the map/table combination. Its visible label
does not change tab/panel IDs, keyboard navigation, shared filters or map rules.

## Public Attribution

The website footer says Created and maintained by Gonzalo Uribarri, without
the university affiliation sentence. University profile, Scholar, GitHub and
license links remain. README retains the Assistant Professor affiliation as
plain text, without the redundant department hyperlink.

The final README licensing paragraph ends with:

Venue Radar is a personal project by Gonzalo Uribarri, not an official
Stockholm University service.

This clarification describes project identity, not a claim about legal
obligations or university policy. Do not claim institutional endorsement or
involvement without the author's confirmation. Public copy changes require
their own approved scope and affected regression checks.

## README

Approved with ADR-041. README opens with the banner (its transparent dark
variant in GitHub's dark themes; not itself a link) and the "Open Venue Radar"
heading, which links to the site, then, centred: the subtitle above; Calendar feeds (linking to
the Subscribe once section), Request a conference and Build status badges; the
line "130+ conference series · Free · No account · Works on your phone"; and
the linked hero screenshot. Sections follow in this order: Deadlines at a
glance, Coverage (the eight family labels and the map), Subscribe once (the
three aggregate feed URLs), Checked by hand (with three collapsed answers on
estimates, acceptance rates and additions), Help keep it accurate, then the
attribution and licensing paragraphs described above.

Family labels, status wording, feed names and menu steps match the site; change
README with them. State catalog size only as "N+ conference series" (a test
keeps N at or below the series count). Do not quote dated examples, such as a
"Checked" date, or snapshot details in image alt text. README stays
nontechnical; maintainers get one link to the documentation index.

## Calendar Menu And Empty States

Approved with ADR-039 (implementation proposal; adjust wording here first):

- Button: Subscribe to calendar. Caption: Auto-updating .ics feeds.
- Intro: Subscribed feeds update automatically when Venue Radar changes.
- Rows: Submission deadlines (New-paper and abstract deadlines, including
  required registration steps); All events (Meeting dates plus every recorded
  milestone); Conference dates (Meeting dates only); One topic (All events for
  a subtopic); One conference series (Every edition, including future ones).
- Actions: Google, Apple, Copy link, Download. Note: Outlook: Add calendar ->
  Subscribe from web, then paste a copied link. Google can take up to a day to
  refresh. Single-edition files are in the Conferences & Map table.
- Cutoffs: "October 30, 2026 · 20:00 UTC", then "Your time: ...".
- Closed rows: "Next: <successor short title> · ~<Mon YYYY> (est.)".
- Empty deadlines view: "No open or upcoming submission options match these
  filters. N matching conferences are closed or have no announced deadline."
  with Show them, Clear filters and Request a conference; otherwise "No
  conferences match these filters." Toolbar link: "Show N closed or unannounced".
- Filter badge: "N active". No-JS note: "Live submission status, countdowns and
  filters need JavaScript. Every conference, date and milestone is still listed below."

## Page Title, Status Guide And Evidence Line

Approved with ADR-040:

- Title: "Venue Radar: ML, AI & Neuroscience Conference Deadlines". Description:
  "Conference deadlines for machine learning, AI, neuroscience, healthcare,
  complex systems and control, with live countdowns, rankings, acceptance rates
  and auto-updating calendars." The same text feeds the Open Graph and X tags.
- Status guide (collapsed above the deadlines table): "What do the statuses
  mean?" It defines each status pill, "~3 weeks · (est.)" ("Estimated countdown
  or date."; estimates use one coarse unit since ADR-044), "(time est.)" ("Official
  day; the cutoff hour is not announced.") and "*" ("Official sources disagree
  on the cutoff; the earliest stated time is shown, with the note below it.").
- Evidence line: "Call for papers" or "Previous call", "Dates source" or
  "Previous dates" (a link to an older year's page says Previous), "Checked
  <Mon D, YYYY>", Hybrid/Online, "Dates estimated", "Copy link", "Report
  outdated info".
- Starring: "Starred only (N)" filter; calendar menu row "Your starred series"
  ("Pick one to subscribe to all its editions").

# Public Introduction And Attribution

Reviewed: 2026-10-29. This records current copy, not rejected alternatives.

## Introduction

Find your next conference in machine learning and AI, or explore related
opportunities in neuroscience, healthcare, complex systems, and control.

This is the website subtitle only. README's fuller description remains
independent, as does [the Share on X draft](sharing.md). These describe the
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

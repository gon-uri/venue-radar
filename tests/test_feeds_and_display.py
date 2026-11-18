from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from datetime import date

from build_ics import (FEED_SIZE_LIMIT, SITE_URL, _escape_text, _topic_groups, build_calendars, edition_last_day,
                       feed_reference_date, is_past_edition, series_groups, series_slug)
from build_site import _clock_label, _deadline_grid_rows, _milestone_label, _milestones, _previous_dates, _successors
from validate import SUBMISSION_TYPES, load_conferences, stable_slug


def _read(path: Path) -> str:
    # Keep the CRLF line endings that ICS requires (text mode would rewrite them).
    return path.read_bytes().decode("utf-8")


def _uids(text: str) -> set[str]:
    # ICS lines are folded at 75 octets; unfold before reading UIDs.
    unfolded = text.replace("\r\n ", "")
    return set(re.findall(r"^UID:(.+?)\r?$", unfolded, flags=re.M))


def _events(text: str) -> dict[str, dict[str, str]]:
    """Unfolded events keyed by UID local part, each as {property: value}."""
    events = {}
    for block in text.replace("\r\n ", "").split("BEGIN:VEVENT\r\n")[1:]:
        fields: dict[str, str] = {}
        for line in block.split("\r\n"):
            name, _, value = line.partition(":")
            fields.setdefault(name.split(";")[0], value)
        events[fields["UID"].split("@")[0]] = fields
    return events


class ClockDisplayTests(unittest.TestCase):
    def test_clock_uses_only_the_recorded_offset(self) -> None:
        self.assertEqual(_clock_label("2026-11-01T23:59:00-12:00"), "23:59 AoE")
        self.assertEqual(_clock_label("2026-10-30T20:00:00Z"), "20:00 UTC")
        self.assertEqual(_clock_label("2026-10-30T20:00:00+00:00"), "20:00 UTC")
        self.assertEqual(_clock_label("2026-12-14T23:59:00-05:00"), "23:59 UTC-5")
        self.assertEqual(_clock_label("2027-01-10T17:00:00+05:30"), "17:00 UTC+5:30")

    def test_only_confirmed_exact_cutoffs_show_a_clock(self) -> None:
        base = {"type": "full_paper", "label": "Paper", "datetime": "2026-11-02T23:59:00-12:00", "show_time": True}
        confirmed = _deadline_grid_rows([dict(base, estimated=False, approximate_time=False)])
        self.assertIn('<span class="deadline-clock" data-offset="-720">23:59 AoE</span>', confirmed)
        self.assertIn("data-local-time", confirmed)
        for variant in (dict(base, estimated=True, approximate_time=False),
                        dict(base, estimated=False, approximate_time=True)):
            html = _deadline_grid_rows([variant])
            self.assertNotIn("deadline-clock", html)
            self.assertNotIn("data-local-time", html)

    def test_meeting_start_and_openings_follow_their_own_precision(self) -> None:
        sample = {
            "conference_start": "2027-01-20", "confidence": "confirmed",
            "deadlines": [{
                "type": "full_paper", "label": "Paper deadline", "time_precision": "date",
                "datetime": "2026-12-01T23:59:00-12:00", "opens_at": "2026-11-10T09:00:00Z",
            }],
        }
        rows = {item["type"]: item for item in _milestones(sample)}
        self.assertFalse(rows["full_paper_opens"]["approximate_time"], "a recorded opening is exact")
        self.assertTrue(rows["full_paper"]["approximate_time"])
        self.assertFalse(rows["conference_start"]["show_time"])
        html = _deadline_grid_rows(list(rows.values()))
        self.assertEqual(html.count("deadline-clock"), 1)
        self.assertIn("09:00 UTC", html)

    def test_successors_follow_series_and_year(self) -> None:
        successors = _successors(load_conferences())
        self.assertEqual(successors["neurips-2026"]["id"], "neurips-2027")
        self.assertEqual(successors["lod-2026"]["id"], "ais-2027")
        self.assertEqual(successors["ts4h-2025"]["id"], "sd4h-2026", "SD4H continues TS4H (owner decision)")


class ProvenanceTests(unittest.TestCase):
    """ADR-055: an estimated milestone names the last confirmed date it rests on."""

    def edition(self, year, confidence, deadlines, **extra):
        return {"id": f"s-{year}", "series": "S", "year": year, "confidence": confidence,
                "conference_start": f"{year}-06-01", "conference_end": f"{year}-06-03", "timezone": "UTC", "website": f"https://s{year}.org",
                "deadlines": deadlines, **extra}

    def test_nearest_confirmed_same_type_milestone_with_its_source(self):
        older = self.edition(2025, "confirmed", [{"type": "full_paper", "label": "Paper", "datetime": "2025-01-28T23:59:00-12:00",
                                                  "source_url": "https://s2025.org/dates"}])
        gap = self.edition(2026, "confirmed", [{"type": "abstract", "label": "Abstract", "datetime": "2026-01-20T23:59:00-12:00"}])
        target = self.edition(2027, "estimated", [{"type": "full_paper", "label": "Paper", "datetime": "2027-01-28T23:59:00-12:00"},
                                                  {"type": "notification", "label": "Decision", "datetime": "2027-04-01T23:59:00-12:00"}])
        previous = _previous_dates([older, gap, target])
        self.assertEqual(previous[("s-2027", "full_paper")], {"date": "January 28, 2025", "url": "https://s2025.org/dates"})
        self.assertNotIn(("s-2027", "notification"), previous, "no earlier edition stored one")
        self.assertEqual(previous[("s-2027", "conference_start")]["url"], "https://s2026.org")
        self.assertFalse([key for key in previous if key[0] != "s-2027"], "confirmed milestones carry no provenance")
        milestone = next(m for m in _milestones(target, previous) if m["type"] == "full_paper")
        html = _deadline_grid_rows([milestone])
        self.assertIn('<span class="deadline-basis">Last edition: <a href="https://s2025.org/dates">January 28, 2025</a></span>', html)

    def test_estimated_rows_drop_a_leading_estimated_word(self):
        self.assertEqual(_milestone_label("Estimated paper author notification", True), "Paper author notification")
        self.assertEqual(_milestone_label("Estimated paper author notification", False), "Estimated paper author notification")
        self.assertEqual(_milestone_label("Paper submission deadline", True), "Paper submission")


class FeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.directory = TemporaryDirectory()
        cls.docs = Path(cls.directory.name)
        build_calendars(docs_dir=cls.docs)
        cls.conferences = load_conferences()
        cls.reference = feed_reference_date()
        cls.current = [c for c in cls.conferences if not is_past_edition(c, cls.reference)]
        # Every event, past editions included, read from the per-edition feeds.
        cls.edition_text = "".join(_read(path) for path in sorted((cls.docs / "conferences").glob("*.ics")))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.directory.cleanup()

    def test_submissions_feed_contains_only_submission_steps_with_stable_uids(self) -> None:
        submissions = _uids(_read(self.docs / "submissions.ics"))
        everything = _uids(_read(self.docs / "calendar-all.ics"))
        expected = {
            f"{conference['id']}-deadline-{stable_slug(deadline['type'])}@scientific-conference-calendar"
            for conference in self.current for deadline in conference["deadlines"]
            if deadline["type"] in SUBMISSION_TYPES or deadline.get("gate_for")
        }
        self.assertEqual(submissions, expected)
        self.assertTrue(submissions <= everything)
        self.assertFalse(any(uid.split("@")[0].endswith("-conference") for uid in submissions))

    def test_series_feeds_roll_forward_with_identical_uids(self) -> None:
        groups = series_groups(self.conferences)
        files = sorted(path.stem for path in (self.docs / "series").glob("*.ics"))
        self.assertEqual(files, sorted(groups))
        self.assertEqual(len(files), len({c["series"] for c in self.conferences}))
        neurips = _uids(_read(self.docs / "series" / f"{series_slug('NeurIPS')}.ics"))
        self.assertIn("neurips-2026-conference@scientific-conference-calendar", neurips)
        self.assertIn("neurips-2027-conference@scientific-conference-calendar", neurips)
        self.assertTrue(neurips <= _uids(self.edition_text))
        # Series feeds keep past editions; the combined feeds do not (ADR-053).
        ts4h = _uids(_read(self.docs / "series" / f"{series_slug('TS4H')}.ics"))
        self.assertIn("ts4h-2025-conference@scientific-conference-calendar", ts4h)

    def test_combined_feeds_leave_out_past_editions_but_keep_their_identities(self) -> None:
        past = {c["id"] for c in self.conferences} - {c["id"] for c in self.current}
        self.assertIn("ts4h-2025", past)
        self.assertNotIn("neurips-2026", past, "a December 2026 meeting is not past on the review date")
        edition_uids = _uids(self.edition_text)
        for name in ("calendar-all.ics", "deadlines.ics", "conferences.ics", "submissions.ics"):
            uids = _uids(_read(self.docs / name))
            self.assertFalse({u for u in uids if u.split("@")[0].rsplit("-conference", 1)[0] in past
                              or any(u.startswith(f"{p}-deadline-") for p in past)}, name)
            self.assertTrue(uids <= edition_uids, name)
        for path in (self.docs / "tags").glob("*.ics"):
            self.assertFalse(any(u.startswith(f"{p}-") for u in _uids(_read(path)) for p in past), path.name)
        # Every published identity still lives in its edition's own feed.
        expected = {f"{c['id']}-conference@scientific-conference-calendar" for c in self.conferences}
        self.assertTrue(expected <= edition_uids)
        self.assertEqual(sorted(p.stem for p in (self.docs / "conferences").glob("*.ics")),
                         sorted(c["id"] for c in self.conferences))
        # Topic feed URLs never disappear, even when every edition of a topic is past.
        self.assertEqual(sorted(p.stem for p in (self.docs / "tags").glob("*.ics")),
                         sorted(_topic_groups(self.conferences)))

    def test_past_means_every_day_of_the_edition_is_before_the_review_date(self) -> None:
        edition = {"conference_start": "2026-11-10", "conference_end": "2026-11-13",
                   "deadlines": [{"datetime": "2026-11-20T23:59:00-12:00"}]}
        self.assertEqual(edition_last_day(edition), date(2026, 11, 20))
        self.assertFalse(is_past_edition(edition, date(2026, 11, 20)))
        self.assertTrue(is_past_edition(edition, date(2026, 11, 21)))
        self.assertTrue(is_past_edition({"conference_start": "2026-11-01", "deadlines": []}, date(2026, 11, 2)))
        # The cutoff is the reviewed dataset date, so a build never depends on the build day.
        self.assertEqual(self.reference, date.fromisoformat(
            re.search(r'last_updated:\s*"?([0-9-]+)', (Path(__file__).resolve().parents[1] / "data" / "metadata.yml").read_text()).group(1)))

    def test_every_feed_asks_clients_to_refresh_daily(self) -> None:
        for path in self.docs.rglob("*.ics"):
            text = _read(path)
            self.assertIn("\r\nREFRESH-INTERVAL;VALUE=DURATION:P1D\r\n", text, path.name)
            self.assertIn("\r\nX-PUBLISHED-TTL:P1D\r\n", text, path.name)

    def test_every_feed_stays_below_the_url_feed_size_guard(self) -> None:
        # Google Calendar is reported to reject URL feeds above about 1 MB (ADR-044).
        for path in self.docs.rglob("*.ics"):
            self.assertLess(path.stat().st_size, FEED_SIZE_LIMIT, path.name)

    def test_titles_lead_with_the_edition_and_a_single_estimate_marker(self) -> None:
        events = _events(self.edition_text)
        self.assertEqual(events["ecc-2027-deadline-full-paper"]["SUMMARY"],
                         "ECC 2027 · Extended contributed paper submission deadline")
        self.assertEqual(events["conll-2027-deadline-full-paper"]["SUMMARY"],
                         "CoNLL 2027 (est.) · Direct paper submission deadline")
        self.assertEqual(events["neurips-2027-conference"]["SUMMARY"], "NeurIPS 2027 (est.) · Conference")
        # A known meeting whose call is unannounced is not an estimated meeting.
        self.assertEqual(events["conll-2026-conference"]["SUMMARY"], "CoNLL 2026 · Conference")
        for conference in self.conferences:
            meeting = events[f"{conference['id']}-conference"]["SUMMARY"]
            self.assertEqual("(est.)" in meeting, conference["confidence"] in {"estimated", "not_yet_announced", "stale"})
            for deadline in conference["deadlines"]:
                summary = events[f"{conference['id']}-deadline-{stable_slug(deadline['type'])}"]["SUMMARY"]
                self.assertTrue(summary.startswith(f"{conference['short_title']} "), summary)
                estimated = deadline.get("confidence", conference["confidence"]) != "confirmed"
                self.assertEqual("(est.)" in summary, estimated, summary)
                self.assertNotIn("stimated", summary, "one marker, never 'Estimated ... (estimated)'")
                self.assertNotIn("unannounced", summary)

    def test_descriptions_keep_status_format_a_row_link_and_meeting_notes(self) -> None:
        events = _events(_read(self.docs / "calendar-all.ics"))
        deadlines = {
            f"{conference['id']}-deadline-{stable_slug(deadline['type'])}": (conference, deadline)
            for conference in self.conferences for deadline in conference["deadlines"]
        }
        by_id = {conference["id"]: conference for conference in self.conferences}
        for key, event in events.items():
            conference, deadline = deadlines.get(key) or (by_id[key.removesuffix("-conference")], None)
            description = event["DESCRIPTION"]
            self.assertTrue(description.startswith(_escape_text(conference["title"]) + "\\n"), key)
            estimated = (deadline.get("confidence", conference["confidence"]) != "confirmed" if deadline
                         else conference["confidence"] in {"estimated", "not_yet_announced", "stale"})
            status = "estimated" if estimated else "confirmed"
            self.assertIn(_escape_text(f"Status: {status}, checked {conference['last_checked']}"), description, key)
            if deadline:
                self.assertIn(_escape_text(f"Meeting: {conference['conference_start']} to {conference['conference_end']}"), description)
                if conference.get("submission_type"):
                    # Non-archival routes are often flagged only here (LoG, SAB).
                    self.assertIn(_escape_text(f"Format: {conference['submission_type']}"), description)
                if deadline.get("time_precision") == "date":
                    self.assertEqual("official deadline day" in description, not estimated, key)
            self.assertIn(_escape_text(f"Venue Radar: {SITE_URL}#{conference['id']}"), description)
            if deadline:
                # ADR-045: Notes appear once per edition, on its meeting event.
                self.assertNotIn("\\nNotes:", description, key)
            elif conference.get("notes"):
                self.assertIn(_escape_text(f"Notes: {conference['notes']}"), description)
            for dropped in ("Scope:", "Scope sources", "Additional topics:", "Topics:", "Conference title:", "Size:"):
                self.assertNotRegex(description, rf"(^|\\n){re.escape(dropped)}", "dropped by ADR-044")
            self.assertEqual(event["CATEGORIES"], ",".join(_escape_text(topic) for topic in conference["topics"]))

    def test_prior_edition_pages_are_not_called_official_sources(self) -> None:
        events = _events(_read(self.docs / "calendar-all.ics"))
        description = events["acm-mm-2027-deadline-full-paper"]["DESCRIPTION"]
        self.assertIn("Previous edition's page: https://2026.acmmm.org/", description)
        self.assertNotIn("Official source: https://2026.", description)
        self.assertIn("Official source: https://ecc27.euca-ecc.org/", events["ecc-2027-deadline-full-paper"]["DESCRIPTION"])

    def test_series_feed_keys_cannot_collide(self) -> None:
        with self.assertRaises(ValueError):
            series_groups([{"series": "S+SSPR"}, {"series": "S SSPR"}])


if __name__ == "__main__":
    unittest.main()

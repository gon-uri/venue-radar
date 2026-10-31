from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_ics import FEED_SIZE_LIMIT, SITE_URL, _escape_text, build_calendars, series_groups, series_slug
from build_site import _clock_label, _deadline_grid_rows, _milestones, _successors
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


class FeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.directory = TemporaryDirectory()
        cls.docs = Path(cls.directory.name)
        build_calendars(docs_dir=cls.docs)
        cls.conferences = load_conferences()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.directory.cleanup()

    def test_submissions_feed_contains_only_submission_steps_with_stable_uids(self) -> None:
        submissions = _uids(_read(self.docs / "submissions.ics"))
        everything = _uids(_read(self.docs / "calendar-all.ics"))
        expected = {
            f"{conference['id']}-deadline-{stable_slug(deadline['type'])}@scientific-conference-calendar"
            for conference in self.conferences for deadline in conference["deadlines"]
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
        everything = _uids(_read(self.docs / "calendar-all.ics"))
        self.assertTrue(neurips <= everything)

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
        events = _events(_read(self.docs / "calendar-all.ics"))
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

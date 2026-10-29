from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_ics import build_calendars, series_groups, series_slug
from build_site import _clock_label, _deadline_grid_rows, _milestones, _successors
from validate import SUBMISSION_TYPES, load_conferences, stable_slug


def _read(path: Path) -> str:
    # Keep the CRLF line endings that ICS requires (text mode would rewrite them).
    return path.read_bytes().decode("utf-8")


def _uids(text: str) -> set[str]:
    # ICS lines are folded at 75 octets; unfold before reading UIDs.
    unfolded = text.replace("\r\n ", "")
    return set(re.findall(r"^UID:(.+?)\r?$", unfolded, flags=re.M))


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
        self.assertNotIn("ts4h-2025", successors)


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

    def test_series_feed_keys_cannot_collide(self) -> None:
        with self.assertRaises(ValueError):
            series_groups([{"series": "S+SSPR"}, {"series": "S SSPR"}])


if __name__ == "__main__":
    unittest.main()

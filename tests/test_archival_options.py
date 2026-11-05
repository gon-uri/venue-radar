from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from archival_options import (
    archival_label, archival_value, feed_label, load_archival_options, validate_archival_options, with_archival,
)
from build_ics import _description
from maintenance_report import archival_backlog
from validate import SUBMISSION_TYPES, load_conferences

CONFERENCES = [
    {"series": "ALPHA", "year": 2026},
    {"series": "ALPHA", "year": 2027},
]
GOOD = {
    "archival": "yes", "estimated": False, "track": "Main track",
    "source_url": "https://alpha.example.org/cfp", "source_year": 2026, "checked": "2026-11-05",
}
TODAY = date(2026, 11, 5)


class ArchivalOptionTests(unittest.TestCase):
    def errors(self, **changes):
        entry = {**GOOD, **changes}
        return validate_archival_options(CONFERENCES, {"ALPHA": entry}, TODAY)

    def test_valid_entry_passes(self) -> None:
        self.assertEqual(self.errors(), [])
        self.assertEqual(self.errors(note="Opt-in archival track.", venue="IEEE Xplore"), [])

    def test_validation_rejects_bad_fields(self) -> None:
        cases = {
            "archival must be yes or no": {"archival": "maybe"},
            "estimated must be boolean": {"estimated": "no"},
            "track must be non-empty": {"track": " "},
            "source_url must be HTTPS": {"source_url": "http://alpha.example.org"},
            "after the latest tracked edition": {"source_year": 2028},
            "checked must not be in the future": {"checked": "2026-11-06"},
            "unknown fields": {"publisher": "IEEE"},
        }
        for message, change in cases.items():
            self.assertTrue(any(message in e for e in self.errors(**change)), (message, change))
        self.assertIn("Archival BETA: unknown series",
                      validate_archival_options(CONFERENCES, {"BETA": GOOD}, TODAY))

    def test_estimate_follows_the_row_not_the_clock(self) -> None:
        # A value read from the 2026 call is confirmed for 2026 and an estimate for 2027.
        self.assertEqual(archival_value(GOOD, 2026), {"archival": True, "estimated": False})
        self.assertEqual(archival_value(GOOD, 2027), {"archival": True, "estimated": True})
        self.assertEqual(archival_value({**GOOD, "estimated": True}, 2026)["estimated"], True)
        self.assertIsNone(archival_value(None, 2027), "absent means not checked yet, never No")

    def test_labels(self) -> None:
        self.assertEqual(archival_label({"archival": True, "estimated": False}), "Archival option")
        self.assertEqual(archival_label({"archival": True, "estimated": True}), "Archival option (est.)")
        self.assertEqual(archival_label({"archival": False, "estimated": True}), "Non-archival (est.)")
        self.assertEqual(feed_label({"archival": False, "estimated": False}), "No")
        self.assertEqual(feed_label({"archival": True, "estimated": True}), "Yes (est.)")
        self.assertIsNone(archival_label(None))

    def test_review_backlog_order(self) -> None:
        def edition(series, year, confidence, routes=("full_paper",)):
            return {"id": f"{series.lower()}-{year}", "series": series, "year": year, "confidence": confidence,
                    "website": f"https://{series.lower()}.example.org", "relevance": "high",
                    "deadlines": [{"type": route} for route in routes]}
        conferences = [edition("NEW", 2027, "confirmed"), edition("OLD", 2026, "confirmed"),
                       edition("OLD", 2027, "confirmed"), edition("EST", 2027, "estimated"),
                       edition("FINE", 2027, "confirmed"), edition("TALKS", 2027, "confirmed", ("talk_proposal",))]
        options = {"OLD": GOOD, "EST": {**GOOD, "estimated": True}, "FINE": {**GOOD, "source_year": 2027}}
        rows = archival_backlog(conferences, options)
        self.assertEqual([row.name for row in rows], ["NEW", "OLD", "EST"])
        self.assertIn("old-2027 has confirmed dates", rows[1].detail)


class ArchivalDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.conferences = load_conferences()
        cls.options = load_archival_options()

    def test_data_validates_and_covers_every_series_with_a_fresh_deadline(self) -> None:
        self.assertEqual(validate_archival_options(self.conferences, self.options), [])
        # The filter ships only when every series with a new-paper route has a value (ADR-047).
        with_routes = {c["series"] for c in self.conferences
                       for d in c.get("deadlines", []) if d["type"] in SUBMISSION_TYPES}
        unchecked = with_routes - set(self.options)
        self.assertLessEqual(unchecked, {"Dynamics Days CAC", "ICCN"}, sorted(unchecked))

    def test_papers_only_rule_for_abstract_volumes(self) -> None:
        # Owner decision 2026-11-05: citable abstract volumes (DOI, ISBN,
        # journal supplement) do not make a meeting archival.
        for name in ("CNS CogNeuro", "OHBM", "International BCI Meeting", "CNS*",
                     "Bernstein Conference", "COSYNE", "AREADNE", "SfN Neuroscience"):
            self.assertEqual(self.options[name]["archival"], "no", name)
        # Opt-in archival tracks count as Yes.
        for name in ("ACM FAccT", "EAAMO", "ECAF", "CLeaR", "COLT"):
            self.assertEqual(self.options[name]["archival"], "yes", name)
        self.assertTrue(self.options["BIOMAG"]["estimated"], "BIOMAG's No rests on silence")

    def test_feed_format_line_carries_the_value(self) -> None:
        conference = next(c for c in with_archival(self.conferences, self.options) if c["id"] == "neurips-2027")
        text = _description(conference, conference["website"], False, meeting=True)
        self.assertIn("; Archival option: Yes (est.)", text)


if __name__ == "__main__":
    unittest.main()

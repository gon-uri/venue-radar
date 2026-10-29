from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from catalog_metadata import CITIES_PATH, CONFERENCE_FAMILIES_PATH, load_mapping, map_events
from conference_scopes import load_scopes
from rollover_editions import CADENCE_YEARS
from validate import load_conferences, load_icore_rankings


class AIiHAdditionTests(unittest.TestCase):
    """User-requested addition reviewed on 2026-10-29 from https://aiih.cc/."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.record = next(c for c in load_conferences() if c["id"] == "aiih-2027")

    def test_identity_and_meeting(self) -> None:
        self.assertEqual(self.record["series"], "AIiH")
        self.assertEqual((self.record["conference_start"], self.record["conference_end"]), ("2027-09-01", "2027-09-03"))
        self.assertEqual(self.record["confidence"], "confirmed")
        self.assertEqual(load_mapping(CONFERENCE_FAMILIES_PATH)["AIiH"], ["healthcare"])
        self.assertEqual(CADENCE_YEARS["AIiH"], 1)
        mapped = {e["id"]: e["city"] for e in map_events([self.record], load_mapping(CITIES_PATH))}
        self.assertEqual(mapped, {"aiih-2027": "oxford"})

    def test_routes_are_independent_and_keep_the_stated_offset(self) -> None:
        deadlines = {d["type"]: d for d in self.record["deadlines"]}
        self.assertEqual(deadlines["full_paper"]["datetime"], "2027-04-09T23:59:00-08:00")
        self.assertEqual(deadlines["abstract"]["datetime"], "2027-04-09T23:59:00-08:00")
        self.assertTrue(all("gate_for" not in d for d in self.record["deadlines"]),
                        "The April abstract is an independent route, not a gate")
        self.assertEqual(deadlines["late_abstract"]["datetime"][:10], "2027-07-02")
        self.assertIn("GMT-7", self.record["notes"], "The PT/GMT-8 discrepancy is documented")
        self.assertNotIn("AIiH", load_icore_rankings()["rankings"], "No unverified rank")

    def test_scope_profile_is_curated(self) -> None:
        scope = load_scopes()["AIiH"]
        self.assertLessEqual(len(scope["additional_topics"]), 6)
        self.assertEqual(scope["source_year"], 2027)


if __name__ == "__main__":
    unittest.main()

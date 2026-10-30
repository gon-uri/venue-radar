from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from catalog_metadata import CITIES_PATH, CONFERENCE_FAMILIES_PATH, load_mapping, map_events
from rollover_editions import CADENCE_YEARS
from validate import SUBMISSION_TYPES, load_ccf_rankings, load_conferences, load_icore_rankings


class ECCAdditionTests(unittest.TestCase):
    """Owner-approved addition reviewed on 2026-10-30 from https://ecc27.euca-ecc.org/."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.record = next(c for c in load_conferences() if c["id"] == "ecc-2027")

    def test_identity_meeting_and_companion_files(self) -> None:
        self.assertEqual((self.record["series"], self.record["confidence"]), ("ECC", "confirmed"))
        # The official window includes the July 13 pre-conference workshop day.
        self.assertEqual((self.record["conference_start"], self.record["conference_end"]), ("2027-07-13", "2027-07-16"))
        self.assertEqual(load_mapping(CONFERENCE_FAMILIES_PATH)["ECC"], ["rl-control"])
        self.assertEqual(CADENCE_YEARS["ECC"], 1)
        mapped = {e["id"]: e["city"] for e in map_events([self.record], load_mapping(CITIES_PATH))}
        self.assertEqual(mapped, {"ecc-2027": "brussels"})

    def test_only_the_extended_contributed_paper_route_is_actionable(self) -> None:
        deadlines = {d["type"]: d for d in self.record["deadlines"]}
        # The CFP strikes October 31 and gives November 9; no hour is published.
        paper = deadlines["full_paper"]
        self.assertEqual((paper["datetime"], paper["time_precision"]), ("2026-11-09T23:59:00-12:00", "date"))
        routes = [d["type"] for d in self.record["deadlines"] if d["type"] in SUBMISSION_TYPES]
        self.assertEqual(routes, ["full_paper"], "Invited sessions, proposals and industry abstracts are schedule-only")
        self.assertTrue(all("gate_for" not in d for d in self.record["deadlines"]))
        self.assertNotIn("ECC", load_icore_rankings()["rankings"], "Not listed in ICORE2026")
        self.assertNotIn("ECC", load_ccf_rankings()["rankings"], "Not listed in CCF")


if __name__ == "__main__":
    unittest.main()

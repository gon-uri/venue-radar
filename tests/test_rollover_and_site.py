from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_site import _acceptance_cell, _deadline_grid_rows, _milestones
from rollover_editions import rollover_candidates
from validate import load_acceptance_rates, load_conferences


class RolloverAndSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.conferences = load_conferences()

    def test_rollover_is_idempotent_for_tracked_next_editions(self) -> None:
        as_of = date(2026, 10, 6)
        drafts = rollover_candidates(self.conferences, as_of)
        tracked = {item["id"] for item in self.conferences}
        self.assertFalse({item["id"] for item in drafts} & tracked)
        self.assertEqual(rollover_candidates(self.conferences + drafts, as_of), [])

    def test_respects_biennial_and_omits_irregular_workshops(self) -> None:
        biennial = {"BIOMAG", "ICPR", "S+SSPR"}
        without_future = [
            item for item in self.conferences
            if item["id"] not in {"biomag-2028", "icpr-2028", "s-sspr-2028"}
        ]
        candidates = [
            item for item in rollover_candidates(without_future, date(2026, 10, 6))
            if item["series"] in biennial
        ]
        self.assertEqual({item["year"] for item in candidates}, {2028})
        self.assertEqual({item["series"] for item in candidates}, biennial)
        everything = rollover_candidates(self.conferences, date(2026, 10, 6))
        self.assertTrue(all(item["confidence"] == "estimated" for item in everything))
        irregular = {"TS4H", "FMTS @ NeurIPS", "IJCAI-ECAI", "NODYCON", "ICCN", "LOD",
                     "Dynamics Days Asia-Pacific", "Dynamics Days CAC", "IJCNLP"}
        self.assertFalse({item["series"] for item in everything} & irregular)

    def test_closed_submission_routes_trigger_successor_before_the_meeting(self) -> None:
        edition = {
            "id": "neurips-2026", "series": "NeurIPS", "year": 2026,
            "short_title": "NeurIPS 2026", "conference_start": "2026-12-06",
            "conference_end": "2026-12-12", "confidence": "confirmed",
            "last_checked": "2026-08-20", "location": "Sydney, Australia",
            "deadlines": [
                {"type": "abstract", "datetime": "2026-05-04T23:59:00-12:00",
                 "gate_for": "full_paper", "opens_at": "2026-04-01T00:00:00Z"},
                {"type": "full_paper", "datetime": "2026-05-06T23:59:00-12:00",
                 "open_observed_on": "2026-04-20", "cutoff_note": "CFP and site disagree."},
            ],
        }
        drafts = rollover_candidates([edition], date(2026, 10, 29))
        self.assertEqual([item["id"] for item in drafts], ["neurips-2027"])
        draft = drafts[0]
        self.assertEqual(draft["conference_start"], "2027-12-06")
        self.assertEqual(draft["last_checked"], "2026-08-20", "drafts are never stamped as reviewed")
        self.assertEqual(draft["location"], "To be announced")
        for deadline in draft["deadlines"]:
            self.assertEqual(deadline["confidence"], "estimated")
            self.assertNotIn("opens_at", deadline)
            self.assertNotIn("open_observed_on", deadline)
            self.assertNotIn("cutoff_note", deadline, "last year's source conflict is not carried over")
        still_open = dict(edition, deadlines=[dict(edition["deadlines"][1], datetime="2026-11-30T23:59:00-12:00")])
        self.assertEqual(rollover_candidates([still_open], date(2026, 10, 29)), [])
        no_routes = dict(edition, deadlines=[{"type": "camera_ready", "datetime": "2026-06-01T00:00:00Z"}])
        self.assertEqual(rollover_candidates([no_routes], date(2026, 10, 29)), [])
        self.assertEqual(rollover_candidates([edition], date(2026, 10, 29), {"ICML"}), [])

    def test_milestones_include_opening_and_conference_start(self) -> None:
        sample = {
            "conference_start": "2027-01-20", "confidence": "confirmed",
            "deadlines": [{
                "type": "full_paper", "label": "Paper deadline",
                "datetime": "2026-12-01T23:59:00Z",
                "opens_at": "2026-11-10T00:00:00Z", "confidence": "estimated",
            }],
        }
        milestones = _milestones(sample)
        self.assertEqual([item["type"] for item in milestones], [
            "full_paper_opens", "full_paper", "conference_start",
        ])
        self.assertEqual([item["estimated"] for item in milestones], [True, True, False])

    def test_qualitative_estimate_is_explicit(self) -> None:
        rates = load_acceptance_rates()["rates"]
        uai = next(item for item in self.conferences if item["series"] == "UAI")
        cell = _acceptance_cell(uai, rates)
        self.assertIn("Low", cell)
        self.assertIn("(estimated)", cell)
        self.assertIn("basis", rates["UAI"])

    def test_date_only_milestone_keeps_tooltip_without_time_estimate_label(self) -> None:
        milestone = {
            "type": "full_paper", "label": "Paper submission",
            "datetime": "2026-11-02T23:59:00-12:00",
            "estimated": False, "approximate_time": True,
        }
        html = _deadline_grid_rows([milestone])
        self.assertNotIn("(time est.)", html)
        self.assertNotIn("(est.)", html)
        self.assertIn('title="Official day; exact hour/timezone unannounced.', html)

    def test_estimated_date_still_has_milestone_label(self) -> None:
        milestone = {
            "type": "full_paper", "label": "Paper submission",
            "datetime": "2026-11-02T23:59:00-12:00",
            "estimated": True, "approximate_time": True,
        }
        html = _deadline_grid_rows([milestone])
        self.assertIn("(est.)", html)
        self.assertNotIn("(time est.)", html)
        self.assertNotIn("Official day", html)


if __name__ == "__main__":
    unittest.main()

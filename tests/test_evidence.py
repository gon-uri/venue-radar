from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_site import _acceptance_cell, _ranking_cell
from validate import (
    acceptance_band,
    load_acceptance_rates,
    load_ccf_rankings,
    load_conferences,
    load_icore_rankings,
    validate_acceptance_rates,
    validate_ccf_rankings,
)


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.conferences = load_conferences()
        cls.ccf = load_ccf_rankings()
        cls.rates = load_acceptance_rates()
        cls.icore = load_icore_rankings()

    def test_ccf_mapping_and_coverage(self) -> None:
        self.assertEqual(validate_ccf_rankings(self.conferences, self.ccf), [])
        self.assertEqual(len(self.ccf["rankings"]), 67)
        self.assertIn("ICASSP", self.ccf["rankings"])
        self.assertNotIn("ICASSP", self.icore["rankings"])
        self.assertNotIn("IJCAI-ECAI", self.ccf["rankings"])
        self.assertEqual(self.ccf["rankings"]["IJCAI"]["rank"], "B")
        self.assertEqual(self.icore["rankings"]["IJCAI"]["rank"], "A*")
        self.assertEqual(self.ccf["rankings"]["ECAI"]["rank"], "B")
        self.assertEqual(self.icore["rankings"]["ECAI"]["rank"], "A")

    def test_ccf_rejects_malformed_rank_and_workshop(self) -> None:
        data = deepcopy(self.ccf)
        data["rankings"]["NeurIPS"]["rank"] = ["A"]
        data["rankings"]["FMTS @ NeurIPS"] = {"rank": "A", "page": 57}
        errors = validate_ccf_rankings(self.conferences, data)
        self.assertTrue(any("NeurIPS: rank must" in error for error in errors))
        self.assertTrue(any("workshops must not inherit" in error for error in errors))

    def test_acceptance_bands_and_sources(self) -> None:
        self.assertEqual(validate_acceptance_rates(self.conferences, self.rates), [])
        for percent, expected in (
            (19.99, "Very low"), (20, "Low"), (29.99, "Low"),
            (30, "Moderate"), (40, "High"), (60, "Very high"),
        ):
            self.assertEqual(acceptance_band(percent), expected)
        neurips = next(item for item in self.conferences if item["series"] == "NeurIPS")
        cell = _acceptance_cell(neurips, self.rates["rates"])
        self.assertIn("24.52%", cell)
        self.assertIn("2025", cell)
        self.assertIn("Low", cell)

    def test_rank_pair_keeps_sources_separate(self) -> None:
        icassp = next(item for item in self.conferences if item["series"] == "ICASSP")
        cell = _ranking_cell(
            icassp, self.icore["rankings"], self.ccf["rankings"], self.ccf["page_url"]
        )
        self.assertIn("No ICORE 2026 main-track rank", cell)
        self.assertIn("CCF 2026 rank B", cell)


if __name__ == "__main__":
    unittest.main()

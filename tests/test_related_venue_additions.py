from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_ics import series_slug
from catalog_metadata import CITIES_PATH, CONFERENCE_FAMILIES_PATH, load_mapping, map_events
from conference_scopes import load_scopes
from rollover_editions import CADENCE_YEARS
from validate import (
    SUBMISSION_TYPES, load_ccf_rankings, load_conferences, load_icore_rankings,
)

# Owner-approved on 2026-10-31 from the related-venue search
# (project_docs/conference_candidates.md). Each series was drafted from official
# pages by one agent and re-checked by an independent verifier.
ADDED = [
    "ACCV", "ALT", "AMIA", "ASRU", "BIOSIG", "CHIIR", "CLeaR", "CNS CogNeuro", "COPA",
    "ENOC", "ESWC", "FENS Forum", "FORC", "ICCP", "ICDL", "ICME", "ICMNS", "ICONS",
    "ICWSM", "IEEE CEC", "INLG", "IPCAI", "IPMI", "IROS", "ISF", "IUI", "IVA", "MTNS",
    "NAISys", "NCM", "NetSci-X", "Neural Interfaces", "PPSN", "RLC", "RLDM", "SIGDIAL",
    "SLT", "SNL", "UMAP", "WASPAA", "EAAMO", "ECAF", "IFAC WC", "SIAM MDS",
]


class RelatedVenueAdditionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.conferences = load_conferences()
        cls.by_id = {c["id"]: c for c in cls.conferences}
        cls.families = load_mapping(CONFERENCE_FAMILIES_PATH)
        cls.scopes = load_scopes()

    def test_every_added_series_has_records_families_and_a_profile(self) -> None:
        series = {c["series"] for c in self.conferences}
        self.assertEqual(len(ADDED), 44)
        for name in ADDED:
            self.assertIn(name, series)
            self.assertIn(name, self.families, name)
            self.assertIn(name, self.scopes, name)
        self.assertEqual(len(series), 175)

    def test_identity_collisions_are_avoided(self) -> None:
        # The Cognitive Neuroscience Society is not OCNS's CNS*.
        cogneuro = self.by_id["cns-cogneuro-2027"]
        self.assertEqual((cogneuro["series"], cogneuro["short_title"]), ("CNS CogNeuro", "CNS CogNeuro 2027"))
        self.assertNotEqual(series_slug("CNS CogNeuro"), series_slug("CNS*"))
        self.assertEqual(self.by_id["cns-2027"]["series"], "CNS*")
        # NetSci-X is the Network Science Society's winter meeting, not NetSci.
        self.assertNotEqual(series_slug("NetSci-X"), series_slug("NetSci"))

    def test_asru_and_slt_have_no_projected_successor(self) -> None:
        # From 2027 IEEE SPS merges ASRU and SLT into the new ASLI conference.
        for name in ("ASRU", "SLT"):
            editions = [c for c in self.conferences if c["series"] == name]
            self.assertEqual(len(editions), 1, name)
            self.assertNotIn(name, CADENCE_YEARS)
            self.assertIn("ASLI", editions[0]["notes"])

    def test_irregular_series_stay_out_of_automatic_rollover(self) -> None:
        for name in ("NAISys", "RLDM", "Neural Interfaces"):
            self.assertNotIn(name, CADENCE_YEARS, name)
        self.assertEqual((CADENCE_YEARS["PPSN"], CADENCE_YEARS["IFAC WC"], CADENCE_YEARS["CLeaR"]), (2, 3, 1))

    def test_unusual_routes_keep_their_semantics(self) -> None:
        # Presenting an already published journal article is not a fresh submission.
        ipcai = {d["type"]: d for d in self.by_id["ipcai-2027"]["deadlines"]}
        self.assertNotIn(ipcai["journal_presentation"]["type"], SUBMISSION_TYPES)
        self.assertIn("late_abstract", ipcai)
        # FORC's two archival cycles are independent routes with distinct types.
        forc = [d["type"] for d in self.by_id["forc-2027"]["deadlines"] if d["type"] in SUBMISSION_TYPES]
        self.assertEqual(forc, ["full_paper", "regular_paper"])
        # A "CDT" cutoff in February stores the earliest literal instant with a note.
        abstract = next(d for d in self.by_id["neural-interfaces-2027"]["deadlines"] if d["type"] == "abstract")
        self.assertEqual(abstract["datetime"], "2027-02-17T13:00:00-05:00")
        self.assertIn("CST", abstract["cutoff_note"])
        # A date the organizer marks tentative stays estimated (ITISE precedent).
        late = next(d for d in self.by_id["cns-cogneuro-2027"]["deadlines"] if d["type"] == "late_abstract")
        self.assertEqual(late["confidence"], "estimated")

    def test_two_site_rlc_2027_is_estimated_and_off_the_map(self) -> None:
        rlc = self.by_id["rlc-2027"]
        self.assertEqual(rlc["confidence"], "estimated")
        self.assertNotIn("timezone", rlc)
        mapped = {e["id"] for e in map_events(self.conferences, load_mapping(CITIES_PATH))}
        self.assertNotIn("rlc-2027", mapped)
        self.assertIn("rldm-2027", mapped)
        self.assertIn("clear-2027", mapped)

    def test_ranks_use_exact_series_and_official_releases_only(self) -> None:
        icore = load_icore_rankings()["rankings"]
        ccf = load_ccf_rankings()["rankings"]
        self.assertEqual((icore["ICCP"]["rank"], icore["ICCP"]["portal_id"]), ("B", 2343), "Computational Photography, not portal 660")
        self.assertEqual(icore["IEEE CEC"], {"rank": "B", "portal_id": 2061})
        self.assertNotIn("AMIA", icore, "ICORE2026 lists AMIA only as National: USA")
        self.assertEqual((ccf["AMIA"]["rank"], ccf["SLT"]["rank"], ccf["ICWSM"]["rank"]), ("C", "C", "B"))
        for name in ("IPMI", "CLeaR", "RLC", "NAISys", "FENS Forum"):
            self.assertNotIn(name, icore)
            self.assertNotIn(name, ccf)


if __name__ == "__main__":
    unittest.main()

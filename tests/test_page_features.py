from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_site import (
    PAGE_TITLE, SOCIAL_CARD_URL, _effective_cutoff, _evidence_line, _older_year_link, build_site,
)
from catalog_metadata import validate_catalog_metadata
from validate import load_controlled_topics
from build_site import TOPIC_CATALOG


class PageFeatureTests(unittest.TestCase):
    """Server-side pieces of ADR-040."""

    @classmethod
    def setUpClass(cls) -> None:
        with TemporaryDirectory() as directory:
            cls.html = build_site(docs_dir=Path(directory)).read_text(encoding="utf-8")

    def test_prior_edition_links_are_recognised_by_year(self) -> None:
        self.assertTrue(_older_year_link("https://icml.cc/Conferences/2026/CallForPapers", 2027))
        self.assertFalse(_older_year_link("https://icml.cc/Conferences/2027/CallForPapers", 2027))
        self.assertFalse(_older_year_link("https://neurips.cc/", 2027))

    def test_date_only_cutoffs_end_in_the_host_zone(self) -> None:
        conference = {"location": "Jeongseon, South Korea", "timezone": "Etc/GMT+12"}
        day_only = {"datetime": "2026-11-15T23:59:00-12:00", "time_precision": "date"}
        self.assertEqual(_effective_cutoff(conference, day_only), ("2026-11-15T14:59:00Z", "Asia/Seoul"))
        exact = {"datetime": "2026-11-15T23:59:00-12:00"}
        self.assertEqual(_effective_cutoff(conference, exact), ("2026-11-16T11:59:00Z", None))
        unknown = {"location": "To be announced", "timezone": "Etc/GMT+12"}
        self.assertEqual(_effective_cutoff(unknown, day_only), ("2026-11-16T11:59:00Z", None))
        # Rollover drafts keep the prior host's zone; an unannounced host has none.
        for location in ("To be announced", "Europe (city to be announced)"):
            prior_host = {"location": location, "timezone": "Europe/Berlin"}
            self.assertEqual(_effective_cutoff(prior_host, day_only), ("2026-11-16T11:59:00Z", None))
        announced = {"location": "Suzhou, China", "timezone": "Asia/Shanghai"}
        self.assertEqual(_effective_cutoff(announced, day_only)[1], "Asia/Shanghai")
        organizer_zone = {"datetime": "2026-11-17T23:59:00+01:00", "time_precision": "date"}
        self.assertIsNone(_effective_cutoff(conference, organizer_zone)[1], "An explicit organizer zone is kept")

    def test_cities_need_real_time_zones(self) -> None:
        cities = {"x": {"label": "X", "lat": 1.0, "lon": 1.0, "tz": "Mars/Olympus", "locations": ["X, Y"]}}
        errors = validate_catalog_metadata(load_controlled_topics() or set(), TOPIC_CATALOG, cities)
        self.assertIn("x: tz must be an IANA time zone", errors)

    def test_evidence_line_names_sources_and_prefills_corrections(self) -> None:
        line = _evidence_line({
            "id": "demo-2027", "short_title": "DEMO 2027", "year": 2027, "confidence": "estimated",
            "website": "https://demo.org/", "cfp_url": "https://demo.org/2026/cfp",
            "source_urls": ["https://demo.org/2026/dates"], "last_checked": "2026-10-29", "mode": "hybrid",
        })
        for text in ("Previous call", "Previous dates", "Checked Oct 29, 2026", "Hybrid", "Dates estimated",
                     'data-copy-link="demo-2027"', "template=correction.yml", "edition=demo-2027"):
            self.assertIn(text, line)

    def test_conference_rows_are_lighter_and_icons_are_shared(self) -> None:
        conference_rows = re.findall(r"<tr [^>]*data-conference-row>", self.html)
        self.assertTrue(conference_rows)
        self.assertFalse(any("data-deadlines=" in row for row in conference_rows))
        self.assertEqual(self.html.count('<symbol id="icon-chevron-down"'), 1)
        # Only the one-off header and map icons keep inline notices; rows use the sprite.
        self.assertLessEqual(self.html.count("@license lucide-static"), 4)

    def test_head_has_search_and_preview_metadata(self) -> None:
        self.assertIn(f"<title>{PAGE_TITLE.replace('&', '&amp;')}</title>", self.html)
        self.assertIn(f'<meta property="og:image" content="{SOCIAL_CARD_URL}">', self.html)
        self.assertIn('<meta name="twitter:card" content="summary_large_image">', self.html)
        self.assertTrue((Path(__file__).resolve().parents[1] / "assets/branding/social-card.png").exists())
        self.assertIn('<link rel="canonical" href="https://gon-uri.github.io/venue-radar/">', self.html)


if __name__ == "__main__":
    unittest.main()

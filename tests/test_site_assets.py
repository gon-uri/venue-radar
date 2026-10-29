from __future__ import annotations

import base64
import re
import struct
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_site import ASSETS_DIR, SHARE_TEXT, SITE_URL, build_site
from validate import load_conferences


class PageElements(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs) -> None:
        self.elements.append((tag, dict(attrs)))


class SiteAssetTests(unittest.TestCase):
    def test_branding_asset_dimensions_and_readme_placement(self) -> None:
        for name, dimensions in (
            ("venue-radar.png", (256, 256)),
            ("branding/venue-radar-source.png", (256, 256)),
            ("branding/venue-radar-banner.png", (1400, 175)),
        ):
            png = (ASSETS_DIR / name).read_bytes()
            self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", png[16:24]), dimensions)
        readme = (ASSETS_DIR.parent / "README.md").read_text(encoding="utf-8")
        self.assertTrue(readme.startswith('<a href="https://gon-uri.github.io/venue-radar/">'))
        self.assertLess(readme.index("assets/branding/venue-radar-banner.png"), readme.index("# [Open Venue Radar]"))
        self.assertNotIn('src="assets/venue-radar.png"', readme)

    def test_readme_images_links_and_counts_stay_true(self) -> None:
        root = ASSETS_DIR.parent
        readme = (root / "README.md").read_text(encoding="utf-8")
        targets = [a or b for a, b in re.findall(r'(?:src|href)="([^"]+)"|\]\(([^)\s]+)\)', readme)]
        local = [t for t in targets if not t.startswith(("http://", "https://", "#", "mailto:"))]
        self.assertIn("assets/readme/hero.webp", local)
        for target in local:
            with self.subTest(target=target):
                self.assertTrue((root / target).is_file(), f"README links a missing file: {target}")
        # In-page links (the Calendar feeds badge) must match a README heading.
        anchors = {re.sub(r"[^\w -]", "", heading.strip().lower()).replace(" ", "-")
                   for heading in re.findall(r"^#{1,6} (.+)$", readme, re.M)}
        for target in (t for t in targets if t.startswith("#")):
            with self.subTest(anchor=target):
                self.assertIn(target[1:], anchors)
        # Screenshots from scripts/build_readme_images.mjs are WebP, and every one is used.
        images = (ASSETS_DIR / "readme").iterdir()
        for image in sorted(p for p in images if p.is_file() and not p.name.startswith(".")):
            with self.subTest(image=image.name):
                header = image.read_bytes()[:12]
                self.assertEqual((header[:4], header[8:12]), (b"RIFF", b"WEBP"))
                self.assertIn(f"assets/readme/{image.name}", local)
        # "N+ conference series" must never claim more than the catalog holds.
        series = {record["series"] for record in load_conferences()}
        claims = [int(n) for n in re.findall(r"(\d+)\+(?:&nbsp;|\s)conference(?:&nbsp;|\s)series", readme)]
        self.assertTrue(claims, "README states the catalog size as N+ conference series")
        for claim in claims:
            self.assertLessEqual(claim, len(series))
        # Static badge labels never carry a count that would go stale.
        for label in re.findall(r'src="https://img\.shields\.io/badge/([^"?]+)-[0-9a-fA-F]{6}"', readme):
            self.assertNotRegex(label, r"\d", label)

    def test_renamed_repository_links_and_stable_comment_mapping(self) -> None:
        with TemporaryDirectory() as directory:
            html = build_site(docs_dir=Path(directory)).read_text(encoding="utf-8")
        repo = "https://github.com/gon-uri/venue-radar"
        for suffix in (
            "", "/issues/new?template=conference-request.yml", "/discussions",
            "/blob/main/LICENSE", "/blob/main/CONTENT-LICENSE.md",
        ):
            self.assertIn(f'href="{repo}{suffix}"', html)
        self.assertIn("repo: 'gon-uri/venue-radar'", html)
        self.assertIn("'repo-id': 'R_kgDOTQKmZg'", html)
        self.assertIn("'category-id': 'DIC_kwDOTQKmZs4DHLTi'", html)
        self.assertIn("mapping: 'specific', term: 'Venue Radar community'", html)
        self.assertIn('href="calendar-all.ics" download', html)
        texts = [html]
        texts.extend((ASSETS_DIR.parent / name).read_text(encoding="utf-8")
                     for name in ("README.md", "CONTENT-LICENSE.md"))
        for text in texts:
            self.assertNotIn("gon-uri/scientific-conference-calendar", text)
            self.assertNotIn("gon-uri.github.io/scientific-conference-calendar", text)

    def test_current_logo_is_embedded_in_the_site(self) -> None:
        with TemporaryDirectory() as directory:
            html = build_site(docs_dir=Path(directory)).read_text(encoding="utf-8")
        logo = base64.b64encode((ASSETS_DIR / "venue-radar.png").read_bytes()).decode("ascii")
        self.assertIn(f'src="data:image/png;base64,{logo}" alt=""', html)
        favicon = base64.b64encode((ASSETS_DIR / "favicon.svg").read_bytes()).decode("ascii")
        self.assertIn(f'<link rel="icon" type="image/svg+xml" sizes="any" href="data:image/svg+xml;base64,{favicon}">', html)
        svg = ElementTree.parse(ASSETS_DIR / "favicon.svg").getroot()
        self.assertEqual(svg.attrib["viewBox"], "0 0 64 64")
        background = svg.find("{http://www.w3.org/2000/svg}rect")
        self.assertEqual(background.attrib, {"width": "64", "height": "64", "fill": "#ffffff"})

    def test_sharing_links_are_prefilled_and_do_not_post_automatically(self) -> None:
        with TemporaryDirectory() as directory:
            html = build_site(docs_dir=Path(directory)).read_text(encoding="utf-8")
        page = PageElements()
        page.feed(html)
        actions = {attrs["class"]: attrs for tag, attrs in page.elements
                   if tag == "a" and "header-button" in attrs.get("class", "")}
        share = actions["header-button share-button"]
        url = urlparse(share["href"])
        self.assertEqual((url.scheme, url.netloc, url.path), ("https", "x.com", "/intent/tweet"))
        self.assertEqual(parse_qs(url.query), {"text": [SHARE_TEXT], "url": [SITE_URL]})
        self.assertIn("for ML, AI, neuroscience, and related fields.", SHARE_TEXT)
        self.assertLessEqual(len(SHARE_TEXT) + 24, 280)
        self.assertEqual(actions["header-button star-button"]["href"], "https://github.com/gon-uri/venue-radar")
        for attrs in actions.values():
            self.assertEqual(attrs["target"], "_blank")
            self.assertEqual(attrs["rel"], "noopener noreferrer")
        self.assertNotIn("platform.twitter.com/widgets.js", html)

    def test_submission_options_selected_and_filters_have_responsive_default(self) -> None:
        with TemporaryDirectory() as directory:
            html = build_site(docs_dir=Path(directory)).read_text(encoding="utf-8")
        page = PageElements()
        page.feed(html)
        inputs = {attrs.get("id"): attrs for tag, attrs in page.elements if tag == "input"}
        self.assertIn("checked", inputs["open-only"])
        details = next(attrs for tag, attrs in page.elements
                       if tag == "details" and attrs.get("id") == "filter-details")
        self.assertIn("open", details)
        self.assertIn("document.querySelector('#filter-details').open = !matchMedia('(max-width: 760px)').matches;", html)
        self.assertNotIn("time-series-shortcut", inputs)
        self.assertIn('value="time-series-sequential-data"', html)

    def test_mobile_cards_have_independent_disclosures_and_full_fallback_details(self) -> None:
        with TemporaryDirectory() as directory:
            html = build_site(docs_dir=Path(directory)).read_text(encoding="utf-8")
        page = PageElements()
        page.feed(html)
        rows = [attrs for tag, attrs in page.elements if tag == "tr" and "data-filter-row" in attrs]
        buttons = [attrs for tag, attrs in page.elements
                   if tag == "button" and attrs.get("class") == "mobile-info-toggle"]
        details = [attrs for tag, attrs in page.elements
                   if tag == "td" and "mobile-detail" in attrs.get("class", "").split()]
        self.assertEqual(len(buttons), len(rows))
        self.assertEqual(len(details), len(rows) * 5)
        self.assertTrue(all(button["type"] == "button" and button["aria-expanded"] == "false"
                            and button["aria-label"].startswith("More info for ") for button in buttons))
        self.assertTrue(all("hidden" not in cell for cell in details))
        self.assertIn('.mobile-row-disclosure { display: none; }', html)
        self.assertIn('.mobile-cards-ready tr[data-mobile-expanded="false"] > .mobile-detail { display: none; }', html)
        self.assertIn("initializeMobileCards();", html)
        self.assertIn('class="lucide lucide-chevron-down"', html)
        css = (ASSETS_DIR / "site.css").read_text(encoding="utf-8")
        mobile = css.split('@media (max-width: 760px) {', 1)[1]
        for rule in (
            'tr[data-filter-row] { border-color: var(--line-strong); margin-bottom: 14px; }',
            'td::before { text-transform: none; font-size: .8125rem; color: #526267; }',
            'td[data-label="Conference"] { background: #edf5f5; border-radius: 7px 7px 0 0; }',
            'min-height: 36px; padding: 4px 10px;',
        ):
            self.assertIn(rule, mobile)
            self.assertIn(rule, html)

    def test_public_attribution_and_header_action_order(self) -> None:
        with TemporaryDirectory() as directory:
            html = build_site(docs_dir=Path(directory)).read_text(encoding="utf-8")
        page = PageElements()
        page.feed(html)
        self.assertEqual(
            [attrs["class"] for tag, attrs in page.elements
             if tag in {"a", "summary"} and attrs.get("class") in {
                 "header-button share-button", "header-button star-button", "calendar-button",
             }],
            ["header-button share-button", "header-button star-button", "calendar-button"],
        )
        self.assertLess(html.index('<summary class="calendar-button">'), html.index('class="calendar-caption"'))

    def test_calendar_menu_offers_subscriptions_and_snapshots(self) -> None:
        with TemporaryDirectory() as directory:
            html = build_site(docs_dir=Path(directory)).read_text(encoding="utf-8")
        for path in ("submissions.ics", "calendar-all.ics", "conferences.ics"):
            webcal = "webcal://gon-uri.github.io/venue-radar/" + path
            self.assertIn(f'href="{webcal}"', html)
            self.assertIn(f'href="https://calendar.google.com/calendar/render?cid={webcal}"', html)
            self.assertIn(f'data-copy-feed="{SITE_URL}{path}"', html)
            self.assertIn(f'href="{path}" download', html)
        self.assertIn('<option value="tags/machine-learning.ics">', html)
        self.assertIn('<option value="series/neurips.ics" data-series-slug="neurips">NeurIPS</option>', html)
        self.assertIn('data-subscribe-series="neurips"', html)
        self.assertIn("lucide-calendar-plus", html)
        self.assertNotIn("On the map", html)
        self.assertIn('tabindex="-1">Conferences &amp; Map</button>', html)
        self.assertIn(
            '<p class="subhead">Find your next conference in machine learning and AI, '
            'or explore related opportunities in neuroscience, healthcare, '
            'complex systems, and control.</p>', html,
        )
        self.assertIn('aria-label="Confirmed upcoming conference locations"', html)
        self.assertIn('Created and maintained by <strong>Gonzalo Uribarri</strong>.', html)
        self.assertNotIn("Assistant Professor", html)
        self.assertIn('href="https://www.su.se/profiles/g/gour8957"', html)
        readme = (ASSETS_DIR.parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("Assistant Professor at the\nDepartment of Computer and Systems Sciences,", readme)
        self.assertNotIn("https://www.su.se/english/divisions/", readme)
        self.assertIn("[University profile](https://www.su.se/profiles/g/gour8957)", readme)
        self.assertIn(
            "Spotted an error or have an idea for a new feature? "
            "[Open an issue](https://github.com/gon-uri/venue-radar/issues/new).", readme,
        )
        self.assertIn(
            "[Send a request](https://github.com/gon-uri/venue-radar/issues/new?template=conference-request.yml)",
            readme,
        )
        final_paragraph = readme.strip().split("\n\n")[-1].replace("\n", " ")
        self.assertTrue(final_paragraph.startswith("Code is available under"))
        self.assertTrue(final_paragraph.endswith(
            "Venue Radar is a personal project by Gonzalo Uribarri, "
            "not an official Stockholm University service."
        ))

    def test_conference_names_are_semibold_without_size_or_color_overrides(self) -> None:
        with TemporaryDirectory() as directory:
            html = build_site(docs_dir=Path(directory)).read_text(encoding="utf-8")
        self.assertIn('td[data-label="Conference"] > a { font-weight: 600; }', html)

    def test_title_font_is_embedded_with_its_original_license(self) -> None:
        font = (ASSETS_DIR / "vendor" / "audiowide-latin.woff2").read_bytes()
        self.assertEqual(font[:4], b"wOF2")
        with TemporaryDirectory() as directory:
            html = build_site(docs_dir=Path(directory)).read_text(encoding="utf-8")
        self.assertIn("data:font/woff2;base64," + base64.b64encode(font).decode("ascii"), html)
        self.assertIn('with Reserved Font Names "Audiowide"', html)
        self.assertIn("SIL OPEN FONT LICENSE Version 1.1", html)
        self.assertNotIn("fonts.googleapis.com", html)
        self.assertNotIn("fonts.gstatic.com", html)


if __name__ == "__main__":
    unittest.main()

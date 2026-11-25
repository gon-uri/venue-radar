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
            ("branding/social-card.png", (1200, 630)),
            ("branding/venue-radar-banner.png", (1400, 175)),
            ("branding/venue-radar-banner-dark.png", (1400, 175)),
        ):
            png = (ASSETS_DIR / name).read_bytes()
            self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", png[16:24]), dimensions)
        readme = (ASSETS_DIR.parent / "README.md").read_text(encoding="utf-8")
        # The banner comes first, as a bare <picture>: GitHub's renderer pulls the
        # image out of a <picture> wrapped in a link, which breaks the dark source.
        self.assertTrue(readme.startswith("<picture>\n"))
        banner = readme[:readme.index("</picture>")]
        self.assertNotIn("<a ", banner)
        self.assertIn('<source media="(prefers-color-scheme: dark)" '
                      'srcset="assets/branding/venue-radar-banner-dark.png">', banner)
        self.assertIn('<img src="assets/branding/venue-radar-banner.png"', banner)
        # The heading right below the banner is the link to the calendar.
        self.assertLess(readme.index("</picture>"), readme.index("# [Open Venue Radar](https://gon-uri.github.io/venue-radar/)"))
        # GitHub's dark themes get the transparent dark banner (RGBA PNG).
        self.assertEqual((ASSETS_DIR / "branding/venue-radar-banner-dark.png").read_bytes()[25], 6)
        self.assertNotIn('src="assets/venue-radar.png"', readme)

    def test_readme_images_links_and_counts_stay_true(self) -> None:
        root = ASSETS_DIR.parent
        readme = (root / "README.md").read_text(encoding="utf-8")
        targets = [a or b for a, b in re.findall(r'(?:src|srcset|href)="([^"]+)"|\]\(([^)\s]+)\)', readme)]
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
        # ADR-057: the Ping tile is inlined (colours follow the page tokens).
        self.assertIn('<div class="brand-line"><svg class="brand-mark" aria-hidden="true" focusable="false" ', html)
        self.assertNotIn("data:image/png;base64", html.split("<header>", 1)[1].split("</header>", 1)[0])
        favicon = base64.b64encode((ASSETS_DIR / "favicon.svg").read_bytes()).decode("ascii")
        self.assertIn(f'<link rel="icon" type="image/svg+xml" sizes="any" href="data:image/svg+xml;base64,{favicon}">', html)
        ns = "{http://www.w3.org/2000/svg}"
        mark = ElementTree.parse(ASSETS_DIR / "venue-radar.svg").getroot()
        icon = ElementTree.parse(ASSETS_DIR / "favicon.svg").getroot()
        for svg in (mark, icon):
            self.assertEqual(svg.attrib["viewBox"], "4 4 40 40")
            tile = svg.find(f"{ns}rect")
            self.assertEqual((tile.attrib["width"], tile.attrib["height"], tile.attrib["rx"]), ("40", "40", "11"))
            circles = svg.findall(f".//{ns}circle")
            self.assertTrue(all((c.attrib["cx"], c.attrib["cy"]) == ("31", "17") for c in circles))
        # The 16 px favicon drops the faint outer ring; everything else is the same drawing.
        self.assertEqual(sorted(c.attrib["r"] for c in mark.findall(f".//{ns}circle")), ["17", "24.5", "4.6", "9.5"])
        self.assertEqual(sorted(c.attrib["r"] for c in icon.findall(f".//{ns}circle")), ["17", "4.6", "9.5"])
        self.assertIn("prefers-color-scheme: dark", (ASSETS_DIR / "favicon.svg").read_text(encoding="utf-8"))

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
        # ADR-049: More filters starts collapsed at every width; search and the
        # family/archival chips stay visible in the bar above it.
        self.assertNotIn("open", details)
        # Only the 1200px rail opens the panel by width (ADR-058); the phone
        # sheet (ADR-059) styles an open panel but never opens it.
        self.assertEqual(html.count("details.open = true"), 1)
        self.assertIn("if (rail.matches && !details.open) { details.open = true;", html)
        chips = [attrs for tag, attrs in page.elements if tag == "button" and "chip" in (attrs.get("class") or "").split()]
        self.assertEqual(len(chips), 9)
        self.assertEqual(sum("data-chip-family" in attrs for attrs in chips), 8)
        self.assertTrue(all(attrs.get("aria-pressed") == "false" for attrs in chips))
        self.assertLess(html.index('id="search"'), html.index('id="filter-details"'))
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
            'td::before { text-transform: none; font-size: .8125rem; color: var(--muted); }',
            'td[data-label="Conference"] { background: var(--raised); border-radius: 7px 7px 0 0; }',
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
        self.assertIn('<select id="feed-family" data-feed-select><option value="families/ml-ai.ics">ML &amp; Data Science</option>', html)
        self.assertIn('<option value="families/neuroscience.ics">Neuroscience &amp; Neurotechnology</option>', html)
        self.assertIn('<strong>Deadlines in one field</strong>', html)
        self.assertIn('<option value="series/neurips.ics" data-series-slug="neurips">NeurIPS</option>', html)
        self.assertIn('data-subscribe-series="neurips"', html)
        self.assertIn("lucide-calendar-plus", html)
        self.assertNotIn("On the map", html)
        self.assertIn('tabindex="-1">Conferences &amp; Map</button>', html)
        self.assertIn(
            '<p class="subhead">Find where to submit next: conference deadlines for '
            'machine learning and AI, neuroscience, healthcare, complex systems, '
            'and control.</p>', html,
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

    def test_fonts_are_embedded_with_their_licenses(self) -> None:
        with TemporaryDirectory() as directory:
            html = build_site(docs_dir=Path(directory)).read_text(encoding="utf-8")
        for name in ("sora-latin-600", "inter-latin-wght", "geist-mono-latin-400", "geist-mono-latin-600"):
            font = (ASSETS_DIR / "vendor" / f"{name}.woff2").read_bytes()
            self.assertEqual(font[:4], b"wOF2")
            self.assertIn("data:font/woff2;base64," + base64.b64encode(font).decode("ascii"), html)
        for notice in ("The Sora Project Authors", "The Inter Project Authors", "The Geist Project Authors"):
            self.assertIn(notice, html)
        self.assertIn("SIL OPEN FONT LICENSE Version 1.1", html)
        self.assertNotIn("Audiowide", html)
        self.assertNotIn("fonts.googleapis.com", html)
        self.assertNotIn("fonts.gstatic.com", html)

    def test_theme_tokens_meet_contrast_in_light_and_dark(self) -> None:
        css = (ASSETS_DIR / "base.css").read_text(encoding="utf-8")
        light = dict(re.findall(r"--([a-z0-9-]+): (#[0-9a-f]{6});", css.split("@media (prefers-color-scheme: dark)", 1)[0]))
        dark = {**light, **dict(re.findall(r"--([a-z0-9-]+): (#[0-9a-f]{6});", css.split("@media (prefers-color-scheme: dark)", 1)[1].split("}", 1)[0]))}

        def luminance(color: str) -> float:
            channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        def ratio(a: str, b: str) -> float:
            hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
            return (hi + 0.05) / (lo + 0.05)

        text_pairs = [("text", "bg"), ("text", "raised"), ("muted", "bg"), ("muted", "raised"), ("faint", "raised"),
                      ("accent-dark", "bg"), ("accent-dark", "raised"), ("on-accent", "accent-dark"),
                      ("open", "open-bg"), ("open", "raised"), ("closed", "closed-bg"), ("warn", "warn-bg"),
                      ("soon", "raised"), ("final", "raised"), ("rank-fg", "rank-bg"), ("rank-top-fg", "rank-top-bg"),
                      ("tip-text", "tip-bg"), ("tag-text", "tag"),
                      ("rank-astar-fg", "rank-astar-bg"), ("rank-a-fg", "rank-a-bg"),
                      ("rank-b-fg", "rank-b-bg"), ("rank-c-fg", "rank-c-bg")]
        for name, tokens in (("light", light), ("dark", dark)):
            for fg, bg in text_pairs:
                self.assertGreaterEqual(ratio(tokens[fg], tokens[bg]), 4.5, f"{name}: --{fg} on --{bg}")
            self.assertGreaterEqual(ratio(tokens["control-border"], tokens["raised"]), 3, f"{name}: control border")

if __name__ == "__main__":
    unittest.main()

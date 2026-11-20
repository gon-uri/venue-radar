import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from build_site import GTM_CONTAINER_ID


class AnalyticsTagTests(unittest.TestCase):
    """ADR-056: the owner's Google Tag Manager container loads once, early in <head>."""

    def test_published_page_loads_the_container_once_in_the_head(self):
        html = (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8')
        head = html.split('</head>', 1)[0]
        source = f'https://www.googletagmanager.com/gtm.js?id={GTM_CONTAINER_ID}'
        self.assertEqual(GTM_CONTAINER_ID, 'GTM-MKS3WJCL')
        self.assertEqual(html.count(source), 1)
        self.assertIn(f'<script async src="{source}"></script>', head)
        self.assertIn("gtag('js', new Date());", head)
        # It precedes the page's own scripts and styles so early visits are counted.
        self.assertLess(head.index(source), head.index('<style>'))


if __name__ == '__main__':
    unittest.main()

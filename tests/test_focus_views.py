import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from build_site import PLAN_B_BUTTON, PLAN_B_TYPES
from validate import SUBMISSION_TYPES, load_conferences


class FocusViewMarkupTests(unittest.TestCase):
    """ADR-064 (Plan B) and ADR-065 (shared shortlist) in the committed page."""

    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8')

    def test_every_decision_date_offers_a_script_only_plan_b(self):
        with_decision = {c['id'] for c in load_conferences()
                         if any(d['type'] == 'notification' for d in c['deadlines'])}
        buttons = re.findall(r'<span class="plan-b-line" hidden><button class="link-button" type="button" '
                             r'data-plan-b="([a-z0-9-]+)">([^<]+)</button></span>', self.html)
        self.assertEqual({edition for edition, _ in buttons}, with_decision)
        self.assertEqual({label for _, label in buttons}, {PLAN_B_BUTTON})
        # The link sits in the decision's own schedule row.
        self.assertRegex(self.html, r'data-deadline-type="notification"[^>]*>(?:(?!</div>).)*data-plan-b="pakdd-2027"')

    def test_plan_b_counts_paper_routes_only(self):
        config = json.loads(re.search(r'<script type="application/json" id="venue-config">(.*?)</script>',
                                      self.html).group(1))
        self.assertEqual(set(config['planBTypes']), set(PLAN_B_TYPES))
        self.assertTrue(PLAN_B_TYPES < SUBMISSION_TYPES)
        self.assertFalse({'abstract', 'poster', 'extended_abstract', 'discussion_paper'} & PLAN_B_TYPES)

    def test_banner_and_share_button_start_hidden(self):
        self.assertIn('<div class="focus-banner" id="focus-banner" role="status" tabindex="-1" hidden>', self.html)
        self.assertIn('data-focus-clear>Show all venues</button>', self.html)
        self.assertIn('data-focus-star hidden>Star these series</button>', self.html)
        self.assertIn('id="share-starred" type="button" hidden', self.html)
        # The banner precedes the tables it explains.
        self.assertLess(self.html.index('id="focus-banner"'), self.html.index('id="panel-deadlines"'))


if __name__ == '__main__':
    unittest.main()

import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from catalog_metadata import CITIES_PATH, load_mapping, map_events
from maintenance_report import decision_backlog
from validate import load_conferences


class NovemberEighteenReviewTests(unittest.TestCase):
    """Facts verified against official pages on 2026-11-18 (draft + independent check)."""

    @classmethod
    def setUpClass(cls):
        cls.conferences = load_conferences()
        cls.records = {item['id']: item for item in cls.conferences}

    def kinds(self, edition):
        return {d['type']: d for d in self.records[edition]['deadlines']}

    def test_extensions_found_in_the_urgent_recheck(self):
        pakdd = self.kinds('pakdd-2027')
        # Only the Research Track moved; the other three tracks keep Nov 20.
        self.assertEqual(pakdd['full_paper']['datetime'], '2026-12-04T23:59:00-12:00')
        self.assertEqual(pakdd['regular_paper']['datetime'][:10], '2026-11-20')
        bci = self.kinds('bci-winter-2027')
        self.assertEqual((bci['full_paper']['datetime'][:10], bci['notification']['datetime'][:10]),
                         ('2026-11-25', '2026-12-20'))
        self.assertIn('extended', bci['full_paper']['label'])

    def test_next_editions_are_added_only_from_official_announcements(self):
        expected = {'ecc-2028': ('confirmed', '2028-06-20', 'Rimini, Italy'),
                    'icassp-2028': ('confirmed', '2028-05-28', 'Tokyo, Japan'),
                    'cvpr-2028': ('estimated', '2028-06-20', 'San Antonio, Texas, USA')}
        for edition, (confidence, start, location) in expected.items():
            item = self.records[edition]
            self.assertEqual((item['confidence'], item['conference_start'], item['location']),
                             (confidence, start, location))
            # No 2028 call exists yet, so every milestone stays a projection.
            self.assertTrue(all(d.get('confidence') == 'estimated' for d in item['deadlines']), edition)
        # Series with only a hosting call or nothing published are not projected.
        for edition in ('aamas-2028', 'ecir-2028', 'netsci-x-2028', 'acm-facct-2028', 'iui-2028'):
            self.assertNotIn(edition, self.records)
        mapped = {event['id'] for event in map_events(self.conferences, load_mapping(CITIES_PATH))}
        self.assertTrue({'ecc-2028', 'icassp-2028', 'icann-2027'} <= mapped)
        self.assertNotIn('cvpr-2028', mapped, 'estimated meetings stay off the map')

    def test_icann_and_conll_corrections(self):
        icann = self.records['icann-2027']
        self.assertEqual((icann['conference_start'], icann['conference_end'], icann['location'], icann['timezone']),
                         ('2027-08-24', '2027-08-27', 'Linköping, Sweden', 'Europe/Stockholm'))
        self.assertTrue(all(d.get('confidence') == 'estimated' for d in icann['deadlines']))
        conll = self.kinds('conll-2027')
        # Re-based on CoNLL 2026 (Feb 19 / Apr 21), not CoNLL 2025.
        self.assertEqual((conll['full_paper']['datetime'][:10], conll['notification']['datetime'][:10]),
                         ('2027-02-19', '2027-04-21'))

    def test_decision_dates_cover_open_main_paper_editions(self):
        confirmed = {'icml-2027': '2027-05-03', 'sigir-2027': '2027-04-05', 'interspeech-2027': '2027-06-02',
                     'rss-2027': '2027-04-30', 'ieee-icmla-2027': '2027-06-15'}
        for edition, day in confirmed.items():
            decision = self.kinds(edition)['notification']
            self.assertEqual(decision['datetime'][:10], day, edition)
            self.assertEqual(decision.get('confidence', self.records[edition]['confidence']), 'confirmed', edition)
        # Projections start from the previous edition's original (pre-extension) pair.
        for edition, day in {'neurips-2027': '2027-09-24', 'alife-2027': '2027-06-07', 'iva-2027': '2027-06-15',
                             'eusipco-2027': '2027-05-12', 'adma-2027': '2027-08-21'}.items():
            decision = self.kinds(edition)['notification']
            self.assertEqual((decision['datetime'][:10], decision['confidence']), (day, 'estimated'), edition)
        # A hidden template block on adma2027.github.io is not an announcement.
        self.assertEqual(self.kinds('adma-2027')['regular_paper'].get('confidence'), 'estimated')
        remaining = {row.name for row in decision_backlog(self.conferences, date(2026, 11, 18))}
        self.assertLessEqual(len(remaining), 6, remaining)

    def test_decision_dates_never_follow_the_meeting(self):
        for item in self.conferences:
            for d in item['deadlines']:
                if d['type'] == 'notification':
                    self.assertLessEqual(d['datetime'][:10], item['conference_start'], item['id'])


if __name__ == '__main__':
    unittest.main()

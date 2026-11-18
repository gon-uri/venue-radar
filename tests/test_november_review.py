import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from validate import SUBMISSION_TYPES, load_conferences


class NovemberReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = {item['id']: item for item in load_conferences()}

    def test_icml_meeting_confirmation_does_not_promote_submission_proxies(self):
        item = self.records['icml-2027']
        self.assertEqual(item['location'], 'Rio de Janeiro, Brazil')
        self.assertEqual((item['conference_start'], item['conference_end']),
                         ('2027-07-31', '2027-08-06'))
        self.assertEqual(item['confidence'], 'confirmed')
        # The 2027 call (read 2026-11-14) confirms the paper routes; the workshop
        # call is still pending, so its proxy stays estimated.
        deadlines = {d['type']: d for d in item['deadlines']}
        self.assertEqual(deadlines['abstract']['datetime'], '2027-01-14T23:59:00-12:00')
        self.assertEqual(deadlines['full_paper']['datetime'], '2027-01-22T23:59:00-12:00')
        for kind in ('abstract', 'full_paper'):
            self.assertEqual(deadlines[kind].get('confidence', item['confidence']), 'confirmed')
        # The decision date is on the 2027 Dates page (read 2026-11-18); other proxies stay estimated.
        self.assertEqual(deadlines['notification']['datetime'][:10], '2027-05-03')
        self.assertNotIn('confidence', deadlines['notification'])
        others = [d for d in item['deadlines'] if d['type'] not in ('abstract', 'full_paper', 'notification')]
        self.assertTrue(others and all(d['confidence'] == 'estimated' for d in others))

    def test_ner_uses_current_days_without_the_stale_template_clock(self):
        deadlines = {d['type']: d for d in self.records['ieee-ner-2027']['deadlines']}
        for kind, day in [('full_paper', '2027-03-15'), ('abstract', '2027-06-02')]:
            deadline = deadlines[kind]
            self.assertEqual(deadline['datetime'], f'{day}T23:59:00-12:00')
            self.assertEqual(deadline['time_precision'], 'date')
            self.assertNotIn('confidence', deadline)
            self.assertEqual(deadline['source_url'], 'https://neuro.embs.org/2027/')
        self.assertNotIn('gate_for', deadlines['abstract'])

    def test_industry_papers_are_independent_of_expired_arr_submissions(self):
        for key, day in [('naacl-2027', '2026-11-13'), ('coling-2027', '2026-11-30')]:
            item = self.records[key]
            deadlines = {d['type']: d for d in item['deadlines']}
            industry = deadlines['regular_paper']
            self.assertIn(industry['type'], SUBMISSION_TYPES)
            self.assertEqual(industry['datetime'], f'{day}T23:59:00-12:00')
            self.assertIn('Industry-track', industry['label'])
            self.assertFalse(any(d.get('gate_for') == 'regular_paper' for d in item['deadlines']))
            self.assertEqual(deadlines['full_paper']['datetime'][:10], '2026-10-12')
            self.assertNotIn(deadlines['commitment']['type'], SUBMISSION_TYPES)
            self.assertNotIn('opens_at', industry)
            self.assertNotIn('open_observed_on', industry)

    def test_sigir_final_dates_do_not_claim_a_known_clock_or_opening(self):
        item = self.records['sigir-2027']
        deadlines = {d['type']: d for d in item['deadlines']}
        self.assertEqual(deadlines['abstract']['gate_for'], 'full_paper')
        for kind, day in [('abstract', '2027-01-14'), ('full_paper', '2027-01-21'),
                          ('camera_ready', '2027-04-30')]:
            deadline = deadlines[kind]
            self.assertEqual(deadline['datetime'][:10], day)
            self.assertEqual(deadline['confidence'], 'confirmed')
            self.assertEqual(deadline['time_precision'], 'date')
            self.assertNotIn('Proposed', deadline['label'])
            self.assertNotIn('opens_at', deadline)
            self.assertNotIn('open_observed_on', deadline)


if __name__ == '__main__':
    unittest.main()

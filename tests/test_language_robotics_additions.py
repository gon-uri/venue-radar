from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from catalog_metadata import CONFERENCE_FAMILIES_PATH, FAMILIES_PATH, load_mapping, validate_conference_families
from conference_scopes import load_scopes
from rollover_editions import CADENCE_YEARS
from validate import load_conferences, load_icore_rankings, load_ccf_rankings, load_acceptance_rates, SUBMISSION_TYPES


ADDED = {'ACL', 'EMNLP', 'NAACL', 'COLING', 'CoNLL', 'LREC', 'IJCNLP',
         'SIGIR', 'ECIR', 'RecSys', 'WWW', 'COLM', 'ISWC', 'ICRA', 'RSS', 'SMC'}


class LanguageRoboticsAdditionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = load_conferences()
        cls.records = {item['id']: item for item in cls.items if item['series'] in ADDED}
        cls.families = load_mapping(FAMILIES_PATH)
        cls.assignments = load_mapping(CONFERENCE_FAMILIES_PATH)

    def test_approved_series_have_reviewed_source_metadata(self):
        self.assertEqual({item['series'] for item in self.records.values()}, ADDED)
        self.assertGreaterEqual(len(self.records), 22)  # later editions may be added
        scopes = load_scopes()
        for series in ADDED:
            self.assertEqual(scopes[series]['scope_last_checked'], '2026-10-07')
        for item in self.records.values():
            self.assertLessEqual(len(item['topics']), 4)
            self.assertTrue(item['source_urls'])
            self.assertTrue(all(d['source_url'] for d in item['deadlines']))

    def test_central_families_are_complete_and_distinct_from_method_tags(self):
        self.assertEqual(validate_conference_families(self.items, self.assignments, self.families), [])
        self.assertEqual(self.assignments['MICCAI'], ['healthcare'])
        self.assertNotIn('ml-ai', self.assignments['L4DC'])
        self.assertIn('language-agents-retrieval', self.assignments['AAMAS'])
        self.assertEqual(self.assignments['ICRA'], ['rl-control'])
        invalid = deepcopy(self.assignments)
        for value in [[], ['unknown'], ['ml-ai', 'ml-ai'], None]:
            invalid['ACL'] = value
            self.assertTrue(validate_conference_families(self.items, invalid, self.families))
        invalid = deepcopy(self.assignments)
        invalid['Untracked'] = ['ml-ai']
        self.assertTrue(validate_conference_families(self.items, invalid, self.families))
        self.assertEqual(validate_conference_families(self.items, invalid, self.families, allow_extra=True), [])
        self.assertTrue(validate_conference_families(self.items, self.assignments, {'families': None}))

    def test_irregular_editions_do_not_acquire_annual_rollover(self):
        self.assertEqual(CADENCE_YEARS['LREC'], 2)
        self.assertIn('lrec-2028', self.records)
        self.assertNotIn('lrec-2027', self.records)
        for series in ['NAACL', 'COLING', 'IJCNLP']:
            self.assertNotIn(series, CADENCE_YEARS)

    def test_proposed_and_proxy_dates_are_not_confirmed(self):
        sigir = self.records['sigir-2027']
        self.assertEqual(sigir['confidence'], 'confirmed')
        self.assertTrue(all(d['confidence'] == 'estimated' for d in sigir['deadlines']))
        for key in ['colm-2027', 'conll-2027', 'iswc-2027', 'lrec-2028', 'smc-2027']:
            self.assertEqual(self.records[key]['confidence'], 'estimated')
        self.assertTrue(all(d['confidence'] == 'estimated' for d in self.records['recsys-2027']['deadlines']))

    def test_arr_and_rss_routes_preserve_eligibility_gates(self):
        for key in ['naacl-2027', 'coling-2027']:
            deadlines = self.records[key]['deadlines']
            commitment = next(d for d in deadlines if 'commit' in d['label'].lower())
            self.assertNotIn(commitment['type'], SUBMISSION_TYPES)
        rss = {d['type']: d for d in self.records['rss-2027']['deadlines']}
        self.assertEqual(rss['extended_abstract']['gate_for'], 'full_paper')
        self.assertEqual(rss['extended_abstract']['datetime'][:10], '2026-12-04')
        self.assertEqual(rss['full_paper']['datetime'][:10], '2027-04-16')
        self.assertIn('resource_paper', SUBMISSION_TYPES)
        ecir = {d['type']: d for d in self.records['ecir-2027']['deadlines']}
        self.assertNotIn('gate_for', ecir['resource_paper'])
        self.assertEqual(ecir['resource_paper']['datetime'][:10], '2026-11-02')

    def test_ranks_and_rates_use_direct_identity_and_evidence(self):
        icore = load_icore_rankings()['rankings']
        ccf = load_ccf_rankings()['rankings']
        rates = load_acceptance_rates()['rates']
        self.assertEqual(ADDED & set(icore), ADDED - {'COLM', 'RSS'})
        self.assertEqual(ADDED & set(ccf), ADDED - {'COLM', 'RSS', 'LREC', 'IJCNLP'})
        self.assertEqual(icore['ISWC']['portal_id'], 1338)
        self.assertIn('Semantic Web', self.records['iswc-2026']['title'])
        self.assertEqual(ADDED & set(rates), {'ACL', 'EMNLP', 'NAACL', 'RecSys'})
        self.assertEqual(rates['ACL']['percent'], 20.3)
        self.assertTrue(rates['NAACL']['approximate'])


if __name__ == '__main__':
    unittest.main()

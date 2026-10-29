from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from build_ics import _deadline_event
from catalog_metadata import CITIES_PATH, CONFERENCE_FAMILIES_PATH, FAMILIES_PATH, load_mapping, map_events
from conference_scopes import load_scopes
from export_catalog import catalog_payload
from maintenance_report import review_queue
from rollover_editions import CADENCE_YEARS, rollover_candidates
from validate import SUBMISSION_TYPES, load_conferences, load_icore_rankings


ADDED = {'COMPLEX NETWORKS', 'CompleNet', 'ALIFE', 'NODYCON', 'NICE', 'SAB',
         'BCI Winter', 'IEEE BioCAS', 'ICCN', 'AREADNE', 'SfN Neuroscience',
         'Dynamics Days Europe', 'Dynamics Days US', 'Dynamics Days LAC',
         'Dynamics Days Asia-Pacific', 'Dynamics Days CAC'}


class DynamicsNeuroscienceAdditionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = {c['id']: c for c in load_conferences() if c['series'] in ADDED}

    def test_all_sixteen_series_have_reviewed_metadata_and_scope(self):
        self.assertEqual({c['series'] for c in self.records.values()}, ADDED)
        self.assertEqual(len(self.records), 22)
        scopes = load_scopes()
        for c in self.records.values():
            self.assertGreaterEqual(c['last_checked'], '2026-10-08')
            self.assertTrue(c['source_urls'])
            self.assertLessEqual(len(c['topics']), 4)
            self.assertTrue(all(d['source_url'] for d in c['deadlines']))
            self.assertEqual(scopes[c['series']]['scope_last_checked'], '2026-10-08')

    def test_eight_families_keep_their_ids_names_and_order(self):
        families = load_mapping(FAMILIES_PATH)['families']
        self.assertEqual([(f['id'], f['label']) for f in families], [
            ('ml-ai', 'ML & Data Science'),
            ('language-agents-retrieval', 'NLP, Agents & Retrieval'),
            ('signals-vision', 'Vision & Multimedia'),
            ('rl-control', 'RL, Robotics & Control'),
            ('dynamics-control', 'Complex Systems, Time Series & Signals'),
            ('healthcare', 'Healthcare & Biometrics'),
            ('neuroscience', 'Neuroscience & Neurotechnology'),
            ('responsible-ai', 'Responsible & Trustworthy AI'),
        ])
        assignments = load_mapping(CONFERENCE_FAMILIES_PATH)
        self.assertEqual(assignments['SfN Neuroscience'], ['neuroscience'])
        self.assertEqual(assignments['CompleNet'], ['dynamics-control'])
        self.assertEqual(assignments['IEEE BioCAS'], ['healthcare', 'neuroscience'])
        leaves = {t: f['id'] for f in families for t in f['topics']}
        self.assertEqual(leaves['Artificial Life & Adaptive Systems'], 'dynamics-control')
        self.assertEqual(leaves['Systems & Experimental Neuroscience'], 'neuroscience')
        self.assertEqual(leaves['Neuromorphic & Brain-inspired Computing'], 'neuroscience')

    def test_abstract_contributions_use_existing_submission_types(self):
        for key in ['areadne-2028', 'sfn-neuroscience-2027', 'dynamics-days-europe-2027',
                    'dynamics-days-us-2027', 'dynamics-days-lac-2026', 'dynamics-days-cac-2026']:
            submissions = [d for d in self.records[key]['deadlines'] if d['type'] in SUBMISSION_TYPES]
            self.assertEqual(len(submissions), 1)
            self.assertEqual(submissions[0]['type'], 'abstract')
            self.assertIn('abstract', submissions[0]['label'].lower())
        nodycon = self.records['nodycon-2026']
        manuscript = next(d for d in nodycon['deadlines'] if d['type'] == 'journal_manuscript')
        self.assertNotIn(manuscript['type'], SUBMISSION_TYPES)

    def test_independent_abstract_routes_do_not_gate_full_papers(self):
        for key in ['complex-networks-2026', 'complenet-2027', 'nice-2027', 'sab-2026']:
            self.assertTrue(all('gate_for' not in d for d in self.records[key]['deadlines']))
        bio = self.records['ieee-biocas-2027']['deadlines'][0]
        self.assertEqual(bio['type'], 'abstract')
        self.assertNotIn('gate_for', bio)
        self.assertEqual(bio['datetime'][:10], '2027-05-07')

    def test_confirmed_meetings_do_not_confirm_proxy_deadlines(self):
        for key in ['alife-2027', 'areadne-2028', 'sfn-neuroscience-2027']:
            c = self.records[key]
            self.assertEqual(c['confidence'], 'confirmed')
            self.assertTrue(all(d['confidence'] == 'estimated' for d in c['deadlines']))
        for key in ['sab-2028', 'dynamics-days-europe-2027', 'iccn-2026']:
            self.assertEqual(self.records[key]['confidence'], 'estimated')
        self.assertFalse(self.records['iccn-2026']['deadlines'])
        self.assertIn('October 27-30', self.records['iccn-2026']['notes'])

    def test_cadence_and_unknown_next_editions_remain_honest(self):
        for series in ['AREADNE', 'SAB', 'Dynamics Days LAC']:
            self.assertEqual(CADENCE_YEARS[series], 2)
        for series in ['NODYCON', 'ICCN', 'Dynamics Days Asia-Pacific', 'Dynamics Days CAC']:
            self.assertNotIn(series, CADENCE_YEARS)
        drafts = rollover_candidates(list(self.records.values()), date(2026, 10, 8))
        self.assertEqual(drafts, [])
        queued = {r[1]: r[2] for r in review_queue(list(self.records.values()), date(2026, 10, 8), 30)}
        for key in ['nodycon-2026', 'dynamics-days-asia-pacific-2024', 'dynamics-days-cac-2026']:
            self.assertIn('next edition not tracked', queued[key])
        self.assertIn('no submission deadline recorded', queued['iccn-2026'])

    def test_date_only_exports_and_confirmed_map_locations(self):
        lac = self.records['dynamics-days-lac-2026']
        event = _deadline_event(lac, lac['deadlines'][0])
        self.assertIn('DTSTART;VALUE=DATE:20261010', event)
        self.assertTrue(any('cutoff time unannounced' in line for line in event))
        cities = load_mapping(CITIES_PATH)
        mapped = {e['id']: e['city'] for e in map_events(list(self.records.values()), cities)}
        self.assertEqual(mapped['complenet-2027'], 'rochester-new-york')
        self.assertEqual(mapped['dynamics-days-us-2027'], 'san-diego')
        self.assertNotIn('iccn-2026', mapped)
        self.assertEqual(mapped['areadne-2028'], 'milos')
        self.assertNotIn('sab-2028', mapped)
        us = self.records['dynamics-days-us-2027']
        self.assertEqual(us['conference_start'], '2027-01-04')
        self.assertEqual(us['deadlines'][0]['datetime'][:10], '2026-11-22')

    def test_workbook_coverage_and_no_other_series_rank_inheritance(self):
        payload = catalog_payload()
        self.assertTrue(ADDED <= {r[0] for r in payload['rows']})
        self.assertTrue(ADDED <= {r[0] for r in payload['scopes']})
        self.assertFalse(ADDED & set(load_icore_rankings()['rankings']))
        self.assertIn('International Conference on Artificial Life', self.records['alife-2027']['title'])
        self.assertNotIn('IEEE International Symposium', self.records['alife-2027']['title'])


if __name__ == '__main__':
    unittest.main()

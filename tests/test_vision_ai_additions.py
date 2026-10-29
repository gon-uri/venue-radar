from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from build_ics import _deadline_event
from catalog_metadata import CITIES_PATH, FAMILIES_PATH, load_mapping, map_events
from conference_scopes import load_scopes
from export_catalog import catalog_payload
from rollover_editions import CADENCE_YEARS, rollover_candidates
from validate import load_acceptance_rates, load_ccf_rankings, load_conferences, load_controlled_topics, load_icore_rankings


ADDED = {'EuroGP', 'KR', 'ICAPS', '3DV', 'ACM MM', 'ACM SIGGRAPH', 'BMVC',
         'CVPR', 'ECCV', 'EUVIP', 'FG', 'ICCV', 'ICMR', 'IJCB', 'WACV'}


class VisionAIAdditionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = {item['id']: item for item in load_conferences() if item['series'] in ADDED}
        cls.scopes = load_scopes()

    def test_all_requested_series_have_future_editions_and_reviewed_scope(self):
        self.assertEqual({item['series'] for item in self.records.values()}, ADDED)
        for series in ADDED:
            editions = [item for item in self.records.values() if item['series'] == series]
            self.assertTrue(any(date.fromisoformat(item['conference_end']) >= date(2026, 10, 7) for item in editions))
            self.assertIn(series, self.scopes)
            self.assertEqual(self.scopes[series]['scope_last_checked'], '2026-10-07')
            for item in editions:
                self.assertLessEqual(len(item['topics']), 4)
                self.assertTrue(item['source_urls'])
                self.assertTrue(all(d['source_url'] for d in item['deadlines']))

    def test_dedicated_biometrics_are_not_duplicate_predecessor_series(self):
        for series in ['FG', 'IJCB']:
            self.assertIn('Biometrics & Human Sensing', self.records[f'{series.lower()}-2027']['topics'])
        self.assertNotIn('BTAS', {item['series'] for item in load_conferences()})
        self.assertNotIn('ICB', {item['series'] for item in load_conferences()})

    def test_fg_extensions_and_ijcb_opening_are_current_official_evidence(self):
        fg = {d['type']: d for d in self.records['fg-2027']['deadlines']}
        self.assertEqual(fg['abstract']['datetime'][:10], '2026-10-23')
        self.assertEqual(fg['full_paper']['datetime'][:10], '2026-10-30')
        self.assertEqual(fg['abstract']['gate_for'], 'full_paper')
        ijcb = next(d for d in self.records['ijcb-2027']['deadlines'] if d['type'] == 'full_paper')
        self.assertEqual(ijcb['datetime'], '2027-04-09T23:59:00-12:00')
        self.assertEqual(ijcb['opens_at'], '2027-03-15T23:59:00-12:00')

    def test_focused_new_leaves_remain_in_eight_families(self):
        families = load_mapping(FAMILIES_PATH)['families']
        self.assertEqual(len(families), 8)
        by_topic = {topic: family['id'] for family in families for topic in family['topics']}
        self.assertEqual(by_topic['Knowledge Representation & Reasoning'], 'ml-ai')
        self.assertEqual(by_topic['Planning & Search'], 'rl-control')
        self.assertEqual(by_topic['Biometrics & Human Sensing'], 'healthcare')
        for topic in ['Computer Graphics & Visualization', 'Multimedia Learning & Retrieval']:
            self.assertEqual(by_topic[topic], 'signals-vision')

    def test_biennial_vision_cadence_and_estimated_next_editions(self):
        self.assertNotIn('eccv-2027', self.records)
        for series in ADDED:
            self.assertEqual(CADENCE_YEARS[series], 2 if series in {'ECCV', 'ICCV'} else 1)
        future = rollover_candidates([self.records['eccv-2026']], date(2026, 10, 7))
        self.assertEqual(future[0]['year'], 2028)
        for key in ['acm-mm-2027', 'eccv-2028', 'euvip-2027']:
            item = self.records[key]
            self.assertEqual(item['confidence'], 'estimated')
            self.assertTrue(all(d['confidence'] == 'estimated' for d in item['deadlines']))

    def test_confirmed_meetings_do_not_confirm_proxy_paper_deadlines(self):
        for key in ['iccv-2027']:
            item = self.records[key]
            self.assertEqual(item['confidence'], 'confirmed')
            self.assertTrue(all(d['confidence'] == 'estimated' for d in item['deadlines']))
        self.assertIn('conflicts', self.records['iccv-2027']['notes'])

    def test_wacv_routes_have_independent_gates_and_post_acceptance_steps(self):
        deadlines = {d['type']: d for d in self.records['wacv-2027']['deadlines']}
        self.assertEqual(deadlines['abstract']['gate_for'], 'full_paper')
        self.assertEqual(deadlines['late_abstract']['gate_for'], 'regular_paper')
        self.assertEqual(deadlines['regular_paper']['datetime'][:10], '2026-08-28')
        self.assertEqual(deadlines['camera_ready']['datetime'][:10], '2026-11-02')
        self.assertEqual(deadlines['camera_ready']['type'], 'camera_ready')

    def test_date_only_cutoffs_export_all_day(self):
        for key in ['eurogp-2027', 'acm-mm-2026']:
            item = self.records[key]
            for deadline in item['deadlines']:
                self.assertEqual(deadline['time_precision'], 'date')
                self.assertTrue(any(line.startswith('DTSTART;VALUE=DATE:') for line in _deadline_event(item, deadline)))

    def test_only_confirmed_meetings_with_city_aliases_reach_map(self):
        events = map_events(list(self.records.values()), load_mapping(CITIES_PATH))
        expected = {key for key, item in self.records.items() if item['confidence'] == 'confirmed'}
        self.assertEqual({event['id'] for event in events}, expected)
        self.assertNotIn('acm-mm-2027', {event['id'] for event in events})

    def test_ranks_have_direct_coverage_and_unknowns_are_preserved(self):
        icore = load_icore_rankings()['rankings']
        ccf = load_ccf_rankings()['rankings']
        self.assertEqual({s for s in ADDED if s in icore}, ADDED - {'3DV', 'EUVIP'})
        self.assertEqual({s for s in ADDED if s in ccf}, ADDED - {'EuroGP', 'EUVIP', 'WACV'})
        self.assertEqual(ccf['3DV'], {'rank': 'C', 'page': 49})
        self.assertEqual(icore['ACM SIGGRAPH']['portal_id'], 38)
        self.assertEqual(ccf['IJCB'], {'rank': 'C', 'page': 60})

    def test_acceptance_evidence_is_track_specific_not_rank_inference(self):
        rates = load_acceptance_rates()['rates']
        self.assertEqual({s for s in ADDED if s in rates}, {'CVPR', 'ECCV', 'ICAPS', 'ICCV', 'WACV'})
        self.assertEqual(rates['WACV']['year'], 2026)
        self.assertIn('both rounds', rates['WACV']['track'])
        self.assertNotIn('FG', rates)

    def test_workbook_payload_contains_all_additions_and_curated_profiles(self):
        payload = catalog_payload()
        self.assertTrue(ADDED <= {row[0] for row in payload['rows']})
        self.assertTrue(ADDED <= {row[0] for row in payload['scopes']})
        # One row per tracked series, controlled leaf and reviewed profile.
        self.assertEqual(len(payload['rows']), len({c['series'] for c in load_conferences()}))
        self.assertEqual(len(payload['topics']), len(load_controlled_topics()))
        self.assertEqual(len(payload['scopes']), len(load_scopes()))


if __name__ == '__main__':
    unittest.main()

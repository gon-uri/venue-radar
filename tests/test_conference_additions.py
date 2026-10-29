from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from build_ics import _deadline_event
from catalog_metadata import CITIES_PATH, FAMILIES_PATH, load_mapping, map_events
from rollover_editions import CADENCE_YEARS, rollover_candidates
from validate import load_conferences, load_ccf_rankings, load_icore_rankings


ADDED = {'AutoML', 'LoG', 'CoRL', 'GECCO', 'SaTML', 'ProbML', 'AAMAS',
         'MLSys', 'CogSci', 'ICIP', 'Interspeech'}


class ConferenceAdditionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.additions = {item['series']: item for item in load_conferences()
                         if item['series'] in ADDED}

    def test_all_approved_series_have_relevant_editions_and_sources(self):
        self.assertEqual(set(self.additions), ADDED)
        for item in self.additions.values():
            self.assertGreaterEqual(date.fromisoformat(item['conference_end']), date(2026, 10, 7))
            self.assertGreaterEqual(item['last_checked'], '2026-10-07')
            self.assertIn(item['website'], item['source_urls'])
            self.assertTrue(all(deadline.get('source_url') for deadline in item['deadlines']))

    def test_meeting_and_deadline_confidence_remain_independent(self):
        for series in ['AutoML', 'ProbML']:
            item = self.additions[series]
            self.assertEqual(item['confidence'], 'estimated')
            self.assertEqual(item['location'], 'To be announced')
            self.assertTrue(all(d['confidence'] == 'estimated' for d in item['deadlines']))
        for series in ['CogSci']:
            item = self.additions[series]
            self.assertEqual(item['confidence'], 'confirmed')
            self.assertTrue(all(d['confidence'] == 'estimated' for d in item['deadlines']))

    def test_new_topics_are_central_leaves_in_existing_families(self):
        families = load_mapping(FAMILIES_PATH)['families']
        by_topic = {topic: family['id'] for family in families for topic in family['topics']}
        for series, topic, family in [
            ('GECCO', 'Evolutionary Computation & Optimization', 'ml-ai'),
            ('CogSci', 'Cognitive Science & Computational Cognition', 'neuroscience'),
            ('MLSys', 'ML Systems & Infrastructure', 'ml-ai'),
        ]:
            self.assertIn(topic, self.additions[series]['topics'])
            self.assertEqual(by_topic[topic], family)

    def test_confirmed_locations_have_map_aliases_but_estimates_do_not(self):
        events = map_events(list(self.additions.values()), load_mapping(CITIES_PATH))
        self.assertEqual({event['id'] for event in events}, {
            item['id'] for series, item in self.additions.items()
            if series not in {'AutoML', 'ProbML'}
        })

    def test_direct_ranking_matches_do_not_inherit_other_venues(self):
        icore = load_icore_rankings()['rankings']
        ccf = load_ccf_rankings()['rankings']
        self.assertEqual({s: icore[s]['rank'] for s in ADDED if s in icore}, {
            'AAMAS': 'A', 'GECCO': 'A', 'Interspeech': 'A', 'CogSci': 'B', 'ICIP': 'B',
        })
        self.assertEqual({s: ccf[s]['rank'] for s in ADDED if s in ccf}, {
            'AAMAS': 'B', 'CogSci': 'B', 'GECCO': 'C', 'ICIP': 'C',
        })

    def test_aamas_tracks_have_independent_prerequisites(self):
        deadlines = {d['type']: d for d in self.additions['AAMAS']['deadlines']}
        self.assertEqual(deadlines['abstract']['gate_for'], 'full_paper')
        self.assertEqual(deadlines['late_abstract']['gate_for'], 'short_paper')
        self.assertEqual(deadlines['abstract']['datetime'][:10], '2026-10-01')
        self.assertEqual(deadlines['late_abstract']['datetime'][:10], '2026-11-05')

    def test_date_only_papers_export_all_day(self):
        for series in ['ICIP', 'Interspeech']:
            item = self.additions[series]
            paper = next(d for d in item['deadlines'] if d['type'] == 'full_paper')
            self.assertEqual(paper['time_precision'], 'date')
            self.assertTrue(any(line.startswith('DTSTART;VALUE=DATE:')
                                for line in _deadline_event(item, paper)))

    def test_annual_rollover_is_explicit_and_clears_known_locations(self):
        for series, previous in self.additions.items():
            self.assertEqual(CADENCE_YEARS[series], 1)
            future = rollover_candidates([previous], date(previous['year'] + 1, 1, 1))
            self.assertEqual(len(future), 1)
            self.assertEqual(future[0]['year'], previous['year'] + 1)
            self.assertEqual(future[0]['confidence'], 'estimated')
            self.assertEqual(future[0]['location'], 'To be announced')


if __name__ == '__main__':
    unittest.main()

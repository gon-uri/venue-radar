from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from build_ics import _conference_event, _deadline_event
from build_site import _milestones
from catalog_metadata import CITIES_PATH, FAMILIES_PATH, load_mapping, map_events, validate_catalog_metadata
from rollover_editions import rollover_candidates
from validate import load_conferences, load_controlled_topics, validate_conferences


class CatalogMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conferences = load_conferences()
        cls.topics = load_controlled_topics()
        cls.families = load_mapping(FAMILIES_PATH)
        cls.cities = load_mapping(CITIES_PATH)

    def test_controlled_topics_have_exactly_one_family(self):
        self.assertEqual(len(self.families['families']), 8)
        self.assertEqual(validate_catalog_metadata(self.topics, self.families, self.cities), [])
        duplicate = deepcopy(self.families)
        duplicate['families'][1]['topics'].append(duplicate['families'][0]['topics'][0])
        self.assertTrue(validate_catalog_metadata(self.topics, duplicate, self.cities))

    def test_city_aliases_and_coordinates_are_validated(self):
        cities = deepcopy(self.cities)
        key = next(iter(cities))
        cities[key]['lat'] = 100
        cities['duplicate'] = deepcopy(cities[key])
        errors = validate_catalog_metadata(self.topics, self.families, cities)
        self.assertTrue(any('invalid lat' in error for error in errors))
        self.assertTrue(any('duplicate location alias' in error for error in errors))

    def test_malformed_registry_reports_validation_errors(self):
        self.assertTrue(validate_catalog_metadata(self.topics, {'families': None}, self.cities))
        self.assertTrue(validate_catalog_metadata(self.topics, self.families, {'invalid': None}))
        malformed = deepcopy(self.families)
        malformed['labels'] = None
        self.assertTrue(validate_catalog_metadata(self.topics, malformed, self.cities))

    def test_map_excludes_estimates_online_and_unmapped_locations(self):
        baseline = next(item for item in self.conferences if item['id'] == 'l4dc-2027')
        eligible = deepcopy(baseline)
        eligible['confidence'] = 'announced_no_deadlines'
        excluded = []
        for field, value in [('confidence', 'estimated'), ('mode', 'online'), ('location', 'To be announced')]:
            item = deepcopy(baseline)
            item[field] = value
            excluded.append(item)
        events = map_events([eligible, *excluded], self.cities)
        self.assertEqual([event['id'] for event in events], ['l4dc-2027'])
        self.assertEqual(events[0]['city'], 'stockholm')

    def test_size_vocabulary_and_four_topic_limit(self):
        item = deepcopy(self.conferences[0])
        item['size'] = 'S/M'
        self.assertTrue(validate_conferences([item], self.topics))
        item['size'] = 'M'
        item['topics'] = list(self.topics)[:5]
        self.assertTrue(validate_conferences([item], self.topics))

    def test_review_days_cannot_be_in_the_future(self):
        item = deepcopy(next(item for item in self.conferences if item['id'] == 'l4dc-2027'))
        limit = date(2026, 10, 31)
        item['last_checked'] = '2026-10-31'
        self.assertEqual(validate_conferences([item], self.topics, review_limit=limit), [])
        item['last_checked'] = '2026-11-01'
        item['deadlines'][0]['open_observed_on'] = '2026-11-01'
        errors = validate_conferences([item], self.topics, review_limit=limit)
        self.assertIn('l4dc-2027: last_checked 2026-11-01 is in the future', errors)
        self.assertTrue(any('open_observed_on is in the future' in error for error in errors), errors)

    def test_date_only_cutoff_is_all_day_but_uid_stays_stable(self):
        item = next(item for item in self.conferences if item['id'] == 'l4dc-2027')
        deadline = deepcopy(item['deadlines'][0])
        deadline['time_precision'] = 'date'
        deadline['confidence'] = 'confirmed'
        all_day = _deadline_event(item, deadline)
        exact = deepcopy(deadline)
        exact['time_precision'] = 'exact'
        self.assertEqual(
            next(line for line in all_day if line.startswith('UID:')),
            next(line for line in _deadline_event(item, exact) if line.startswith('UID:')),
        )
        self.assertTrue(any(line.startswith('DTSTART;VALUE=DATE:') for line in all_day))
        self.assertFalse(any(line.startswith('DTSTART:') for line in all_day))
        self.assertTrue(any('cutoff time unannounced' in line for line in all_day))
        sample = deepcopy(item)
        sample['deadlines'] = [deadline]
        milestone = next(m for m in _milestones(sample) if m['type'] == deadline['type'])
        self.assertTrue(milestone['approximate_time'])
        self.assertFalse(milestone['estimated'])

    def test_repository_rename_preserves_published_uid_namespace(self):
        item = next(item for item in self.conferences if item['id'] == 'l4dc-2027')
        self.assertIn('UID:l4dc-2027-conference@scientific-conference-calendar',
                      _conference_event(item))
        for deadline in item['deadlines']:
            uid = next(line for line in _deadline_event(item, deadline)
                       if line.startswith('UID:'))
            self.assertTrue(uid.endswith('@scientific-conference-calendar'))

    def test_triennial_rollover_does_not_invent_annual_sysid(self):
        previous = deepcopy(next(item for item in self.conferences if item['id'] == 'ifac-sysid-2027'))
        projected = rollover_candidates([previous], date(2027, 7, 10))
        self.assertEqual([item['year'] for item in projected], [2030])
        self.assertEqual(projected[0]['confidence'], 'estimated')
        self.assertEqual(projected[0]['location'], 'To be announced')


if __name__ == '__main__':
    unittest.main()

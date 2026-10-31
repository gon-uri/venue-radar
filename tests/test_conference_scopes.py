from copy import deepcopy
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from build_ics import _conference_event, _description, _escape_text, _topic_groups
from build_site import _conference_rows, _deadline_group_rows, _search_text, _topic_labels
from conference_scopes import all_topics, load_scopes, scope_review_queue, validate_scopes, with_scopes
from export_catalog import catalog_payload
from validate import load_conferences, load_controlled_topics, stable_slug


class RowParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.rows = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == 'tr' and 'data-filter-row' in attributes:
            self.rows.append(attributes)


class ConferenceScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = load_conferences()
        cls.profiles = load_scopes()
        cls.topics = load_controlled_topics()
        cls.enriched = with_scopes(cls.raw, cls.profiles)
        cls.automl = next(item for item in cls.enriched if item['series'] == 'AutoML')

    def test_curated_catalog_profiles_are_valid(self):
        self.assertEqual(validate_scopes(self.raw, self.profiles, self.topics), [])
        self.assertTrue(all(len(profile['additional_topics']) <= 6 for profile in self.profiles.values()))
        self.assertEqual(self.profiles['ICIP']['additional_topics'], [])
        # Broad CFP applications do not automatically become specialist tags.
        self.assertNotIn('Healthcare & Clinical AI', all_topics(next(item for item in self.enriched if item['series'] == 'NeurIPS')))

    def test_schema_rejects_uncontrolled_duplicate_and_excessive_topics(self):
        for extra in [['invented'], ['Machine Learning', 'Machine Learning'], list(self.topics)[:7], None, [42]]:
            profile = deepcopy(self.profiles['AutoML'])
            profile['additional_topics'] = extra
            self.assertTrue(validate_scopes(self.raw, {'AutoML': profile}, self.topics))

    def test_schema_requires_summary_source_edition_and_review_date(self):
        for field, value in [('scope_summary', ''), ('scope_summary', 'x' * 1201),
                             ('scope_source_urls', []), ('scope_source_urls', ['javascript:alert(1)']),
                             ('scope_source_urls', ['https://[']),
                             ('scope_last_checked', 'not a date'), ('source_year', True)]:
            profile = deepcopy(self.profiles['AutoML'])
            profile[field] = value
            self.assertTrue(validate_scopes(self.raw, {'AutoML': profile}, self.topics))
        self.assertTrue(validate_scopes(self.raw, {'unknown': self.profiles['AutoML']}, self.topics))
        self.assertTrue(validate_scopes(self.raw, {'AutoML': None}, self.topics))
        self.assertTrue(validate_scopes(self.raw, [], self.topics))
        profile = deepcopy(self.profiles['AutoML'])
        del profile['scope_source_urls']
        self.assertTrue(validate_scopes(self.raw, {'AutoML': profile}, self.topics))

    def test_primary_display_and_canonical_editions_are_unchanged(self):
        raw = deepcopy(self.raw)
        enriched = with_scopes(raw, self.profiles)
        self.assertEqual(raw, self.raw)
        for original, item in zip(raw, enriched):
            self.assertEqual({key: value for key, value in item.items() if key != 'scope'}, original)
            self.assertEqual(_topic_labels(item['topics']).count('class="tag"'), len(original['topics']))
        missing = with_scopes([raw[0]], {})[0]
        self.assertEqual(all_topics(missing), raw[0]['topics'])
        self.assertEqual(_search_text(missing), _search_text(raw[0]))

    def test_extended_topics_and_summary_are_searchable_in_both_tables(self):
        self.assertIn('bayesian optimization', _search_text(self.automl).lower())
        topic = 'Probabilistic, Causal & Uncertainty ML'
        self.assertNotIn(topic, self.automl['topics'])
        for render in [_conference_rows, _deadline_group_rows]:
            html = render([self.automl], {}, {}, 'https://example.org', {})
            row = RowParser(html).rows[0]
            self.assertIn(stable_slug(topic), row['data-topics'].split())
            self.assertIn('bayesian optimization', row['data-search'].lower())
            self.assertNotIn('>Probabilistic, Causal &amp; Uncertainty ML</span>', html)
        duplicate = deepcopy(self.automl)
        duplicate['scope']['additional_topics'].append(duplicate['topics'][0])
        self.assertEqual(len(all_topics(duplicate)), len(set(all_topics(duplicate))))

    def test_topic_calendars_share_extended_matching_and_keep_uids(self):
        groups = _topic_groups([self.automl])
        self.assertIn(self.automl, groups['probabilistic-causal-uncertainty-ml']['conferences'])
        plain = next(item for item in self.raw if item['series'] == 'AutoML')
        uid = lambda item: next(line for line in _conference_event(item) if line.startswith('UID:'))
        self.assertEqual(uid(plain), uid(self.automl))
        # ADR-044: profiles widen topic-feed matching, but their prose and
        # evidence stay on the site rather than in every calendar event.
        description = _description(self.automl, 'https://example.org', True)
        self.assertNotIn('Scope', description)
        self.assertNotIn('Additional topics', description)
        unfolded = '\r\n'.join(_conference_event(self.automl)).replace('\r\n ', '').split('\r\n')
        categories = next(line for line in unfolded if line.startswith('CATEGORIES:'))
        self.assertEqual(categories, 'CATEGORIES:' + ','.join(_escape_text(t) for t in self.automl['topics']),
                         'CATEGORIES carry the four display topics, not the scope union')

    def test_maintenance_reports_missing_stale_and_prior_edition_profiles(self):
        profile = deepcopy(self.profiles['AutoML'])
        profile['scope_last_checked'] = '2026-08-01'
        rows = scope_review_queue([self.automl], {'AutoML': profile}, date(2026, 10, 7), 30)
        self.assertIn('67 days ago', rows[0][1])
        self.assertIn('based on 2026; check 2027 CFP', rows[0][1])
        missing = scope_review_queue([self.automl], {}, date(2026, 10, 7), 30)
        self.assertEqual(missing[0][1], 'no reviewed scope profile')
        profile['source_year'] = 2027
        profile['scope_last_checked'] = '2026-10-07'
        self.assertEqual(scope_review_queue([self.automl], {'AutoML': profile}, date(2026, 10, 7), 30), [])

    def test_workbook_export_keeps_primary_topics_and_separate_scope_rows(self):
        payload = catalog_payload()
        self.assertEqual(len(payload['scopes']), len(self.profiles))
        row = next(row for row in payload['rows'] if row[0] == 'AutoML')
        self.assertEqual(row[1], '; '.join(self.automl['topics']))
        scope = next(row for row in payload['scopes'] if row[0] == 'AutoML')
        self.assertEqual(scope[1], '; '.join(self.profiles['AutoML']['additional_topics']))
        self.assertEqual(scope[-1], '2026-10-07')


if __name__ == '__main__':
    unittest.main()

import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from archival_options import load_archival_options
from catalog_metadata import CITIES_PATH, load_mapping, map_events
from validate import SUBMISSION_TYPES, load_conferences


class MidNovemberReviewTests(unittest.TestCase):
    """Facts verified against official pages on 2026-11-14 (draft + independent check)."""

    @classmethod
    def setUpClass(cls):
        cls.records = {item['id']: item for item in load_conferences()}
        cls.archival = load_archival_options()

    def deadline(self, edition, kind):
        return next(d for d in self.records[edition]['deadlines'] if d['type'] == kind)

    def test_extensions_replace_the_original_cutoffs(self):
        esann = self.deadline('esann-2027', 'full_paper')
        self.assertEqual(esann['datetime'], '2026-11-25T23:59:00+01:00')
        self.assertEqual(esann['time_precision'], 'date')
        cec = self.deadline('ieee-cec-2027', 'special_session_proposal')
        self.assertEqual(cec['datetime'], '2026-11-29T23:59:00-12:00')
        self.assertNotIn('cutoff_note', cec, 'the revised CFP removed the Nov 15 vs Nov 29 conflict')

    def test_newly_confirmed_meetings_keep_their_proxy_deadlines_estimated(self):
        for edition, start, location in [('acm-mm-2027', '2027-11-08', 'Hong Kong, China'),
                                         ('iswc-2027', '2027-10-24', 'Montevideo, Uruguay')]:
            item = self.records[edition]
            self.assertEqual((item['confidence'], item['conference_start'], item['location']),
                             ('confirmed', start, location))
            self.assertTrue(all(d['confidence'] == 'estimated' for d in item['deadlines']), edition)
        icmla = self.records['ieee-icmla-2027']
        self.assertEqual((icmla['conference_start'], icmla['location']), ('2027-12-14', 'Miami, Florida, USA'))
        self.assertEqual(self.deadline('ieee-icmla-2027', 'full_paper').get('confidence', 'confirmed'), 'confirmed')
        mapped = {event['id'] for event in map_events(list(self.records.values()), load_mapping(CITIES_PATH))}
        self.assertTrue({'iswc-2027', 'ieee-icmla-2027', 'acm-mm-2027'} <= mapped)

    def test_new_routes_use_supported_types_only_where_fresh_papers_are_invited(self):
        icip = {d['type']: d for d in self.records['icip-2027']['deadlines']}
        self.assertIn('journal_paper', SUBMISSION_TYPES, 'OJ-SP papers are new journal submissions')
        self.assertIn('8 pages + 1 reference page', icip['journal_paper']['label'])
        biocas = {d['type']: d for d in self.records['ieee-biocas-2027']['deadlines']}
        self.assertEqual(biocas['full_paper']['datetime'], '2027-06-11T23:59:00+02:00')
        self.assertEqual(biocas['abstract']['confidence'], 'estimated', 'SSCS-only date conflicts with the host timeline')
        for edition, kind in [('eusipco-2027', 'special_session_proposal'), ('rldm-2027', 'workshop_proposal'),
                              ('aime-2027', 'tutorial_proposal')]:
            self.assertNotIn(self.deadline(edition, kind)['type'], SUBMISSION_TYPES, 'organizer proposals are schedule-only')

    def test_owner_decisions_of_2026_11_14(self):
        # RLC 2027 has no abstract step (rolling RLJ submissions); its published
        # event is retired rather than silently dropped.
        rlc = {d['type'] for d in self.records['rlc-2027']['deadlines']}
        self.assertEqual(rlc, {'full_paper', 'notification'})
        retired = yaml.safe_load((ROOT / 'data' / 'retired_identities.yml').read_text(encoding='utf-8'))
        self.assertIn('rlc-2027-deadline-abstract@scientific-conference-calendar', {item['id'] for item in retired})
        # A call that declares its own proceedings non-archival settles No, even
        # though it publishes them (CogSci 2027).
        cogsci = self.archival['CogSci']
        self.assertEqual((cogsci['archival'], cogsci['source_year'], cogsci['estimated']), ('no', 2027, False))
        self.assertIn('not considered archival', cogsci['note'])
        for series in ('ICML', 'IEEE EMBC', 'RLC', 'ICIP', 'IEEE ICMLA'):
            self.assertEqual((self.archival[series]['source_year'], self.archival[series]['checked']),
                             (2027, '2026-11-14'), series)

if __name__ == '__main__':
    unittest.main()

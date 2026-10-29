from pathlib import Path
import re
import subprocess
import sys
import unittest
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from catalog_metadata import FAMILIES_PATH, load_mapping, validate_conference_families
from conference_scopes import validate_scopes
from validate import REQUIRED_FIELDS, SUBMISSION_TYPES, VALID_CONFIDENCE, load_conferences, load_controlled_topics, validate_conferences


def yaml_examples(name):
    text = (ROOT / 'project_docs' / name).read_text(encoding='utf-8')
    return [yaml.safe_load(block) for block in re.findall(r'```yaml\n(.*?)\n```', text, re.S)]


def heading_anchors(text):
    return {
        re.sub(r'[^\w -]', '', heading.lower()).replace(' ', '-')
        for heading in re.findall(r'^#{1,6} (.+)$', text, re.M)
    }


class DocumentationTests(unittest.TestCase):
    def test_local_documentation_links_and_section_anchors_resolve(self):
        documents = [ROOT / 'AGENTS.md', *sorted((ROOT / 'project_docs').glob('*.md'))]
        for document in documents:
            content = document.read_text(encoding='utf-8')
            for href in re.findall(r'\[[^\]\n]*\]\(([^)\n]+)\)', content):
                url = urlsplit(href.strip('<>'))
                if url.scheme or url.netloc:
                    continue
                target = (document.parent / unquote(url.path)).resolve() if url.path else document
                with self.subTest(document=document.name, href=href):
                    self.assertTrue(target.is_file(), f'Missing link target: {target}')
                    self.assertIn(ROOT, target.parents, 'Maintained links must be repository-local')
                    self.assertNotIn(ROOT / 'private_notes', target.parents,
                                     'Public documentation must not depend on private notes')
                    if url.fragment and target.suffix == '.md':
                        self.assertIn(unquote(url.fragment), heading_anchors(target.read_text(encoding='utf-8')))

    def test_index_routes_to_every_project_document(self):
        index = (ROOT / 'project_docs' / 'README.md').read_text()
        for document in (ROOT / 'project_docs').glob('*.md'):
            if document.name != 'README.md':
                with self.subTest(document=document.name):
                    self.assertIn(f']({document.name})', index)

    def test_agent_entrypoint_includes_workflows_and_full_local_checks(self):
        agents = (ROOT / 'AGENTS.md').read_text()
        for name in ['README', 'implementation_status', 'architecture', 'roadmap',
                     'decisions', 'documentation_policy', 'adding_conferences', 'data_schema',
                     'data_maintenance', 'development', 'conference_scopes', 'topic_audit']:
            self.assertIn(f'project_docs/{name}.md', agents)
        for command in ['python3 scripts/validate.py',
                        'python3 -m unittest discover -s tests -v',
                        'python3 scripts/build_all.py']:
            self.assertIn(command, agents)

    def test_private_notes_are_ignored_without_requiring_files_to_exist(self):
        paths = ['private_notes/README.md', 'private_notes/session_log.md',
                 'private_notes/nested/unfinished-plan.md']
        result = subprocess.run(['git', 'check-ignore', '--no-index', '--stdin'],
                                input='\n'.join(paths) + '\n', text=True,
                                capture_output=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), paths)

    def test_private_notes_are_not_tracked(self):
        result = subprocess.run(['git', 'ls-files', '--', 'private_notes/'],
                                text=True, capture_output=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '', 'Private notes must never be committed')

    def test_field_reference_matches_required_fields_and_supported_types(self):
        schema = (ROOT / 'project_docs' / 'data_schema.md').read_text()
        for field in REQUIRED_FIELDS:
            self.assertIn(f'`{field}`', schema)
        for confidence in VALID_CONFIDENCE:
            self.assertIn(f'`{confidence}`', schema)
        types = re.search(r'### Supported New-Contribution Types.*?```text\n(.*?)\n```', schema, re.S)
        self.assertIsNotNone(types)
        self.assertEqual(set(types.group(1).split()), SUBMISSION_TYPES)

    def test_fictional_edition_and_family_examples_validate(self):
        records, assignments = yaml_examples('adding_conferences.md')
        self.assertEqual(validate_conferences(records, load_controlled_topics()), [])
        self.assertEqual(validate_conference_families(records, assignments, load_mapping(FAMILIES_PATH)), [])
        record = records[0]
        self.assertNotIn(record['id'], {item['id'] for item in load_conferences()})
        gate, terminal = record['deadlines']
        self.assertEqual(gate['gate_for'], terminal['type'])
        self.assertIn(terminal['type'], SUBMISSION_TYPES)
        self.assertTrue(all('opens_at' not in d and 'open_observed_on' not in d for d in record['deadlines']))

    def test_fictional_scope_example_validates_without_guessing_extra_keys(self):
        records, _ = yaml_examples('adding_conferences.md')
        profiles, = yaml_examples('conference_scopes.md')
        self.assertEqual(validate_scopes(records, profiles, load_controlled_topics()), [])


if __name__ == '__main__':
    unittest.main()

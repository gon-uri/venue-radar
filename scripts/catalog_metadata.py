"""Shared topic hierarchy and offline map metadata."""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pathlib import Path
import yaml
from validate import ROOT, parse_date

FAMILIES_PATH = ROOT / 'data' / 'topic_families.yml'
CONFERENCE_FAMILIES_PATH = ROOT / 'data' / 'conference_families.yml'
CITIES_PATH = ROOT / 'data' / 'cities.yml'


def load_mapping(path: Path) -> dict:
    with path.open(encoding='utf-8') as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f'{path} must contain a mapping')
    return value


def validate_catalog_metadata(topics: set[str], families: dict, cities: dict) -> list[str]:
    errors = []
    seen_topics = set()
    seen_ids = set()
    family_list = families.get('families')
    if not isinstance(family_list, list) or not all(isinstance(family, dict) for family in family_list):
        return ['Topic families must be a list of mappings']
    for family in family_list:
        family_id = family.get('id')
        if not isinstance(family_id, str) or not family_id.strip() or family_id in seen_ids:
            errors.append('Topic family IDs must be non-empty and unique')
        else:
            seen_ids.add(family_id)
        if not isinstance(family.get('label'), str) or not family['label'].strip() or not family.get('topics'):
            errors.append('Each topic family needs a label and subtopics')
        children = family.get('topics', [])
        if not isinstance(children, list) or not all(isinstance(topic, str) for topic in children):
            errors.append('Family subtopics must be a list of strings')
            continue
        for topic in children:
            if topic not in topics or topic in seen_topics:
                errors.append(f'Topic must occur in exactly one family: {topic}')
            seen_topics.add(topic)
    if seen_topics != topics:
        errors.append('Every controlled topic must belong to one family')
    labels = families.get('labels', {})
    if not isinstance(labels, dict) or set(labels) != topics or not all(isinstance(value, str) and value.strip() for value in labels.values()):
        errors.append('Every controlled topic must have one display label')
    locations = set()
    for key, city in cities.items():
        if not isinstance(city, dict):
            errors.append(f'{key}: city must be a mapping')
            continue
        if not isinstance(city.get('label'), str) or not city['label'].strip() or not city.get('locations'):
            errors.append(f'{key}: city label and location aliases are required')
        for axis, limit in [('lat', 90), ('lon', 180)]:
            value = city.get(axis)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not -limit <= value <= limit:
                errors.append(f'{key}: invalid {axis}')
        try:
            ZoneInfo(city.get('tz') or '')
        except (ValueError, ZoneInfoNotFoundError):
            errors.append(f'{key}: tz must be an IANA time zone')
        aliases = city.get('locations', [])
        if not isinstance(aliases, list) or not all(isinstance(alias, str) and alias.strip() for alias in aliases):
            errors.append(f'{key}: location aliases must be non-empty strings')
            continue
        for location in aliases:
            if location in locations:
                errors.append(f'{key}: duplicate location alias {location}')
            locations.add(location)
    return errors


def map_events(conferences: list[dict], cities: dict) -> list[dict]:
    by_location = {alias: (key, city) for key, city in cities.items() for alias in city['locations']}
    events = []
    for item in conferences:
        match = by_location.get(item.get('location'))
        if not match or item['confidence'] not in {'confirmed', 'announced_no_deadlines'} or item.get('mode') == 'online':
            continue
        key, city = match
        events.append({
            'id': item['id'], 'city': key, 'label': city['label'],
            'lat': city['lat'], 'lon': city['lon'], 'title': item['short_title'],
            'start': parse_date(item['conference_start']).isoformat(),
            'end': parse_date(item['conference_end']).isoformat(), 'url': item['website'],
        })
    return sorted(events, key=lambda event: (event['start'], event['id']))


def validate_conference_families(conferences: list[dict], assignments: dict,
                                 families: dict, allow_extra: bool = False) -> list[str]:
    series = {item['series'] for item in conferences
              if isinstance(item, dict) and isinstance(item.get('series'), str)}
    family_list = families.get('families')
    if not isinstance(family_list, list):
        return ['Central identities require a valid family registry']
    valid_ids = {family['id'] for family in family_list
                 if isinstance(family, dict) and isinstance(family.get('id'), str)}
    errors = []
    if not allow_extra and set(assignments) - series:
        errors.append('Central family assignments contain untracked series')
    for name in sorted(series):
        values = assignments.get(name)
        if (not isinstance(values, list) or not 1 <= len(values) <= 3
                or not all(isinstance(value, str) for value in values)
                or len(set(values)) != len(values) or set(values) - valid_ids):
            errors.append(f'{name}: assign one to three distinct valid central families')
    return errors

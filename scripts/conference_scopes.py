"""Curated, sourced conference-series profiles, independent of edition timing."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from validate import ROOT, call_is_out, parse_date

SCOPES_PATH = ROOT / "data" / "conference_scopes.yml"
MAX_ADDITIONAL_TOPICS = 6


def load_scopes(path: Path = SCOPES_PATH) -> dict:
    with path.open(encoding="utf-8") as handle:
        profiles = yaml.safe_load(handle)
    if not isinstance(profiles, dict):
        raise ValueError(f"{path} must contain a mapping of conference series")
    return profiles


def validate_scopes(conferences: list[dict], profiles: dict, topics: set[str]) -> list[str]:
    if not isinstance(profiles, dict):
        return ["Conference scopes must be a mapping"]
    series = {item["series"] for item in conferences}
    errors = []
    required = {"additional_topics", "scope_summary", "scope_source_urls", "scope_last_checked", "source_year"}
    for name, profile in profiles.items():
        label = f"{name}: scope"
        if name not in series:
            errors.append(f"{label}: unknown conference series")
        if not isinstance(profile, dict):
            errors.append(f"{label}: profile must be a mapping")
            continue
        if set(profile) != required:
            errors.append(f"{label}: fields must be {sorted(required)}")
        summary = profile.get("scope_summary")
        if not isinstance(summary, str) or not summary.strip() or len(summary) > 1200:
            errors.append(f"{label}: scope_summary must be non-empty and at most 1200 characters")
        extra = profile.get("additional_topics")
        if not isinstance(extra, list) or not all(isinstance(topic, str) for topic in extra):
            errors.append(f"{label}: additional_topics must be a list of strings")
        else:
            if len(extra) > MAX_ADDITIONAL_TOPICS or len(set(extra)) != len(extra):
                errors.append(f"{label}: use at most six distinct additional topics")
            for topic in extra:
                if topic not in topics:
                    errors.append(f"{label}: uncontrolled additional topic '{topic}'")
        urls = profile.get("scope_source_urls")
        if not isinstance(urls, list) or not urls:
            errors.append(f"{label}: scope_source_urls must be a non-empty list")
        else:
            for url in urls:
                try:
                    parsed = urlsplit(url) if isinstance(url, str) else None
                except ValueError:
                    parsed = None
                if not parsed or parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    errors.append(f"{label}: scope sources must be HTTP(S) URLs")
        try:
            checked = parse_date(profile.get("scope_last_checked"))
            if checked > date.today():
                errors.append(f"{label}: scope_last_checked cannot be in the future")
        except (TypeError, ValueError):
            errors.append(f"{label}: invalid scope_last_checked date")
        year = profile.get("source_year")
        if type(year) is not int or not 2000 <= year <= date.today().year + 2:
            errors.append(f"{label}: source_year must identify the reviewed edition")
    return errors


def with_scopes(conferences: list[dict], profiles: dict) -> list[dict]:
    return [dict(item, scope=profiles.get(item["series"], {})) for item in conferences]


def all_topics(conference: dict) -> list[str]:
    return list(dict.fromkeys([
        *conference.get("topics", []),
        *conference.get("scope", {}).get("additional_topics", []),
    ]))


def scope_review_queue(conferences: list[dict], profiles: dict, as_of: date,
                       max_age_days: int) -> list[tuple[str, str, str]]:
    latest = {}
    for item in conferences:
        if item["series"] not in latest or item["year"] > latest[item["series"]]["year"]:
            latest[item["series"]] = item
    rows = []
    for name, item in sorted(latest.items(), key=lambda pair: pair[0].casefold()):
        profile = profiles.get(name)
        if not profile:
            rows.append((name, "no reviewed scope profile", item.get("cfp_url") or item["website"]))
            continue
        reasons = []
        age = (as_of - parse_date(profile["scope_last_checked"])).days
        if age > max_age_days:
            reasons.append(f"scope last checked {age} days ago")
        # A profile from an earlier edition is only re-read once a newer call is
        # out; an estimated projection has nothing new to read yet.
        newer = [edition["year"] for edition in conferences if edition["series"] == name
                 and edition["year"] > profile["source_year"] and call_is_out(edition)]
        if newer:
            reasons.append(f"scope based on {profile['source_year']}; check {max(newer)} CFP")
        if reasons:
            rows.append((name, "; ".join(reasons), profile["scope_source_urls"][0]))
    return rows

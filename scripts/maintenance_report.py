"""Print a source-linked, triaged review queue for the static conference catalog.

Report-only: it reads the canonical YAML and never writes or fetches anything.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Callable
from urllib.parse import urlsplit

from catalog_metadata import CITIES_PATH, load_mapping
from conference_scopes import load_scopes, scope_review_queue
from validate import SUBMISSION_TYPES, load_acceptance_rates, load_conferences, parse_date, parse_datetime

# Joint editions do not need a same-name successor.
JOINT_SERIES = frozenset({"IJCAI-ECAI"})
ACT_NOW_DAYS = 30
SOON_DAYS = 90
TIERS = {
    "act-now": ("Act now", f"fresh-submission action due within {ACT_NOW_DAYS} days ({SOON_DAYS} if estimated)"),
    "soon": ("Soon", f"fresh-submission action due within {SOON_DAYS} days"),
    "later": ("Later", f"fresh-submission action due after {SOON_DAYS} days"),
    "call-unannounced": ("Call unannounced", "upcoming meeting with no recorded fresh-submission route"),
    "schedule-only": ("Schedule only", "no remaining fresh-submission route"),
    "successor-missing": ("Successor missing", "latest tracked edition is past or closed and no later edition exists"),
}
ADVISORY_CHECKS = {
    "estimated-deadline-passed": "Estimated deadline already passed (meeting still upcoming)",
    "missing-city-alias": "Confirmed future location without a data/cities.yml alias",
    "old-year-url": "Confirmed record cites a URL from an earlier year",
    "aggregator-source": "Aggregator or social-media source",
}
# Mirrors catalog_metadata.map_events: which records the offline map can place.
MAP_CONFIDENCE = frozenset({"confirmed", "announced_no_deadlines"})
PLACEHOLDER_LOCATIONS = frozenset({"", "tba", "tbd", "to be announced", "to be determined"})
SOCIAL_HOSTS = ("linkedin.com", "x.com", "twitter.com", "facebook.com")
AGGREGATOR_MARKERS = ("wikicfp", "conferenceindex", "aideadlin.es", "ccfddl")
YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
RELEVANCE_ORDER = {"high": 0, "medium": 1, "low": 2, "watch": 3}


@dataclass(frozen=True)
class Milestone:
    """The next author action on a fresh-submission route (the route itself or its gate)."""

    type: str
    label: str
    due: str
    days: int
    confidence: str
    route_estimated: bool
    route: str
    source_url: str


@dataclass(frozen=True)
class TriagedEdition:
    tier: str
    title: str
    id: str
    reasons: str
    source: str
    meeting_start: str
    meeting_end: str
    milestone: Milestone | None


@dataclass(frozen=True)
class Advisory:
    check: str
    title: str
    id: str
    detail: str
    url: str


@dataclass(frozen=True)
class BacklogRow:
    name: str
    detail: str
    source: str


@dataclass(frozen=True)
class Report:
    as_of: date
    max_age_days: int
    total_editions: int
    editions: list[TriagedEdition]
    advisories: list[Advisory]
    acceptance: list[BacklogRow]
    scope: list[BacklogRow]


def review_queue(
    conferences: list[dict], as_of: date, max_age_days: int,
) -> list[tuple[str, str, str, str]]:
    queue = []
    latest_by_series = {
        series: max(
            (item for item in conferences if item["series"] == series),
            key=lambda item: item["year"],
        )
        for series in {item["series"] for item in conferences}
    }
    for item in conferences:
        reasons = []
        checked = parse_date(item["last_checked"])
        age = (as_of - checked).days
        upcoming = parse_date(item["conference_end"]) >= as_of
        if upcoming:
            if item["confidence"] != "confirmed":
                reasons.append(item["confidence"].replace("_", " "))
            if any(
                deadline.get("confidence", item["confidence"]) != "confirmed"
                for deadline in item.get("deadlines", [])
            ):
                reasons.append("estimated deadline(s): compare with official CFP")
            if age > max_age_days:
                reasons.append(f"last checked {age} days ago")
            if not item.get("deadlines"):
                reasons.append("no submission deadline recorded")
        elif latest_by_series[item["series"]] is item and item["series"] not in JOINT_SERIES:
            reasons.append("next edition not tracked")
        if reasons:
            source = (item.get("source_urls") or [item.get("cfp_url") or item["website"]])[0]
            queue.append((item["short_title"], item["id"], ", ".join(reasons), source))
    return sorted(queue, key=lambda row: ("next edition not tracked" in row[2], row[0].casefold()))


def _due_date(deadline: dict) -> date | None:
    try:
        return parse_datetime(deadline.get("datetime")).date()
    except (TypeError, ValueError):
        return None


def _confidence(edition: dict, deadline: dict) -> str:
    return str(deadline.get("confidence", edition["confidence"]))


def next_route_action(edition: dict, as_of: date) -> Milestone | None:
    """Earliest remaining action on a supported route, mirroring the site's gate rules."""
    deadlines = [item for item in edition.get("deadlines") or [] if _due_date(item)]
    best: Milestone | None = None
    for route in deadlines:
        if route.get("type") not in SUBMISSION_TYPES or route.get("gate_for") or _due_date(route) < as_of:
            continue
        gates = [item for item in deadlines if item.get("gate_for") == route["type"]]
        if any(_due_date(gate) < as_of for gate in gates):
            continue
        action = min(gates, key=_due_date, default=route)
        due = _due_date(action)
        candidate = Milestone(
            type=action["type"],
            label=str(action.get("label", action["type"])),
            due=due.isoformat(),
            days=(due - as_of).days,
            confidence=_confidence(edition, action),
            route_estimated=any(_confidence(edition, item) != "confirmed" for item in [route, *gates]),
            route=route["type"],
            source_url=str(action.get("source_url") or route.get("source_url") or ""),
        )
        if best is None or candidate.days < best.days:
            best = candidate
    return best


def triage_tier(edition: dict, action: Milestone | None, is_latest: bool, as_of: date) -> str:
    past = parse_date(edition["conference_end"]) < as_of
    # A closed route differs from a call that was never recorded (the site's
    # "Deadline unannounced"): only the former needs a successor.
    routes = [item for item in edition.get("deadlines") or []
              if item.get("type") in SUBMISSION_TYPES and not item.get("gate_for")]
    started = parse_date(edition["conference_start"]) <= as_of  # the site shows it closed
    if is_latest and edition["series"] not in JOINT_SERIES and (past or (action is None and (routes or started))):
        return "successor-missing"
    if action is None:
        return "schedule-only" if routes or past or started else "call-unannounced"
    if action.days <= ACT_NOW_DAYS or (action.route_estimated and action.days <= SOON_DAYS):
        return "act-now"
    return "soon" if action.days <= SOON_DAYS else "later"


def triage(conferences: list[dict], as_of: date, max_age_days: int) -> list[TriagedEdition]:
    """Assign an urgency tier to every queued edition, most urgent first."""
    by_id = {item["id"]: item for item in conferences}
    latest_year: dict[str, int] = {}
    for item in conferences:
        latest_year[item["series"]] = max(item["year"], latest_year.get(item["series"], item["year"]))
    rows = []
    for title, identifier, reasons, source in review_queue(conferences, as_of, max_age_days):
        edition = by_id[identifier]
        action = next_route_action(edition, as_of)
        tier = triage_tier(edition, action, edition["year"] >= latest_year[edition["series"]], as_of)
        start, end = (parse_date(edition[field]).isoformat() for field in ("conference_start", "conference_end"))
        rows.append(TriagedEdition(tier, title, identifier, reasons, source, start, end, action))

    def key(row: TriagedEdition) -> tuple[int, int, str]:
        days = row.milestone.days if row.milestone else (date.fromisoformat(row.meeting_start) - as_of).days
        return list(TIERS).index(row.tier), days, row.title.casefold()

    return sorted(rows, key=key)


def _cited_urls(edition: dict, include_website: bool = True, confirmed_only: bool = False) -> list[str]:
    urls = [edition.get("website")] if include_website else []
    urls += [edition.get("cfp_url"), *(edition.get("source_urls") or [])]
    urls += [
        item.get("source_url") for item in edition.get("deadlines") or []
        if not confirmed_only or _confidence(edition, item) == "confirmed"
    ]
    return list(dict.fromkeys(url for url in urls if isinstance(url, str) and url))


def is_aggregator(url: str) -> bool:
    parts = urlsplit(url.lower())
    host = parts.hostname or ""
    if any(host == domain or host.endswith("." + domain) for domain in SOCIAL_HOSTS):
        return True
    return any(marker in host or marker in parts.path for marker in AGGREGATOR_MARKERS)


def url_years(url: str) -> list[int]:
    return [int(year) for year in YEAR_RE.findall(url)]


def edition_advisories(item: dict, aliases: set[str], as_of: date) -> list[Advisory]:
    """Data smells on one edition, independent of the review queue."""
    found: list[tuple[str, str, str]] = []
    for deadline in item.get("deadlines") or []:
        due = _due_date(deadline)
        if due and due < as_of and _confidence(item, deadline) != "confirmed":
            found.append(("estimated-deadline-passed", f"estimated {deadline.get('type')} date {due} has passed",
                          str(deadline.get("source_url") or "")))
    location = str(item.get("location") or "").strip()
    if (item["confidence"] in MAP_CONFIDENCE and item.get("mode") != "online"
            and parse_date(item["conference_start"]) >= as_of
            and location.casefold() not in PLACEHOLDER_LOCATIONS and location not in aliases):
        found.append(("missing-city-alias", f"location '{location}' has no exact alias, so the map omits it", ""))
    if item["confidence"] == "confirmed":
        for url in _cited_urls(item, include_website=False, confirmed_only=True):
            years = url_years(url)
            if years and max(years) < item["year"]:
                found.append(("old-year-url", f"URL year {max(years)} is earlier than edition year {item['year']}", url))
    for url in _cited_urls(item):
        if is_aggregator(url):
            found.append(("aggregator-source", "discovery evidence only; cite the official page", url))
    return [Advisory(check, item["short_title"], item["id"], detail, url) for check, detail, url in found]


def advisories(conferences: list[dict], cities: dict, as_of: date) -> list[Advisory]:
    """Advisory checks for current and upcoming editions, grouped by check."""
    aliases = {alias for city in cities.values() for alias in city.get("locations", [])}
    rows = [
        row for item in conferences if parse_date(item["conference_end"]) >= as_of
        for row in edition_advisories(item, aliases, as_of)
    ]
    order = list(ADVISORY_CHECKS)
    return sorted(rows, key=lambda row: (order.index(row.check), row.title.casefold(), row.url))


def _acceptance_gaps(conferences: list[dict], rates: dict, as_of: date) -> list[tuple[str, str]]:
    names = sorted({item["series"] for item in conferences}, key=str.casefold)
    return [
        (name, "no sourced rate" if name not in rates else f"latest evidence is {rates[name]['year']}")
        for name in names
        if name not in rates or as_of.year - rates[name]["year"] > 2
    ]


def acceptance_queue(conferences: list[dict], rates: dict, as_of: date) -> list[str]:
    return [f"{name}: {detail}" for name, detail in _acceptance_gaps(conferences, rates, as_of)]


def series_relevance(conferences: list[dict]) -> dict[str, int]:
    """Relevance rank (0 = high) of each series' latest edition."""
    latest: dict[str, dict] = {}
    for item in conferences:
        if item["series"] not in latest or item["year"] > latest[item["series"]]["year"]:
            latest[item["series"]] = item
    return {name: RELEVANCE_ORDER.get(item.get("relevance", ""), len(RELEVANCE_ORDER)) for name, item in latest.items()}


def acceptance_backlog(conferences: list[dict], rates: dict, as_of: date) -> list[BacklogRow]:
    """Acceptance gaps ordered missing/oldest evidence first, then by relevance."""
    relevance = series_relevance(conferences)
    gaps = sorted(
        _acceptance_gaps(conferences, rates, as_of),
        key=lambda gap: (rates.get(gap[0], {}).get("year", 0), relevance[gap[0]], gap[0].casefold()),
    )
    return [BacklogRow(name, detail, str(rates.get(name, {}).get("source_url", ""))) for name, detail in gaps]


def scope_backlog(conferences: list[dict], profiles: dict, as_of: date, max_age_days: int) -> list[BacklogRow]:
    """Scope gaps ordered missing/oldest profile first, then by relevance."""
    relevance = series_relevance(conferences)

    def key(row: tuple[str, str, str]) -> tuple[str, int, str]:
        checked = str(profiles.get(row[0], {}).get("scope_last_checked", ""))
        return checked, relevance[row[0]], row[0].casefold()

    rows = sorted(scope_review_queue(conferences, profiles, as_of, max_age_days), key=key)
    return [BacklogRow(*row) for row in rows]


def build_report(as_of: date, max_age_days: int) -> Report:
    conferences = load_conferences()
    rates = load_acceptance_rates()["rates"]
    return Report(
        as_of=as_of,
        max_age_days=max_age_days,
        total_editions=len(conferences),
        editions=triage(conferences, as_of, max_age_days),
        advisories=advisories(conferences, load_mapping(CITIES_PATH), as_of),
        acceptance=acceptance_backlog(conferences, rates, as_of),
        scope=scope_backlog(conferences, load_scopes(), as_of, max_age_days),
    )


def _sample(rows: list[BacklogRow], limit: int | None) -> list[BacklogRow]:
    return rows if limit is None else rows[:limit]


def _due_text(milestone: Milestone, code: Callable[[str], str] = str) -> str:
    gate = f" (gate for {code(milestone.route)})" if milestone.type != milestone.route else ""
    confidence = milestone.confidence.replace("_", " ")
    if milestone.route_estimated and milestone.confidence == "confirmed":
        confidence += "; route estimated"
    days = "today" if milestone.days == 0 else f"in {milestone.days} day{'s' * (milestone.days != 1)}"
    return f"{code(milestone.type)}{gate} due {milestone.due}, {days} ({confidence})"


def render_text(report: Report, sample: int | None) -> str:
    lines = [f"Edition review as of {report.as_of}: {len(report.editions)} of {report.total_editions} editions"]
    for tier, (label, meaning) in TIERS.items():
        rows = [row for row in report.editions if row.tier == tier]
        if not rows:
            continue
        lines += ["", f"{label} ({len(rows)}): {meaning}"]
        for row in rows:
            lines.append(f"- {row.title} ({row.id}): {row.reasons}")
            if row.milestone:
                lines.append(f"  {_due_text(row.milestone)}")
                lines.append(f"  {row.milestone.source_url or row.source}")
            else:
                lines.append(f"  meeting {row.meeting_start} to {row.meeting_end}")
                lines.append(f"  {row.source}")
    lines += ["", f"Advisory checks: {len(report.advisories)}"]
    for check, label in ADVISORY_CHECKS.items():
        rows = [row for row in report.advisories if row.check == check]
        if rows:
            lines.append(f"{label} ({len(rows)})")
            lines += [f"- {row.title} ({row.id}): {row.detail}" + (f"\n  {row.url}" if row.url else "") for row in rows]
    for heading, rows in [("Acceptance evidence review", report.acceptance), ("Scope review", report.scope)]:
        shown = _sample(rows, sample)
        suffix = f" (showing {len(shown)}; --full lists all)" if len(shown) < len(rows) else ""
        lines += ["", f"{heading}: {len(rows)} series{suffix}"]
        lines += [f"- {row.name}: {row.detail}" + (f"\n  {row.source}" if row.source else "") for row in shown]
    return "\n".join(lines)


_MD_SPECIAL = re.compile(r"([\\`*_\[\]<>#|~])")


def md(text: str) -> str:
    return _MD_SPECIAL.sub(r"\\\1", text)


def _md_link(url: str, label: str = "source") -> str:
    return f"[{label}](<{url}>)" if url else ""


def render_markdown(report: Report, sample: int | None) -> str:
    counts = ", ".join(
        f"{label}: {sum(row.tier == tier for row in report.editions)}" for tier, (label, _) in TIERS.items()
    )
    lines = [
        f"## Review queue as of {report.as_of}",
        "",
        f"Advisory output of `scripts/maintenance_report.py --as-of {report.as_of} "
        f"--max-age-days {report.max_age_days}`. It reads the committed YAML only; verify every "
        "change against official sources before editing data (ADR-015).",
        "",
        f"### Editions: {len(report.editions)} of {report.total_editions} queued",
        "",
        counts,
    ]
    for tier, (label, meaning) in TIERS.items():
        rows = [row for row in report.editions if row.tier == tier]
        if not rows:
            continue
        lines += ["", f"#### {label} ({len(rows)})", "", f"_{meaning}_", ""]
        for row in rows:
            if row.milestone:
                due = _due_text(row.milestone, code=lambda value: f"`{value}`")
                detail = f"{due} · {_md_link(row.milestone.source_url or row.source)}"
            else:
                detail = f"meeting {row.meeting_start} to {row.meeting_end} · {_md_link(row.source)}"
            lines.append(f"- [ ] **{md(row.title)}** (`{row.id}`): {md(row.reasons)} — {detail}")
    lines += ["", f"### Advisory checks ({len(report.advisories)})"]
    for check, label in ADVISORY_CHECKS.items():
        rows = [row for row in report.advisories if row.check == check]
        if rows:
            lines += ["", f"#### {md(label)} ({len(rows)})", ""]
            lines += [
                f"- [ ] **{md(row.title)}** (`{row.id}`): {md(row.detail)}"
                + (f" · {_md_link(row.url)}" if row.url else "")
                for row in rows
            ]
    for heading, rows in [("Acceptance evidence", report.acceptance), ("Scope profiles", report.scope)]:
        shown = _sample(rows, sample)
        lines += ["", f"### {heading} backlog: {len(rows)} series", ""]
        if len(shown) < len(rows):
            lines += [f"Oldest or most relevant {len(shown)} shown; run with `--full` for all.", ""]
        lines += [
            f"- [ ] **{md(row.name)}**: {md(row.detail)}" + (f" · {_md_link(row.source)}" if row.source else "")
            for row in shown
        ]
    return "\n".join(lines)


def render_json(report: Report, sample: int | None) -> str:
    def backlog(rows: list[BacklogRow]) -> dict[str, Any]:
        shown = _sample(rows, sample)
        return {"count": len(rows), "complete": len(shown) == len(rows), "items": [asdict(row) for row in shown]}

    payload = {
        "as_of": report.as_of.isoformat(),
        "max_age_days": report.max_age_days,
        "total_editions": report.total_editions,
        "tier_counts": {tier: sum(row.tier == tier for row in report.editions) for tier in TIERS},
        "editions": [asdict(row) for row in report.editions],
        "advisories": [asdict(row) for row in report.advisories],
        "acceptance": backlog(report.acceptance),
        "scope": backlog(report.scope),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


RENDERERS: dict[str, Callable[[Report, int | None], str]] = {
    "text": render_text, "markdown": render_markdown, "json": render_json,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument("--max-age-days", type=int, default=30)
    parser.add_argument("--format", choices=sorted(RENDERERS), default="text")
    parser.add_argument("--backlog-sample", type=int, default=5, metavar="N",
                        help="acceptance/scope backlog rows to list (default 5)")
    parser.add_argument("--full", action="store_true", help="list every acceptance/scope backlog row")
    args = parser.parse_args()
    if args.max_age_days < 0:
        parser.error("--max-age-days must be non-negative")
    if args.backlog_sample < 0:
        parser.error("--backlog-sample must be non-negative")
    report = build_report(args.as_of, args.max_age_days)
    print(RENDERERS[args.format](report, None if args.full else args.backlog_sample))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

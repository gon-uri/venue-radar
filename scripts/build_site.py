from __future__ import annotations

import json
import base64
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import yaml
from build_ics import SITE_URL, series_display_name, series_groups, series_slug
from catalog_metadata import CITIES_PATH, CONFERENCE_FAMILIES_PATH, FAMILIES_PATH, load_mapping, map_events, validate_catalog_metadata, validate_conference_families
from conference_scopes import SCOPES_PATH, all_topics, load_scopes, validate_scopes, with_scopes

from validate import (
    DATA_PATH,
    CCF_PATH,
    ACCEPTANCE_PATH,
    ICORE_PATH,
    SUBMISSION_TYPES,
    acceptance_band,
    load_acceptance_rates,
    load_ccf_rankings,
    load_conferences,
    load_controlled_topics,
    load_icore_rankings,
    parse_date,
    parse_datetime,
    stable_slug,
    validate_conferences,
    validate_acceptance_rates,
    validate_ccf_rankings,
    validate_icore_rankings,
)


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
METADATA_PATH = ROOT / "data" / "metadata.yml"
ASSETS_DIR = ROOT / "assets"
TOPIC_CATALOG = load_mapping(FAMILIES_PATH)
CITIES = load_mapping(CITIES_PATH)
CONFERENCE_FAMILIES = load_mapping(CONFERENCE_FAMILIES_PATH)
TIME_ESTIMATE_TOOLTIP = (
    "Official day; exact hour/timezone unannounced. "
    "Countdown uses a provisional calendar time."
)
# Public copy for search results and link previews (site_copy.md owns wording).
PAGE_TITLE = "Venue Radar: ML, AI & Neuroscience Conference Deadlines"
PAGE_DESCRIPTION = (
    "Conference deadlines for machine learning, AI, neuroscience, healthcare, complex systems "
    "and control, with live countdowns, rankings, acceptance rates and auto-updating calendars."
)
# Pages serves only docs/ (generated output), so the card is served from the repository.
SOCIAL_CARD_URL = "https://raw.githubusercontent.com/gon-uri/venue-radar/main/assets/branding/social-card.png"
SHARE_TEXT = (
    "Check out Venue Radar, a new conference calendar for ML, AI, neuroscience, and related fields. "
    "Search and filter submission deadlines, compare ICORE/CCF rankings, "
    "and check historical acceptance rates."
)

MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def _attr(value: Any) -> str:
    return escape(str(value), quote=True)


def _topic_labels(topics: list[str]) -> str:
    return '<div class="topic-tags">' + " ".join(
        f'<span class="tag" title="{_attr(topic)}">{escape(TOPIC_CATALOG["labels"].get(topic, topic))}</span>'
        for topic in topics
    ) + '</div>'


def _conference_source_url(conference: dict[str, Any]) -> str:
    source_urls = conference.get("source_urls") or []
    if source_urls:
        return source_urls[0]
    return conference.get("cfp_url") or conference["website"]


def _deadline_source_url(
    conference: dict[str, Any], deadline: dict[str, Any]
) -> str:
    return deadline.get("source_url") or _conference_source_url(conference)


def _format_date(value: datetime) -> str:
    return f"{MONTHS[value.month - 1]} {value.day}, {value.year}"


def _deadline_iso_utc(value: Any) -> str:
    parsed = parse_datetime(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _display_deadline_datetime(value: Any) -> str:
    parsed = parse_datetime(value)
    return _format_date(parsed)


def _offset_minutes(value: Any) -> int:
    parsed = parse_datetime(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return 0
    return int(parsed.utcoffset().total_seconds() // 60)


def _host_zone(conference: dict[str, Any]) -> str | None:
    """IANA zone of the confirmed host city, else a real edition zone (not Etc/*)."""
    for city in CITIES.values():
        if conference.get("location") in city.get("locations", []):
            return city.get("tz")
    if "to be announced" in str(conference.get("location") or "").casefold():
        return None  # rollover drafts keep the prior host's zone
    zone = str(conference.get("timezone") or "")
    return zone if "/" in zone and not zone.startswith("Etc/") else None


def _effective_cutoff(conference: dict[str, Any], deadline: dict[str, Any]) -> tuple[str, str | None]:
    """UTC instant used for countdowns and closing, plus the zone it came from.

    A published day without an hour is stored as 23:59 AoE (-12:00). When the
    host zone is known, the countdown instead ends at 23:59 in that zone on the
    same day, which is never later than AoE (ADR-040). ICS stays all-day.
    """
    stored = deadline["datetime"]
    if deadline.get("time_precision") != "date" or _offset_minutes(stored) != -12 * 60:
        return _deadline_iso_utc(stored), None
    zone = _host_zone(conference)
    if not zone:
        return _deadline_iso_utc(stored), None
    day = parse_datetime(stored)
    local = datetime(day.year, day.month, day.day, 23, 59, tzinfo=ZoneInfo(zone))
    return local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"), zone


def _clock_label(value: Any) -> str:
    """Cutoff in the stored offset: '23:59 AoE', '20:00 UTC' or '17:00 UTC-4'.

    Zone abbreviations are never guessed; only the recorded offset is shown.
    """
    parsed = parse_datetime(value)
    minutes = _offset_minutes(value)
    if minutes == -12 * 60:
        zone = "AoE"
    elif minutes == 0:
        zone = "UTC"
    else:
        hours, rest = divmod(abs(minutes), 60)
        zone = f"UTC{'+' if minutes > 0 else '-'}{hours}" + (f":{rest:02d}" if rest else "")
    return f"{parsed.hour:02d}:{parsed.minute:02d} {zone}"


def _display_deadline_label(label: str) -> str:
    cleaned = label.strip()
    suffix = " deadline"
    if cleaned.lower().endswith(suffix):
        cleaned = cleaned[: -len(suffix)].rstrip()
    return cleaned


def _display_conference_dates(start_value: Any, end_value: Any) -> str:
    start = parse_date(start_value)
    end = parse_date(end_value)
    if start == end:
        return f"{MONTHS[start.month - 1]} {start.day}, {start.year}"
    if start.year == end.year and start.month == end.month:
        return f"{MONTHS[start.month - 1]} {start.day}-{end.day}, {start.year}"
    if start.year == end.year:
        return (
            f"{MONTHS[start.month - 1]} {start.day} - "
            f"{MONTHS[end.month - 1]} {end.day}, {start.year}"
        )
    return (
        f"{MONTHS[start.month - 1]} {start.day}, {start.year} - "
        f"{MONTHS[end.month - 1]} {end.day}, {end.year}"
    )


def _search_text(conference: dict[str, Any], extra: list[str] | None = None) -> str:
    topics = all_topics(conference)
    parts = [
        conference["series"],
        conference["title"],
        conference["short_title"],
        conference.get("location", ""),
        conference.get("confidence", ""),
        conference.get("size", ""),
        conference.get("submission_type", ""),
        " ".join(topics),
        " ".join(TOPIC_CATALOG["labels"].get(topic, topic) for topic in topics),
        " ".join(family["label"] for family in TOPIC_CATALOG["families"]
                 if family["id"] in CONFERENCE_FAMILIES.get(conference["series"], [])),
        conference.get("scope", {}).get("scope_summary", ""),
    ]
    if extra:
        parts.extend(extra)
    return " ".join(str(part) for part in parts if part)


def _topic_slugs(topics: list[str]) -> str:
    return " ".join(stable_slug(topic) for topic in topics)


def _value_slug(value: Any) -> str:
    return stable_slug(str(value))


def _metadata_label(value: Any) -> str:
    return f'<span class="meta-pill">{escape(str(value))}</span>'


def _icore_cell(conference: dict[str, Any], rankings: dict[str, Any]) -> str:
    entry = rankings.get(conference["series"])
    if entry is None:
        return (
            '<span class="rank-empty" title="No ICORE 2026 main-track rank '
            'is listed for this conference series.">&mdash;</span>'
        )
    rank = entry["rank"]
    url = f'https://portal.core.edu.au/conf-ranks/{entry["portal_id"]}/'
    return (
        f'<a class="rank-link" href="{_attr(url)}" '
        f'aria-label="ICORE 2026 rank {_attr(rank)}" '
        f'title="ICORE 2026: {_attr(rank)}. Applies to main-track full papers.">'
        f"{escape(rank)}</a>"
    )


def _ranking_cell(
    conference: dict[str, Any],
    icore: dict[str, Any],
    ccf: dict[str, Any],
    ccf_page: str,
) -> str:
    ccf_entry = ccf.get(conference["series"])
    if ccf_entry:
        rank = ccf_entry["rank"]
        ccf_html = (
            f'<a class="rank-link rank-link-ccf" href="{_attr(ccf_page)}" '
            f'aria-label="CCF 2026 rank {_attr(rank)}" '
            f'title="CCF 2026: {_attr(rank)}. Main-track full papers only.">'
            f"{escape(rank)}</a>"
        )
    else:
        ccf_html = '<span class="rank-empty" title="No direct CCF 2026 rank">&mdash;</span>'
    return (
        '<span class="rank-pair">'
        f"{_icore_cell(conference, icore)}"
        '<span class="rank-separator" aria-hidden="true">/</span>'
        f"{ccf_html}</span>"
    )


def _acceptance_cell(conference: dict[str, Any], rates: dict[str, Any]) -> str:
    entry = rates.get(conference["series"])
    if entry is None:
        return '<span class="rate-unknown" title="No defensible historical rate is available">Unknown</span>'
    percent = entry.get("percent")
    band = acceptance_band(percent) if percent is not None else entry["band"]
    detail = (
        f'{"~" if entry.get("approximate") else ""}{percent:g}% ({entry["year"]})'
        if percent is not None
        else "(estimated)"
    )
    return (
        '<span class="acceptance-cell">'
        f'<strong>{escape(band)}</strong> '
        f'<a href="{_attr(entry["source_url"])}" '
        f'title="{_attr(entry["track"])}; evidence year {entry["year"]}; {_attr(entry.get("basis", "historical rate"))}">'
        f"{escape(detail)}</a></span>"
    )


def _conference_calendar_href(conference: dict[str, Any]) -> str:
    return f"conferences/{conference['id']}.ics"


def _icon_symbol(name: str) -> str:
    """Turn a vendored Lucide SVG into a <symbol> for the shared sprite."""
    svg = (ASSETS_DIR / "vendor" / f"{name}.svg").read_text(encoding="utf-8")
    body = svg[svg.index(">", svg.index("<svg")) + 1: svg.rindex("</svg>")]
    return (
        f'<symbol id="icon-{name}" viewBox="0 0 24 24" stroke="currentColor" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{" ".join(body.split())}</symbol>'
    )


def _icon(name: str) -> str:
    """Reference a sprite icon; the class keeps the original Lucide name."""
    return (f'<svg class="lucide lucide-{name}" width="24" height="24" aria-hidden="true" '
            f'focusable="false"><use href="#icon-{name}"></use></svg>')


def _icon_sprite() -> str:
    symbols = "".join(_icon_symbol(name) for name in ("chevron-down", "download", "star"))
    return ('<!-- Icons: lucide-static v0.468.0, ISC (assets/vendor/Lucide-LICENSE) -->'
            '<svg class="icon-sprite" width="0" height="0" aria-hidden="true" focusable="false">'
            f'{symbols}</svg>')


def _conference_calendar_link(conference: dict[str, Any]) -> str:
    title = (
        f"Download an ICS calendar file for {conference['short_title']} with "
        "conference dates and deadlines."
    )
    slug = series_slug(conference["series"])
    series_title = (
        f"Calendar feed with every {conference['series']} edition; subscribe once "
        "and future editions appear automatically."
    )
    return (
        '<div class="row-calendar-actions">'
        f'<a class="row-calendar-button" href="{_attr(_conference_calendar_href(conference))}" '
        f'download title="{_attr(title)}" '
        f'aria-label="Download calendar for {_attr(conference["short_title"])}">'
        f'{_icon("download")}</a>'
        f'<a class="row-series-link" href="series/{_attr(slug)}.ics" '
        f'data-subscribe-series="{_attr(slug)}" title="{_attr(series_title)}" '
        f'aria-label="Series feed: subscribe to all {_attr(conference["series"])} editions">Series</a>'
        "</div>"
    )


def _round_coordinates(value: Any, digits: int = 3) -> Any:
    if isinstance(value, float):
        return round(value, digits)
    if isinstance(value, list):
        return [_round_coordinates(item, digits) for item in value]
    if isinstance(value, dict):
        return {key: _round_coordinates(item, digits) for key, item in value.items()}
    return value


REPOSITORY_URL = "https://github.com/gon-uri/venue-radar"


def _star_button(conference: dict[str, Any]) -> str:
    """Per-browser shortlist toggle keyed by series (hidden until JS runs)."""
    return (
        f'<button class="star-toggle" type="button" aria-pressed="false" hidden '
        f'data-star="{_attr(series_slug(conference["series"]))}" data-star-name="{_attr(conference["series"])}" '
        f'aria-label="Star {_attr(conference["series"])}" title="Star this series in this browser">'
        f'{_icon("star")}</button>'
    )


def _older_year_link(url: str, year: int) -> bool:
    """True when a URL names only earlier years than the edition (a prior-edition page)."""
    years = [int(value) for value in re.findall(r"(?<!\d)(20\d{2})(?!\d)", url)]
    return bool(years) and max(years) < year


def _evidence_line(conference: dict[str, Any]) -> str:
    """Sources, review date and actions for one edition (ADR-040)."""
    estimated = conference["confidence"] != "confirmed"
    items = []
    cfp = conference.get("cfp_url")
    if cfp:
        older = _older_year_link(cfp, conference["year"])
        items.append(f'<a href="{_attr(cfp)}">{"Previous call" if older else "Call for papers"}</a>')
    dates = next((url for url in conference.get("source_urls") or [] if url not in {cfp, conference["website"]}), None)
    if dates:
        older = _older_year_link(dates, conference["year"])
        items.append(f'<a href="{_attr(dates)}">{"Previous dates" if older else "Dates source"}</a>')
    checked = parse_date(conference["last_checked"])
    items.append(f'<span>Checked {MONTHS[checked.month - 1][:3]} {checked.day}, {checked.year}</span>')
    if conference.get("mode") in {"hybrid", "online"}:
        items.append(f'<span>{escape(conference["mode"].capitalize())}</span>')
    if estimated:
        items.append('<span>Dates estimated</span>')
    items.append(f'<button class="link-button" type="button" data-copy-link="{_attr(conference["id"])}" hidden>Copy link</button>')
    report = REPOSITORY_URL + "/issues/new?" + urlencode({
        "template": "correction.yml", "edition": conference["id"],
        "title": f"Correction: {conference['short_title']}",
    })
    items.append(f'<a href="{_attr(report)}" target="_blank" rel="noopener noreferrer">Report outdated info</a>')
    return f'<div class="evidence-line">{"".join(items)}</div>'


def _successors(conferences: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Map each edition ID to the next tracked edition of the same series."""
    by_series: dict[str, list[dict[str, Any]]] = {}
    for conference in conferences:
        by_series.setdefault(conference["series"], []).append(conference)
    result: dict[str, dict[str, Any]] = {}
    for editions in by_series.values():
        ordered = sorted(editions, key=lambda item: (item["year"], str(item["conference_start"])))
        for current, following in zip(ordered, ordered[1:]):
            result[current["id"]] = following
    return result


def _colgroup(widths: list[str]) -> str:
    columns = "".join(f'<col style="width: {width}">' for width in widths)
    return f"<colgroup>{columns}</colgroup>"


def _filter_attributes(
    conference: dict[str, Any],
    search_text: str,
    icore: dict[str, Any],
    ccf: dict[str, Any],
    rates: dict[str, Any],
    include_deadlines: bool = True,
) -> str:
    rate = rates.get(conference["series"])
    band = (
        acceptance_band(rate["percent"])
        if rate and rate.get("percent") is not None
        else rate.get("band", "Unknown") if rate else "Unknown"
    )
    deadlines = [
        {
            "type": deadline["type"],
            "label": _display_deadline_label(deadline["label"]),
            "at": _effective_cutoff(conference, deadline)[0],
            "gate_for": deadline.get("gate_for"),
            "opens_at": _deadline_iso_utc(deadline["opens_at"]) if deadline.get("opens_at") else None,
            "open_observed_on": str(deadline["open_observed_on"]) if deadline.get("open_observed_on") else None,
            "estimated": deadline.get("confidence", conference["confidence"]) != "confirmed",
            "approximate_time": deadline.get("time_precision") == "date",
        }
        for deadline in conference.get("deadlines", [])
    ]
    return (
        f'data-filter-row data-edition="{_attr(conference["id"])}" '
        f'data-series-slug="{_attr(series_slug(conference["series"]))}" data-search="{_attr(search_text)}" '
        f'data-topics="{_attr(_topic_slugs(all_topics(conference)))}" '
        f'data-families="{_attr(" ".join(CONFERENCE_FAMILIES.get(conference["series"], [])))}" '
        f'data-size="{_attr(_value_slug(conference.get("size", "")))}" '
        f'data-icore="{_attr(icore.get(conference["series"], {}).get("rank", "Unranked"))}" '
        f'data-ccf="{_attr(ccf.get(conference["series"], {}).get("rank", "Unranked"))}" '
        f'data-acceptance="{_attr(_value_slug(band))}" '
        f'data-confidence="{_attr(conference["confidence"])}" '
        f'data-conference-start="{_attr(conference["conference_start"])}" '
        f'data-conference-end="{_attr(conference["conference_end"])}"'
        + (f' data-deadlines="{_attr(json.dumps(deadlines, separators=(",", ":")))}"' if include_deadlines else "")
    )


def _milestones(conference: dict[str, Any]) -> list[dict[str, Any]]:
    milestones = []
    for deadline in conference.get("deadlines", []):
        milestones.append({
            "type": deadline["type"],
            "label": _display_deadline_label(deadline["label"]),
            "datetime": deadline["datetime"],
            "estimated": deadline.get("confidence", conference["confidence"]) != "confirmed",
            "approximate_time": deadline.get("time_precision") == "date",
            "show_time": True,
            "instant": _effective_cutoff(conference, deadline)[0],
            "host_zone": _effective_cutoff(conference, deadline)[1],
            "cutoff_note": deadline.get("cutoff_note"),
        })
        if deadline.get("opens_at"):
            # A recorded opening is always an exact published time (schema rule),
            # so it does not inherit the cutoff's date-only precision.
            milestones.append({
                "type": f'{deadline["type"]}_opens',
                "label": f'{_display_deadline_label(deadline["label"])} opens',
                "datetime": deadline["opens_at"],
                "estimated": deadline.get("confidence", conference["confidence"]) != "confirmed",
                "approximate_time": False,
                "show_time": True,
            })
    milestones.append({
        "type": "conference_start",
        "label": "Conference starts",
        "datetime": f'{conference["conference_start"]}T00:00:00Z',
        "estimated": conference["confidence"] in {"estimated", "not_yet_announced", "stale"},
        "show_time": False,
    })
    return sorted(milestones, key=lambda item: item.get("instant") or _deadline_iso_utc(item["datetime"]))


def _shows_clock(milestone: dict[str, Any]) -> bool:
    """Only confirmed cutoffs with a published hour show a clock time (ADR-039)."""
    return (
        milestone.get("show_time", False)
        and not milestone["estimated"]
        and not milestone.get("approximate_time")
    )


def _deadline_grid_rows(milestones: list[dict[str, Any]], grid_id: str = "") -> str:
    rows = []
    for index, milestone in enumerate(milestones):
        deadline_utc = milestone.get("instant") or _deadline_iso_utc(milestone["datetime"])
        row_hidden = "" if index == 0 else " hidden"
        estimate = ' <span class="milestone-estimate" title="Estimated date">(est.)</span>' if milestone["estimated"] else ""
        time_title = ""
        if milestone.get("approximate_time") and not milestone["estimated"]:
            tooltip = TIME_ESTIMATE_TOOLTIP
            if milestone.get("host_zone"):
                tooltip = (f"Official day; exact hour/timezone unannounced. The countdown ends at "
                           f"23:59 {milestone['host_zone']} time, the earliest likely cutoff.")
            time_title = f' title="{_attr(tooltip)}"'
        clock = local = ""
        if _shows_clock(milestone):
            clock = (
                f'<span class="deadline-clock" data-offset="{_offset_minutes(milestone["datetime"])}">'
                f'{escape(_clock_label(milestone["datetime"]))}</span>'
            )
            local = '<span class="deadline-local" data-local-time hidden></span>'
        when = (f'<time datetime="{_attr(deadline_utc)}"{time_title}>'
                f"{escape(_display_deadline_datetime(milestone['datetime']))}</time>")
        note = ""
        if milestone.get("cutoff_note"):
            # Official sources disagree; the stored instant is the earliest one.
            mark = (f'<span class="cutoff-note-mark" title="{_attr(milestone["cutoff_note"])}" '
                    f'aria-hidden="true">*</span>')
            note = (f'<span class="deadline-note"><span class="visually-hidden">Note: </span>'
                    f'* {escape(milestone["cutoff_note"])}</span>')
            if clock:
                clock = f'<span class="deadline-clock-wrap">{clock}{mark}</span>'
            else:
                when = f'<span class="deadline-clock-wrap is-date">{when}{mark}</span>'
        rows.append(
            f'<div class="deadline-grid-row" data-deadline-row data-entry-index="{index}" '
            f'data-deadline-type="{_attr(milestone["type"])}"{row_hidden}>'
            f"{when}{clock}{estimate}"
            f'<span class="deadline-milestone">'
            f"{escape(milestone['label'])}</span>{local}{note}"
            f'<span class="deadline-passed" data-deadline-passed="{_attr(deadline_utc)}"></span>'
            "</div>"
        )
    grid_attr = f' id="{_attr(grid_id)}"' if grid_id else ""
    return f'<div class="deadline-grid" data-deadline-grid{grid_attr}>{"".join(rows)}</div>'


def _mobile_row_disclosure(title: str) -> str:
    icon = _icon("chevron-down")
    return (
        '<td class="mobile-row-disclosure" colspan="8">'
        f'<button class="mobile-info-toggle" type="button" aria-expanded="false" '
        f'aria-label="More info for {_attr(title)}">'
        '<span data-mobile-info-label>More info</span>'
        f'<span aria-hidden="true">{icon}</span></button></td>'
    )


def _deadline_group_rows(
    conferences: list[dict[str, Any]],
    icore: dict[str, Any],
    ccf: dict[str, Any],
    ccf_page: str,
    rates: dict[str, Any],
    successors: dict[str, dict[str, Any]] | None = None,
) -> str:
    successors = successors or {}
    rows = []
    for conference in conferences:
        milestones = _milestones(conference)
        search_extras = []
        for deadline in conference.get("deadlines", []):
            # Labels and types are searchable; source URLs are not (they made
            # queries such as "2026" match later editions via old links).
            search_extras.extend([_display_deadline_label(deadline["label"]), deadline["type"]])
        search_text = _search_text(conference, search_extras)
        group_id = stable_slug(conference["id"])
        grid_id = f"milestones-{group_id}"
        toggle_html = ""
        if len(milestones) > 1:
            toggle_html = (
                f"<button class=\"deadline-toggle\" type=\"button\" aria-expanded=\"false\" "
                f"aria-controls=\"{_attr(grid_id)}\" "
                f"aria-label=\"Show milestones for {_attr(conference['short_title'])}\">"
                "<span class=\"expand-icon\" aria-hidden=\"true\">&#9656;</span>"
                "</button>"
            )
        successor_html = ""
        following = successors.get(conference["id"])
        if following:
            successor_html = (
                f'<a class="successor-link" data-successor-link href="#deadline-{_attr(following["id"])}" '
                f'data-successor="{_attr(following["id"])}" hidden>'
                f'Next: {escape(following["short_title"])}</a>'
            )
        rows.append(
            f'<tr class="deadline-group-row" id="deadline-{_attr(group_id)}" '
            f'{_filter_attributes(conference, search_text, icore, ccf, rates)} '
            f'data-deadline-group="{_attr(group_id)}" data-expanded="false">'
            f"<td data-label=\"Conference\"><a href=\"{_attr(conference['website'])}\">{escape(conference['short_title'])}</a>{_star_button(conference)}</td>"
            '<td data-label="Submission status"><div class="status-cell">'
            '<span class="submission-status" data-submission-status>Checking...</span>'
            '<span class="next-step" data-next-step hidden></span>'
            f'{successor_html}</div></td>'
            '<td data-label="Time left"><div class="time-left-cell">'
            '<span class="time-left" data-time-left aria-hidden="true">&mdash;</span>'
            '<span class="visually-hidden" data-time-left-sr></span>'
            f'<span class="time-estimate" data-time-estimate hidden title="{_attr(TIME_ESTIMATE_TOOLTIP)}">(time est.)</span>'
            '</div></td>'
            f'<td class="deadline-combined-cell mobile-detail" data-label="Next milestone"><div class="deadline-cell-content">{toggle_html}<div class="milestone-stack">{_deadline_grid_rows(milestones, grid_id)}{_evidence_line(conference)}</div></div></td>'
            f"<td class=\"mobile-detail\" data-label=\"Topics\">{_topic_labels(conference.get('topics', []))}</td>"
            f'<td class="mobile-detail" data-label="Accept. rate">{_acceptance_cell(conference, rates)}</td>'
            f'<td class="mobile-detail" data-label="ICORE / CCF">{_ranking_cell(conference, icore, ccf, ccf_page)}</td>'
            f"<td class=\"mobile-detail\" data-label=\"Size\">{_metadata_label(conference.get('size', ''))}</td>"
            f"{_mobile_row_disclosure(conference['short_title'])}"
            "</tr>"
        )
    return "\n".join(rows)


def _conference_rows(
    conferences: list[dict[str, Any]],
    icore: dict[str, Any],
    ccf: dict[str, Any],
    ccf_page: str,
    rates: dict[str, Any],
) -> str:
    rows = []
    for conference in sorted(
        conferences,
        key=lambda item: (parse_date(item["conference_start"]), item["id"]),
    ):
        search_text = _search_text(conference)
        date_estimate = (
            ' <span class="milestone-estimate" title="Conference dates estimated">(est.)</span>'
            if conference["confidence"] in {"estimated", "not_yet_announced", "stale"}
            else ""
        )
        rows.append(
            f'<tr id="conference-{_attr(stable_slug(conference["id"]))}" '
            f'{_filter_attributes(conference, search_text, icore, ccf, rates, include_deadlines=False)} data-conference-row>'
            f"<td data-label=\"Conference\"><a href=\"{_attr(conference['website'])}\">{escape(conference['short_title'])}</a>{_star_button(conference)}</td>"
            f"<td data-label=\"Dates\">{escape(_display_conference_dates(conference['conference_start'], conference['conference_end']))}{date_estimate}</td>"
            f"<td data-label=\"Location\">{escape(conference.get('location', 'TBD'))}</td>"
            f"<td class=\"mobile-detail\" data-label=\"Topics\">{_topic_labels(conference.get('topics', []))}</td>"
            f'<td class="mobile-detail" data-label="Accept. rate">{_acceptance_cell(conference, rates)}</td>'
            f'<td class="mobile-detail" data-label="ICORE / CCF">{_ranking_cell(conference, icore, ccf, ccf_page)}</td>'
            f"<td class=\"mobile-detail\" data-label=\"Size\">{_metadata_label(conference.get('size', ''))}</td>"
            f"<td class=\"mobile-detail\" data-label=\"Calendar\">{_conference_calendar_link(conference)}</td>"
            f"{_mobile_row_disclosure(conference['short_title'])}"
            "</tr>"
        )
    return "\n".join(rows)


def _max_last_checked(conferences: list[dict[str, Any]]) -> str:
    dates = [parse_date(conference["last_checked"]) for conference in conferences]
    if not dates:
        return "unknown"
    latest = max(dates)
    return f"{MONTHS[latest.month - 1]} {latest.day}, {latest.year}"


def _load_metadata(path: Path = METADATA_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def _dataset_last_updated(conferences: list[dict[str, Any]]) -> str:
    metadata = _load_metadata()
    if metadata.get("last_updated"):
        updated = parse_date(metadata["last_updated"])
        return f"{MONTHS[updated.month - 1]} {updated.day}, {updated.year}"
    return _max_last_checked(conferences)


def _topics(conferences: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {topic for conference in conferences for topic in all_topics(conference)},
        key=lambda value: value.casefold(),
    )


def _unique_values(conferences: list[dict[str, Any]], field: str) -> list[str]:
    return sorted(
        {
            str(conference[field])
            for conference in conferences
            if str(conference.get(field, "")).strip()
        },
        key=lambda value: value.casefold(),
    )


def _checkbox_group(
    label: str,
    group: str,
    values: list[str],
    slug_values: bool = True,
    link_href: str | None = None,
) -> str:
    boxes = []
    for value in values:
        filter_value = stable_slug(value) if slug_values else value
        boxes.append(
            "<label class=\"check-option\">"
            f"<input type=\"checkbox\" data-filter-group=\"{_attr(group)}\" "
            f"value=\"{_attr(filter_value)}\">"
            f"<span>{escape(value)}</span>"
            "</label>"
        )
    heading = escape(label)
    if link_href:
        heading = f'<a href="{_attr(link_href)}">{heading}</a>'
    return (
        "<fieldset class=\"filter-group\">"
        f"<legend>{heading}</legend>"
        f"<div class=\"check-list\">{''.join(boxes)}</div>"
        "</fieldset>"
    )


FEED_ROWS = [
    ("submissions.ics", "Submission deadlines",
     "New-paper and abstract deadlines, including required registration steps"),
    ("calendar-all.ics", "All events", "Meeting dates plus every recorded milestone"),
    ("conferences.ics", "Conference dates", "Meeting dates only"),
]


def _feed_actions(path: str, name: str) -> str:
    https_url = SITE_URL + path
    webcal_url = "webcal://" + https_url.split("://", 1)[1]
    google_url = "https://calendar.google.com/calendar/render?cid=" + webcal_url
    return (
        f'<div class="feed-actions" data-feed-actions data-feed-name="{_attr(name)}">'
        f'<a class="feed-link" data-feed-google href="{_attr(google_url)}" target="_blank" '
        f'rel="noopener noreferrer" title="Subscribe in Google Calendar">Google</a>'
        f'<a class="feed-link" data-feed-webcal href="{_attr(webcal_url)}" '
        f'title="Subscribe in Apple Calendar or another app that opens webcal links">Apple</a>'
        f'<button class="feed-link" type="button" data-copy-feed="{_attr(https_url)}" '
        f'title="Copy the feed address to paste into Outlook or any calendar app">Copy link</button>'
        f'<a class="feed-link" data-feed-download href="{_attr(path)}" download '
        f'title="Download a one-time snapshot; it will not receive updates">Download</a>'
        '</div>'
    )


def _calendar_menu(conferences: list[dict[str, Any]], icon: str) -> str:
    rows = "".join(
        f'<li class="feed-row"><div class="feed-name"><strong>{escape(name)}</strong>'
        f'<span>{escape(description)}</span></div>{_feed_actions(path, name)}</li>'
        for path, name, description in FEED_ROWS
    )
    topics = sorted(
        {topic for conference in conferences for topic in all_topics(conference)},
        key=lambda topic: TOPIC_CATALOG["labels"].get(topic, topic).casefold(),
    )
    topic_options = "".join(
        f'<option value="tags/{_attr(stable_slug(topic))}.ics">'
        f'{escape(TOPIC_CATALOG["labels"].get(topic, topic))}</option>'
        for topic in topics
    )
    groups = sorted(series_groups(conferences).items(),
                    key=lambda item: series_display_name(item[1]).casefold())
    series_options = "".join(
        f'<option value="series/{_attr(slug)}.ics" data-series-slug="{_attr(slug)}">'
        f'{escape(series_display_name(group))}</option>'
        for slug, group in groups
    )
    first_topic = f"tags/{stable_slug(topics[0])}.ics"
    first_series = f"series/{groups[0][0]}.ics"
    pickers = (
        '<li class="feed-row feed-picker"><label class="feed-name" for="feed-topic">'
        '<strong>One topic</strong><span>All events for a subtopic</span></label>'
        f'<select id="feed-topic" data-feed-select>{topic_options}</select>'
        f'{_feed_actions(first_topic, "Topic feed")}</li>'
        '<li class="feed-row" data-starred-feeds hidden><div class="feed-name"><strong>Your starred series</strong>'
        '<span>Pick one to subscribe to all its editions</span></div><div class="feed-actions" data-starred-list></div></li>'
        '<li class="feed-row feed-picker"><label class="feed-name" for="feed-series">'
        '<strong>One conference series</strong><span>Every edition, including future ones</span></label>'
        f'<select id="feed-series" data-feed-select>{series_options}</select>'
        f'{_feed_actions(first_series, "Series feed")}</li>'
    )
    return (
        f'<details class="calendar-menu" id="calendar-menu" data-site-url="{_attr(SITE_URL)}">'
        f'<summary class="calendar-button">{icon}Subscribe to calendar</summary>'
        '<div class="calendar-panel">'
        '<p class="calendar-panel-intro">Subscribed feeds update automatically when Venue Radar changes.</p>'
        f'<ul class="feed-list">{rows}{pickers}</ul>'
        '<p class="calendar-panel-note">Outlook: Add calendar &rarr; Subscribe from web, then paste a '
        'copied link. Google can take up to a day to refresh. Single-edition files are in the '
        'Conferences &amp; Map table.</p>'
        '</div></details>'
    )


def _topic_filter() -> str:
    families = []
    for family in TOPIC_CATALOG["families"]:
        children = ''.join(
            f'<label class="check-option"><input type="checkbox" data-filter-group="topics" '
            f'data-topic-family="{_attr(family["id"])}" value="{_attr(stable_slug(topic))}">'
            f'<span>{escape(TOPIC_CATALOG["labels"][topic])}</span></label>'
            for topic in family["topics"]
        )
        families.append(
            f'<details class="topic-family"><summary title="Expand or collapse subtopics"><label class="check-option">'
            f'<input type="checkbox" data-family-toggle="{_attr(family["id"])}" '
            f'title="{_attr("Central conference focus: " + family["label"])}">'
            f'<span>{escape(family["label"])}</span></label></summary>'
            f'<div class="check-list">{children}</div></details>'
        )
    return '<fieldset class="topic-filter"><legend>Topics &amp; Subtopics</legend><div class="topic-tree">' + ''.join(families) + '</div></fieldset>'


def build_site(
    data_path: Path = DATA_PATH,
    docs_dir: Path = DOCS_DIR,
    rankings_path: Path = ICORE_PATH,
    ccf_path: Path = CCF_PATH,
    acceptance_path: Path = ACCEPTANCE_PATH,
    scopes_path: Path = SCOPES_PATH,
) -> Path:
    conferences = load_conferences(data_path)
    icore_data = load_icore_rankings(rankings_path)
    ccf_data = load_ccf_rankings(ccf_path)
    acceptance_data = load_acceptance_rates(acceptance_path)
    scopes = load_scopes(scopes_path)
    errors = validate_conferences(conferences, load_controlled_topics())
    cities = load_mapping(CITIES_PATH)
    errors.extend(validate_catalog_metadata(load_controlled_topics() or set(), TOPIC_CATALOG, cities))
    errors.extend(validate_conference_families(conferences, CONFERENCE_FAMILIES, TOPIC_CATALOG,
                                              allow_extra=data_path != DATA_PATH))
    errors.extend(validate_icore_rankings(conferences, icore_data))
    errors.extend(validate_ccf_rankings(conferences, ccf_data))
    errors.extend(validate_acceptance_rates(conferences, acceptance_data))
    errors.extend(validate_scopes(conferences, scopes, load_controlled_topics() or set()))
    if errors:
        raise ValueError("conference data is invalid; run scripts/validate.py")
    conferences = with_scopes(conferences, scopes)

    docs_dir.mkdir(parents=True, exist_ok=True)
    output = docs_dir / "index.html"
    last_updated = _dataset_last_updated(conferences)
    icore = icore_data["rankings"]
    ccf = ccf_data["rankings"]
    ccf_page = ccf_data["page_url"]
    rates = acceptance_data["rates"]
    logo = 'data:image/png;base64,' + base64.b64encode((ASSETS_DIR / 'venue-radar.png').read_bytes()).decode('ascii')
    favicon = 'data:image/svg+xml;base64,' + base64.b64encode((ASSETS_DIR / 'favicon.svg').read_bytes()).decode('ascii')
    share_url = "https://x.com/intent/tweet?" + urlencode({"text": SHARE_TEXT, "url": SITE_URL})
    title_font = base64.b64encode((ASSETS_DIR / 'vendor' / 'audiowide-latin.woff2').read_bytes()).decode('ascii')
    # Base layout/component styles, then site.css brand and responsive overrides.
    base_css = (ASSETS_DIR / 'base.css').read_text(encoding='utf-8')
    custom_css = (ASSETS_DIR / 'site.css').read_text(encoding='utf-8')
    leaflet_css = (ASSETS_DIR / 'vendor' / 'leaflet.css').read_text(encoding='utf-8')
    leaflet_js = (ASSETS_DIR / 'vendor' / 'leaflet.js').read_text(encoding='utf-8')
    custom_js = (ASSETS_DIR / 'site.js').read_text(encoding='utf-8')
    # Core client logic lives in assets/ (pure helpers first) instead of this template.
    logic_js = (ASSETS_DIR / 'logic.js').read_text(encoding='utf-8')
    core_js = (ASSETS_DIR / 'core.js').read_text(encoding='utf-8')
    venue_config = json.dumps({'submissionTypes': sorted(SUBMISSION_TYPES)}).replace('</', '<\\/')
    map_data = json.dumps({
        'events': map_events(conferences, cities),
        'land': _round_coordinates(json.loads((ASSETS_DIR / 'vendor' / 'world-land.geojson').read_text())),
        'resetIcon': (ASSETS_DIR / 'vendor' / 'globe.svg').read_text(encoding='utf-8'),
    }, separators=(',', ':')).replace('</', '<\\/')
    calendar_icon = (ASSETS_DIR / 'vendor' / 'calendar-plus.svg').read_text(encoding='utf-8')
    calendar_menu = _calendar_menu(conferences, calendar_icon)
    successors = _successors(conferences)
    share_icon = (ASSETS_DIR / 'vendor' / 'share-2.svg').read_text(encoding='utf-8')
    star_icon = (ASSETS_DIR / 'vendor' / 'star.svg').read_text(encoding='utf-8')
    vendor_notices = '\n\n'.join(
        (ASSETS_DIR / 'vendor' / name).read_text(encoding='utf-8')
        for name in ['Leaflet-LICENSE', 'Lucide-LICENSE', 'Audiowide-OFL.txt']
    ).replace('--', '- -')
    vendor_notices = '\n'.join(line.rstrip() for line in vendor_notices.splitlines())

    html = f"""<!doctype html>
<!-- Embedded third-party license notices:
{vendor_notices}
-->
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(PAGE_TITLE)}</title>
  <meta name="description" content="{_attr(PAGE_DESCRIPTION)}">
  <link rel="canonical" href="{_attr(SITE_URL)}">
  <meta name="theme-color" content="#0e5d62">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Venue Radar">
  <meta property="og:title" content="{_attr(PAGE_TITLE)}">
  <meta property="og:description" content="{_attr(PAGE_DESCRIPTION)}">
  <meta property="og:url" content="{_attr(SITE_URL)}">
  <meta property="og:image" content="{_attr(SOCIAL_CARD_URL)}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="Venue Radar logo with the line: conference deadlines for machine learning, AI, neuroscience, healthcare, complex systems and control.">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{_attr(PAGE_TITLE)}">
  <meta name="twitter:description" content="{_attr(PAGE_DESCRIPTION)}">
  <meta name="twitter:image" content="{_attr(SOCIAL_CARD_URL)}">
  <link rel="icon" type="image/svg+xml" sizes="any" href="{favicon}">
  <style>
{base_css}    {leaflet_css}
    @font-face {{
      font-family: Audiowide;
      font-style: normal;
      font-weight: 400;
      font-display: swap;
      src: url(data:font/woff2;base64,{title_font}) format('woff2');
    }}
    {custom_css}
  </style>
  <noscript><style>
    /* Without JavaScript, show every table, date and milestone (no live status). */
    #panel-conferences[hidden] {{ display: block !important; }}
    .deadline-grid-row[hidden] {{ display: flex !important; }}
    .evidence-line {{ display: flex !important; }}
    .status-guide-live {{ display: none !important; }}
    .table-tabs, .open-toggle, .toolbar-actions, .filter-section, .map-section,
    .deadline-toggle, .calendar-menu > .calendar-panel .feed-picker, [data-copy-feed] {{ display: none !important; }}
    #panel-deadlines col:nth-child(2), #panel-deadlines col:nth-child(3),
    #panel-deadlines th:nth-child(2), #panel-deadlines th:nth-child(3),
    #panel-deadlines td[data-label="Submission status"], #panel-deadlines td[data-label="Time left"] {{ display: none !important; }}
    .noscript-note {{ display: block !important; }}
  </style></noscript>
</head>
<body>
  {_icon_sprite()}
  <a class="skip-link" href="#tables">Skip to conference tables</a>
  <main>
    <header>
      <div class="brand-copy">
        <div class="brand-line"><img class="brand-mark" src="{logo}" alt="" width="82" height="82"><h1>Venue Radar</h1></div>
        <p class="subhead">Find where to submit next: conference deadlines for machine learning and AI, neuroscience, healthcare, complex systems, and control.</p>
      </div>
      <div class="header-actions">
        <a class="header-button share-button" href="{_attr(share_url)}" target="_blank" rel="noopener noreferrer" title="Prepare a post about Venue Radar on X">{share_icon}Share on X</a>
        <a class="header-button star-button" href="https://github.com/gon-uri/venue-radar" target="_blank" rel="noopener noreferrer" title="Open Venue Radar on GitHub to star the repository">{star_icon}Star the repo</a>
        <div class="calendar-action">
          {calendar_menu}
          <span class="calendar-caption">Auto-updating .ics feeds</span>
        </div>
      </div>
    </header>

    <section class="controls filter-section" aria-label="Filters and search">
    <details class="filter-details" id="filter-details" open>
      <summary><span class="filter-disclosure-icon" aria-hidden="true">&#9654;</span><span>Filters &amp; search</span><span class="filter-count" id="filter-count" hidden></span></summary>
      <div class="filter-content">
        <div class="filter-grid">
          {_topic_filter()}
          {_checkbox_group("Size", "size", ["S", "M", "L", "XL", "XXL"])}
          {_checkbox_group("ICORE Rank", "icore", ["A*", "A", "B", "C", "Unranked"], slug_values=False, link_href="https://portal.core.edu.au/conf-ranks/")}
          {_checkbox_group("CCF Rank", "ccf", ["A", "B", "C", "Unranked"], slug_values=False, link_href=ccf_page)}
          {_checkbox_group("Acceptance rate", "acceptance", ["Very low", "Low", "Moderate", "High", "Very high", "Unknown"])}
          <label class="search-control">
            <span class="control-label">Search</span>
            <input id="search" type="search" autocomplete="off" placeholder="Conference, topic, location, milestone">
          </label>
        </div>
        <div class="filter-actions">
          <label class="topic-mode"><span>Match</span><select id="topic-match" aria-label="Topic family matching"><option value="any">Any selected family</option><option value="all">All selected families</option></select></label>
        </div>
      </div>
    </details>
    <script>document.querySelector('#filter-details').open = !matchMedia('(max-width: 760px)').matches;</script>
    <button class="clear-filters" id="clear-filters" type="button">Clear filters</button>
    </section>

    <section class="tab-shell" id="tables" tabindex="-1" aria-label="Conference calendar tables">
      <p class="noscript-note">Live submission status, countdowns and filters need JavaScript. Every conference, date and milestone is still listed below.</p>
      <div class="tab-toolbar">
        <div class="table-tabs" role="tablist" aria-label="Table view">
          <button class="tab-button" id="tab-deadlines" type="button" role="tab" aria-selected="true" aria-controls="panel-deadlines" data-tab-target="deadlines">Upcoming Deadlines</button>
          <button class="tab-button" id="tab-conferences" type="button" role="tab" aria-selected="false" aria-controls="panel-conferences" data-tab-target="conferences" tabindex="-1">Conferences &amp; Map</button>
        </div>
        <label class="open-toggle"><input id="open-only" type="checkbox" checked>Show submission options only</label>
        <label class="starred-toggle" hidden><input id="starred-only" type="checkbox">Starred only <span data-starred-count></span></label>
        <div class="toolbar-actions">
          <span id="result-count" aria-live="polite"></span>
          <button class="link-button" id="show-hidden" type="button" hidden></button>
        </div>
      </div>

      <div class="tab-panel" id="panel-deadlines" role="tabpanel" aria-labelledby="tab-deadlines" data-tab-panel="deadlines">
        <details class="status-guide">
          <summary>What do the statuses mean?</summary>
          <dl>
            <div class="status-guide-live"><dt><span class="submission-status status-open">Open paper submissions</span></dt><dd>The submission site is confirmed open.</dd></div>
            <div class="status-guide-live"><dt><span class="submission-status status-scheduled">Scheduled submission</span></dt><dd>The deadline and the opening time are announced.</dd></div>
            <div class="status-guide-live"><dt><span class="submission-status status-opportunity">Submission opportunity</span></dt><dd>The deadline is confirmed; the opening is not verified.</dd></div>
            <div class="status-guide-live"><dt><span class="submission-status status-estimated">Submission opportunity (estimated)</span></dt><dd>Projected from the previous edition or not yet confirmed by the organizers.</dd></div>
            <div class="status-guide-live"><dt><span class="submission-status status-closed">Closed to new submissions</span></dt><dd>Every route for new work has passed (production steps may remain).</dd></div>
            <div class="status-guide-live"><dt><span class="submission-status status-unknown">Deadline unannounced</span></dt><dd>The meeting is known but no call is published yet.</dd></div>
            <div class="status-guide-live"><dt>~4d 14h · (est.)</dt><dd>Estimated countdown or date.</dd></div>
            <div><dt>(time est.)</dt><dd>Official day; the cutoff hour is not announced.</dd></div>
            <div><dt>*</dt><dd>Official sources disagree on the cutoff; the earliest stated time is shown, with the note below it.</dd></div>
          </dl>
        </details>
        <div class="empty-state" id="deadlines-empty" hidden></div>
        <div class="table-wrap">
          <table>
            <caption class="visually-hidden">Upcoming submission deadlines, ordered by the next required action</caption>
            {_colgroup(["12%", "14%", "7%", "30%", "15%", "9%", "9%", "4%"])}
            <thead>
              <tr>
                <th scope="col">Conference</th>
                <th scope="col">Submission status</th>
                <th scope="col">Time left</th>
                <th scope="col">Next milestone</th>
                <th scope="col">Topics</th>
                <th scope="col">Accept. rate</th>
                <th scope="col">ICORE / CCF</th>
                <th scope="col">Size</th>
              </tr>
            </thead>
            <tbody id="deadlines-body">
              {_deadline_group_rows(conferences, icore, ccf, ccf_page, rates, successors)}
            </tbody>
          </table>
        </div>
      </div>

      <div class="tab-panel" id="panel-conferences" role="tabpanel" aria-labelledby="tab-conferences" data-tab-panel="conferences" hidden>
        <section class="map-section" aria-label="Confirmed upcoming conference locations">
          <div class="map-heading"><span id="map-count" aria-live="polite"></span></div>
          <div id="conference-map" aria-label="World map of confirmed upcoming conferences"></div>
          <p id="map-empty" class="map-empty" hidden>No confirmed upcoming locations match these filters.</p>
          <div id="map-cities" class="map-cities" aria-label="Conference cities"></div>
        </section>
        <div class="empty-state" id="conferences-empty" hidden></div>
        <div class="table-wrap">
          <table>
            <caption class="visually-hidden">Upcoming conferences by meeting date</caption>
            {_colgroup(["15%", "15%", "16%", "22%", "10%", "10%", "5%", "7%"])}
            <thead>
              <tr>
                <th scope="col">Conference</th>
                <th scope="col">Dates</th>
                <th scope="col">Location</th>
                <th scope="col">Topics</th>
                <th scope="col">Accept. rate</th>
                <th scope="col">ICORE / CCF</th>
                <th scope="col">Size</th>
                <th scope="col">Calendar</th>
              </tr>
            </thead>
            <tbody id="upcoming-conferences-body">
              {_conference_rows(conferences, icore, ccf, ccf_page, rates)}
            </tbody>
          </table>
        </div>
        <details id="past-conferences-section" hidden>
          <summary>Ongoing and past conferences</summary>
          <div class="table-wrap">
            <table>
              <caption class="visually-hidden">Ongoing and past conferences</caption>
              {_colgroup(["15%", "15%", "16%", "22%", "10%", "10%", "5%", "7%"])}
              <thead><tr><th scope="col">Conference</th><th scope="col">Dates</th><th scope="col">Location</th><th scope="col">Topics</th><th scope="col">Accept. rate</th><th scope="col">ICORE / CCF</th><th scope="col">Size</th><th scope="col">Calendar</th></tr></thead>
              <tbody id="past-conferences-body"></tbody>
            </table>
          </div>
        </details>
      </div>
    </section>

    <section class="community" id="community" aria-labelledby="community-title">
      <h2 id="community-title">Community</h2>
      <p>Missing a conference, or spotted a correction? Leave a comment or send a conference request.</p>
      <div class="community-links">
        <a href="https://github.com/gon-uri/venue-radar/issues/new?template=conference-request.yml">Request a conference</a>
        <a href="https://github.com/gon-uri/venue-radar/discussions">GitHub discussions</a>
        <a href="https://github.com/gon-uri/venue-radar">Find Venue Radar useful? Star the repository</a>
        <a href="https://x.com/gonzauri">Follow @gonzauri on X</a>
      </div>
      <div class="giscus"></div>
      <noscript><a href="https://github.com/gon-uri/venue-radar/discussions">Join the discussion on GitHub</a></noscript>
    </section>
    <footer>
      <strong>Database last updated {escape(last_updated)}.</strong>
      The calendar is reviewed regularly as organizers publish new schedules. An estimated submission status or date means the information is uncertain. Some estimated dates use prior-edition timing as a proxy until organizers publish the next schedule.
      <div>ICORE 2026 and CCF 2026 ranks are separate assessments of main-track full papers; a dash means no direct rank is shown. Historical acceptance rates refer to the linked year and track, not the next edition's expected outcome. Unknown means no defensible rate is available.</div>
      <div>Size is a qualitative scale, not a verified attendance count. A time-estimated milestone has a published day but no confirmed cutoff hour. Always check the organizer's call before submitting.</div>
      <div class="author">Created and maintained by <strong>Gonzalo Uribarri</strong>.</div>
      <div class="author-links"><a href="https://www.su.se/profiles/g/gour8957">University profile</a><a href="https://scholar.google.com/citations?user=q5sweuIAAAAJ&amp;hl=en">Google Scholar</a><a href="https://github.com/gon-uri">GitHub</a><a href="https://github.com/gon-uri/venue-radar/blob/main/LICENSE">Code: MIT</a><a href="https://github.com/gon-uri/venue-radar/blob/main/CONTENT-LICENSE.md">Original content: CC BY 4.0</a></div>
    </footer>
  </main>
  <script>const venueMapData = {map_data};
  {custom_js}</script>
  <script type="application/json" id="venue-config">{venue_config}</script>
  <script>{logic_js}
{core_js}</script>
  <script>{leaflet_js}
  updateConferenceMap();</script>
</body>
</html>
"""
    output.write_text(html, encoding="utf-8")
    return output


def main() -> int:
    output = build_site()
    print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

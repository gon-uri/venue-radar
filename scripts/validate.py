from __future__ import annotations

import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "conferences.yml"
TOPICS_PATH = ROOT / "data" / "topics.yml"
ICORE_PATH = ROOT / "data" / "icore_rankings.yml"
CCF_PATH = ROOT / "data" / "ccf_rankings.yml"
ACCEPTANCE_PATH = ROOT / "data" / "acceptance_rates.yml"

REQUIRED_FIELDS = {
    "id",
    "series",
    "year",
    "title",
    "short_title",
    "website",
    "conference_start",
    "conference_end",
    "topics",
    "size",
    "submission_type",
    "deadlines",
    "last_checked",
    "confidence",
}

VALID_CONFIDENCE = {
    "confirmed",
    "estimated",
    "announced_no_deadlines",
    "not_yet_announced",
    "stale",
}

VALID_RELEVANCE = {"high", "medium", "low", "watch"}
VALID_ICORE_RANKS = {"A*", "A", "B", "C"}
VALID_CCF_RANKS = {"A", "B", "C"}
VALID_SIZES = {"S", "M", "L", "XL", "XXL"}
SUBMISSION_TYPES = {
    "full_paper", "regular_paper", "short_paper", "workshop_paper",
    "special_session_paper", "abstract", "late_abstract",
    "extended_abstract", "poster",
    "journal_paper", "discussion_paper", "resource_paper",
}
ACCEPTANCE_BANDS = (
    (20, "Very low"),
    (30, "Low"),
    (40, "Moderate"),
    (60, "High"),
    (101, "Very high"),
)

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def stable_slug(value: Any) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError(f"expected ISO date string, got {type(value).__name__}")


def parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise TypeError(f"expected ISO datetime string, got {type(value).__name__}")


def load_conferences(path: Path = DATA_PATH) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a YAML list of conferences")
    return data


def load_controlled_topics(path: Path = TOPICS_PATH) -> set[str] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, list) or not all(_non_empty_string(item) for item in data):
        raise ValueError(f"{path} must contain a YAML list of topic strings")
    return {str(item) for item in data}


def load_icore_rankings(path: Path = ICORE_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def load_ccf_rankings(path: Path = CCF_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def load_acceptance_rates(path: Path = ACCEPTANCE_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def acceptance_band(percent: float) -> str:
    for limit, label in ACCEPTANCE_BANDS:
        if percent < limit:
            return label
    raise ValueError("acceptance percent must be below 101")


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        _non_empty_string(item) for item in value
    )


def _has_source_urls(conference: dict[str, Any]) -> bool:
    return _non_empty_string_list(conference.get("source_urls"))


def validate_conferences(
    conferences: list[dict[str, Any]], controlled_topics: set[str] | None = None
) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()

    for index, conference in enumerate(conferences, start=1):
        label = f"entry #{index}"
        if not isinstance(conference, dict):
            errors.append(f"{label}: must be a mapping")
            continue

        conference_id = conference.get("id", f"<missing-{index}>")
        label = str(conference_id)

        missing = sorted(REQUIRED_FIELDS - set(conference))
        for field in missing:
            errors.append(f"{label}: missing required field '{field}'")
        if "difficulty" in conference:
            errors.append(f"{label}: legacy difficulty field must be removed")

        if "id" in conference:
            if not _non_empty_string(conference["id"]):
                errors.append(f"{label}: id must be a non-empty string")
            elif not ID_RE.match(conference["id"]):
                errors.append(
                    f"{label}: id must use lowercase letters, numbers, and hyphens"
                )
            elif conference["id"] in seen_ids:
                errors.append(f"{label}: duplicate id")
            seen_ids.add(conference["id"])

        for field in (
            "series",
            "title",
            "short_title",
            "website",
            "size",
            "submission_type",
        ):
            if field in conference and not _non_empty_string(conference[field]):
                errors.append(f"{label}: {field} must be a non-empty string")

        if "year" in conference and not isinstance(conference["year"], int):
            errors.append(f"{label}: year must be an integer")
        if conference.get("size") not in VALID_SIZES:
            errors.append(f"{label}: size must be S, M, L, XL, or XXL")

        start = None
        end = None
        if "conference_start" in conference:
            try:
                start = parse_date(conference["conference_start"])
            except (TypeError, ValueError) as exc:
                errors.append(f"{label}: conference_start is invalid: {exc}")
        if "conference_end" in conference:
            try:
                end = parse_date(conference["conference_end"])
            except (TypeError, ValueError) as exc:
                errors.append(f"{label}: conference_end is invalid: {exc}")
        if start and end and end < start:
            errors.append(f"{label}: conference_end is before conference_start")

        if "last_checked" in conference:
            try:
                parse_date(conference["last_checked"])
            except (TypeError, ValueError) as exc:
                errors.append(f"{label}: last_checked is invalid: {exc}")

        if "source_urls" in conference and not _non_empty_string_list(
            conference["source_urls"]
        ):
            errors.append(f"{label}: source_urls must be a non-empty list of strings")

        confidence = conference.get("confidence")
        if "confidence" in conference and confidence not in VALID_CONFIDENCE:
            errors.append(
                f"{label}: confidence must be one of {sorted(VALID_CONFIDENCE)}"
            )

        relevance = conference.get("relevance")
        if relevance is not None and relevance not in VALID_RELEVANCE:
            errors.append(f"{label}: relevance must be one of {sorted(VALID_RELEVANCE)}")

        topics = conference.get("topics")
        if "topics" in conference:
            if not isinstance(topics, list) or not topics:
                errors.append(f"{label}: topics must be a non-empty list")
            else:
                if len(topics) > 4 or len(set(map(str, topics))) != len(topics):
                    errors.append(f"{label}: use at most four distinct central subtopics")
                for topic in topics:
                    if not _non_empty_string(topic):
                        errors.append(f"{label}: topics must contain non-empty strings")
                    elif controlled_topics is not None and topic not in controlled_topics:
                        errors.append(
                            f"{label}: topic '{topic}' is not in data/topics.yml"
                        )

        if confidence == "confirmed" and not _has_source_urls(conference):
            errors.append(
                f"{label}: confirmed conference dates require at least one source_urls entry"
            )

        deadlines = conference.get("deadlines")
        if "deadlines" in conference:
            if not isinstance(deadlines, list):
                errors.append(f"{label}: deadlines must be a list")
            else:
                seen_deadline_keys: set[str] = set()
                for deadline_index, deadline in enumerate(deadlines, start=1):
                    deadline_label = f"{label}: deadline #{deadline_index}"
                    if not isinstance(deadline, dict):
                        errors.append(f"{deadline_label}: must be a mapping")
                        continue

                    for field in ("type", "label", "datetime"):
                        if field not in deadline:
                            errors.append(f"{deadline_label}: missing '{field}'")
                    if deadline.get("time_precision", "exact") not in {"exact", "date"}:
                        errors.append(f"{deadline_label}: time_precision must be exact or date")

                    deadline_type = deadline.get("type")
                    if "type" in deadline:
                        if not _non_empty_string(deadline_type):
                            errors.append(f"{deadline_label}: type must be non-empty")
                        else:
                            uid_key = stable_slug(deadline_type)
                            if not uid_key:
                                errors.append(
                                    f"{deadline_label}: type cannot form a stable UID"
                                )
                            elif uid_key in seen_deadline_keys:
                                errors.append(
                                    f"{deadline_label}: duplicate deadline type '{deadline_type}'"
                                )
                            seen_deadline_keys.add(uid_key)

                    if "label" in deadline and not _non_empty_string(
                        deadline["label"]
                    ):
                        errors.append(f"{deadline_label}: label must be non-empty")

                    if "datetime" in deadline:
                        try:
                            if parse_datetime(deadline["datetime"]).utcoffset() is None:
                                # The site would read a naive time as UTC while ICS
                                # exports floating local time; require an offset.
                                errors.append(f"{deadline_label}: datetime needs an explicit UTC offset")
                        except (TypeError, ValueError) as exc:
                            errors.append(f"{deadline_label}: datetime is invalid: {exc}")

                    if "source_url" in deadline and not _non_empty_string(
                        deadline["source_url"]
                    ):
                        errors.append(f"{deadline_label}: source_url must be non-empty")

                    if "cutoff_note" in deadline and not (
                        _non_empty_string(deadline["cutoff_note"]) and len(deadline["cutoff_note"]) <= 200
                    ):
                        errors.append(f"{deadline_label}: cutoff_note must be a non-empty string of at most 200 characters")

                    if "confidence" in deadline and deadline["confidence"] not in {"confirmed", "estimated"}:
                        errors.append(f"{deadline_label}: confidence must be confirmed or estimated")

                    for field in ("opens_at", "open_observed_on"):
                        if field not in deadline:
                            continue
                        try:
                            opening = parse_datetime(deadline[field]) if field == "opens_at" else parse_date(deadline[field])
                            closing = parse_datetime(deadline["datetime"])
                            if field == "opens_at" and opening.utcoffset() is None:
                                errors.append(f"{deadline_label}: opens_at needs an explicit UTC offset")
                            opening_day = opening.date() if isinstance(opening, datetime) else opening
                            if opening_day > closing.date():
                                errors.append(f"{deadline_label}: {field} is after deadline")
                        except (KeyError, TypeError, ValueError) as exc:
                            errors.append(f"{deadline_label}: {field} is invalid: {exc}")

                    if (
                        conference.get("confidence") == "confirmed"
                        and not _non_empty_string(deadline.get("source_url"))
                    ):
                        errors.append(
                            f"{deadline_label}: confirmed deadlines require source_url"
                        )

                by_type = {
                    deadline.get("type"): deadline
                    for deadline in deadlines
                    if isinstance(deadline, dict)
                    and _non_empty_string(deadline.get("type"))
                }
                for deadline in deadlines:
                    if not isinstance(deadline, dict) or "gate_for" not in deadline:
                        continue
                    target = by_type.get(deadline["gate_for"]) if isinstance(deadline["gate_for"], str) else None
                    if not target or target is deadline:
                        errors.append(
                            f"{label}: gate_for must name another deadline type in this edition"
                        )
                        continue
                    if deadline["gate_for"] not in SUBMISSION_TYPES:
                        errors.append(f"{label}: gate_for must target a submission route")
                    try:
                        if parse_datetime(deadline["datetime"]) >= parse_datetime(target["datetime"]):
                            errors.append(f"{label}: gate_for deadline must precede its target")
                    except (KeyError, TypeError, ValueError):
                        pass

    return errors


def validate_icore_rankings(
    conferences: list[dict[str, Any]], data: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    if data.get("release") != "ICORE2026":
        errors.append("ICORE release must be ICORE2026")
    try:
        parse_date(data.get("checked_on"))
    except (TypeError, ValueError):
        errors.append("ICORE checked_on must be an ISO date")
    source_url = data.get("source_url")
    if not _non_empty_string(source_url) or not source_url.startswith(
        "https://portal.core.edu.au/conf-ranks/"
    ):
        errors.append("ICORE source_url must point to the official conference portal")

    rankings = data.get("rankings")
    if not isinstance(rankings, dict):
        return errors + ["ICORE rankings must be a mapping"]

    series_records: dict[str, list[dict[str, Any]]] = {}
    for conference in conferences:
        if isinstance(conference, dict) and _non_empty_string(conference.get("series")):
            series_records.setdefault(conference["series"], []).append(conference)

    seen_portal_ids: set[int] = set()
    for series, entry in rankings.items():
        if not _non_empty_string(series) or series not in series_records:
            errors.append(f"ICORE series '{series}' is not in conferences.yml")
            continue
        if not isinstance(entry, dict):
            errors.append(f"ICORE {series}: entry must be a mapping")
            continue
        rank = entry.get("rank")
        if not isinstance(rank, str) or rank not in VALID_ICORE_RANKS:
            errors.append(f"ICORE {series}: rank must be A*, A, B, or C")
        portal_id = entry.get("portal_id")
        if type(portal_id) is not int or portal_id <= 0:
            errors.append(f"ICORE {series}: portal_id must be a positive integer")
        elif portal_id in seen_portal_ids:
            errors.append(f"ICORE {series}: duplicate portal_id {portal_id}")
        else:
            seen_portal_ids.add(portal_id)
        if any(
            "workshop" in str(record.get("submission_type", "")).lower()
            for record in series_records[series]
        ):
            errors.append(f"ICORE {series}: workshops must not inherit main-track ranks")
    return errors


def validate_ccf_rankings(
    conferences: list[dict[str, Any]], data: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    if data.get("release") != "CCF2026-7th":
        errors.append("CCF release must be CCF2026-7th")
    try:
        parse_date(data.get("checked_on"))
    except (TypeError, ValueError):
        errors.append("CCF checked_on must be an ISO date")
    if not _non_empty_string(data.get("source_url")) or not data["source_url"].startswith(
        "https://www.ccf.org.cn/ccf/contentcore/resource/download?"
    ):
        errors.append("CCF source_url must point to the official catalog PDF")
    page_url = data.get("page_url")
    if not _non_empty_string(page_url) or not page_url.startswith(
        "https://www.ccf.org.cn/Academic_Evaluation/"
    ):
        errors.append("CCF page_url must point to the official ranking webpage")
    rankings = data.get("rankings")
    if not isinstance(rankings, dict):
        return errors + ["CCF rankings must be a mapping"]
    series_records = {
        conference["series"]: conference
        for conference in conferences
        if isinstance(conference, dict) and _non_empty_string(conference.get("series"))
    }
    for series, entry in rankings.items():
        if series not in series_records:
            errors.append(f"CCF series '{series}' is not in conferences.yml")
            continue
        if not isinstance(entry, dict):
            errors.append(f"CCF {series}: entry must be a mapping")
            continue
        if not isinstance(entry.get("rank"), str) or entry["rank"] not in VALID_CCF_RANKS:
            errors.append(f"CCF {series}: rank must be A, B, or C")
        if type(entry.get("page")) is not int or entry["page"] <= 0:
            errors.append(f"CCF {series}: page must be a positive integer")
        if "workshop" in str(series_records[series].get("submission_type", "")).lower():
            errors.append(f"CCF {series}: workshops must not inherit main-track ranks")
    return errors


def validate_acceptance_rates(
    conferences: list[dict[str, Any]], data: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    try:
        parse_date(data.get("checked_on"))
    except (TypeError, ValueError):
        errors.append("Acceptance checked_on must be an ISO date")
    rates = data.get("rates")
    if not isinstance(rates, dict):
        return errors + ["Acceptance rates must be a mapping"]
    series = {
        conference["series"]
        for conference in conferences
        if isinstance(conference, dict) and _non_empty_string(conference.get("series"))
    }
    for name, entry in rates.items():
        label = f"Acceptance {name}"
        if name not in series:
            errors.append(f"{label}: unknown series")
            continue
        if not isinstance(entry, dict):
            errors.append(f"{label}: entry must be a mapping")
            continue
        percent = entry.get("percent")
        band = entry.get("band")
        if percent is None:
            if band not in {item[1] for item in ACCEPTANCE_BANDS}:
                errors.append(f"{label}: a qualitative-only entry requires a valid band")
            if not _non_empty_string(entry.get("basis")):
                errors.append(f"{label}: qualitative-only entry requires a basis")
        elif type(percent) not in (int, float) or not 0 < percent <= 100:
            errors.append(f"{label}: percent must be between 0 and 100")
        elif band is not None and band != acceptance_band(percent):
            errors.append(f"{label}: band does not match percent")
        if type(entry.get("year")) is not int or not 2000 <= entry["year"] <= date.today().year:
            errors.append(f"{label}: year must be a completed edition year")
        if not _non_empty_string(entry.get("track")):
            errors.append(f"{label}: track must be non-empty")
        if not _non_empty_string(entry.get("source_url")) or not entry["source_url"].startswith("https://"):
            errors.append(f"{label}: source_url must be HTTPS")
        if "approximate" in entry and type(entry["approximate"]) is not bool:
            errors.append(f"{label}: approximate must be boolean")
    return errors


def main() -> int:
    from catalog_metadata import CITIES_PATH, CONFERENCE_FAMILIES_PATH, FAMILIES_PATH, load_mapping, validate_catalog_metadata, validate_conference_families
    from conference_scopes import load_scopes, validate_scopes

    try:
        conferences = load_conferences()
        controlled_topics = load_controlled_topics()
        icore_rankings = load_icore_rankings()
        ccf_rankings = load_ccf_rankings()
        acceptance_rates = load_acceptance_rates()
        families = load_mapping(FAMILIES_PATH)
        assignments = load_mapping(CONFERENCE_FAMILIES_PATH)
        cities = load_mapping(CITIES_PATH)
        scopes = load_scopes()
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1

    errors = validate_conferences(conferences, controlled_topics)
    errors.extend(validate_catalog_metadata(controlled_topics or set(), families, cities))
    errors.extend(validate_conference_families(conferences, assignments, families))
    errors.extend(validate_icore_rankings(conferences, icore_rankings))
    errors.extend(validate_ccf_rankings(conferences, ccf_rankings))
    errors.extend(validate_acceptance_rates(conferences, acceptance_rates))
    errors.extend(validate_scopes(conferences, scopes, controlled_topics or set()))
    if errors:
        print("Validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Validated {len(conferences)} conferences.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

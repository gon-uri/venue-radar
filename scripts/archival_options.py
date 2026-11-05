"""Series-level archival option (ADR-047).

One sourced value per exact series in data/archival_options.yml. A series is
"yes" when at least one fresh-submission track publishes accepted papers in the
conference's own archival proceedings or journal (opt-in or opt-out counts).
Absent series are "not checked yet" and are never treated as "no".
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
ARCHIVAL_PATH = ROOT / "data" / "archival_options.yml"
ARCHIVAL_VALUES = ("yes", "no")
REQUIRED = ("archival", "estimated", "track", "source_url", "source_year", "checked")


def load_archival_options(path: Path = ARCHIVAL_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    options = data.get("options", {}) if isinstance(data, dict) else None
    if not isinstance(options, dict):
        raise ValueError(f"{path} must contain an 'options' mapping")
    return options


def archival_value(entry: dict[str, Any] | None, edition_year: int) -> dict[str, Any] | None:
    """Return the value shown for one edition, or None when not checked yet.

    A value read from an earlier edition's call is an estimate for this one,
    so the label follows the row and never goes stale as time passes.
    """
    if not entry:
        return None
    estimated = bool(entry["estimated"]) or int(entry["source_year"]) < int(edition_year)
    return {"archival": entry["archival"] == "yes", "estimated": estimated}


def archival_label(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    text = "Archival option" if value["archival"] else "Non-archival"
    return f"{text} (est.)" if value["estimated"] else text


def feed_label(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    text = "Yes" if value["archival"] else "No"
    return f"{text} (est.)" if value["estimated"] else text


def validate_archival_options(
    conferences: list[dict[str, Any]], options: dict[str, Any], today: date | None = None
) -> list[str]:
    today = today or date.today()
    latest: dict[str, int] = {}
    for conference in conferences:
        if isinstance(conference, dict) and isinstance(conference.get("series"), str):
            year = conference.get("year")
            if isinstance(year, int):
                latest[conference["series"]] = max(latest.get(conference["series"], 0), year)
    errors: list[str] = []
    for name, entry in options.items():
        label = f"Archival {name}"
        if name not in latest:
            errors.append(f"{label}: unknown series")
            continue
        if not isinstance(entry, dict):
            errors.append(f"{label}: entry must be a mapping")
            continue
        missing = [key for key in REQUIRED if key not in entry]
        if missing:
            errors.append(f"{label}: missing {', '.join(missing)}")
            continue
        unknown = set(entry) - set(REQUIRED) - {"note", "venue"}
        if unknown:
            errors.append(f"{label}: unknown fields {', '.join(sorted(unknown))}")
        if entry["archival"] not in ARCHIVAL_VALUES:
            errors.append(f"{label}: archival must be yes or no")
        if type(entry["estimated"]) is not bool:
            errors.append(f"{label}: estimated must be boolean")
        if not isinstance(entry["track"], str) or not entry["track"].strip():
            errors.append(f"{label}: track must be non-empty")
        url = entry["source_url"]
        if not isinstance(url, str) or not url.startswith("https://"):
            errors.append(f"{label}: source_url must be HTTPS")
        year = entry["source_year"]
        if type(year) is not int or not 2015 <= year <= latest[name]:
            errors.append(f"{label}: source_year must not be after the latest tracked edition")
        try:
            checked = date.fromisoformat(str(entry["checked"]))
        except ValueError:
            errors.append(f"{label}: checked must be an ISO date")
        else:
            if checked > today:
                errors.append(f"{label}: checked must not be in the future")
        if "note" in entry and (not isinstance(entry["note"], str) or not entry["note"].strip()):
            errors.append(f"{label}: note must be non-empty text when present")
    return errors


def with_archival(conferences: list[dict[str, Any]], options: dict[str, Any]) -> list[dict[str, Any]]:
    """Attach each edition's shown value as `_archival` (None when not checked)."""
    return [
        {**conference, "_archival": archival_value(options.get(conference["series"]), conference["year"])}
        for conference in conferences
    ]

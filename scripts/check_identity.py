"""Fail when a published calendar UID or edition ID disappears.

Calendar clients key subscribed events on their UID (ADR-004). Removing a
published UID silently drops the event for subscribers, and removing an edition
ID also removes its per-edition feed. This report-only check compares a base git
ref with the working tree and exits 1 when an identity disappears without an
entry in data/retired_identities.yml. It never modifies any file.

Usage: python3 scripts/check_identity.py --base REF
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
ICS_PATH = "docs/calendar-all.ics"
CONFERENCES_PATH = "data/conferences.yml"
RETIRED_PATH = "data/retired_identities.yml"
UID_DOMAIN = "scientific-conference-calendar"


def unfold_ics(text: str) -> list[str]:
    """Return logical ICS lines: a line break followed by a space or tab continues a line."""
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def ics_uids(text: str) -> set[str]:
    """Collect every event UID value from ICS text."""
    uids: set[str] = set()
    for line in unfold_ics(text):
        name, separator, value = line.partition(":")
        if separator and name.split(";", 1)[0].upper() == "UID":
            uids.add(value.strip())
    return uids


def edition_ids(yaml_text: str) -> set[str]:
    """Collect edition IDs from conferences.yml text."""
    data = yaml.safe_load(yaml_text) or []
    if not isinstance(data, list):
        raise ValueError(f"{CONFERENCES_PATH} must contain a YAML list")
    return {str(item["id"]) for item in data if isinstance(item, dict) and "id" in item}


def parse_retired(yaml_text: str) -> set[str]:
    """Return retired IDs; each entry must be a mapping with id, reason and ISO date."""
    data = yaml.safe_load(yaml_text) if yaml_text.strip() else []
    if data is None:
        data = []
    if not isinstance(data, list):
        raise ValueError(f"{RETIRED_PATH} must contain a YAML list")
    retired: set[str] = set()
    for index, entry in enumerate(data):
        where = f"{RETIRED_PATH} entry {index + 1}"
        if not isinstance(entry, dict):
            raise ValueError(f"{where} must be a mapping with id, reason and date")
        for field in ("id", "reason", "date"):
            if not str(entry.get(field) or "").strip():
                raise ValueError(f"{where} is missing {field!r}")
        try:
            date.fromisoformat(str(entry["date"]))
        except ValueError:
            raise ValueError(f"{where} date must be YYYY-MM-DD") from None
        retired.add(str(entry["id"]).strip())
    return retired


def is_retired(identity: str, retired: set[str]) -> bool:
    """A retired edition ID also covers that edition's generated event UIDs."""
    if identity in retired:
        return True
    local, _, domain = identity.partition("@")
    if domain != UID_DOMAIN:
        return False
    return any(local == f"{edition}-conference" or local.startswith(f"{edition}-deadline-")
               for edition in retired)


def unexplained_removals(base: set[str], current: set[str], retired: set[str]) -> list[str]:
    return sorted(identity for identity in base - current if not is_retired(identity, retired))


def git_show(ref: str, path: str, cwd: Path = ROOT) -> str | None:
    """Return a file's content at ref, or None when the file does not exist there."""
    result = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=cwd,
                            capture_output=True, text=True, encoding="utf-8")
    return result.stdout if result.returncode == 0 else None


def resolve_commit(ref: str, cwd: Path = ROOT) -> str | None:
    """Return the full commit SHA for ref, or None when it is not a known commit."""
    result = subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
                            cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def summary_line(label: str, base: set[str], current: set[str]) -> str:
    return (f"{label}: {len(base)} -> {len(current)} "
            f"(+{len(current - base)} added, -{len(base - current)} removed)")


def compare(base_ics: str | None, base_yaml: str | None, current_ics: str,
            current_yaml: str, retired: set[str]) -> tuple[list[str], list[str]]:
    """Return (report lines, unexplained removals)."""
    pairs: list[tuple[str, set[str], set[str]]] = [
        ("calendar UIDs", ics_uids(base_ics or ""), ics_uids(current_ics)),
        ("edition IDs", edition_ids(base_yaml or ""), edition_ids(current_yaml)),
    ]
    lines = [summary_line(label, base, current) for label, base, current in pairs]
    missing: list[str] = []
    for _, base, current in pairs:
        missing.extend(unexplained_removals(base, current, retired))
    retired_removed = sum(len(base - current) for _, base, current in pairs) - len(missing)
    if retired_removed:
        lines.append(f"removed but listed in {RETIRED_PATH}: {retired_removed}")
    return lines, missing


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", required=True, help="git ref to compare against, e.g. origin/main")
    args = parser.parse_args(list(argv) if argv is not None else None)

    commit = resolve_commit(args.base)
    if commit is None:
        print(f"Identity check error: {args.base!r} is not a commit in this repository.",
              file=sys.stderr)
        return 2
    try:
        retired = parse_retired(_read(ROOT / RETIRED_PATH))
        lines, missing = compare(git_show(commit, ICS_PATH), git_show(commit, CONFERENCES_PATH),
                                 _read(ROOT / ICS_PATH), _read(ROOT / CONFERENCES_PATH), retired)
    except (ValueError, yaml.YAMLError) as exc:
        print(f"Identity check error: {exc}", file=sys.stderr)
        return 2

    print(f"Identity check against {args.base} ({commit[:12]}):")
    for line in lines:
        print(f"  {line}")
    if not missing:
        print("OK: no published identity disappeared without a retirement entry.")
        return 0
    print(f"FAIL: {len(missing)} published identit{'y' if len(missing) == 1 else 'ies'} "
          "disappeared without a retirement entry:")
    for identity in missing:
        print(f"  - {identity}")
    print("Removing a published UID breaks calendar subscribers. Restore the ID, or, if the "
          f"removal is intentional, add {{id, reason, date}} to {RETIRED_PATH}.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

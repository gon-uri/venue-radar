"""Draft the next edition of verified recurring series from prior-edition timing.

This is an editorial helper, not an automatic source of confirmed dates. Review
official pages and edit the appended records before publication.

A series becomes a candidate once its latest edition has ended or once every
fresh-submission route of that edition has closed (ADR-039), so the next call
can appear while the current meeting is still upcoming.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from validate import (
    DATA_PATH,
    SUBMISSION_TYPES,
    load_conferences,
    parse_date,
    parse_datetime,
    stable_slug,
)


# Only series with a documented recurring cadence belong here. Irregular
# workshops and the one-off joint IJCAI-ECAI edition are intentionally absent.
CADENCE_YEARS = {
    "ICML": 1, "UAI": 1, "ECML PKDD": 1, "KDD": 1, "MLHC": 1,
    "CHIL": 1, "MICCAI": 1, "MIDL": 1, "IEEE EMBC": 1,
    "IEEE MLSP": 1, "CCN": 1, "Bernstein Conference": 1,
    "CNS*": 1, "ICANN": 1, "EUSIPCO": 1,
    "BIOMAG": 2, "ICPR": 2, "S+SSPR": 2,
    "L4DC": 1, "IFAC SYSID": 3, "IEEE CDC": 1, "ACC": 1,
    "NOLTA": 1, "SIAM DS": 2, "CCS": 1, "NetSci": 1,
    "AutoML": 1, "LoG": 1, "CoRL": 1, "GECCO": 1, "SaTML": 1,
    "ProbML": 1, "AAMAS": 1, "MLSys": 1, "CogSci": 1,
    "ICIP": 1, "Interspeech": 1,
    "EuroGP": 1, "KR": 1, "ICAPS": 1, "3DV": 1,
    "ACM MM": 1, "ACM SIGGRAPH": 1, "BMVC": 1, "CVPR": 1,
    "ECCV": 2, "EUVIP": 1, "FG": 1, "ICCV": 2,
    "ICMR": 1, "IJCB": 1, "WACV": 1,
    "ACL": 1, "EMNLP": 1, "CoNLL": 1, "LREC": 2,
    "SIGIR": 1, "ECIR": 1, "RecSys": 1, "WWW": 1,
    "COLM": 1, "ISWC": 1, "ICRA": 1, "RSS": 1, "SMC": 1,
    "COMPLEX NETWORKS": 1, "CompleNet": 1, "ALIFE": 1, "NICE": 1,
    "SAB": 2, "BCI Winter": 1, "IEEE BioCAS": 1, "AREADNE": 2,
    "SfN Neuroscience": 1, "Dynamics Days Europe": 1,
    "Dynamics Days US": 1, "Dynamics Days LAC": 2,
    # Long-running annual series added 2026-10-29 (ADR-039).
    "NeurIPS": 1, "ICLR": 1, "AISTATS": 1, "AAAI": 1, "IJCAI": 1,
    "COLT": 1, "CIKM": 1, "ICDM": 1, "SDM": 1, "WSDM": 1, "PAKDD": 1,
    "IDA": 1, "Discovery Science": 1, "DSAA": 1, "ADMA": 1, "IDEAL": 1,
    "IEEE BigData": 1, "IEEE ICMLA": 1, "ACML": 1, "ICONIP": 1,
    "IJCNN": 1, "ESANN": 1, "AALTD": 1, "AIES": 1, "ACM FAccT": 1,
    "CHI": 1, "ICASSP": 1, "ISBI": 1, "IEEE BHI": 1, "ML4H": 1,
    "COSYNE": 1, "OHBM": 1, "AIiH": 1,
    # Biennial series added 2026-10-29.
    "ACPR": 2, "IEEE NER": 2, "IEEE SSP": 2, "International BCI Meeting": 2,
}


def _submissions_closed(edition: dict, as_of: date) -> bool:
    """True when the edition had fresh-submission routes and all have passed."""
    routes = [
        deadline for deadline in edition.get("deadlines", [])
        if deadline.get("type") in SUBMISSION_TYPES
    ]
    if not routes:
        return False
    cutoff = datetime(as_of.year, as_of.month, as_of.day, tzinfo=timezone.utc)
    for deadline in routes:
        moment = parse_datetime(deadline["datetime"])
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        if moment >= cutoff:
            return False
    return True


def _shift(value: str, years: int) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if "T" in value else date.fromisoformat(value)
    try:
        shifted = parsed.replace(year=parsed.year + years)
    except ValueError:  # February 29 when the target year is not a leap year.
        shifted = parsed.replace(year=parsed.year + years, day=28)
    return shifted.isoformat()


def rollover_candidates(
    conferences: list[dict], as_of: date, series_filter: set[str] | None = None,
) -> list[dict]:
    latest = {}
    for item in conferences:
        if item["series"] not in latest or item["year"] > latest[item["series"]]["year"]:
            latest[item["series"]] = item
    candidates = []
    for series, cadence in CADENCE_YEARS.items():
        if series_filter is not None and series not in series_filter:
            continue
        previous = latest.get(series)
        if previous is None:
            continue
        ended = parse_date(previous["conference_end"]) < as_of
        if not ended and not _submissions_closed(previous, as_of):
            continue
        years = cadence
        while parse_date(_shift(previous["conference_end"], years)) < as_of:
            years += cadence
        projected = deepcopy(previous)
        projected["year"] = previous["year"] + years
        projected["id"] = f'{stable_slug(series)}-{projected["year"]}'
        projected["short_title"] = f'{series} {projected["year"]}'
        projected["conference_start"] = _shift(previous["conference_start"], years)
        projected["conference_end"] = _shift(previous["conference_end"], years)
        projected["location"] = "To be announced"
        projected["confidence"] = "estimated"
        # A draft is not a fresh review: keep the prior edition's review date
        # so the maintenance queue still flags it until sources are checked.
        projected["last_checked"] = previous["last_checked"]
        projected["notes"] = (
            f'Provisional {cadence}-year cadence projection from {previous["short_title"]}. '
            "Meeting dates, location, and deadlines require organizer confirmation; "
            "website and source links refer to the prior edition."
        )
        for deadline in projected["deadlines"]:
            deadline["datetime"] = _shift(deadline["datetime"], years)
            deadline["confidence"] = "estimated"
            deadline.pop("open_observed_on", None)
            # Openings are never guessed; a shifted prior opening is not evidence.
            deadline.pop("opens_at", None)
        candidates.append(projected)
    return candidates


def append_candidates(path: Path, candidates: list[dict]) -> None:
    if not candidates:
        return
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n# Provisional future editions; review organizer sources before publishing.\n")
        yaml.safe_dump(candidates, handle, sort_keys=False, allow_unicode=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument("--write", action="store_true", help="Append projected records to data/conferences.yml")
    parser.add_argument(
        "--series", action="append", metavar="SERIES",
        help="Limit drafts to this exact series key (repeatable); use with --write after review.",
    )
    args = parser.parse_args()
    series_filter = set(args.series) if args.series else None
    if series_filter:
        unknown = sorted(series_filter - set(CADENCE_YEARS))
        if unknown:
            parser.error(f"series not in CADENCE_YEARS: {', '.join(unknown)}")
    candidates = rollover_candidates(load_conferences(), args.as_of, series_filter)
    for item in candidates:
        print(f'{item["id"]}: estimated from {item["notes"].split(" from ")[1].split(".")[0]}')
    if args.write:
        append_candidates(DATA_PATH, candidates)
    print(f"{len(candidates)} candidate edition(s){' appended' if args.write else ' (dry run)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Check that cited organizer URLs still load and print date hints for manual review.

Report-only and networked: run it by hand, never from CI. It reads the canonical
YAML, never edits it, and writes nothing except an optional --output report.
Snippets are hints for a maintainer to compare with the YAML, not evidence.
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
import urllib.robotparser
from dataclasses import asdict, dataclass, field, replace
from datetime import date
from html.parser import HTMLParser
from http.client import HTTPException
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit

from validate import load_conferences, parse_date, parse_datetime

USER_AGENT = "VenueRadar-source-check (+https://github.com/gon-uri/venue-radar)"
MIN_HOST_DELAY = 1.0
MAX_CRAWL_DELAY = 30.0
DEFAULT_TIMEOUT = 20.0
MAX_BODY_BYTES = 2_000_000
MAX_SNIPPETS = 6
MAX_PROBES_PER_EDITION = 8
PROBE_LOOKBACK_YEARS = 3
CATEGORIES = {
    "dead": "dead (4xx/5xx, soft 404 or connection error)",
    "tls-error": "TLS certificate not verified: if many URLs show this, fix this Python's CA certificates; "
                 "otherwise check the site in a browser",
    "blocked":"blocked (403/429): check manually in a browser",
    "robots": "not fetched: robots.txt disallows it; check manually",
    "redirect": "redirected to another host",
    "ok": "loaded",
}
TEXT_TYPES = ("text/html", "application/xhtml+xml", "text/plain")
NOT_FOUND_TITLE = re.compile(r"\b404\b|not found|page missing|does not exist", re.IGNORECASE)
KEYWORD = re.compile(r"important dates|deadlines?|submissions?|abstracts?|papers?", re.IGNORECASE)
_MONTH = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?"
          r"|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)")
_YEAR = r"(?:19|20)\d{2}"
DATE_LIKE = re.compile(
    rf"\b(?:{_YEAR}-\d{{1,2}}-\d{{1,2}}"
    rf"|\d{{1,2}}[/.]\d{{1,2}}[/.](?:{_YEAR}|\d{{2}})"
    rf"|\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?{_MONTH}\.?(?:,?\s+{_YEAR})?"
    rf"|{_MONTH}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+{_YEAR})?)\b",
    re.IGNORECASE,
)

Opener = Callable[..., Any]


@dataclass(frozen=True)
class FetchResult:
    url: str
    status: int | None = None
    final_url: str = ""
    error: str = ""
    title: str = ""
    text: str = ""
    robots_blocked: bool = False


@dataclass(frozen=True)
class UrlCheck:
    url: str
    cited_as: list[str]
    category: str
    status: int | None
    final_url: str
    error: str
    snippets: list[str]


@dataclass(frozen=True)
class Probe:
    cited_url: str
    candidate: str
    category: str
    status: int | None
    final_url: str
    snippets: list[str]

    @property
    def exists(self) -> bool:
        return self.category == "ok"


@dataclass(frozen=True)
class EditionCheck:
    id: str
    title: str
    confidence: str
    yaml_dates: list[str]
    urls: list[UrlCheck]
    probes: list[Probe] = field(default_factory=list)


class _TextExtractor(HTMLParser):
    SKIP = frozenset({"script", "style", "noscript", "template", "svg"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title: list[str] = []
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._skip += tag in self.SKIP
        self._in_title = self._in_title or tag == "title"

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title.append(data)
        elif not self._skip:
            self.parts.append(data)


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def html_to_text(raw: str) -> tuple[str, str]:
    """Return (title, visible text) of an HTML document, ignoring scripts and styles."""
    parser = _TextExtractor()
    try:
        parser.feed(raw)
        parser.close()
    except (AssertionError, ValueError):  # malformed markup: keep what was parsed
        pass
    return _squash(" ".join(parser.title)), _squash(" ".join(parser.parts))


def date_snippets(text: str, limit: int = MAX_SNIPPETS, radius: int = 80) -> list[str]:
    """Short passages joining a submission keyword to a nearby date-like string.

    A date after the keyword ("Paper deadline: May 4") wins over one before it;
    text already quoted in an earlier snippet is not reused.
    """
    snippets: list[str] = []
    covered = 0
    for keyword in KEYWORD.finditer(text):
        if keyword.start() < covered:
            continue
        match = DATE_LIKE.search(text, keyword.end(), keyword.end() + radius + 40)
        if match and match.start() > keyword.end() + radius:
            match = None
        if match is None:
            before = list(DATE_LIKE.finditer(text, max(covered, keyword.start() - radius), keyword.start()))
            match = before[-1] if before else None
        if match is None:
            continue
        covered = max(keyword.end(), match.end())
        snippet = _squash(text[min(keyword.start(), match.start()):covered])
        if snippet.casefold() not in {item.casefold() for item in snippets}:
            snippets.append(snippet)
        if len(snippets) >= limit:
            break
    return snippets


def same_site(url: str, other: str) -> bool:
    def host(value: str) -> str:
        name = (urlsplit(value).hostname or "").lower()
        return name[4:] if name.startswith("www.") else name

    return host(url) == host(other)


def classify(result: FetchResult) -> str:
    if result.robots_blocked:
        return "robots"
    if result.status in (403, 429):
        return "blocked"
    # A local trust-store problem is not evidence that the organizer's page is gone.
    if result.status is None and _is_certificate_error(result.error):
        return "tls-error"
    if result.status is None or result.status >= 400:
        return "dead"
    if NOT_FOUND_TITLE.search(result.title):
        return "dead"
    if result.final_url and not same_site(result.url, result.final_url):
        return "redirect"
    return "ok"


def successor_urls(url: str, edition_year: int, lookback: int = PROBE_LOOKBACK_YEARS) -> list[str]:
    """Year-substituted guesses for this edition's page, e.g. 2026 -> 2027 and -26 -> -27.

    Only the host and path change. The 4-digit-only variant comes first; the
    second variant also replaces a standalone two-digit year (``aaai-26``).
    """
    parts = urlsplit(url)
    base = urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))
    candidates: list[str] = []
    for old in range(edition_year - lookback, edition_year):
        rules = [(rf"(?<!\d){old}(?!\d)", str(edition_year)),
                 (rf"(?<!\d){old % 100:02d}(?!\d)", f"{edition_year % 100:02d}")]
        for count in (1, 2):
            netloc, path = parts.netloc, parts.path
            for pattern, new in rules[:count]:
                netloc, path = re.sub(pattern, new, netloc), re.sub(pattern, new, path)
            candidate = urlunsplit((parts.scheme, netloc, path, parts.query, ""))
            if candidate != base and candidate not in candidates:
                candidates.append(candidate)
    return candidates


def ssl_contexts() -> list[ssl.SSLContext]:
    """The system trust store, then certifi's bundle when it is installed."""
    contexts = [ssl.create_default_context()]
    try:
        import certifi  # type: ignore[import-not-found]
    except ImportError:
        return contexts
    contexts.append(ssl.create_default_context(cafile=certifi.where()))
    return contexts


def _is_certificate_error(reason: object) -> bool:
    return isinstance(reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(reason)


class Fetcher:
    """Polite GET client: identifying User-Agent, robots.txt, per-host delay, cache."""

    def __init__(self, timeout: float = DEFAULT_TIMEOUT, delay: float = MIN_HOST_DELAY,
                 opener: Opener | None = None, sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.timeout = timeout
        self.delay = max(delay, MIN_HOST_DELAY)
        self._open = opener or urllib.request.urlopen
        self._sleep, self._clock = sleep, clock
        self._contexts = ssl_contexts()
        self._last: dict[str, float] = {}
        self._host_delay: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser | FetchResult] = {}
        self._cache: dict[str, FetchResult] = {}

    def fetch(self, url: str) -> FetchResult:
        if url not in self._cache:
            self._cache[url] = self._fetch(url)
        return self._cache[url]

    def _fetch(self, url: str) -> FetchResult:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            return FetchResult(url, error="unsupported URL")
        rules = self._robot_rules(parts.scheme, parts.netloc)
        if isinstance(rules, FetchResult):
            return replace(rules, url=url)
        if not rules.can_fetch(USER_AGENT, url):
            return FetchResult(url, error="robots.txt disallows this URL", robots_blocked=True)
        return self._request(url)

    def _robot_rules(self, scheme: str, netloc: str) -> urllib.robotparser.RobotFileParser | FetchResult:
        origin = f"{scheme}://{netloc}"
        if origin not in self._robots:
            response = self._request(origin + "/robots.txt", any_type=True)
            rules = urllib.robotparser.RobotFileParser()
            if response.status is None:
                self._robots[origin] = response  # host unreachable: report pages as dead
                return response
            if response.status in (401, 403) or response.status >= 500:
                rules.disallow_all = True
            elif response.status >= 400:
                rules.allow_all = True
            else:
                rules.parse(response.text.splitlines())
                crawl_delay = rules.crawl_delay(USER_AGENT)
                if crawl_delay:
                    host = (urlsplit(origin).hostname or "").lower()
                    self._host_delay[host] = min(max(float(crawl_delay), self.delay), MAX_CRAWL_DELAY)
            self._robots[origin] = rules
        return self._robots[origin]

    def _wait(self, host: str) -> None:
        if host in self._last:
            remaining = self._host_delay.get(host, self.delay) - (self._clock() - self._last[host])
            if remaining > 0:
                self._sleep(remaining)

    def _request(self, url: str, any_type: bool = False) -> FetchResult:
        host = (urlsplit(url).hostname or "").lower()
        request = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.5",
        })
        while True:
            self._wait(host)
            try:
                with self._open(request, timeout=self.timeout, context=self._contexts[0]) as response:
                    status = getattr(response, "status", None) or response.getcode()
                    content_type = response.headers.get_content_type()
                    title = text = ""
                    if any_type or content_type in TEXT_TYPES:
                        raw = response.read(MAX_BODY_BYTES)
                        decoded = raw.decode(response.headers.get_content_charset() or "utf-8", "replace")
                        title, text = (html_to_text(decoded) if "html" in content_type and not any_type
                                       else ("", decoded))
                    return FetchResult(url, status, response.geturl() or url, title=title, text=text)
            except urllib.error.HTTPError as error:
                error.close()
                return FetchResult(url, error.code, error.geturl() or url, error=f"HTTP {error.code}")
            except urllib.error.URLError as error:
                if _is_certificate_error(error.reason) and len(self._contexts) > 1:
                    self._contexts.pop(0)  # keep using the certifi bundle from now on
                    continue
                return FetchResult(url, error=str(error.reason))
            except (OSError, HTTPException, ValueError, LookupError) as error:
                return FetchResult(url, error=f"{type(error).__name__}: {error}")
            finally:
                self._last[host] = self._clock()


def cited_urls(edition: dict) -> dict[str, list[str]]:
    """Every URL an edition cites, mapped to the fields citing it, in YAML order."""
    cited: dict[str, list[str]] = {}

    def add(url: object, where: str) -> None:
        if isinstance(url, str) and url.strip():
            cited.setdefault(url.strip(), []).append(where)

    add(edition.get("website"), "website")
    add(edition.get("cfp_url"), "cfp_url")
    for url in edition.get("source_urls") or []:
        add(url, "source_urls")
    for deadline in edition.get("deadlines") or []:
        add(deadline.get("source_url"), f"deadline:{deadline.get('type')}")
    return cited


def _deadline_day(deadline: dict) -> str:
    try:
        return parse_datetime(deadline.get("datetime")).date().isoformat()
    except (TypeError, ValueError):
        return "no date"


def yaml_dates(edition: dict) -> list[str]:
    confidence = str(edition["confidence"])
    rows = [f"meeting {parse_date(edition['conference_start'])} to {parse_date(edition['conference_end'])} "
            f"({confidence.replace('_', ' ')})"]
    for deadline in edition.get("deadlines") or []:
        own = str(deadline.get("confidence", confidence)).replace("_", " ")
        rows.append(f"{deadline.get('type')} {_deadline_day(deadline)} ({own})")
    return rows


def needs_probe(edition: dict) -> bool:
    """Estimated meetings or deadlines often cite last year's pages."""
    confidence = edition["confidence"]
    return confidence != "confirmed" or any(
        item.get("confidence", confidence) != "confirmed" for item in edition.get("deadlines") or []
    )


def select_editions(conferences: list[dict], as_of: date, ids: list[str] | None = None,
                    series: list[str] | None = None, limit: int | None = None) -> list[dict]:
    """Upcoming editions by start date, or the requested IDs/series."""
    if ids:
        by_id = {item["id"]: item for item in conferences}
        unknown = [identifier for identifier in ids if identifier not in by_id]
        if unknown:
            raise ValueError(f"unknown edition id(s): {', '.join(unknown)}")
        chosen = [by_id[identifier] for identifier in dict.fromkeys(ids)]
    else:
        unknown = sorted(set(series or []) - {item["series"] for item in conferences})
        if unknown:
            raise ValueError(f"unknown series: {', '.join(unknown)}")
        pool = [item for item in conferences if not series or item["series"] in series]
        chosen = [item for item in pool if parse_date(item["conference_end"]) >= as_of]
        for name in series or []:
            if not any(item["series"] == name for item in chosen):
                chosen.append(max((item for item in pool if item["series"] == name), key=lambda item: item["year"]))
        chosen.sort(key=lambda item: (parse_date(item["conference_start"]), item["id"]))
    return chosen[:limit] if limit else chosen


def check_edition(edition: dict, fetcher: Fetcher, probe: bool = True) -> EditionCheck:
    cited = cited_urls(edition)
    urls = []
    for url, where in cited.items():
        result = fetcher.fetch(url)
        urls.append(UrlCheck(url, where, classify(result), result.status, result.final_url,
                             result.error, date_snippets(result.text)))
    probes: list[Probe] = []
    if probe and needs_probe(edition):
        candidates: dict[str, str] = {}
        for url in cited:
            for candidate in successor_urls(url, edition["year"]):
                if candidate not in cited:
                    candidates.setdefault(candidate, url)
        for candidate, url in list(candidates.items())[:MAX_PROBES_PER_EDITION]:
            result = fetcher.fetch(candidate)
            probes.append(Probe(url, candidate, classify(result), result.status, result.final_url,
                                date_snippets(result.text)))
    return EditionCheck(edition["id"], edition["short_title"], edition["confidence"],
                        yaml_dates(edition), urls, probes)


def summary(checks: list[EditionCheck]) -> dict[str, int]:
    counts = {category: 0 for category in CATEGORIES}
    for check in checks:
        for url in check.urls:
            counts[url.category] += 1
    counts["probes"] = sum(len(check.probes) for check in checks)
    counts["successors_found"] = sum(probe.exists for check in checks for probe in check.probes)
    return counts


def tls_hint(checks: list[EditionCheck]) -> str:
    failures = sum(_is_certificate_error(url.error) for check in checks for url in check.urls)
    if not failures:
        return ""
    return (f"TLS verification failed for {failures} URL(s); this Python may lack CA certificates. "
            "Install certifi, run python.org's Install Certificates.command or set SSL_CERT_FILE; "
            "never disable verification.")


def _status(category: str, status: int | None) -> str:
    if category == "dead" and status and status < 400:
        return "soft-404"
    return f"{category} {status}" if status and category != "ok" else category


def _url_note(check: UrlCheck) -> str:
    notes = [", ".join(check.cited_as)]
    if check.category == "redirect" or (check.final_url and check.final_url != check.url and check.category == "ok"):
        notes.append(f"-> {check.final_url}")
    if check.error and check.category != "blocked":
        notes.append(check.error)
    return "; ".join(note for note in notes if note)


def render_text(checks: list[EditionCheck], as_of: date) -> str:
    counts = summary(checks)
    lines = [
        f"Source check as of {as_of}: {sum(len(check.urls) for check in checks)} cited URLs "
        f"across {len(checks)} editions",
        "  " + ", ".join(f"{name}: {counts[name]}" for name in CATEGORIES),
        f"  successor probes: {counts['successors_found']} of {counts['probes']} found",
        "Snippets are hints only: compare them with the official page before editing YAML.",
    ]
    if tls_hint(checks):
        lines.append(tls_hint(checks))
    for check in checks:
        lines += ["", f"{check.title} ({check.id}) [{check.confidence.replace('_', ' ')}]",
                  "  YAML: " + "; ".join(check.yaml_dates)]
        for url in check.urls:
            lines.append(f"  {_status(url.category, url.status):<12} {url.url}  [{_url_note(url)}]")
            lines += [f"  {'':<12} hint: {snippet}" for snippet in url.snippets]
        for probe in check.probes:
            found = "found" if probe.exists else _status(probe.category, probe.status)
            lines.append(f"  probe {found:<6} {probe.candidate}")
            if probe.final_url and probe.final_url != probe.candidate:
                lines.append(f"  {'':<12} -> {probe.final_url}")
            lines += [f"  {'':<12} hint: {snippet}" for snippet in probe.snippets]
    return "\n".join(lines)


def _md(text: str) -> str:
    return re.sub(r"([\\`*_\[\]<>#|~])", r"\\\1", text)


def render_markdown(checks: list[EditionCheck], as_of: date) -> str:
    counts = summary(checks)
    lines = [
        f"## Source check as of {as_of}",
        "",
        " · ".join(f"{name}: {counts[name]}" for name in CATEGORIES)
        + f" · successor probes found: {counts['successors_found']} of {counts['probes']}",
        "",
        "_Snippets are hints only; confirm on the official page before editing YAML._",
    ]
    if tls_hint(checks):
        lines += ["", f"> {_md(tls_hint(checks))}"]
    for check in checks:
        lines += ["", f"### {_md(check.title)} (`{check.id}`), {check.confidence.replace('_', ' ')}", "",
                  "YAML: " + _md("; ".join(check.yaml_dates)), ""]
        for url in check.urls:
            lines.append(f"- **{_status(url.category, url.status)}** <{url.url}> ({_md(_url_note(url))})")
            lines += [f"  - hint: {_md(snippet)}" for snippet in url.snippets]
        for probe in check.probes:
            found = "found" if probe.exists else _status(probe.category, probe.status)
            lines.append(f"- probe **{found}** <{probe.candidate}>")
            lines += [f"  - hint: {_md(snippet)}" for snippet in probe.snippets]
    return "\n".join(lines)


def render_json(checks: list[EditionCheck], as_of: date) -> str:
    editions = [
        {**asdict(check), "probes": [{**asdict(probe), "exists": probe.exists} for probe in check.probes]}
        for check in checks
    ]
    return json.dumps({"as_of": as_of.isoformat(), "summary": summary(checks), "editions": editions},
                      indent=2, ensure_ascii=False)


RENDERERS: dict[str, Callable[[list[EditionCheck], date], str]] = {
    "text": render_text, "markdown": render_markdown, "json": render_json,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument("--id", action="append", dest="ids", metavar="ID", help="edition id (repeatable)")
    parser.add_argument("--series", action="append", metavar="NAME", help="exact series name (repeatable; ignored with --id)")
    parser.add_argument("--limit", type=int, metavar="N", help="check at most N editions")
    parser.add_argument("--format", choices=sorted(RENDERERS), default="text")
    parser.add_argument("--output", type=Path, help="write the report here instead of stdout")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="seconds per request")
    parser.add_argument("--delay", type=float, default=MIN_HOST_DELAY,
                        help=f"seconds between requests to one host (minimum {MIN_HOST_DELAY:g})")
    parser.add_argument("--no-probe", action="store_true", help="skip year-substituted successor probes")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.delay < MIN_HOST_DELAY or args.timeout <= 0:
        parser.error(f"--delay must be at least {MIN_HOST_DELAY:g} and --timeout positive")
    try:
        editions = select_editions(load_conferences(), args.as_of, args.ids, args.series, args.limit)
    except ValueError as error:
        parser.error(str(error))
    fetcher = Fetcher(timeout=args.timeout, delay=args.delay)
    checks = []
    for index, edition in enumerate(editions, start=1):
        print(f"[{index}/{len(editions)}] {edition['id']}", file=sys.stderr, flush=True)
        checks.append(check_edition(edition, fetcher, probe=not args.no_probe))
    report = RENDERERS[args.format](checks, args.as_of)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

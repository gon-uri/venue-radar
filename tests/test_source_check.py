from __future__ import annotations

import io
import json
import ssl
import sys
import tempfile
import unittest
import urllib.error
from datetime import date
from email.message import Message
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import source_check  # noqa: E402
from source_check import (  # noqa: E402
    USER_AGENT,
    EditionCheck,
    FetchResult,
    Fetcher,
    Probe,
    UrlCheck,
    check_edition,
    cited_urls,
    classify,
    date_snippets,
    html_to_text,
    needs_probe,
    render_json,
    render_markdown,
    render_text,
    select_editions,
    successor_urls,
    yaml_dates,
)

AS_OF = date(2026, 10, 29)


def edition(**overrides: Any) -> dict[str, Any]:
    item = {
        "id": "sample-2027", "short_title": "Sample 2027", "series": "Sample", "year": 2027,
        "confidence": "estimated", "conference_start": "2027-05-01", "conference_end": "2027-05-03",
        "website": "https://example.org/", "cfp_url": "https://example.org/2026/cfp",
        "source_urls": ["https://example.org/2026/dates"],
        "deadlines": [{"type": "full_paper", "label": "Paper", "datetime": "2027-01-15T23:59:00-12:00",
                       "source_url": "https://example.org/2026/dates"}],
    }
    item.update(overrides)
    return item


class FakeResponse:
    def __init__(self, url: str, body: bytes = b"", status: int = 200,
                 content_type: str = "text/html; charset=utf-8", final_url: str = "") -> None:
        self.status, self._body, self._url = status, body, final_url or url
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def read(self, size: int = -1) -> bytes:
        return self._body if size < 0 else self._body[:size]

    def geturl(self) -> str:
        return self._url

    def getcode(self) -> int:
        return self.status

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


class FakeWeb:
    """urlopen stand-in: maps URLs to responses, HTTP status codes or exceptions (default 404)."""

    def __init__(self, routes: dict[str, Any]) -> None:
        self.routes = routes
        self.calls: list[tuple[str, str | None, float]] = []

    def __call__(self, request: Any, timeout: float, context: ssl.SSLContext) -> FakeResponse:
        url = request.full_url
        self.calls.append((url, request.get_header("User-agent"), timeout))
        outcome = self.routes.get(url, 404)
        if isinstance(outcome, list):
            outcome = outcome.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, int):
            raise urllib.error.HTTPError(url, outcome, "error", Message(), io.BytesIO())
        if isinstance(outcome, bytes):
            return FakeResponse(url, outcome)
        return outcome

    def urls(self) -> list[str]:
        return [call[0] for call in self.calls]


class Clock:
    def __init__(self) -> None:
        self.now = 100.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def fetcher(web: FakeWeb, clock: Clock | None = None) -> Fetcher:
    clock = clock or Clock()
    return Fetcher(timeout=5, opener=web, sleep=clock.sleep, clock=clock)


class PureFunctionTests(unittest.TestCase):
    def test_successor_urls_substitute_years_in_host_and_path_only(self) -> None:
        self.assertEqual(successor_urls("https://icml.cc/Conferences/2026/Dates", 2027),
                         ["https://icml.cc/Conferences/2027/Dates"])
        self.assertEqual(successor_urls("https://kdd2026.kdd.org/cfp/?year=2026#dates", 2027),
                         ["https://kdd2027.kdd.org/cfp/?year=2026"])
        self.assertEqual(successor_urls("https://aaai.org/conference/aaai/aaai-26/", 2027),
                         ["https://aaai.org/conference/aaai/aaai-27/"])
        self.assertEqual(successor_urls("https://neuro.embs.org/2025/NER-25-CFP.pdf", 2027), [
            "https://neuro.embs.org/2027/NER-25-CFP.pdf", "https://neuro.embs.org/2027/NER-27-CFP.pdf",
        ])
        self.assertEqual(successor_urls("https://eccv.ecva.net/Conferences/2026/Dates", 2028),
                         ["https://eccv.ecva.net/Conferences/2028/Dates"])
        for unchanged in ["https://example.org/", "https://example.org/2027/", "https://example.org/id/20260"]:
            self.assertEqual(successor_urls(unchanged, 2027), [], unchanged)

    def test_snippets_join_keywords_to_nearby_dates_without_repeats(self) -> None:
        text = ("Welcome. Important Dates: Paper submission deadline: May 4, 2027. "
                "Notification: July 1, 2027. 15 January 2027 is when abstract registration closes. "
                "Our papers are great.")
        snippets = date_snippets(text)
        self.assertEqual(snippets, [
            "Important Dates: Paper submission deadline: May 4, 2027",
            "15 January 2027 is when abstract",
        ])
        self.assertEqual(date_snippets("Submission is open to everyone."), [])
        self.assertEqual(date_snippets("Nothing relevant on 2027-01-02."), [])
        many = " ".join(f"Deadline {day} March 2027." for day in range(1, 20))
        self.assertEqual(len(date_snippets(many, limit=3)), 3)
        self.assertEqual(date_snippets("Abstract due 2027-01-12 AoE"), ["Abstract due 2027-01-12"])

    def test_html_to_text_skips_scripts_and_keeps_the_title(self) -> None:
        title, text = html_to_text(
            "<html><head><title>CFP &amp; Dates</title><style>p{}</style></head>"
            "<body><script>var deadline='Jan 1';</script><p>Paper&nbsp;deadline:</p><td>Mar 3, 2027</td></body>"
        )
        self.assertEqual(title, "CFP & Dates")
        self.assertEqual(text, "Paper deadline: Mar 3, 2027")
        self.assertEqual(date_snippets(text), ["Paper deadline: Mar 3, 2027"])

    def test_classification(self) -> None:
        url = "https://example.org/page"
        cases = [
            (FetchResult(url, 200, url), "ok"),
            (FetchResult(url, 200, "https://www.example.org/page/"), "ok"),
            (FetchResult(url, 200, "https://other.org/"), "redirect"),
            (FetchResult(url, 200, url, title="Page Not Found"), "dead"),
            (FetchResult(url, 404, url, error="HTTP 404"), "dead"),
            (FetchResult(url, 500, url), "dead"),
            (FetchResult(url, error="timed out"), "dead"),
            (FetchResult(url, 403, url), "blocked"),
            (FetchResult(url, 429, url), "blocked"),
            (FetchResult(url, robots_blocked=True), "robots"),
        ]
        for result, expected in cases:
            self.assertEqual(classify(result), expected, result)

    def test_cited_urls_and_yaml_dates(self) -> None:
        item = edition()
        self.assertEqual(cited_urls(item), {
            "https://example.org/": ["website"],
            "https://example.org/2026/cfp": ["cfp_url"],
            "https://example.org/2026/dates": ["source_urls", "deadline:full_paper"],
        })
        self.assertEqual(yaml_dates(item), ["meeting 2027-05-01 to 2027-05-03 (estimated)",
                                            "full_paper 2027-01-15 (estimated)"])
        self.assertTrue(needs_probe(item))
        self.assertFalse(needs_probe(edition(confidence="confirmed")))
        self.assertTrue(needs_probe(edition(confidence="confirmed", deadlines=[{"type": "x", "confidence": "estimated"}])))

    def test_select_editions(self) -> None:
        records = [
            edition(id="b-2027", series="B", conference_start="2027-06-01", conference_end="2027-06-02"),
            edition(id="a-2027", series="A"),
            edition(id="a-2025", series="A", year=2025, conference_start="2025-05-01", conference_end="2025-05-02"),
            edition(id="c-2025", series="C", year=2025, conference_start="2025-05-01", conference_end="2025-05-02"),
            edition(id="c-2024", series="C", year=2024, conference_start="2024-05-01", conference_end="2024-05-02"),
        ]
        ids = lambda rows: [row["id"] for row in rows]  # noqa: E731
        self.assertEqual(ids(select_editions(records, AS_OF)), ["a-2027", "b-2027"])
        self.assertEqual(ids(select_editions(records, AS_OF, limit=1)), ["a-2027"])
        self.assertEqual(ids(select_editions(records, AS_OF, ids=["c-2024", "a-2025"])), ["c-2024", "a-2025"])
        self.assertEqual(ids(select_editions(records, AS_OF, series=["C", "B"])), ["c-2025", "b-2027"])
        with self.assertRaises(ValueError):
            select_editions(records, AS_OF, ids=["missing"])
        with self.assertRaises(ValueError):
            select_editions(records, AS_OF, series=["Missing"])


class FetcherTests(unittest.TestCase):
    def test_identifies_itself_honours_robots_and_waits_per_host(self) -> None:
        web = FakeWeb({
            "https://example.org/robots.txt": FakeResponse(
                "https://example.org/robots.txt", b"User-agent: *\nDisallow: /private\n", content_type="text/plain"),
            "https://example.org/a": b"<p>ok</p>",
            "https://example.org/b": b"<p>ok</p>",
        })
        clock = Clock()
        client = fetcher(web, clock)
        self.assertEqual(classify(client.fetch("https://example.org/a")), "ok")
        self.assertEqual(classify(client.fetch("https://example.org/b")), "ok")
        self.assertEqual(classify(client.fetch("https://example.org/private/x")), "robots")
        self.assertEqual(classify(client.fetch("https://example.org/a")), "ok")
        self.assertEqual(web.urls(), ["https://example.org/robots.txt", "https://example.org/a", "https://example.org/b"])
        self.assertTrue(all(agent == USER_AGENT and timeout == 5 for _, agent, timeout in web.calls))
        self.assertEqual(clock.sleeps, [1.0, 1.0])

    def test_robots_status_codes_and_unreachable_hosts(self) -> None:
        web = FakeWeb({
            "https://forbidden.org/robots.txt": 403,
            "https://missing.org/page": b"<p>ok</p>",
            "https://gone.org/robots.txt": urllib.error.URLError("Name or service not known"),
        })
        client = fetcher(web)
        self.assertEqual(classify(client.fetch("https://forbidden.org/page")), "robots")
        self.assertEqual(classify(client.fetch("https://missing.org/page")), "ok")
        gone = client.fetch("https://gone.org/page")
        self.assertEqual((classify(gone), gone.url), ("dead", "https://gone.org/page"))
        self.assertIn("Name or service not known", gone.error)
        self.assertNotIn("https://forbidden.org/page", web.urls())
        self.assertNotIn("https://gone.org/page", web.urls())

    def test_http_errors_redirects_and_non_html_bodies(self) -> None:
        web = FakeWeb({
            "https://example.org/blocked": 429,
            "https://example.org/moved": FakeResponse("https://example.org/moved", b"", final_url="https://new.org/"),
            "https://example.org/cfp.pdf": FakeResponse("https://example.org/cfp.pdf", b"%PDF deadline May 1",
                                                         content_type="application/pdf"),
            "https://example.org/slow": TimeoutError("timed out"),
        })
        client = fetcher(web)
        self.assertEqual(classify(client.fetch("https://example.org/blocked")), "blocked")
        self.assertEqual(classify(client.fetch("https://example.org/gone")), "dead")
        self.assertEqual(classify(client.fetch("https://example.org/moved")), "redirect")
        pdf = client.fetch("https://example.org/cfp.pdf")
        self.assertEqual((classify(pdf), pdf.text), ("ok", ""))
        slow = client.fetch("https://example.org/slow")
        self.assertEqual(classify(slow), "dead")
        self.assertIn("timed out", slow.error)
        self.assertEqual(classify(client.fetch("ftp://example.org/file")), "dead")

    def test_certificate_failure_falls_back_to_the_next_trust_store(self) -> None:
        failure = urllib.error.URLError(ssl.SSLCertVerificationError("CERTIFICATE_VERIFY_FAILED"))
        web = FakeWeb({"https://example.org/robots.txt": [failure, 404], "https://example.org/": b"<p>ok</p>"})
        client = fetcher(web)
        first, second = ssl.create_default_context(), ssl.create_default_context()
        client._contexts = [first, second]
        self.assertEqual(classify(client.fetch("https://example.org/")), "ok")
        self.assertEqual(client._contexts, [second])
        self.assertEqual(web.urls().count("https://example.org/robots.txt"), 2)


class ReportTests(unittest.TestCase):
    def test_check_edition_reports_snippets_and_successor_probes(self) -> None:
        page = b"<title>Dates</title><p>Paper submission deadline: January 15, 2026</p>"
        successor = b"<p>Paper submission deadline: January 20, 2027</p>"
        web = FakeWeb({
            "https://example.org/": b"<p>Home</p>",
            "https://example.org/2026/cfp": 404,
            "https://example.org/2026/dates": page,
            "https://example.org/2027/dates": successor,
        })
        check = check_edition(edition(), fetcher(web))
        categories = {url.url: url.category for url in check.urls}
        self.assertEqual(categories, {"https://example.org/": "ok", "https://example.org/2026/cfp": "dead",
                                      "https://example.org/2026/dates": "ok"})
        dates = next(url for url in check.urls if url.url.endswith("/2026/dates"))
        self.assertEqual(dates.snippets, ["Paper submission deadline: January 15, 2026"])
        probes = {probe.candidate: probe for probe in check.probes}
        self.assertEqual(set(probes), {"https://example.org/2027/cfp", "https://example.org/2027/dates"})
        self.assertTrue(probes["https://example.org/2027/dates"].exists)
        self.assertFalse(probes["https://example.org/2027/cfp"].exists)
        self.assertEqual(probes["https://example.org/2027/dates"].snippets,
                         ["Paper submission deadline: January 20, 2027"])
        confirmed = check_edition(edition(confidence="confirmed", deadlines=[]), fetcher(FakeWeb({})))
        self.assertEqual(confirmed.probes, [])

    def sample(self) -> list[EditionCheck]:
        return [EditionCheck(
            "sample-2027", "CNS* 2027", "estimated", ["meeting 2027-05-01 to 2027-05-03 (estimated)"],
            [UrlCheck("https://example.org/", ["website"], "ok", 200, "https://example.org/", "", ["Paper deadline: May 1"]),
             UrlCheck("https://example.org/x", ["cfp_url"], "blocked", 403, "https://example.org/x", "HTTP 403", []),
             UrlCheck("https://example.org/y", ["source_urls"], "dead", None, "",
                      "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed", [])],
            [Probe("https://example.org/2026/", "https://example.org/2027/", "ok", 200, "https://example.org/2027/", [])],
        )]

    def test_renderers(self) -> None:
        text = render_text(self.sample(), AS_OF)
        self.assertIn("dead: 1, blocked: 1, robots: 0, redirect: 0, ok: 1", text)
        self.assertIn("successor probes: 1 of 1 found", text)
        self.assertIn("TLS verification failed for 1 URL(s)", text)
        self.assertIn("blocked 403", text)
        self.assertIn("hint: Paper deadline: May 1", text)
        markdown = render_markdown(self.sample(), AS_OF)
        self.assertIn("### CNS\\* 2027 (`sample-2027`), estimated", markdown)
        self.assertIn("- probe **found** <https://example.org/2027/>", markdown)
        payload = json.loads(render_json(self.sample(), AS_OF))
        self.assertEqual(payload["summary"]["successors_found"], 1)
        self.assertTrue(payload["editions"][0]["probes"][0]["exists"])

    def test_main_writes_only_the_requested_report(self) -> None:
        class OfflineFetcher:
            def __init__(self, **_: Any) -> None:
                pass

            def fetch(self, url: str) -> FetchResult:
                return FetchResult(url, 200, url, text="Abstract deadline: 3 May 2027")

        with tempfile.TemporaryDirectory() as folder, \
                mock.patch.object(source_check, "Fetcher", OfflineFetcher), \
                mock.patch.object(source_check, "load_conferences", return_value=[edition()]), \
                mock.patch("sys.stdout", new=io.StringIO()) as stdout, \
                mock.patch("sys.stderr", new=io.StringIO()):
            output = Path(folder) / "report.json"
            self.assertEqual(source_check.main(["--as-of", "2026-10-29", "--format", "json", "--output", str(output)]), 0)
            self.assertEqual([path.name for path in Path(folder).iterdir()], ["report.json"])
            self.assertEqual(stdout.getvalue(), "")
            payload = json.loads(output.read_text())
        self.assertEqual(payload["editions"][0]["id"], "sample-2027")
        self.assertIn("Abstract deadline: 3 May 2027", payload["editions"][0]["urls"][0]["snippets"])


if __name__ == "__main__":
    unittest.main()

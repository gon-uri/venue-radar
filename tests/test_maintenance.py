from __future__ import annotations

import json
import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from maintenance_report import (  # noqa: E402
    TIERS,
    BacklogRow,
    Milestone,
    Report,
    TriagedEdition,
    acceptance_backlog,
    acceptance_queue,
    advisories,
    is_aggregator,
    next_route_action,
    render_json,
    render_markdown,
    render_text,
    review_queue,
    scope_backlog,
    triage,
)

AS_OF = date(2026, 10, 29)
STALE = "2026-01-01"


def edition(**overrides: Any) -> dict[str, Any]:
    item = {
        "id": "sample-2027", "short_title": "Sample 2027", "series": "Sample", "year": 2027,
        "last_checked": "2026-10-20", "confidence": "confirmed",
        "conference_start": "2027-05-01", "conference_end": "2027-05-03", "deadlines": [],
        "website": "https://example.org", "source_urls": ["https://example.org/2027/dates"],
    }
    item.update(overrides)
    return item


def deadline(kind: str, day: str, **extra: Any) -> dict[str, Any]:
    return {"type": kind, "label": kind, "datetime": f"{day}T23:59:00-12:00",
            "source_url": f"https://example.org/{kind}", **extra}


class MaintenanceTests(unittest.TestCase):
    def test_flags_estimated_stale_and_missing_deadline(self) -> None:
        item = {
            "id": "sample-2027", "short_title": "Sample 2027", "series": "Sample", "year": 2027,
            "last_checked": "2026-01-01", "confidence": "estimated",
            "conference_end": "2027-05-01", "deadlines": [],
            "website": "https://example.org", "source_urls": ["https://example.org/dates"],
        }
        result = review_queue([item], date(2026, 10, 6), 60)
        self.assertEqual(len(result), 1)
        self.assertIn("estimated", result[0][2])
        self.assertIn("no submission deadline", result[0][2])
        self.assertEqual(result[0][3], "https://example.org/dates")
        self.assertEqual(acceptance_queue([item], {}, date(2026, 10, 6)), ["Sample: no sourced rate"])

    def test_confirmed_fresh_complete_record_is_not_queued(self) -> None:
        item = {
            "id": "sample-2027", "short_title": "Sample 2027", "series": "Sample", "year": 2027,
            "last_checked": "2026-10-01", "confidence": "confirmed",
            "conference_end": "2027-05-01", "deadlines": [{"type": "full_paper"}],
            "website": "https://example.org",
        }
        self.assertEqual(review_queue([item], date(2026, 10, 6), 60), [])

    def test_confirmed_meeting_with_estimated_deadline_is_queued(self) -> None:
        item = {
            "id": "sample-2027", "short_title": "Sample 2027", "series": "Sample", "year": 2027,
            "last_checked": "2026-10-06", "confidence": "confirmed",
            "conference_end": "2027-05-01", "deadlines": [{"type": "full_paper", "confidence": "estimated"}],
            "website": "https://example.org",
        }
        result = review_queue([item], date(2026, 10, 6), 30)
        self.assertIn("compare with official CFP", result[0][2])

    def test_joint_edition_does_not_require_same_named_successor(self) -> None:
        joint = {
            "id": "ijcai-ecai-2026", "short_title": "IJCAI-ECAI 2026",
            "series": "IJCAI-ECAI", "year": 2026,
            "last_checked": "2026-10-06", "confidence": "confirmed",
            "conference_end": "2026-08-21", "deadlines": [],
            "website": "https://2026.ijcai.org/",
        }
        self.assertEqual(review_queue([joint], date(2026, 10, 6), 30), [])


class TriageTests(unittest.TestCase):
    def test_gate_is_the_due_action_and_closes_the_route_once_passed(self) -> None:
        item = edition(deadlines=[
            deadline("abstract", "2026-11-10", gate_for="full_paper"),
            deadline("full_paper", "2026-11-17"),
            deadline("camera_ready", "2026-11-05"),
            {"type": "short_paper", "label": "no date"},
        ])
        action = next_route_action(item, AS_OF)
        assert action is not None
        self.assertEqual((action.type, action.route, action.due, action.days), ("abstract", "full_paper", "2026-11-10", 12))
        self.assertEqual(action.source_url, "https://example.org/abstract")
        self.assertFalse(action.route_estimated)
        self.assertIsNone(next_route_action(item, date(2026, 11, 12)))
        item["deadlines"][0]["confidence"] = "estimated"
        action = next_route_action(item, AS_OF)
        assert action is not None
        self.assertTrue(action.route_estimated)
        self.assertEqual(action.confidence, "estimated")

    def test_earliest_independent_route_wins_and_inherits_edition_confidence(self) -> None:
        item = edition(confidence="estimated", deadlines=[
            deadline("short_paper", "2026-12-01"), deadline("full_paper", "2026-11-20"),
        ])
        action = next_route_action(item, AS_OF)
        assert action is not None
        self.assertEqual((action.type, action.confidence, action.route_estimated), ("full_paper", "estimated", True))

    def test_tiers_follow_due_date_confidence_and_successors(self) -> None:
        records = [
            edition(id="now-2027", series="Now", short_title="Now 2027", last_checked=STALE,
                    deadlines=[deadline("full_paper", "2026-11-20")]),
            edition(id="est-2027", series="Est", short_title="Est 2027", last_checked=STALE,
                    deadlines=[deadline("abstract", "2027-01-15", confidence="estimated")]),
            edition(id="soon-2027", series="Soon", short_title="Soon 2027", last_checked=STALE,
                    deadlines=[deadline("full_paper", "2027-01-15")]),
            edition(id="later-2027", series="Later", short_title="Later 2027", last_checked=STALE,
                    deadlines=[deadline("full_paper", "2027-03-01")]),
            edition(id="closed-2027", series="Closed", short_title="Closed 2027", last_checked=STALE,
                    deadlines=[deadline("full_paper", "2026-09-01")]),
            edition(id="closed-2028", series="Closed", short_title="Closed 2028", year=2028,
                    confidence="estimated", conference_start="2028-05-01", conference_end="2028-05-03",
                    deadlines=[deadline("full_paper", "2027-11-01")]),
            edition(id="solo-2027", series="Solo", short_title="Solo 2027", last_checked=STALE,
                    deadlines=[deadline("full_paper", "2026-09-01")]),
            edition(id="ijcai-ecai-2027", series="IJCAI-ECAI", short_title="IJCAI-ECAI 2027",
                    last_checked=STALE, deadlines=[deadline("full_paper", "2026-09-01")]),
            edition(id="past-2026", series="Past", short_title="Past 2026", year=2026,
                    conference_start="2026-06-01", conference_end="2026-06-03"),
            edition(id="pending-2027", series="Pending", short_title="Pending 2027", last_checked=STALE,
                    deadlines=[]),
            edition(id="camera-2027", series="Camera", short_title="Camera 2027", last_checked=STALE,
                    deadlines=[deadline("camera_ready", "2027-03-01")]),
            edition(id="live-2026", series="Live", short_title="Live 2026", year=2026, last_checked=STALE,
                    conference_start=AS_OF.isoformat(), conference_end="2026-11-05", deadlines=[]),
        ]
        rows = triage(records, AS_OF, 30)
        self.assertEqual({row.id: row.tier for row in rows}, {
            "now-2027": "act-now", "est-2027": "act-now", "soon-2027": "soon",
            "later-2027": "later", "closed-2028": "later", "closed-2027": "schedule-only",
            "ijcai-ecai-2027": "schedule-only", "solo-2027": "successor-missing",
            "past-2026": "successor-missing", "live-2026": "successor-missing",
            # No call recorded yet: find this edition's call, not a successor.
            "pending-2027": "call-unannounced", "camera-2027": "call-unannounced",
        })
        self.assertEqual([row.id for row in rows][:5], [
            "now-2027", "est-2027", "soon-2027", "later-2027", "closed-2028",
        ])
        self.assertEqual({row.id for row in rows[5:7]}, {"pending-2027", "camera-2027"})
        self.assertEqual([row.id for row in rows][7:9], ["closed-2027", "ijcai-ecai-2027"])
        self.assertEqual({row.id for row in rows[9:]}, {"past-2026", "solo-2027", "live-2026"})
        self.assertEqual(rows[0].milestone.due if rows[0].milestone else None, "2026-11-20")
        self.assertEqual({row.id for row in rows}, {row[1] for row in review_queue(records, AS_OF, 30)})


    def test_confirmed_route_due_soon_is_rechecked_before_the_deadline(self) -> None:
        due_soon = [deadline("full_paper", "2026-11-15")]  # 17 days after AS_OF
        records = [
            edition(id="recheck-2027", series="Recheck", short_title="Recheck 2027", last_checked="2026-10-15",
                    deadlines=due_soon),
            # Boundaries: due in exactly 21 days on a record checked exactly 10 days ago.
            edition(id="edge-2027", series="Edge", short_title="Edge 2027", last_checked="2026-10-19",
                    deadlines=[deadline("abstract", "2026-11-19", gate_for="full_paper"),
                               deadline("full_paper", "2026-11-26")]),
            edition(id="fresh-2027", series="Fresh", short_title="Fresh 2027", last_checked="2026-10-20",
                    deadlines=due_soon),
            edition(id="far-2027", series="Far", short_title="Far 2027", last_checked="2026-10-15",
                    deadlines=[deadline("full_paper", "2026-11-20")]),
            edition(id="camera-2027", series="Camera", short_title="Camera 2027", last_checked="2026-10-15",
                    deadlines=[deadline("camera_ready", "2026-11-15"), deadline("full_paper", "2027-02-01")]),
            # Already queued for another reason: the existing tier wins.
            edition(id="est-2027", series="Est", short_title="Est 2027", last_checked="2026-10-15",
                    deadlines=[deadline("full_paper", "2026-11-15", confidence="estimated")]),
            edition(id="stale-2027", series="Stale", short_title="Stale 2027", last_checked=STALE,
                    deadlines=due_soon),
        ]
        rows = triage(records, AS_OF, 30)
        self.assertEqual({row.id: row.tier for row in rows}, {
            "recheck-2027": "recheck", "edge-2027": "recheck", "est-2027": "act-now", "stale-2027": "act-now",
        })
        self.assertEqual([row.id for row in rows][2:], ["recheck-2027", "edge-2027"])
        recheck = rows[2]
        self.assertEqual(recheck.reasons, "confirmed full_paper due in 17 days, last checked 14 days ago")
        self.assertEqual(recheck.milestone.due if recheck.milestone else None, "2026-11-15")
        self.assertEqual(rows[3].reasons, "confirmed abstract due in 21 days, last checked 10 days ago")
        self.assertEqual(TIERS["recheck"][0], "Recheck before deadline")


class AdvisoryTests(unittest.TestCase):
    CITIES = {"paris": {"label": "Paris, France", "locations": ["Paris, France"]}}

    def test_midnight_opening_on_an_open_route_is_flagged(self) -> None:
        item = edition(deadlines=[
            deadline("full_paper", "2027-01-10", opens_at="2026-12-01T00:00:00Z"),
            deadline("short_paper", "2027-01-20", opens_at="2026-12-01T09:00:00-12:00"),
            deadline("abstract", "2026-10-01", opens_at="2026-09-01T00:00:00Z"),  # route closed: quiet
        ])
        found = [(row.check, row.url) for row in advisories([item], self.CITIES, AS_OF)]
        self.assertEqual(found, [("midnight-opening", "https://example.org/full_paper")])

    def test_flags_passed_estimates_missing_alias_old_urls_and_aggregators(self) -> None:
        item = edition(
            location="Lyon, France", mode="in-person", cfp_url="https://example.org/2026/cfp",
            source_urls=["https://www.linkedin.com/posts/example", "https://example.org/2027/"],
            deadlines=[
                deadline("abstract", "2026-10-01", confidence="estimated", source_url="https://example.org/2025/old"),
                deadline("full_paper", "2027-01-10"),
            ],
        )
        found = {(row.check, row.url) for row in advisories([item], self.CITIES, AS_OF)}
        self.assertEqual(found, {
            ("estimated-deadline-passed", "https://example.org/2025/old"),
            ("missing-city-alias", ""),
            ("old-year-url", "https://example.org/2026/cfp"),
            ("aggregator-source", "https://www.linkedin.com/posts/example"),
        })

    def test_quiet_for_placeholders_online_estimated_mapped_and_past_records(self) -> None:
        records = [
            edition(id="tba", location="To be announced", mode="in-person"),
            edition(id="online", location="Lyon, France", mode="online"),
            edition(id="estimated", location="Lyon, France", confidence="estimated",
                    cfp_url="https://example.org/2026/cfp"),
            edition(id="mapped", location="Paris, France", mode="in-person"),
            edition(id="past", year=2025, conference_start="2025-05-01", conference_end="2025-05-03",
                    location="Lyon, France", cfp_url="https://www.wikicfp.com/cfp/x"),
        ]
        self.assertEqual(advisories(records, self.CITIES, AS_OF), [])

    def test_aggregator_detection_uses_hosts_not_substrings(self) -> None:
        for url in ["https://x.com/conf", "https://twitter.com/a", "https://m.facebook.com/x",
                    "http://www.wikicfp.com/cfp/servlet/event.showcfp?eventid=1", "https://ccfddl.com/",
                    "https://github.com/ccfddl/ccf-deadlines", "https://aideadlin.es/?sub=ML",
                    "https://conferenceindex.org/event/x", "https://www.linkedin.com/posts/x"]:
            self.assertTrue(is_aggregator(url), url)
        for url in ["https://dropbox.com/x", "https://example.org/x.com", "https://linkedin.example.org/"]:
            self.assertFalse(is_aggregator(url), url)


class BacklogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = [
            edition(id="a", series="A", relevance="low"), edition(id="b", series="B", relevance="high"),
            edition(id="c", series="C", relevance="high"), edition(id="d", series="D"),
        ]

    def test_acceptance_backlog_puts_missing_then_oldest_then_relevant_first(self) -> None:
        rates = {"C": {"year": 2020, "source_url": "https://c.example"}, "D": {"year": 2026}}
        rows = acceptance_backlog(self.records, rates, AS_OF)
        self.assertEqual([row.name for row in rows], ["B", "A", "C"])
        self.assertEqual(rows[-1], BacklogRow("C", "latest evidence is 2020", "https://c.example"))
        self.assertEqual(acceptance_queue(self.records, rates, AS_OF),
                         ["A: no sourced rate", "B: no sourced rate", "C: latest evidence is 2020"])

    def test_scope_backlog_puts_missing_then_oldest_profiles_first(self) -> None:
        def profile(checked: str) -> dict[str, Any]:
            return {"scope_last_checked": checked, "source_year": 2027, "scope_source_urls": ["https://s.example"]}

        rows = scope_backlog(self.records, {"C": profile("2026-05-01"), "D": profile("2026-01-01")}, AS_OF, 30)
        self.assertEqual([row.name for row in rows], ["B", "A", "D", "C"])


class RenderTests(unittest.TestCase):
    def report(self) -> Report:
        milestone = Milestone("abstract", "Abstract", "2026-11-10", 12, "confirmed", True, "full_paper",
                              "https://example.org/abstract")
        rows = [
            TriagedEdition("act-now", "CNS* 2027", "cns-2027", "last checked 70 days ago",
                           "https://example.org", "2027-07-01", "2027-07-03", milestone),
            TriagedEdition("successor-missing", "Old 2026", "old-2026", "next edition not tracked",
                           "https://old.example", "2026-06-01", "2026-06-03", None),
        ]
        backlog = [BacklogRow(f"S{index}", "no sourced rate", "") for index in range(7)]
        return Report(AS_OF, 30, 3, rows, [], backlog, backlog[:2])

    def test_markdown_is_an_issue_body_with_headings_and_checkboxes(self) -> None:
        body = render_markdown(self.report(), 5)
        self.assertTrue(body.startswith("## Review queue as of 2026-10-29"))
        self.assertIn("#### Act now (1)", body)
        self.assertIn("- [ ] **CNS\\* 2027** (`cns-2027`)", body)
        self.assertIn("`abstract` (gate for `full_paper`) due 2026-11-10, in 12 days (confirmed; route estimated)",
                      body)
        self.assertIn("[source](<https://example.org/abstract>)", body)
        self.assertIn("meeting 2026-06-01 to 2026-06-03", body)
        self.assertIn("### Acceptance evidence backlog: 7 series", body)
        self.assertEqual(body.count("- [ ] **S"), 5 + 2)
        self.assertEqual(render_markdown(self.report(), None).count("- [ ] **S"), 7 + 2)

    def test_text_keeps_summary_line_and_collapses_backlogs(self) -> None:
        text = render_text(self.report(), 5)
        self.assertTrue(text.startswith("Edition review as of 2026-10-29: 2 of 3 editions"))
        self.assertIn("Acceptance evidence review: 7 series (showing 5; --full lists all)", text)
        self.assertIn("Scope review: 2 series\n", text)

    def test_json_reports_tiers_and_sampled_backlogs(self) -> None:
        payload = json.loads(render_json(self.report(), 5))
        self.assertEqual(payload["tier_counts"]["act-now"], 1)
        self.assertEqual(set(payload["tier_counts"]), set(TIERS))
        self.assertEqual(payload["editions"][0]["milestone"]["source_url"], "https://example.org/abstract")
        self.assertEqual((payload["acceptance"]["count"], len(payload["acceptance"]["items"])), (7, 5))
        self.assertFalse(payload["acceptance"]["complete"])
        self.assertTrue(json.loads(render_json(self.report(), None))["acceptance"]["complete"])

    def test_cli_formats_run_on_repository_data(self) -> None:
        def run(*args: str) -> str:
            return subprocess.run(
                [sys.executable, "scripts/maintenance_report.py", "--as-of", "2026-10-29", *args],
                cwd=ROOT, check=True, capture_output=True, text=True,
            ).stdout

        payload = json.loads(run("--format", "json"))
        self.assertTrue(payload["editions"])
        self.assertTrue(all(row["tier"] in TIERS for row in payload["editions"]))
        self.assertTrue(run("--format", "markdown").startswith("## Review queue as of 2026-10-29"))
        self.assertTrue(run().startswith("Edition review as of 2026-10-29:"))


class WorkflowTests(unittest.TestCase):
    def test_weekly_workflow_only_refreshes_one_issue(self) -> None:
        workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "maintenance-report.yml").read_text())
        triggers = workflow.get("on", workflow.get(True))
        self.assertIn("workflow_dispatch", triggers)
        self.assertEqual(triggers["schedule"], [{"cron": "0 6 * * 1"}])
        self.assertEqual(workflow["permissions"], {"contents": "read", "issues": "write"})
        steps = [step for job in workflow["jobs"].values() for step in job["steps"]]
        setup = next(step for step in steps if step.get("uses", "").startswith("actions/setup-python"))
        # CI and local virtual environments share one pinned interpreter version.
        self.assertEqual(setup["with"], {"python-version-file": ".python-version"})
        self.assertEqual((ROOT / ".python-version").read_text().strip(), "3.12")
        script = "\n".join(step.get("run", "") for step in steps)
        self.assertIn("maintenance_report.py --format markdown --as-of", script)
        self.assertIn("60 days without repository activity", script)
        self.assertIn('select(.title == "Review queue")', script)
        # Only the workflow's own issue is adopted, never one opened by someone else.
        self.assertIn("author:app/github-actions", script)
        for forbidden in ("git commit", "git push", "gh issue comment", "gh pr", "--write"):
            self.assertNotIn(forbidden, script)


if __name__ == "__main__":
    unittest.main()

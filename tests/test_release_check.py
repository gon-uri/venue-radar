from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from typing import Any, Callable
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import release_check
from release_check import (
    FAIL,
    PASS,
    SKIP,
    Result,
    changed_paths,
    docs_hashes,
    format_table,
    freshness_problem,
    output_lines,
)


class HashTests(unittest.TestCase):
    def test_hashes_nested_files_by_posix_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tags").mkdir()
            (root / "index.html").write_text("<p>a</p>", encoding="utf-8")
            (root / "tags" / "ml.ics").write_bytes(b"UID:x\r\n")
            hashes = docs_hashes(root)
            self.assertEqual(sorted(hashes), ["index.html", "tags/ml.ics"])
            self.assertEqual(docs_hashes(root), hashes)

    def test_changed_paths_reports_edits_additions_and_deletions(self) -> None:
        before = {"a.ics": "1", "b.ics": "2", "c.ics": "3"}
        after = {"a.ics": "1", "b.ics": "changed", "d.ics": "4"}
        self.assertEqual(changed_paths(before, after), ["b.ics", "c.ics", "d.ics"])
        self.assertEqual(changed_paths(before, dict(before)), [])


class FreshnessTests(unittest.TestCase):
    def test_last_updated_on_or_after_newest_check_passes(self) -> None:
        conferences = [{"last_checked": "2026-10-06"}, {"last_checked": date(2026, 10, 8)}]
        self.assertIsNone(freshness_problem("2026-10-08", conferences))
        self.assertIsNone(freshness_problem(date(2026, 10, 9), conferences))

    def test_last_updated_before_newest_check_fails(self) -> None:
        problem = freshness_problem("2026-10-07", [{"last_checked": "2026-10-08"}])
        self.assertEqual(problem, "last_updated 2026-10-07 < newest last_checked 2026-10-08")

    def test_last_updated_in_the_future_fails(self) -> None:
        problem = freshness_problem("2026-11-02", [{"last_checked": "2026-10-08"}], review_limit=date(2026, 10, 31))
        self.assertEqual(problem, "last_updated 2026-11-02 is in the future")
        self.assertIsNone(freshness_problem("2026-10-31", [{"last_checked": "2026-10-08"}],
                                            review_limit=date(2026, 10, 31)))

    def test_missing_values(self) -> None:
        self.assertIsNotNone(freshness_problem(None, [{"last_checked": "2026-10-08"}]))
        self.assertIsNone(freshness_problem("2026-10-08", [{"id": "x"}, "not-a-record"]))


class ReportTests(unittest.TestCase):
    def test_table_lists_every_check_with_aligned_status(self) -> None:
        table = format_table([Result("validate", PASS, "ok"), Result("deterministic build", FAIL)])
        lines = table.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertTrue(lines[0].startswith("CHECK"))
        self.assertEqual(lines[2].index("PASS"), lines[3].index("FAIL"))
        self.assertTrue(lines[3].endswith("FAIL"))

    def test_output_lines_drop_blanks(self) -> None:
        self.assertEqual(output_lines("docs/a.ics\n\ndocs/b.ics\n"), ["docs/a.ics", "docs/b.ics"])


class OrderingTests(unittest.TestCase):
    def _patched(self, build_status: str) -> tuple[list[str], Any]:
        calls: list[str] = []

        def fake(name: str, status: str = PASS) -> Callable[[], Result]:
            def check() -> Result:
                calls.append(name)
                return Result(name, status)
            return check

        patches = {
            "check_validate": fake("validate"),
            "check_tests": fake("unit tests"),
            "check_build": fake("build", build_status),
            "check_determinism": fake("deterministic build"),
            "check_drift": fake("docs/ vs git index"),
            "check_whitespace": fake("git diff --check"),
            "check_private_notes": fake("private notes"),
            "check_freshness": fake("last_updated"),
        }
        return calls, mock.patch.multiple(release_check, **patches)

    def test_runs_all_checks_in_documented_order(self) -> None:
        calls, patcher = self._patched(PASS)
        with patcher:
            results = release_check.run_checks()
        expected = ["validate", "unit tests", "build", "deterministic build",
                    "docs/ vs git index", "git diff --check", "private notes", "last_updated"]
        self.assertEqual(calls, expected)
        self.assertEqual([result.name for result in results], expected)

    def test_skip_tests_and_failed_build_skip_dependent_checks(self) -> None:
        calls, patcher = self._patched(FAIL)
        with patcher:
            results = release_check.run_checks(skip_tests=True)
        self.assertNotIn("unit tests", calls)
        self.assertNotIn("deterministic build", calls)
        statuses = {result.name: result.status for result in results}
        self.assertEqual(statuses["unit tests"], SKIP)
        self.assertEqual(statuses["deterministic build"], SKIP)
        self.assertEqual(statuses["docs/ vs git index"], SKIP)
        self.assertEqual(statuses["last_updated"], PASS)


if __name__ == "__main__":
    unittest.main()

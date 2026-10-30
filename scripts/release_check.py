"""Run the pre-publication checks in one command and print a pass/fail table.

Order: standalone validation, unit tests, full build, a second build to prove
deterministic output, docs/ drift against the git index, whitespace check
(excluding CRLF-folded ICS), no tracked private notes, and dataset
last_updated freshness. The builds regenerate docs/ exactly like
scripts/build_all.py; nothing else is modified and nothing is committed.

Usage: python3 scripts/release_check.py [--skip-tests]
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import yaml

from validate import latest_review_day

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"


@dataclass
class Result:
    name: str
    status: str
    detail: str = ""
    output: str = ""


def docs_hashes(root: Path) -> dict[str, str]:
    """Map each file below root (POSIX relative path) to its SHA-256."""
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*")) if path.is_file()
    }


def changed_paths(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))


def _as_date(value: Any) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def freshness_problem(last_updated: Any, conferences: Iterable[dict[str, Any]],
                      review_limit: date | None = None) -> str | None:
    """Return a message when last_updated predates the newest last_checked or is in the future, else None."""
    checked = [_as_date(item["last_checked"]) for item in conferences
               if isinstance(item, dict) and item.get("last_checked")]
    if not checked:
        return None
    if not last_updated:
        return "data/metadata.yml has no last_updated"
    newest = max(checked)
    if _as_date(last_updated) < newest:
        return f"last_updated {_as_date(last_updated)} < newest last_checked {newest}"
    if _as_date(last_updated) > (review_limit or latest_review_day()):
        return f"last_updated {_as_date(last_updated)} is in the future"
    return None


def output_lines(output: str) -> list[str]:
    """Non-empty lines of git name-only output (one path per line)."""
    return [line for line in output.splitlines() if line.strip()]


def format_table(results: list[Result]) -> str:
    width = max([len(result.name) for result in results] + [5])
    rows = [f"{'CHECK'.ljust(width)}  STATUS  DETAIL", f"{'-' * width}  ------  ------"]
    rows.extend(f"{result.name.ljust(width)}  {result.status.ljust(6)}  {result.detail}".rstrip()
                for result in results)
    return "\n".join(rows)


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")


def _tail(text: str, lines: int = 25) -> str:
    return "\n".join(text.strip().splitlines()[-lines:])


def _command(name: str, args: list[str], ok_detail: str) -> Result:
    result = _run(args)
    if result.returncode == 0:
        return Result(name, PASS, ok_detail)
    return Result(name, FAIL, f"exit {result.returncode}", _tail(result.stdout + result.stderr))


def check_validate() -> Result:
    return _command("validate", [sys.executable, "scripts/validate.py"], "data/registries valid")


def check_tests() -> Result:
    return _command("unit tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                    "all tests passed")


def check_build() -> Result:
    return _command("build", [sys.executable, "scripts/build_all.py"], "docs/ regenerated")


def check_determinism() -> Result:
    before = docs_hashes(DOCS_DIR)
    rebuilt = check_build()
    if rebuilt.status != PASS:
        return Result("deterministic build", FAIL, "second build failed", rebuilt.output)
    changed = changed_paths(before, docs_hashes(DOCS_DIR))
    if changed:
        return Result("deterministic build", FAIL, f"{len(changed)} file(s) differ",
                      "\n".join(changed[:20]))
    return Result("deterministic build", PASS, f"{len(before)} files identical")


def check_drift() -> Result:
    unstaged = _run(["git", "diff", "--name-only", "--", "docs/"]).stdout
    untracked = _run(["git", "ls-files", "--others", "--exclude-standard", "--", "docs/"]).stdout
    paths = output_lines(unstaged) + output_lines(untracked)
    if paths:
        return Result("docs/ vs git index", FAIL, f"{len(paths)} file(s) not staged; review, then git add docs/",
                      "\n".join(sorted(paths)[:20]))
    return Result("docs/ vs git index", PASS, "generated output staged/committed")


def check_whitespace() -> Result:
    pathspec = ["--", ".", ":(exclude)*.ics"]
    outputs = [_run(["git", "diff", "--check", *pathspec]),
               _run(["git", "diff", "--cached", "--check", *pathspec])]
    problems = "".join(result.stdout for result in outputs if result.returncode != 0)
    if problems:
        return Result("git diff --check", FAIL, "whitespace errors (non-ICS)", _tail(problems))
    return Result("git diff --check", PASS, "no whitespace errors (ICS excluded)")


def check_private_notes() -> Result:
    tracked = output_lines(_run(["git", "ls-files", "--", "private_notes/"]).stdout)
    if tracked:
        return Result("private notes", FAIL, f"{len(tracked)} tracked file(s); git rm --cached them",
                      "\n".join(tracked[:20]))
    return Result("private notes", PASS, "none tracked or staged")


def check_freshness() -> Result:
    try:
        metadata = yaml.safe_load((ROOT / "data" / "metadata.yml").read_text(encoding="utf-8")) or {}
        conferences = yaml.safe_load((ROOT / "data" / "conferences.yml").read_text(encoding="utf-8")) or []
        problem = freshness_problem(metadata.get("last_updated"), conferences)
    except (OSError, ValueError, TypeError, yaml.YAMLError) as exc:
        return Result("last_updated", FAIL, f"cannot read dates: {exc}")
    if problem:
        return Result("last_updated", FAIL, problem + " (set it before building)")
    return Result("last_updated", PASS, f"{metadata.get('last_updated')} >= newest last_checked")


def run_checks(skip_tests: bool = False) -> list[Result]:
    results = [check_validate()]
    results.append(Result("unit tests", SKIP, "--skip-tests") if skip_tests else check_tests())
    build = check_build()
    results.append(build)
    if build.status == PASS:
        results.extend([check_determinism(), check_drift()])
    else:
        results.extend(Result(name, SKIP, "build failed")
                       for name in ("deterministic build", "docs/ vs git index"))
    results.extend([check_whitespace(), check_private_notes(), check_freshness()])
    return results


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skip-tests", action="store_true", help="skip the unit-test step")
    args = parser.parse_args(list(argv) if argv is not None else None)

    results = run_checks(skip_tests=args.skip_tests)
    print(format_table(results))
    failures = [result for result in results if result.status == FAIL]
    for result in failures:
        if result.output:
            print(f"\n--- {result.name} ---\n{result.output}")
    print(f"\n{'FAILED' if failures else 'OK'}: {len(failures)} failing check(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

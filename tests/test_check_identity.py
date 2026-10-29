from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_ics import _property
from check_identity import (
    UID_DOMAIN,
    compare,
    edition_ids,
    ics_uids,
    is_retired,
    parse_retired,
    unexplained_removals,
    unfold_ics,
)


def calendar(*uids: str) -> str:
    """A minimal feed folded exactly like the real builder output."""
    lines = ["BEGIN:VCALENDAR"]
    for uid in uids:
        lines += ["BEGIN:VEVENT", *_property("UID", uid), "SUMMARY:x", "END:VEVENT"]
    return "\r\n".join(lines + ["END:VCALENDAR"]) + "\r\n"


def uid(local: str) -> str:
    return f"{local}@{UID_DOMAIN}"


EDITIONS = '- id: "alpha-2026"\n  series: "Alpha"\n- id: "beta-2027"\n  series: "Beta"\n'


class UnfoldingTests(unittest.TestCase):
    def test_unfolds_crlf_space_and_tab_continuations(self) -> None:
        text = "UID:abc\r\n def\r\n\tghi\r\nSUMMARY:x\r\n"
        self.assertEqual(unfold_ics(text), ["UID:abcdefghi", "SUMMARY:x", ""])

    def test_folded_long_uid_is_recovered_whole(self) -> None:
        long_uid = uid("dynamics-days-asia-pacific-2024-conference")
        self.assertGreater(len(f"UID:{long_uid}"), 75)
        self.assertEqual(ics_uids(calendar(long_uid)), {long_uid})

    def test_only_uid_properties_are_collected(self) -> None:
        text = "DESCRIPTION:UID:not-an-id\r\nUID:real\r\nX-UID:other\r\n"
        self.assertEqual(ics_uids(text), {"real"})

    def test_published_feed_uids_parse_completely(self) -> None:
        text = (ROOT / "docs" / "calendar-all.ics").read_text(encoding="utf-8")
        uids = ics_uids(text)
        self.assertEqual(len(uids), text.count("BEGIN:VEVENT"))
        self.assertTrue(all(value.endswith(f"@{UID_DOMAIN}") for value in uids))


class RetiredListTests(unittest.TestCase):
    def test_committed_retired_list_is_valid(self) -> None:
        parse_retired((ROOT / "data" / "retired_identities.yml").read_text(encoding="utf-8"))

    def test_empty_or_comment_only_file_retires_nothing(self) -> None:
        for text in ("", "[]\n", "# header only\n"):
            with self.subTest(text=text):
                self.assertEqual(parse_retired(text), set())

    def test_valid_entries_return_ids(self) -> None:
        text = '- id: "alpha-2026"\n  reason: "Duplicate"\n  date: "2026-10-29"\n'
        self.assertEqual(parse_retired(text), {"alpha-2026"})

    def test_rejects_incomplete_or_malformed_entries(self) -> None:
        bad = [
            "id: alpha-2026\n",
            "- alpha-2026\n",
            '- id: "alpha-2026"\n  date: "2026-10-29"\n',
            '- id: "alpha-2026"\n  reason: " "\n  date: "2026-10-29"\n',
            '- id: "alpha-2026"\n  reason: "Duplicate"\n  date: "29/10/2026"\n',
        ]
        for text in bad:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_retired(text)

    def test_retired_edition_covers_only_its_own_event_uids(self) -> None:
        retired = {"alpha-2026"}
        self.assertTrue(is_retired("alpha-2026", retired))
        self.assertTrue(is_retired(uid("alpha-2026-conference"), retired))
        self.assertTrue(is_retired(uid("alpha-2026-deadline-full-paper"), retired))
        self.assertFalse(is_retired(uid("alpha-2026x-conference"), retired))
        self.assertFalse(is_retired("alpha-2026-conference@elsewhere", retired))
        self.assertTrue(is_retired(uid("beta-2027-deadline-abstract"),
                                   {uid("beta-2027-deadline-abstract")}))


class CompareTests(unittest.TestCase):
    def test_edition_ids_read_conference_list(self) -> None:
        self.assertEqual(edition_ids(EDITIONS), {"alpha-2026", "beta-2027"})
        self.assertEqual(edition_ids(""), set())
        with self.assertRaises(ValueError):
            edition_ids("alpha: 1\n")

    def test_additions_pass_and_are_counted(self) -> None:
        base = calendar(uid("alpha-2026-conference"))
        current = calendar(uid("alpha-2026-conference"), uid("beta-2027-conference"))
        lines, missing = compare(base, '- id: "alpha-2026"\n', current, EDITIONS, set())
        self.assertEqual(missing, [])
        self.assertIn("calendar UIDs: 1 -> 2 (+1 added, -0 removed)", lines)
        self.assertIn("edition IDs: 1 -> 2 (+1 added, -0 removed)", lines)

    def test_removed_uid_and_edition_fail_unless_retired(self) -> None:
        base = calendar(uid("alpha-2026-conference"), uid("beta-2027-deadline-abstract"))
        current = calendar(uid("alpha-2026-conference"))
        current_yaml = '- id: "alpha-2026"\n'
        _, missing = compare(base, EDITIONS, current, current_yaml, set())
        self.assertEqual(missing, ["beta-2027-deadline-abstract@" + UID_DOMAIN, "beta-2027"])
        lines, missing = compare(base, EDITIONS, current, current_yaml, {"beta-2027"})
        self.assertEqual(missing, [])
        self.assertIn("removed but listed in data/retired_identities.yml: 2", lines)

    def test_missing_base_files_count_as_nothing_published(self) -> None:
        lines, missing = compare(None, None, calendar(uid("alpha-2026-conference")), EDITIONS, set())
        self.assertEqual(missing, [])
        self.assertIn("edition IDs: 0 -> 2 (+2 added, -0 removed)", lines)

    def test_unexplained_removals_are_sorted(self) -> None:
        self.assertEqual(unexplained_removals({"b", "a", "c"}, {"c"}, set()), ["a", "b"])


if __name__ == "__main__":
    unittest.main()

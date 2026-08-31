#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for file_vuln_issues.py — uses unittest so no external deps.

Run:  python -m unittest _scripts/test_file_vuln_issues.py -v
or:   python _scripts/test_file_vuln_issues.py
"""
import os
import subprocess
import sys
import unittest
from unittest.mock import MagicMock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import file_vuln_issues as fvi  # noqa: E402


def _ok(issue_n):
    return subprocess.CompletedProcess(
        args=[], returncode=0,
        stdout=f"https://github.com/neohiro/achievement-hacks/issues/{issue_n}",
        stderr="",
    )


def _err(issue_n, msg="gh: not logged in"):
    return subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr=msg,
    )


class TestRepoConstant(unittest.TestCase):
    def test_canonical_repo(self):
        self.assertEqual(fvi.REPO, "neohiro/achievement-hacks")

    def test_no_wrong_name_in_source(self):
        src = open(os.path.join(HERE, "file_vuln_issues.py"), encoding="utf-8")
        with src:
            content = src.read()
        self.assertNotIn("achievementhacks", content,
                         "wrong repo name 'achievementhacks' (no dash) present in script")


class TestIssuesStructure(unittest.TestCase):
    def test_six_issues(self):
        self.assertEqual(len(fvi.ISSUES), 6)

    def test_each_issue_has_required_fields(self):
        for issue in fvi.ISSUES:
            self.assertIn("title", issue)
            self.assertIn("body", issue)
            self.assertIn("labels", issue)
            self.assertTrue(issue["title"].startswith("[VULN-"))
            self.assertGreater(len(issue["body"]), 100, "body too short")
            self.assertGreater(len(issue["labels"]), 0, "no labels")

    def test_unique_titles(self):
        titles = [i["title"] for i in fvi.ISSUES]
        self.assertEqual(len(titles), len(set(titles)))

    def test_unique_vuln_ids(self):
        import re
        ids = [re.search(r"VULN-\d{3}", i["title"]).group() for i in fvi.ISSUES]
        self.assertEqual(sorted(ids), ["VULN-001", "VULN-002", "VULN-003",
                                       "VULN-004", "VULN-005", "VULN-006"])

    def test_required_labels_present(self):
        for issue in fvi.ISSUES:
            for required in ("security", "vulnerability", "achievement"):
                self.assertIn(required, issue["labels"],
                              f"label {required!r} missing in {issue['title']!r}")

    def test_canonical_links_in_bodies(self):
        for issue in fvi.ISSUES:
            self.assertNotIn("achievementhacks", issue["body"],
                             f"wrong repo ref in body of {issue['title']!r}")
            self.assertIn("neohiro/achievement-hacks", issue["body"],
                          f"canonical repo ref missing in body of {issue['title']!r}")


class TestBuildCommand(unittest.TestCase):
    def test_command_shape(self):
        cmd = fvi.build_command(fvi.ISSUES[0])
        self.assertEqual(cmd[0], "gh")
        self.assertEqual(cmd[1], "issue")
        self.assertEqual(cmd[2], "create")
        self.assertIn("--repo", cmd)
        self.assertEqual(cmd[cmd.index("--repo") + 1], "neohiro/achievement-hacks")
        self.assertIn("--title", cmd)
        self.assertIn("--body", cmd)

    def test_repeated_label_flags(self):
        # The fix: --label per item, not comma-joined
        cmd = fvi.build_command(fvi.ISSUES[0])
        label_indices = [i for i, x in enumerate(cmd) if x == "--label"]
        self.assertEqual(len(label_indices), len(fvi.ISSUES[0]["labels"]),
                         "each label must be passed as a separate --label flag")
        for idx in label_indices:
            self.assertNotIn(",", cmd[idx + 1],
                             "labels must not be comma-joined")

    def test_labels_preserved(self):
        issue = fvi.ISSUES[2]  # heart-on-your-sleeve
        cmd = fvi.build_command(issue)
        labels_in_order = []
        for j, x in enumerate(cmd):
            if x == "--label":
                labels_in_order.append(cmd[j + 1])
        self.assertEqual(labels_in_order, issue["labels"])


class TestDryRun(unittest.TestCase):
    def test_dry_run_does_not_invoke_runner(self):
        runner = MagicMock()
        rc = fvi.file_issues(dry_run=True, runner=runner)
        self.assertEqual(rc, 0)
        runner.assert_not_called()

    def test_dry_run_default_runner_not_called(self):
        # ensure default runner is not invoked in dry-run even with no mock
        rc = fvi.file_issues(dry_run=True)
        self.assertEqual(rc, 0)


class TestSuccessPath(unittest.TestCase):
    def test_all_issues_called(self):
        runner = MagicMock(side_effect=lambda cmd: _ok(1))
        rc = fvi.file_issues(runner=runner)
        self.assertEqual(rc, 0)
        self.assertEqual(runner.call_count, len(fvi.ISSUES))

    def test_each_command_targets_correct_repo(self):
        runner = MagicMock(side_effect=lambda cmd: _ok(1))
        fvi.file_issues(runner=runner)
        for call in runner.call_args_list:
            cmd = call.args[0]
            self.assertIn("neohiro/achievement-hacks", cmd)


class TestStopOnError(unittest.TestCase):
    def test_stops_at_first_failure(self):
        runner = MagicMock(side_effect=lambda cmd: _err(1))
        rc = fvi.file_issues(stop_on_error=True, runner=runner)
        self.assertEqual(rc, 1)
        self.assertEqual(runner.call_count, 1, "must stop on first error")

    def test_continues_when_stop_on_error_false(self):
        runner = MagicMock(side_effect=lambda cmd: _err(1))
        rc = fvi.file_issues(stop_on_error=False, runner=runner)
        self.assertEqual(rc, 0, "continues and returns 0 when not stopping")
        self.assertEqual(runner.call_count, len(fvi.ISSUES))


class TestCli(unittest.TestCase):
    def test_help_exits_zero(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "file_vuln_issues.py"), "--help"],
            capture_output=True, encoding="utf-8", timeout=10,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("--dry-run", proc.stdout)
        self.assertIn("--stop-on-error", proc.stdout)

    def test_dry_run_exit_zero(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "file_vuln_issues.py"), "--dry-run"],
            capture_output=True, encoding="utf-8", timeout=10,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("[DRY-RUN]", proc.stderr)
        # confirm we never actually called gh
        self.assertNotIn("https://github.com/neohiro/achievement-hacks/issues/", proc.stdout)

    def test_unknown_flag_exits_nonzero(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "file_vuln_issues.py"), "--bogus"],
            capture_output=True, encoding="utf-8", timeout=10,
        )
        self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

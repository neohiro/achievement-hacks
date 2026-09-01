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
        self.assertEqual(runner.call_count, len(fvi.ISSUES),
                         "must process all issues even on error")
        self.assertEqual(rc, 1, "returns 1 when any issue fails (even with stop_on_error=False)")


class TestGhRun(unittest.TestCase):
    def test_gh_run_returns_completed_process(self):
        r = subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")
        with unittest.mock.patch("subprocess.run", return_value=r) as mock_sr:
            result = fvi._gh_run(["gh", "issue", "list"])
            mock_sr.assert_called_once_with(
                ["gh", "issue", "list"],
                capture_output=True, encoding="utf-8", errors="replace",
            )
            self.assertEqual(result.stdout, "ok")

    def test_gh_run_string_output_not_bytes(self):
        r = subprocess.CompletedProcess(args=[], returncode=0, stdout="url", stderr="")
        with unittest.mock.patch("subprocess.run", return_value=r):
            result = fvi._gh_run(["gh"])
            self.assertIsInstance(result.stdout, str)
            self.assertIsInstance(result.stderr, str)


class TestExceptionHandling(unittest.TestCase):
    def test_file_not_found_returns_one(self):
        """FileNotFoundError means gh is not installed — this is a fatal failure."""
        runner = MagicMock(side_effect=FileNotFoundError("gh not found"))
        rc = fvi.file_issues(runner=runner)
        self.assertEqual(rc, 1)
        self.assertEqual(runner.call_count, len(fvi.ISSUES))

    def test_file_not_found_stop_on_error_returns_one(self):
        runner = MagicMock(side_effect=FileNotFoundError("gh not found"))
        rc = fvi.file_issues(stop_on_error=True, runner=runner)
        self.assertEqual(rc, 1)
        self.assertEqual(runner.call_count, 1)

    def test_generic_exception_returns_one(self):
        """Any unexpected exception is treated as a failure — returns 1."""
        runner = MagicMock(side_effect=RuntimeError("unexpected"))
        rc = fvi.file_issues(runner=runner)
        self.assertEqual(rc, 1)
        self.assertEqual(runner.call_count, len(fvi.ISSUES))

    def test_generic_exception_stop_on_error_returns_one(self):
        runner = MagicMock(side_effect=RuntimeError("unexpected"))
        rc = fvi.file_issues(stop_on_error=True, runner=runner)
        self.assertEqual(rc, 1)
        self.assertEqual(runner.call_count, 1)


class TestRateLimitDetection(unittest.TestCase):
    def test_detects_429_in_stderr(self):
        self.assertTrue(fvi._is_rate_limited("API rate limit exceeded: 429"))
        self.assertTrue(fvi._is_rate_limited("HTTP 429: too many requests"))
        self.assertTrue(fvi._is_rate_limited("Rate limit reached"))

    def test_ignores_unrelated_errors(self):
        self.assertFalse(fvi._is_rate_limited(""))
        self.assertFalse(fvi._is_rate_limited("gh: not logged in"))
        self.assertFalse(fvi._is_rate_limited("could not resolve to a Repository"))


class TestRetry(unittest.TestCase):
    def test_retry_succeeds_on_second_attempt(self):
        """A 429 first, then a success should be retried exactly once."""
        results = [
            subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="HTTP 429"),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="https://x/i/1", stderr=""),
        ]
        runner = MagicMock(side_effect=results)
        # Patch _gh_run so we exercise the retry path, not the injected mock
        with unittest.mock.patch("file_vuln_issues._gh_run", side_effect=results), \
             unittest.mock.patch("file_vuln_issues.time.sleep") as mock_sleep:
            result = fvi._retry_gh_run(["gh", "issue", "create"])
        self.assertEqual(result.returncode, 0)
        mock_sleep.assert_called_once()  # backed off once before retry

    def test_retry_gives_up_after_max_attempts(self):
        results = [
            subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="HTTP 429")
        ] * 3
        with unittest.mock.patch("file_vuln_issues._gh_run", side_effect=results), \
             unittest.mock.patch("file_vuln_issues.time.sleep") as mock_sleep:
            result = fvi._retry_gh_run(["gh"], max_retries=3)
        self.assertEqual(result.returncode, 1, "returns last failure after max retries")
        self.assertEqual(mock_sleep.call_count, 2, "backed off 2 times between 3 attempts")

    def test_retry_does_not_retry_non_rate_limit_failures(self):
        result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="not logged in")
        with unittest.mock.patch("file_vuln_issues._gh_run", return_value=result), \
             unittest.mock.patch("file_vuln_issues.time.sleep") as mock_sleep:
            out = fvi._retry_gh_run(["gh"])
        self.assertEqual(out.returncode, 1)
        mock_sleep.assert_not_called()


class TestScrubSensitive(unittest.TestCase):
    def test_redacts_ghp_token(self):
        text = "Error: ghp_abc123DEF456ghi789jkl012mno345pqr678STU for repo x"
        out = fvi._scrub_sensitive(text)
        self.assertNotIn("ghp_abc123DEF456", out)
        self.assertIn("REDACTED", out)

    def test_redacts_pat_token(self):
        text = "auth: github_pat_11ABCDEFG0_xyz123 is invalid"
        out = fvi._scrub_sensitive(text)
        self.assertNotIn("xyz123", out)
        self.assertIn("REDACTED", out)

    def test_leaves_normal_text_alone(self):
        text = "gh: command not found"
        self.assertEqual(fvi._scrub_sensitive(text), text)


class TestSecurityAnchors(unittest.TestCase):
    """Verify every SECURITY.md anchor referenced in issue bodies resolves to a heading."""

    @classmethod
    def setUpClass(cls):
        sec_path = os.path.join(HERE, "..", "SECURITY.md")
        with open(sec_path, encoding="utf-8") as f:
            cls.sec_content = f.read()

    @staticmethod
    def _heading_to_slug(heading_text):
        """Match github-slugger: spaces->hyphens first, then strip non-alnum/hyphen."""
        import re
        slug = heading_text.lower().strip()
        slug = re.sub(r"[\s]+", "-", slug)
        slug = re.sub(r"[^\w-]", "", slug)
        return slug.strip("-")

    def test_all_anchored_links_resolve(self):
        import re
        sec_headings = re.findall(r"^#{1,6}\s+(.+)$", self.sec_content, re.MULTILINE)
        valid_slugs = {self._heading_to_slug(h) for h in sec_headings}

        all_anchors = []
        for issue in fvi.ISSUES:
            all_anchors += re.findall(r"SECURITY\.md#([\w-]+)", issue["body"])

        for anchor in set(all_anchors):
            self.assertIn(
                anchor, valid_slugs,
                f"anchor #{anchor} referenced in issue body but no matching heading in SECURITY.md",
            )


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

#!/usr/bin/env python3
"""Tests for file_vuln_issues.py — uses unittest so no external deps.

Run:  python -m unittest _scripts/test_file_vuln_issues.py -v
or:   python _scripts/test_file_vuln_issues.py
"""
import io
import json
import os
import re
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
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
    def test_seven_issues(self):
        self.assertEqual(len(fvi.ISSUES), 7)

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
        ids = [re.search(r"VULN-\d{3}", i["title"]).group() for i in fvi.ISSUES]
        self.assertEqual(sorted(ids), ["VULN-001", "VULN-002", "VULN-003",
                                       "VULN-004", "VULN-005", "VULN-006",
                                       "VULN-007"])

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

    def test_continues_but_reports_failure_when_stop_on_error_false(self):
        """Regression: this used to assert rc == 0 with every issue failing.

        Reporting success after filing nothing is the one outcome this script
        must never produce. stop_on_error governs early abort only; it must never
        change the reported outcome.
        """
        runner = MagicMock(side_effect=lambda cmd: _err(1))
        rc = fvi.file_issues(stop_on_error=False, runner=runner)
        self.assertEqual(runner.call_count, len(fvi.ISSUES),
                         "must process all issues even on error")
        self.assertEqual(rc, 1, "returns 1 when any issue fails (even with stop_on_error=False)")

    def test_partial_failure_reports_failure(self):
        seen = []

        def runner(cmd):
            seen.append(cmd)
            return _ok(len(seen)) if len(seen) <= 2 else _err(len(seen))

        rc = fvi.file_issues(stop_on_error=False, runner=runner)
        self.assertEqual(rc, 1, "5 of 7 failed, so the run must not report success")
        self.assertEqual(len(seen), len(fvi.ISSUES))

    def test_all_success_reports_zero(self):
        runner = MagicMock(side_effect=lambda cmd: _ok(1))
        rc = fvi.file_issues(stop_on_error=False, runner=runner)
        self.assertEqual(rc, 0)


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

    def test_gh_run_decodes_leniently(self):
        """errors="replace" must be passed so cp1252 output cannot crash a run.

        Asserted via the call rather than by fabricating a CompletedProcess,
        because subprocess.run is mocked and the decoding never actually runs.
        """
        r = subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")
        with unittest.mock.patch("subprocess.run", return_value=r) as mock_sr:
            fvi._gh_run(["gh"])
        self.assertEqual(mock_sr.call_args.kwargs["errors"], "replace")

    def test_gh_run_has_a_timeout(self):
        r = subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")
        with unittest.mock.patch("subprocess.run", return_value=r) as mock_sr:
            fvi._gh_run(["gh"])
        self.assertGreater(mock_sr.call_args.kwargs["timeout"], 0)

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

    def test_timeout_is_reported_as_failure(self):
        runner = MagicMock(side_effect=subprocess.TimeoutExpired(cmd="gh", timeout=1))
        rc = fvi.file_issues(runner=runner)
        self.assertEqual(rc, 1)
        self.assertEqual(runner.call_count, len(fvi.ISSUES))

    def test_timeout_stop_on_error_aborts_immediately(self):
        runner = MagicMock(side_effect=subprocess.TimeoutExpired(cmd="gh", timeout=1))
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
        out = fvi.scrub_sensitive(text)
        self.assertNotIn("ghp_abc123DEF456", out)
        self.assertIn("REDACTED", out)

    def test_redacts_pat_token(self):
        text = "auth: github_pat_11ABCDEFG0_xyz123 is invalid"
        out = fvi.scrub_sensitive(text)
        self.assertNotIn("xyz123", out)
        self.assertIn("REDACTED", out)

    def test_leaves_normal_text_alone(self):
        text = "gh: command not found"
        self.assertEqual(fvi.scrub_sensitive(text), text)

    def test_redacts_gho_token(self):
        text = "Error: gho_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA is invalid"
        out = fvi.scrub_sensitive(text)
        self.assertNotIn("gho_", out)
        self.assertIn("***REDACTED***", out)

    def test_redacts_ghs_token(self):
        text = "auth: ghs_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx failed"
        out = fvi.scrub_sensitive(text)
        self.assertNotIn("ghs_", out)
        self.assertIn("***REDACTED***", out)

    def test_redacts_multiple_tokens(self):
        text = "ghp_AAA github_pat_xxx gho_BBB ghs_CCC"
        out = fvi.scrub_sensitive(text)
        self.assertNotIn("ghp_AAA", out)
        self.assertNotIn("github_pat_xxx", out)
        self.assertNotIn("gho_BBB", out)
        self.assertNotIn("ghs_CCC", out)


# Characters to strip in slugify_heading (em-dash, en-dash, punctuation).
# The en-dash is intentional test data for the slugifier.
_SLUG_STRIP_TABLE = [
    ("—", "-"),   # em-dash
    ("\u2013", "-"),   # en-dash
    ("—", "-"),   # left/right em-dash variants
    (":", ""),
    ("(", ""),
    (")", ""),
    ("/", ""),
    ("&", ""),
    ("'", ""),
    (".", ""),
    (",", ""),
]


class TestSlugifyHeading(unittest.TestCase):
    """Verify the GitHub-compatible heading slugifier behaves correctly.

    The previous version incorrectly kept `—` (em-dash) as `--`, producing
    anchor links that didn't match the real GitHub-rendered slugs. These
    tests pin down the correct behavior so a future regression is caught.
    """

    def setUp(self):
        from test_file_vuln_issues import TestSecurityAnchors
        self.slugify = TestSecurityAnchors._slugify_heading

    def test_em_dash_collapses_to_single_hyphen(self):
        self.assertEqual(
            self.slugify("VULN-001: Quickdraw — Sub-5-Minute Issue/PR Close Loop"),
            "vuln-001-quickdraw-sub-5-minute-issuepr-close-loop",
        )

    def test_colons_and_parens_stripped(self):
        self.assertEqual(
            self.slugify("VULN-002: YOLO (something)"),
            "vuln-002-yolo-something",
        )

    def test_consecutive_hyphens_collapsed(self):
        self.assertEqual(
            self.slugify("foo --- bar"),
            "foo-bar",
        )

    def test_lowercases(self):
        self.assertEqual(self.slugify("HELLO World"), "hello-world")

    def test_leading_trailing_hyphens_stripped(self):
        self.assertEqual(self.slugify("  --hi--  "), "hi")

    def test_pure_unicode_stripped(self):
        self.assertEqual(self.slugify("🎓 Campus Expert"), "campus-expert")


class TestSecurityAnchors(unittest.TestCase):
    """Verify every SECURITY.md anchor referenced in issue bodies resolves to a heading.

    Uses the correct GitHub-compatible slugifier that:
      1. Replaces unicode punctuation (em-dash, en-dash, etc.) with ASCII equivalents
      2. Replaces spaces with hyphens
      3. Removes non-alphanumeric characters except hyphens
      4. Collapses consecutive hyphens to one
      5. Strips leading/trailing hyphens
    """

    @classmethod
    def setUpClass(cls):
        sec_path = os.path.join(HERE, "..", "SECURITY.md")
        with open(sec_path, encoding="utf-8") as f:
            cls.sec_content = f.read()

    @staticmethod
    def _slugify_heading(heading: str) -> str:
        """GitHub-compatible heading-to-anchor slugifier.

        Matches the algorithm GitHub uses to render heading anchor IDs.
        Handles:
          - Unicode punctuation (em-dash → '-', en-dash → '-')
          - Forward slashes, ampersands, parens → stripped
          - Consecutive hyphens collapsed to one
          - Leading/trailing hyphens stripped
        """
        import unicodedata

        slug = heading.lower()
        slug = unicodedata.normalize("NFKD", slug)
        # Replace unicode punctuation that GitHub treats as word separators
        for old, new in _SLUG_STRIP_TABLE:
            slug = slug.replace(old, new)
        # Spaces → hyphens
        slug = re.sub(r"\s+", "-", slug)
        # Remove any remaining non-alphanumeric (keep hyphens)
        slug = re.sub(r"[^a-z0-9-]", "", slug)
        # Collapse consecutive hyphens
        slug = re.sub(r"-+", "-", slug)
        return slug.strip("-")

    def test_all_anchored_links_resolve(self):
        sec_headings = re.findall(r"^#{1,6}\s+(.+)$", self.sec_content, re.MULTILINE)
        valid_slugs = {self._slugify_heading(h) for h in sec_headings}

        all_anchors = []
        for issue in fvi.ISSUES:
            all_anchors += re.findall(r"SECURITY\.md#([\w-]+)", issue["body"])

        failures = []
        for anchor in sorted(set(all_anchors)):
            if anchor not in valid_slugs:
                failures.append(anchor)

        self.assertEqual(
            failures, [],
            f"These anchor(s) have no matching heading in SECURITY.md: {failures}\n"
            f"Expected slugs (sample): {sorted(valid_slugs)[:6]}",
        )


class TestCli(unittest.TestCase):
    def test_help_exits_zero(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "file_vuln_issues.py"), "--help"],
            capture_output=True, encoding="utf-8", errors="replace", timeout=10,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("--dry-run", proc.stdout)
        self.assertIn("--stop-on-error", proc.stdout)
        self.assertIn("--sync", proc.stdout,
                      "new --sync flag must appear in help output")
        self.assertIn("--format", proc.stdout,
                      "--format flag must appear in help output")

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


class TestSyncFormat(unittest.TestCase):
    """Tests for the --sync --format {summary,diff,json} modes."""

    # These three shelled out to file_vuln_issues.py with no injection, so they
    # made live `gh issue list` calls against the real repository. In a unit
    # suite that is wrong twice over: the result depends on live repo state, and
    # CI's GITHUB_TOKEN is rate limited and scoped differently from a
    # developer's. That is why these were the three failures on every run while
    # the other 56 passed.
    #
    # sync_issues() takes an injectable runner, so drive it directly with a fake
    # that reports every VULN id as present and up to date. Deterministic and
    # offline.

    @staticmethod
    def _fake_issue_list(writes, body_transform=None):
        """Fake runner: `gh issue list` returns one matching issue per VULN id.

        `body_transform(vid, body)` optionally rewrites a returned body, which is
        how the drifted-body case is expressed.
        """
        def runner(cmd):
            if "issue" in cmd and "list" in cmd:
                rows = []
                for idx, issue in enumerate(fvi.ISSUES):
                    vid = fvi._extract_vuln_id(issue["title"])
                    body = issue["body"]
                    if body_transform is not None:
                        body = body_transform(vid, body)
                    rows.append({"number": idx + 1,
                                 "title": f"[{vid}] placeholder",
                                 "body": body,
                                 "labels": [{"name": "vulnerability"}]})
                return subprocess.CompletedProcess(
                    args=cmd, returncode=0, stdout=json.dumps(rows), stderr="")
            writes.append(cmd)
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        return runner

    @classmethod
    def _all_up_to_date_runner(cls, writes):
        return cls._fake_issue_list(writes)

    def test_sync_format_summary_reports_no_writes_in_dry_run(self):
        writes = []
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = fvi.sync_issues(dry_run=True, format="summary",
                                 runner=self._all_up_to_date_runner(writes))
        self.assertEqual(rc, 0)
        self.assertEqual(writes, [], "dry run must not issue any write commands")
        self.assertIn("[SYNC]", buf.getvalue())

    def test_sync_format_diff_exits_zero(self):
        writes = []
        with redirect_stderr(io.StringIO()):
            rc = fvi.sync_issues(dry_run=True, format="diff",
                                 runner=self._all_up_to_date_runner(writes))
        self.assertEqual(rc, 0)
        self.assertEqual(writes, [], "dry run must not issue any write commands")

    def test_sync_format_json_reports_empty_work_lists(self):
        writes = []
        buf = io.StringIO()
        with redirect_stderr(io.StringIO()), redirect_stdout(buf):
            rc = fvi.sync_issues(dry_run=True, format="json",
                                 runner=self._all_up_to_date_runner(writes))
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        for key in ("up_to_date", "create_needed", "update_needed"):
            self.assertIn(key, data)
        self.assertEqual(data["create_needed"], [])
        self.assertEqual(data["update_needed"], [])
        self.assertEqual(writes, [], "dry run must not issue any write commands")

    # --- Drifted bodies: the case sync exists to detect ---
    #
    # The up-to-date cases above only prove the happy path. These prove the
    # interesting one: a remote body that no longer matches the local source must
    # land in update_needed (and be reported), and a dry run must still not write.

    def test_sync_reports_drifted_body_as_update_needed(self):
        writes = []
        drifted_id = fvi._extract_vuln_id(fvi.ISSUES[0]["title"])

        def drift(vid, body):
            if vid == drifted_id:
                return body + "\n\n<!-- edited on the remote -->"
            return body

        buf = io.StringIO()
        with redirect_stderr(io.StringIO()), redirect_stdout(buf):
            rc = fvi.sync_issues(dry_run=True, format="json",
                                 runner=self._fake_issue_list(writes, body_transform=drift))

        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(len(data["update_needed"]), 1,
                         f"expected exactly one drifted issue, got {data['update_needed']}")
        self.assertEqual(len(data["create_needed"]), 0)
        self.assertNotIn(drifted_id, data["up_to_date"])
        self.assertEqual(writes, [], "dry run must not issue any write commands")

    def test_sync_dry_run_does_not_write_a_drifted_issue(self):
        """A drift must still produce no write when running as a dry run.

        Guards the `if not dry_run:` guard on the UPDATE branch specifically. The
        json-format tests assert on the plan and never enter the write loop, so
        removing that guard would otherwise go unnoticed.
        """
        writes = []
        drifted_id = fvi._extract_vuln_id(fvi.ISSUES[0]["title"])

        def drift(vid, body):
            if vid == drifted_id:
                return body + "\n\n<!-- edited on the remote -->"
            return body

        err = io.StringIO()
        with redirect_stderr(err):
            rc = fvi.sync_issues(dry_run=True, format="summary",
                                 runner=self._fake_issue_list(writes, body_transform=drift))

        self.assertEqual(rc, 0)
        out = err.getvalue()
        # The drift must be reported...
        self.assertIn(f"UPDATE {drifted_id}", out)
        # ...and no write command may be issued.
        self.assertEqual(writes, [], "dry run must not issue any write commands")
        self.assertFalse(any("issue" in c and "edit" in c for c in writes))

    def test_sync_diff_format_reports_the_drift(self):
        writes = []
        drifted_id = fvi._extract_vuln_id(fvi.ISSUES[0]["title"])

        def drift(vid, body):
            if vid == drifted_id:
                return body + "\n\n<!-- edited on the remote -->"
            return body

        # Progress goes to stderr; the diff itself is written to stdout.
        err = io.StringIO()
        out_buf = io.StringIO()
        with redirect_stderr(err), redirect_stdout(out_buf):
            rc = fvi.sync_issues(dry_run=True, format="diff",
                                 runner=self._fake_issue_list(writes, body_transform=drift))

        self.assertEqual(rc, 0)
        self.assertIn(f"UPDATE {drifted_id}", err.getvalue())
        diff_out = out_buf.getvalue()
        self.assertIn("edited on the remote", diff_out,
                      "diff must show the changed line, not just announce a change")
        self.assertEqual(writes, [], "dry run must not issue any write commands")

    def test_sync_ignores_trailing_whitespace_only_change(self):
        """Trailing whitespace on a line is stripped, so it is not drift.

        _body_diff strips trailing whitespace per line to absorb CRLF/LF and
        reformatting differences. Appending a whole extra line would be real
        drift, so this pads an existing line instead.
        """
        writes = []
        drifted_id = fvi._extract_vuln_id(fvi.ISSUES[0]["title"])

        def drift(vid, body):
            if vid != drifted_id:
                return body
            lines = body.rstrip("\n").split("\n")
            lines[-1] = lines[-1] + "    "
            return "\n".join(lines) + "\n"

        buf = io.StringIO()
        with redirect_stderr(io.StringIO()), redirect_stdout(buf):
            rc = fvi.sync_issues(dry_run=True, format="json",
                                 runner=self._fake_issue_list(writes, body_transform=drift))

        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["update_needed"], [],
                         "a trailing-whitespace-only change must not be treated as drift")
    def test_sync_format_unknown_exits_nonzero(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "file_vuln_issues.py"),
             "--sync", "--format", "toml"],
            capture_output=True, encoding="utf-8", errors="replace", timeout=10,
        )
        self.assertNotEqual(proc.returncode, 0)

    def test_body_diff_produces_unified_diff(self):
        import file_vuln_issues as fvi
        diff = fvi._body_diff(
            "line 1\nline 2\nline 3",
            "line 1\nline CHANGED\nline 3",
            local_label="local", remote_label="remote",
        )
        self.assertIn("--- remote", diff)
        self.assertIn("+++ local", diff)
        self.assertIn("-line CHANGED", diff)
        self.assertIn("+line 2", diff)

    def test_body_diff_empty_when_identical(self):
        import file_vuln_issues as fvi
        diff = fvi._body_diff("hello\nworld", "hello\nworld")
        self.assertEqual(diff, "")

    def test_body_diff_crlf_ignored(self):
        import file_vuln_issues as fvi
        diff = fvi._body_diff("hello\r\nworld", "hello\nworld")
        self.assertEqual(diff, "")


class TestUtilsScrub(unittest.TestCase):
    """Direct tests for the shared _utils.scrub_sensitive — critical security helper."""

    def setUp(self):
        from _utils import scrub_sensitive
        self.scrub = scrub_sensitive

    def test_redacts_ghp_token(self):
        out = self.scrub("Error: ghp_AAAABBBBCCCCDDDDEEEEFFFFGGGGHHHH is invalid")
        self.assertNotIn("AAAABBBB", out)
        self.assertIn("***REDACTED***", out)

    def test_redacts_gho_oauth_token(self):
        out = self.scrub("Bearer gho_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        self.assertNotIn("gho_", out)
        self.assertIn("***REDACTED***", out)

    def test_redacts_ghs_server_to_server(self):
        out = self.scrub("token=ghs_yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy")
        self.assertNotIn("ghs_", out)
        self.assertIn("***REDACTED***", out)

    def test_redacts_github_pat(self):
        out = self.scrub("github_pat_11ABCDEFG0_xyz123xyz123xyz123xyz123xyz123")
        self.assertNotIn("github_pat_", out)
        self.assertIn("***REDACTED***", out)

    def test_passes_through_normal_text(self):
        text = "gh: command not found"
        self.assertEqual(self.scrub(text), text)

    def test_passes_through_paths_and_urls(self):
        text = "https://github.com/neohiro/achievement-hacks/issues/1"
        self.assertEqual(self.scrub(text), text)

    def test_redacts_multiple_tokens_in_one_string(self):
        out = self.scrub("ghp_AAA gho_BBB ghs_CCC github_pat_DDD")
        for token in ("ghp_", "gho_", "ghs_", "github_pat_"):
            self.assertNotIn(token, out)
        self.assertEqual(out.count("***REDACTED***"), 4)


class TestTempfileCleanup(unittest.TestCase):
    """Verify tempfile is removed even when runner raises."""

    def test_update_path_cleans_up_on_runner_exception(self):
        """Verify that if runner() raises after tempfile is created, the file
        is still removed (no temp file leak).

        Also verifies that the exception propagates — it is NOT swallowed by
        sync_issues, since the caller is responsible for error handling.
        """
        import os
        import tempfile

        import file_vuln_issues as fvi

        captured_tmp: list[str] = []
        orig_named = tempfile.NamedTemporaryFile

        class _CapturingTempFile:
            def __init__(self, *a, **kw):
                self._delegate = orig_named(*a, **kw)
                captured_tmp.append(self._delegate.name)
            def __enter__(self):
                return self._delegate.__enter__()
            def __exit__(self, *a):
                return self._delegate.__exit__(*a)
            def write(self, data):
                return self._delegate.write(data)

        def failing_runner(cmd):
            raise RuntimeError("simulated network failure after tempfile created")

        def fake_fetch(runner=None):
            return {"VULN-001": {"number": 1, "title": "[VULN-001] Test",
                                  "body": "different body"}}

        with unittest.mock.patch.object(tempfile, "NamedTemporaryFile", _CapturingTempFile):
            with unittest.mock.patch.object(fvi, "_fetch_existing_issues", fake_fetch):
                with self.assertRaises(RuntimeError):
                    fvi.sync_issues(dry_run=False, runner=failing_runner)

        self.assertEqual(len(captured_tmp), 1, "expected exactly one tempfile")
        self.assertFalse(os.path.exists(captured_tmp[0]),
                         "tempfile was NOT cleaned up — LEAK")


if __name__ == "__main__":
    unittest.main(verbosity=2)

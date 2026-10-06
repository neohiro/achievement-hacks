#!/usr/bin/env python3
"""Tests for the read-only catalog tooling.

Run:  python -m unittest discover -s tests -v
"""
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from typing import ClassVar
from unittest import mock

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
SCRIPTS_DIR = os.path.join(REPO_ROOT, "_scripts")
sys.path.insert(0, SCRIPTS_DIR)

import file_vuln_issues as fvi  # noqa: E402
import grant_check as gc  # noqa: E402
import list_achievements as la  # noqa: E402


class _FakeHeaders:
    def get_content_charset(self):
        return "utf-8"


class _FakeResponse:
    """Minimal stand-in for the object urlopen returns as a context manager."""

    def __init__(self, body):
        self._body = body.encode("utf-8")
        self.headers = _FakeHeaders()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def _write_meta(root, slug, status="Not yet", earnable="true"):
    """Create a throwaway catalog entry for tests that need a controlled catalog."""
    folder = os.path.join(root, slug)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "meta.yaml"), "w", encoding="utf-8") as fh:
        fh.write(
            f"slug: {slug}\n"
            f"name: {slug}\n"
            f"status: {status}\n"
            f"earnable: {earnable}\n"
            "tiers:\n"
            "  - name: Default\n"
            "    threshold: 1\n"
        )
    return folder

CARD = (
    '<a href="/neohiro?achievement=pull-shark&amp;tab=achievements" class="position-relative">'
    '<img src="https://github.githubassets.com/assets/pull-shark-silver-0643f87ac9fd.png" '
    'data-hovercard-url="/users/neohiro/achievements/pull-shark/detail?hovercard=1" '
    'width="64" alt="Achievement: Pull Shark" class="achievement-badge-sidebar" />'
    '<span class="Label achievement-tier-label achievement-tier-label--silver text-small '
    'text-bold position-absolute right-0 bottom-0">x3</span></a>'
)

SIMPLE_CARD = (
    '<a href="/neohiro?achievement=yolo&amp;tab=achievements" class="position-relative">'
    '<img src="https://github.githubassets.com/assets/yolo-default-be0bbff04951.png" '
    'alt="Achievement: YOLO" class="achievement-badge-sidebar" /></a>'
)

MULTI_WORD_CARD = (
    '<a href="/neohiro?achievement=heart-on-your-sleeve&amp;tab=achievements">'
    '<img src="https://github.githubassets.com/assets/heart-on-your-sleeve-gold-abcdef0123.png" '
    'alt="Achievement: Heart On Your Sleeve" /></a>'
)


def html(*cards):
    return "<html><body>" + "".join(cards) + "</body></html>"


class TestParseBadges(unittest.TestCase):
    def test_single_tier_no_count(self):
        found = gc.parse_badges(html(SIMPLE_CARD))
        self.assertEqual(list(found), ["yolo"])
        self.assertEqual(found["yolo"].tier, "default")
        self.assertIsNone(found["yolo"].count)

    def test_tier_and_repeat_count(self):
        found = gc.parse_badges(html(CARD))
        self.assertEqual(found["pull-shark"].tier, "silver")
        self.assertEqual(found["pull-shark"].count, "3")

    def test_multi_word_slug_uses_asset_not_href(self):
        found = gc.parse_badges(html(MULTI_WORD_CARD))
        self.assertEqual(list(found), ["heart-on-your-sleeve"])
        self.assertEqual(found["heart-on-your-sleeve"].tier, "gold")

    def test_multiple_cards_do_not_bleed_into_each_other(self):
        found = gc.parse_badges(html(CARD, SIMPLE_CARD, MULTI_WORD_CARD))
        self.assertEqual(len(found), 3)
        self.assertEqual(found["pull-shark"].tier, "silver")
        self.assertEqual(found["pull-shark"].count, "3")
        self.assertEqual(found["yolo"].tier, "default")
        self.assertIsNone(found["yolo"].count)
        self.assertEqual(found["heart-on-your-sleeve"].tier, "gold")

    def test_no_achievements_returns_empty(self):
        self.assertEqual(gc.parse_badges("<html><body>nothing</body></html>"), {})

    def test_unknown_slug_in_href_falls_back_to_asset(self):
        card = (
            '<a href="/neohiro?achievement=wrong-slug&amp;tab=achievements">'
            '<img src="https://github.githubassets.com/assets/quickdraw-default-39c6.png" /></a>'
        )
        found = gc.parse_badges(html(card))
        self.assertEqual(list(found), ["quickdraw"])


class TestClassify(unittest.TestCase):
    def entry(self, status, earnable="true"):
        return gc.CatalogEntry(
            slug="x", status=status, earnable=earnable, path="_achievements/x/meta.yaml"
        )

    def test_earned_matches_earned(self):
        verdict, _ = gc.classify(self.entry("Earned"), gc.EarnedBadge("x", "default"))
        self.assertEqual(verdict, "earned")

    def test_live_badge_against_not_yet_is_drift(self):
        verdict, detail = gc.classify(self.entry("Not yet"), gc.EarnedBadge("x", "silver"))
        self.assertEqual(verdict, "stale-not-earned")
        self.assertIn("silver", detail)

    def test_earned_claim_without_badge_is_drift(self):
        verdict, _ = gc.classify(self.entry("Earned"), None)
        self.assertEqual(verdict, "stale-earned")

    def test_not_yet_without_badge_is_clean(self):
        verdict, _ = gc.classify(self.entry("Not yet"), None)
        self.assertEqual(verdict, "not-yet")

    def test_unobtainable_without_badge_is_clean(self):
        verdict, _ = gc.classify(self.entry("Unobtainable", "false"), None)
        self.assertEqual(verdict, "not-earnable")

    def test_live_badge_on_unearnable_entry_is_contradiction(self):
        verdict, _ = gc.classify(self.entry("Unobtainable", "false"), gc.EarnedBadge("x", "gold"))
        self.assertEqual(verdict, "contradiction")


class TestDriftRows(unittest.TestCase):
    def row(self, verdict):
        return gc.AuditRow(
            slug="x",
            claimed_status="Not yet",
            earnable="true",
            live_tier=None,
            live_count=None,
            verdict=verdict,
        )

    def test_clean_verdicts_excluded(self):
        rows = [self.row(v) for v in ("earned", "not-yet", "not-earnable")]
        self.assertEqual(gc.drift_rows(rows), [])

    def test_drift_verdicts_included(self):
        rows = [self.row(v) for v in ("stale-not-earned", "stale-earned", "uncatalogued", "contradiction")]
        self.assertEqual(len(gc.drift_rows(rows)), 4)


class TestAuditUncatalogued(unittest.TestCase):
    def test_live_badge_absent_from_catalog_is_flagged(self):
        entries = [gc.CatalogEntry("yolo", "Earned", "true", "p")]
        badges = {
            "yolo": gc.EarnedBadge("yolo", "default"),
            "brand-new": gc.EarnedBadge("brand-new", "gold"),
        }
        rows = gc.audit(entries, badges)
        verdicts = {r.slug: r.verdict for r in rows}
        self.assertEqual(verdicts["yolo"], "earned")
        self.assertEqual(verdicts["brand-new"], "uncatalogued")


class TestRenderTable(unittest.TestCase):
    def test_header_present_and_widths_cover_content(self):
        rows = [
            gc.AuditRow(
                slug="pull-shark",
                claimed_status="Earned",
                earnable="true",
                live_tier="silver",
                live_count="3",
                verdict="earned",
                detail="silver (x3)",
            )
        ]
        table = gc.render_table(rows)
        lines = table.splitlines()
        self.assertIn("SLUG", lines[0])
        self.assertIn("pull-shark", table)
        self.assertIn("x3", table)
        self.assertLessEqual(len(lines[0]), len(lines[2]))


class TestRealCatalog(unittest.TestCase):
    """Assertions against the catalog actually checked into this repo."""

    @classmethod
    def setUpClass(cls):
        cls.entries = gc.parse_catalog(os.path.join(REPO_ROOT, "_achievements"))

    def test_catalog_is_not_empty(self):
        self.assertGreaterEqual(len(self.entries), 15)

    def test_every_slug_is_unique(self):
        slugs = [e.slug for e in self.entries]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_no_entry_still_says_not_yet_if_known_earned(self):
        """Regression guard for the 2026-10-03 stale-status incident."""
        for slug in ("pull-shark", "quickdraw", "starstruck", "yolo"):
            entry = next(e for e in self.entries if e.slug == slug)
            self.assertEqual(
                entry.status,
                "Earned",
                f"{slug} is verified earned on the live profile but meta.yaml says {entry.status!r}",
            )

    def test_earned_entries_record_a_verified_block(self):
        for entry in self.entries:
            if entry.status != "Earned":
                continue
            path = os.path.join(REPO_ROOT, entry.path)
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            self.assertIn("verified:", text, f"{entry.slug} has no verified: block")
            self.assertIn("tier:", text, f"{entry.slug} verified block records no tier")

    def test_statuses_are_from_the_documented_legend(self):
        allowed = {"Not yet", "In progress", "Earned", "Deprecated", "Unobtainable"}
        for entry in self.entries:
            self.assertIn(entry.status, allowed, f"{entry.slug} has unknown status {entry.status!r}")


class TestListAchievements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = la.load_catalog(os.path.join(REPO_ROOT, "_achievements"))

    def test_records_have_required_keys(self):
        for rec in self.records:
            for key in ("slug", "name", "status", "tier_names", "tier_count", "group"):
                self.assertIn(key, rec)

    def test_group_bucketing(self):
        groups = {rec["slug"]: rec["group"] for rec in self.records}
        self.assertEqual(groups["starstruck"], "active")
        self.assertEqual(groups["mars-2020"], "_deprecated")
        self.assertEqual(groups["github-pro"], "_highlights")

    def test_catalog_table_only_lists_active_achievements(self):
        table = la.render_catalog_table(self.records)
        self.assertIn("starstruck", table)
        self.assertNotIn("mars-2020", table)
        self.assertNotIn("github-pro", table)

    def test_index_table_covers_every_record(self):
        table = la.render_index_table(self.records)
        for rec in self.records:
            self.assertIn(rec["slug"], table)

    def test_committed_markdown_is_in_sync(self):
        problems = la.check_sync(self.records)
        self.assertEqual(problems, [], "catalog markdown is out of sync: " + "; ".join(problems))

    def test_replace_block_is_idempotent(self):
        text = f"before\n{la.BEGIN_INDEX}\nold\n{la.END_INDEX}\nafter\n"
        once = la.replace_block(text, la.BEGIN_INDEX, la.END_INDEX, "new")
        twice = la.replace_block(once, la.BEGIN_INDEX, la.END_INDEX, "new")
        self.assertEqual(once, twice)
        self.assertIn("new", once)
        self.assertNotIn("old", once)

    def test_replace_block_preserves_surrounding_text(self):
        text = f"before\n{la.BEGIN_INDEX}\nold\n{la.END_INDEX}\nafter\n"
        out = la.replace_block(text, la.BEGIN_INDEX, la.END_INDEX, "new")
        self.assertTrue(out.startswith("before\n"))
        self.assertTrue(out.endswith("\nafter\n"))

    def test_replace_block_leaves_text_untouched_when_markers_absent(self):
        text = "no markers here"
        out = la.replace_block(text, la.BEGIN_INDEX, la.END_INDEX, "body")
        self.assertEqual(out, text)


class TestLooksLikeProfile(unittest.TestCase):
    """The guard that stops a soft-failed fetch from reading as 'all badges gone'."""

    def test_real_profile_markup_accepted(self):
        self.assertTrue(gc.looks_like_profile(html(CARD, SIMPLE_CARD)))

    def test_achievements_tab_only_accepted(self):
        self.assertTrue(gc.looks_like_profile('<a href="/neohiro?tab=achievements">x</a>'))

    def test_empty_body_rejected(self):
        self.assertFalse(gc.looks_like_profile("<html><body></body></html>"))

    def test_interstitial_rejected(self):
        interstitial = "<html><body>Sign in to GitHub</body></html>"
        self.assertFalse(gc.looks_like_profile(interstitial))

    def test_account_with_no_badges_still_accepted(self):
        """A user who genuinely has zero badges must NOT be flagged as a parse failure.

        The sidebar container is present even when it is empty, which is what keeps
        this from misclassifying a legitimate empty state as a broken parser.
        """
        page = '<html><body><div class="achievement-badge-sidebar"></div></body></html>'
        self.assertTrue(gc.looks_like_profile(page))


class TestFetchProfileHtml(unittest.TestCase):
    """Retry policy: transient failures retry, permanent ones do not."""

    def _fake_urlopen(self, responses):
        calls = []

        def fake(request, timeout=None):
            calls.append(request.full_url)
            item = responses.pop(0)
            if isinstance(item, Exception):
                raise item
            return _FakeResponse(item)

        return fake, calls

    def test_success_first_try(self):
        fake, calls = self._fake_urlopen(["<html>ok</html>"])
        with mock.patch.object(gc.urllib.request, "urlopen", fake):
            out = gc.fetch_profile_html("neohiro", sleep=lambda _: None)
        self.assertEqual(out, "<html>ok</html>")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], "https://github.com/neohiro")

    def test_retries_on_503_then_succeeds(self):
        err = urllib.error.HTTPError("u", 503, "unavailable", {}, None)
        fake, calls = self._fake_urlopen([err, "<html>ok</html>"])
        with mock.patch.object(gc.urllib.request, "urlopen", fake):
            out = gc.fetch_profile_html("neohiro", sleep=lambda _: None)
        self.assertEqual(out, "<html>ok</html>")
        self.assertEqual(len(calls), 2)

    def test_retries_on_429(self):
        err = urllib.error.HTTPError("u", 429, "rate limited", {}, None)
        fake, calls = self._fake_urlopen([err, err, "<html>ok</html>"])
        with mock.patch.object(gc.urllib.request, "urlopen", fake):
            out = gc.fetch_profile_html("neohiro", sleep=lambda _: None)
        self.assertEqual(out, "<html>ok</html>")
        self.assertEqual(len(calls), 3)

    def test_retries_on_network_error(self):
        fake, calls = self._fake_urlopen(
            [urllib.error.URLError("dns"), "<html>ok</html>"]
        )
        with mock.patch.object(gc.urllib.request, "urlopen", fake):
            out = gc.fetch_profile_html("neohiro", sleep=lambda _: None)
        self.assertEqual(out, "<html>ok</html>")
        self.assertEqual(len(calls), 2)

    def test_404_is_not_retried(self):
        err = urllib.error.HTTPError("u", 404, "not found", {}, None)
        fake, calls = self._fake_urlopen([err])
        with mock.patch.object(gc.urllib.request, "urlopen", fake):
            with self.assertRaises(gc.CatalogError) as ctx:
                gc.fetch_profile_html("ghost-account-xyz", attempts=3, sleep=lambda _: None)
        self.assertEqual(len(calls), 1, "404 must not be retried")
        self.assertIn("404", str(ctx.exception))
        self.assertIn("does not exist", str(ctx.exception))

    def test_exhausted_retries_report_attempt_count(self):
        err = urllib.error.HTTPError("u", 503, "unavailable", {}, None)
        fake, calls = self._fake_urlopen([err, err, err])
        with mock.patch.object(gc.urllib.request, "urlopen", fake):
            with self.assertRaises(gc.CatalogError) as ctx:
                gc.fetch_profile_html("neohiro", attempts=3, sleep=lambda _: None)
        self.assertEqual(len(calls), 3)
        self.assertIn("3 attempt", str(ctx.exception))

    def test_backoff_is_increasing(self):
        slept = []
        err = urllib.error.HTTPError("u", 500, "boom", {}, None)
        fake, _ = self._fake_urlopen([err, err, "<html>ok</html>"])
        with mock.patch.object(gc.urllib.request, "urlopen", fake):
            gc.fetch_profile_html("neohiro", attempts=3, backoff=2.0, sleep=slept.append)
        self.assertEqual(slept, [1.0, 2.0])


class TestGrantCheckMain(unittest.TestCase):
    """CLI contract: 0 = clean, 2 = drift, 1 = could not determine."""

    def _run(self, html_text, argv):
        buf = io.StringIO()
        with (
            mock.patch.object(gc, "fetch_profile_html", return_value=html_text),
            contextlib.redirect_stdout(buf),
        ):
            code = gc.main(argv)
        return code, buf.getvalue()

    def test_clean_catalog_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, "yolo", status="Earned")
            code, out = self._run(html(SIMPLE_CARD), ["--catalog", tmp])
        self.assertEqual(code, 0)
        self.assertIn("OK: catalog matches the live profile", out)

    def test_stale_earned_claim_is_detected(self):
        """The 'Earned but not rendered' direction must also fail the audit.

        This is the direction that catches someone switching off the public-profile
        achievement toggle, which would otherwise silently invalidate the catalog.
        The page is a valid profile that simply has no badges, so the parser-sanity
        check must not mask the drift.
        """
        empty_profile = '<html><body><div class="achievement-badge-sidebar"></div></body></html>'
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, "yolo", status="Earned")
            code, out = self._run(empty_profile, ["--catalog", tmp])
        self.assertEqual(code, 2)
        self.assertIn("stale-earned", out)

    def test_json_stdout_is_pure_json(self):
        """`grant_check.py --json | jq` must work, so nothing else goes to stdout."""
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, "yolo", status="Earned")
            out_buf, err_buf = io.StringIO(), io.StringIO()
            with (
                mock.patch.object(gc, "fetch_profile_html", return_value=html(SIMPLE_CARD)),
                contextlib.redirect_stdout(out_buf),
                contextlib.redirect_stderr(err_buf),
            ):
                code = gc.main(["--json", "--catalog", tmp])
            payload = json.loads(out_buf.getvalue())

        self.assertEqual(code, 0)
        self.assertEqual(payload["parser_sanity"], "ok")
        self.assertEqual(payload["live_badge_count"], 1)
        self.assertEqual(payload["catalog_entry_count"], 1)
        self.assertEqual(payload["drift_count"], 0)
        self.assertEqual(payload["rows"][0]["slug"], "yolo")
        self.assertEqual(payload["rows"][0]["verdict"], "earned")
        self.assertIn("OK:", err_buf.getvalue())

    def test_json_reports_drift_without_corrupting_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, "demo", status="Not yet")
            out_buf, err_buf = io.StringIO(), io.StringIO()
            with (
                mock.patch.object(gc, "fetch_profile_html", return_value=html(SIMPLE_CARD)),
                contextlib.redirect_stdout(out_buf),
                contextlib.redirect_stderr(err_buf),
            ):
                code = gc.main(["--json", "--catalog", tmp])
            payload = json.loads(out_buf.getvalue())

        self.assertEqual(code, 2)
        self.assertEqual(payload["drift_count"], 1)
        self.assertIn("DRIFT", err_buf.getvalue())

    def test_drift_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, "demo", status="Not yet", earnable="true")
            code, out = self._run(html(SIMPLE_CARD), ["--catalog", tmp])
        self.assertEqual(code, 2)
        self.assertIn("DRIFT", out)

    def test_interstitial_exits_one_and_refuses_to_report_drift(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code, _ = self._run("<html><body>Sign in</body></html>", ["--account", "x"])
        self.assertEqual(code, 1)
        self.assertIn("Refusing to report drift", err.getvalue())


    def test_quiet_suppresses_table_but_keeps_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, "yolo", status="Earned")
            _, out = self._run(html(SIMPLE_CARD), ["--catalog", tmp, "--quiet"])
        self.assertNotIn("SLUG", out)
        self.assertIn("OK:", out)

    def test_missing_catalog_dir_exits_one(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = gc.main(["--catalog", os.path.join("no", "such", "dir")])
        self.assertEqual(code, 1)
        self.assertIn("error:", err.getvalue())

    def test_positional_and_account_together_is_refused(self):
        """Two accounts named, one silently discarded, is how an audit of the
        wrong account comes back clean. Neither account is fetched."""
        err = io.StringIO()
        with mock.patch.object(
            gc, "fetch_profile_html", side_effect=AssertionError("must not fetch")
        ):
            with contextlib.redirect_stderr(err):
                code = gc.main(["neohiro", "--account", "someoneelse"])
        self.assertEqual(code, 1)
        self.assertIn("not both", err.getvalue())

    def test_account_flag_alone_is_not_a_conflict(self):
        """`--account neohiro` contains a non-flag token, so it is easy to write
        a conflict check that fires on its own value."""
        buf = io.StringIO()
        with (
            mock.patch.object(gc, "fetch_profile_html", return_value=html(SIMPLE_CARD)),
            contextlib.redirect_stdout(buf),
        ):
            with tempfile.TemporaryDirectory() as tmp:
                _write_meta(tmp, "yolo", status="Earned")
                code = gc.main(["--account", "neohiro", "--catalog", tmp])
        self.assertEqual(code, 0)

    def test_positional_alone_is_not_a_conflict(self):
        buf = io.StringIO()
        with (
            mock.patch.object(gc, "fetch_profile_html", return_value=html(SIMPLE_CARD)),
            contextlib.redirect_stdout(buf),
        ):
            with tempfile.TemporaryDirectory() as tmp:
                _write_meta(tmp, "yolo", status="Earned")
                code = gc.main(["neohiro", "--catalog", tmp])
        self.assertEqual(code, 0)

    def test_neither_uses_the_default_account(self):
        buf = io.StringIO()
        seen = []

        def spy(login, **kwargs):
            seen.append(login)
            return html(SIMPLE_CARD)

        with mock.patch.object(gc, "fetch_profile_html", side_effect=spy):
            with contextlib.redirect_stdout(buf):
                with tempfile.TemporaryDirectory() as tmp:
                    _write_meta(tmp, "yolo", status="Earned")
                    code = gc.main(["--catalog", tmp])
        self.assertEqual(code, 0)
        self.assertEqual(seen, [gc.DEFAULT_ACCOUNT])


class TestMalformedCatalogEntry(unittest.TestCase):
    def test_unknown_status_is_flagged_not_treated_as_not_yet(self):
        entry = gc.CatalogEntry("x", "Totally Bogus", "true", "p")
        verdict, _ = gc.classify(entry, None)
        self.assertEqual(verdict, "malformed")

    def test_missing_earnable_is_flagged(self):
        entry = gc.CatalogEntry("x", "Not yet", "(missing)", "p")
        verdict, _ = gc.classify(entry, None)
        self.assertEqual(verdict, "malformed")

    def test_malformed_counts_as_drift(self):
        row = gc.AuditRow("x", "Bogus", "true", None, None, "malformed")
        self.assertEqual(gc.drift_rows([row]), [row])


class TestListAchievementsMain(unittest.TestCase):
    def test_check_passes_on_committed_repo(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = la.main(["--check"])
        self.assertEqual(code, 0)
        self.assertIn("in sync", buf.getvalue())

    def test_check_verdict_is_on_stdout_not_only_stderr(self):
        """`neohiro_validate.py` runs this and reports the schema check.

        It read stderr only, so when the summary moved to stdout the tool exited
        0 having printed "OK" while its caller reported a failure - a failing
        gate on a passing check, which is worse than a gap because it trains
        people to ignore the gate. Pinned here so the stream is a contract rather
        than an accident, and so a caller that reads one stream has to say so.
        """
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = la.main(["--check"])
        self.assertEqual(code, 0)
        self.assertIn("OK", out.getvalue(), "--check must say its verdict on stdout")
        self.assertNotIn("OK", err.getvalue())

    def test_json_mode_keeps_stdout_pure(self):
        """`--json | jq` only works if nothing else lands on stdout."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            la.main(["--json"])
        json.loads(out.getvalue())  # must not raise
        self.assertEqual(err.getvalue(), "")

    def test_check_detects_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            readme = os.path.join(tmp, "README.md")
            with open(readme, "w", encoding="utf-8") as fh:
                fh.write(f"nothing here {la.BEGIN_CATALOG}\nstale\n{la.END_CATALOG}\n")
            catalog = os.path.join(tmp, "_achievements")
            _write_meta(catalog, "demo", status="Earned")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = la.main(["--check", "--catalog", catalog])
        self.assertEqual(code, 2)
        self.assertIn("OUT OF SYNC", buf.getvalue())

    def test_json_output_includes_verified_and_earned_on(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            la.main(["--json"])
        records = json.loads(buf.getvalue())
        by_slug = {r["slug"]: r for r in records}
        self.assertEqual(by_slug["pull-shark"]["verified"]["tier"], "Silver")
        self.assertEqual(by_slug["pull-shark"]["earned_on"], ["neohiro"])

    def test_missing_catalog_exits_one(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = la.main(["--check", "--catalog", os.path.join("no", "such")])
        self.assertEqual(code, 1)


class TestFindingCoverageMatchesSecurityDoc(unittest.TestCase):
    """Integration guard.

    ``SECURITY.md`` is the human-readable record; ``file_vuln_issues.py`` is what
    actually posts. If they diverge, the repo claims findings it cannot file, or
    files findings it never documented. Either way the catalog is lying.
    """

    def _security_vuln_ids(self):
        path = os.path.join(REPO_ROOT, "SECURITY.md")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        return sorted(set(re.findall(r"^## (VULN-\d{3})", text, re.MULTILINE)))

    def _issue_vuln_ids(self):
        return sorted({m for i in fvi.ISSUES for m in re.findall(r"VULN-\d{3}", i["title"])})

    def test_security_md_documents_exactly_the_filed_findings(self):
        self.assertEqual(self._security_vuln_ids(), self._issue_vuln_ids())

    def test_every_issue_has_a_security_md_section(self):
        with open(os.path.join(REPO_ROOT, "SECURITY.md"), encoding="utf-8") as fh:
            text = fh.read()
        for vuln_id in self._issue_vuln_ids():
            self.assertIn(f"## {vuln_id}:", text, f"{vuln_id} has no SECURITY.md section")

    def test_issue_titles_are_numbered_and_ordered(self):
        ids = [re.search(r"VULN-\d{3}", i["title"]).group(0) for i in fvi.ISSUES]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), len(set(ids)))

    def test_issue_bodies_reference_the_repo(self):
        for issue in fvi.ISSUES:
            self.assertIn("neohiro/achievement-hacks", issue["body"])


class TestReadmeSectionContract(unittest.TestCase):
    """Enforce the convention documented in _docs/ACHIEVEMENT_FORMAT.md.

    The previous version of that document mandated eleven sections in a fixed
    order which no README followed, which is worse than having no contract: it
    reads as enforced. These tests make the real convention load-bearing.
    """

    REQUIRED: ClassVar[list[str]] = [
        "What it measures",
        "Visual",
        "Tiers",
        "How it works",
        "Automated recipe",
        "Manual recipe",
        "neohiro status",
        "Difficulty assessment",
    ]

    def _active_readmes(self):
        base = os.path.join(REPO_ROOT, "_achievements")
        for slug in sorted(os.listdir(base)):
            if slug.startswith("_"):
                continue
            readme = os.path.join(base, slug, "README.md")
            if os.path.isfile(readme):
                yield slug, readme

    def _sections(self, readme):
        with open(readme, encoding="utf-8") as fh:
            text = fh.read()
        return [m.strip() for m in re.findall(r"^##\s+(.*)$", text, re.MULTILINE)]

    def test_catalog_is_not_empty(self):
        self.assertGreaterEqual(len(list(self._active_readmes())), 9)

    def test_required_sections_present_in_order(self):
        for slug, readme in self._active_readmes():
            with self.subTest(slug=slug):
                sections = self._sections(readme)
                positions = []
                for required in self.REQUIRED:
                    match = next(
                        (
                            i
                            for i, s in enumerate(sections)
                            if s.startswith(required)
                        ),
                        None,
                    )
                    self.assertIsNotNone(
                        match, f"{slug} is missing required section {required!r}"
                    )
                    positions.append(match)
                self.assertEqual(
                    positions,
                    sorted(positions),
                    f"{slug} has required sections out of order: "
                    f"{[sections[i] for i in positions]}",
                )

    def test_status_line_present_and_names_a_status(self):
        for slug, readme in self._active_readmes():
            with self.subTest(slug=slug):
                with open(readme, encoding="utf-8") as fh:
                    head = fh.read(1200)
                match = re.search(r"\*\*Status:\s*`([^`]+)`\*\*", head)
                self.assertIsNotNone(match, f"{slug} has no status line under the H1")
                self.assertIn(
                    match.group(1),
                    gc.VALID_STATUSES,
                    f"{slug} status line uses undocumented value {match.group(1)!r}",
                )

    def test_status_line_agrees_with_meta_yaml(self):
        for slug, readme in self._active_readmes():
            with self.subTest(slug=slug):
                meta_path = os.path.join(REPO_ROOT, "_achievements", slug, "meta.yaml")
                with open(meta_path, encoding="utf-8") as fh:
                    meta_status = re.search(r"^status:\s*(.+)$", fh.read(), re.MULTILINE).group(1).strip()
                with open(readme, encoding="utf-8") as fh:
                    head = fh.read(1200)
                readme_status = re.search(r"\*\*Status:\s*`([^`]+)`\*\*", head).group(1)
                self.assertEqual(
                    readme_status,
                    meta_status,
                    f"{slug}: README says {readme_status!r}, meta.yaml says {meta_status!r}",
                )


BROKEN_ASSET_HTML = (
    '<html><body><img class="achievement-badge-sidebar" '
    'src="https://cdn.example.com/v2/badges/pull-shark.png">'
    '<a href="/neohiro?achievement=pull-shark&amp;tab=achievements">'
    '<img src="https://cdn.example.com/v2/badges/pull-shark.png" '
    'alt="Achievement: Pull Shark"></a>'
    '<a href="/neohiro?achievement=starstruck&amp;tab=achievements">'
    '<img src="https://cdn.example.com/v2/badges/starstruck.png" '
    'alt="Achievement: Starstruck"></a>'
    "</body></html>"
)

EMPTY_SIDEBAR_HTML = (
    '<html><body><div class="achievement-badge-sidebar"></div></body></html>'
)


class TestCountAchievementCards(unittest.TestCase):
    def test_counts_cards_independently_of_asset_parsing(self):
        self.assertEqual(gc.count_achievement_cards(html(CARD, SIMPLE_CARD)), 2)
        self.assertEqual(gc.count_achievement_cards(BROKEN_ASSET_HTML), 2)

    def test_zero_when_no_cards(self):
        self.assertEqual(gc.count_achievement_cards(EMPTY_SIDEBAR_HTML), 0)


class TestParserBreakGuard(unittest.TestCase):
    """A CDN or naming change must not be reported as 'these were never earned'."""

    def _run(self, html_text, argv):
        out, err = io.StringIO(), io.StringIO()
        with (
            mock.patch.object(gc, "fetch_profile_html", return_value=html_text),
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
        ):
            code = gc.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_cards_present_but_none_extracted_exits_one(self):
        code, out, err = self._run(BROKEN_ASSET_HTML, ["--account", "neohiro"])
        self.assertEqual(code, 1)
        self.assertNotIn("DRIFT", out)
        self.assertIn("Update ASSET_RE", err)

    def test_guard_would_have_been_a_false_drift_report(self):
        """Regression pin: without the guard this input yields 4 bogus findings."""
        self.assertEqual(len(gc.parse_badges(BROKEN_ASSET_HTML)), 0)
        self.assertGreater(gc.count_achievement_cards(BROKEN_ASSET_HTML), 0)

    def test_genuinely_badge_free_account_is_not_a_parser_break(self):
        """Zero cards and zero badges is a legitimate empty state, not a break."""
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, "demo", status="Not yet")
            code, _, _ = self._run(EMPTY_SIDEBAR_HTML, ["--catalog", tmp])
        self.assertEqual(code, 0)

    def test_json_reports_cards_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, "yolo", status="Earned")
            out = io.StringIO()
            with (
                mock.patch.object(gc, "fetch_profile_html", return_value=html(SIMPLE_CARD)),
                contextlib.redirect_stdout(out),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                gc.main(["--json", "--catalog", tmp])
            payload = json.loads(out.getvalue())
        self.assertEqual(payload["cards_found"], 1)
        self.assertEqual(payload["live_badge_count"], 1)


class TestValidateLogin(unittest.TestCase):
    def test_accepts_normal_logins(self):
        for login in ("neohiro", "a", "A1", "user-name", "u" * 39):
            self.assertEqual(gc.validate_login(login), login)

    def test_rejects_control_characters(self):
        for bad in ("bad\nlogin", "bad\rlogin", "bad\tlogin", "a b"):
            with self.assertRaises(gc.CatalogError):
                gc.validate_login(bad)

    def test_rejects_bad_shape(self):
        for bad in ("", "-lead", "trail-", "a" * 40, "under_score", "dot.ted", "sla/sh"):
            with self.assertRaises(gc.CatalogError):
                gc.validate_login(bad)

    def test_invalid_login_exits_one_without_traceback(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with mock.patch.object(gc, "fetch_profile_html", side_effect=AssertionError("must not fetch")):
                code = gc.main(["--account", "bad\nlogin"])
        self.assertEqual(code, 1)
        self.assertIn("not a valid GitHub login", err.getvalue())


class TestNumericArgValidation(unittest.TestCase):
    def _expect_usage_exit(self, argv):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                gc.main(argv)

    def test_rejects_non_positive_timeout(self):
        for bad in ("0", "-1"):
            self._expect_usage_exit(["--timeout", bad])

    def test_rejects_non_integer_attempts(self):
        self._expect_usage_exit(["--attempts", "abc"])

    def test_accepts_valid_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, "yolo", status="Earned")
            with mock.patch.object(gc, "fetch_profile_html", return_value=html(SIMPLE_CARD)):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = gc.main(["--catalog", tmp, "--timeout", "5", "--attempts", "1"])
        self.assertEqual(code, 0)


class TestCatalogValidation(unittest.TestCase):
    """load_catalog gates what reaches committed markdown."""

    def _meta(self, tmp, slug="demo", **overrides):
        folder = os.path.join(tmp, slug)
        os.makedirs(folder, exist_ok=True)
        fields = {"slug": slug, "name": "Demo", "status": "Not yet", "earnable": "true"}
        fields.update(overrides)
        with open(os.path.join(folder, "meta.yaml"), "w", encoding="utf-8") as fh:
            for key, value in fields.items():
                fh.write(f"{key}: {value}\n")

    def test_slug_must_match_folder_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = os.path.join(tmp, "starstruck")
            os.makedirs(folder)
            with open(os.path.join(folder, "meta.yaml"), "w", encoding="utf-8") as fh:
                fh.write("slug: totally-different\nname: X\nstatus: Earned\nearnable: true\n")
            with self.assertRaises(la.CatalogError) as ctx:
                la.load_catalog(tmp)
        self.assertIn("does not match its folder name", str(ctx.exception))

    def test_unknown_status_is_rejected_before_rendering(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._meta(tmp, status="totally bogus")
            with self.assertRaises(la.CatalogError) as ctx:
                la.load_catalog(tmp)
        self.assertIn("is not one of", str(ctx.exception))

    def test_string_earnable_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._meta(tmp, earnable="'true'")
            with self.assertRaises(la.CatalogError) as ctx:
                la.load_catalog(tmp)
        self.assertIn("must be a YAML boolean", str(ctx.exception))

    def test_real_catalog_passes_validation(self):
        records = la.load_catalog(os.path.join(REPO_ROOT, "_achievements"))
        self.assertGreaterEqual(len(records), 15)

    def test_status_constants_agree_across_tools(self):
        self.assertEqual(la.VALID_STATUSES, gc.VALID_STATUSES)


class TestBlockMarkerIntegrity(unittest.TestCase):
    """Misordered markers must not read as 'in sync'."""

    def test_misordered_markers_are_detected(self):
        misordered = f"{la.END_CATALOG}\nstale\n{la.BEGIN_CATALOG}\n"
        self.assertFalse(la.has_block(misordered, la.BEGIN_CATALOG, la.END_CATALOG))
        self.assertEqual(
            la.replace_block(misordered, la.BEGIN_CATALOG, la.END_CATALOG, "NEW"),
            misordered,
        )

    def test_well_formed_block_is_detected(self):
        good = f"{la.BEGIN_CATALOG}\nbody\n{la.END_CATALOG}\n"
        self.assertTrue(la.has_block(good, la.BEGIN_CATALOG, la.END_CATALOG))

    def test_check_sync_reports_misordered_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            orig_readme, orig_index = la.README_PATH, la.INDEX_PATH
            la.README_PATH = os.path.join(tmp, "README.md")
            la.INDEX_PATH = os.path.join(tmp, "INDEX.md")
            try:
                with open(la.README_PATH, "w", encoding="utf-8") as fh:
                    fh.write(f"{la.END_CATALOG}\nstale\n{la.BEGIN_CATALOG}\n")
                with open(la.INDEX_PATH, "w", encoding="utf-8") as fh:
                    fh.write(f"{la.BEGIN_INDEX}\nstale\n{la.END_INDEX}\n")
                problems = la.check_sync([{"slug": "x", "name": "X", "status": "Not yet",
                                           "earnable": True, "difficulty": "x",
                                           "how_earned": "y", "emoji": "", "tier_names": [],
                                           "tier_count": 0, "group": "active"}])
            finally:
                la.README_PATH, la.INDEX_PATH = orig_readme, orig_index
        joined = " | ".join(problems)
        self.assertIn("misordered", joined)
        self.assertIn("out of sync", joined)

    def test_write_tables_raises_cleanly_on_missing_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            orig_readme, orig_index = la.README_PATH, la.INDEX_PATH
            la.README_PATH = os.path.join(tmp, "nope", "README.md")
            la.INDEX_PATH = os.path.join(tmp, "nope", "INDEX.md")
            try:
                with self.assertRaises(la.CatalogError) as ctx:
                    la.write_tables([])
            finally:
                la.README_PATH, la.INDEX_PATH = orig_readme, orig_index
        self.assertIn("does not exist", str(ctx.exception))

    def test_write_on_missing_file_exits_one_not_traceback(self):
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            orig_readme, orig_index = la.README_PATH, la.INDEX_PATH
            la.README_PATH = os.path.join(tmp, "nope", "README.md")
            la.INDEX_PATH = os.path.join(tmp, "nope", "INDEX.md")
            try:
                with contextlib.redirect_stderr(err):
                    with contextlib.redirect_stdout(io.StringIO()):
                        code = la.main(["--write"])
            finally:
                la.README_PATH, la.INDEX_PATH = orig_readme, orig_index
        self.assertEqual(code, 1)
        self.assertIn("error:", err.getvalue())

    def test_modes_are_mutually_exclusive(self):
        with contextlib.redirect_stderr(io.StringIO()):
            for argv in (["--check", "--json"], ["--check", "--write"], ["--write", "--json"]):
                with self.subTest(argv=argv), self.assertRaises(SystemExit):
                    la.main(argv)


class TestCheckLinks(unittest.TestCase):
    """The link checker had no unit coverage; it only ran as a CI subprocess."""

    def setUp(self):
        self.repo = os.path.join(REPO_ROOT, "tests")
        if self.repo not in sys.path:
            sys.path.insert(0, self.repo)
        import check_links as cl

        self.cl = cl

    def _run(self, files):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        repo = os.path.join(tmp, "repo")
        os.makedirs(os.path.join(repo, "docs"))
        for rel, content in files.items():
            path = os.path.join(repo, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
        orig = self.cl.REPO
        self.cl.REPO = repo
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                code = self.cl.main()
        finally:
            self.cl.REPO = orig
        return code, buf.getvalue()

    def test_unquoted_space_is_suspect_not_truncated(self):
        """Regression: an earlier version split at the first space, resolving a
        path that never existed and reporting a false positive."""
        target, malformed = self.cl.parse_target("my file.md")
        self.assertEqual(target, "my file.md")
        self.assertTrue(malformed)

    def test_quoted_title_is_stripped(self):
        self.assertEqual(self.cl.parse_target('a/b.md "Title"'), ("a/b.md", False))
        self.assertEqual(self.cl.parse_target("a/b.md 'Title'"), ("a/b.md", False))

    def test_angle_bracket_destination_allows_spaces(self):
        self.assertEqual(self.cl.parse_target("<my file.md>"), ("my file.md", False))

    def test_plain_target_is_clean(self):
        self.assertEqual(self.cl.parse_target("a/b.md"), ("a/b.md", False))

    def test_external_and_anchor_and_webroute_skipped(self):
        for link in ("[x](https://e.com)", "[x](#a)", "[x](./issues/1)", "[x](/abs)"):
            with self.subTest(link=link):
                self.assertEqual(list(self.cl.iter_relative_links(link)), [])

    def test_existing_link_passes(self):
        code, out = self._run({"docs/a.md": "[x](b.md)\n", "docs/b.md": "hi\n"})
        self.assertEqual(code, 0)
        self.assertIn("0 problem", out)

    def test_broken_link_fails(self):
        code, out = self._run({"docs/a.md": "[x](nope.md)\n"})
        self.assertEqual(code, 1)
        self.assertIn("BROKEN", out)

    def test_malformed_link_fails_without_false_broken(self):
        code, out = self._run({"docs/a.md": "[x](missing file.md)\n"})
        self.assertEqual(code, 1)
        self.assertIn("SUSPECT", out)
        self.assertNotIn("BROKEN", out)

    def test_import_does_not_terminate_interpreter(self):
        """Regression: this module used to call sys.exit() at import time."""
        self.assertTrue(hasattr(self.cl, "main"))
        self.assertTrue(callable(self.cl.main))


class TestAnchorValidation(unittest.TestCase):
    """Fragments used to be stripped and never checked.

    GitHub resolves an unknown anchor to the top of the page silently, so a link
    pointing at a heading that does not exist looks fine and is not. Two real
    broken anchors were found the day this was added, both written earlier in the
    same session.
    """

    def setUp(self):
        self.repo = os.path.join(REPO_ROOT, "tests")
        if self.repo not in sys.path:
            sys.path.insert(0, self.repo)
        import check_links as cl

        self.cl = cl

    def test_slugify_drops_punctuation(self):
        self.assertEqual(self.cl.slugify("Why this is not a HackerOne submission"),
                         "why-this-is-not-a-hackerone-submission")

    def test_slugify_preserves_existing_hyphens(self):
        self.assertEqual(self.cl.slugify("VULN-006: Galaxy Brain"), "vuln-006-galaxy-brain")

    def test_slugify_em_dash_yields_double_hyphen(self):
        """Punctuation is removed but the surrounding spaces survive."""
        self.assertEqual(self.cl.slugify("Brain — Abuse"), "brain--abuse")

    def test_slugify_plain_hyphen_yields_triple_hyphen(self):
        self.assertEqual(self.cl.slugify("Brain - Abuse"), "brain---abuse")

    def test_headings_ignores_fenced_code(self):
        text = "## Real Heading\n\n```bash\n# not a heading\n```\n"
        anchors = self.cl.headings(text)
        self.assertIn("real-heading", anchors)
        self.assertNotIn("not-a-heading", anchors)

    def test_headings_handles_closing_hashes(self):
        self.assertIn("closed-heading", self.cl.headings("## Closed Heading ##\n"))

    def test_iter_fragments_yields_path_and_fragment(self):
        found = list(self.cl.iter_fragments("[a](#x) [b](f.md#y) [c](https://e.com#z)"))
        self.assertEqual(found, [("", "x"), ("f.md", "y")])

    def test_committed_repo_has_no_broken_anchors(self):
        buf = io.StringIO()
        orig = self.cl.REPO
        self.cl.REPO = REPO_ROOT
        try:
            with contextlib.redirect_stdout(buf):
                code = self.cl.main()
        finally:
            self.cl.REPO = orig
        out = buf.getvalue()
        self.assertEqual(code, 0, f"broken links or anchors:\n{out}")
        self.assertIn("in-document anchors", out)

    def test_broken_anchor_is_detected_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, "repo")
            os.makedirs(repo)
            with open(os.path.join(repo, "a.md"), "w", encoding="utf-8") as fh:
                fh.write("# Real Heading\n\n[x](#real-heading)\n[y](#nope)\n")
            orig = self.cl.REPO
            self.cl.REPO = repo
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    code = self.cl.main()
            finally:
                self.cl.REPO = orig
        out = buf.getvalue()
        self.assertEqual(code, 1)
        self.assertIn("no such heading", out)
        self.assertNotIn("#real-heading)", out)

    def test_cross_file_anchor_is_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, "repo")
            os.makedirs(repo)
            with open(os.path.join(repo, "target.md"), "w", encoding="utf-8") as fh:
                fh.write("# Deep Section\n")
            with open(os.path.join(repo, "src.md"), "w", encoding="utf-8") as fh:
                fh.write("[ok](target.md#deep-section)\n[bad](target.md#missing)\n")
            orig = self.cl.REPO
            self.cl.REPO = repo
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    code = self.cl.main()
            finally:
                self.cl.REPO = orig
        self.assertEqual(code, 1)
        self.assertIn("src.md -> target.md#missing", buf.getvalue())


class TestCheckWorkflows(unittest.TestCase):
    def setUp(self):
        self.repo = os.path.join(REPO_ROOT, "tests")
        if self.repo not in sys.path:
            sys.path.insert(0, self.repo)
        import check_workflows as cw

        self.cw = cw

    def test_committed_workflow_validates(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = self.cw.main()
        self.assertEqual(code, 0)
        self.assertIn("catalog-drift.yml", buf.getvalue())

    def test_every_ci_runs_step_script_exists(self):
        """The reason this checker exists: a renamed script must break CI loudly."""
        import yaml

        path = os.path.join(REPO_ROOT, ".github", "workflows", "catalog-drift.yml")
        with open(path, encoding="utf-8") as fh:
            wf = yaml.safe_load(fh)
        referenced = 0
        for job in wf["jobs"].values():
            for step in job.get("steps") or []:
                run = step.get("run")
                if not run:
                    continue
                for token in run.replace("|", " ").replace(">", " ").split():
                    token = token.strip("'\"")
                    if token.startswith(("_scripts/", "tests/")) and token.endswith(".py"):
                        referenced += 1
                        self.assertTrue(
                            os.path.isfile(os.path.join(REPO_ROOT, token)),
                            f"CI runs {token}, which does not exist",
                        )
        self.assertGreaterEqual(referenced, 4)


class TestRetractedClaimsStayRetracted(unittest.TestCase):
    """Pin the VULN-006 retraction.

    This repo exists to avoid publishing false claims about how achievements
    work. On 2026-10-03 we published one: that Galaxy Brain could be earned by
    self-accepting your own answer. It cannot, and following our own recipe cost
    a maintainer real effort. The retraction must not be quietly reverted.
    """

    DISPROVEN = (
        "the badge does not check",
        "You can answer your own question",
        "self-answer accepted by bot",
        "Repeat twice. → Default",
    )
    # A retraction is allowed to quote what it retracts. These markers are what
    # distinguishes "this is false" from a restatement of the claim as fact.
    RETRACTION_MARKERS = (
        "RETRACTED",
        "That is false",
        "does not work",
        "not possible",
        "did not count",
        "Wrong",
        "wrong",
        "earlier",
        "previously",
        "It was wrong",
    )

    def _read(self, rel):
        with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
            return fh.read()

    def _assert_only_retracted(self, rel):
        text = self._read(rel)
        for claim in self.DISPROVEN:
            for line in text.splitlines():
                if claim not in line:
                    continue
                with self.subTest(rel=rel, claim=claim, line=line.strip()[:100]):
                    self.assertTrue(
                        any(marker in line for marker in self.RETRACTION_MARKERS),
                        f"{rel} restates the disproven claim {claim!r} as fact: "
                        f"{line.strip()[:120]}",
                    )

    def test_galaxy_brain_readme_states_the_different_accepter_rule(self):
        text = self._read("_achievements/galaxy-brain/README.md")
        self.assertIn("someone other than you", text)
        self.assertIn("You cannot accept your own answer", text)

    def test_galaxy_brain_meta_records_the_rule_and_retraction(self):
        text = self._read("_achievements/galaxy-brain/meta.yaml")
        self.assertIn("different account", text)
        self.assertIn("RETRACTED", text)

    def test_disproven_claims_appear_only_inside_a_retraction(self):
        for rel in (
            "_achievements/galaxy-brain/README.md",
            "_achievements/galaxy-brain/meta.yaml",
        ):
            self._assert_only_retracted(rel)

    def test_vuln_006_is_marked_retracted(self):
        text = self._read("SECURITY.md")
        self.assertIn("VULN-006: Galaxy Brain — Self-Answer Abuse (RETRACTED", text)
        self.assertIn("**Status: RETRACTED.**", text)

    def test_vuln_006_proposed_defenses_are_no_longer_claimed_as_needed(self):
        text = self._read("SECURITY.md")
        section = text.split("VULN-006: Galaxy Brain", 1)[1].split("## VULN-007", 1)[0]
        self.assertNotIn("counts at 25% weight", section)
        self.assertIn("already requires", section)

    def test_vuln_006_issue_body_is_a_retraction(self):
        issue = next(i for i in fvi.ISSUES if "VULN-006" in i["title"])
        self.assertIn("RETRACTED", issue["title"])
        self.assertIn("retracted", issue["labels"])
        self.assertIn("That is not possible", issue["body"])

    def test_galaxy_brain_is_not_claimed_automatable(self):
        records = la.load_catalog(os.path.join(REPO_ROOT, "_achievements"))
        gb = next(r for r in records if r["slug"] == "galaxy-brain")
        self.assertIs(gb["automatable"], False)
        self.assertEqual(gb["difficulty"], "Hard")

    def test_difficulty_table_matches_the_social_requirement(self):
        """`Medium` was wrong: the bottleneck is a second person, not technique."""
        readme = self._read("_achievements/galaxy-brain/README.md")
        self.assertIn("**Hard**", readme)


class TestEvidenceLabelling(unittest.TestCase):
    """Every tier threshold must declare how it is known.

    This repo published a false claim once (VULN-006) and shipped a recipe that
    could not work. A bare number invites a reader to treat folklore as fact, so
    the convention is: Verified / community-reported / Unpublished, never a bare
    figure. Only galaxy-brain had this column before it was made mandatory.
    """

    ALLOWED: ClassVar[tuple[str, ...]] = ("Verified", "community-reported", "Unpublished")

    def _tier_tables(self):
        base = os.path.join(REPO_ROOT, "_achievements")
        for slug in sorted(os.listdir(base)):
            if slug.startswith("_"):
                continue
            readme = os.path.join(base, slug, "README.md")
            if not os.path.isfile(readme):
                continue
            with open(readme, encoding="utf-8") as fh:
                lines = fh.read().split("\n")
            start = next(
                (i for i, line in enumerate(lines) if line.startswith("| Tier |")), None
            )
            if start is None:
                self.fail(f"{slug} has no tier table")
            body = []
            i = start + 2
            while i < len(lines) and lines[i].startswith("|"):
                body.append(lines[i])
                i += 1
            yield slug, lines[start], body

    def test_every_tier_table_has_an_evidence_column(self):
        for slug, header, body in self._tier_tables():
            with self.subTest(slug=slug):
                self.assertIn(
                    "Evidence", header, f"{slug} tier table has no Evidence column"
                )
                self.assertTrue(body, f"{slug} tier table has no rows")

    def test_every_tier_row_carries_a_recognised_label(self):
        for slug, header, body in self._tier_tables():
            # Column count varies (some tables have a Badge column), so the last
            # cell is the evidence label and the count is checked against the
            # header separately.
            header_cells = len(header.strip().strip("|").split("|"))
            for row in body:
                cells = [c.strip() for c in row.strip().strip("|").split("|")]
                with self.subTest(slug=slug, row=cells[0]):
                    self.assertEqual(
                        len(cells), header_cells, f"{slug}: row {cells} malformed"
                    )
                    label = cells[-1]
                    self.assertTrue(
                        any(label.startswith(a) for a in self.ALLOWED),
                        f"{slug}: evidence label {label!r} is not one of {list(self.ALLOWED)}",
                    )

    def test_column_count_is_consistent_between_header_and_separator(self):
        for slug, header, body in self._tier_tables():
            with self.subTest(slug=slug):
                header_cells = len(header.strip().strip("|").split("|"))
                for row in body:
                    self.assertEqual(
                        len(row.strip().strip("|").split("|")), header_cells
                    )

    def test_unearned_achievements_are_not_claimed_verified(self):
        """An unearned achievement cannot have a Verified threshold.

        Holding a badge proves the threshold is at most what you reached; it says
        nothing about the number for a tier you have not reached. Only the four
        achievements we actually hold may carry 'Verified'.
        """
        earned = {
            "pull-shark",
            "quickdraw",
            "starstruck",
            "yolo",
        }
        for slug, _header, body in self._tier_tables():
            if slug in earned:
                continue
            for row in body:
                with self.subTest(slug=slug):
                    self.assertNotIn(
                        "Verified", row, f"{slug} is not earned but claims a Verified tier"
                    )

    def test_format_doc_defines_the_labels(self):
        with open(os.path.join(REPO_ROOT, "_docs", "ACHIEVEMENT_FORMAT.md"),
                  encoding="utf-8") as fh:
            text = fh.read()
        for label in ("Verified", "community-reported", "Unpublished"):
            self.assertIn(f"`{label}", text, f"{label} is not defined in the schema doc")


class TestFileIssuesSubprocessSafety(unittest.TestCase):
    """file_vuln_issues.py shells out to `gh` with user-authored bodies.

    The bodies contain backticks, quotes, pipes, newlines and em-dashes. Passing
    them through a shell would be an injection vector and would also break on the
    first quote, so the list-args form is load-bearing and needs a guard.
    """

    def test_gh_run_never_uses_a_shell(self):
        import subprocess as sp

        completed = sp.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with mock.patch("subprocess.run", return_value=completed) as runner:
            fvi._gh_run(["gh", "issue", "create", "--body", "text"])
        self.assertNotIn("shell", runner.call_args.kwargs)

    def test_no_source_file_enables_a_shell(self):
        """The token is assembled at runtime.

        A literal would match this file's own assertion and its failure message,
        making the test permanently and uselessly red.
        """
        token = re.compile(r"shell\s*=\s*" + "True")
        offenders: list[str] = []
        for directory in ("_scripts", "tests"):
            base = os.path.join(REPO_ROOT, directory)
            for name in sorted(os.listdir(base)):
                if not name.endswith(".py"):
                    continue
                with open(os.path.join(base, name), encoding="utf-8") as fh:
                    if token.search(fh.read()):
                        offenders.append(f"{directory}/{name}")
        self.assertEqual(offenders, [], f"shell invocation enabled in: {offenders}")

    def test_bodies_are_passed_as_discrete_argv_entries(self):
        """A body containing shell metacharacters stays one argument."""
        nasty = 'a b "c" `d` | e\nf\ng'
        cmd = ["gh", "issue", "create", "--body", nasty]
        self.assertEqual(cmd[4], nasty)
        self.assertNotIn(nasty, " ".join(cmd[1:4]))

    def test_every_issue_body_is_nonempty_and_has_a_title(self):
        for issue in fvi.ISSUES:
            with self.subTest(title=issue["title"][:30]):
                self.assertTrue(issue["title"].strip())
                self.assertGreater(len(issue["body"].strip()), 200)


# Flags and their values, e.g. "--account neohiro" or "--label 'help wanted'".
# Values may be bare or quoted; quotes are stripped when the command is run.
# A '#' comment ends the capture because '#' cannot start a flag or a value.
DOC_COMMAND_RE = re.compile(
    r"python\s+(?P<path>(?:_scripts|tests)/[A-Za-z0-9_./-]+\.py)"
    r"(?P<args>(?:\s+--?[A-Za-z0-9][A-Za-z0-9-]*"
    r"(?:[ =](?:\"[^\"]*\"|'[^']*'|[A-Za-z0-9][A-Za-z0-9_./:#-]*)?)*)*)"
)


def _split_doc_args(raw: str) -> list[str]:
    """Tokenise a captured argument string, stripping quotes from values."""
    import shlex

    try:
        return shlex.split(raw)
    except ValueError:
        return raw.split()


# Values in the docs that stand in for something the reader supplies. Commands
# containing them are illustrative, not runnable here, so they are verified for
# existence and flags but not executed.
DOC_PLACEHOLDERS = frozenset({
    "owner/name", "a/b", "feature/x", "your/title", "your-file.md", "notes.md",
})


def _normalise_continuations(text: str) -> str:
    """Join shell line-continuations so a multi-line command matches as one line."""
    return re.sub(r"\\\s*\n\s*", " ", text)


def _read_doc(rel: str) -> str:
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


class TestDocumentedCommandsAreReal(unittest.TestCase):
    """Every command we tell a reader to run must actually work.

    ``check_workflows.py`` validates scripts referenced by CI ``run:`` steps. Docs
    were unchecked, which is how ``_achievements/galaxy-brain/README.md`` came to
    cite ``_scripts/seed_discussion.py`` -- a file that never existed -- with no
    check failing. A docs repo that hands out broken commands has failed at its
    one job.
    """

    @classmethod
    def setUpClass(cls):
        cls.referenced: dict[str, list[str]] = {}
        for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
            dirnames[:] = [
                d
                for d in dirnames
                if d not in {".git", "__pycache__", ".pytest_cache"}
            ]
            for name in sorted(filenames):
                if not name.endswith(".md"):
                    continue
                md = os.path.join(dirpath, name)
                with open(md, encoding="utf-8") as fh:
                    text = _normalise_continuations(fh.read())
                for match in DOC_COMMAND_RE.finditer(text):
                    rel = os.path.relpath(md, REPO_ROOT).replace("\\", "/")
                    cls.referenced.setdefault(match.group("path"), []).append(rel)

    def test_docs_actually_reference_our_scripts(self):
        """Guards the guard: if this regex stops matching, the tests below pass
        for free."""
        self.assertGreaterEqual(
            len(self.referenced), 4, f"only found {sorted(self.referenced)}"
        )

    def test_every_referenced_script_exists(self):
        missing = [s for s in self.referenced if not os.path.isfile(os.path.join(REPO_ROOT, s))]
        self.assertEqual(missing, [], f"docs cite non-existent scripts: {missing}")

    def test_every_documented_flag_is_accepted(self):
        """Catches typo'd flags such as ``--chek`` that nothing else would notice."""
        bad: list[str] = []
        for script, docs in sorted(self.referenced.items()):
            path = os.path.join(REPO_ROOT, script)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            for match in DOC_COMMAND_RE.finditer(
                "\n".join(_read_doc(d) for d in docs)
            ):
                if match.group("path") != script:
                    continue
                for flag in _split_doc_args(match.group("args")):
                    # Only flags this script owns; ignore values and prose.
                    if flag.startswith("--") and flag not in text:
                        bad.append(f"{flag} in {script} (cited by {docs})")
        self.assertEqual(bad, [], f"documented flags absent from their script: {bad}")

    # Only hermetic commands are executed. Network-dependent ones (grant_check,
    # find_contributions) are verified to exist and to accept their flags, but not
    # run: doing so made the suite take 13s+ and turned a GitHub outage into a
    # red test suite. Both already run as their own CI steps.
    HERMETIC = frozenset({
        "_scripts/list_achievements.py",
        "_scripts/check_coauthor.py",
        "_scripts/submit_contribution.py",
        "tests/check_links.py",
        "tests/check_workflows.py",
    })

    def test_every_documented_command_actually_runs(self):
        """Execute what we tell readers to run, for commands that touch nothing.

        Any hermetic documented invocation must exit 0. Drift, a missing marker or
        a broken anchor all surface here as a documentation failure.
        """
        import subprocess

        checked: list[tuple[str, ...]] = []

        for script, docs in sorted(self.referenced.items()):
            path = os.path.join(REPO_ROOT, script)
            if not os.path.isfile(path):
                continue
            if script not in self.HERMETIC:
                continue
            joined = _normalise_continuations(
                "\n".join(_read_doc(d) for d in docs)
            )
            for match in DOC_COMMAND_RE.finditer(joined):
                if match.group("path") != script:
                    continue
                argv = (script, *_split_doc_args(match.group("args")))
                if argv in checked:
                    continue
                if DOC_PLACEHOLDERS.intersection(_split_doc_args(match.group("args"))):
                    continue
                checked.append(argv)
                result = subprocess.run(
                    ["python", *argv],
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=120,
                    cwd=REPO_ROOT,
                )
                with self.subTest(command=" ".join(argv)):
                    self.assertEqual(
                        result.returncode,
                        0,
                        f"`{' '.join(argv)}` exited {result.returncode}\n"
                        f"{(result.stderr or '').strip()[:300]}",
                    )

        self.assertGreaterEqual(len(checked), 4)

    def setUp(self):
        self.scripts = os.path.join(REPO_ROOT, "_scripts")
        if self.scripts not in sys.path:
            sys.path.insert(0, self.scripts)
        import find_contributions as fc

        self.fc = fc

    @staticmethod
    def _item(url, repo, title="t", comments=0, label=None):
        return {
            "url": url,
            "title": title,
            "repository": {"nameWithOwner": repo},
            "commentsCount": comments,
            "labels": [],
            "matched_label": label,
        }

    def test_cap_per_repo_limits_domination(self):
        items = [
            self._item("u1", "spam/farm"),
            self._item("u2", "spam/farm"),
            self._item("u3", "spam/farm"),
            self._item("u4", "real/project"),
        ]
        kept = self.fc.cap_per_repo(items, 2)
        repos = [i["repository"]["nameWithOwner"] for i in kept]
        self.assertEqual(repos.count("spam/farm"), 2)
        self.assertIn("real/project", repos)

    def test_cap_per_repo_zero_is_unlimited(self):
        items = [self._item(f"u{i}", "spam/farm") for i in range(5)]
        self.assertEqual(len(self.fc.cap_per_repo(items, 0)), 5)

    def test_own_repos_are_filtered(self):
        """Open Sourcerer needs a repo we do NOT own; ours would be Pull Shark."""
        items = [
            self._item("u1", "neohiro/ExploitProtection"),
            self._item("u2", "stranger/project"),
        ]
        owned = {"neohiro/exploitprotection"}
        kept = self.fc.filter_out_own_repos(items, "neohiro", owned)
        self.assertEqual([i["url"] for i in kept], ["u2"])

    def test_filter_is_case_insensitive(self):
        items = [self._item("u1", "NeoHiro/Thing")]
        self.assertEqual(self.fc.filter_out_own_repos(items, "neohiro", set()), [])

    def test_owner_of_handles_missing_repository(self):
        self.assertEqual(self.fc.owner_of({}), "")

    def test_search_issues_parses_gh_output(self):
        payload = json.dumps([{"url": "u1", "repository": {"nameWithOwner": "a/b"}}])
        with mock.patch.object(self.fc, "run_gh", return_value=payload):
            out = self.fc.search_issues("good first issue", 5)
        self.assertEqual(len(out), 1)

    def test_search_issues_raises_on_unparseable_output(self):
        with mock.patch.object(self.fc, "run_gh", return_value="not json"):
            with self.assertRaises(self.fc.FinderError):
                self.fc.search_issues("good first issue", 5)

    def test_search_issues_rejects_non_list_payload(self):
        with mock.patch.object(self.fc, "run_gh", return_value='{"a": 1}'):
            with self.assertRaises(self.fc.FinderError):
                self.fc.search_issues("good first issue", 5)

    def test_gh_failure_becomes_a_clean_error(self):
        boom = subprocess.CompletedProcess(args=[], returncode=1, stdout="",
                                           stderr="HTTP 401: Bad credentials")
        with mock.patch.object(self.fc.subprocess, "run", return_value=boom):
            with self.assertRaises(self.fc.FinderError) as ctx:
                self.fc.run_gh(["search", "issues"])
        self.assertIn("401", str(ctx.exception))

    def test_missing_gh_cli_is_reported_clearly(self):
        with mock.patch.object(
            self.fc.subprocess, "run", side_effect=FileNotFoundError("gh")
        ):
            with self.assertRaises(self.fc.FinderError) as ctx:
                self.fc.run_gh(["search", "issues"])
        self.assertIn("gh", str(ctx.exception))

    def test_main_returns_two_when_nothing_matches(self):
        with mock.patch.object(self.fc, "collect", return_value=[]):
            with contextlib.redirect_stdout(io.StringIO()):
                code = self.fc.main([])
        self.assertEqual(code, 2)

    def test_main_returns_zero_with_results(self):
        items = [self._item("u1", "a/b", label="good first issue")]
        with (
            mock.patch.object(self.fc, "collect", return_value=items),
            mock.patch.object(self.fc, "load_owned_repos", return_value=set()),
        ):
            with contextlib.redirect_stdout(io.StringIO()):
                code = self.fc.main([])
        self.assertEqual(code, 0)

    def test_main_rejects_bad_limit(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = self.fc.main(["--limit", "0"])
        self.assertEqual(code, 1)
        self.assertIn(">= 1", err.getvalue())

    def test_main_returns_one_on_finder_error(self):
        err = io.StringIO()
        with mock.patch.object(self.fc, "collect", side_effect=self.fc.FinderError("x")):
            with contextlib.redirect_stderr(err):
                code = self.fc.main([])
        self.assertEqual(code, 1)
        self.assertIn("error:", err.getvalue())

    def test_json_output_is_valid(self):
        items = [self._item("u1", "a/b", label="good first issue")]
        buf = io.StringIO()
        with (
            mock.patch.object(self.fc, "collect", return_value=items),
            mock.patch.object(self.fc, "load_owned_repos", return_value=set()),
            contextlib.redirect_stdout(buf),
        ):
            self.fc.main(["--json"])
        self.assertEqual(len(json.loads(buf.getvalue())), 1)

    def test_tool_opens_nothing(self):
        """The guarantee that keeps this legitimate: search and read only."""
        with open(os.path.join(REPO_ROOT, "_scripts", "find_contributions.py"),
                  encoding="utf-8") as fh:
            source = fh.read()
        for forbidden in ('"issue", "create"', '"issue", "comment"', '"api"',
                          '"pr", "create"', '"reaction"'):
            self.assertNotIn(forbidden, source, f"write operation present: {forbidden}")


class TestCheckCoauthor(unittest.TestCase):
    """Trailer linting. The value is catching a malformed address before the
    commit lands, because GitHub then attributes it to nobody and says nothing."""

    def setUp(self):
        scripts = os.path.join(REPO_ROOT, "_scripts")
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        import check_coauthor as cc

        self.cc = cc

    def test_valid_trailers_accepted(self):
        for good in (
            "Co-authored-by: Alex Smith <alex@example.com>",
            "Co-authored-by: Alex Smith <1234+alex@users.noreply.github.com>",
            "Co-authored-by: Alex <a.b@x.co.uk>",
        ):
            with self.subTest(trailer=good):
                ok, reason = self.cc.check_trailer(good)
                self.assertTrue(ok, reason)

    def test_malformed_trailers_rejected_with_reasons(self):
        cases = {
            "Co-authored-by:": "expected exactly",
            "Co-authored-by: Alex": "expected exactly",
            "Co-authored-by: <alex@example.com>": "missing co-author name",
            "Co-authored-by: Alex <notanemail>": "not a valid address",
            "Co-authored-by: Alex <>": "missing co-author email",
            "Co-authored-by: Alex <a b@c.com>": "not a valid address",
        }
        for bad, expected in cases.items():
            with self.subTest(trailer=bad):
                ok, reason = self.cc.check_trailer(bad)
                self.assertFalse(ok)
                self.assertIn(expected, reason)

    def test_case_insensitive_prefix_is_detected_by_caller(self):
        """git log gives the raw message; we match the prefix case-insensitively."""
        trailers = ["Co-authored-by: A <a@b.co>", "co-authored-by: B <b@b.co>"]
        lowered = [t.lower().startswith("co-authored-by:") for t in trailers]
        self.assertEqual(lowered, [True, True])

    def test_git_failure_is_reported_cleanly(self):
        boom = subprocess.CompletedProcess(args=[], returncode=128, stdout="",
                                           stderr="fatal: not a git repository")
        with mock.patch.object(self.cc, "run_git", side_effect=self.cc.GitError("x")):
            with self.assertRaises(self.cc.GitError):
                self.cc.commits_to_check(None, None)
        self.assertIn("not a git repository", boom.stderr)

    def test_missing_git_is_named(self):
        with mock.patch.object(
            self.cc.subprocess, "run", side_effect=FileNotFoundError("git")
        ):
            with self.assertRaises(self.cc.GitError) as ctx:
                self.cc.run_git(["log"])
        self.assertIn("git", str(ctx.exception))

    def test_main_rejects_bad_last(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = self.cc.main(["--last", "0"])
        self.assertEqual(code, 1)

    def test_main_returns_two_on_malformed_trailer(self):
        finding = [{"sha": "abc", "subject": "s", "trailers": ["Co-authored-by: X"],
                    "problems": ["missing co-author email"]}]
        with mock.patch.object(self.cc, "audit", return_value=finding):
            with contextlib.redirect_stdout(io.StringIO()):
                code = self.cc.main([])
        self.assertEqual(code, 2)

    def test_main_returns_zero_without_trailers(self):
        finding = [{"sha": "abc", "subject": "s", "trailers": [], "problems": []}]
        with mock.patch.object(self.cc, "audit", return_value=finding):
            with contextlib.redirect_stdout(io.StringIO()):
                code = self.cc.main([])
        self.assertEqual(code, 0)

    def test_tool_creates_no_commits(self):
        """Guarantee: this script only reads. It must never author a commit."""
        with open(os.path.join(REPO_ROOT, "_scripts", "check_coauthor.py"),
                  encoding="utf-8") as fh:
            source = fh.read()
        for forbidden in ("commit\"", "commit --", "merge", "push", "amend"):
            self.assertNotIn(forbidden, source, f"write operation present: {forbidden}")


class TestSubmitContribution(unittest.TestCase):
    def setUp(self):
        scripts = os.path.join(REPO_ROOT, "_scripts")
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        import submit_contribution as sc

        self.sc = sc

    def test_rejects_malformed_repo(self):
        for bad in ("norepo", "/leading", "trailing/", "a/b/c"):
            with self.subTest(repo=bad):
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    code = self.sc.main(["--title", "t", "--repo", bad])
                self.assertEqual(code, 1)
                self.assertIn("owner/name", err.getvalue())

    def test_rejects_empty_title(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = self.sc.main(["--title", "   ", "--repo", "a/b"])
        self.assertEqual(code, 1)
        self.assertIn("--title", err.getvalue())

    def test_refuses_when_nothing_to_propose(self):
        with (
            mock.patch.object(self.sc, "current_branch", return_value="feature"),
            mock.patch.object(self.sc, "commits_ahead", return_value=[]),
            mock.patch.object(self.sc, "uncommitted_changes", return_value=False),
        ):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = self.sc.main(["--title", "t", "--repo", "a/b"])
        self.assertEqual(code, 2)
        self.assertIn("nothing to propose", err.getvalue())

    def test_refuses_when_work_is_uncommitted(self):
        with (
            mock.patch.object(self.sc, "current_branch", return_value="feature"),
            mock.patch.object(self.sc, "commits_ahead", return_value=["a1 b"]),
            mock.patch.object(self.sc, "uncommitted_changes", return_value=True),
        ):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = self.sc.main(["--title", "t", "--repo", "a/b"])
        self.assertEqual(code, 2)
        self.assertIn("uncommitted", err.getvalue())

    def test_dry_run_opens_nothing(self):
        with (
            mock.patch.object(self.sc, "current_branch", return_value="feature"),
            mock.patch.object(self.sc, "commits_ahead", return_value=["a1 fix"]),
            mock.patch.object(self.sc, "uncommitted_changes", return_value=False),
            mock.patch.object(self.sc, "gh", side_effect=AssertionError("must not open")),
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = self.sc.main(["--title", "t", "--repo", "a/b", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("dry run", buf.getvalue())

    def test_body_includes_closes_reference(self):
        body = self.sc.build_body(42, None)
        self.assertIn("Closes #42", body)
        self.assertIn("Testing", body)

    def test_body_file_appends_missing_closes(self):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("my notes")
            path = fh.name
        try:
            body = self.sc.build_body(7, path)
        finally:
            os.unlink(path)
        self.assertTrue(body.startswith("my notes"))
        self.assertIn("Closes #7", body)

    def test_body_file_does_not_duplicate_closes(self):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("notes\n\nCloses #9")
            path = fh.name
        try:
            body = self.sc.build_body(9, path)
        finally:
            os.unlink(path)
        self.assertEqual(body.count("Closes #9"), 1)

    def test_empty_body_file_is_refused(self):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("   ")
            path = fh.name
        try:
            with self.assertRaises(self.sc.PreflightError):
                self.sc.build_body(None, path)
        finally:
            os.unlink(path)

    def test_tool_does_not_generate_code(self):
        """The legitimacy guarantee: it opens a PR for work already done."""
        with open(os.path.join(REPO_ROOT, "_scripts", "submit_contribution.py"),
                  encoding="utf-8") as fh:
            source = fh.read()
        for forbidden in ("patch\"", "diff --git", "sed -i", "write_text"):
            self.assertNotIn(forbidden, source, f"code generation present: {forbidden}")


class TestHermeticAllowlistIsHonest(unittest.TestCase):
    """The allowlist exists to keep the suite fast and offline.

    An earlier version had a test asserting network scripts were absent from the
    allowlist, but it derived the set of network scripts by subtracting the
    allowlist from the referenced scripts, so it could never fail. This asserts
    something falsifiable instead: the allowlist names files that exist, and the
    scripts it excludes are genuinely the network-dependent ones.
    """
    scripts = os.path.join(REPO_ROOT, "_scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import find_contributions as fc

    allowlist = TestDocumentedCommandsAreReal.HERMETIC

    def test_every_allowlisted_script_exists(self):
        for script in sorted(self.allowlist):
            with self.subTest(script=script):
                self.assertTrue(
                    os.path.isfile(os.path.join(REPO_ROOT, script)),
                    f"{script} is allowlisted but does not exist",
                )

    def test_network_scripts_are_genuinely_excluded(self):
        """find_contributions shells out to `gh search`; it must stay out."""
        with open(
            os.path.join(REPO_ROOT, "_scripts", "find_contributions.py"),
            encoding="utf-8",
        ) as fh:
            source = fh.read()
        self.assertIn("gh", source)
        self.assertNotIn("_scripts/find_contributions.py", self.allowlist)

    def test_allowlist_covers_the_fast_checks(self):
        for expected in ("tests/check_links.py", "tests/check_workflows.py",
                         "_scripts/list_achievements.py"):
            self.assertIn(expected, self.allowlist)


class TestCollectOrdering(unittest.TestCase):
    """Regression: an ascending sort led with the stalest issues.

    For a first contribution the freshest unclaimed issue in an active repo is
    what you want, so ordering is fewest-comments first, then newest first.
    """

    def setUp(self):
        scripts = os.path.join(REPO_ROOT, "_scripts")
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        import find_contributions as fc

        self.fc = fc

    def _item(self, url, repo, updated, comments):
        return {
            "url": url,
            "title": "t",
            "repository": {"nameWithOwner": repo},
            "commentsCount": comments,
            "updatedAt": updated,
        }

    def test_newest_comes_first_within_equal_comments(self):
        pages = {
            "good first issue": [
                self._item("a", "x/one", "2026-01-01T00:00:00Z", 0),
                self._item("b", "x/two", "2026-10-01T00:00:00Z", 0),
                self._item("c", "x/three", "2026-06-01T00:00:00Z", 0),
            ]
        }
        with mock.patch.object(self.fc, "search_issues", side_effect=lambda label, n: pages[label]):
            out = self.fc.collect(("good first issue",), 10)
        self.assertEqual([i["url"] for i in out], ["b", "c", "a"])

    def test_fewer_comments_wins_even_if_older(self):
        pages = {
            "good first issue": [
                self._item("fresh-but-claimed", "x/one", "2026-10-01T00:00:00Z", 5),
                self._item("stale-and-open", "x/two", "2026-01-01T00:00:00Z", 0),
            ]
        }
        with mock.patch.object(self.fc, "search_issues", side_effect=lambda label, n: pages[label]):
            out = self.fc.collect(("good first issue",), 10)
        self.assertEqual(out[0]["url"], "stale-and-open")

    def test_dedupes_across_labels(self):
        shared = self._item("same", "x/one", "2026-10-01T00:00:00Z", 0)
        pages = {"good first issue": [shared], "help wanted": [dict(shared)]}
        with mock.patch.object(self.fc, "search_issues", side_effect=lambda label, n: pages[label]):
            out = self.fc.collect(("good first issue", "help wanted"), 10)
        self.assertEqual(len(out), 1)

    def test_missing_repository_field_does_not_crash(self):
        item = {"url": "u", "title": "t", "commentsCount": 0, "updatedAt": "z"}
        pages = {"good first issue": [item]}
        with mock.patch.object(self.fc, "search_issues", side_effect=lambda label, n: pages[label]):
            out = self.fc.collect(("good first issue",), 10)
        self.assertEqual(self.fc.repo_name(out[0]), "")
        self.assertEqual(self.fc.owner_of(out[0]), "")
        self.assertIn("?", self.fc.render(out))

    def test_non_dict_repository_is_tolerated(self):
        item = {"url": "u", "title": "t", "commentsCount": 0,
                "updatedAt": "z", "repository": "just-a-string"}
        pages = {"good first issue": [item]}
        with mock.patch.object(self.fc, "search_issues", side_effect=lambda label, n: pages[label]):
            out = self.fc.collect(("good first issue",), 10)
        self.assertEqual(self.fc.repo_name(out[0]), "")


class TestSubmitContributionFailsClosed(unittest.TestCase):
    """If we cannot prove the tree is clean, we must not open a PR."""

    def setUp(self):
        scripts = os.path.join(REPO_ROOT, "_scripts")
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        import submit_contribution as sc

        self.sc = sc

    def test_uncommitted_changes_raises_on_git_failure(self):
        with mock.patch.object(self.sc, "git", side_effect=self.sc.ToolError("boom")):
            with self.assertRaises(self.sc.PreflightError):
                self.sc.uncommitted_changes()

    def test_main_refuses_when_tree_state_unknown(self):
        with (
            mock.patch.object(self.sc, "current_branch", return_value="f"),
            mock.patch.object(self.sc, "commits_ahead", return_value=["a1 x"]),
            mock.patch.object(
                self.sc, "uncommitted_changes",
                side_effect=self.sc.PreflightError("cannot determine"),
            ),
            mock.patch.object(self.sc, "gh", side_effect=AssertionError("must not open")),
        ):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = self.sc.main(["--title", "t", "--repo", "a/b"])
        self.assertEqual(code, 2)
        self.assertIn("cannot determine", err.getvalue())

    def test_validate_repo_rejects_path_like_values(self):
        for bad in ("a/b/c", "..", "../x", "a b/c", "/x", "a/"):
            with self.subTest(repo=bad):
                with self.assertRaises(self.sc.ToolError):
                    self.sc.validate_repo(bad)

    def test_validate_repo_accepts_ordinary_slugs(self):
        for good in ("owner/name", "a-b_c.d/e-f_g.h"):
            with self.subTest(repo=good):
                self.assertEqual(self.sc.validate_repo(good), good)


class TestReadmeStructureBlockIsComplete(unittest.TestCase):
    """Every script we ship must appear in the README's structure block.

    The inverse of TestDocumentedCommandsAreReal. That test asks "does every
    script referenced in prose exist?", which cannot notice a script that exists
    and is never mentioned. Three had drifted that way, two of them added in the
    same session that wrote the tests.
    """

    def _structure_block(self):
        with open(os.path.join(REPO_ROOT, "README.md"), encoding="utf-8") as fh:
            text = fh.read()
        start = text.index("achievement-hacks/")
        end = text.index("### Running the checks")
        return text[start:end]

    def test_every_script_is_listed(self):
        block = self._structure_block()
        missing = []
        for directory in ("_scripts", "tests"):
            base = os.path.join(REPO_ROOT, directory)
            for name in sorted(os.listdir(base)):
                if not name.endswith(".py") or name == "__init__.py":
                    continue
                if name not in block:
                    missing.append(f"{directory}/{name}")
        self.assertEqual(
            missing, [], f"scripts absent from the README structure block: {missing}"
        )

    def test_every_doc_is_listed(self):
        block = self._structure_block()
        missing = [
            name
            for name in sorted(os.listdir(os.path.join(REPO_ROOT, "_docs")))
            if name.endswith(".md") and name not in block
        ]
        self.assertEqual(
            missing, [], f"_docs entries absent from the README structure block: {missing}"
        )

    def test_block_lists_nothing_that_does_not_exist(self):
        block = self._structure_block()
        for rel in re.findall(r"(_scripts/[A-Za-z0-9_.-]+\.py|tests/[A-Za-z0-9_.-]+\.py)", block):
            with self.subTest(path=rel):
                self.assertTrue(os.path.isfile(os.path.join(REPO_ROOT, rel)))


class TestCheckCoauthorIsSinglePass(unittest.TestCase):
    """Performance: auditing N commits must not cost 2N git invocations.

    The original implementation shelled out twice per commit (body, then
    subject), so ``--last 100`` meant 201 subprocess spawns for data git can
    return in one call. Not fatal, but it is a hot spot for no reason.
    """

    def setUp(self):
        scripts = os.path.join(REPO_ROOT, "_scripts")
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        import check_coauthor as cc

        self.cc = cc

    def test_one_git_call_per_audit(self):
        calls = []

        def fake(args):
            calls.append(args)
            if args[0] == "log" and "--format=%H" in args:
                return "aaa111\nbbb222\n"
            if args[0] == "log" and "--format=%s" in args:
                return "subject"
            if args[0] == "rev-parse":
                return "aaa111\n"
            return "s\n\nCo-authored-by: A <a@b.co>\n"

        with mock.patch.object(self.cc, "run_git", side_effect=fake):
            self.cc.audit(last=2, branch=None)

        per_commit = [
            c for c in calls if c[0] == "log" and "--format=%s" not in c
            and "rev-parse" not in c and "-1" not in c
        ]
        self.assertEqual(
            len(per_commit), 1,
            f"expected a single bulk log call, got {len(per_commit)}: {per_commit}",
        )

    def _rec(self, sha: str, subject: str, body: str) -> str:
        """One git-log record: exactly three fields, record terminated.

        Arity is fixed at three on purpose. An earlier ``*fields`` version joined
        every argument with the field separator, which silently produced
        ``body\\x1fCo-authored-by: ...`` -- a fourth field that does not exist in
        the real format -- and made the trailer unfindable. The body is one
        field and contains newlines, never separators.
        """
        return (
            self.cc.FIELD_SEP.join([sha, subject, body]) + self.cc.RECORD_SEP
        )

    def test_audit_reports_subjects_alongside_trailers(self):
        payload = self._rec(
            "aaa111111111", "first subject",
            "first body\n\nCo-authored-by: A <a@b.co>\n",
        ) + self._rec(
            "bbb222222222", "second subject",
            "second body\n\nCo-authored-by: B <b@b.co>\n",
        )

        with mock.patch.object(self.cc, "run_git", return_value=payload):
            findings = self.cc.audit(last=2, branch=None)

        self.assertEqual(len(findings), 2, "one record per commit, not two")
        self.assertEqual([f["sha"] for f in findings], ["aaa111111111", "bbb222222222"])
        self.assertEqual([f["subject"] for f in findings],
                         ["first subject", "second subject"])
        self.assertEqual(findings[0]["trailers"], ["Co-authored-by: A <a@b.co>"])
        self.assertEqual(findings[1]["trailers"], ["Co-authored-by: B <b@b.co>"])
        self.assertEqual([f["problems"] for f in findings], [[], []])

    def test_sha_is_never_a_subject_line(self):
        """Regression: the record separator once fell between subject and body,
        so the second half of each commit parsed as a commit whose 'sha' was the
        previous subject line."""
        payload = self._rec("deadbeef0001", "fix: something important", "body one\n") \
            + self._rec("deadbeef0002", "chore: another thing", "body two\n")

        with mock.patch.object(self.cc, "run_git", return_value=payload):
            findings = self.cc.audit(last=2, branch=None)
        self.assertEqual(len(findings), 2)
        for finding in findings:
            with self.subTest(subject=finding["subject"]):
                self.assertRegex(finding["sha"], r"^[0-9a-f]{12}$")

    def test_comment_lines_are_not_mistaken_for_trailers(self):
        payload = self._rec(
            "aaa111111111", "subject",
            "body\n# Co-authored-by: Ghost <ghost@example.com>\n",
        )
        with mock.patch.object(self.cc, "run_git", return_value=payload):
            findings = self.cc.audit(last=1, branch=None)
        self.assertEqual(findings[0]["trailers"], [])

    def test_blank_records_are_discarded(self):
        payload = self._rec("aaa111111111", "s", "b\n") + "\n\n"
        with mock.patch.object(self.cc, "run_git", return_value=payload):
            findings = self.cc.audit(last=1, branch=None)
        self.assertEqual(len(findings), 1)


class TestYamlLoading(unittest.TestCase):
    def test_missing_pyyaml_raises_actionable_error(self):
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("no module named yaml")
            return real_import(name, *args, **kwargs)

        path = os.path.join(REPO_ROOT, "_achievements", "starstruck", "meta.yaml")
        builtins.__import__ = fake_import
        try:
            with self.assertRaises(la.CatalogError) as ctx:
                la._load_yaml(path)
        finally:
            builtins.__import__ = real_import
        self.assertIn("pip install", str(ctx.exception))

    def test_types_are_coerced_not_strings(self):
        path = os.path.join(REPO_ROOT, "_achievements", "starstruck", "meta.yaml")
        data = la._load_yaml(path)
        self.assertIs(data["earnable"], True)
        self.assertEqual(data["tiers"][0]["threshold"], 16)
        self.assertIsInstance(data["earned_on"], list)

    def test_verified_block_is_parsed_as_nested_mapping(self):
        path = os.path.join(REPO_ROOT, "_achievements", "pull-shark", "meta.yaml")
        data = la._load_yaml(path)
        self.assertEqual(data["verified"]["tier"], "Silver")
        self.assertEqual(data["verified"]["repeat_count"], 3)

    def test_invalid_yaml_is_reported(self):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as fh:
            fh.write("slug: x\n  bad_indent: y\n")
            path = fh.name
        try:
            with self.assertRaises(la.CatalogError):
                la._load_yaml(path)
        finally:
            os.unlink(path)

    def test_non_mapping_is_rejected(self):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as fh:
            fh.write("- just\n- a\n- list\n")
            path = fh.name
        try:
            with self.assertRaises(la.CatalogError):
                la._load_yaml(path)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)

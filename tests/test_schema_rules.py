"""Both conditional rules in _docs/meta.schema.json are load-bearing.

The schema carries two ``if``/``then`` pairs: an ``Earned`` entry must carry a
``verified:`` block, and an ``earnable: false`` entry must say why in
``deprecated_reason``. Rewriting the schema to add the first rule quietly dropped
the second, and every committed entry still happened to comply - so nothing
failed and nothing said so.

Both rules are therefore pinned here, in both directions: each fires on the
shapes it should reject, and stays quiet on the shapes it should leave alone. A
rule that only ever fires is indistinguishable from one that is not wired up.
"""
import json
import os
import pathlib
import unittest

import yaml

REPO = pathlib.Path(os.path.dirname(os.path.abspath(__file__))).parent
SCHEMA_PATH = REPO / "_docs" / "meta.schema.json"

try:
    import jsonschema
except ImportError:  # pragma: no cover
    # Skipped, not failed. jsonschema is only needed for --validate-schema, and
    # the rest of this repository runs without it. A module-level import failure
    # would abort collection for the whole file, so a missing optional dependency
    # would read as a broken schema rule rather than as an absent package.
    jsonschema = None

VALID_ENTRY = {
    "slug": "demo",
    "name": "Demo",
    "emoji": "D",
    "tiers": [{"name": "Default", "threshold": 1}],
    "earned_on": [],
    "status": "Not yet",
    "earnable": True,
    "how_earned": "Opened a pull request that was merged.",
    "automatable": False,
    "automation_difficulty": "Trivial",
}

VERIFIED_BLOCK = {
    "account": "neohiro",
    "tier": "Default",
    "verified_on": "2026-10-06",
    "method": "observed on the profile sidebar",
}


def _validator():
    if jsonschema is None:
        raise unittest.SkipTest("jsonschema not installed; pip install -r requirements.txt")
    return jsonschema.Draft202012Validator(
        json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    )


class TestSchemaConditionalRules(unittest.TestCase):
    def assertValid(self, document):
        errors = list(_validator().iter_errors(document))
        self.assertEqual(
            [f"{'.'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors],
            [],
        )

    def assertInvalid(self, document):
        self.assertTrue(
            list(_validator().iter_errors(document)),
            "expected this document to be rejected by meta.schema.json",
        )

    # --- Earned requires a verified block ---------------------------------

    def test_earned_with_verified_block_is_valid(self):
        self.assertValid(
            dict(VALID_ENTRY, status="Earned", earned_on=["neohiro"], verified=VERIFIED_BLOCK)
        )

    def test_earned_without_verified_block_is_rejected(self):
        self.assertInvalid(dict(VALID_ENTRY, status="Earned", earned_on=["neohiro"]))

    # --- unearnable requires a reason -------------------------------------

    def test_unearnable_with_reason_is_valid(self):
        self.assertValid(
            dict(
                VALID_ENTRY,
                status="Unobtainable",
                earnable=False,
                deprecated_reason="Requires an active paid subscription.",
            )
        )

    def test_unearnable_without_reason_is_rejected(self):
        """The rule that was dropped when `verified:` was added. Every committed
        entry happens to carry a reason, so nothing caught its absence."""
        self.assertInvalid(dict(VALID_ENTRY, status="Unobtainable", earnable=False))

    # --- and neither fires when it should not -----------------------------

    def test_earnable_true_needs_no_reason(self):
        self.assertValid(dict(VALID_ENTRY))

    def test_not_yet_needs_no_verified_block(self):
        self.assertValid(dict(VALID_ENTRY, status="Not yet"))

    # --- the committed catalog --------------------------------------------

    def test_every_committed_entry_validates(self):
        entries = sorted((REPO / "_achievements").rglob("meta.yaml"))
        self.assertGreaterEqual(len(entries), 15)
        for path in entries:
            with self.subTest(slug=path.parent.name):
                document = yaml.safe_load(path.read_text(encoding="utf-8"))
                self.assertValid(document)

    def test_every_earned_entry_records_how_it_was_verified(self):
        """A `verified:` block with an empty method separates nothing."""
        earned = 0
        for path in sorted((REPO / "_achievements").rglob("meta.yaml")):
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
            if document.get("status") != "Earned":
                continue
            earned += 1
            with self.subTest(slug=path.parent.name):
                self.assertValid(document)
                for field in ("account", "tier", "verified_on", "method"):
                    self.assertTrue(
                        str(document["verified"].get(field, "")).strip(),
                        f"{path.parent.name}: verified.{field} is empty",
                    )
        self.assertGreaterEqual(earned, 4, "expected the four badges neohiro holds")


if __name__ == "__main__":
    unittest.main(verbosity=2)
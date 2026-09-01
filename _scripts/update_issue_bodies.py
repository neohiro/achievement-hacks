#!/usr/bin/env python3
"""update_issue_bodies.py — fix anchor links in existing GitHub Issues 1-6."""
import subprocess

ANCHORS = {
    1: "vuln-001-quickdraw-sub-5-minute-issuepr-close-loop",
    2: "vuln-002-yolo-review-free-merge-via-admin-override",
    3: "vuln-003-heart-on-your-sleeve-mass-reaction-automation",
    4: "vuln-004-pair-extraordinaire-co-author-trailer-abuse",
    5: "vuln-005-pull-shark-automated-pr-farming",
    6: "vuln-006-galaxy-brain-discussion-self-answer-abuse",
}

REPO = "neohiro/achievement-hacks"


def gh(*args):
    result = subprocess.run(
        ["gh"] + list(args),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        print(f"ERR [{args[0]} #{args[1] if len(args) > 1 else '?'}]: {result.stderr.strip()}")
        return None
    return result.stdout


def main():
    for num, anchor in ANCHORS.items():
        # Get current body
        current = gh("issue", "view", str(num), "--repo", REPO, "--json", "body")
        if not current:
            print(f"Issue #{num}: could not fetch body, skipping")
            continue
        import json
        try:
            data = json.loads(current)
        except json.JSONDecodeError as exc:
            print(f"Issue #{num}: JSON decode error — {exc}")
            continue
        old_body = data.get("body", "")

        # Replace the broken anchor in the "Full security analysis" line
        old_marker = f"SECURITY.md#vuln-{num:03d}"
        # Fix pattern: vuln-001-quickdraw--... → vuln-001-quickdraw-...
        import re
        new_body = re.sub(
            rf"(SECURITY\.md#vuln-{num:03d}-[a-z-]+)--",
            lambda m: m.group(1) + "-",
            old_body,
        )

        if old_body == new_body:
            print(f"Issue #{num}: no change needed (anchor may already be correct)")
        else:
            # Write new body to temp file to avoid escaping issues
            import tempfile, os
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, encoding="utf-8"
            ) as f:
                f.write(new_body)
                tmp = f.name
            gh("issue", "edit", str(num), "--repo", REPO, "--body-file", tmp)
            os.unlink(tmp)
            print(f"Issue #{num}: updated anchor to {anchor}")

    print("\nDone.")


if __name__ == "__main__":
    main()

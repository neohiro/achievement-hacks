"""Verify markdown links resolve: both relative paths and in-document anchors.

Deliberately a narrow linter, not a markdown parser. It checks the two failure
modes that matter for a docs repo:

1. A relative link pointing at a file that does not exist.
2. A link pointing at a heading anchor that does not exist. GitHub resolves an
   unknown anchor to the top of the page silently, so this breakage is otherwise
   invisible — two such anchors existed in ``SECURITY.md`` when anchor checking
   was added.

Reference-style links (``[text][ref]``) and inline HTML hrefs are not inspected.

One trap worth naming: this script used to call ``sys.exit()`` at module level,
which meant that importing it would terminate the interpreter. That is harmless
today only because unittest's default discovery pattern is ``test*.py`` and this
file does not match. It is wrapped in ``main()`` so the pattern can change
without consequence.

It resolves the repo as the parent of this file's directory. A copy of this
script placed anywhere else will scan the wrong tree and report a confident
false pass — which is exactly what happened during development.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)

# Targets may contain spaces (e.g. "my file.md"), so the character class excludes
# only the closing paren. An optional "title" suffix is stripped below.
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

SKIP_PREFIX = ("http://", "https://", "mailto:", "/")
# GitHub web routes, not filesystem paths. './issues/1' resolves on github.com but
# has no local counterpart, so it is not a broken relative link.
WEB_ROUTES = ("./issues", "./pull", "./labels", "./milestones", "./wiki", "./actions")

FENCE_RE = re.compile(r"^\s*(```|~~~)")
ATX_HEADING_RE = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")


# A markdown link title is only recognised when quoted or parenthesised.
# "path.md \"Title\"" -> "path.md". An *unquoted* target containing spaces is
# malformed markdown and must not be silently truncated at the first space,
# which would resolve a path that does not exist and report a false positive.
TITLE_RE = re.compile(r"^(?P<dest>.*?)\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\))$")


def parse_target(raw: str) -> tuple[str, bool]:
    """Split a raw link destination into (target, looks_malformed).

    ``looks_malformed`` is True when the destination has unquoted whitespace,
    which CommonMark does not permit for a bare destination.
    """
    text = raw.strip()
    match = TITLE_RE.match(text)
    if match and match.group("dest").strip():
        text = match.group("dest").strip()
    malformed = " " in text
    if text.startswith("<") and ">" in text:
        text = text[1 : text.index(">")]
        malformed = False
    return text, malformed


def strip_fenced_blocks(text: str) -> str:
    """Blank out fenced code blocks, keeping every line in place.

    ``headings()`` already skips fences so a ``#`` comment inside a shell snippet
    is not read as a heading. The link scanners did not, and that turned into a
    real failure rather than a theoretical one.

    ``_achievements/starstruck/README.md`` shows an *example* of the cross-link a
    contributor is supposed to add, inside a ```bash fence::

        # see also [neohiro/your-best-repo](...)"

    The ``(...)`` is prose standing in for "your repo URL", not a link. The
    scanner read it as one and resolved it against the filesystem, where it does
    not exist, so CI failed on a placeholder that was never meant to resolve.

    The failure was also platform-dependent, which is why it passed review and
    then failed in CI rather than the reverse. On Linux
    ``_achievements/starstruck/...`` is simply absent and the check reports
    BROKEN. On Windows a path component cannot end in a dot - the filesystem
    strips trailing dots - so ``os.path.exists`` answers True for a path that
    cannot actually be opened, and the check passes. A linter whose verdict
    flips on the host OS is not one to trust on either platform.

    Fenced lines are replaced with empty strings rather than deleted so a
    reported line number still points at the right line, and the fence markers
    themselves are kept so an unbalanced fence toggles exactly as it did before.
    """
    out = []
    fence: str | None = None
    for line in text.splitlines():
        match = FENCE_RE.match(line)
        if fence is None:
            out.append(line)
            if match:
                fence = match.group(1)
            continue
        if match and match.group(1) == fence:
            fence = None
            out.append(line)
        else:
            out.append("")
    return "\n".join(out)


def iter_relative_links(text: str):
    """Yield (target, malformed) for links that are neither external nor anchors."""
    for raw in LINK_RE.findall(strip_fenced_blocks(text)):
        target, malformed = parse_target(raw)
        target = target.split("#", 1)[0]
        if not target:
            continue
        if target.startswith(SKIP_PREFIX):
            continue
        if target.startswith(WEB_ROUTES):
            continue
        yield target, malformed


def iter_fragments(text: str):
    """Yield (path_part, fragment) for every link carrying an anchor.

    Fragments used to be stripped and ignored, which meant a link could point at
    a heading that does not exist and still be reported as fine. GitHub resolves
    these silently to the top of the page, so the breakage is easy to miss.
    """
    for raw in LINK_RE.findall(strip_fenced_blocks(text)):
        target, _malformed = parse_target(raw)
        path_part, _, frag = target.partition("#")
        if not frag:
            continue
        if path_part.startswith(("http://", "https://", "mailto:")):
            continue
        if path_part.startswith(WEB_ROUTES):
            continue
        yield path_part, frag


def slugify(text: str) -> str:
    """GitHub's heading-anchor algorithm.

    Lowercase, drop everything that is not a word character, space, or hyphen,
    then turn spaces into hyphens. Note that punctuation is removed but the
    spaces around it survive, so "Brain — Abuse" yields a double hyphen while
    "Brain - Abuse" yields a triple one.
    """
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"\s", "-", text)


def headings(text: str) -> set[str]:
    """Collect anchors for ATX headings, ignoring anything inside a code fence.

    A ``#`` comment line inside a fenced block is not a heading, and treating it
    as one would produce a large set of phantom valid anchors.
    """
    anchors: set[str] = set()
    in_fence = False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = ATX_HEADING_RE.match(line)
        if match:
            anchors.add(slugify(match.group(1)))
    return anchors


def main() -> int:
    checked = 0
    fragments = 0
    broken: list[str] = []
    suspect: list[str] = []
    anchor_cache: dict[str, set[str] | None] = {}

    def anchors_for(path: str) -> set[str] | None:
        if path not in anchor_cache:
            try:
                with open(path, encoding="utf-8") as fh:
                    anchor_cache[path] = headings(fh.read())
            except OSError:
                anchor_cache[path] = None
        return anchor_cache[path]

    for dirpath, dirnames, filenames in os.walk(REPO):
        dirnames[:] = [d for d in dirnames if d not in {".git", "__pycache__", ".pytest_cache"}]
        for name in sorted(filenames):
            if not name.endswith(".md"):
                continue
            md = os.path.join(dirpath, name)
            with open(md, encoding="utf-8") as fh:
                text = fh.read()
            rel = os.path.relpath(md, REPO).replace("\\", "/")

            for target, malformed in iter_relative_links(text):
                checked += 1
                if malformed:
                    # Resolving a truncated path would manufacture a false
                    # positive, so report the syntax instead.
                    suspect.append(f"{rel}: unquoted space in link target {target!r}")
                    continue
                resolved = os.path.normpath(os.path.join(dirpath, target))
                if not os.path.exists(resolved):
                    broken.append(f"{rel}: {target}")

            for path_part, frag in iter_fragments(text):
                fragments += 1
                resolved = (
                    os.path.normpath(os.path.join(dirpath, path_part))
                    if path_part
                    else os.path.normpath(md)
                )
                anchors = anchors_for(resolved)
                label = f"{rel} -> {path_part}#{frag}" if path_part else f"{rel} -> #{frag}"
                if anchors is None:
                    broken.append(f"{label} (target file not found)")
                elif frag.lower() not in anchors:
                    broken.append(f"{label} (no such heading)")

    print(f"checked {checked} relative links, {fragments} in-document anchors")
    for entry in broken:
        print(f"  BROKEN {entry}")
    for entry in suspect:
        print(f"  SUSPECT {entry}")
    problems = len(broken) + len(suspect)
    print(f"{problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

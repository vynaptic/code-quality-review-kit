#!/usr/bin/env python3
"""Install repository review guidance without replacing existing project files."""

import argparse
from pathlib import Path
import sys


SOURCE = Path(__file__).resolve().parents[1] / "repo"
GUIDANCE = {Path(name) for name in ("AGENTS.md", "CLAUDE.md", "REVIEW.md")}
OVERRIDES = Path(".agents/review-overrides.md")
START = b"<!-- code-quality-review-kit:start -->"
END = b"<!-- code-quality-review-kit:end -->"


def plan_install(target):
    """Check the entire destination before adding assets or appending guidance."""
    if not (SOURCE / ".agents/skills/strict-code-review/SKILL.md").is_file():
        raise ValueError("Incomplete kit: canonical skill is missing under " + str(SOURCE))
    changes = []
    conflicts = set()
    for source in sorted(SOURCE.rglob("*")):
        if not source.is_file() or "__pycache__" in source.parts or source.suffix == ".pyc":
            continue
        relative = source.relative_to(SOURCE)
        destination = target / relative
        parents = [target] + [target / parent for parent in reversed(relative.parents) if parent != Path(".")]
        blocked = False
        for parent in parents:
            if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                conflicts.add(str(parent))
                blocked = True
                break
        if blocked:
            continue
        if destination.is_symlink() or (destination.exists() and not destination.is_file()):
            conflicts.add(str(destination))
            continue
        incoming = source.read_bytes()
        if not destination.exists():
            changes.append((destination, incoming, False))
            continue
        if relative == OVERRIDES:
            continue
        existing = destination.read_bytes()
        if relative in GUIDANCE:
            starts, ends = existing.count(START), existing.count(END)
            if starts == 1 and ends == 1 and existing.index(START) < existing.index(END):
                continue
            if starts or ends:
                conflicts.add(str(destination) + " (incomplete or repeated kit markers)")
            else:
                separator = b"\n\n" if existing else b""
                changes.append((destination, separator + incoming, True))
        elif existing != incoming:
            conflicts.add(str(destination))
    if conflicts:
        raise ValueError("Conflicts; no files changed:\n" + "\n".join(sorted(conflicts)))
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="repository root (created if missing)")
    args = parser.parse_args()
    target = args.target.expanduser().absolute()
    try:
        changes = plan_install(target)
        for destination, content, append in changes:
            destination.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation refuses a file added after preflight; append never truncates guidance.
            with destination.open("ab" if append else "xb") as output:
                output.write(content)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print("Installed review kit in {} ({} files added or appended).".format(target, len(changes)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

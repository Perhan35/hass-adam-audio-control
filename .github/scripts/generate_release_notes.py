#!/usr/bin/env python3
"""Build categorized release notes from conventional commits since the last v* tag."""

import os
import re
import subprocess
import sys

CATEGORIES = {
    "feat": ("Features", "✨"),
    "fix": ("Fixes", "\U0001F41B"),
    "chore": ("Chores", "\U0001F9F9"),
    "docs": ("Docs", "\U0001F4DD"),
    "doc": ("Docs", "\U0001F4DD"),
}

COMMIT_RE = re.compile(r"^(?P<type>[a-zA-Z]+)(\([^)]*\))?!?:\s*(?P<desc>.+)$")


def run(*args: str) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip()


def previous_tag(current_tag: str) -> str | None:
    tags = run("git", "tag", "-l", "v*", "--sort=-v:refname").splitlines()
    if current_tag not in tags:
        tags = sorted({current_tag, *tags}, reverse=True)
    idx = tags.index(current_tag)
    return tags[idx + 1] if idx + 1 < len(tags) else None


def commit_subjects(commit_range: str) -> list[str]:
    output = run("git", "log", commit_range, "--no-merges", "--pretty=format:%s")
    return [line for line in output.splitlines() if line.strip()]


def build_notes(current_tag: str, prev_tag: str | None, repo: str) -> str:
    commit_range = f"{prev_tag}..{current_tag}" if prev_tag else current_tag
    buckets: dict[str, list[str]] = {name: [] for name, _ in CATEGORIES.values()}
    other: list[str] = []

    for subject in commit_subjects(commit_range):
        match = COMMIT_RE.match(subject)
        if not match:
            other.append(subject[0].upper() + subject[1:] if subject else subject)
            continue
        category = CATEGORIES.get(match.group("type").lower())
        desc = match.group("desc").strip()
        entry = desc[0].upper() + desc[1:] if desc else desc
        if not category:
            other.append(entry)
            continue
        name, _ = category
        buckets[name].append(entry)

    sections = []
    for name, emoji in dict.fromkeys(CATEGORIES.values()):
        entries = buckets[name]
        if not entries:
            continue
        lines = "\n".join(f"- {entry}" for entry in entries)
        sections.append(f"### {emoji} {name}\n\n{lines}")

    if other:
        lines = "\n".join(f"- {entry}" for entry in other)
        sections.append(f"### Other noteworthy changes:\n\n{lines}")

    body = "## What's Changed\n\n" + "\n\n".join(sections) if sections else "## What's Changed"
    if prev_tag:
        body += f"\n\n**Full Changelog**: https://github.com/{repo}/compare/{prev_tag}...{current_tag}"
    return body


def main() -> None:
    current_tag = os.environ["CURRENT_TAG"]
    repo = os.environ["GITHUB_REPOSITORY"]
    prev_tag = previous_tag(current_tag)
    notes = build_notes(current_tag, prev_tag, repo)
    print(notes)


if __name__ == "__main__":
    main()

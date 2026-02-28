#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[1]
INIT_FILE = ROOT / "pubsub_publisher" / "__init__.py"
SPEC_FILE = ROOT / "PubSub Publisher.spec"
CHANGELOG_FILE = ROOT / "CHANGELOG.md"

VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
INIT_VERSION_PATTERN = re.compile(r'^(__version__\s*=\s*")[^"]+(")', re.MULTILINE)
SPEC_VERSION_PATTERN = re.compile(r'^(APP_VERSION\s*=\s*")[^"]+(")', re.MULTILINE)

CHANGELOG_HEADER = """# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

"""


def run_git(args: List[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def validate_version(version: str) -> None:
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError("Version must use semantic format: MAJOR.MINOR.PATCH (for example, 1.2.3)")


def update_version_file(path: Path, pattern: re.Pattern[str], version: str) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = pattern.subn(rf"\g<1>{version}\g<2>", text, count=1)
    if count != 1:
        raise RuntimeError(f"Could not update version in {path}")
    path.write_text(updated, encoding="utf-8")


def latest_tag() -> str | None:
    output = run_git(["tag", "--list", "v*", "--sort=-version:refname"])
    tags = [line.strip() for line in output.splitlines() if line.strip()]
    return tags[0] if tags else None


def commit_subjects_since(tag: str | None) -> List[str]:
    if tag:
        revision_range = f"{tag}..HEAD"
    else:
        revision_range = "HEAD"

    output = run_git(["log", "--pretty=format:%s", revision_range])
    return [line.strip() for line in output.splitlines() if line.strip()]


def classify(subject: str) -> str:
    lowered = subject.lower().strip()
    match = re.match(r"^([a-z]+)(\([^)]+\))?!?:", lowered)
    token = match.group(1) if match else lowered.split(" ", 1)[0]

    if token in {"feat", "add", "added", "new", "introduce", "introduced"}:
        return "added"
    if token in {"fix", "fixed", "bugfix", "hotfix"}:
        return "fixed"
    return "changed"


def render_changelog_entry(version: str, subjects: List[str], entry_date: str) -> str:
    groups: Dict[str, List[str]] = {"added": [], "changed": [], "fixed": []}
    for subject in subjects:
        groups[classify(subject)].append(subject)

    lines = [f"## [{version}] - {entry_date}", ""]
    if groups["added"]:
        lines.append("### Added")
        lines.extend([f"- {item}" for item in groups["added"]])
        lines.append("")
    if groups["changed"]:
        lines.append("### Changed")
        lines.extend([f"- {item}" for item in groups["changed"]])
        lines.append("")
    if groups["fixed"]:
        lines.append("### Fixed")
        lines.extend([f"- {item}" for item in groups["fixed"]])
        lines.append("")

    if not any(groups.values()):
        lines.append("### Changed")
        lines.append("- No user-facing changes recorded.")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n\n"


def prepend_changelog_entry(version: str, entry: str) -> None:
    if CHANGELOG_FILE.exists():
        content = CHANGELOG_FILE.read_text(encoding="utf-8")
    else:
        content = CHANGELOG_HEADER

    heading = f"## [{version}]"
    if heading in content:
        raise RuntimeError(f"CHANGELOG already contains an entry for version {version}")

    first_entry = re.search(r"^## \[", content, flags=re.MULTILINE)
    if first_entry:
        new_content = f"{content[:first_entry.start()]}{entry}{content[first_entry.start():]}"
    else:
        sep = "" if content.endswith("\n\n") else "\n"
        new_content = f"{content}{sep}{entry}"

    CHANGELOG_FILE.write_text(new_content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare a new release by updating version files and creating a CHANGELOG entry."
    )
    parser.add_argument("version", help="Release version (for example, 1.2.3)")
    parser.add_argument(
        "--date",
        dest="entry_date",
        default=date.today().isoformat(),
        help="Release date in YYYY-MM-DD format (default: today)",
    )
    args = parser.parse_args()

    try:
        validate_version(args.version)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        update_version_file(INIT_FILE, INIT_VERSION_PATTERN, args.version)
        update_version_file(SPEC_FILE, SPEC_VERSION_PATTERN, args.version)

        previous = latest_tag()
        subjects = commit_subjects_since(previous)
        entry = render_changelog_entry(args.version, subjects, args.entry_date)
        prepend_changelog_entry(args.version, entry)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Prepared release {args.version}")
    if previous:
        print(f"Collected commits since {previous}")
    else:
        print("Collected commits from repository history (no previous tags found)")
    print("")
    print("Next steps:")
    print(f"  1) git add {INIT_FILE.relative_to(ROOT)} \"{SPEC_FILE.name}\" {CHANGELOG_FILE.relative_to(ROOT)}")
    print(f"  2) git commit -m \"Release {args.version}\"")
    print(f"  3) git tag v{args.version}")
    print("  4) git push origin <branch> --follow-tags")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


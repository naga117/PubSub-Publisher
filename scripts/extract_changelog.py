#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHANGELOG_FILE = ROOT / "CHANGELOG.md"
VERSION_HEADING = re.compile(r"^## \[(?P<version>[^\]]+)\](?:\s*-\s*.+)?$", re.MULTILINE)


def extract_version_notes(version: str) -> str:
    if not CHANGELOG_FILE.exists():
        raise FileNotFoundError("CHANGELOG.md does not exist")

    content = CHANGELOG_FILE.read_text(encoding="utf-8")
    matches = list(VERSION_HEADING.finditer(content))
    for index, match in enumerate(matches):
        if match.group("version") != version:
            continue

        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        section = content[start:end].strip()
        if not section:
            return "No release notes were recorded for this version."
        return section + "\n"

    raise ValueError(f"Version {version} was not found in CHANGELOG.md")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract release notes for one version from CHANGELOG.md.")
    parser.add_argument("version", help="Version number, without a leading v (for example, 1.2.3)")
    args = parser.parse_args()

    try:
        notes = extract_version_notes(args.version)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


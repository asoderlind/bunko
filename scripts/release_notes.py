"""Validate a stable release tag and extract its changelog section."""
import re
import sys
from pathlib import Path


def release_notes(tag: str, changelog: str) -> str:
    if not re.fullmatch(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", tag):
        raise ValueError("Release tags must use vMAJOR.MINOR.PATCH (no leading zeros)")
    version = tag[1:]
    sections = re.split(r"^## +", changelog, flags=re.MULTILINE)[1:]
    matches = []
    for section in sections:
        heading, _, body = section.partition("\n")
        if heading.strip() == version or heading.startswith(version + " — "):
            matches.append(body.strip())
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one '## {version}' changelog section")
    if not matches[0]:
        raise ValueError(f"Changelog section for {version} is empty")
    return matches[0] + "\n"


if __name__ == "__main__":
    try:
        print(release_notes(sys.argv[1], Path("changelog.md").read_text()), end="")
    except (ValueError, IndexError) as error:
        sys.exit(str(error))

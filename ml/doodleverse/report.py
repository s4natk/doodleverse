"""Rewrite one `## ` section of a markdown file and leave the others alone."""

from __future__ import annotations

import re
from pathlib import Path

_HEADING = re.compile(r"^## (.+)$", re.MULTILINE)


def split_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Return the text before the first `## ` heading and (heading, block) pairs."""

    matches = list(_HEADING.finditer(text))
    if not matches:
        return text, []
    blocks = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks.append((match.group(1).strip(), text[match.start() : end].rstrip() + "\n"))
    return text[: matches[0].start()], blocks


def join_sections(preamble: str, blocks: list[str]) -> str:
    head = preamble.rstrip() + "\n\n" if preamble.strip() else ""
    return head + "\n".join(block.rstrip() + "\n" for block in blocks)


def upsert_section(path: Path, heading: str, block: str) -> None:
    """Replace the `## heading` block in place, or append it when it is new."""

    text = path.read_text(encoding="utf-8") if path.exists() else ""
    preamble, blocks = split_sections(text)
    replaced = False
    updated = []
    for name, existing in blocks:
        if name == heading:
            updated.append(block)
            replaced = True
        else:
            updated.append(existing)
    if not replaced:
        updated.append(block)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(join_sections(preamble, updated), encoding="utf-8")

"""Parser for NFHS rulebook markdown files."""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class HeadingInfo:
    """Information extracted from a heading line."""
    level: int
    heading_type: str  # 'rule', 'section', 'article', 'other'
    title: Optional[str] = None
    rule_num: Optional[str] = None
    section_num: Optional[str] = None
    article_num: Optional[str] = None


def parse_heading(line: str) -> Optional[HeadingInfo]:
    """
    Parse a markdown heading line and extract structured info.

    Returns None if line is not a heading.
    """
    # Match markdown heading
    heading_match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
    if not heading_match:
        return None

    level = len(heading_match.group(1))
    text = heading_match.group(2).strip()

    # Try to match Rule heading: "Rule N – Title" or "Rule N - Title"
    rule_match = re.match(r'^Rule\s+(\d+)\s*[–-]\s*(.+)$', text, re.IGNORECASE)
    if rule_match:
        return HeadingInfo(
            level=level,
            heading_type='rule',
            rule_num=rule_match.group(1),
            title=rule_match.group(2).strip()
        )

    # Try to match Section heading: "Section N – Title" or "Section N - Title"
    section_match = re.match(r'^Section\s+(\d+)\s*[–-]\s*(.+)$', text, re.IGNORECASE)
    if section_match:
        return HeadingInfo(
            level=level,
            heading_type='section',
            section_num=section_match.group(1),
            title=section_match.group(2).strip()
        )

    # Try to match Article heading: "Article N" or "Article N."
    article_match = re.match(r'^Article\s+(\d+)\.?(?:\s|$)', text, re.IGNORECASE)
    if article_match:
        return HeadingInfo(
            level=level,
            heading_type='article',
            article_num=article_match.group(1),
            title=text
        )

    # Other heading
    return HeadingInfo(
        level=level,
        heading_type='other',
        title=text
    )


@dataclass
class PenaltyScope:
    """Scope information for a PENALTY/PENALTIES block."""
    scope_type: str  # 'section', 'sections', 'article', 'inline'
    scope_values: list[str]  # section/article numbers
    raw_line: str


def parse_penalty_scope(line: str) -> Optional[PenaltyScope]:
    """
    Parse a PENALTY: or PENALTIES: line and extract scope.

    Returns None if line is not a penalty line.
    """
    # Match PENALTY: or PENALTIES:
    penalty_match = re.match(r'^PENALT(?:Y|IES):\s*(.*)$', line.strip())
    if not penalty_match:
        return None

    rest = penalty_match.group(1)

    # Try to match (Section N)
    section_match = re.match(r'^\(Section\s+(\d+)\)', rest)
    if section_match:
        return PenaltyScope(
            scope_type='section',
            scope_values=[section_match.group(1)],
            raw_line=line
        )

    # Try to match (Sections N-M)
    sections_match = re.match(r'^\(Sections\s+(\d+)-(\d+)\)', rest)
    if sections_match:
        return PenaltyScope(
            scope_type='sections',
            scope_values=[sections_match.group(1), sections_match.group(2)],
            raw_line=line
        )

    # Try to match (Art. N) or (Article N)
    article_match = re.match(r'^\(Art(?:icle)?\.?\s+(\d+)\)', rest)
    if article_match:
        return PenaltyScope(
            scope_type='article',
            scope_values=[article_match.group(1)],
            raw_line=line
        )

    # No scope specified - inline penalty
    return PenaltyScope(
        scope_type='inline',
        scope_values=[],
        raw_line=line
    )

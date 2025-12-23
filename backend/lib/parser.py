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

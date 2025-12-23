import pytest
from lib.parser import parse_heading, HeadingInfo


def test_parse_rule_heading():
    line = "# Rule 1 – Court and Equipment"
    result = parse_heading(line)

    assert result is not None
    assert result.level == 1
    assert result.rule_num == "1"
    assert result.title == "Court and Equipment"
    assert result.heading_type == "rule"


def test_parse_section_heading():
    line = "## Section 2 – THROW-IN PROVISIONS"
    result = parse_heading(line)

    assert result is not None
    assert result.level == 2
    assert result.section_num == "2"
    assert result.title == "THROW-IN PROVISIONS"
    assert result.heading_type == "section"


def test_parse_article_heading():
    line = "### Article 1"
    result = parse_heading(line)

    assert result is not None
    assert result.level == 3
    assert result.article_num == "1"
    assert result.heading_type == "article"


def test_parse_non_heading():
    line = "This is just regular text."
    result = parse_heading(line)

    assert result is None

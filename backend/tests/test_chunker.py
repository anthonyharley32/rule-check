import json
import pytest
from lib.chunker import RulesBookChunker, CasebookChunker, ManualChunker, Chunk


SAMPLE_RULES_MD = '''
# Rule 9 – Violations and Penalties

## Section 1 – FREE THROW

### Article 1

The free throw starts when the ball is placed at the disposal of the free thrower.

### Article 2

The free throw ends when the try is successful, when it is certain the try will not be successful.

PENALTIES: (Section 1)
1. If the first violation is by the free thrower, no point can be scored.
2. If the violation is by the opponent, substitute throw shall be attempted.

## Section 2 – THROW-IN

### Article 1

The thrower shall not leave the designated spot.

PENALTY: (Section 2) The ball becomes dead when the violation occurs.
'''


def test_chunk_rules_book_extracts_articles():
    chunker = RulesBookChunker()
    chunks = chunker.chunk(SAMPLE_RULES_MD)

    # Should have 3 articles
    article_chunks = [c for c in chunks if c.type == 'rule_article']
    assert len(article_chunks) == 3


def test_chunk_rules_book_attaches_penalties():
    chunker = RulesBookChunker()
    chunks = chunker.chunk(SAMPLE_RULES_MD)

    # Section 1 articles should have penalty attached
    section1_chunks = [c for c in chunks if c.section_ref == "Rule 9-1"]
    for chunk in section1_chunks:
        assert chunk.penalty_text is not None
        assert "If the first violation" in chunk.penalty_text


def test_chunk_rules_book_sets_refs():
    chunker = RulesBookChunker()
    chunks = chunker.chunk(SAMPLE_RULES_MD)

    # Find first article
    article1 = next(c for c in chunks if "free throw starts" in c.content)

    assert article1.source_ref == "Rule 9-1-1"
    assert article1.section_ref == "Rule 9-1"
    assert article1.rule_ref == "Rule 9"


def test_chunk_rules_book_includes_context_in_content():
    chunker = RulesBookChunker()
    chunks = chunker.chunk(SAMPLE_RULES_MD)

    article1 = next(c for c in chunks if "free throw starts" in c.content)

    # Content should have context prefix
    assert "[Rule 9: Violations and Penalties - Section 1: FREE THROW]" in article1.content


def test_chunk_rules_book_stores_json_title():
    chunker = RulesBookChunker()
    chunks = chunker.chunk(SAMPLE_RULES_MD)

    article1 = next(c for c in chunks if "free throw starts" in c.content)

    # Title should be valid JSON with rule and section
    title_data = json.loads(article1.title)
    assert title_data["rule"] == "Violations and Penalties"
    assert title_data["section"] == "FREE THROW"


SAMPLE_CASEBOOK_MD = '''
4.6.1 SITUATION:
During a fast break, A1 drives to the basket and attempts a layup. As the ball contacts the backboard and bounces toward the ring, B1 slaps the backboard forcefully, causing vibration.

**RULING:**
This is basket interference by B1. Award two points to Team A.

**COMMENT:**
This type of play is now classified as basket interference. (4-6-1a, 4-6-1b, 9-11-1)

4.22.1 SITUATION:
Late in the fourth quarter, A1 attempts a layup. The ball is on its downward flight.

**RULING:**
This is goaltending by the defensive player. Award two points to Team A.

**COMMENT:**
This rule change clarifies that goaltending can only be committed by defensive players.
'''


def test_chunk_casebook_extracts_situations():
    chunker = CasebookChunker()
    chunks = chunker.chunk(SAMPLE_CASEBOOK_MD)

    assert len(chunks) == 2


def test_chunk_casebook_includes_ruling_and_comment():
    chunker = CasebookChunker()
    chunks = chunker.chunk(SAMPLE_CASEBOOK_MD)

    chunk = chunks[0]
    assert "SITUATION" in chunk.content or "fast break" in chunk.content
    assert "RULING" in chunk.content or "basket interference" in chunk.content
    assert "COMMENT" in chunk.content or "classified as" in chunk.content


def test_chunk_casebook_sets_refs():
    chunker = CasebookChunker()
    chunks = chunker.chunk(SAMPLE_CASEBOOK_MD)

    chunk = chunks[0]
    assert chunk.source_ref == "4.6.1"
    assert chunk.rule_ref == "Rule 4-6-1"
    assert chunk.type == "situation"
    assert chunk.book == "casebook"


SAMPLE_MANUAL_MD = '''
## 1.2 Personal Characteristics

### 1.2.1 Conduct

Every member of the officiating profession carries a responsibility to act in a manner becoming of a professional person.

### 1.2.2 Communication

Communication is vital to being a successful official. Understanding non-verbal and verbal communication sends a message to players, coaches and fans.

## 1.3 Game Preparation

### 1.3.1 Equipment

Officials should ensure they have all required equipment before the game.
'''


def test_chunk_manual_by_subsections():
    chunker = ManualChunker()
    chunks = chunker.chunk(SAMPLE_MANUAL_MD)

    # Should chunk by ### subsections
    assert len(chunks) == 3


def test_chunk_manual_sets_refs():
    chunker = ManualChunker()
    chunks = chunker.chunk(SAMPLE_MANUAL_MD)

    chunk = chunks[0]
    assert chunk.source_ref == "1.2.1"
    assert chunk.title == "Conduct"
    assert chunk.type == "manual"
    assert chunk.book == "manual"

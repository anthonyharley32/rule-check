# NFHS Basketball Rules Chat App Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a chat application that answers NFHS basketball rules questions with Perplexity-style citations linking to source material from the rules book, casebook, and officials manual.

**Architecture:** RAG-based chat using Supabase pgvector for semantic search across three rulebooks. Chunks are retrieved per-book (top N from each), combined and passed to Gemini 2.5 Flash via OpenRouter. LLM outputs text with `[N]` citation markers, frontend parses and renders as clickable buttons.

**Tech Stack:** React + Vite + TypeScript (frontend), Python serverless functions (backend), Supabase (Postgres + pgvector), LangChain + LangSmith, Gemini 2.5 Flash via OpenRouter.

---

## Phase 1: Project Setup

### Task 1.1: Initialize Frontend Project

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/index.css`

**Step 1: Create frontend directory and initialize Vite project**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
npm create vite@latest frontend -- --template react-ts
```

Expected: Scaffolding for frontend... Done.

**Step 2: Install frontend dependencies**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/frontend"
npm install
npm install @supabase/supabase-js tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Expected: added X packages

**Step 3: Configure Tailwind**

Update `frontend/tailwind.config.js`:
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

Update `frontend/src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

**Step 4: Verify frontend runs**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/frontend"
npm run dev
```

Expected: VITE ready at http://localhost:5173

**Step 5: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git init
git add frontend/
git commit -m "feat: initialize frontend with Vite + React + TypeScript + Tailwind"
```

---

### Task 1.2: Initialize Backend Project

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/functions/__init__.py`
- Create: `backend/lib/__init__.py`

**Step 1: Create backend directory structure**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
mkdir -p backend/functions backend/lib backend/tests
```

**Step 2: Create requirements.txt**

Create `backend/requirements.txt`:
```text
langchain>=0.3.0
langchain-community>=0.3.0
langchain-openai>=0.2.0
langsmith>=0.1.0
supabase>=2.0.0
python-dotenv>=1.0.0
tiktoken>=0.5.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
```

**Step 3: Create pyproject.toml**

Create `backend/pyproject.toml`:
```toml
[project]
name = "nfhs-rules-backend"
version = "0.1.0"
description = "Backend for NFHS Basketball Rules Chat App"
requires-python = ">=3.11"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 4: Create .env.example**

Create `backend/.env.example`:
```bash
SUPABASE_URL=your_supabase_url
SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxx
SUPABASE_SECRET_KEY=sb_secret_xxx
OPENROUTER_API_KEY=your_openrouter_key
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=nfhs-rules-chat
```

**Step 5: Create Python virtual environment**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Expected: Successfully installed langchain...

**Step 6: Create __init__.py files**

Create `backend/functions/__init__.py`:
```python
"""Serverless function handlers."""
```

Create `backend/lib/__init__.py`:
```python
"""Library modules for parsing, chunking, and embeddings."""
```

**Step 7: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add backend/
git commit -m "feat: initialize backend with Python dependencies"
```

---

### Task 1.3: Setup Supabase Project

**Files:**
- Create: `supabase/migrations/001_create_chunks.sql`
- Create: `supabase/config.toml`

**Step 1: Create supabase directory**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
mkdir -p supabase/migrations
```

**Step 2: Create migration for chunks table**

Create `supabase/migrations/001_create_chunks.sql`:
```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create chunks table
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding VECTOR(768),
    type TEXT NOT NULL CHECK (type IN ('rule_article', 'situation', 'ruling', 'emphasis', 'manual')),
    book TEXT NOT NULL CHECK (book IN ('rules', 'casebook', 'manual')),
    source_ref TEXT NOT NULL,
    section_ref TEXT,
    rule_ref TEXT,
    title TEXT,
    penalty_text TEXT,
    page_number INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for vector similarity search
CREATE INDEX chunks_embedding_idx ON chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create indexes for filtering
CREATE INDEX chunks_book_idx ON chunks (book);
CREATE INDEX chunks_type_idx ON chunks (type);
CREATE INDEX chunks_source_ref_idx ON chunks (source_ref);

-- Create function for similarity search
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding VECTOR(768),
    match_count INT DEFAULT 5,
    filter_book TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    type TEXT,
    book TEXT,
    source_ref TEXT,
    section_ref TEXT,
    rule_ref TEXT,
    title TEXT,
    penalty_text TEXT,
    page_number INTEGER,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.content,
        c.type,
        c.book,
        c.source_ref,
        c.section_ref,
        c.rule_ref,
        c.title,
        c.penalty_text,
        c.page_number,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM chunks c
    WHERE (filter_book IS NULL OR c.book = filter_book)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

**Step 3: Create Supabase project (manual step)**

Note: Go to https://supabase.com and create a new project. Save the URL, publishable key, and secret key.

**Step 4: Apply migration via Supabase dashboard**

Note: Go to SQL Editor in Supabase dashboard and run the contents of `001_create_chunks.sql`.

**Step 5: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add supabase/
git commit -m "feat: add Supabase migration for chunks table with pgvector"
```

---

## Phase 2: Markdown Parser

### Task 2.1: Create Base Parser Module

**Files:**
- Create: `backend/lib/parser.py`
- Create: `backend/tests/test_parser.py`

**Step 1: Write failing test for heading extraction**

Create `backend/tests/test_parser.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
PYTHONPATH=. pytest tests/test_parser.py -v
```

Expected: FAILED - ModuleNotFoundError: No module named 'lib.parser'

**Step 3: Write minimal implementation**

Create `backend/lib/parser.py`:
```python
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
```

**Step 4: Run test to verify it passes**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
PYTHONPATH=. pytest tests/test_parser.py -v
```

Expected: 4 passed

**Step 5: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add backend/lib/parser.py backend/tests/test_parser.py
git commit -m "feat: add heading parser for rulebook markdown"
```

---

### Task 2.2: Add Penalty Pattern Parsing

**Files:**
- Modify: `backend/lib/parser.py`
- Modify: `backend/tests/test_parser.py`

**Step 1: Write failing tests for penalty parsing**

Add to `backend/tests/test_parser.py`:
```python
from lib.parser import parse_penalty_scope, PenaltyScope


def test_parse_penalty_section():
    line = "PENALTIES: (Section 1)"
    result = parse_penalty_scope(line)

    assert result is not None
    assert result.scope_type == "section"
    assert result.scope_values == ["1"]


def test_parse_penalty_multiple_sections():
    line = "PENALTIES: (Sections 11-12)"
    result = parse_penalty_scope(line)

    assert result is not None
    assert result.scope_type == "sections"
    assert result.scope_values == ["11", "12"]


def test_parse_penalty_article():
    line = "PENALTY: (Art. 10)"
    result = parse_penalty_scope(line)

    assert result is not None
    assert result.scope_type == "article"
    assert result.scope_values == ["10"]


def test_parse_penalty_no_scope():
    line = "PENALTY: The ball is dead when the violation occurs."
    result = parse_penalty_scope(line)

    assert result is not None
    assert result.scope_type == "inline"
    assert result.scope_values == []


def test_parse_non_penalty():
    line = "This is regular text."
    result = parse_penalty_scope(line)

    assert result is None
```

**Step 2: Run test to verify it fails**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
PYTHONPATH=. pytest tests/test_parser.py::test_parse_penalty_section -v
```

Expected: FAILED - ImportError: cannot import name 'parse_penalty_scope'

**Step 3: Add penalty parsing implementation**

Add to `backend/lib/parser.py`:
```python
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
```

**Step 4: Run test to verify it passes**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
PYTHONPATH=. pytest tests/test_parser.py -v
```

Expected: 9 passed

**Step 5: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add backend/lib/parser.py backend/tests/test_parser.py
git commit -m "feat: add penalty scope parsing for PENALTY/PENALTIES blocks"
```

---

### Task 2.3: Add Casebook Situation Parsing

**Files:**
- Modify: `backend/lib/parser.py`
- Modify: `backend/tests/test_parser.py`

**Step 1: Write failing tests for situation parsing**

Add to `backend/tests/test_parser.py`:
```python
from lib.parser import parse_situation, SituationInfo


def test_parse_situation():
    line = "4.6.1 SITUATION:"
    result = parse_situation(line)

    assert result is not None
    assert result.ref == "4.6.1"
    assert result.rule == "4"
    assert result.section == "6"
    assert result.article == "1"


def test_parse_situation_with_suffix():
    line = "1.13.2 SITUATION A :"
    result = parse_situation(line)

    assert result is not None
    assert result.ref == "1.13.2"
    assert result.suffix == "A"


def test_parse_non_situation():
    line = "This is not a situation."
    result = parse_situation(line)

    assert result is None
```

**Step 2: Run test to verify it fails**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
PYTHONPATH=. pytest tests/test_parser.py::test_parse_situation -v
```

Expected: FAILED - ImportError: cannot import name 'parse_situation'

**Step 3: Add situation parsing implementation**

Add to `backend/lib/parser.py`:
```python
@dataclass
class SituationInfo:
    """Information extracted from a casebook situation header."""
    ref: str  # "4.6.1"
    rule: str
    section: str
    article: str
    suffix: Optional[str] = None  # "A", "B", etc.


def parse_situation(line: str) -> Optional[SituationInfo]:
    """
    Parse a casebook SITUATION line.

    Matches patterns like:
    - "4.6.1 SITUATION:"
    - "1.13.2 SITUATION A :"

    Returns None if line is not a situation header.
    """
    # Match X.X.X SITUATION or X.X.X SITUATION A :
    match = re.match(
        r'^(\d+)\.(\d+)\.(\d+)\s+SITUATION\s*([A-Z])?\s*:',
        line.strip()
    )
    if not match:
        return None

    return SituationInfo(
        ref=f"{match.group(1)}.{match.group(2)}.{match.group(3)}",
        rule=match.group(1),
        section=match.group(2),
        article=match.group(3),
        suffix=match.group(4)
    )
```

**Step 4: Run test to verify it passes**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
PYTHONPATH=. pytest tests/test_parser.py -v
```

Expected: 12 passed

**Step 5: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add backend/lib/parser.py backend/tests/test_parser.py
git commit -m "feat: add casebook situation parsing"
```

---

## Phase 3: Chunking Logic

### Task 3.1: Create Chunker for Rules Book

**Files:**
- Create: `backend/lib/chunker.py`
- Create: `backend/tests/test_chunker.py`

**Step 1: Write failing test for rules book chunking**

Create `backend/tests/test_chunker.py`:
```python
import pytest
from lib.chunker import RulesBookChunker, Chunk


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
```

**Step 2: Run test to verify it fails**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
PYTHONPATH=. pytest tests/test_chunker.py -v
```

Expected: FAILED - ModuleNotFoundError: No module named 'lib.chunker'

**Step 3: Write chunker implementation**

Create `backend/lib/chunker.py`:
```python
"""Chunking logic for NFHS rulebooks."""

from dataclasses import dataclass, field
from typing import Optional
from .parser import parse_heading, parse_penalty_scope, parse_situation


@dataclass
class Chunk:
    """A chunk of content for embedding."""
    content: str
    type: str  # 'rule_article', 'situation', 'ruling', 'emphasis', 'manual'
    book: str  # 'rules', 'casebook', 'manual'
    source_ref: str  # "Rule 9-1-2" or "4.6.1"
    section_ref: Optional[str] = None
    rule_ref: Optional[str] = None
    title: Optional[str] = None
    penalty_text: Optional[str] = None
    page_number: Optional[int] = None


class RulesBookChunker:
    """Chunker for the NFHS Rules Book."""

    def __init__(self):
        self.current_rule: Optional[str] = None
        self.current_section: Optional[str] = None
        self.current_article: Optional[str] = None
        self.current_content: list[str] = []
        self.chunks: list[Chunk] = []
        self.pending_penalties: dict[str, str] = {}  # section_ref -> penalty_text

    def chunk(self, markdown: str) -> list[Chunk]:
        """Parse markdown and return list of chunks."""
        self.chunks = []
        self.current_rule = None
        self.current_section = None
        self.current_article = None
        self.current_content = []
        self.pending_penalties = {}

        lines = markdown.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check for heading
            heading = parse_heading(line)
            if heading:
                if heading.heading_type == 'rule':
                    self._flush_article()
                    self.current_rule = heading.rule_num
                    self.current_section = None
                    self.current_article = None
                elif heading.heading_type == 'section':
                    self._flush_article()
                    self.current_section = heading.section_num
                    self.current_article = None
                elif heading.heading_type == 'article':
                    self._flush_article()
                    self.current_article = heading.article_num
                i += 1
                continue

            # Check for penalty
            penalty = parse_penalty_scope(line)
            if penalty:
                # Collect full penalty text
                penalty_lines = [line]
                i += 1
                while i < len(lines) and lines[i].strip() and not parse_heading(lines[i]) and not parse_penalty_scope(lines[i]):
                    # Stop if we hit a new section/heading
                    if lines[i].strip().startswith('#'):
                        break
                    penalty_lines.append(lines[i])
                    i += 1

                penalty_text = '\n'.join(penalty_lines)

                # Determine scope and attach
                if penalty.scope_type == 'section' and self.current_rule:
                    section_num = penalty.scope_values[0] if penalty.scope_values else self.current_section
                    section_ref = f"Rule {self.current_rule}-{section_num}"
                    self.pending_penalties[section_ref] = penalty_text
                elif penalty.scope_type == 'sections' and self.current_rule:
                    start, end = int(penalty.scope_values[0]), int(penalty.scope_values[1])
                    for sec in range(start, end + 1):
                        section_ref = f"Rule {self.current_rule}-{sec}"
                        self.pending_penalties[section_ref] = penalty_text
                elif penalty.scope_type == 'inline':
                    # Attach to current article
                    if self.current_rule and self.current_section:
                        section_ref = f"Rule {self.current_rule}-{self.current_section}"
                        self.pending_penalties[section_ref] = penalty_text
                continue

            # Regular content line
            if self.current_article is not None:
                self.current_content.append(line)

            i += 1

        # Flush remaining
        self._flush_article()

        # Attach penalties to chunks
        self._attach_penalties()

        return self.chunks

    def _flush_article(self):
        """Save current article as a chunk."""
        if self.current_article is None or not self.current_content:
            self.current_content = []
            return

        content = '\n'.join(self.current_content).strip()
        if not content:
            self.current_content = []
            return

        source_ref = f"Rule {self.current_rule}-{self.current_section}-{self.current_article}"
        section_ref = f"Rule {self.current_rule}-{self.current_section}"
        rule_ref = f"Rule {self.current_rule}"

        self.chunks.append(Chunk(
            content=content,
            type='rule_article',
            book='rules',
            source_ref=source_ref,
            section_ref=section_ref,
            rule_ref=rule_ref
        ))

        self.current_content = []

    def _attach_penalties(self):
        """Attach penalty text to chunks based on section."""
        for chunk in self.chunks:
            if chunk.section_ref and chunk.section_ref in self.pending_penalties:
                chunk.penalty_text = self.pending_penalties[chunk.section_ref]
```

**Step 4: Run test to verify it passes**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
PYTHONPATH=. pytest tests/test_chunker.py -v
```

Expected: 3 passed

**Step 5: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add backend/lib/chunker.py backend/tests/test_chunker.py
git commit -m "feat: add rules book chunker with penalty attachment"
```

---

### Task 3.2: Create Chunker for Casebook

**Files:**
- Modify: `backend/lib/chunker.py`
- Modify: `backend/tests/test_chunker.py`

**Step 1: Write failing test for casebook chunking**

Add to `backend/tests/test_chunker.py`:
```python
from lib.chunker import CasebookChunker


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
```

**Step 2: Run test to verify it fails**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
PYTHONPATH=. pytest tests/test_chunker.py::test_chunk_casebook_extracts_situations -v
```

Expected: FAILED - ImportError: cannot import name 'CasebookChunker'

**Step 3: Add casebook chunker implementation**

Add to `backend/lib/chunker.py`:
```python
class CasebookChunker:
    """Chunker for the NFHS Casebook."""

    def chunk(self, markdown: str) -> list[Chunk]:
        """Parse casebook markdown and return list of chunks."""
        chunks = []
        lines = markdown.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check for situation header
            situation = parse_situation(line)
            if situation:
                # Collect entire situation block (situation + ruling + comment)
                content_lines = [line]
                i += 1

                # Continue until next situation or end
                while i < len(lines):
                    next_line = lines[i]
                    # Check if next situation starts
                    if parse_situation(next_line):
                        break
                    content_lines.append(next_line)
                    i += 1

                content = '\n'.join(content_lines).strip()

                # Convert casebook ref (4.6.1) to rule ref (Rule 4-6-1)
                rule_ref = f"Rule {situation.rule}-{situation.section}-{situation.article}"

                ref = situation.ref
                if situation.suffix:
                    ref = f"{ref}{situation.suffix}"

                chunks.append(Chunk(
                    content=content,
                    type='situation',
                    book='casebook',
                    source_ref=ref,
                    rule_ref=rule_ref
                ))
                continue

            i += 1

        return chunks
```

**Step 4: Run test to verify it passes**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
PYTHONPATH=. pytest tests/test_chunker.py -v
```

Expected: 6 passed

**Step 5: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add backend/lib/chunker.py backend/tests/test_chunker.py
git commit -m "feat: add casebook chunker for situations"
```

---

### Task 3.3: Create Chunker for Officials Manual

**Files:**
- Modify: `backend/lib/chunker.py`
- Modify: `backend/tests/test_chunker.py`

**Step 1: Write failing test for manual chunking**

Add to `backend/tests/test_chunker.py`:
```python
from lib.chunker import ManualChunker


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
```

**Step 2: Run test to verify it fails**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
PYTHONPATH=. pytest tests/test_chunker.py::test_chunk_manual_by_subsections -v
```

Expected: FAILED - ImportError: cannot import name 'ManualChunker'

**Step 3: Add manual chunker implementation**

Add to `backend/lib/chunker.py`:
```python
import re as regex_module  # avoid name collision


class ManualChunker:
    """Chunker for the NFHS Officials Manual."""

    def chunk(self, markdown: str) -> list[Chunk]:
        """Parse officials manual markdown and return list of chunks."""
        chunks = []
        lines = markdown.split('\n')
        i = 0

        current_ref = None
        current_title = None
        current_content = []

        while i < len(lines):
            line = lines[i]

            # Check for subsection heading (### X.X.X Title)
            subsection_match = regex_module.match(
                r'^###\s+(\d+\.\d+\.\d+)\s+(.+)$',
                line.strip()
            )

            if subsection_match:
                # Flush previous
                if current_ref and current_content:
                    content = '\n'.join(current_content).strip()
                    if content:
                        chunks.append(Chunk(
                            content=content,
                            type='manual',
                            book='manual',
                            source_ref=current_ref,
                            title=current_title
                        ))

                current_ref = subsection_match.group(1)
                current_title = subsection_match.group(2).strip()
                current_content = []
                i += 1
                continue

            # Skip section headings (##) but collect content
            if line.strip().startswith('## '):
                i += 1
                continue

            # Collect content if we're in a subsection
            if current_ref is not None:
                current_content.append(line)

            i += 1

        # Flush remaining
        if current_ref and current_content:
            content = '\n'.join(current_content).strip()
            if content:
                chunks.append(Chunk(
                    content=content,
                    type='manual',
                    book='manual',
                    source_ref=current_ref,
                    title=current_title
                ))

        return chunks
```

**Step 4: Run test to verify it passes**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
PYTHONPATH=. pytest tests/test_chunker.py -v
```

Expected: 8 passed

**Step 5: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add backend/lib/chunker.py backend/tests/test_chunker.py
git commit -m "feat: add officials manual chunker"
```

---

## Phase 4: Embeddings & Ingestion

### Task 4.1: Create Embeddings Module

**Files:**
- Create: `backend/lib/embeddings.py`
- Create: `backend/tests/test_embeddings.py`

**Step 1: Write failing test for embeddings**

Create `backend/tests/test_embeddings.py`:
```python
import pytest
from unittest.mock import Mock, patch
from lib.embeddings import EmbeddingService


def test_embed_text_returns_vector():
    with patch('lib.embeddings.OpenAI') as mock_openai:
        # Mock the embedding response
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 768)]
        )

        service = EmbeddingService(api_key="test-key")
        result = service.embed("Test text")

        assert len(result) == 768
        assert all(isinstance(x, float) for x in result)


def test_embed_batch_returns_vectors():
    with patch('lib.embeddings.OpenAI') as mock_openai:
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.embeddings.create.return_value = Mock(
            data=[
                Mock(embedding=[0.1] * 768),
                Mock(embedding=[0.2] * 768)
            ]
        )

        service = EmbeddingService(api_key="test-key")
        results = service.embed_batch(["Text 1", "Text 2"])

        assert len(results) == 2
        assert len(results[0]) == 768
```

**Step 2: Run test to verify it fails**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
PYTHONPATH=. pytest tests/test_embeddings.py -v
```

Expected: FAILED - ModuleNotFoundError: No module named 'lib.embeddings'

**Step 3: Write embeddings implementation**

Create `backend/lib/embeddings.py`:
```python
"""Embeddings service using OpenRouter/OpenAI-compatible API."""

from openai import OpenAI


class EmbeddingService:
    """Service for generating text embeddings."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "google/gemini-2.0-flash-001"
    ):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model
        # Note: For embeddings, we'll use a dedicated embedding model
        # OpenRouter supports text-embedding-3-small via OpenAI
        self.embedding_model = "openai/text-embedding-3-small"

    def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding

    def embed_batch(self, texts: list[str], batch_size: int = 100) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=batch
            )
            all_embeddings.extend([d.embedding for d in response.data])

        return all_embeddings
```

**Step 4: Run test to verify it passes**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
PYTHONPATH=. pytest tests/test_embeddings.py -v
```

Expected: 2 passed

**Step 5: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add backend/lib/embeddings.py backend/tests/test_embeddings.py
git commit -m "feat: add embeddings service for text vectorization"
```

---

### Task 4.2: Create Ingestion Script

**Files:**
- Create: `backend/scripts/ingest.py`

**Step 1: Create ingestion script**

Create `backend/scripts/__init__.py`:
```python
"""Scripts for data ingestion and maintenance."""
```

Create `backend/scripts/ingest.py`:
```python
#!/usr/bin/env python3
"""Ingest NFHS rulebooks into Supabase vector database."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.chunker import RulesBookChunker, CasebookChunker, ManualChunker, Chunk
from lib.embeddings import EmbeddingService


def load_markdown(filepath: Path) -> str:
    """Load markdown file content."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def chunk_to_dict(chunk: Chunk, embedding: list[float]) -> dict:
    """Convert chunk to dictionary for Supabase insert."""
    return {
        'content': chunk.content,
        'embedding': embedding,
        'type': chunk.type,
        'book': chunk.book,
        'source_ref': chunk.source_ref,
        'section_ref': chunk.section_ref,
        'rule_ref': chunk.rule_ref,
        'title': chunk.title,
        'penalty_text': chunk.penalty_text,
        'page_number': chunk.page_number
    }


def print_chunk_stats(chunks: list, book_name: str):
    """Print detailed statistics about chunks."""
    from collections import Counter

    type_counts = Counter(c.type for c in chunks)

    print(f"\n  === {book_name} Statistics ===")
    print(f"  Total chunks: {len(chunks)}")
    print(f"  By type:")
    for chunk_type, count in sorted(type_counts.items()):
        print(f"    - {chunk_type}: {count}")

    # Show sample chunks for each type
    print(f"\n  Sample chunks:")
    shown_types = set()
    for chunk in chunks:
        if chunk.type not in shown_types:
            shown_types.add(chunk.type)
            preview = chunk.content[:100].replace('\n', ' ')
            print(f"    [{chunk.type}] {chunk.source_ref}: {preview}...")
            if len(shown_types) >= 3:
                break


def main():
    """Main ingestion function."""
    load_dotenv()

    # Initialize services
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_secret_key = os.getenv('SUPABASE_SECRET_KEY')
    openrouter_key = os.getenv('OPENROUTER_API_KEY')

    if not all([supabase_url, supabase_secret_key, openrouter_key]):
        print("Error: Missing required environment variables")
        print("Required: SUPABASE_URL, SUPABASE_SECRET_KEY, OPENROUTER_API_KEY")
        sys.exit(1)

    supabase = create_client(supabase_url, supabase_secret_key)
    embeddings = EmbeddingService(api_key=openrouter_key)

    # Define books to ingest
    books_dir = Path(__file__).parent.parent.parent / "NFHS BOOKS"

    books = [
        {
            'path': books_dir / 'nfhs_basketball_rules_2025-26.md',
            'chunker': RulesBookChunker(),
            'name': 'Rules Book'
        },
        {
            'path': books_dir / 'nfhs_basketball_casebook_2025-26.md',
            'chunker': CasebookChunker(),
            'name': 'Casebook'
        },
        {
            'path': books_dir / 'nfhs_basketball_officials_manual_2025-27.md',
            'chunker': ManualChunker(),
            'name': 'Officials Manual'
        }
    ]

    total_chunks = 0
    stats_summary = []

    for book in books:
        print(f"\nProcessing {book['name']}...")

        if not book['path'].exists():
            print(f"  Warning: File not found: {book['path']}")
            continue

        # Load and chunk
        markdown = load_markdown(book['path'])
        chunks = book['chunker'].chunk(markdown)
        print(f"  Found {len(chunks)} chunks")

        if not chunks:
            continue

        # Print detailed stats
        print_chunk_stats(chunks, book['name'])

        # Track stats for summary
        from collections import Counter
        type_counts = Counter(c.type for c in chunks)
        stats_summary.append({
            'book': book['name'],
            'total': len(chunks),
            'by_type': dict(type_counts)
        })

        # Generate embeddings
        print("\n  Generating embeddings...")
        texts = [c.content for c in chunks]
        vectors = embeddings.embed_batch(texts)

        # Insert into Supabase
        print("  Inserting into database...")
        records = [chunk_to_dict(c, v) for c, v in zip(chunks, vectors)]

        # Insert in batches
        batch_size = 50
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            supabase.table('chunks').insert(batch).execute()
            print(f"    Inserted {min(i + batch_size, len(records))}/{len(records)}")

        total_chunks += len(chunks)

    # Print final summary
    print("\n" + "=" * 50)
    print("INGESTION SUMMARY")
    print("=" * 50)
    for stats in stats_summary:
        print(f"\n{stats['book']}:")
        print(f"  Total: {stats['total']} chunks")
        for chunk_type, count in sorted(stats['by_type'].items()):
            print(f"    {chunk_type}: {count}")
    print(f"\nGrand Total: {total_chunks} chunks ingested")


if __name__ == '__main__':
    main()
```

**Step 2: Verify script syntax**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
python -m py_compile scripts/ingest.py
```

Expected: No output (success)

**Step 3: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add backend/scripts/
git commit -m "feat: add ingestion script for loading rulebooks into Supabase"
```

---

### Task 4.3: Create Verification Script

**Files:**
- Create: `backend/scripts/verify_ingestion.py`

**Step 1: Create verification script**

Create `backend/scripts/verify_ingestion.py`:
```python
#!/usr/bin/env python3
"""Verify NFHS rulebook ingestion in Supabase."""

import os
import sys
from collections import Counter
from dotenv import load_dotenv
from supabase import create_client


def main():
    """Verify ingestion results."""
    load_dotenv()

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_secret_key = os.getenv('SUPABASE_SECRET_KEY')

    if not all([supabase_url, supabase_secret_key]):
        print("Error: Missing SUPABASE_URL or SUPABASE_SECRET_KEY")
        sys.exit(1)

    supabase = create_client(supabase_url, supabase_secret_key)

    print("=" * 60)
    print("NFHS RULEBOOK INGESTION VERIFICATION")
    print("=" * 60)

    # Get total count
    total_result = supabase.table('chunks').select('id', count='exact').execute()
    total_count = total_result.count
    print(f"\nTotal chunks in database: {total_count}")

    # Get counts by book
    print("\n--- By Book ---")
    for book in ['rules', 'casebook', 'manual']:
        result = supabase.table('chunks').select('id', count='exact').eq('book', book).execute()
        print(f"  {book}: {result.count}")

    # Get counts by type
    print("\n--- By Type ---")
    for chunk_type in ['rule_article', 'situation', 'ruling', 'emphasis', 'manual']:
        result = supabase.table('chunks').select('id', count='exact').eq('type', chunk_type).execute()
        if result.count > 0:
            print(f"  {chunk_type}: {result.count}")

    # Verify embeddings exist
    print("\n--- Embedding Verification ---")
    null_embeddings = supabase.table('chunks').select('id', count='exact').is_('embedding', 'null').execute()
    print(f"  Chunks with embeddings: {total_count - null_embeddings.count}")
    print(f"  Chunks without embeddings: {null_embeddings.count}")

    if null_embeddings.count > 0:
        print("  WARNING: Some chunks are missing embeddings!")

    # Sample chunks from each book
    print("\n--- Sample Chunks ---")
    for book in ['rules', 'casebook', 'manual']:
        result = supabase.table('chunks').select('source_ref, type, content').eq('book', book).limit(2).execute()
        if result.data:
            print(f"\n  {book.upper()}:")
            for chunk in result.data:
                preview = chunk['content'][:80].replace('\n', ' ')
                print(f"    [{chunk['type']}] {chunk['source_ref']}: {preview}...")

    # Test vector search
    print("\n--- Vector Search Test ---")
    try:
        # Simple test query using match_chunks function
        # We'll use a zero vector just to verify the function works
        test_vector = [0.0] * 768
        result = supabase.rpc('match_chunks', {
            'query_embedding': test_vector,
            'match_count': 3
        }).execute()
        print(f"  match_chunks function: OK (returned {len(result.data)} results)")
    except Exception as e:
        print(f"  match_chunks function: FAILED - {e}")

    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)

    # Return success/failure for CI
    if total_count == 0:
        print("\nERROR: No chunks found in database!")
        sys.exit(1)
    if null_embeddings.count > 0:
        print("\nWARNING: Some chunks missing embeddings")
        sys.exit(1)

    print("\nAll checks passed!")


if __name__ == '__main__':
    main()
```

**Step 2: Verify script syntax**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
python -m py_compile scripts/verify_ingestion.py
```

Expected: No output (success)

**Step 3: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add backend/scripts/verify_ingestion.py
git commit -m "feat: add post-ingestion verification script"
```

---

## Phase 5: Backend API

### Task 5.1: Create Search Function

**Files:**
- Create: `backend/functions/search.py`
- Create: `backend/tests/test_search.py`

**Step 1: Write failing test for search**

Create `backend/tests/test_search.py`:
```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from functions.search import search_chunks, SearchResult


def test_search_returns_results_from_all_books():
    with patch('functions.search.create_client') as mock_supabase, \
         patch('functions.search.EmbeddingService') as mock_embed:

        # Mock embedding
        mock_embed_instance = Mock()
        mock_embed.return_value = mock_embed_instance
        mock_embed_instance.embed.return_value = [0.1] * 768

        # Mock Supabase RPC responses for each book
        mock_client = Mock()
        mock_supabase.return_value = mock_client

        mock_client.rpc.return_value.execute.return_value = Mock(data=[
            {
                'id': '123',
                'content': 'Test content',
                'type': 'rule_article',
                'book': 'rules',
                'source_ref': 'Rule 4-6-1',
                'similarity': 0.9
            }
        ])

        results = search_chunks("basket interference", top_k=3)

        # Should call RPC 3 times (once per book)
        assert mock_client.rpc.call_count == 3
        assert len(results) > 0


def test_search_result_structure():
    result = SearchResult(
        id='123',
        content='Test content',
        type='rule_article',
        book='rules',
        source_ref='Rule 4-6-1',
        section_ref='Rule 4-6',
        rule_ref='Rule 4',
        title=None,
        penalty_text=None,
        similarity=0.9
    )

    assert result.source_ref == 'Rule 4-6-1'
    assert result.similarity == 0.9
```

**Step 2: Run test to verify it fails**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
PYTHONPATH=. pytest tests/test_search.py -v
```

Expected: FAILED - ModuleNotFoundError: No module named 'functions.search'

**Step 3: Write search implementation**

Create `backend/functions/search.py`:
```python
"""Vector search function for NFHS rulebook chunks."""

import os
from dataclasses import dataclass
from typing import Optional
from supabase import create_client

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.embeddings import EmbeddingService


@dataclass
class SearchResult:
    """A search result from the vector database."""
    id: str
    content: str
    type: str
    book: str
    source_ref: str
    section_ref: Optional[str]
    rule_ref: Optional[str]
    title: Optional[str]
    penalty_text: Optional[str]
    similarity: float


def search_chunks(
    query: str,
    top_k: int = 5,
    supabase_url: Optional[str] = None,
    supabase_publishable_key: Optional[str] = None,
    openrouter_key: Optional[str] = None
) -> list[SearchResult]:
    """
    Search for relevant chunks across all books.

    Retrieves top_k results from each book, then combines and reranks.
    """
    # Get credentials
    supabase_url = supabase_url or os.getenv('SUPABASE_URL')
    supabase_publishable_key = supabase_publishable_key or os.getenv('SUPABASE_PUBLISHABLE_KEY')
    openrouter_key = openrouter_key or os.getenv('OPENROUTER_API_KEY')

    # Initialize services
    supabase = create_client(supabase_url, supabase_publishable_key)
    embeddings = EmbeddingService(api_key=openrouter_key)

    # Generate query embedding
    query_embedding = embeddings.embed(query)

    # Search each book separately
    books = ['rules', 'casebook', 'manual']
    all_results = []

    for book in books:
        response = supabase.rpc(
            'match_chunks',
            {
                'query_embedding': query_embedding,
                'match_count': top_k,
                'filter_book': book
            }
        ).execute()

        for row in response.data:
            all_results.append(SearchResult(
                id=row['id'],
                content=row['content'],
                type=row['type'],
                book=row['book'],
                source_ref=row['source_ref'],
                section_ref=row.get('section_ref'),
                rule_ref=row.get('rule_ref'),
                title=row.get('title'),
                penalty_text=row.get('penalty_text'),
                similarity=row['similarity']
            ))

    # Sort by similarity and take top results
    all_results.sort(key=lambda x: x.similarity, reverse=True)

    return all_results[:top_k * 2]  # Return more for LLM context
```

**Step 4: Run test to verify it passes**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
PYTHONPATH=. pytest tests/test_search.py -v
```

Expected: 2 passed

**Step 5: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add backend/functions/search.py backend/tests/test_search.py
git commit -m "feat: add vector search function with per-book retrieval"
```

---

### Task 5.2: Create Chat Function

**Files:**
- Create: `backend/functions/chat.py`
- Create: `backend/tests/test_chat.py`

**Step 1: Write failing test for chat**

Create `backend/tests/test_chat.py`:
```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
from functions.chat import build_prompt, ChatService


def test_build_prompt_includes_sources():
    sources = [
        Mock(
            source_ref='Rule 4-6-1',
            content='Basket interference occurs when...',
            penalty_text='PENALTY: Two points awarded.'
        ),
        Mock(
            source_ref='4.6.1',
            content='SITUATION: Player slaps backboard...',
            penalty_text=None
        )
    ]

    prompt = build_prompt("What is basket interference?", sources)

    assert '[1]' in prompt
    assert '[2]' in prompt
    assert 'Rule 4-6-1' in prompt
    assert 'Basket interference' in prompt
    assert 'PENALTY' in prompt


def test_build_prompt_instructs_citations():
    sources = [Mock(source_ref='Rule 1-1-1', content='Test', penalty_text=None)]
    prompt = build_prompt("Test question", sources)

    assert 'cite' in prompt.lower() or '[1]' in prompt
```

**Step 2: Run test to verify it fails**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
PYTHONPATH=. pytest tests/test_chat.py -v
```

Expected: FAILED - ModuleNotFoundError: No module named 'functions.chat'

**Step 3: Write chat implementation**

Create `backend/functions/chat.py`:
```python
"""Chat function with RAG and citations."""

import os
from typing import Generator, Optional
from dataclasses import dataclass
from openai import OpenAI

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from functions.search import search_chunks, SearchResult


@dataclass
class Citation:
    """A citation reference."""
    ref_num: int
    source_ref: str
    content_preview: str


def build_prompt(question: str, sources: list[SearchResult]) -> str:
    """Build the prompt with sources for the LLM."""

    sources_text = []
    for i, source in enumerate(sources, 1):
        source_block = f"[{i}] {source.source_ref}\n{source.content}"
        if source.penalty_text:
            source_block += f"\n\n{source.penalty_text}"
        sources_text.append(source_block)

    sources_section = "\n\n---\n\n".join(sources_text)

    prompt = f"""You are an expert on NFHS (National Federation of High Schools) basketball rules. Answer the question using ONLY the provided sources.

When you use information from a source, cite it immediately after using [1], [2], etc. Place citations right after the relevant information with no space before the bracket.

SOURCES:
{sources_section}

---

QUESTION: {question}

Provide a clear, accurate answer citing the sources. If the sources don't contain enough information to fully answer, say so."""

    return prompt


class ChatService:
    """Service for handling chat requests with RAG."""

    def __init__(
        self,
        openrouter_key: Optional[str] = None,
        model: str = "google/gemini-2.5-flash-preview"
    ):
        self.openrouter_key = openrouter_key or os.getenv('OPENROUTER_API_KEY')
        self.model = model
        self.client = OpenAI(
            api_key=self.openrouter_key,
            base_url="https://openrouter.ai/api/v1"
        )

    def chat(self, question: str, top_k: int = 5) -> tuple[str, list[Citation]]:
        """
        Process a question and return answer with citations.

        Returns:
            Tuple of (answer_text, list of citations used)
        """
        # Search for relevant chunks
        sources = search_chunks(question, top_k=top_k)

        if not sources:
            return "I couldn't find any relevant information in the rulebooks.", []

        # Build prompt
        prompt = build_prompt(question, sources)

        # Call LLM
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        answer = response.choices[0].message.content

        # Build citations list
        citations = [
            Citation(
                ref_num=i,
                source_ref=source.source_ref,
                content_preview=source.content[:200] + "..." if len(source.content) > 200 else source.content
            )
            for i, source in enumerate(sources, 1)
        ]

        return answer, citations

    def chat_stream(self, question: str, top_k: int = 5) -> Generator[dict, None, None]:
        """
        Stream a chat response with citations.

        Yields dicts with either:
            {"type": "text", "content": "..."}
            {"type": "citations", "citations": [...]}
        """
        # Search for relevant chunks
        sources = search_chunks(question, top_k=top_k)

        if not sources:
            yield {"type": "text", "content": "I couldn't find any relevant information in the rulebooks."}
            return

        # Build prompt
        prompt = build_prompt(question, sources)

        # Build citations list first
        citations = [
            {
                "ref_num": i,
                "source_ref": source.source_ref,
                "content_preview": source.content[:200] + "..." if len(source.content) > 200 else source.content,
                "book": source.book,
                "penalty_text": source.penalty_text
            }
            for i, source in enumerate(sources, 1)
        ]

        # Yield citations first so frontend has them ready
        yield {"type": "citations", "citations": citations}

        # Stream LLM response
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            stream=True
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield {"type": "text", "content": chunk.choices[0].delta.content}

        yield {"type": "done"}
```

**Step 4: Run test to verify it passes**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
PYTHONPATH=. pytest tests/test_chat.py -v
```

Expected: 2 passed

**Step 5: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add backend/functions/chat.py backend/tests/test_chat.py
git commit -m "feat: add chat function with RAG and streaming citations"
```

---

### Task 5.3: Create HTTP Handler

**Files:**
- Create: `backend/main.py`

**Step 1: Create FastAPI application**

Create `backend/main.py`:
```python
"""FastAPI application for NFHS Rules Chat API."""

import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from functions.chat import ChatService

app = FastAPI(
    title="NFHS Rules Chat API",
    description="Chat API for NFHS Basketball Rules with citations",
    version="0.1.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chat_service = ChatService()


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    question: str
    top_k: int = 5


class ChatResponse(BaseModel):
    """Response body for non-streaming chat."""
    answer: str
    citations: list[dict]


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Non-streaming chat endpoint."""
    try:
        answer, citations = chat_service.chat(
            question=request.question,
            top_k=request.top_k
        )
        return ChatResponse(
            answer=answer,
            citations=[
                {
                    "ref_num": c.ref_num,
                    "source_ref": c.source_ref,
                    "content_preview": c.content_preview
                }
                for c in citations
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint."""

    def generate():
        try:
            for event in chat_service.chat_stream(
                question=request.question,
                top_k=request.top_k
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Step 2: Add uvicorn to requirements**

Add to `backend/requirements.txt`:
```text
fastapi>=0.109.0
uvicorn>=0.27.0
```

**Step 3: Install new dependencies**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
pip install fastapi uvicorn
```

**Step 4: Verify server starts**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
timeout 5 python main.py || true
```

Expected: Uvicorn running on http://0.0.0.0:8000 (or timeout after 5s)

**Step 5: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add backend/main.py backend/requirements.txt
git commit -m "feat: add FastAPI server with streaming chat endpoint"
```

---

## Phase 6: Frontend

### Task 6.1: Create API Client

**Files:**
- Create: `frontend/src/lib/api.ts`

**Step 1: Create API client**

Create `frontend/src/lib/api.ts`:
```typescript
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface Citation {
  ref_num: number;
  source_ref: string;
  content_preview: string;
  book?: string;
  penalty_text?: string;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
}

export interface StreamEvent {
  type: 'text' | 'citations' | 'done' | 'error';
  content?: string;
  citations?: Citation[];
  message?: string;
}

export async function chat(question: string, topK = 5): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, top_k: topK }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

export async function* chatStream(
  question: string,
  topK = 5
): AsyncGenerator<StreamEvent> {
  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, top_k: topK }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event = JSON.parse(line.slice(6)) as StreamEvent;
          yield event;
        } catch {
          console.error('Failed to parse SSE event:', line);
        }
      }
    }
  }
}
```

**Step 2: Create lib directory**

Run:
```bash
mkdir -p "/Users/anthonyharley/Desktop/code/NFHS APP/frontend/src/lib"
```

**Step 3: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add frontend/src/lib/api.ts
git commit -m "feat: add API client with streaming support"
```

---

### Task 6.2: Create Chat Hook

**Files:**
- Create: `frontend/src/hooks/useChat.ts`

**Step 1: Create hooks directory and chat hook**

Create `frontend/src/hooks/useChat.ts`:
```typescript
import { useState, useCallback } from 'react';
import { chatStream, Citation, StreamEvent } from '../lib/api';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  isStreaming?: boolean;
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(async (question: string) => {
    if (!question.trim() || isLoading) return;

    setError(null);
    setIsLoading(true);

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: question,
    };

    // Add placeholder assistant message
    const assistantId = (Date.now() + 1).toString();
    const assistantMessage: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      citations: [],
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);

    try {
      let citations: Citation[] = [];
      let content = '';

      for await (const event of chatStream(question)) {
        if (event.type === 'citations') {
          citations = event.citations || [];
        } else if (event.type === 'text') {
          content += event.content || '';
        } else if (event.type === 'error') {
          throw new Error(event.message);
        }

        // Update assistant message
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? { ...msg, content, citations, isStreaming: event.type !== 'done' }
              : msg
          )
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      // Remove failed assistant message
      setMessages((prev) => prev.filter((msg) => msg.id !== assistantId));
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
  };
}
```

**Step 2: Create hooks directory**

Run:
```bash
mkdir -p "/Users/anthonyharley/Desktop/code/NFHS APP/frontend/src/hooks"
```

**Step 3: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add frontend/src/hooks/useChat.ts
git commit -m "feat: add useChat hook for streaming chat state"
```

---

### Task 6.3: Create Citation Components

**Files:**
- Create: `frontend/src/components/CitationButton.tsx`
- Create: `frontend/src/components/CitationPanel.tsx`

**Step 1: Create components directory**

Run:
```bash
mkdir -p "/Users/anthonyharley/Desktop/code/NFHS APP/frontend/src/components"
```

**Step 2: Create CitationButton component**

Create `frontend/src/components/CitationButton.tsx`:
```typescript
import { useState } from 'react';
import { Citation } from '../lib/api';

interface CitationButtonProps {
  refNum: number;
  citation: Citation;
  onClick: (citation: Citation) => void;
}

export function CitationButton({ refNum, citation, onClick }: CitationButtonProps) {
  return (
    <button
      onClick={() => onClick(citation)}
      className="inline-flex items-center justify-center min-w-[1.5rem] h-5 px-1 mx-0.5
                 text-xs font-medium text-blue-700 bg-blue-100 rounded
                 hover:bg-blue-200 transition-colors"
      title={citation.source_ref}
    >
      {refNum}
    </button>
  );
}
```

**Step 3: Create CitationPanel component**

Create `frontend/src/components/CitationPanel.tsx`:
```typescript
import { Citation } from '../lib/api';

interface CitationPanelProps {
  citation: Citation | null;
  onClose: () => void;
}

export function CitationPanel({ citation, onClose }: CitationPanelProps) {
  if (!citation) return null;

  const bookLabels: Record<string, string> = {
    rules: 'Rules Book',
    casebook: 'Casebook',
    manual: 'Officials Manual',
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t shadow-lg p-4 max-h-[40vh] overflow-y-auto">
      <div className="max-w-3xl mx-auto">
        <div className="flex justify-between items-start mb-2">
          <div>
            <span className="text-xs font-medium text-gray-500 uppercase">
              {bookLabels[citation.book || 'rules'] || citation.book}
            </span>
            <h3 className="text-lg font-semibold text-gray-900">
              {citation.source_ref}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <p className="text-gray-700 whitespace-pre-wrap">
          {citation.content_preview}
        </p>

        {citation.penalty_text && (
          <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded">
            <p className="text-sm font-medium text-amber-800 mb-1">Penalty</p>
            <p className="text-sm text-amber-700 whitespace-pre-wrap">
              {citation.penalty_text}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
```

**Step 4: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add frontend/src/components/
git commit -m "feat: add CitationButton and CitationPanel components"
```

---

### Task 6.4: Create Message Component with Citation Parsing

**Files:**
- Create: `frontend/src/components/Message.tsx`

**Step 1: Create Message component**

Create `frontend/src/components/Message.tsx`:
```typescript
import { useMemo } from 'react';
import { Citation } from '../lib/api';
import { CitationButton } from './CitationButton';

interface MessageProps {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  isStreaming?: boolean;
  onCitationClick: (citation: Citation) => void;
}

export function Message({
  role,
  content,
  citations = [],
  isStreaming,
  onCitationClick,
}: MessageProps) {
  // Parse content and replace [N] with citation buttons
  const renderedContent = useMemo(() => {
    if (!content) return null;

    // Split by citation pattern [N]
    const parts = content.split(/(\[\d+\])/g);

    return parts.map((part, index) => {
      const match = part.match(/\[(\d+)\]/);
      if (match) {
        const refNum = parseInt(match[1], 10);
        const citation = citations.find((c) => c.ref_num === refNum);
        if (citation) {
          return (
            <CitationButton
              key={index}
              refNum={refNum}
              citation={citation}
              onClick={onCitationClick}
            />
          );
        }
      }
      return <span key={index}>{part}</span>;
    });
  }, [content, citations, onCitationClick]);

  const isUser = role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-900'
        }`}
      >
        <div className="whitespace-pre-wrap">{renderedContent}</div>
        {isStreaming && (
          <span className="inline-block w-2 h-4 ml-1 bg-gray-400 animate-pulse" />
        )}
      </div>
    </div>
  );
}
```

**Step 2: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add frontend/src/components/Message.tsx
git commit -m "feat: add Message component with citation parsing"
```

---

### Task 6.5: Create Chat Component

**Files:**
- Create: `frontend/src/components/Chat.tsx`

**Step 1: Create Chat component**

Create `frontend/src/components/Chat.tsx`:
```typescript
import { useState, useRef, useEffect } from 'react';
import { useChat } from '../hooks/useChat';
import { Message } from './Message';
import { CitationPanel } from './CitationPanel';
import { Citation } from '../lib/api';

export function Chat() {
  const { messages, isLoading, error, sendMessage, clearMessages } = useChat();
  const [input, setInput] = useState('');
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      sendMessage(input);
      setInput('');
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-4 py-3 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">
          NFHS Basketball Rules
        </h1>
        {messages.length > 0 && (
          <button
            onClick={clearMessages}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Clear chat
          </button>
        )}
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 mt-20">
            <p className="text-lg mb-2">Ask a question about NFHS basketball rules</p>
            <p className="text-sm">
              Examples: "What is basket interference?" or "Can a coach stand during play?"
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <Message
              key={message.id}
              role={message.role}
              content={message.content}
              citations={message.citations}
              isStreaming={message.isStreaming}
              onCitationClick={setSelectedCitation}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Error */}
      {error && (
        <div className="px-4 py-2 bg-red-50 text-red-700 text-sm">
          Error: {error}
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="border-t bg-white p-4">
        <div className="flex gap-2 max-w-3xl mx-auto">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about basketball rules..."
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Thinking...' : 'Send'}
          </button>
        </div>
      </form>

      {/* Citation Panel */}
      <CitationPanel
        citation={selectedCitation}
        onClose={() => setSelectedCitation(null)}
      />
    </div>
  );
}
```

**Step 2: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add frontend/src/components/Chat.tsx
git commit -m "feat: add main Chat component"
```

---

### Task 6.6: Update App Component

**Files:**
- Modify: `frontend/src/App.tsx`

**Step 1: Update App.tsx**

Replace contents of `frontend/src/App.tsx`:
```typescript
import { Chat } from './components/Chat';

function App() {
  return <Chat />;
}

export default App;
```

**Step 2: Create .env file for frontend**

Create `frontend/.env`:
```bash
VITE_API_URL=http://localhost:8000
```

**Step 3: Verify frontend builds**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/frontend"
npm run build
```

Expected: build completed successfully

**Step 4: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add frontend/src/App.tsx frontend/.env
git commit -m "feat: wire up Chat component in App"
```

---

## Phase 7: Integration & Testing

### Task 7.1: Create Environment File

**Files:**
- Create: `backend/.env` (from .env.example)

**Step 1: Copy and fill environment variables**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
cp .env.example .env
```

Note: Manually fill in the actual values for:
- SUPABASE_URL
- SUPABASE_PUBLISHABLE_KEY
- SUPABASE_SECRET_KEY
- OPENROUTER_API_KEY
- LANGCHAIN_API_KEY

**Step 2: Add .env to .gitignore**

Create `/Users/anthonyharley/Desktop/code/NFHS APP/.gitignore`:
```
# Environment
.env
*.env.local

# Python
__pycache__/
*.py[cod]
venv/
.venv/

# Node
node_modules/
dist/

# IDE
.idea/
.vscode/
*.swp
```

**Step 3: Commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add .gitignore
git commit -m "chore: add .gitignore"
```

---

### Task 7.2: Run Ingestion

**Step 1: Ensure environment is configured**

Verify `.env` file has all required values.

**Step 2: Run ingestion script**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
python scripts/ingest.py
```

Expected:
```
Processing Rules Book...
  Found X chunks
  Generating embeddings...
  Inserting into database...
Processing Casebook...
...
Done! Ingested Y total chunks.
```

**Step 3: Verify data in Supabase**

Check Supabase dashboard → Table Editor → chunks table has records.

---

### Task 7.3: End-to-End Test

**Step 1: Start backend**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/backend"
source venv/bin/activate
python main.py
```

**Step 2: Start frontend (new terminal)**

Run:
```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP/frontend"
npm run dev
```

**Step 3: Test in browser**

1. Open http://localhost:5173
2. Ask: "What is basket interference?"
3. Verify:
   - Response streams in
   - Citation buttons appear (e.g., [1], [2])
   - Clicking citation opens panel with source text
   - Penalty text shows if applicable

**Step 4: Final commit**

```bash
cd "/Users/anthonyharley/Desktop/code/NFHS APP"
git add -A
git commit -m "feat: complete NFHS Basketball Rules Chat App v0.1.0"
```

---

## Summary

**Total Tasks:** 21

**Phase Breakdown:**
- Phase 1: Project Setup (3 tasks)
- Phase 2: Markdown Parser (3 tasks)
- Phase 3: Chunking Logic (3 tasks)
- Phase 4: Embeddings & Ingestion (2 tasks)
- Phase 5: Backend API (3 tasks)
- Phase 6: Frontend (6 tasks)
- Phase 7: Integration & Testing (3 tasks)

**Key Files Created:**
- `backend/lib/parser.py` - Markdown parsing
- `backend/lib/chunker.py` - Chunking logic for all 3 books
- `backend/lib/embeddings.py` - Embedding generation
- `backend/functions/search.py` - Vector search
- `backend/functions/chat.py` - Chat with RAG
- `backend/main.py` - FastAPI server
- `frontend/src/components/Chat.tsx` - Main chat UI
- `frontend/src/hooks/useChat.ts` - Chat state management

"""Chunking logic for NFHS rulebooks."""

import json
import re as regex_module

from dataclasses import dataclass, field
from typing import Optional
from .parser import parse_heading, parse_penalty_scope, parse_situation, parse_situation_suffix_only


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
        self.current_rule_title: Optional[str] = None
        self.current_section: Optional[str] = None
        self.current_section_title: Optional[str] = None
        self.current_article: Optional[str] = None
        self.current_content: list[str] = []
        self.chunks: list[Chunk] = []
        self.pending_penalties: dict[str, str] = {}  # section_ref -> penalty_text

    def chunk(self, markdown: str) -> list[Chunk]:
        """Parse markdown and return list of chunks."""
        self.chunks = []
        self.current_rule = None
        self.current_rule_title = None
        self.current_section = None
        self.current_section_title = None
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
                    self.current_rule_title = heading.title
                    self.current_section = None
                    self.current_section_title = None
                    self.current_article = None
                elif heading.heading_type == 'section':
                    self._flush_article()
                    self.current_section = heading.section_num
                    self.current_section_title = heading.title
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

        body_content = '\n'.join(self.current_content).strip()
        if not body_content:
            self.current_content = []
            return

        source_ref = f"Rule {self.current_rule}-{self.current_section}-{self.current_article}"
        section_ref = f"Rule {self.current_rule}-{self.current_section}"
        rule_ref = f"Rule {self.current_rule}"

        # Build JSON title with rule and section names
        title_data = {
            "rule": self.current_rule_title,
            "section": self.current_section_title
        }
        title_json = json.dumps(title_data)

        # Prepend context to content for better embedding retrieval
        context_line = f"[Rule {self.current_rule}: {self.current_rule_title} - Section {self.current_section}: {self.current_section_title}]"
        content = f"{context_line}\n\n{body_content}"

        self.chunks.append(Chunk(
            content=content,
            type='rule_article',
            book='rules',
            source_ref=source_ref,
            section_ref=section_ref,
            rule_ref=rule_ref,
            title=title_json
        ))

        self.current_content = []

    def _attach_penalties(self):
        """Attach penalty text to chunks based on section."""
        for chunk in self.chunks:
            if chunk.section_ref and chunk.section_ref in self.pending_penalties:
                chunk.penalty_text = self.pending_penalties[chunk.section_ref]


class CasebookChunker:
    """Chunker for the NFHS Casebook."""

    def chunk(self, markdown: str) -> list[Chunk]:
        """Parse casebook markdown and return list of chunks."""
        chunks = []
        lines = markdown.split('\n')
        i = 0

        # Track the last numbered situation for suffix-only situations
        last_ref = None
        last_rule = None
        last_section = None
        last_article = None

        while i < len(lines):
            line = lines[i]

            # Check for numbered situation header
            situation = parse_situation(line)
            if situation:
                # Update tracking for suffix-only situations
                last_ref = situation.ref
                last_rule = situation.rule
                last_section = situation.section
                last_article = situation.article

                # Collect entire situation block (situation + ruling + comment)
                content_lines = [line]
                i += 1

                # Continue until next situation or end
                while i < len(lines):
                    next_line = lines[i]
                    # Check if next situation starts (numbered or suffix-only)
                    if parse_situation(next_line) or parse_situation_suffix_only(next_line):
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

            # Check for suffix-only situation (e.g., "SITUATION A:")
            suffix = parse_situation_suffix_only(line)
            if suffix and last_ref:
                # Collect entire situation block
                content_lines = [line]
                i += 1

                # Continue until next situation or end
                while i < len(lines):
                    next_line = lines[i]
                    if parse_situation(next_line) or parse_situation_suffix_only(next_line):
                        break
                    content_lines.append(next_line)
                    i += 1

                content = '\n'.join(content_lines).strip()

                # Use the last numbered ref with this suffix
                rule_ref = f"Rule {last_rule}-{last_section}-{last_article}"
                ref = f"{last_ref}{suffix}"

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


class ManualChunker:
    """Chunker for the NFHS Officials Manual."""

    # Max characters per chunk (~6000 chars ≈ 1500 tokens, safe for embedding)
    MAX_CHUNK_SIZE = 6000

    # Page header/footer patterns to filter out
    PAGE_HEADER_PATTERN = regex_module.compile(
        r'^\d+\s+NFHS Basketball Offi?cials Manual|'
        r'^NFHS Basketball Offi?cials Manual\s+\d+|'
        r'^\d+\s+$'
    )

    def _is_noise_line(self, line: str) -> bool:
        """Check if line is a page header, diagram label, or other noise."""
        stripped = line.strip()
        # Page headers/footers
        if self.PAGE_HEADER_PATTERN.match(stripped):
            return True
        # Diagram labels (all caps, short, specific keywords)
        if stripped.isupper() and len(stripped) < 60:
            # Skip crew markers - they're not noise
            if stripped in ('CREW OF TWO', 'CREW OF THREE'):
                return False
            # Common diagram label patterns
            noise_keywords = ['SCORER', 'TIMER', 'PRIMARY', 'COVERAGE', 'POSITION',
                            'BASELINE', 'SIDELINE', 'FRONTCOURT', 'BACKCOURT',
                            'MECHANI', 'DIAGRAM', 'HALFCOURT', 'BOUNDARY']
            if any(kw in stripped for kw in noise_keywords):
                return True
        return False

    def chunk(self, markdown: str) -> list[Chunk]:
        """Parse officials manual markdown and return list of chunks."""
        chunks = []
        lines = markdown.split('\n')
        i = 0

        current_ref = None
        current_title = None
        current_content = []
        current_crew = None  # Track CREW OF TWO/THREE context

        def flush_chunk():
            """Save current chunk if it has content."""
            nonlocal current_ref, current_title, current_content
            if current_ref and current_content:
                content = '\n'.join(current_content).strip()
                if content:
                    # Add crew context to ref if applicable
                    ref = current_ref
                    if current_crew and not ref.startswith(('Part', 'Term', 'Signal', '1.')):
                        ref = f"{current_ref} ({current_crew})"

                    # Split oversized chunks
                    if len(content) > self.MAX_CHUNK_SIZE:
                        sub_chunks = self._split_content(content, ref, current_title)
                        chunks.extend(sub_chunks)
                    else:
                        chunks.append(Chunk(
                            content=content,
                            type='manual',
                            book='manual',
                            source_ref=ref,
                            title=current_title
                        ))
            current_content = []

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Skip noise lines (page headers, diagram labels)
            if self._is_noise_line(stripped):
                i += 1
                continue

            # Track crew context (CREW OF TWO / CREW OF THREE)
            if stripped == 'CREW OF TWO':
                flush_chunk()
                current_crew = 'Crew of 2'
                i += 1
                continue
            elif stripped == 'CREW OF THREE':
                flush_chunk()
                current_crew = 'Crew of 3'
                i += 1
                continue

            # Check for subsection heading (### X.X.X Title)
            subsection_match = regex_module.match(
                r'^###\s+(\d+\.\d+\.\d+)\s+(.+)$',
                stripped
            )

            if subsection_match:
                flush_chunk()
                current_ref = subsection_match.group(1)
                current_title = subsection_match.group(2).strip()
                i += 1
                continue

            # Check for markdown section heading (## X.X Title)
            md_section_match = regex_module.match(
                r'^##\s+(\d+\.\d+)\s+(.+)$',
                stripped
            )

            if md_section_match:
                flush_chunk()
                current_ref = md_section_match.group(1)
                current_title = md_section_match.group(2).strip()
                i += 1
                continue

            # Check for plain text section heading (X.X Title - no hashtags)
            # Must start with number, have title-case or all-caps title
            plain_section_match = regex_module.match(
                r'^(\d+\.\d+)\s+([A-Z][A-Za-z,\s\-\(\)&]+)$',
                stripped
            )

            if plain_section_match:
                title_candidate = plain_section_match.group(2).strip()
                # Must be a real title (not just a number or short noise)
                if len(title_candidate) > 5 and not title_candidate.isupper():
                    flush_chunk()
                    current_ref = plain_section_match.group(1)
                    current_title = title_candidate
                    i += 1
                    continue

            # Check for inline subsection (X.X.X: content on same line)
            inline_match = regex_module.match(
                r'^(\d+\.\d+\.\d+):\s*(.*)$',
                stripped
            )

            if inline_match:
                flush_chunk()
                current_ref = inline_match.group(1)
                # Title is the first significant word(s) from content
                content_start = inline_match.group(2)
                current_title = content_start[:50].split('.')[0] if content_start else None
                current_content = [content_start] if content_start else []
                i += 1
                continue

            # Check for Part heading (# Part N:)
            part_match = regex_module.match(
                r'^#\s+Part\s+(\d+):\s*(.*)$',
                stripped
            )

            if part_match:
                flush_chunk()
                current_ref = f"Part {part_match.group(1)}"
                current_title = part_match.group(2).strip() if part_match.group(2) else None
                current_crew = None  # Reset crew context for new part
                i += 1
                continue

            # Check for Signal heading (#N SIGNAL_NAME)
            signal_match = regex_module.match(
                r'^#(\d+)\s+(.+)$',
                stripped
            )

            if signal_match:
                flush_chunk()
                current_ref = f"Signal {signal_match.group(1)}"
                current_title = signal_match.group(2).strip()
                i += 1
                continue

            # Check for glossary term (ALL CAPS TERM: definition)
            glossary_match = regex_module.match(
                r'^([A-Z][A-Z\s/]+):\s*(.*)$',
                stripped
            )

            if glossary_match and len(glossary_match.group(1)) > 3:
                # Only treat as glossary if we're in Part 2 (Terminology)
                term = glossary_match.group(1).strip()
                if current_ref and 'Part 2' in str(current_ref):
                    flush_chunk()
                    current_ref = f"Term: {term}"
                    current_title = term
                    current_content = [glossary_match.group(2)] if glossary_match.group(2) else []
                    i += 1
                    continue

            # Collect content if we're in a section
            if current_ref is not None:
                current_content.append(line)

            i += 1

        # Flush remaining
        flush_chunk()

        return chunks

    def _split_content(self, content: str, base_ref: str, title: Optional[str]) -> list[Chunk]:
        """Split oversized content into smaller chunks."""
        chunks = []
        paragraphs = content.split('\n\n')
        current_chunk = []
        current_size = 0
        part_num = 1

        for para in paragraphs:
            para_size = len(para)
            if current_size + para_size > self.MAX_CHUNK_SIZE and current_chunk:
                # Flush current chunk
                chunk_content = '\n\n'.join(current_chunk).strip()
                if chunk_content:
                    chunks.append(Chunk(
                        content=chunk_content,
                        type='manual',
                        book='manual',
                        source_ref=f"{base_ref} (Part {part_num})",
                        title=title
                    ))
                    part_num += 1
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size

        # Flush remaining
        if current_chunk:
            chunk_content = '\n\n'.join(current_chunk).strip()
            if chunk_content:
                ref = base_ref if part_num == 1 else f"{base_ref} (Part {part_num})"
                chunks.append(Chunk(
                    content=chunk_content,
                    type='manual',
                    book='manual',
                    source_ref=ref,
                    title=title
                ))

        return chunks

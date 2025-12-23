"""Chunking logic for NFHS rulebooks."""

import json
import re as regex_module

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

"""Chat function with RAG and citations."""

import os
from typing import Generator, Optional
from dataclasses import dataclass
from openai import OpenAI
from langsmith import traceable

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


@traceable(name="build_prompt")
def build_prompt(question: str, sources: list[SearchResult]) -> str:
    """Build the prompt with sources for the LLM."""

    sources_text = []
    for i, source in enumerate(sources, 1):
        source_block = f"[{i}] {source.source_ref}\n{source.content}"
        if source.penalty_text:
            source_block += f"\n\n{source.penalty_text}"
        sources_text.append(source_block)

    sources_section = "\n\n---\n\n".join(sources_text)

    prompt = f"""You are an expert NFHS basketball rules advisor. Your role is to help officials understand and apply the rules correctly.

Answer using ONLY the provided sources. When rules text is relevant, quote it directly - officials need to know the actual language, not just a paraphrase. Use citations [1], [2], etc. immediately after quoted, paraphrased, or referenced material (no space before the bracket).

Structure your answers naturally:
- Start by addressing the question
- Support your answer with direct quotes from the rulebook where the precise wording matters
- When multiple sources apply, synthesize them clearly
- Reference relevant casebook situations or mechanics guidance to illustrate application
- Conclude with any important clarifications or related considerations

If the sources don't contain enough information, acknowledge the limitation.

SOURCES:
{sources_section}

---

QUESTION: {question}"""

    return prompt


class ChatService:
    """Service for handling chat requests with RAG."""

    def __init__(
        self,
        openrouter_key: Optional[str] = None,
        model: str = "google/gemini-2.0-flash-001"
    ):
        self.openrouter_key = openrouter_key or os.getenv('OPENROUTER_API_KEY')
        self.model = model
        self.client = OpenAI(
            api_key=self.openrouter_key,
            base_url="https://openrouter.ai/api/v1"
        )

    @traceable(name="chat")
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

    @traceable(name="chat_stream")
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

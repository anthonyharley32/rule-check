"""Vector search function for NFHS rulebook chunks."""

import os
from dataclasses import dataclass, asdict
from typing import Optional
from supabase import create_client
from langsmith import traceable

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


@traceable(name="search_chunks")
def search_chunks(
    query: str,
    top_k: int = 5,
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
    openrouter_key: Optional[str] = None
) -> list[SearchResult]:
    """
    Search for relevant chunks across all books.

    Retrieves top_k results from each book, then combines and reranks.
    """
    # Get credentials
    supabase_url = supabase_url or os.getenv('SUPABASE_URL')
    supabase_key = supabase_key or os.getenv('SUPABASE_PUBLISHABLE_KEY')
    openrouter_key = openrouter_key or os.getenv('OPENROUTER_API_KEY')

    # Initialize services
    supabase = create_client(supabase_url, supabase_key)
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
    final_results = all_results[:top_k * 2]  # Return more for LLM context

    # Log results summary for LangSmith observability
    from langsmith.run_helpers import get_current_run_tree
    run = get_current_run_tree()
    if run:
        run.extra = run.extra or {}
        run.extra["metadata"] = {
            "results": [
                {"source_ref": r.source_ref, "book": r.book, "similarity": round(r.similarity, 4)}
                for r in final_results
            ]
        }

    return final_results

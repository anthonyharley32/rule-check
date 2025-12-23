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

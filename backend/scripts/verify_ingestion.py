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

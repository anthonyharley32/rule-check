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

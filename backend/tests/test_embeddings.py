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

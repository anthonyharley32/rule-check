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

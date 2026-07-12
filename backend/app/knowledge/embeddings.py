"""
Embedding Service — Generates vector embeddings for KB documents.
Uses sentence-transformers for local embedding generation.
"""

from typing import List


class EmbeddingService:
    """Generates text embeddings for vector search."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.dimension = 384  # MiniLM default
        self._load_model()

    def _load_model(self):
        """Attempt to load sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(self.model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
        except ImportError:
            raise RuntimeError("sentence-transformers is required but not installed.")
        except Exception as e:
            raise RuntimeError(f"Failed to load embedding model: {e}")

    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text string."""
        if not self.model:
            raise RuntimeError("Embedding model is not loaded.")
        return self.model.encode(text).tolist()

    async def embed_async(self, text: str) -> List[float]:
        """Generate embedding asynchronously."""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed, text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        if not self.model:
            raise RuntimeError("Embedding model is not loaded.")
        return [e.tolist() for e in self.model.encode(texts)]

    async def embed_batch_async(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch asynchronously."""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed_batch, texts)

    def chunk_text(
        self, text: str, chunk_size: int = 500, overlap: int = 50
    ) -> List[str]:
        """Split text into overlapping chunks for embedding."""
        words = text.split()
        chunks = []
        i = 0
        while i < len(words):
            chunk = " ".join(words[i : i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
            i += chunk_size - overlap
        return chunks if chunks else [text[:2000]]


# Singleton
embedding_service = EmbeddingService()

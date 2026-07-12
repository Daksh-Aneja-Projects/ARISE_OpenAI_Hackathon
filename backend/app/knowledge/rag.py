"""
RAG Pipeline — Dual-backend semantic search against Knowledge Base documents.

Storage backends (auto-selected at startup):
  1. pgvector  — PostgreSQL + pgvector extension (PGVECTOR_URL set in .env)
                 Multi-process safe, persistent, production-grade.
                 Embeddings survive restarts and scale horizontally.
  2. File cache — JSON on disk (knowledge_base/.rag_cache.json)
                 Single-process, zero dependencies, good for dev/local.

Both backends implement identical retrieval semantics:
  - Cosine similarity scoring
  - Outcome weighting (won=1.5x, lost=0.8x)
  - Recency boost (+3% for docs ingested in last 30 days)
  - Collection filtering
  - Top-K retrieval with confidence threshold

The singleton `rag_pipeline` auto-selects the best available backend.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

# ─── Text normalization ────────────────────────────────────────────────────


def _normalize_text(text: str) -> str:
    """BUG-05 fix: normalize CRLF, strip BOM, collapse excessive whitespace."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\ufeff\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    text = re.sub(r" {3,}", "  ", text)
    return text.strip()


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _apply_weights(score: float, metadata: dict, now: float) -> float:
    """Apply outcome and recency weights — identical for both backends."""
    if metadata.get("outcome") == "won":
        score *= 1.5
    elif metadata.get("outcome") == "lost":
        score *= 0.8
    ingested_at = metadata.get("ingested_at", 0)
    if ingested_at and (now - ingested_at) < 30 * 86400:
        score *= 1.03
    return score


# ─── Abstract backend ──────────────────────────────────────────────────────


class RAGBackend(ABC):
    """Abstract interface for RAG storage backends."""

    @abstractmethod
    def add_embedding(
        self,
        doc_id: str,
        chunk_text: str,
        embedding: List[float],
        metadata: Optional[Dict] = None,
    ): ...

    @abstractmethod
    def invalidate_doc(self, doc_id: str): ...

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        top_k: int,
        collection_filter: Optional[str],
        confidence_threshold: float,
    ) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def stats(self) -> Dict[str, Any]: ...


# ─── File-cache backend (default / dev) ───────────────────────────────────


_CACHE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "knowledge_base",
    ".rag_cache.json",
)


class FileCacheBackend(RAGBackend):
    """JSON-file-based embedding store. Single-process, zero dependencies."""

    def __init__(self):
        self.embeddings_store: List[Dict[str, Any]] = []
        self._load_cache()

    def _load_cache(self):
        try:
            if os.path.isfile(_CACHE_PATH):
                with open(_CACHE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.embeddings_store = data.get("embeddings", [])
                print(
                    f"[RAG/file] Loaded {len(self.embeddings_store)} embeddings from cache"
                )
        except Exception as e:
            print(f"[RAG/file] Cache load failed (starting fresh): {e}")
            self.embeddings_store = []

    def _save_cache(self):
        try:
            os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
            with open(_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(
                    {"embeddings": self.embeddings_store, "saved_at": time.time()}, f
                )
        except Exception as e:
            print(f"[RAG/file] Cache save failed: {e}")

    def add_embedding(
        self,
        doc_id: str,
        chunk_text: str,
        embedding: List[float],
        metadata: Optional[Dict] = None,
    ):
        normalized = _normalize_text(chunk_text)
        if not normalized:
            return
        self.embeddings_store.append(
            {
                "doc_id": doc_id,
                "chunk_text": normalized,
                "embedding": embedding,
                "metadata": {**(metadata or {}), "ingested_at": time.time()},
            }
        )
        self._save_cache()

    def invalidate_doc(self, doc_id: str):
        before = len(self.embeddings_store)
        self.embeddings_store = [
            e for e in self.embeddings_store if e["doc_id"] != doc_id
        ]
        if len(self.embeddings_store) < before:
            self._save_cache()

    async def search(
        self,
        query_embedding: List[float],
        top_k: int,
        collection_filter: Optional[str],
        confidence_threshold: float,
    ) -> List[Dict[str, Any]]:
        now = time.time()
        results = []
        for entry in self.embeddings_store:
            if (
                collection_filter
                and entry["metadata"].get("collection") != collection_filter
            ):
                continue
            score = cosine_similarity(query_embedding, entry["embedding"])
            score = _apply_weights(score, entry["metadata"], now)
            if score >= confidence_threshold:
                results.append(
                    {
                        "doc_id": entry["doc_id"],
                        "chunk_text": entry["chunk_text"],
                        "score": round(score, 4),
                        "metadata": entry["metadata"],
                    }
                )
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def stats(self) -> Dict[str, Any]:
        by_col: dict = {}
        for e in self.embeddings_store:
            col = e["metadata"].get("collection", "unknown")
            by_col[col] = by_col.get(col, 0) + 1
        return {
            "backend": "file_cache",
            "total_chunks": len(self.embeddings_store),
            "by_collection": by_col,
            "cache_path": _CACHE_PATH,
        }

    @property
    def chunk_count(self) -> int:
        return len(self.embeddings_store)


# ─── pgvector backend (production) ────────────────────────────────────────


class PgVectorBackend(RAGBackend):
    """PostgreSQL + pgvector backend. Multi-process safe, horizontally scalable.

    Schema (auto-created on first use):
      CREATE EXTENSION IF NOT EXISTS vector;
      CREATE TABLE IF NOT EXISTS arise_embeddings (
        id         SERIAL PRIMARY KEY,
        doc_id     TEXT NOT NULL,
        chunk_text TEXT NOT NULL,
        embedding  vector(384),      -- dimension matches MiniLM
        metadata   JSONB NOT NULL DEFAULT '{}',
        ingested_at DOUBLE PRECISION NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())
      );
      CREATE INDEX IF NOT EXISTS idx_arise_embeddings_doc_id
        ON arise_embeddings(doc_id);
    """

    def __init__(self, url: str):
        # Convert asyncpg URL to psycopg2-compatible sync URL for pgvector ops
        self._url = url
        self._async_url = url
        self._ready = False
        self._dimension = 384  # MiniLM default — updated after first embed
        self._init_sync()

    def _sync_url(self) -> str:
        """Convert asyncpg URL to psycopg2 URL for sync operations."""
        u = self._url
        u = u.replace("postgresql+asyncpg://", "postgresql://")
        u = u.replace("postgres+asyncpg://", "postgresql://")
        return u

    def _init_sync(self):
        """Create schema on startup (sync, one-time)."""
        try:
            import psycopg2
            from psycopg2.extras import Json

            conn = psycopg2.connect(self._sync_url())
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS arise_embeddings (
                    id          SERIAL PRIMARY KEY,
                    doc_id      TEXT NOT NULL,
                    chunk_text  TEXT NOT NULL,
                    embedding   vector(384),
                    metadata    JSONB NOT NULL DEFAULT '{}',
                    ingested_at DOUBLE PRECISION NOT NULL
                                DEFAULT EXTRACT(EPOCH FROM NOW())
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_arise_embeddings_doc_id
                    ON arise_embeddings(doc_id);
            """)
            # IVFFlat index for ANN search (builds automatically when rows >= 100)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_arise_embeddings_ivfflat
                    ON arise_embeddings USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
            """)
            conn.close()
            self._ready = True
            print("[RAG/pgvector] Schema ready")
        except ImportError:
            print("[RAG/pgvector] psycopg2 not installed — falling back to file cache")
            self._ready = False
        except Exception as e:
            print(f"[RAG/pgvector] Init failed ({e}) — falling back to file cache")
            self._ready = False

    def add_embedding(
        self,
        doc_id: str,
        chunk_text: str,
        embedding: List[float],
        metadata: Optional[Dict] = None,
    ):
        if not self._ready:
            return
        try:
            import psycopg2
            import json as _json

            meta = {**(metadata or {}), "ingested_at": time.time()}
            vec_str = "[" + ",".join(str(v) for v in embedding) + "]"
            conn = psycopg2.connect(self._sync_url())
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO arise_embeddings (doc_id, chunk_text, embedding, metadata, ingested_at) "
                "VALUES (%s, %s, %s::vector, %s, %s)",
                (
                    doc_id,
                    _normalize_text(chunk_text),
                    vec_str,
                    _json.dumps(meta),
                    meta["ingested_at"],
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[RAG/pgvector] add_embedding failed: {e}")

    def invalidate_doc(self, doc_id: str):
        if not self._ready:
            return
        try:
            import psycopg2

            conn = psycopg2.connect(self._sync_url())
            cur = conn.cursor()
            cur.execute("DELETE FROM arise_embeddings WHERE doc_id = %s", (doc_id,))
            conn.commit()
            conn.close()
            print(f"[RAG/pgvector] Invalidated doc {doc_id}")
        except Exception as e:
            print(f"[RAG/pgvector] invalidate_doc failed: {e}")

    async def search(
        self,
        query_embedding: List[float],
        top_k: int,
        collection_filter: Optional[str],
        confidence_threshold: float,
    ) -> List[Dict[str, Any]]:
        if not self._ready:
            return []
        try:
            import asyncio
            import psycopg2

            def _sync_search():
                vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
                # Fetch top_k * 5 candidates via ANN, then re-rank with weights
                fetch_k = top_k * 5
                conn = psycopg2.connect(self._sync_url())
                cur = conn.cursor()
                if collection_filter:
                    cur.execute(
                        "SELECT doc_id, chunk_text, metadata, ingested_at, "
                        "1 - (embedding <=> %s::vector) AS cosine_score "
                        "FROM arise_embeddings "
                        "WHERE metadata->>'collection' = %s "
                        "ORDER BY embedding <=> %s::vector "
                        f"LIMIT {fetch_k}",
                        (vec_str, collection_filter, vec_str),
                    )
                else:
                    cur.execute(
                        "SELECT doc_id, chunk_text, metadata, ingested_at, "
                        "1 - (embedding <=> %s::vector) AS cosine_score "
                        "FROM arise_embeddings "
                        "ORDER BY embedding <=> %s::vector "
                        f"LIMIT {fetch_k}",
                        (vec_str, vec_str),
                    )
                rows = cur.fetchall()
                conn.close()
                return rows

            rows = await asyncio.to_thread(_sync_search)
            now = time.time()
            results = []
            for doc_id, chunk_text, meta_raw, ingested_at, cosine_score in rows:
                meta = (
                    meta_raw
                    if isinstance(meta_raw, dict)
                    else json.loads(meta_raw or "{}")
                )
                meta["ingested_at"] = ingested_at
                score = _apply_weights(float(cosine_score), meta, now)
                if score >= confidence_threshold:
                    results.append(
                        {
                            "doc_id": doc_id,
                            "chunk_text": chunk_text,
                            "score": round(score, 4),
                            "metadata": meta,
                        }
                    )
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]
        except Exception as e:
            print(f"[RAG/pgvector] search failed: {e}")
            return []

    def stats(self) -> Dict[str, Any]:
        if not self._ready:
            return {"backend": "pgvector", "status": "unavailable"}
        try:
            import psycopg2

            conn = psycopg2.connect(self._sync_url())
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM arise_embeddings")
            total = cur.fetchone()[0]
            cur.execute(
                "SELECT metadata->>'collection', COUNT(*) "
                "FROM arise_embeddings GROUP BY metadata->>'collection'"
            )
            by_col = {row[0] or "unknown": row[1] for row in cur.fetchall()}
            conn.close()
            return {
                "backend": "pgvector",
                "total_chunks": total,
                "by_collection": by_col,
            }
        except Exception as e:
            return {"backend": "pgvector", "error": str(e)}

    @property
    def chunk_count(self) -> int:
        s = self.stats()
        return s.get("total_chunks", 0)


# ─── Unified RAG Pipeline ──────────────────────────────────────────────────


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline.

    Auto-selects backend:
      - If PGVECTOR_URL is set and psycopg2 is installed → pgvector
      - Otherwise → file cache (JSON on disk)

    All agents interact with this class identically regardless of backend.
    """

    def __init__(self, confidence_threshold: float = 0.5):
        self.confidence_threshold = confidence_threshold
        self._backend: RAGBackend = self._select_backend()

    def _select_backend(self) -> RAGBackend:
        from app.config import settings

        pgurl = getattr(settings, "PGVECTOR_URL", "").strip()
        if pgurl:
            backend = PgVectorBackend(pgurl)
            if backend._ready:
                print("[RAG] Using pgvector backend (multi-process, persistent)")
                return backend
            else:
                print("[RAG] pgvector unavailable — falling back to file cache")
        print("[RAG] Using file-cache backend (dev mode)")
        return FileCacheBackend()

    # ── Passthrough to backend ─────────────────────────────────────────────

    def add_embedding(
        self,
        doc_id: str,
        chunk_text: str,
        embedding: List[float],
        metadata: Optional[Dict] = None,
    ):
        self._backend.add_embedding(doc_id, chunk_text, embedding, metadata)

    def invalidate_doc(self, doc_id: str):
        self._backend.invalidate_doc(doc_id)

    def preprocess_text(self, raw_text: str) -> str:
        return _normalize_text(raw_text)

    @property
    def embeddings_store(self) -> list:
        """Backward-compat shim — agents check len(rag_pipeline.embeddings_store)."""
        if isinstance(self._backend, FileCacheBackend):
            return self._backend.embeddings_store
        # For pgvector, return a proxy list of the right length
        return [None] * self._backend.chunk_count

    # ── Retrieval ──────────────────────────────────────────────────────────

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        collection_filter: Optional[str] = None,
        outcome_weight: float = 1.5,
    ) -> List[Dict[str, Any]]:
        """Semantic search — outcome_weight param kept for API compat but baked into backend."""
        return await self._backend.search(
            query_embedding, top_k, collection_filter, self.confidence_threshold
        )

    async def search_with_context(
        self,
        query_embedding: List[float],
        context: str = "",
        top_k: int = 5,
        collection_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        results = await self.search(query_embedding, top_k, collection_filter)
        context_chunks = []
        sources = []
        for r in results:
            context_chunks.append(
                f"[Source: {r['metadata'].get('filename', 'Unknown')} | Score: {r['score']}]\n{r['chunk_text']}"
            )
            sources.append(
                {
                    "doc_id": r["doc_id"],
                    "filename": r["metadata"].get("filename", "Unknown"),
                    "collection": r["metadata"].get("collection", ""),
                    "score": r["score"],
                }
            )
        return {
            "context": "\n\n---\n\n".join(context_chunks),
            "sources": sources,
            "result_count": len(results),
        }

    def stats(self) -> Dict[str, Any]:
        return self._backend.stats()


# Singleton — imported by all agents and upload handlers
rag_pipeline = RAGPipeline()

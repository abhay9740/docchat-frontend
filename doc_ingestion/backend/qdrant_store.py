from __future__ import annotations

import uuid

import structlog

log = structlog.get_logger(__name__)

try:
    from qdrant_client import QdrantClient
    from qdrant_client import models as qmodels
    _QDRANT_AVAILABLE = True
except Exception:
    QdrantClient = None  # type: ignore[assignment,misc]
    qmodels = None  # type: ignore[assignment]
    _QDRANT_AVAILABLE = False


class QdrantStore:
    """
    Manages one Qdrant collection for chunk vectors.

    Lifecycle per ingest:
      1. ensure_collection()       — creates collection if absent (auto-creates)
      2. upsert_batch()            — writes new points with UUID IDs, tagged by generation
      3. delete_old_generations()  — prunes all points from prior generations so the
                                     collection does not grow unboundedly

    Point IDs are UUIDs to avoid the integer overflow issue with gen*1_000_000+idx.
    Generation is stored in the payload for filtering on both search and delete.
    """

    def __init__(self, url: str, api_key: str, collection: str) -> None:
        if not _QDRANT_AVAILABLE:
            raise RuntimeError(
                "qdrant-client is not installed. Add it to requirements.txt."
            )
        self._collection = collection
        self._client = QdrantClient(url=url, api_key=api_key)

    # ── Collection management ──────────────────────────────────────────────────

    def ensure_collection(self, vector_size: int) -> None:
        """Create the collection if it does not exist yet."""
        if self._client.collection_exists(self._collection):
            return
        self._client.create_collection(
            collection_name=self._collection,
            vectors_config=qmodels.VectorParams(
                size=vector_size,
                distance=qmodels.Distance.COSINE,
            ),
        )
        log.info(
            "qdrant.collection_created",
            collection=self._collection,
            vector_size=vector_size,
        )

    def delete_old_generations(self, current_generation: int) -> None:
        """
        Delete all points whose generation != current_generation.
        Called after a successful upsert to keep the collection lean.
        """
        if current_generation <= 0:
            return
        try:
            self._client.delete(
                collection_name=self._collection,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must_not=[
                            qmodels.FieldCondition(
                                key="generation",
                                match=qmodels.MatchValue(value=current_generation),
                            )
                        ]
                    )
                ),
            )
        except Exception as exc:
            log.error("qdrant.delete_old_generations_failed", error=str(exc))

    # ── Write ──────────────────────────────────────────────────────────────────

    def upsert_batch(
        self,
        generation: int,
        chunks: list[str],
        vectors: list[list[float]],
    ) -> None:
        """Upsert all chunk vectors in a single Qdrant call."""
        if len(chunks) != len(vectors):
            raise ValueError(
                f"chunks/vectors length mismatch: {len(chunks)} vs {len(vectors)}"
            )
        points = [
            qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector=vectors[idx],
                payload={
                    "text": chunks[idx],
                    "chunk_index": idx,
                    "generation": generation,
                },
            )
            for idx in range(len(chunks))
        ]
        self._client.upsert(collection_name=self._collection, points=points)

    # ── Search ─────────────────────────────────────────────────────────────────

    def search(
        self,
        query_vector: list[float],
        generation: int,
        limit: int,
    ) -> list[dict]:
        """
        Return up to `limit` nearest neighbours for the current generation.
        Falls back to an empty list (not an exception) on any Qdrant error so
        RAGEngine can degrade gracefully to graph-only retrieval.
        """
        try:
            hits = self._client.search(
                collection_name=self._collection,
                query_vector=query_vector,
                limit=limit,
                query_filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="generation",
                            match=qmodels.MatchValue(value=generation),
                        )
                    ]
                ),
                with_payload=True,
            )
            results: list[dict] = []
            for hit in hits:
                payload = hit.payload or {}
                idx = payload.get("chunk_index")
                text = payload.get("text")
                if idx is None or text is None:
                    continue
                results.append(
                    {"chunk_index": int(idx), "text": str(text), "score": float(hit.score)}
                )
            return results
        except Exception as exc:
            log.error("qdrant.search_failed", error=str(exc))
            return []

    # ── Health ─────────────────────────────────────────────────────────────────

    def ping(self) -> bool:
        try:
            self._client.get_collections()
            return True
        except Exception:
            return False

    def status(self, generation: int) -> dict:
        try:
            exists = self._client.collection_exists(self._collection)
            points_count = 0
            if exists:
                info = self._client.get_collection(self._collection)
                points_count = int(getattr(info, "points_count", 0) or 0)
            return {
                "provider": "qdrant",
                "collection": self._collection,
                "collection_exists": exists,
                "points_count": points_count,
                "generation": generation,
                "detail": "Qdrant vector index active.",
            }
        except Exception as exc:
            return {
                "provider": "qdrant",
                "collection": self._collection,
                "collection_exists": False,
                "error": str(exc),
            }

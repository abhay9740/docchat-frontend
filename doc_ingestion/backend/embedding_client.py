from __future__ import annotations

import structlog
from huggingface_hub import InferenceClient

log = structlog.get_logger(__name__)


class EmbeddingClient:
    """
    Wraps HuggingFace InferenceClient for batch text embedding.

    A single InferenceClient instance is reused across all calls
    (fixes original bug: new client was created per chunk).

    embed_batch() sends texts in configurable batches, calling the HF
    feature_extraction endpoint once per batch instead of once per text.
    """

    def __init__(self, model: str, hf_token: str, batch_size: int = 32) -> None:
        if not hf_token:
            raise ValueError("HF_TOKEN is required for EmbeddingClient")
        self._model = model
        self._batch_size = batch_size
        self._client = InferenceClient(api_key=hf_token)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of texts, batching HF API calls.
        Returns one float vector per input text.
        Raises RuntimeError on API failure.
        """
        if not texts:
            return []
        results: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            results.extend(self._embed_one_batch(batch))
        return results

    def embed_single(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    # ── Internal ──────────────────────────────────────────────────────────────

    def _embed_one_batch(self, texts: list[str]) -> list[list[float]]:
        raw = self._client.feature_extraction(texts, model=self._model)

        # Normalise numpy arrays to plain Python lists
        if hasattr(raw, "tolist"):
            raw = raw.tolist()

        if not raw:
            raise RuntimeError("Embedding API returned an empty response")

        # Single-text call: API may return a flat 1-D list of floats
        if isinstance(raw[0], (int, float)):
            return [[float(x) for x in raw]]

        # Batch call: raw is list[vector]; each vector may be an array or a nested list
        vectors: list[list[float]] = []
        for vec in raw:
            if hasattr(vec, "tolist"):
                vec = vec.tolist()
            # Guard against unexpected double-nesting
            if vec and isinstance(vec[0], list):
                vec = vec[0]
            vectors.append([float(x) for x in vec])
        return vectors

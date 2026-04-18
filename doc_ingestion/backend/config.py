from __future__ import annotations

import os
from dataclasses import dataclass, field

# ── Ingest-state constants ──────────────────────────────────────────────────
STATE_IDLE = "idle"
STATE_RUNNING = "running"
STATE_DONE = "done"
STATE_ERROR = "error"

# ── Backend constants ───────────────────────────────────────────────────────
BACKEND_GRAPH = "knowledge_graph"
BACKEND_QDRANT = "qdrant"
_QDRANT_ALIASES: frozenset[str] = frozenset({"qdrant", "vector", "vector_db"})

FALLBACK_LLM_MODELS: list[str] = [
    "Qwen/Qwen2.5-72B-Instruct",
    "meta-llama/Llama-3.3-70B-Instruct",
    "mistralai/Mistral-Small-24B-Instruct-2501",
]


@dataclass(frozen=True)
class Config:
    """All runtime configuration loaded once from environment variables."""

    # Retrieval
    retrieval_backend: str = field(
        default_factory=lambda: os.environ.get("RETRIEVAL_BACKEND", "graph").lower()
    )
    embed_provider: str = field(
        default_factory=lambda: os.environ.get("EMBED_PROVIDER", "hf").lower()
    )

    # Qdrant
    qdrant_url: str = field(
        default_factory=lambda: os.environ.get("QDRANT_URL", "").strip()
    )
    qdrant_api_key: str = field(
        default_factory=lambda: os.environ.get("QDRANT_API_KEY", "").strip()
    )
    qdrant_collection: str = field(
        default_factory=lambda: (
            os.environ.get("QDRANT_COLLECTION", "docchat_chunks").strip()
            or "docchat_chunks"
        )
    )

    # Embeddings
    embedding_model: str = field(
        default_factory=lambda: os.environ.get(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ).strip()
    )
    embedding_batch_size: int = field(
        default_factory=lambda: int(os.environ.get("EMBEDDING_BATCH_SIZE", "32"))
    )

    # Graph
    graph_hop_limit: int = field(
        default_factory=lambda: int(os.environ.get("GRAPH_HOP_LIMIT", "1"))
    )
    graph_per_node_limit: int = field(
        default_factory=lambda: int(os.environ.get("GRAPH_PER_NODE_LIMIT", "6"))
    )

    # Retrieval thresholds
    retrieve_min_score: float = field(
        default_factory=lambda: float(os.environ.get("RETRIEVE_MIN_SCORE", "0.15"))
    )
    retrieve_relative_ratio: float = field(
        default_factory=lambda: float(os.environ.get("RETRIEVE_RELATIVE_RATIO", "0.35"))
    )

    # Hybrid scoring weights (Qdrant + graph)
    hybrid_vector_weight: float = field(
        default_factory=lambda: float(os.environ.get("HYBRID_VECTOR_WEIGHT", "0.6"))
    )
    hybrid_graph_weight: float = field(
        default_factory=lambda: float(os.environ.get("HYBRID_GRAPH_WEIGHT", "0.4"))
    )

    # LLM
    hf_token: str = field(
        default_factory=lambda: os.environ.get("HF_TOKEN", "")
    )
    llm_model: str = field(
        default_factory=lambda: os.environ.get(
            "LLM_MODEL", "Qwen/Qwen2.5-72B-Instruct"
        )
    )

    @property
    def wants_qdrant(self) -> bool:
        return (
            self.retrieval_backend in _QDRANT_ALIASES
            or self.retrieval_backend == BACKEND_QDRANT
        )

    @property
    def qdrant_configured(self) -> bool:
        return bool(self.qdrant_url and self.qdrant_api_key)

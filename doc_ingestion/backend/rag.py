from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass

import structlog
from huggingface_hub import InferenceClient
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import (
    BACKEND_GRAPH,
    BACKEND_QDRANT,
    FALLBACK_LLM_MODELS,
    STATE_DONE,
    STATE_ERROR,
    STATE_IDLE,
    STATE_RUNNING,
    Config,
)
from .embedding_client import EmbeddingClient
from .graph_index import GraphIndex, extract_entities, extract_terms
from .qdrant_store import QdrantStore

log = structlog.get_logger(__name__)

SYSTEM_PROMPT = """\
You are a Graph-RAG reasoning engine.

Your job is NOT to answer directly from text.
Your job is to construct answers by traversing entity relationships.

STRICT RULES:

1. ENTITY EXTRACTION
   - Identify all entities in the question.
   - Do not answer yet.

2. RELATIONSHIP TRAVERSAL
   - Use retrieved context to find explicit relationships between entities.
   - Build a step-by-step path using only these relationships.

3. MULTI-HOP ENFORCEMENT
   - If the question requires multiple steps, you MUST show intermediate entities.
   - Do NOT skip steps even if the answer is obvious.

4. NO SHORTCUTS
   - Do NOT answer from a single chunk if it contains the full answer.
   - You MUST validate at least one intermediate relationship (bridge).

5. FAITHFULNESS
   - Use ONLY retrieved context. Do NOT use prior knowledge.
   - If the path cannot be constructed -> return INSUFFICIENT_CONTEXT.

6. NEGATIVE GUARD
   - If the question asks for unknown/private/unsupported info -> return INSUFFICIENT_CONTEXT.

7. OUTPUT FORMAT (MANDATORY) - Return JSON ONLY:
{
  "answer": "...",
  "reasoning_type": "direct | multi-hop | insufficient",
  "path": ["Entity1 -> Entity2", "Entity2 -> Entity3"],
  "used_chunks": ["0", "1"],
  "justification": "Explain briefly how the path leads to the answer using retrieved data only."
}

8. FAILURE CONDITIONS - Return:
{
  "answer": "INSUFFICIENT_CONTEXT",
  "reasoning_type": "insufficient",
  "path": [],
  "used_chunks": [],
  "justification": "No valid relationship path found in retrieved context."
}
IF: No relationship path exists | Only one-hop shortcut found | Information is missing
"""


@dataclass
class RetrievedChunk:
    index: int
    score: float
    text: str


class RAGEngine:
    """
    Orchestrates chunking, graph indexing, vector storage, and LLM answering.

    Modes
    -----
    knowledge_graph  Pure in-memory graph. No external dependencies.
    qdrant           Qdrant vector search + graph re-scoring (hybrid).
                     Falls back to knowledge_graph if Qdrant is unreachable.

    Public API is fully backward-compatible with the original single-class design.
    """

    def __init__(
        self,
        embed_provider: str = "hf",
        retrieval_backend: str = "graph",
        chunk_size: int = 180,
        chunk_overlap: int = 40,
        top_k: int = 3,
        llm_model: str | None = None,
    ) -> None:
        self._cfg = Config()

        # Mutable runtime params
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k
        self.llm_model = llm_model or self._cfg.llm_model

        # Resolved for external callers / API responses
        self.embed_provider: str = self._cfg.embed_provider
        self.retrieval_backend: str = BACKEND_GRAPH

        self.chunks: list[str] = []
        self._ingest_progress: dict = {"state": STATE_IDLE, "embedded": 0, "total": 0}
        self._ingest_generation: int = 0
        self._gen_lock = threading.Lock()

        self._graph = GraphIndex(
            hop_limit=self._cfg.graph_hop_limit,
            per_node_limit=self._cfg.graph_per_node_limit,
        )
        self._embedder: EmbeddingClient | None = None
        self._qdrant: QdrantStore | None = None

        self._init_backends()
        log.info("rag_engine.started", backend=self.retrieval_backend)

    # ── Backend initialisation ─────────────────────────────────────────────────

    def _init_backends(self) -> None:
        if not self._cfg.wants_qdrant:
            return

        if not self._cfg.hf_token:
            log.warning("qdrant.skipped", reason="HF_TOKEN missing")
            return

        try:
            self._embedder = EmbeddingClient(
                model=self._cfg.embedding_model,
                hf_token=self._cfg.hf_token,
                batch_size=self._cfg.embedding_batch_size,
            )
        except Exception as exc:
            log.error("embedding_client.init_failed", error=str(exc))
            return

        if not self._cfg.qdrant_configured:
            log.warning("qdrant.skipped", reason="QDRANT_URL or QDRANT_API_KEY missing")
            return

        try:
            self._qdrant = QdrantStore(
                url=self._cfg.qdrant_url,
                api_key=self._cfg.qdrant_api_key,
                collection=self._cfg.qdrant_collection,
            )
            self.retrieval_backend = BACKEND_QDRANT
            log.info("qdrant.enabled", collection=self._cfg.qdrant_collection)
        except Exception as exc:
            log.error("qdrant.init_failed", error=str(exc))
            self._embedder = None

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def ingest_progress(self) -> dict:
        return dict(self._ingest_progress)

    @property
    def is_ready(self) -> bool:
        return bool(self.chunks) and self._ingest_progress.get("state") != STATE_RUNNING

    # ── Status ────────────────────────────────────────────────────────────────

    def vector_store_status(self) -> dict:
        base = {
            "is_ready": self.is_ready,
            "loaded_chunks": len(self.chunks),
            "ingest_state": self._ingest_progress.get("state", STATE_IDLE),
        }
        if self._qdrant is not None:
            return {**base, **self._qdrant.status(self._ingest_generation)}
        gs = self._graph.status()
        return {
            **base,
            "provider": "knowledge_graph",
            "graph_nodes": gs["graph_nodes"],
            "graph_edges": gs["graph_edges"],
            "detail": "GraphRAG index active. Retrieval is entity and relation based.",
        }

    def graph_store_status(self) -> dict:
        gs = self._graph.status()
        return {
            "provider": "knowledge_graph",
            "is_ready": self.is_ready,
            "loaded_chunks": len(self.chunks),
            "ingest_state": self._ingest_progress.get("state", STATE_IDLE),
            "graph_nodes": gs["graph_nodes"],
            "graph_edges": gs["graph_edges"],
            "active_backend": self.retrieval_backend,
            "detail": "Graph index status.",
        }

    def graph_data(self, max_nodes: int = 200, max_edges: int = 500) -> dict:
        log.info("rag.graph_data.called", max_nodes=max_nodes, max_edges=max_edges)
        try:
            self._graph.export_graph_data(max_nodes=max_nodes, max_edges=max_edges)
        except Exception as exc:
            log.error("rag.graph_data_failed", error=str(exc))
            raise

    def health(self) -> dict:
        qdrant_ok: bool | None = self._qdrant.ping() if self._qdrant else None
        return {
            "status": "degraded" if qdrant_ok is False else "ok",
            "ingest_state": self._ingest_progress.get("state", STATE_IDLE),
            "retrieval_backend": self.retrieval_backend,
            "qdrant_reachable": qdrant_ok,
        }

    # ── Ingest ────────────────────────────────────────────────────────────────

    def start_ingest(self, text: str) -> int:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        self.chunks = splitter.split_text(text)
        with self._gen_lock:
            self._ingest_generation += 1
        total = len(self.chunks)
        self._ingest_progress = {"state": STATE_RUNNING, "embedded": 0, "total": total}
        return total

    def ingest(self, text: str) -> int:
        n = self.start_ingest(text)
        self._do_embed()
        return n

    def _do_embed(self) -> None:
        if self._qdrant is not None and self._embedder is not None:
            self._do_embed_qdrant()
        else:
            self._do_embed_graph()

    def _do_embed_graph(self) -> None:
        gen = self._ingest_generation
        chunks = list(self.chunks)
        total = len(chunks)
        if total == 0:
            self._graph.clear()
            self._ingest_progress = {"state": STATE_DONE, "embedded": 0, "total": 0}
            return
        try:
            self._graph.build(chunks)
            # Only update progress if this generation hasn't been superseded
            if gen == self._ingest_generation:
                self._ingest_progress = {"state": STATE_DONE, "embedded": total, "total": total}
        except Exception as exc:
            log.error("graph.build_failed", error=str(exc))
            self._ingest_progress = {
                "state": STATE_ERROR, "embedded": 0, "total": total, "error": str(exc)
            }

    def _do_embed_qdrant(self) -> None:
        gen = self._ingest_generation
        chunks = list(self.chunks)
        total = len(chunks)
        if total == 0:
            self._ingest_progress = {"state": STATE_DONE, "embedded": 0, "total": 0}
            return
        try:
            # Always build graph; used for hybrid re-scoring during retrieval
            self._graph.build(chunks)

            # Re-check generation: if a newer ingest arrived during graph build, abort
            if gen != self._ingest_generation:
                return

            # Batch-embed all chunks in as few HF API calls as possible
            vectors = self._embedder.embed_batch(chunks)

            if gen != self._ingest_generation:
                return

            vector_size = len(vectors[0])
            self._qdrant.ensure_collection(vector_size)
            self._qdrant.upsert_batch(gen, chunks, vectors)
            # Prune stale points from previous ingests
            self._qdrant.delete_old_generations(gen)

            self._ingest_progress = {"state": STATE_DONE, "embedded": total, "total": total}
        except Exception as exc:
            log.error("qdrant.embed_failed", error=str(exc))
            self._ingest_progress = {
                "state": STATE_ERROR, "embedded": 0, "total": total, "error": str(exc)
            }

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        if not self.chunks:
            return []
        if self._qdrant is not None and self._embedder is not None:
            return self._retrieve_hybrid(query)
        return self._retrieve_graph(query)

    def _retrieve_graph(self, query: str) -> list[RetrievedChunk]:
        terms, entities = self._graph.extract_query_features(query)
        candidates = self._graph.retrieve(
            terms,
            entities,
            self.top_k,
            self._cfg.retrieve_min_score,
            self._cfg.retrieve_relative_ratio,
        )
        return [RetrievedChunk(index=c.index, score=c.score, text=c.text) for c in candidates]

    def _retrieve_hybrid(self, query: str) -> list[RetrievedChunk]:
        """
        True hybrid: Qdrant cosine similarity narrows candidates;
        graph scorer re-ranks them via entity path reasoning.
        Falls back to graph-only if Qdrant embedding or search fails.
        """
        try:
            qvec = self._embedder.embed_single(query)
        except Exception as exc:
            log.warning("hybrid.embed_query_failed", error=str(exc), action="fallback_to_graph")
            return self._retrieve_graph(query)

        hits = self._qdrant.search(qvec, self._ingest_generation, limit=self.top_k * 4)
        if not hits:
            log.warning("hybrid.qdrant_empty", action="fallback_to_graph")
            return self._retrieve_graph(query)

        terms, entities = self._graph.extract_query_features(query)
        candidate_indices = [h["chunk_index"] for h in hits]
        vector_scores = {h["chunk_index"]: h["score"] for h in hits}

        graph_candidates = self._graph.score_candidates(
            candidate_indices, terms, entities, list(self.chunks)
        )
        graph_scores = {c.index: c.score for c in graph_candidates}

        vw = self._cfg.hybrid_vector_weight
        gw = self._cfg.hybrid_graph_weight
        scored = [
            RetrievedChunk(
                index=idx,
                score=(vw * vector_scores.get(idx, 0.0)) + (gw * graph_scores.get(idx, 0.0)),
                text=self.chunks[idx],
            )
            for idx in candidate_indices
            if idx < len(self.chunks)
        ]
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[: self.top_k]

    # ── Confidence ────────────────────────────────────────────────────────────

    def _confidence_from_retrieved(self, retrieved: list[RetrievedChunk]) -> tuple[float, str]:
        top_score = float(retrieved[0].score) if retrieved else 0.0
        strong_support = sum(1 for c in retrieved if c.score >= 0.5)
        if top_score >= 0.75 and strong_support >= 2:
            return top_score, "High"
        if top_score >= 0.45:
            return top_score, "Medium"
        return top_score, "Low"

    # ── Answer ────────────────────────────────────────────────────────────────

    def answer(
        self,
        query: str,
        history: list[dict] | None = None,
        answer_mode: str = "balanced",
    ) -> dict:
        retrieved = self.retrieve(query)
        chunks_payload = [
            {"index": c.index, "score": round(c.score, 4), "text": c.text} for c in retrieved
        ]
        top_score, confidence_label = self._confidence_from_retrieved(retrieved)

        if answer_mode == "strict_grounded" and confidence_label == "Low":
            return {
                "answer": "INSUFFICIENT_CONTEXT",
                "chunks": chunks_payload,
                "model_used": None,
                "top_score": round(top_score, 4),
                "confidence_label": confidence_label,
                "reasoning_type": "insufficient",
                "path": [],
                "used_chunks": [],
                "justification": "Low retrieval confidence; no valid path found.",
            }

        if not self._cfg.hf_token:
            return {
                "answer": "HF_TOKEN not set.",
                "chunks": chunks_payload,
                "model_used": None,
                "top_score": round(top_score, 4),
                "confidence_label": confidence_label,
                "reasoning_type": "insufficient",
                "path": [],
                "used_chunks": [],
                "justification": "",
            }

        context_block = "\n\n".join(
            f"[chunk_id: {c.index}]\n{c.text}" for c in retrieved
        )
        messages = self._build_messages(query, context_block, history)
        return self._call_llm(messages, chunks_payload, top_score, confidence_label)

    def stream_answer(
        self,
        query: str,
        history: list[dict] | None = None,
        answer_mode: str = "balanced",
    ):
        retrieved = self.retrieve(query)
        chunks_payload = [
            {"index": c.index, "score": round(c.score, 4), "text": c.text} for c in retrieved
        ]
        top_score, confidence_label = self._confidence_from_retrieved(retrieved)
        yield {"type": "meta", "top_score": round(top_score, 4), "confidence_label": confidence_label}
        yield {"type": "chunks", "data": chunks_payload}

        if answer_mode == "strict_grounded" and confidence_label == "Low":
            yield {"type": "token", "data": "INSUFFICIENT_CONTEXT"}
            yield {
                "type": "done", "model_used": None,
                "reasoning_type": "insufficient", "path": [],
                "used_chunks": [], "justification": "Low retrieval confidence; no valid path found.",
            }
            return

        if not self._cfg.hf_token:
            yield {"type": "token", "data": "HF_TOKEN not set."}
            yield {
                "type": "done", "model_used": None, "reasoning_type": "insufficient",
                "path": [], "used_chunks": [], "justification": "",
            }
            return

        context_block = "\n\n".join(
            f"[chunk_id: {c.index}]\n{c.text}" for c in retrieved
        )
        messages = self._build_messages(query, context_block, history)
        full_text, model_used = self._buffer_llm(messages)
        graph_resp = self._parse_graph_response(full_text)
        answer_text = graph_resp.get("answer", full_text)

        for token_chunk in re.split(r"(\s+)", answer_text):
            if token_chunk:
                yield {"type": "token", "data": token_chunk}

        yield {
            "type": "done",
            "model_used": model_used,
            "reasoning_type": graph_resp.get("reasoning_type", "direct"),
            "path": graph_resp.get("path", []),
            "used_chunks": graph_resp.get("used_chunks", []),
            "justification": graph_resp.get("justification", ""),
        }

    # ── LLM helpers ───────────────────────────────────────────────────────────

    def _buffer_llm(self, messages: list[dict]) -> tuple[str, str | None]:
        client = InferenceClient(api_key=self._cfg.hf_token)
        candidates = list(dict.fromkeys([self.llm_model] + FALLBACK_LLM_MODELS))
        for model in candidates:
            try:
                resp = client.chat_completion(
                    model=model, messages=messages, max_tokens=600, temperature=0.2
                )
                return resp.choices[0].message.content, model
            except Exception as exc:
                log.warning("llm.model_failed", model=model, error=str(exc))
        return "All candidate models failed.", None

    def _call_llm(
        self,
        messages: list[dict],
        chunks_payload: list[dict],
        top_score: float,
        confidence_label: str,
    ) -> dict:
        client = InferenceClient(api_key=self._cfg.hf_token)
        candidates = list(dict.fromkeys([self.llm_model] + FALLBACK_LLM_MODELS))
        for model in candidates:
            try:
                resp = client.chat_completion(
                    model=model, messages=messages, max_tokens=600, temperature=0.2
                )
                raw = resp.choices[0].message.content
                graph_resp = self._parse_graph_response(raw)
                return {
                    "answer": graph_resp.get("answer", raw),
                    "chunks": chunks_payload,
                    "model_used": model,
                    "top_score": round(top_score, 4),
                    "confidence_label": confidence_label,
                    "reasoning_type": graph_resp.get("reasoning_type", "direct"),
                    "path": graph_resp.get("path", []),
                    "used_chunks": graph_resp.get("used_chunks", []),
                    "justification": graph_resp.get("justification", ""),
                }
            except Exception as exc:
                log.warning("llm.model_failed", model=model, error=str(exc))

        return {
            "answer": "All candidate models failed.",
            "chunks": chunks_payload,
            "model_used": None,
            "top_score": round(top_score, 4),
            "confidence_label": confidence_label,
            "reasoning_type": "insufficient",
            "path": [],
            "used_chunks": [],
            "justification": "All LLM candidates failed.",
        }

    def _parse_graph_response(self, text: str) -> dict:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {
            "answer": text.strip(),
            "reasoning_type": "direct",
            "path": [],
            "used_chunks": [],
            "justification": "JSON parse failed; raw answer returned.",
        }

    def _build_messages(
        self, query: str, context: str, history: list[dict] | None
    ) -> list[dict]:
        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        if history:
            messages.extend(
                {"role": m["role"], "content": m["content"]} for m in history
            )
        messages.append({
            "role": "user",
            "content": (
                f"Question:\n{query}\n\n"
                "Retrieved Context (use the chunk_id values in your used_chunks field):\n"
                f"{context}\n\n"
                "Instructions:\n"
                "- Step 1: Extract entities from the question.\n"
                "- Step 2: Traverse relationships across chunks to build a path.\n"
                "- Step 3: Return ONLY a valid JSON object matching the mandatory format.\n"
                "- Do NOT include any text outside the JSON object."
            ),
        })
        return messages

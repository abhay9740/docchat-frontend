import logging
import os
import re
import threading
from collections import Counter, defaultdict
from dataclasses import dataclass

from huggingface_hub import InferenceClient
from langchain_text_splitters import RecursiveCharacterTextSplitter

log = logging.getLogger(__name__)

FALLBACK_MODELS = [
    "Qwen/Qwen2.5-72B-Instruct",
    "meta-llama/Llama-3.3-70B-Instruct",
    "mistralai/Mistral-Small-24B-Instruct-2501",
]

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

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he", "in", "is", "it",
    "its", "of", "on", "that", "the", "to", "was", "were", "will", "with", "this", "these", "those",
    "or", "if", "then", "than", "into", "can", "could", "should", "would", "about", "over", "under",
    "after", "before", "between", "during", "also", "such", "their", "there", "them", "they", "you",
    "your", "we", "our", "i", "me", "my", "mine", "his", "her", "hers", "what", "which", "who",
    "whom", "when", "where", "why", "how", "do", "does", "did", "done", "not", "no", "yes",
}


@dataclass
class RetrievedChunk:
    index: int
    score: float
    text: str


class RAGEngine:
    def __init__(
        self,
        embed_provider: str = "graph",
        chunk_size: int = 180,
        chunk_overlap: int = 40,
        top_k: int = 3,
        llm_model: str = "Qwen/Qwen2.5-72B-Instruct",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k
        self.llm_model = llm_model
        self.embed_provider = "graph"
        self.chunks: list[str] = []

        self._ingest_progress: dict = {"state": "idle", "embedded": 0, "total": 0}
        self._graph_lock = threading.Lock()
        self._ingest_generation = 0

        self._chunk_terms: dict[int, Counter[str]] = {}
        self._chunk_entities: dict[int, set[str]] = {}
        self._entity_to_chunks: dict[str, set[int]] = defaultdict(set)
        self._entity_graph: dict[str, dict[str, float]] = defaultdict(dict)

    @property
    def ingest_progress(self) -> dict:
        return dict(self._ingest_progress)

    @property
    def is_ready(self) -> bool:
        return bool(self.chunks) and self._ingest_progress.get("state") != "running"

    def vector_store_status(self) -> dict:
        node_count = len(self._entity_to_chunks)
        edge_count = sum(len(v) for v in self._entity_graph.values()) // 2
        return {
            "provider": "knowledge_graph",
            "is_ready": self.is_ready,
            "loaded_chunks": len(self.chunks),
            "ingest_state": self._ingest_progress.get("state", "idle"),
            "graph_nodes": node_count,
            "graph_edges": edge_count,
            "detail": "GraphRAG index active. Retrieval is entity and relation based, not vector similarity.",
        }

    def ingest(self, text: str) -> int:
        self._do_split(text)
        self._do_embed()
        return len(self.chunks)

    def start_ingest(self, text: str) -> int:
        self._do_split(text)
        return len(self.chunks)

    def _do_split(self, text: str):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        self.chunks = splitter.split_text(text)
        self._ingest_generation += 1
        total = len(self.chunks)
        self._ingest_progress = {"state": "running", "embedded": 0, "total": total}
        log.info("Chunked into %d pieces (size=%d). Building graph index...", total, self.chunk_size)

    def _do_embed(self):
        gen = self._ingest_generation
        try:
            with self._graph_lock:
                if gen != self._ingest_generation:
                    return

                total = len(self.chunks)
                if total == 0:
                    self._clear_graph()
                    self._ingest_progress = {"state": "done", "embedded": 0, "total": 0}
                    return

                self._clear_graph()

                for idx, chunk in enumerate(self.chunks):
                    if gen != self._ingest_generation:
                        return

                    terms = self._extract_terms(chunk)
                    entities = self._extract_entities(chunk)
                    if not entities:
                        entities = set(terms[:5])

                    self._chunk_terms[idx] = Counter(terms)
                    self._chunk_entities[idx] = entities

                    for ent in entities:
                        self._entity_to_chunks[ent].add(idx)

                    ent_list = sorted(entities)
                    for i in range(len(ent_list)):
                        left = ent_list[i]
                        for j in range(i + 1, len(ent_list)):
                            right = ent_list[j]
                            w = 1.0 / max(len(ent_list), 1)
                            self._add_undirected_edge(left, right, w)

                    self._ingest_progress["embedded"] = idx + 1

                self._ingest_progress["state"] = "done"
                log.info(
                    "Graph index built: %d chunks, %d nodes, %d edges",
                    len(self.chunks),
                    len(self._entity_to_chunks),
                    sum(len(v) for v in self._entity_graph.values()) // 2,
                )
        except Exception as e:
            log.exception("Graph index build failed")
            self._ingest_progress = {"state": "error", "embedded": 0, "total": 0, "error": str(e)}

    def _clear_graph(self):
        self._chunk_terms = {}
        self._chunk_entities = {}
        self._entity_to_chunks = defaultdict(set)
        self._entity_graph = defaultdict(dict)

    def _add_undirected_edge(self, left: str, right: str, weight: float):
        self._entity_graph[left][right] = self._entity_graph[left].get(right, 0.0) + weight
        self._entity_graph[right][left] = self._entity_graph[right].get(left, 0.0) + weight

    def _extract_terms(self, text: str) -> list[str]:
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text.lower())
        return [t for t in tokens if t not in STOPWORDS]

    def _extract_entities(self, text: str) -> set[str]:
        entities: set[str] = set()

        for phrase in re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b", text):
            norm = phrase.strip().lower()
            if len(norm) > 2 and norm not in STOPWORDS:
                entities.add(norm)

        for acronym in re.findall(r"\b[A-Z]{2,}\b", text):
            entities.add(acronym.lower())

        terms = self._extract_terms(text)
        counts = Counter(terms)
        for token, count in counts.most_common(6):
            if count >= 2 and token not in STOPWORDS:
                entities.add(token)

        return entities

    def _expand_query_entities(self, query_entities: set[str], hop_limit: int = 1, per_node_limit: int = 6) -> set[str]:
        expanded = set(query_entities)
        frontier = set(query_entities)

        for _ in range(hop_limit):
            next_frontier: set[str] = set()
            for ent in frontier:
                neighbors = sorted(
                    self._entity_graph.get(ent, {}).items(),
                    key=lambda kv: kv[1],
                    reverse=True,
                )[:per_node_limit]
                for nbr, _weight in neighbors:
                    if nbr not in expanded:
                        expanded.add(nbr)
                        next_frontier.add(nbr)
            frontier = next_frontier
            if not frontier:
                break

        return expanded

    def _candidate_chunks(self, query_entities: set[str], expanded_entities: set[str]) -> set[int]:
        candidates: set[int] = set()
        for ent in expanded_entities:
            candidates.update(self._entity_to_chunks.get(ent, set()))

        if candidates:
            return candidates

        # No graph-entity match. Fall back to all chunks for lexical retrieval.
        return set(range(len(self.chunks)))

    def _keyword_overlap(self, query_terms: list[str], chunk_terms: Counter[str]) -> float:
        if not query_terms:
            return 0.0
        hit = sum(1 for t in set(query_terms) if t in chunk_terms)
        return hit / max(len(set(query_terms)), 1)

    def _entity_coverage(self, query_entities: set[str], chunk_entities: set[str]) -> float:
        if not query_entities:
            return 0.0
        inter = len(query_entities.intersection(chunk_entities))
        return inter / max(len(query_entities), 1)

    def _neighbor_support(self, query_entities: set[str], chunk_entities: set[str]) -> float:
        if not query_entities:
            return 0.0

        support = 0.0
        for q in query_entities:
            nbrs = self._entity_graph.get(q, {})
            if not nbrs:
                continue
            top = sorted(nbrs.items(), key=lambda kv: kv[1], reverse=True)[:8]
            total_weight = sum(w for _, w in top) or 1.0
            chunk_weight = sum(w for e, w in top if e in chunk_entities)
            support += chunk_weight / total_weight

        return support / max(len(query_entities), 1)

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        if not self.chunks:
            return []

        query_terms = self._extract_terms(query)
        query_entities = self._extract_entities(query)
        expanded = self._expand_query_entities(query_entities)
        candidates = self._candidate_chunks(query_entities, expanded)

        scored: list[RetrievedChunk] = []
        for idx in candidates:
            chunk_terms = self._chunk_terms.get(idx, Counter())
            chunk_entities = self._chunk_entities.get(idx, set())

            entity_score = self._entity_coverage(query_entities, chunk_entities)
            neighbor_score = self._neighbor_support(query_entities, chunk_entities)
            lexical_score = self._keyword_overlap(query_terms, chunk_terms)

            if query_entities:
                score = (0.55 * entity_score) + (0.25 * neighbor_score) + (0.20 * lexical_score)
            else:
                score = (0.85 * lexical_score) + (0.15 * (1.0 if chunk_entities else 0.0))

            if score > 0:
                scored.append(RetrievedChunk(index=idx, score=float(score), text=self.chunks[idx]))

        if not scored:
            return []

        scored.sort(key=lambda c: c.score, reverse=True)
        candidate_count = max(self.top_k * 4, self.top_k)
        candidates = scored[:candidate_count]

        top_score = candidates[0].score
        min_abs = float(os.environ.get("RETRIEVE_MIN_SCORE", "0.15"))
        min_ratio = float(os.environ.get("RETRIEVE_RELATIVE_RATIO", "0.35"))
        filtered = [c for c in candidates if c.score >= min_abs and c.score >= (top_score * min_ratio)]

        if not filtered:
            filtered = [candidates[0]]

        return filtered[: self.top_k]

    def _confidence_from_retrieved(self, retrieved: list[RetrievedChunk]) -> tuple[float, str]:
        top_score = float(retrieved[0].score) if retrieved else 0.0
        strong_support = sum(1 for c in retrieved if c.score >= 0.5)
        if top_score >= 0.75 and strong_support >= 2:
            return top_score, "High"
        if top_score >= 0.45:
            return top_score, "Medium"
        return top_score, "Low"

    def answer(self, query: str, history: list[dict] | None = None, answer_mode: str = "balanced") -> dict:
        retrieved = self.retrieve(query)
        chunks_payload = [{"index": c.index, "score": round(c.score, 4), "text": c.text} for c in retrieved]
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

        context_block = "\n\n".join(
            f"[chunk_id: {c.index}]\n{c.text}" for c in retrieved
        )

        hf_token = os.environ.get("HF_TOKEN")
        if not hf_token:
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

        messages = self._build_messages(query, context_block, history)
        return self._call_llm(hf_token, messages, chunks_payload, top_score, confidence_label)

    def stream_answer(self, query: str, history: list[dict] | None = None, answer_mode: str = "balanced"):
        retrieved = self.retrieve(query)
        chunks_payload = [{"index": c.index, "score": round(c.score, 4), "text": c.text} for c in retrieved]
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

        hf_token = os.environ.get("HF_TOKEN")
        if not hf_token:
            yield {"type": "token", "data": "HF_TOKEN not set."}
            yield {"type": "done", "model_used": None, "reasoning_type": "insufficient", "path": [], "used_chunks": [], "justification": ""}
            return

        context_block = "\n\n".join(
            f"[chunk_id: {c.index}]\n{c.text}" for c in retrieved
        )
        messages = self._build_messages(query, context_block, history)

        # Buffer full LLM output so we can parse the JSON before emitting clean answer tokens.
        full_text, model_used = self._buffer_llm(hf_token, messages)
        graph = self._parse_graph_response(full_text)
        answer_text = graph.get("answer", full_text)

        # Emit answer text word-by-word so the frontend stream still assembles naturally.
        for token_chunk in re.split(r'(\s+)', answer_text):
            if token_chunk:
                yield {"type": "token", "data": token_chunk}

        yield {
            "type": "done",
            "model_used": model_used,
            "reasoning_type": graph.get("reasoning_type", "direct"),
            "path": graph.get("path", []),
            "used_chunks": graph.get("used_chunks", []),
            "justification": graph.get("justification", ""),
        }

    def _buffer_llm(self, token: str, messages: list[dict]) -> tuple[str, str | None]:
        """Non-streaming call used by stream_answer to enable JSON parsing before token emission."""
        client = InferenceClient(api_key=token)
        candidates = list(dict.fromkeys([self.llm_model] + FALLBACK_MODELS))
        for model in candidates:
            try:
                resp = client.chat_completion(model=model, messages=messages, max_tokens=600, temperature=0.2)
                return resp.choices[0].message.content, model
            except Exception as e:
                log.warning("Buffered LLM %s failed: %s", model, e)
                continue
        return "All candidate models failed.", None

    def _parse_graph_response(self, text: str) -> dict:
        """Extract and parse the mandatory JSON object from the LLM response."""
        import json
        # Strip optional markdown fences
        cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip(), flags=re.MULTILINE)
        # Grab outermost JSON object
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        # Fallback: treat raw text as answer, mark as direct
        return {
            "answer": text.strip(),
            "reasoning_type": "direct",
            "path": [],
            "used_chunks": [],
            "justification": "JSON parse failed; raw answer returned.",
        }

    def _build_messages(self, query: str, context: str, history: list[dict] | None) -> list[dict]:
        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        if history:
            messages.extend({"role": m["role"], "content": m["content"]} for m in history)
        messages.append(
            {
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
            }
        )
        return messages

    def _call_llm(
        self,
        token: str,
        messages: list[dict],
        chunks_payload: list[dict],
        top_score: float,
        confidence_label: str,
    ) -> dict:
        client = InferenceClient(api_key=token)
        candidates = list(dict.fromkeys([self.llm_model] + FALLBACK_MODELS))

        for model in candidates:
            try:
                resp = client.chat_completion(model=model, messages=messages, max_tokens=600, temperature=0.2)
                raw = resp.choices[0].message.content
                graph = self._parse_graph_response(raw)
                return {
                    "answer": graph.get("answer", raw),
                    "chunks": chunks_payload,
                    "model_used": model,
                    "top_score": round(top_score, 4),
                    "confidence_label": confidence_label,
                    "reasoning_type": graph.get("reasoning_type", "direct"),
                    "path": graph.get("path", []),
                    "used_chunks": graph.get("used_chunks", []),
                    "justification": graph.get("justification", ""),
                }
            except Exception as e:
                log.warning("LLM %s failed: %s", model, e)
                continue

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

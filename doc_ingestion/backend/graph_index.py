from __future__ import annotations

import re
import threading
from collections import Counter, defaultdict
from dataclasses import dataclass

import structlog

log = structlog.get_logger(__name__)

STOPWORDS: frozenset[str] = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he", "in", "is", "it",
    "its", "of", "on", "that", "the", "to", "was", "were", "will", "with", "this", "these", "those",
    "or", "if", "then", "than", "into", "can", "could", "should", "would", "about", "over", "under",
    "after", "before", "between", "during", "also", "such", "their", "there", "them", "they", "you",
    "your", "we", "our", "i", "me", "my", "mine", "his", "her", "hers", "what", "which", "who",
    "whom", "when", "where", "why", "how", "do", "does", "did", "done", "not", "no", "yes",
})


@dataclass
class GraphCandidate:
    index: int
    score: float
    text: str


class GraphIndex:
    """
    In-memory knowledge graph over document chunks.
    Nodes are extracted entities; edges represent co-occurrence weight.

    Thread-safe: build() locks internally and swaps state atomically.
    retrieve() and score_candidates() read a snapshot under the lock.
    """

    def __init__(self, hop_limit: int = 1, per_node_limit: int = 6) -> None:
        self._hop_limit = hop_limit
        self._per_node_limit = per_node_limit
        self._lock = threading.Lock()
        self._chunks: list[str] = []
        self._chunk_terms: dict[int, Counter[str]] = {}
        self._chunk_entities: dict[int, set[str]] = {}
        self._entity_to_chunks: dict[str, set[int]] = defaultdict(set)
        self._entity_graph: dict[str, dict[str, float]] = defaultdict(dict)

    # ── Build ─────────────────────────────────────────────────────────────────

    def build(self, chunks: list[str]) -> None:
        """Build graph from chunks. Atomic swap — safe to call from any thread."""
        new_terms: dict[int, Counter[str]] = {}
        new_entities: dict[int, set[str]] = {}
        new_e2c: dict[str, set[int]] = defaultdict(set)
        new_graph: dict[str, dict[str, float]] = defaultdict(dict)

        for idx, chunk in enumerate(chunks):
            terms = extract_terms(chunk)
            entities = extract_entities(chunk, terms)
            new_terms[idx] = Counter(terms)
            new_entities[idx] = entities

            for ent in entities:
                new_e2c[ent].add(idx)

            ent_list = sorted(entities)
            n = len(ent_list)
            if n > 1:
                # Use 1/sqrt(n) so signal degrades gracefully in dense chunks
                # (fixes original inverted weight bug: 1/max(n,1) penalised large n)
                weight = 1.0 / max(n ** 0.5, 1.0)
                for i in range(n):
                    for j in range(i + 1, n):
                        left, right = ent_list[i], ent_list[j]
                        new_graph[left][right] = new_graph[left].get(right, 0.0) + weight
                        new_graph[right][left] = new_graph[right].get(left, 0.0) + weight

        with self._lock:
            self._chunks = list(chunks)
            self._chunk_terms = new_terms
            self._chunk_entities = new_entities
            self._entity_to_chunks = new_e2c
            self._entity_graph = new_graph

    def clear(self) -> None:
        with self._lock:
            self._chunks = []
            self._chunk_terms = {}
            self._chunk_entities = {}
            self._entity_to_chunks = defaultdict(set)
            self._entity_graph = defaultdict(dict)

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def retrieve(
        self,
        query_terms: list[str],
        query_entities: set[str],
        top_k: int,
        min_score: float = 0.0,
        relative_ratio: float = 0.0,
    ) -> list[GraphCandidate]:
        """Full graph retrieval pipeline (graph-only mode)."""
        with self._lock:
            chunks = list(self._chunks)
            e2c = self._entity_to_chunks
            e_graph = self._entity_graph
            c_terms = self._chunk_terms
            c_entities = self._chunk_entities

        if not chunks:
            return []

        expanded = _expand_entities(query_entities, e_graph, self._hop_limit, self._per_node_limit)
        candidate_set = _candidate_set(query_entities, expanded, e2c, len(chunks))
        scored = _score(candidate_set, query_terms, query_entities, chunks, c_terms, c_entities, e_graph)
        return _filter_and_cap(scored, top_k, min_score, relative_ratio)

    def score_candidates(
        self,
        candidate_indices: list[int],
        query_terms: list[str],
        query_entities: set[str],
        chunks: list[str],
    ) -> list[GraphCandidate]:
        """Score a pre-selected set of indices (used in hybrid mode)."""
        with self._lock:
            c_terms = self._chunk_terms
            c_entities = self._chunk_entities
            e_graph = self._entity_graph

        return _score(
            set(candidate_indices), query_terms, query_entities, chunks,
            c_terms, c_entities, e_graph,
        )

    def extract_query_features(self, query: str) -> tuple[list[str], set[str]]:
        """Extract terms and entities from a query string."""
        terms = extract_terms(query)
        return terms, extract_entities(query, terms)

    # ── Status ────────────────────────────────────────────────────────────────

    def status(self) -> dict:
        with self._lock:
            node_count = len(self._entity_to_chunks)
            edge_count = sum(len(v) for v in self._entity_graph.values()) // 2
            chunk_count = len(self._chunks)
        return {
            "graph_nodes": node_count,
            "graph_edges": edge_count,
            "indexed_chunks": chunk_count,
        }


# ── Module-level pure functions (also used by rag.py) ─────────────────────────

def extract_terms(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text.lower())
    return [t for t in tokens if t not in STOPWORDS]


def extract_entities(text: str, terms: list[str] | None = None) -> set[str]:
    entities: set[str] = set()

    for phrase in re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b", text):
        norm = phrase.strip().lower()
        if len(norm) > 2 and norm not in STOPWORDS:
            entities.add(norm)

    for acronym in re.findall(r"\b[A-Z]{2,}\b", text):
        entities.add(acronym.lower())

    if terms is None:
        terms = extract_terms(text)
    counts = Counter(terms)
    for token, count in counts.most_common(6):
        if count >= 2 and token not in STOPWORDS:
            entities.add(token)

    return entities


# ── Internal helpers (functions, not methods, to keep lock scope minimal) ─────

def _expand_entities(
    entities: set[str],
    graph: dict[str, dict[str, float]],
    hop_limit: int,
    per_node_limit: int,
) -> set[str]:
    expanded = set(entities)
    frontier = set(entities)
    for _ in range(hop_limit):
        next_frontier: set[str] = set()
        for ent in frontier:
            neighbors = sorted(
                graph.get(ent, {}).items(), key=lambda kv: kv[1], reverse=True
            )[:per_node_limit]
            for nbr, _ in neighbors:
                if nbr not in expanded:
                    expanded.add(nbr)
                    next_frontier.add(nbr)
        frontier = next_frontier
        if not frontier:
            break
    return expanded


def _candidate_set(
    query_entities: set[str],
    expanded: set[str],
    e2c: dict[str, set[int]],
    total: int,
) -> set[int]:
    candidates: set[int] = set()
    for ent in expanded:
        candidates.update(e2c.get(ent, set()))
    return candidates if candidates else set(range(total))


def _keyword_overlap(query_terms: list[str], chunk_terms: Counter[str]) -> float:
    if not query_terms:
        return 0.0
    return sum(1 for t in set(query_terms) if t in chunk_terms) / max(len(set(query_terms)), 1)


def _entity_coverage(query_entities: set[str], chunk_entities: set[str]) -> float:
    if not query_entities:
        return 0.0
    return len(query_entities & chunk_entities) / max(len(query_entities), 1)


def _neighbor_support(
    query_entities: set[str],
    chunk_entities: set[str],
    graph: dict[str, dict[str, float]],
) -> float:
    if not query_entities:
        return 0.0
    support = 0.0
    for q in query_entities:
        nbrs = graph.get(q, {})
        if not nbrs:
            continue
        top = sorted(nbrs.items(), key=lambda kv: kv[1], reverse=True)[:8]
        total_weight = sum(w for _, w in top) or 1.0
        chunk_weight = sum(w for e, w in top if e in chunk_entities)
        support += chunk_weight / total_weight
    return support / max(len(query_entities), 1)


def _score(
    indices: set[int],
    query_terms: list[str],
    query_entities: set[str],
    chunks: list[str],
    c_terms: dict[int, Counter[str]],
    c_entities: dict[int, set[str]],
    e_graph: dict[str, dict[str, float]],
) -> list[GraphCandidate]:
    results: list[GraphCandidate] = []
    for idx in indices:
        if idx >= len(chunks):
            continue
        ch_terms = c_terms.get(idx, Counter())
        ch_entities = c_entities.get(idx, set())
        e_sc = _entity_coverage(query_entities, ch_entities)
        n_sc = _neighbor_support(query_entities, ch_entities, e_graph)
        l_sc = _keyword_overlap(query_terms, ch_terms)

        if query_entities:
            score = (0.55 * e_sc) + (0.25 * n_sc) + (0.20 * l_sc)
        else:
            score = (0.85 * l_sc) + (0.15 * (1.0 if ch_entities else 0.0))

        if score > 0:
            results.append(GraphCandidate(index=idx, score=float(score), text=chunks[idx]))
    return results


def _filter_and_cap(
    scored: list[GraphCandidate],
    top_k: int,
    min_score: float,
    relative_ratio: float,
) -> list[GraphCandidate]:
    if not scored:
        return []
    scored.sort(key=lambda c: c.score, reverse=True)
    pool = scored[: max(top_k * 4, top_k)]
    top = pool[0].score
    filtered = [c for c in pool if c.score >= min_score and c.score >= top * relative_ratio]
    return (filtered or [pool[0]])[:top_k]

"""Standalone validation: Graph-RAG engine (no LLM token required)."""
import sys, json
sys.path.insert(0, ".")
from backend.rag import RAGEngine

engine = RAGEngine(chunk_size=95, chunk_overlap=0)

doc = (
    "Alpha Dynamics acquired Beta Labs in 2023 to expand its diagnostics portfolio.\n\n"
    "Beta Labs later formed a strategic alliance with Orion Health for hospital analytics.\n\n"
    "Orion Health announced a joint research program with Nova BioSystems focused on predictive care."
)
engine.ingest(doc)

# ── 1. Graph index ────────────────────────────────────────────────────────────
print("=== GRAPH INDEX ===")
nodes = len(engine._entity_to_chunks)
edges = sum(len(v) for v in engine._entity_graph.values()) // 2
print(f"  nodes  : {nodes}")
print(f"  edges  : {edges}")
print(f"  chunks : {len(engine.chunks)}")
top = sorted(engine._entity_to_chunks.items(), key=lambda x: len(x[1]), reverse=True)[:5]
print("  top entities:", [(e, sorted(c)) for e, c in top])
assert nodes > 0, "Graph must have nodes"
assert edges > 0, "Graph must have edges"

# ── 2. Retrieval – 2-hop ──────────────────────────────────────────────────────
print("\n=== RETRIEVAL: 2-hop ===")
r = engine.retrieve("How is Orion Health connected to Alpha Dynamics?")
for c in r:
    print(f"  chunk {c.index}  score={c.score:.4f}  {c.text[:70]}")
assert any(c.index == 0 for c in r), "Must include Alpha Dynamics chunk"
assert any(c.index == 1 for c in r), "Must include bridge chunk (Beta Labs)"

# ── 3. Retrieval – 3-hop ──────────────────────────────────────────────────────
print("\n=== RETRIEVAL: 3-hop ===")
r2 = engine.retrieve("What links Nova BioSystems to Alpha Dynamics?")
for c in r2:
    print(f"  chunk {c.index}  score={c.score:.4f}  {c.text[:70]}")
assert len(r2) >= 2, "Needs at least 2 bridge chunks for 3-hop"

# ── 4. JSON parser – clean JSON ───────────────────────────────────────────────
print("\n=== JSON PARSER ===")
sample = {
    "answer": "Alpha Dynamics -> Beta Labs -> Orion Health",
    "reasoning_type": "multi-hop",
    "path": ["Alpha Dynamics -> Beta Labs", "Beta Labs -> Orion Health"],
    "used_chunks": ["0", "1"],
    "justification": "Alpha acquired Beta, Beta allied with Orion.",
}
p = engine._parse_graph_response(json.dumps(sample))
assert p["reasoning_type"] == "multi-hop"
assert len(p["path"]) == 2
print(f"  reasoning_type : {p['reasoning_type']}")
print(f"  path           : {p['path']}")
print(f"  used_chunks    : {p['used_chunks']}")

# ── 5. JSON parser – markdown fenced ─────────────────────────────────────────
fenced = "```json\n" + json.dumps(sample) + "\n```"
p2 = engine._parse_graph_response(fenced)
assert p2["reasoning_type"] == "multi-hop", "Must strip markdown fences"
print(f"  fenced input parsed OK : {p2['reasoning_type']}")

# ── 6. JSON parser – fallback on non-JSON ────────────────────────────────────
p3 = engine._parse_graph_response("I cannot answer that question.")
assert p3["reasoning_type"] == "direct"
print(f"  fallback answer: {p3['answer'][:50]}")

# ── 7. Negative: completely unknown entity (not in graph at all) ──────────────
print("\n=== RETRIEVAL: negative (unknown entity) ===")
r3 = engine.retrieve("Who is the founder of ZetaCorp Robotics?")
_, conf = engine._confidence_from_retrieved(r3)
print(f"  confidence_label: {conf}  (expected Low — ZetaCorp is not in graph)")
assert conf == "Low", "Unknown-entity queries should produce Low confidence"

print("\nALL ASSERTIONS PASSED - Graph-RAG engine fully validated.")

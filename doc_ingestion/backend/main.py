from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import asyncio
import json
import os
import re
from typing import Literal
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .ingestion import read_upload
from .logging_config import configure_logging
from .parser import parse_file
from .rag import RAGEngine

import structlog
log = structlog.get_logger(__name__)

configure_logging()

app = FastAPI(title="Document Ingestion API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_engine = RAGEngine(
    embed_provider=os.environ.get("EMBED_PROVIDER", "graph"),
    retrieval_backend=os.environ.get("RETRIEVAL_BACKEND", "graph"),
)


class ChatMessage(BaseModel):
    role: str
    content: str


class QueryRequest(BaseModel):
    query: str
    history: list[ChatMessage] = []
    top_k: int = 3
    answer_mode: Literal["balanced", "strict_grounded"] = "balanced"


class IngestTextRequest(BaseModel):
    text: str
    chunk_size: int = 180
    chunk_overlap: int = 40


def _compute_recommendations(text: str, num_chunks: int) -> dict:
    sentences = [s.strip() for s in re.split(r"[.!?\n]+", text) if s.strip()]
    avg_len = sum(len(s) for s in sentences) / max(len(sentences), 1)
    text_len = len(text)

    if text_len > 5_000_000:
        rec_cs = max(500, min(1000, int(avg_len * 8 / 10) * 10))
    elif text_len > 1_000_000:
        rec_cs = max(300, min(800, int(avg_len * 6 / 10) * 10))
    else:
        rec_cs = max(50, min(1000, int(avg_len * 4 / 10) * 10))

    rec_co = max(0, min(200, int(rec_cs * 0.2 / 5) * 5))

    if num_chunks <= 20:
        rec_tk = 3
    elif num_chunks <= 100:
        rec_tk = 5
    elif num_chunks <= 500:
        rec_tk = 7
    else:
        rec_tk = 10

    return {"chunk_size": rec_cs, "chunk_overlap": rec_co, "top_k": rec_tk}


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    chunk_size: int = Form(180),
    chunk_overlap: int = Form(40),
):
    content, metadata = await read_upload(file)

    try:
        text = parse_file(metadata.filename, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to process the file.")

    rag_engine.chunk_size = chunk_size
    rag_engine.chunk_overlap = chunk_overlap
    num_chunks = rag_engine.start_ingest(text)

    # Run CPU-bound embedding in a background thread
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, rag_engine._do_embed)

    recs = _compute_recommendations(text, num_chunks)

    return {
        "text": text,
        "metadata": {
            "filename": metadata.filename,
            "file_type": metadata.file_type,
            "size_bytes": metadata.size_bytes,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        },
        "num_chunks": num_chunks,
        "recommended_chunk_size": recs["chunk_size"],
        "recommended_chunk_overlap": recs["chunk_overlap"],
        "recommended_top_k": recs["top_k"],
    }


@app.post("/ingest_text")
async def ingest_text(body: IngestTextRequest):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Text is empty.")
    rag_engine.chunk_size = body.chunk_size
    rag_engine.chunk_overlap = body.chunk_overlap
    num_chunks = rag_engine.start_ingest(body.text)

    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, rag_engine._do_embed)

    return {"num_chunks": num_chunks}


@app.get("/ingest_status")
async def ingest_status():
    return rag_engine.ingest_progress


@app.get("/config")
async def config():
    return {
        "embed_provider": rag_engine.embed_provider,
        "retrieval_backend": rag_engine.retrieval_backend,
    }


@app.get("/healthz")
async def healthz():
    """Liveness + readiness probe. Returns 503 when Qdrant is configured but unreachable."""
    from fastapi.responses import JSONResponse
    result = rag_engine.health()
    status_code = 503 if result.get("status") == "degraded" else 200
    return JSONResponse(content=result, status_code=status_code)


@app.get("/graph_data")
async def graph_data(max_nodes: int = 200, max_edges: int = 500):
    """Return knowledge graph nodes and edges for visualisation."""
    log.info("graph_data.request", max_nodes=max_nodes, max_edges=max_edges)
    try:
        if not rag_engine.chunks:
            log.warning("graph_data.no_document")
            raise HTTPException(status_code=400, detail="No document ingested.")
        result = rag_engine.graph_data(max_nodes=max_nodes, max_edges=max_edges)
        log.info("graph_data.success", nodes=len(result.get("nodes", [])), edges=len(result.get("edges", [])))
        return result
    except Exception as exc:
        log.error("graph_data.failed", error=str(exc))
        raise

@app.get("/vector_store_status")
async def vector_store_status():
    return rag_engine.vector_store_status()


@app.get("/graph_store_status")
async def graph_store_status():
    return rag_engine.graph_store_status()


@app.post("/query")
async def query_document(body: QueryRequest):
    if not rag_engine.chunks:
        raise HTTPException(status_code=400, detail="No document has been ingested yet. Upload a file first.")
    if not rag_engine.is_ready:
        raise HTTPException(status_code=409, detail="Document is still being embedded. Please wait.")
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    history = [{"role": m.role, "content": m.content} for m in body.history]
    rag_engine.top_k = body.top_k
    result = rag_engine.answer(body.query, history=history, answer_mode=body.answer_mode)
    return result


@app.post("/query/stream")
async def query_stream(body: QueryRequest):
    if not rag_engine.chunks:
        raise HTTPException(status_code=400, detail="No document has been ingested yet. Upload a file first.")
    if not rag_engine.is_ready:
        raise HTTPException(status_code=409, detail="Document is still being embedded. Please wait.")
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    history = [{"role": m.role, "content": m.content} for m in body.history]
    rag_engine.top_k = body.top_k

    def event_stream():
        for event in rag_engine.stream_answer(body.query, history=history, answer_mode=body.answer_mode):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/chunk_context")
async def chunk_context(index: int, window: int = 1):
    """Return the chunk at `index` plus up to `window` neighbours on each side."""
    if not rag_engine.chunks:
        raise HTTPException(status_code=400, detail="No document ingested.")
    total = len(rag_engine.chunks)
    if index < 0 or index >= total:
        raise HTTPException(status_code=404, detail=f"Chunk index {index} out of range.")
    start = max(0, index - window)
    end = min(total, index + window + 1)
    return {
        "index": index,
        "chunks": [
            {"index": i, "text": rag_engine.chunks[i], "is_target": i == index}
            for i in range(start, end)
        ]
    }


@app.get("/chunks")
async def list_chunks(offset: int = 0, limit: int = 50, search: str = ""):
    """Return a paginated, optionally filtered list of all ingested chunks."""
    if not rag_engine.chunks:
        raise HTTPException(status_code=400, detail="No document ingested.")
    source = rag_engine.chunks
    if search:
        q = search.lower()
        indices = [i for i, c in enumerate(source) if q in c.lower()]
    else:
        indices = list(range(len(source)))
    page = indices[offset: offset + limit]
    return {
        "total": len(indices),
        "offset": offset,
        "limit": limit,
        "chunks": [{"index": i, "text": source[i]} for i in page],
    }

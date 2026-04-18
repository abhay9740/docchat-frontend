---
title: DocChat Backend
emoji: 📄
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
---

# Querify

RAG-powered document chat. Upload a PDF, TXT, or CSV and ask questions against its content using a conversational interface.

## Features

- Chunked document ingestion with configurable size and overlap
- Knowledge graph indexing (entities + relations) for GraphRAG retrieval
- Retrieval-augmented generation using Qwen, Llama, or Mistral via Hugging Face Inference API
- Auto-recommended chunking parameters based on document size and type
- Async graph-index build progress tracking

## Project Structure

```
doc_ingestion/
├── backend/
│   ├── main.py          # FastAPI routes
│   ├── ingestion.py     # File handling and metadata
│   ├── parser.py        # Text extraction (PDF, TXT, CSV)
│   └── rag.py           # Chunking, graph indexing, retrieval, generation
├── frontend/
│   └── app.py           # Streamlit UI
├── Dockerfile
└── requirements.txt
```

## Quick Start

```bash
cd doc_ingestion
pip install -r requirements.txt
```

Set environment variables:

```bash
export HF_TOKEN=your_hf_token           # LLM inference
```

Start the backend:

```bash
uvicorn backend.main:app --reload --port 8000
```

Start the frontend (separate terminal):

```bash
cd frontend
streamlit run app.py
```

Open `http://localhost:8501`, upload a document, and start chatting.

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload` | Upload and ingest a file |
| `POST` | `/ingest_text` | Ingest raw text directly |
| `GET` | `/ingest_status` | Poll graph-index progress |
| `GET` | `/graph_store_status` | Graph index health and stats |
| `POST` | `/query` | Submit a question |

Interactive docs available at `http://localhost:8000/docs`.

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `chunk_size` | 180 | Characters per chunk |
| `chunk_overlap` | 40 | Overlap between adjacent chunks |
| `top_k` | 3 | Chunks retrieved per query |

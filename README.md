# Querify — Document Chat (RAG)

Upload a PDF, TXT, or CSV and chat with it using Retrieval-Augmented Generation.
The backend chunks the document and builds a knowledge graph for GraphRAG retrieval; the frontend lets you ask questions in a conversational UI.

## Architecture

| Layer | Tech | Hosted on |
|-------|------|-----------|
| Backend | FastAPI + RAG engine | Hugging Face Spaces (`csabhay/docchat-backend`) |
| Frontend | Streamlit | GitHub (`abhay9740/docchat-frontend`) |
| Retrieval | Knowledge graph (GraphRAG style) | — |
| LLM | Qwen/Llama/Mistral via HF Inference API | — |

## Quick Start (local)

### 1. Install dependencies

```bash
cd doc_ingestion
pip install -r requirements.txt
```

### 2. Set environment variables

```powershell
$env:HF_TOKEN       = "your_hf_token"     # for LLM inference
```

### 3. Start the backend (Terminal 1)

```bash
cd doc_ingestion
uvicorn backend.main:app --reload --port 8000
```

### 4. Start the frontend (Terminal 2)

```bash
cd doc_ingestion/frontend
streamlit run app.py
```

Open `http://localhost:8501`, upload a document, and start chatting.

## Chunking settings

Adjust in the sidebar before or after uploading:

| Setting | Default | Description |
|---------|---------|-------------|
| Chunk size | 180 | Characters per chunk |
| Chunk overlap | 40 | Overlap between adjacent chunks |
| Top-K | 3 | Chunks retrieved per query |

The backend also returns auto-recommended values based on document size and type.

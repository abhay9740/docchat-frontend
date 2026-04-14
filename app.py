import streamlit as st
import requests
import json
import time
import os
from datetime import datetime

API_BASE = st.secrets.get("API_BASE", os.environ.get("API_BASE", "http://localhost:8000"))
REQUEST_TIMEOUT = 600
ACCEPTED_TYPES = ["txt", "pdf", "csv"]

st.set_page_config(page_title="Querify", layout="wide", initial_sidebar_state="auto")


_GLOBAL_CSS = """
<style>
/* ── Hide Streamlit chrome ── */
#MainMenu, footer, [data-testid="stToolbar"],
[data-testid="stStatusWidget"], [data-testid="stDecoration"] {
    display: none !important;
}
header[data-testid="stHeader"] {
    background: transparent !important;
    pointer-events: none;
}

/* ── Sidebar: pinned open on desktop, collapsible on mobile ── */
@media (min-width: 769px) {
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"],
    [data-testid="stSidebarNavCollapseIcon"],
    button[data-testid="baseButton-headerNoPadding"] {
        display: none !important;
    }
    [data-testid="stSidebar"] {
        transform: none !important;
        visibility: visible !important;
        width: 22rem !important;
        min-width: 22rem !important;
    }
}
@media (max-width: 768px) {
    [data-testid="stSidebar"] {
        width: 85vw !important;
        min-width: unset !important;
    }
}

/* ── Force light theme ── */
:root, [data-testid="stAppViewContainer"], .stApp {
    color-scheme: light !important;
}
.stApp {
    background-color: #f7f7f8 !important;
    color: #1f1f1f !important;
    background-image:
        linear-gradient(rgba(0,0,0,0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,0,0,0.04) 1px, transparent 1px);
    background-size: 40px 40px;
}

/* ── Global text color reset ── */
.stApp, .stApp p, .stApp span, .stApp li, .stApp label,
.stApp div, .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
    color: #1f1f1f !important;
}

.block-container {
    max-width: 800px;
    margin: 0 auto;
    padding-top: 2rem;
    padding-bottom: 2rem;
}
@media (max-width: 768px) {
    .block-container {
        padding-top: 0.75rem !important;
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        padding-bottom: 5rem !important;
    }
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #fafafa !important;
    border-right: 1px solid #e5e7eb;
}
[data-testid="stSidebar"] h1 { font-size: 1.1rem; }
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {
    color: #374151 !important;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: #ffffff !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    margin-bottom: 0.5rem;
}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] code,
[data-testid="stChatMessage"] div {
    color: #1f1f1f !important;
}
[data-testid="stChatMessage"] pre {
    background: #f3f4f6 !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 8px !important;
}
[data-testid="stChatMessage"] pre code {
    color: #374151 !important;
}

/* ── Expander (retrieved chunks) ── */
[data-testid="stExpander"] {
    background: #f9fafb !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 8px !important;
}
[data-testid="stExpander"] p,
[data-testid="stExpander"] span,
[data-testid="stExpander"] summary {
    color: #374151 !important;
}

/* ── Right info panel ── */
.right-panel {
    position: fixed; right: 0; top: 0;
    width: 300px; height: 100vh;
    background: #fafafa;
    border-left: 1px solid #e5e7eb;
    padding: 1.5rem 1.2rem;
    z-index: 999; overflow-y: auto;
    box-shadow: -2px 0 12px rgba(0,0,0,0.05);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
@media (max-width: 768px) {
    .right-panel {
        position: relative !important;
        right: auto !important;
        top: auto !important;
        width: 100% !important;
        height: auto !important;
        box-shadow: none !important;
        border-left: none !important;
        border-top: 1px solid #e5e7eb;
        border-radius: 12px !important;
        margin-bottom: 1rem;
        padding: 1rem !important;
    }
}
.right-panel h3 {
    font-size: 1rem; font-weight: 600; color: #374151 !important;
    margin: 0 0 0.8rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #e5e7eb;
}
.right-panel .section-title {
    font-size: 0.8rem; font-weight: 600; color: #9ca3af !important;
    text-transform: uppercase; letter-spacing: 0.05em;
    margin: 1rem 0 0.4rem 0;
}
.right-panel .info-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 5px 0; font-size: 0.84rem;
    border-bottom: 1px solid #f3f4f6;
}
.right-panel .info-row .label { color: #6b7280 !important; }
.right-panel .info-row .value { font-weight: 600; color: #1f2937 !important; }
.right-panel .rec-pill {
    display: inline-block; background: #ecfdf5; color: #059669 !important;
    font-size: 0.75rem; font-weight: 600;
    padding: 2px 8px; border-radius: 10px;
}

/* ── Landing page ── */
.logo-cluster {
    display: flex; justify-content: center; align-items: center;
    margin-top: 6vh; margin-bottom: 20px;
    position: relative; height: 80px;
}
.logo-box {
    width: 60px; height: 60px; border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 28px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.10);
    position: absolute;
}
.logo-teal {
    background: linear-gradient(135deg, #2d9b83, #40c9a2); color: white !important;
    transform: rotate(-6deg); left: calc(50% - 40px); z-index: 2;
}
.logo-blue {
    background: linear-gradient(135deg, #4285f4, #669df6); color: white !important;
    transform: rotate(6deg); left: calc(50% - 10px); top: -8px; z-index: 3;
}
.logo-doc {
    width: 52px; height: 64px; background: white;
    border: 1.5px solid #ddd; border-radius: 6px;
    position: absolute; left: calc(50% - 60px); top: 4px; z-index: 1;
    transform: rotate(-10deg);
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    display: flex; align-items: center; justify-content: center;
}
.logo-doc::before {
    content: ''; position: absolute; top: 12px; left: 8px; right: 8px;
    height: 2px; background: #ddd;
    box-shadow: 0 6px 0 #ddd, 0 12px 0 #ddd, 0 18px 0 #ddd, 0 24px 0 #ddd;
}

.greeting {
    text-align: center; font-size: 34px; font-weight: 500; color: #1f1f1f !important;
    font-family: 'Georgia', 'Times New Roman', serif;
    margin-bottom: 30px; line-height: 1.3;
}
@media (max-width: 768px) {
    .greeting {
        font-size: 22px !important;
        margin-bottom: 16px !important;
    }
    .logo-cluster {
        margin-top: 2vh !important;
        margin-bottom: 12px !important;
    }
    .logo-box { width: 48px !important; height: 48px !important; font-size: 22px !important; }
    .logo-teal { left: calc(50% - 32px) !important; }
    .logo-blue { left: calc(50% - 8px) !important; }
    .logo-doc  { left: calc(50% - 48px) !important; }
}

/* ── Chat input ── */
[data-testid="stChatInput"] {
    border-radius: 16px !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06) !important;
    background: #ffffff !important;
}
[data-testid="stChatInput"] textarea {
    font-size: 16px !important; /* 16 px prevents iOS auto-zoom */
    color: #1f1f1f !important;
    background: #ffffff !important;
}
@media (max-width: 768px) {
    [data-testid="stChatInput"] {
        border-radius: 12px !important;
    }
    [data-testid="stChatMessage"] {
        padding: 0.65rem 0.75rem !important;
    }
}

/* ── File uploader ── */
.drop-zone-wrapper [data-testid="stFileUploader"] {
    border: 2px dashed #cfe3ff !important; border-radius: 12px !important;
    padding: 16px 20px !important; background: #f0f6ff !important;
    transition: border-color 0.2s, background 0.2s;
}
.drop-zone-wrapper [data-testid="stFileUploader"]:hover {
    border-color: #7ab3f7 !important; background: #e8f0fe !important;
}
.drop-zone-wrapper [data-testid="stFileUploader"] section,
.drop-zone-wrapper [data-testid="stFileUploaderDropzone"] {
    border: none !important; background: transparent !important;
}
.drop-zone-wrapper label { display: none !important; }

.drop-hint {
    text-align: center; font-size: 15px; color: #3b82f6 !important;
    font-weight: 500; margin-top: -8px; margin-bottom: 4px;
    pointer-events: none;
}

/* ── File badge ── */
.file-badge {
    text-align: center; color: #6b7280 !important; font-size: 0.85rem;
    padding: 0.5rem 0 0.8rem 0;
}
.file-badge b { color: #374151 !important; }

/* ── Buttons ── */
.stButton > button {
    color: #374151 !important;
    background: #ffffff !important;
    border: 1px solid #d1d5db !important;
    border-radius: 8px !important;
}
.stButton > button:hover {
    background: #f3f4f6 !important;
    border-color: #9ca3af !important;
}

/* ── Slider labels ── */
[data-testid="stSlider"] label,
[data-testid="stSlider"] div {
    color: #374151 !important;
}

/* ── Confidence + citations ── */
.confidence-row {
    margin: 0.2rem 0 0.7rem 0;
}
.confidence-badge {
    display: inline-block;
    font-size: 0.78rem;
    font-weight: 700;
    border-radius: 999px;
    padding: 0.18rem 0.6rem;
    border: 1px solid transparent;
}
.conf-high {
    color: #065f46 !important;
    background: #d1fae5;
    border-color: #6ee7b7;
}
.conf-medium {
    color: #92400e !important;
    background: #fef3c7;
    border-color: #fcd34d;
}
.conf-low {
    color: #991b1b !important;
    background: #fee2e2;
    border-color: #fca5a5;
}
.citations-row {
    margin: 0.25rem 0 0.6rem 0;
}
</style>
"""

st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


_DEFAULTS = {
    "doc_ingested": False,
    "messages": [],
    "current_file": None,
    "sl_chunk_size": 180,
    "sl_chunk_overlap": 40,
    "answer_mode": "balanced",
    "selected_chunk": None,
    "show_right_panel": False,
}

for key, default in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default


_WIDGET_KEYS = {"sl_chunk_size", "sl_chunk_overlap"}


def _clear_session():
    for key, default in _DEFAULTS.items():
        if key not in _WIDGET_KEYS:
            st.session_state[key] = default
    for key in ("doc_meta", "num_chunks", "doc_text",
                "recommended_chunk_size", "recommended_chunk_overlap",
                "recommended_top_k", "last_chunk_size", "last_chunk_overlap"):
        st.session_state.pop(key, None)
    st.session_state.selected_chunk = None


def _upload_file(file_obj, chunk_size: int, chunk_overlap: int) -> dict | None:
    try:
        resp = requests.post(
            f"{API_BASE}/upload",
            files={"file": (file_obj.name, file_obj.getvalue(), file_obj.type)},
            data={"chunk_size": chunk_size, "chunk_overlap": chunk_overlap},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.ConnectionError:
        st.error("Cannot connect to backend (port 8000).")
        return None
    except requests.Timeout:
        st.error("Request timed out.")
        return None

    if resp.status_code != 200:
        st.error(resp.json().get("detail", "Unknown error"))
        return None
    return resp.json()


def _apply_upload_result(data: dict, file_name: str, chunk_size: int, chunk_overlap: int):
    st.session_state.doc_ingested = True
    st.session_state.current_file = file_name
    st.session_state.doc_meta = data["metadata"]
    st.session_state.num_chunks = data.get("num_chunks", "?")
    st.session_state.doc_text = data["text"]
    st.session_state.last_chunk_size = chunk_size
    st.session_state.last_chunk_overlap = chunk_overlap
    st.session_state.recommended_chunk_size = data.get("recommended_chunk_size")
    st.session_state.recommended_chunk_overlap = data.get("recommended_chunk_overlap")
    st.session_state.recommended_top_k = data.get("recommended_top_k")


def _poll_ingest_progress(max_wait=1800):
    """Poll backend for embedding progress and show a progress bar."""
    progress_bar = st.progress(0, text="Embedding document chunks...")
    start = time.time()
    while time.time() - start < max_wait:
        try:
            resp = requests.get(f"{API_BASE}/ingest_status", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                state = data.get("state", "idle")
                embedded = data.get("embedded", 0)
                total = max(data.get("total", 1), 1)
                pct = min(embedded / total, 1.0)
                progress_bar.progress(pct, text=f"Embedding chunks: {embedded}/{total}")
                if state == "done":
                    progress_bar.progress(1.0, text=f"Embedded {total} chunks \u2713")
                    time.sleep(0.3)
                    progress_bar.empty()
                    return True
                if state == "error":
                    progress_bar.empty()
                    st.error(f"Embedding failed: {data.get('error', 'unknown error')}")
                    return False
        except Exception:
            pass
        time.sleep(0.5)
    progress_bar.empty()
    st.error("Embedding timed out.")
    return False


def _process_and_ingest(file_obj, chunk_size: int, chunk_overlap: int):
    data = _upload_file(file_obj, chunk_size, chunk_overlap)
    if data:
        _apply_upload_result(data, file_obj.name, chunk_size, chunk_overlap)
        _poll_ingest_progress()
        st.rerun()


def _query_with_auto_reingest(prompt: str, top_k: int) -> dict | None:
    payload = {"query": prompt, "history": st.session_state.messages[:-1], "top_k": top_k}
    try:
        resp = requests.post(f"{API_BASE}/query", json=payload, timeout=REQUEST_TIMEOUT)
    except requests.ConnectionError:
        st.error("Lost connection to the backend.")
        return None

    if resp.status_code == 409:
        _poll_ingest_progress()
        resp = requests.post(f"{API_BASE}/query", json=payload, timeout=REQUEST_TIMEOUT)

    if resp.status_code == 400 and "No document has been ingested" in resp.json().get("detail", ""):
        if st.session_state.get("doc_text"):
            requests.post(
                f"{API_BASE}/ingest_text",
                json={
                    "text": st.session_state.doc_text,
                    "chunk_size": st.session_state.get("last_chunk_size", 180),
                    "chunk_overlap": st.session_state.get("last_chunk_overlap", 40),
                },
                timeout=REQUEST_TIMEOUT,
            )
            _poll_ingest_progress()
            resp = requests.post(f"{API_BASE}/query", json=payload, timeout=REQUEST_TIMEOUT)

    if resp.status_code != 200:
        st.error(resp.json().get("detail", "Unknown error"))
        return None
    return resp.json()


def _format_size(size_bytes: int) -> str:
    if size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.1f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


def _time_greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


def _confidence_css_class(confidence_label: str | None) -> str:
    if confidence_label == "High":
        return "conf-high"
    if confidence_label == "Medium":
        return "conf-medium"
    return "conf-low"


def _render_confidence_badge(confidence_label: str | None, top_score: float | None):
    if not confidence_label:
        return
    score_text = f" ({top_score:.4f})" if isinstance(top_score, (int, float)) else ""
    css_class = _confidence_css_class(confidence_label)
    st.markdown(
        (
            '<div class="confidence-row">'
            f'<span class="confidence-badge {css_class}">Confidence: {confidence_label}{score_text}</span>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_citation_chips(chunks: list[dict], key_prefix: str, owner_key: str):
    if not chunks:
        return
    st.markdown('<div class="citations-row"><b>Citations</b></div>', unsafe_allow_html=True)
    cols = st.columns(min(len(chunks), 5))
    for i, chunk in enumerate(chunks[:5]):
        idx = chunk["index"]
        if cols[i].button(f"Chunk {idx}", key=f"{key_prefix}_chip_{idx}", use_container_width=True):
            st.session_state.selected_chunk = {
                "owner": owner_key,
                "index": idx,
                "score": chunk["score"],
                "text": chunk["text"],
            }


def _render_selected_chunk_preview():
    selected = st.session_state.get("selected_chunk")
    if not selected:
        return

    target_idx = selected["index"]
    score = selected["score"]

    # Fetch expanded context (target ± 1 neighbour) from backend.
    try:
        resp = requests.get(
            f"{API_BASE}/chunk_context",
            params={"index": target_idx, "window": 1},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()["chunks"]
        else:
            data = [{"index": target_idx, "text": selected["text"], "is_target": True}]
    except Exception:
        data = [{"index": target_idx, "text": selected["text"], "is_target": True}]

    with st.expander(
        f"Citation — Chunk {target_idx} (score: {score:.4f})  ·  showing passage context",
        expanded=True,
    ):
        for part in data:
            if part["is_target"]:
                st.markdown(f"**▶ Chunk {part['index']}** *(cited)*")
                st.code(part["text"], language=None)
            else:
                st.markdown(f"*Chunk {part['index']} (adjacent)*")
                st.markdown(f"```\n{part['text']}\n```")


def _render_sidebar():
    with st.sidebar:
        st.markdown("### ⚙️ Chunking Settings")

        rec_cs = st.session_state.get("recommended_chunk_size")
        rec_co = st.session_state.get("recommended_chunk_overlap")
        rec_tk = st.session_state.get("recommended_top_k")

        chunk_size = st.slider(
            f"Chunk size (rec: {rec_cs})" if rec_cs else "Chunk size",
            min_value=50, max_value=1000, step=10, key="sl_chunk_size",
            value=st.session_state.get("last_chunk_size", st.session_state.sl_chunk_size),
        )
        chunk_overlap = st.slider(
            f"Chunk overlap (rec: {rec_co})" if rec_co is not None else "Chunk overlap",
            min_value=0, max_value=200, step=5, key="sl_chunk_overlap",
            value=st.session_state.get("last_chunk_overlap", st.session_state.sl_chunk_overlap),
        )
        top_k = st.slider(
            f"Top-K chunks (rec: {rec_tk})" if rec_tk else "Top-K chunks",
            min_value=1, max_value=20, value=3, step=1,
        )

        answer_mode = st.radio(
            "Answer mode",
            options=["balanced", "strict_grounded"],
            format_func=lambda x: "Balanced" if x == "balanced" else "Strict grounded",
            index=0 if st.session_state.answer_mode == "balanced" else 1,
            help="Strict grounded returns only document-grounded answers and refuses low-confidence queries.",
        )
        st.session_state.answer_mode = answer_mode

        st.divider()
        st.markdown("### 📂 Upload")

        uploaded_file = st.file_uploader(
            "Upload a file", type=ACCEPTED_TYPES, accept_multiple_files=False,
        )

        if uploaded_file is not None and uploaded_file.name != st.session_state.current_file:
            _clear_session()
            st.session_state.current_file = uploaded_file.name

        if uploaded_file is not None:
            _warn_large_file(uploaded_file, chunk_size, chunk_overlap)

        settings_changed = (
            st.session_state.doc_ingested
            and (
                chunk_size != st.session_state.get("last_chunk_size")
                or chunk_overlap != st.session_state.get("last_chunk_overlap")
            )
        )

        col_proc, col_clear = st.columns(2, gap="small")

        process_clicked = False
        if settings_changed:
            process_clicked = col_proc.button("🔄 Reprocess", use_container_width=True)
        elif uploaded_file is not None and not st.session_state.doc_ingested:
            process_clicked = col_proc.button("⚙ Process", use_container_width=True)
        else:
            col_proc.button("⚙ Process", disabled=True, use_container_width=True)

        if col_clear.button("🗑 Clear", use_container_width=True):
            _clear_session()
            st.rerun()

        if process_clicked:
            if uploaded_file is not None:
                with st.spinner("Processing..."):
                    _process_and_ingest(uploaded_file, chunk_size, chunk_overlap)
            elif st.session_state.get("doc_text"):
                with st.spinner("Reprocessing with new settings..."):
                    try:
                        resp = requests.post(
                            f"{API_BASE}/ingest_text",
                            json={
                                "text": st.session_state.doc_text,
                                "chunk_size": chunk_size,
                                "chunk_overlap": chunk_overlap,
                            },
                            timeout=REQUEST_TIMEOUT,
                        )
                        if resp.status_code == 200:
                            st.session_state.num_chunks = resp.json().get("num_chunks", "?")
                            st.session_state.last_chunk_size = chunk_size
                            st.session_state.last_chunk_overlap = chunk_overlap
                            if st.session_state.get("doc_meta"):
                                st.session_state.doc_meta["chunk_size"] = chunk_size
                                st.session_state.doc_meta["chunk_overlap"] = chunk_overlap
                            _poll_ingest_progress()
                            st.rerun()
                        else:
                            st.error(resp.json().get("detail", "Reprocessing failed."))
                    except requests.ConnectionError:
                        st.error("Cannot connect to backend.")

    return chunk_size, chunk_overlap, top_k, answer_mode


def _warn_large_file(uploaded_file, chunk_size: int, chunk_overlap: int):
    file_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    effective_stride = max(chunk_size - chunk_overlap, 1)
    est_chunks = int(file_mb * 1_000_000 / effective_stride)
    if est_chunks > 10_000:
        est_minutes = est_chunks / 200 / 60
        st.warning(
            f"~{est_chunks:,} chunks ({file_mb:.0f} MB / {chunk_size} chars). "
            f"~{est_minutes:.0f} min on CPU. Try chunk size 500-1000."
        )


def _render_right_panel():
    meta = st.session_state.doc_meta
    rec_cs = st.session_state.get("recommended_chunk_size", "—")
    rec_co = st.session_state.get("recommended_chunk_overlap", "—")
    rec_tk = st.session_state.get("recommended_top_k", "—")
    size_str = _format_size(meta["size_bytes"])

    st.markdown(f"""
    <div class="right-panel">
        <h3>📄 File Info</h3>
        <div class="info-row"><span class="label">Filename</span>
            <span class="value">{meta['filename']}</span></div>
        <div class="info-row"><span class="label">Type</span>
            <span class="value">{meta['file_type']}</span></div>
        <div class="info-row"><span class="label">Size</span>
            <span class="value">{size_str}</span></div>
        <div class="info-row"><span class="label">Chunks</span>
            <span class="value">{st.session_state.num_chunks}</span></div>
        <div class="info-row"><span class="label">Chunk size</span>
            <span class="value">{meta.get('chunk_size', '?')}</span></div>
        <div class="info-row"><span class="label">Overlap</span>
            <span class="value">{meta.get('chunk_overlap', '?')}</span></div>
        <div class="section-title">Recommendations</div>
        <div class="info-row"><span class="label">Chunk size</span>
            <span class="rec-pill">{rec_cs}</span></div>
        <div class="info-row"><span class="label">Overlap</span>
            <span class="rec-pill">{rec_co}</span></div>
        <div class="info-row"><span class="label">Top-K</span>
            <span class="rec-pill">{rec_tk}</span></div>
    </div>
    """, unsafe_allow_html=True)


def _render_landing():
    st.markdown("""
    <div class="logo-cluster">
        <div class="logo-doc"></div>
        <div class="logo-box logo-teal">🤖</div>
        <div class="logo-box logo-blue">∞</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        f'<div class="greeting">{_time_greeting()}, what can I answer for you?</div>',
        unsafe_allow_html=True,
    )

    _, col_c, _ = st.columns([1, 3, 1])
    with col_c:
        st.markdown(
            '<div class="drop-hint">📎&nbsp; Drop PDF, TXT, or CSV to start chatting &nbsp;📄</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="drop-zone-wrapper">', unsafe_allow_html=True)
        landing_file = st.file_uploader(
            "drop", type=ACCEPTED_TYPES, accept_multiple_files=False,
            key="landing_uploader", label_visibility="collapsed",
        )
        st.markdown('</div>', unsafe_allow_html=True)

        if landing_file is not None:
            st.markdown(f"**📄 {landing_file.name}** — configure chunking settings before processing:")
            lc1, lc2 = st.columns(2)
            landing_chunk_size = lc1.slider(
                "Chunk size", min_value=50, max_value=1000, step=10,
                value=st.session_state.sl_chunk_size,
                key="landing_sl_chunk_size",
            )
            landing_chunk_overlap = lc2.slider(
                "Chunk overlap", min_value=0, max_value=200, step=5,
                value=st.session_state.sl_chunk_overlap,
                key="landing_sl_chunk_overlap",
            )
            if st.button("⚙ Process document", use_container_width=True):
                with st.spinner("Processing file..."):
                    _process_and_ingest(
                        landing_file,
                        landing_chunk_size,
                        landing_chunk_overlap,
                    )

    if st.chat_input("How can I help you today?"):
        st.info("Please upload a document first, then ask your question.")


def _stream_query(prompt: str, top_k: int, answer_mode: str, stream_state: dict):
    """Generator for st.write_stream. Populates stream_state['chunks'] and stream_state['model'].
    Sets stream_state['need_reingest'] = True if the backend signals no document / still embedding.
    """
    payload = {
        "query": prompt,
        "history": st.session_state.messages[:-1],
        "top_k": top_k,
        "answer_mode": answer_mode,
    }
    try:
        with requests.post(
            f"{API_BASE}/query/stream",
            json=payload,
            stream=True,
            timeout=REQUEST_TIMEOUT,
        ) as resp:
            if resp.status_code in (400, 409):
                stream_state["need_reingest"] = True
                stream_state["reingest_detail"] = resp.json().get("detail", "")
                return
            if resp.status_code != 200:
                try:
                    detail = resp.json().get("detail", "Unknown error")
                except Exception:
                    detail = resp.text
                yield detail
                return
            for raw in resp.iter_lines():
                if not raw:
                    continue
                line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                if not line.startswith("data: "):
                    continue
                try:
                    event = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
                t = event.get("type")
                if t == "meta":
                    stream_state["confidence_label"] = event.get("confidence_label")
                    stream_state["top_score"] = event.get("top_score")
                elif t == "chunks":
                    stream_state["chunks"] = event["data"]
                elif t == "token":
                    yield event["data"]
                elif t == "done":
                    stream_state["model"] = event.get("model_used")
    except requests.ConnectionError:
        yield "Error: lost connection to the backend."


def _render_chat(top_k: int, answer_mode: str):
    meta = st.session_state.doc_meta
    top_l, top_r = st.columns([9, 1])
    with top_l:
        st.markdown(
            f'<div class="file-badge">📄 <b>{meta["filename"]}</b> &nbsp;·&nbsp; '
            f'{st.session_state.num_chunks} chunks</div>',
            unsafe_allow_html=True,
        )
    with top_r:
        toggle_label = "✕" if st.session_state.show_right_panel else "ℹ️"
        if st.button(toggle_label, key="toggle_info", help="Toggle file info panel"):
            st.session_state.show_right_panel = not st.session_state.show_right_panel
            st.rerun()

    if st.session_state.show_right_panel:
        _render_right_panel()

    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                owner_key = f"hist_{i}"
                _render_confidence_badge(msg.get("confidence_label"), msg.get("top_score"))
                _render_citation_chips(msg.get("chunks", []), key_prefix=owner_key, owner_key=owner_key)

    if prompt := st.chat_input("How can I help you today?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            pending_owner = f"hist_{len(st.session_state.messages)}"
            stream_state = {
                "chunks": [],
                "model": None,
                "need_reingest": False,
                "reingest_detail": "",
                "confidence_label": None,
                "top_score": None,
            }

            for attempt in range(2):
                stream_state["need_reingest"] = False

                answer = st.write_stream(_stream_query(prompt, top_k, answer_mode, stream_state))

                if not stream_state["need_reingest"]:
                    break

                # Handle 409 (still embedding) or 400 "No document" by re-ingesting then retrying
                detail = stream_state["reingest_detail"]
                if "No document" in detail and st.session_state.get("doc_text"):
                    try:
                        requests.post(
                            f"{API_BASE}/ingest_text",
                            json={
                                "text": st.session_state.doc_text,
                                "chunk_size": st.session_state.get("last_chunk_size", 180),
                                "chunk_overlap": st.session_state.get("last_chunk_overlap", 40),
                            },
                            timeout=REQUEST_TIMEOUT,
                        )
                    except requests.ConnectionError:
                        st.error("Cannot reconnect to backend.")
                        st.stop()
                _poll_ingest_progress()

            _render_confidence_badge(stream_state.get("confidence_label"), stream_state.get("top_score"))
            _render_citation_chips(stream_state["chunks"], key_prefix="live", owner_key=pending_owner)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
                "chunks": stream_state["chunks"],
                "top_score": stream_state.get("top_score"),
                "confidence_label": stream_state.get("confidence_label"),
                "model_used": stream_state.get("model"),
            }
        )

    # Keep citation preview anchored in one place to avoid layout jumps.
    # Render at the bottom so it does not displace conversation headers.
    _render_selected_chunk_preview()


_, _, top_k, answer_mode = _render_sidebar()

if st.session_state.doc_ingested:
    _render_chat(top_k, answer_mode)
else:
    _render_landing()
import streamlit as st
import requests
import json
import time
import os
from datetime import datetime

try:
    _streamlit_api_base = st.secrets["API_BASE"]
except Exception:
    _streamlit_api_base = None

API_BASE = _streamlit_api_base or os.environ.get("API_BASE", "http://localhost:8000")
REQUEST_TIMEOUT = 600
ACCEPTED_TYPES = ["txt", "pdf", "csv"]

st.set_page_config(
    page_title="Querify",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ╔══════════════════════════════════════════════════════════════╗
#   CSS — dark, minimal, ChatGPT-inspired
# ╚══════════════════════════════════════════════════════════════╝
_CSS = """
<style>
/* ── Design tokens ── */
:root {
    --bg:       #0d1117;
    --surface:  #161b22;
    --overlay:  #1c2130;
    --hover:    #21262d;
    --border:   #30363d;
    --subtle:   #21262d;
    --pri:      #e6edf3;
    --sec:      #8b949e;
    --muted:    #484f58;
    --accent:   #7c84fa;
    --adim:     rgba(124,132,250,0.14);
    --green:    #3fb950;
    --yellow:   #d29922;
    --red:      #f85149;
    --r:        10px;
}

/* ── Chrome reset ── */
#MainMenu, footer,
[data-testid="stToolbar"],
[data-testid="stStatusWidget"],
[data-testid="stDecoration"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; }

/* ── App background ── */
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    background-image:
        radial-gradient(ellipse 80% 45% at 50% -5%,  rgba(124,132,250,0.10) 0%, transparent 65%),
        radial-gradient(ellipse 55% 35% at 95% 90%,  rgba(49,196,141,0.05)  0%, transparent 55%);
    background-attachment: fixed !important;
    color-scheme: dark !important;
}

/* ── Global text ── */
.stApp, .stApp p, .stApp span, .stApp li, .stApp label,
.stApp div, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stMarkdownContainer"] p { color: var(--pri) !important; }

/* ── Main content column ── */
.block-container {
    max-width: 800px;
    margin: 0 auto;
    padding-top: 1.25rem !important;
    padding-bottom: 5rem !important;
}

/* ════════════════════════════════
   SIDEBAR
   ════════════════════════════════ */
[data-testid="stSidebar"] {
    background-color: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: var(--pri) !important; }
[data-testid="stSidebar"] hr { border-color: var(--border) !important; }

/* Sidebar toggle — always visible */
[data-testid="stSidebarCollapseButton"] button,
[data-testid="collapsedControl"] button {
    background: var(--surface) !important;
    color: var(--accent) !important;
    border: 1.5px solid var(--accent) !important;
    border-radius: 8px !important;
    opacity: 1 !important;
}
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="collapsedControl"] svg {
    fill: var(--accent) !important;
    stroke: var(--accent) !important;
}

/* ── Brand header ── */
.qfy-brand {
    display: flex; align-items: center; gap: 10px;
    padding: 2px 0 18px 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 14px;
}
.qfy-brand-icon {
    width: 32px; height: 32px; border-radius: 9px;
    background: linear-gradient(135deg, #4f5ce0, #7c84fa);
    display: flex; align-items: center; justify-content: center;
    font-size: 17px; flex-shrink: 0;
    box-shadow: 0 2px 10px rgba(124,132,250,0.4);
}
.qfy-brand-name {
    font-size: 1.1rem !important; font-weight: 700 !important;
    color: var(--pri) !important; letter-spacing: -0.01em;
}

/* ── Section labels ── */
.qfy-label {
    font-size: 0.70rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--muted) !important; margin: 14px 0 6px 0;
}

/* ── Active document badge ── */
.qfy-doc-badge {
    background: var(--overlay); border: 1px solid var(--border);
    border-radius: var(--r); padding: 9px 12px; margin-bottom: 12px;
    font-size: 0.84rem;
}
.qfy-doc-badge .dname {
    font-weight: 600; color: var(--pri) !important;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    max-width: 200px; display: block;
}
.qfy-doc-badge .dmeta { color: var(--sec) !important; font-size: 0.76rem; margin-top: 3px; }
.live-dot {
    display: inline-block; width: 7px; height: 7px;
    border-radius: 50%; background: var(--green);
    margin-right: 5px; vertical-align: middle;
}

/* ── Info rows ── */
.qfy-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 5px 0; font-size: 0.82rem; border-bottom: 1px solid var(--subtle);
}
.qfy-row .k { color: var(--sec) !important; }
.qfy-row .v { font-weight: 600; color: var(--pri) !important; }
.qfy-pill {
    display: inline-block; background: rgba(124,132,250,0.15);
    color: var(--accent) !important; font-size: 0.73rem; font-weight: 600;
    padding: 2px 8px; border-radius: 10px; border: 1px solid rgba(124,132,250,0.35);
}

/* ════════════════════════════════
   CHAT — header bar
   ════════════════════════════════ */
.qfy-chat-bar {
    display: flex; align-items: center; gap: 8px;
    padding: 10px 14px; margin-bottom: 14px;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--r); font-size: 0.88rem;
}
.qfy-chat-bar .fname { font-weight: 600; color: var(--pri) !important; }
.qfy-chat-bar .fmeta { color: var(--sec) !important; }
.qfy-chat-bar .gap   { flex: 1; }

/* ════════════════════════════════
   CHAT — messages
   ════════════════════════════════ */
[data-testid="stChatMessage"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    margin-bottom: 0.45rem;
}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] code,
[data-testid="stChatMessage"] div { color: var(--pri) !important; }
[data-testid="stChatMessage"] pre {
    background: var(--overlay) !important;
    border: 1px solid var(--border) !important;
    border-radius: 7px !important;
}
[data-testid="stChatMessage"] pre code { color: #79c0ff !important; }

/* ════════════════════════════════
   CHAT — input
   ════════════════════════════════ */
[data-testid="stChatInput"] {
    border-radius: 14px !important;
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    box-shadow: 0 4px 22px rgba(0,0,0,0.35) !important;
}
[data-testid="stChatInput"] textarea {
    font-size: 15px !important; color: var(--pri) !important;
    background: transparent !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: var(--muted) !important; }

/* ════════════════════════════════
   Expander
   ════════════════════════════════ */
[data-testid="stExpander"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r) !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] p,
[data-testid="stExpander"] span { color: var(--sec) !important; }

/* ════════════════════════════════
   Buttons
   ════════════════════════════════ */
.stButton > button {
    color: var(--sec) !important;
    background: var(--overlay) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    transition: all 0.15s;
}
.stButton > button:hover {
    background: var(--hover) !important;
    border-color: var(--accent) !important;
    color: var(--pri) !important;
}

/* ── Radio / Slider ── */
[data-testid="stRadio"] label,
[data-testid="stRadio"] span { color: var(--sec) !important; }
[data-testid="stSlider"] label,
[data-testid="stSlider"] [data-testid="stMarkdownContainer"] p { color: var(--sec) !important; }

/* ── Alerts ── */
[data-testid="stAlert"] {
    background: var(--overlay) !important; border-color: var(--border) !important;
    border-radius: var(--r) !important; color: var(--sec) !important;
}

/* ── Inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    background: var(--overlay) !important; border-color: var(--border) !important;
    color: var(--pri) !important; border-radius: 6px !important;
}

/* ── Code ── */
pre, [data-testid="stCode"], .stCodeBlock {
    background: var(--overlay) !important;
    border: 1px solid var(--border) !important;
    border-radius: 7px !important;
}
pre code { color: #79c0ff !important; }

/* ════════════════════════════════
   Landing page
   ════════════════════════════════ */
.qfy-hero {
    display: flex; flex-direction: column; align-items: center;
    padding: 8vh 0 4vh 0; text-align: center;
}
.qfy-hero-logo {
    width: 64px; height: 64px; border-radius: 18px;
    background: linear-gradient(135deg, #4a56d4, #7c84fa);
    display: flex; align-items: center; justify-content: center;
    font-size: 32px; margin-bottom: 20px;
    box-shadow: 0 8px 32px rgba(124,132,250,0.40);
}
.qfy-hero-title {
    font-size: 2.2rem; font-weight: 700;
    color: var(--pri) !important; letter-spacing: -0.03em; margin-bottom: 6px;
}
.qfy-hero-sub { font-size: 1rem; color: var(--sec) !important; margin-bottom: 36px; }

/* ── Upload card ── */
.qfy-upload-wrap [data-testid="stFileUploader"] {
    background: var(--surface) !important;
    border: 2px dashed var(--border) !important;
    border-radius: 14px !important; padding: 20px !important;
    transition: border-color 0.2s, background 0.2s;
}
.qfy-upload-wrap [data-testid="stFileUploader"]:hover {
    border-color: var(--accent) !important;
    background: var(--adim) !important;
}
.qfy-upload-wrap [data-testid="stFileUploaderDropzone"],
.qfy-upload-wrap section { border: none !important; background: transparent !important; }

/* ════════════════════════════════
   Confidence badges
   ════════════════════════════════ */
.conf-row { margin: 0.2rem 0 0.55rem 0; }
.conf-badge {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 0.74rem; font-weight: 700; border-radius: 999px;
    padding: 0.14rem 0.55rem; border: 1px solid transparent;
}
.conf-high   { color: var(--green)  !important; background: rgba(63,185,80,0.10);   border-color: rgba(63,185,80,0.28);   }
.conf-medium { color: var(--yellow) !important; background: rgba(210,153,34,0.10);  border-color: rgba(210,153,34,0.28);  }
.conf-low    { color: var(--red)    !important; background: rgba(248,81,73,0.10);   border-color: rgba(248,81,73,0.28);   }

/* ── Source chip label ── */
.cite-label {
    font-size: 0.70rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.07em; color: var(--muted) !important; margin: 0 0 4px 0;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--sec); }
</style>
"""

st.markdown(_CSS, unsafe_allow_html=True)

# ╔══════════════════════════════════════════════════════════════╗
#   Session state
# ╚══════════════════════════════════════════════════════════════╝
_DEFAULTS = {
    "doc_ingested": False,
    "messages": [],
    "current_file": None,
    "sl_chunk_size": 180,
    "sl_chunk_overlap": 40,
    "answer_mode": "balanced",
    "selected_chunk": None,
}

for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

_WIDGET_KEYS        = {"sl_chunk_size", "sl_chunk_overlap"}
_GRAPH_SESSION_KEYS = ("cached_graph_html", "cached_graph_caption", "graph_fetch_attempted")

# ╔══════════════════════════════════════════════════════════════╗
#   Backend helpers  (no UI output)
# ╚══════════════════════════════════════════════════════════════╝

def _clear_session():
    for k, v in _DEFAULTS.items():
        if k not in _WIDGET_KEYS:
            st.session_state[k] = v
    for k in ("doc_meta", "num_chunks", "doc_text",
              "recommended_chunk_size", "recommended_chunk_overlap",
              "recommended_top_k", "last_chunk_size", "last_chunk_overlap"):
        st.session_state.pop(k, None)
    st.session_state.selected_chunk = None
    for k in _GRAPH_SESSION_KEYS:
        st.session_state.pop(k, None)


def _upload_file(file_obj, chunk_size: int, chunk_overlap: int):
    try:
        r = requests.post(
            f"{API_BASE}/upload",
            files={"file": (file_obj.name, file_obj.getvalue(), file_obj.type)},
            data={"chunk_size": chunk_size, "chunk_overlap": chunk_overlap},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.ConnectionError:
        st.error("Cannot connect to backend.")
        return None
    except requests.Timeout:
        st.error("Request timed out.")
        return None
    if r.status_code != 200:
        st.error(r.json().get("detail", "Upload failed."))
        return None
    return r.json()


def _apply_upload_result(data: dict, file_name: str, chunk_size: int, chunk_overlap: int):
    st.session_state.doc_ingested               = True
    st.session_state.current_file               = file_name
    st.session_state.doc_meta                   = data["metadata"]
    st.session_state.num_chunks                 = data.get("num_chunks", "?")
    st.session_state.doc_text                   = data["text"]
    st.session_state.last_chunk_size            = chunk_size
    st.session_state.last_chunk_overlap         = chunk_overlap
    st.session_state.recommended_chunk_size     = data.get("recommended_chunk_size")
    st.session_state.recommended_chunk_overlap  = data.get("recommended_chunk_overlap")
    st.session_state.recommended_top_k          = data.get("recommended_top_k")
    for k in _GRAPH_SESSION_KEYS:
        st.session_state.pop(k, None)


def _poll_ingest_progress(max_wait: int = 1800):
    bar = st.progress(0, text="Embedding chunks…")
    t0  = time.time()
    while time.time() - t0 < max_wait:
        try:
            r = requests.get(f"{API_BASE}/ingest_status", timeout=10)
            if r.status_code == 200:
                d     = r.json()
                state = d.get("state", "idle")
                done  = d.get("embedded", 0)
                total = max(d.get("total", 1), 1)
                bar.progress(min(done / total, 1.0), text=f"Embedding {done}/{total} chunks")
                if state == "done":
                    bar.progress(1.0, text=f"Done — {total} chunks ✓")
                    time.sleep(0.3); bar.empty(); return True
                if state == "error":
                    bar.empty()
                    st.error(f"Embedding failed: {d.get('error', 'unknown')}")
                    return False
        except Exception:
            pass
        time.sleep(0.5)
    bar.empty()
    st.error("Embedding timed out.")
    return False


def _process_and_ingest(file_obj, chunk_size: int, chunk_overlap: int):
    data = _upload_file(file_obj, chunk_size, chunk_overlap)
    if data:
        _apply_upload_result(data, file_obj.name, chunk_size, chunk_overlap)
        _poll_ingest_progress()
        st.rerun()


def _format_size(n: int) -> str:
    if n >= 1_048_576: return f"{n / 1_048_576:.1f} MB"
    if n >= 1024:      return f"{n / 1024:.1f} KB"
    return f"{n} B"


def _time_greeting() -> str:
    h = datetime.now().hour
    if h < 12: return "Good morning"
    if h < 17: return "Good afternoon"
    return "Good evening"


def _warn_large_file(file_obj, chunk_size: int, chunk_overlap: int):
    mb     = len(file_obj.getvalue()) / 1_048_576
    stride = max(chunk_size - chunk_overlap, 1)
    est    = int(mb * 1_000_000 / stride)
    if est > 10_000:
        st.warning(
            f"~{est:,} chunks estimated ({mb:.0f} MB). "
            "Try a larger chunk size to reduce processing time."
        )


# ── Knowledge graph ────────────────────────────────────────────

_GRAPH_PALETTE = [
    "#4f94f7", "#ea4335", "#34a853", "#fbbc04", "#9c27b0",
    "#00acc1", "#ff7043", "#43a047", "#e91e63", "#795548",
]


def _fetch_graph_into_session(max_nodes: int):
    try:
        from pyvis.network import Network
    except ImportError:
        st.error("`pyvis` not installed — add it to requirements.txt.")
        return

    with st.spinner("Building knowledge graph…"):
        try:
            r = requests.get(
                f"{API_BASE}/graph_data",
                params={"max_nodes": max_nodes, "max_edges": 500},
                timeout=30,
            )
        except requests.ConnectionError:
            st.error("Cannot connect to backend.")
            return
        if r.status_code == 400:
            st.info(r.json().get("detail", "No graph data yet."))
            return
        if r.status_code != 200:
            st.error(f"Graph fetch failed (HTTP {r.status_code}).")
            return
        data = r.json()

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    if not nodes:
        st.info("Graph is empty — document may still be indexing.")
        return

    net = Network(
        height="560px", width="100%",
        bgcolor="#161b22", font_color="#e6edf3",
        directed=False,
    )
    net.barnes_hut(spring_length=120, spring_strength=0.04, damping=0.09)
    net.set_options("""{
        "nodes": {"borderWidth": 1, "shadow": true},
        "edges": {"smooth": {"type": "continuous"}},
        "interaction": {"hover": true, "navigationButtons": true, "keyboard": true},
        "physics": {"stabilization": {"iterations": 120}}
    }""")

    mx = max((n["degree"] for n in nodes), default=1)
    for n in nodes:
        size  = 10 + 28 * (n["degree"] / max(mx, 1))
        color = _GRAPH_PALETTE[(n["chunks"][0] if n["chunks"] else 0) % len(_GRAPH_PALETTE)]
        net.add_node(
            n["id"], label=n["label"],
            title=f"Entity: {n['id']}<br>Degree: {n['degree']}",
            size=size, color=color,
        )
    for e in edges:
        net.add_edge(e["source"], e["target"], value=e["weight"],
                     title=f"Weight: {e['weight']:.3f}")

    st.session_state["cached_graph_html"]    = net.generate_html()
    st.session_state["cached_graph_caption"] = (
        f"**{data['shown_nodes']}** of {data['total_nodes']} entities · "
        f"**{data['shown_edges']}** of {data['total_edges']} edges · "
        "node size = connectivity · colour = source chunk · drag to explore"
    )


# ╔══════════════════════════════════════════════════════════════╗
#   UI — Sidebar
# ╚══════════════════════════════════════════════════════════════╝

def _render_sidebar():
    with st.sidebar:

        # Brand
        st.markdown("""
        <div class="qfy-brand">
            <div class="qfy-brand-icon">⬡</div>
            <span class="qfy-brand-name">Querify</span>
        </div>
        """, unsafe_allow_html=True)

        # Active document badge
        if st.session_state.doc_ingested:
            meta = st.session_state.doc_meta
            st.markdown(f"""
            <div class="qfy-doc-badge">
                <span class="dname">
                    <span class="live-dot"></span>{meta['filename']}
                </span>
                <span class="dmeta">
                    {meta.get('file_type', '').upper()} ·
                    {_format_size(meta['size_bytes'])} ·
                    {st.session_state.num_chunks} chunks
                </span>
            </div>
            """, unsafe_allow_html=True)

        # Upload
        st.markdown('<div class="qfy-label">Document</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload", type=ACCEPTED_TYPES, accept_multiple_files=False,
            label_visibility="collapsed",
        )
        if uploaded_file is not None and uploaded_file.name != st.session_state.current_file:
            _clear_session()
            st.session_state.current_file = uploaded_file.name
        if uploaded_file is not None:
            _warn_large_file(
                uploaded_file,
                st.session_state.sl_chunk_size,
                st.session_state.sl_chunk_overlap,
            )

        # Chunking settings
        st.markdown('<div class="qfy-label">Chunking</div>', unsafe_allow_html=True)
        rec_cs = st.session_state.get("recommended_chunk_size")
        rec_co = st.session_state.get("recommended_chunk_overlap")
        rec_tk = st.session_state.get("recommended_top_k")

        chunk_size = st.slider(
            f"Chunk size (rec {rec_cs})" if rec_cs else "Chunk size",
            50, 1000, step=10, key="sl_chunk_size",
            value=st.session_state.get("last_chunk_size", st.session_state.sl_chunk_size),
        )
        chunk_overlap = st.slider(
            f"Overlap (rec {rec_co})" if rec_co is not None else "Overlap",
            0, 200, step=5, key="sl_chunk_overlap",
            value=st.session_state.get("last_chunk_overlap", st.session_state.sl_chunk_overlap),
        )
        top_k = st.slider(
            f"Top-K (rec {rec_tk})" if rec_tk else "Top-K chunks",
            1, 20, value=3, step=1,
        )

        # Answer mode
        st.markdown('<div class="qfy-label">Answer mode</div>', unsafe_allow_html=True)
        answer_mode = st.radio(
            "Answer mode",
            options=["balanced", "strict_grounded"],
            label_visibility="collapsed",
            format_func=lambda x: "Balanced" if x == "balanced" else "Strict grounded",
            index=0 if st.session_state.answer_mode == "balanced" else 1,
        )
        st.session_state.answer_mode = answer_mode

        # Actions
        settings_changed = st.session_state.doc_ingested and (
            chunk_size    != st.session_state.get("last_chunk_size")
            or chunk_overlap != st.session_state.get("last_chunk_overlap")
        )
        st.markdown('<div class="qfy-label">Actions</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        process_clicked = False
        if settings_changed:
            process_clicked = c1.button("🔄 Reprocess", use_container_width=True)
        elif uploaded_file is not None and not st.session_state.doc_ingested:
            process_clicked = c1.button("▶ Process", use_container_width=True)
        else:
            c1.button("▶ Process", disabled=True, use_container_width=True)

        if c2.button("🗑 Clear", use_container_width=True):
            _clear_session()
            st.rerun()

        if process_clicked:
            if uploaded_file is not None:
                with st.spinner("Processing…"):
                    _process_and_ingest(uploaded_file, chunk_size, chunk_overlap)
            elif st.session_state.get("doc_text"):
                with st.spinner("Reprocessing…"):
                    try:
                        r = requests.post(
                            f"{API_BASE}/ingest_text",
                            json={
                                "text": st.session_state.doc_text,
                                "chunk_size": chunk_size,
                                "chunk_overlap": chunk_overlap,
                            },
                            timeout=REQUEST_TIMEOUT,
                        )
                        if r.status_code == 200:
                            st.session_state.num_chunks = r.json().get("num_chunks", "?")
                            st.session_state.last_chunk_size    = chunk_size
                            st.session_state.last_chunk_overlap = chunk_overlap
                            if st.session_state.get("doc_meta"):
                                st.session_state.doc_meta["chunk_size"]   = chunk_size
                                st.session_state.doc_meta["chunk_overlap"] = chunk_overlap
                            _poll_ingest_progress()
                            st.rerun()
                        else:
                            st.error(r.json().get("detail", "Reprocessing failed."))
                    except requests.ConnectionError:
                        st.error("Cannot connect to backend.")

        # File info + recommendations
        if st.session_state.doc_ingested:
            meta = st.session_state.doc_meta
            st.divider()
            st.markdown('<div class="qfy-label">File info</div>', unsafe_allow_html=True)
            rows_html = "".join(
                f'<div class="qfy-row"><span class="k">{k}</span>'
                f'<span class="v">{v}</span></div>'
                for k, v in [
                    ("Type",       meta.get("file_type", "—")),
                    ("Chunk size", meta.get("chunk_size", "?")),
                    ("Overlap",    meta.get("chunk_overlap", "?")),
                ]
            )
            if rec_cs or rec_co is not None or rec_tk:
                rows_html += '<div class="qfy-label" style="margin-top:12px">Recommended</div>'
                for k, v in [
                    ("Chunk size", rec_cs),
                    ("Overlap",    rec_co),
                    ("Top-K",      rec_tk),
                ]:
                    pill = (
                        f'<span class="qfy-pill">{v}</span>'
                        if v is not None else "—"
                    )
                    rows_html += (
                        f'<div class="qfy-row"><span class="k">{k}</span>'
                        f'<span class="v">{pill}</span></div>'
                    )
            st.markdown(rows_html, unsafe_allow_html=True)

            # Debug chunk browser
            st.divider()
            with st.expander("🔍 Browse chunks", expanded=False):
                search_q = st.text_input("Filter", placeholder="keyword…", key="dbg_search")
                pg_size  = 20
                n_ch     = st.session_state.get("num_chunks", 0)
                max_pg   = max(0, (n_ch - 1) // pg_size) if isinstance(n_ch, int) and n_ch > 0 else 0
                pg       = st.number_input("Page", 0, max_pg, 0, 1, key="dbg_page")
                if st.button("Load", key="dbg_load"):
                    try:
                        r = requests.get(
                            f"{API_BASE}/chunks",
                            params={"offset": pg * pg_size, "limit": pg_size, "search": search_q},
                            timeout=10,
                        )
                        if r.status_code == 200:
                            d = r.json()
                            st.caption(f"Showing {len(d['chunks'])} of {d['total']} chunks")
                            for ch in d["chunks"]:
                                st.markdown(f"**Chunk {ch['index']}**")
                                st.code(ch["text"], language=None)
                        else:
                            st.error(r.json().get("detail", "Failed."))
                    except requests.ConnectionError:
                        st.error("Cannot connect to backend.")

    return chunk_size, chunk_overlap, top_k, answer_mode


# ╔══════════════════════════════════════════════════════════════╗
#   UI — Confidence + Citations
# ╚══════════════════════════════════════════════════════════════╝

def _render_confidence_badge(label: str | None, score: float | None):
    if not label:
        return
    cls       = "conf-high" if label == "High" else "conf-medium" if label == "Medium" else "conf-low"
    score_txt = f"· {score:.3f}" if isinstance(score, (int, float)) else ""
    st.markdown(
        f'<div class="conf-row"><span class="conf-badge {cls}">'
        f'● {label} confidence {score_txt}</span></div>',
        unsafe_allow_html=True,
    )


def _render_citation_chips(chunks: list[dict], key_prefix: str, owner_key: str):
    if not chunks:
        return
    st.markdown('<div class="cite-label">Sources</div>', unsafe_allow_html=True)
    cols = st.columns(min(len(chunks), 5))
    for i, ch in enumerate(chunks[:5]):
        idx = ch["index"]
        if cols[i].button(
            f"§ {idx}",
            key=f"{key_prefix}_chip_{idx}",
            use_container_width=True,
            help=f"Score: {ch['score']:.4f}",
        ):
            st.session_state.selected_chunk = {
                "owner": owner_key, "index": idx,
                "score": ch["score"], "text": ch["text"],
            }
            st.rerun()


def _render_selected_chunk_preview():
    sel = st.session_state.get("selected_chunk")
    if not sel:
        return
    idx, score = sel["index"], sel["score"]
    try:
        r     = requests.get(f"{API_BASE}/chunk_context",
                             params={"index": idx, "window": 1}, timeout=10)
        parts = r.json()["chunks"] if r.status_code == 200 else \
                [{"index": idx, "text": sel["text"], "is_target": True}]
    except Exception:
        parts = [{"index": idx, "text": sel["text"], "is_target": True}]

    with st.expander(f"Source · Chunk {idx}  (score {score:.4f})", expanded=True):
        for p in parts:
            if p["is_target"]:
                st.markdown(f"**▶ Chunk {p['index']}** — cited passage")
                st.code(p["text"], language=None)
            else:
                st.caption(f"Chunk {p['index']} — adjacent context")
                st.code(p["text"], language=None)


# ╔══════════════════════════════════════════════════════════════╗
#   UI — Knowledge Graph
# ╚══════════════════════════════════════════════════════════════╝

def _render_knowledge_graph_section():
    with st.expander("🕸 Knowledge Graph", expanded=False):
        c1, c2 = st.columns([3, 2])
        max_nodes = c1.slider(
            "Max nodes", 20, 300, 120, 10,
            key="graph_max_nodes",
            help="Larger values show more entities but may slow rendering.",
        )
        if c2.button("🔄 Refresh", key="load_graph_btn", use_container_width=True):
            for k in _GRAPH_SESSION_KEYS:
                st.session_state.pop(k, None)
            _fetch_graph_into_session(max_nodes)
            st.rerun()

        if (
            not st.session_state.get("cached_graph_html")
            and not st.session_state.get("graph_fetch_attempted")
        ):
            st.session_state["graph_fetch_attempted"] = True
            _fetch_graph_into_session(max_nodes)
            st.rerun()

        html = st.session_state.get("cached_graph_html")
        if html:
            st.caption(st.session_state.get("cached_graph_caption", ""))
            st.components.v1.html(html, height=580, scrolling=False)
        else:
            st.info("Click **Refresh** to load the knowledge graph.")


# ╔══════════════════════════════════════════════════════════════╗
#   UI — Streaming query
# ╚══════════════════════════════════════════════════════════════╝

def _stream_query(prompt: str, top_k: int, answer_mode: str, state: dict):
    payload = {
        "query":       prompt,
        "history":     st.session_state.messages[:-1],
        "top_k":       top_k,
        "answer_mode": answer_mode,
    }
    try:
        with requests.post(
            f"{API_BASE}/query/stream",
            json=payload, stream=True, timeout=REQUEST_TIMEOUT,
        ) as r:
            if r.status_code in (400, 409):
                state["need_reingest"]   = True
                state["reingest_detail"] = r.json().get("detail", "")
                return
            if r.status_code != 200:
                try:    yield r.json().get("detail", "Unknown error")
                except: yield r.text
                return
            for raw in r.iter_lines():
                if not raw:
                    continue
                line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                if not line.startswith("data: "):
                    continue
                try:    ev = json.loads(line[6:])
                except: continue
                t = ev.get("type")
                if   t == "meta":   state["confidence_label"] = ev.get("confidence_label"); state["top_score"] = ev.get("top_score")
                elif t == "chunks": state["chunks"] = ev["data"]
                elif t == "token":  yield ev["data"]
                elif t == "done":   state["model"]  = ev.get("model_used")
    except requests.ConnectionError:
        yield "Error: lost connection to the backend."


# ╔══════════════════════════════════════════════════════════════╗
#   UI — Landing page
# ╚══════════════════════════════════════════════════════════════╝

def _render_landing():
    st.markdown(f"""
    <div class="qfy-hero">
        <div class="qfy-hero-logo">⬡</div>
        <div class="qfy-hero-title">Querify</div>
        <div class="qfy-hero-sub">
            {_time_greeting()} — upload a document and start asking questions
        </div>
    </div>
    """, unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown('<div class="qfy-upload-wrap">', unsafe_allow_html=True)
        landing_file = st.file_uploader(
            "Drop PDF, TXT or CSV here",
            type=ACCEPTED_TYPES, accept_multiple_files=False,
            key="landing_uploader",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if landing_file is not None:
            st.markdown(f"**📄 {landing_file.name}**")
            lc1, lc2 = st.columns(2)
            lcs = lc1.slider(
                "Chunk size", 50, 1000, step=10,
                value=st.session_state.sl_chunk_size,
                key="landing_sl_chunk_size",
            )
            lco = lc2.slider(
                "Overlap", 0, 200, step=5,
                value=st.session_state.sl_chunk_overlap,
                key="landing_sl_chunk_overlap",
            )
            if st.button("▶ Process document", use_container_width=True):
                with st.spinner("Processing…"):
                    _process_and_ingest(landing_file, lcs, lco)

    if st.chat_input("Ask a question…"):
        st.info("Upload a document first, then ask your question.")


# ╔══════════════════════════════════════════════════════════════╗
#   UI — Chat view
# ╚══════════════════════════════════════════════════════════════╝

def _render_chat(top_k: int, answer_mode: str):
    meta = st.session_state.doc_meta

    # Header bar
    st.markdown(f"""
    <div class="qfy-chat-bar">
        <span>📄</span>
        <span class="fname">{meta['filename']}</span>
        <span class="fmeta">{st.session_state.num_chunks} chunks</span>
        <span class="gap"></span>
    </div>
    """, unsafe_allow_html=True)

    # Message history
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                ok = f"hist_{i}"
                _render_confidence_badge(msg.get("confidence_label"), msg.get("top_score"))
                _render_citation_chips(msg.get("chunks", []), key_prefix=ok, owner_key=ok)

    # Chat input
    if prompt := st.chat_input("Ask a question about the document…"):
        st.session_state.selected_chunk = None
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            pending_owner = f"hist_{len(st.session_state.messages)}"
            state = {
                "chunks":           [],
                "model":            None,
                "need_reingest":    False,
                "reingest_detail":  "",
                "confidence_label": None,
                "top_score":        None,
            }

            for _ in range(2):
                state["need_reingest"] = False
                answer = st.write_stream(_stream_query(prompt, top_k, answer_mode, state))
                if not state["need_reingest"]:
                    break
                if "No document" in state["reingest_detail"] and st.session_state.get("doc_text"):
                    try:
                        requests.post(
                            f"{API_BASE}/ingest_text",
                            json={
                                "text":          st.session_state.doc_text,
                                "chunk_size":    st.session_state.get("last_chunk_size", 180),
                                "chunk_overlap": st.session_state.get("last_chunk_overlap", 40),
                            },
                            timeout=REQUEST_TIMEOUT,
                        )
                    except requests.ConnectionError:
                        st.error("Cannot reconnect to backend.")
                        st.stop()
                _poll_ingest_progress()

            _render_confidence_badge(state.get("confidence_label"), state.get("top_score"))
            _render_citation_chips(state["chunks"], key_prefix="live", owner_key=pending_owner)

        st.session_state.messages.append({
            "role":             "assistant",
            "content":          answer,
            "chunks":           state["chunks"],
            "top_score":        state.get("top_score"),
            "confidence_label": state.get("confidence_label"),
            "model_used":       state.get("model"),
        })

    # Knowledge graph + source preview
    _render_knowledge_graph_section()
    _render_selected_chunk_preview()


# ╔══════════════════════════════════════════════════════════════╗
#   Entry point
# ╚══════════════════════════════════════════════════════════════╝
_, _, top_k, answer_mode = _render_sidebar()

if st.session_state.doc_ingested:
    _render_chat(top_k, answer_mode)
else:
    _render_landing()
import streamlit as st
import requests
import json
import time
import os
from datetime import datetime

try:
    _streamlit_api_base = st.secrets["API_BASE"]
except Exception:
    _streamlit_api_base = None

API_BASE = _streamlit_api_base or os.environ.get("API_BASE", "http://localhost:8000")
REQUEST_TIMEOUT = 600
ACCEPTED_TYPES = ["txt", "pdf", "csv"]

st.set_page_config(page_title="Querify", layout="wide", initial_sidebar_state="expanded")


_GLOBAL_CSS = """
<style>
/* ════════════════════════════════════════════════════════
   DARK THEME  —  Querify
   ════════════════════════════════════════════════════════ */

/* ── Design tokens ── */
:root {
    --bg-main:       #0d1117;
    --bg-surface:    #161b22;
    --bg-overlay:    #1c2130;
    --bg-hover:      #21262d;
    --border:        #30363d;
    --border-subtle: #21262d;
    --text-pri:      #e6edf3;
    --text-sec:      #8b949e;
    --text-muted:    #484f58;
    --accent:        #7c84fa;
    --accent-dim:    #2d3561;
    --accent-glow:   rgba(124,132,250,0.15);
    --green:         #3fb950;
    --yellow:        #d29922;
    --red:           #f85149;
}

/* ── Chromium reset ── */
#MainMenu, footer, [data-testid="stToolbar"],
[data-testid="stStatusWidget"], [data-testid="stDecoration"] {
    display: none !important;
}
header[data-testid="stHeader"] {
    background: transparent !important;
}

/* ── Root background: deep dark with soft radial glow ── */
html, body, [data-testid="stAppViewContainer"], .stApp {
    background-color: var(--bg-main) !important;
    background-image:
        radial-gradient(ellipse 80% 50% at 50% -10%, rgba(124,132,250,0.12) 0%, transparent 70%),
        radial-gradient(ellipse 60% 40% at 90% 80%, rgba(49,196,141,0.06) 0%, transparent 60%) !important;
    background-attachment: fixed !important;
    color-scheme: dark !important;
}

/* ── Global text ── */
.stApp, .stApp p, .stApp span, .stApp li, .stApp label,
.stApp div, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stMarkdownContainer"] p {
    color: var(--text-pri) !important;
}

/* ── Main content column ── */
.block-container {
    max-width: 820px;
    margin: 0 auto;
    padding-top: 2rem;
    padding-bottom: 3rem;
}
@media (max-width: 768px) {
    .block-container {
        padding-top: 0.75rem !important;
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        padding-bottom: 5rem !important;
    }
}

/* ══════════════════════════════════════════════════════
   SIDEBAR  — let Streamlit own show/hide; we only set colours.
   ══════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background-color: var(--bg-surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }
/* Sidebar toggle buttons — high contrast so they're always visible */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] > button,
[data-testid="collapsedControl"],
[data-testid="collapsedControl"] > button,
button[kind="headerNoPadding"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--accent) !important;
    border-radius: 6px !important;
    color: var(--accent) !important;
    opacity: 1 !important;
    z-index: 1000 !important;
}
[data-testid="stSidebarCollapseButton"]:hover,
[data-testid="stSidebarCollapseButton"] > button:hover,
[data-testid="collapsedControl"]:hover,
[data-testid="collapsedControl"] > button:hover {
    background: var(--accent-dim) !important;
    color: var(--text-pri) !important;
}
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="collapsedControl"] svg {
    fill: var(--accent) !important;
    stroke: var(--accent) !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: var(--text-pri) !important; }
[data-testid="stSidebar"] hr { border-color: var(--border) !important; }
[data-testid="stSidebar"] [data-testid="stSlider"] div { color: var(--text-sec) !important; }

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    margin-bottom: 0.5rem;
}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] code,
[data-testid="stChatMessage"] div { color: var(--text-pri) !important; }
[data-testid="stChatMessage"] pre {
    background: var(--bg-overlay) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}
[data-testid="stChatMessage"] pre code { color: #79c0ff !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] p,
[data-testid="stExpander"] span { color: var(--text-sec) !important; }

/* ── Right info panel ── */
.right-panel {
    position: fixed; right: 0; top: 0;
    width: 300px; height: 100vh;
    background: var(--bg-surface);
    border-left: 1px solid var(--border);
    padding: 1.5rem 1.2rem;
    z-index: 999; overflow-y: auto;
    box-shadow: -4px 0 24px rgba(0,0,0,0.4);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
@media (max-width: 768px) {
    .right-panel {
        position: relative !important; right: auto !important; top: auto !important;
        width: 100% !important; height: auto !important;
        box-shadow: none !important; border-left: none !important;
        border-top: 1px solid var(--border);
        border-radius: 12px !important; margin-bottom: 1rem; padding: 1rem !important;
    }
}
.right-panel h3 {
    font-size: 1rem; font-weight: 600; color: var(--text-pri) !important;
    margin: 0 0 0.8rem 0; padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
}
.right-panel .section-title {
    font-size: 0.78rem; font-weight: 600; color: var(--text-muted) !important;
    text-transform: uppercase; letter-spacing: 0.06em; margin: 1rem 0 0.4rem 0;
}
.right-panel .info-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 5px 0; font-size: 0.84rem;
    border-bottom: 1px solid var(--border-subtle);
}
.right-panel .info-row .label { color: var(--text-sec) !important; }
.right-panel .info-row .value { font-weight: 600; color: var(--text-pri) !important; }
.right-panel .rec-pill {
    display: inline-block;
    background: var(--accent-dim); color: var(--accent) !important;
    font-size: 0.75rem; font-weight: 600;
    padding: 2px 9px; border-radius: 10px; border: 1px solid var(--accent);
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
    font-size: 28px; box-shadow: 0 4px 24px rgba(0,0,0,0.5); position: absolute;
}
.logo-teal {
    background: linear-gradient(135deg, #1a7a64, #2ea88a); color: white !important;
    transform: rotate(-6deg); left: calc(50% - 40px); z-index: 2;
}
.logo-blue {
    background: linear-gradient(135deg, #3b5fd4, #6070e8); color: white !important;
    transform: rotate(6deg); left: calc(50% - 10px); top: -8px; z-index: 3;
}
.logo-doc {
    width: 52px; height: 64px; background: var(--bg-overlay);
    border: 1.5px solid var(--border); border-radius: 6px;
    position: absolute; left: calc(50% - 60px); top: 4px; z-index: 1;
    transform: rotate(-10deg); box-shadow: 0 2px 12px rgba(0,0,0,0.4);
    display: flex; align-items: center; justify-content: center;
}
.logo-doc::before {
    content: ''; position: absolute; top: 12px; left: 8px; right: 8px;
    height: 2px; background: var(--border);
    box-shadow: 0 6px 0 var(--border), 0 12px 0 var(--border),
                0 18px 0 var(--border), 0 24px 0 var(--border);
}
.greeting {
    text-align: center; font-size: 34px; font-weight: 400;
    color: var(--text-pri) !important;
    font-family: 'Georgia', 'Times New Roman', serif;
    margin-bottom: 30px; line-height: 1.3;
}
@media (max-width: 768px) {
    .greeting { font-size: 22px !important; margin-bottom: 16px !important; }
    .logo-cluster { margin-top: 2vh !important; margin-bottom: 12px !important; }
    .logo-box { width: 48px !important; height: 48px !important; font-size: 22px !important; }
    .logo-teal { left: calc(50% - 32px) !important; }
    .logo-blue { left: calc(50% - 8px) !important; }
    .logo-doc  { left: calc(50% - 48px) !important; }
}

/* ── Chat input ── */
[data-testid="stChatInput"] {
    border-radius: 14px !important;
    box-shadow: 0 0 0 1px var(--border), 0 4px 20px rgba(0,0,0,0.3) !important;
    background: var(--bg-surface) !important;
}
[data-testid="stChatInput"] textarea {
    font-size: 16px !important;
    color: var(--text-pri) !important;
    background: transparent !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: var(--text-muted) !important; }
@media (max-width: 768px) {
    [data-testid="stChatInput"] { border-radius: 12px !important; }
    [data-testid="stChatMessage"] { padding: 0.65rem 0.75rem !important; }
}

/* ── File uploader ── */
.drop-zone-wrapper [data-testid="stFileUploader"] {
    border: 2px dashed var(--accent-dim) !important;
    border-radius: 12px !important; padding: 16px 20px !important;
    background: rgba(124,132,250,0.04) !important;
    transition: border-color 0.2s, background 0.2s;
}
.drop-zone-wrapper [data-testid="stFileUploader"]:hover {
    border-color: var(--accent) !important;
    background: var(--accent-glow) !important;
}
.drop-zone-wrapper [data-testid="stFileUploader"] section,
.drop-zone-wrapper [data-testid="stFileUploaderDropzone"] {
    border: none !important; background: transparent !important;
}
.drop-zone-wrapper label { display: none !important; }
.drop-hint {
    text-align: center; font-size: 15px; color: var(--accent) !important;
    font-weight: 500; margin-top: -8px; margin-bottom: 4px; pointer-events: none;
}

/* ── File badge ── */
.file-badge {
    text-align: center; color: var(--text-sec) !important; font-size: 0.85rem;
    padding: 0.5rem 0 0.8rem 0;
}
.file-badge b { color: var(--text-pri) !important; }

/* ── Buttons ── */
.stButton > button {
    color: var(--text-sec) !important;
    background: var(--bg-overlay) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.stButton > button:hover {
    background: var(--bg-hover) !important;
    border-color: var(--accent) !important;
    color: var(--text-pri) !important;
}

/* ── Radio / Slider ── */
[data-testid="stRadio"] label,
[data-testid="stRadio"] span { color: var(--text-sec) !important; }
[data-testid="stSlider"] label,
[data-testid="stSlider"] [data-testid="stMarkdownContainer"] p { color: var(--text-sec) !important; }

/* ── Alerts ── */
[data-testid="stAlert"] {
    background: var(--bg-overlay) !important;
    border-color: var(--border) !important;
    border-radius: 10px !important;
    color: var(--text-sec) !important;
}

/* ── Code blocks ── */
[data-testid="stCode"], .stCodeBlock, pre {
    background: var(--bg-overlay) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: #79c0ff !important;
}

/* ── Inputs ── */
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input {
    background: var(--bg-overlay) !important;
    border-color: var(--border) !important;
    color: var(--text-pri) !important;
    border-radius: 6px !important;
}

/* ── Confidence + citations ── */
.confidence-row { margin: 0.2rem 0 0.7rem 0; }
.confidence-badge {
    display: inline-block; font-size: 0.78rem; font-weight: 700;
    border-radius: 999px; padding: 0.18rem 0.6rem;
    border: 1px solid transparent;
}
.conf-high   { color: #3fb950 !important; background: rgba(63,185,80,0.12);  border-color: rgba(63,185,80,0.35); }
.conf-medium { color: #d29922 !important; background: rgba(210,153,34,0.12); border-color: rgba(210,153,34,0.35); }
.conf-low    { color: #f85149 !important; background: rgba(248,81,73,0.12);  border-color: rgba(248,81,73,0.35); }
.citations-row { margin: 0.25rem 0 0.6rem 0; }
</style>
"""

st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


_DEFAULTS = {
    "doc_ingested": False,
    "messages": [],
    "current_file": None,
    "sl_chunk_size": 180,
    "sl_chunk_overlap": 40,
    "landing_sl_chunk_size": 180,
    "landing_sl_chunk_overlap": 40,
    "answer_mode": "balanced",
    "selected_chunk": None,
    "show_right_panel": False,
}

for key, default in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default


_WIDGET_KEYS = {"sl_chunk_size", "sl_chunk_overlap"}

_GRAPH_SESSION_KEYS = ("cached_graph_html", "cached_graph_caption", "graph_fetch_attempted")


def _clear_session():
    for key, default in _DEFAULTS.items():
        if key not in _WIDGET_KEYS:
            st.session_state[key] = default
    for key in ("doc_meta", "num_chunks", "doc_text",
                "recommended_chunk_size", "recommended_chunk_overlap",
                "recommended_top_k", "last_chunk_size", "last_chunk_overlap"):
        st.session_state.pop(key, None)
    st.session_state.selected_chunk = None
    for k in _GRAPH_SESSION_KEYS:
        st.session_state.pop(k, None)


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
    for k in _GRAPH_SESSION_KEYS:
        st.session_state.pop(k, None)


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


# ── Knowledge Graph visualiser ────────────────────────────────────────────────

_GRAPH_PALETTE = [
    "#4f94f7", "#ea4335", "#34a853", "#fbbc04", "#9c27b0",
    "#00acc1", "#ff7043", "#43a047", "#e91e63", "#795548",
]


def _fetch_graph_into_session(max_nodes: int) -> None:
    """Fetch graph data from backend, build pyvis HTML, store in session_state."""
    try:
        from pyvis.network import Network
    except ImportError:
        st.error("`pyvis` is not installed — add it to `requirements.txt` and redeploy.")
        return

    with st.spinner("Building graph…"):
        try:
            resp = requests.get(
                f"{API_BASE}/graph_data",
                params={"max_nodes": max_nodes, "max_edges": 500},
                timeout=30,
            )
        except requests.ConnectionError:
            st.error("Cannot connect to backend.")
            return

        if resp.status_code == 400:
            st.info(resp.json().get("detail", "No graph data yet."))
            return
        if resp.status_code != 200:
            st.error(f"Failed to fetch graph data (HTTP {resp.status_code}).")
            return

        data = resp.json()

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    if not nodes:
        st.info("Graph is empty — the document may still be indexing.")
        return

    net = Network(
        height="580px", width="100%",
        bgcolor="#161b22", font_color="#e6edf3",
        directed=False,
    )
    net.barnes_hut(spring_length=120, spring_strength=0.04, damping=0.09)
    net.set_options("""
    {
      "nodes": {"borderWidth": 1, "shadow": true},
      "edges": {"smooth": {"type": "continuous"}, "shadow": false},
      "interaction": {"hover": true, "tooltipDelay": 150,
                      "navigationButtons": true, "keyboard": true},
      "physics": {"stabilization": {"iterations": 120}}
    }
    """)

    max_degree = max((n["degree"] for n in nodes), default=1)
    for node in nodes:
        deg = node["degree"]
        size = 10 + 28 * (deg / max(max_degree, 1))
        chunk_idx = node["chunks"][0] if node["chunks"] else 0
        color = _GRAPH_PALETTE[chunk_idx % len(_GRAPH_PALETTE)]
        chunks_str = ", ".join(str(c) for c in node["chunks"])
        net.add_node(
            node["id"],
            label=node["label"],
            title=f"Entity: {node['id']}<br>Chunks: {chunks_str}<br>Degree: {deg}",
            size=size,
            color=color,
        )

    for edge in edges:
        net.add_edge(
            edge["source"], edge["target"],
            value=edge["weight"],
            title=f"Co-occurrence weight: {edge['weight']:.3f}",
        )

    st.session_state["cached_graph_html"] = net.generate_html()
    st.session_state["cached_graph_caption"] = (
        f"Showing **{data['shown_nodes']}** of {data['total_nodes']} entities · "
        f"**{data['shown_edges']}** of {data['total_edges']} co-occurrence edges. "
        f"Node size = connectivity · colour = source chunk · drag to explore."
    )


def _render_knowledge_graph_section() -> None:
    with st.expander("🕸 Knowledge Graph", expanded=True):
        c1, c2 = st.columns([3, 2])
        max_nodes = c1.slider(
            "Max nodes", min_value=20, max_value=300, value=120, step=10,
            key="graph_max_nodes",
            help="Larger values show more entities but may slow rendering.",
        )
        if c2.button("🔄 Load / Refresh", key="load_graph_btn", use_container_width=True):
            for k in _GRAPH_SESSION_KEYS:
                st.session_state.pop(k, None)
            _fetch_graph_into_session(max_nodes)
            st.rerun()

        cached_html = st.session_state.get("cached_graph_html")
        if not cached_html and not st.session_state.get("graph_fetch_attempted"):
            st.session_state["graph_fetch_attempted"] = True
            _fetch_graph_into_session(max_nodes)
            st.rerun()

        cached_html = st.session_state.get("cached_graph_html")
        if cached_html:
            st.markdown(st.session_state.get("cached_graph_caption", ""))
            st.components.v1.html(cached_html, height=600, scrolling=False)
        else:
            st.info("No graph data yet — click **Load / Refresh** to try again.")


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
            st.rerun()


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

        # ── Debug: Browse chunks ─────────────────────────────────────────────
        if st.session_state.doc_ingested:
            st.divider()
            with st.expander("🔍 Browse chunks (debug)", expanded=False):
                search_q = st.text_input(
                    "Filter chunks", placeholder="keyword…", key="debug_chunk_search",
                )
                page_size = 20
                total_chunks = st.session_state.get("num_chunks", 0)
                if isinstance(total_chunks, int) and total_chunks > 0:
                    max_page = max(0, (total_chunks - 1) // page_size)
                else:
                    max_page = 0
                page_num = st.number_input(
                    "Page", min_value=0, max_value=max_page, value=0, step=1,
                    key="debug_chunk_page",
                )
                if st.button("Load", key="debug_chunk_load"):
                    try:
                        resp = requests.get(
                            f"{API_BASE}/chunks",
                            params={"offset": page_num * page_size, "limit": page_size, "search": search_q},
                            timeout=10,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            st.caption(f"Showing {len(data['chunks'])} of {data['total']} matching chunks")
                            for ch in data["chunks"]:
                                st.markdown(f"**Chunk {ch['index']}**")
                                st.code(ch["text"], language=None)
                        else:
                            st.error(resp.json().get("detail", "Failed to load chunks."))
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
        st.session_state.selected_chunk = None
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

    # Knowledge graph — shown after the chat history
    _render_knowledge_graph_section()

    # Keep citation preview anchored in one place to avoid layout jumps.
    # Render at the bottom so it does not displace conversation headers.
    _render_selected_chunk_preview()


_, _, top_k, answer_mode = _render_sidebar()

if st.session_state.doc_ingested:
    _render_chat(top_k, answer_mode)
else:
    _render_landing()
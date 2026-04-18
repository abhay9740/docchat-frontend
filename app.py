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
    page_icon="â¬¡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
#   CSS â€” dark, minimal, ChatGPT-inspired
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
_CSS = """
<style>
/* â”€â”€ Design tokens â”€â”€ */
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

/* â”€â”€ Chrome reset â”€â”€ */
#MainMenu, footer,
[data-testid="stToolbar"],
[data-testid="stStatusWidget"],
[data-testid="stDecoration"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; }

/* â”€â”€ App background â”€â”€ */
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    background-image:
        radial-gradient(ellipse 80% 45% at 50% -5%,  rgba(124,132,250,0.10) 0%, transparent 65%),
        radial-gradient(ellipse 55% 35% at 95% 90%,  rgba(49,196,141,0.05)  0%, transparent 55%);
    background-attachment: fixed !important;
    color-scheme: dark !important;
}

/* â”€â”€ Global text â”€â”€ */
.stApp, .stApp p, .stApp span, .stApp li, .stApp label,
.stApp div, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stMarkdownContainer"] p { color: var(--pri) !important; }

/* â”€â”€ Main content column â”€â”€ */
.block-container {
    max-width: 800px;
    margin: 0 auto;
    padding-top: 1.25rem !important;
    padding-bottom: 5rem !important;
}

/* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
   SIDEBAR
   â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
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

/* Sidebar toggle â€” always visible */
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

/* â”€â”€ Brand header â”€â”€ */
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

/* â”€â”€ Section labels â”€â”€ */
.qfy-label {
    font-size: 0.70rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--muted) !important; margin: 14px 0 6px 0;
}

/* â”€â”€ Active document badge â”€â”€ */
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

/* â”€â”€ Info rows â”€â”€ */
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

/* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
   CHAT â€” header bar
   â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
.qfy-chat-bar {
    display: flex; align-items: center; gap: 8px;
    padding: 10px 14px; margin-bottom: 14px;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--r); font-size: 0.88rem;
}
.qfy-chat-bar .fname { font-weight: 600; color: var(--pri) !important; }
.qfy-chat-bar .fmeta { color: var(--sec) !important; }
.qfy-chat-bar .gap   { flex: 1; }

/* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
   CHAT â€” messages
   â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
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

/* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
   CHAT â€” input
   â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
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

/* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
   Expander
   â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
[data-testid="stExpander"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r) !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] p,
[data-testid="stExpander"] span { color: var(--sec) !important; }

/* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
   Buttons
   â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
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

/* â”€â”€ Radio / Slider â”€â”€ */
[data-testid="stRadio"] label,
[data-testid="stRadio"] span { color: var(--sec) !important; }
[data-testid="stSlider"] label,
[data-testid="stSlider"] [data-testid="stMarkdownContainer"] p { color: var(--sec) !important; }

/* â”€â”€ Alerts â”€â”€ */
[data-testid="stAlert"] {
    background: var(--overlay) !important; border-color: var(--border) !important;
    border-radius: var(--r) !important; color: var(--sec) !important;
}

/* â”€â”€ Inputs â”€â”€ */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    background: var(--overlay) !important; border-color: var(--border) !important;
    color: var(--pri) !important; border-radius: 6px !important;
}

/* â”€â”€ Code â”€â”€ */
pre, [data-testid="stCode"], .stCodeBlock {
    background: var(--overlay) !important;
    border: 1px solid var(--border) !important;
    border-radius: 7px !important;
}
pre code { color: #79c0ff !important; }

/* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
   Landing page
   â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
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

/* â”€â”€ Upload card â”€â”€ */
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

/* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
   Confidence badges
   â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
.conf-row { margin: 0.2rem 0 0.55rem 0; }
.conf-badge {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 0.74rem; font-weight: 700; border-radius: 999px;
    padding: 0.14rem 0.55rem; border: 1px solid transparent;
}
.conf-high   { color: var(--green)  !important; background: rgba(63,185,80,0.10);   border-color: rgba(63,185,80,0.28);   }
.conf-medium { color: var(--yellow) !important; background: rgba(210,153,34,0.10);  border-color: rgba(210,153,34,0.28);  }
.conf-low    { color: var(--red)    !important; background: rgba(248,81,73,0.10);   border-color: rgba(248,81,73,0.28);   }

/* â”€â”€ Source chip label â”€â”€ */
.cite-label {
    font-size: 0.70rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.07em; color: var(--muted) !important; margin: 0 0 4px 0;
}

/* â”€â”€ Scrollbar â”€â”€ */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--sec); }
</style>
"""

st.markdown(_CSS, unsafe_allow_html=True)

# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
#   Session state
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
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

# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
#   Backend helpers  (no UI output)
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

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
    bar = st.progress(0, text="Embedding chunksâ€¦")
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
                    bar.progress(1.0, text=f"Done â€” {total} chunks âœ“")
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


# â”€â”€ Knowledge graph â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_GRAPH_PALETTE = [
    "#4f94f7", "#ea4335", "#34a853", "#fbbc04", "#9c27b0",
    "#00acc1", "#ff7043", "#43a047", "#e91e63", "#795548",
]


def _fetch_graph_into_session(max_nodes: int):
    try:
        from pyvis.network import Network
    except ImportError:
        st.error("`pyvis` not installed â€” add it to requirements.txt.")
        return

    with st.spinner("Building knowledge graphâ€¦"):
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
        st.info("Graph is empty â€” document may still be indexing.")
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
        f"**{data['shown_nodes']}** of {data['total_nodes']} entities Â· "
        f"**{data['shown_edges']}** of {data['total_edges']} edges Â· "
        "node size = connectivity Â· colour = source chunk Â· drag to explore"
    )


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
#   UI â€” Sidebar
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _render_sidebar():
    with st.sidebar:

        # Brand
        st.markdown("""
        <div class="qfy-brand">
            <div class="qfy-brand-icon">â¬¡</div>
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
                    {meta.get('file_type', '').upper()} Â·
                    {_format_size(meta['size_bytes'])} Â·
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
            process_clicked = c1.button("ðŸ”„ Reprocess", use_container_width=True)
        elif uploaded_file is not None and not st.session_state.doc_ingested:
            process_clicked = c1.button("â–¶ Process", use_container_width=True)
        else:
            c1.button("â–¶ Process", disabled=True, use_container_width=True)

        if c2.button("ðŸ—‘ Clear", use_container_width=True):
            _clear_session()
            st.rerun()

        if process_clicked:
            if uploaded_file is not None:
                with st.spinner("Processingâ€¦"):
                    _process_and_ingest(uploaded_file, chunk_size, chunk_overlap)
            elif st.session_state.get("doc_text"):
                with st.spinner("Reprocessingâ€¦"):
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
                    ("Type",       meta.get("file_type", "â€”")),
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
                        if v is not None else "â€”"
                    )
                    rows_html += (
                        f'<div class="qfy-row"><span class="k">{k}</span>'
                        f'<span class="v">{pill}</span></div>'
                    )
            st.markdown(rows_html, unsafe_allow_html=True)

            # Debug chunk browser
            st.divider()
            with st.expander("ðŸ” Browse chunks", expanded=False):
                search_q = st.text_input("Filter", placeholder="keywordâ€¦", key="dbg_search")
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


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
#   UI â€” Confidence + Citations
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _render_confidence_badge(label: str | None, score: float | None):
    if not label:
        return
    cls       = "conf-high" if label == "High" else "conf-medium" if label == "Medium" else "conf-low"
    score_txt = f"Â· {score:.3f}" if isinstance(score, (int, float)) else ""
    st.markdown(
        f'<div class="conf-row"><span class="conf-badge {cls}">'
        f'â— {label} confidence {score_txt}</span></div>',
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
            f"Â§ {idx}",
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

    with st.expander(f"Source Â· Chunk {idx}  (score {score:.4f})", expanded=True):
        for p in parts:
            if p["is_target"]:
                st.markdown(f"**â–¶ Chunk {p['index']}** â€” cited passage")
                st.code(p["text"], language=None)
            else:
                st.caption(f"Chunk {p['index']} â€” adjacent context")
                st.code(p["text"], language=None)


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
#   UI â€” Knowledge Graph
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _render_knowledge_graph_section():
    with st.expander("Knowledge Graph", expanded=False):
        c1, c2 = st.columns([3, 2])
        max_nodes = c1.slider(
            "Max nodes", 20, 300, 120, 10,
            key="graph_max_nodes",
            help="Larger values show more entities but may slow rendering.",
        )
        if c2.button("Refresh", key="load_graph_btn", use_container_width=True):
            for k in _GRAPH_SESSION_KEYS:
                st.session_state.pop(k, None)
            st.rerun()
            _fetch_graph_into_session(max_nodes)

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


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
#   UI â€” Streaming query
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

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


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
#   UI â€” Landing page
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _render_landing():
    st.markdown(f"""
    <div class="qfy-hero">
        <div class="qfy-hero-logo">â¬¡</div>
        <div class="qfy-hero-title">Querify</div>
        <div class="qfy-hero-sub">
            {_time_greeting()} â€” upload a document and start asking questions
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
            st.markdown(f"**ðŸ“„ {landing_file.name}**")
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
            if st.button("â–¶ Process document", use_container_width=True):
                with st.spinner("Processingâ€¦"):
                    _process_and_ingest(landing_file, lcs, lco)

    if st.chat_input("Ask a questionâ€¦"):
        st.info("Upload a document first, then ask your question.")


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
#   UI â€” Chat view
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _render_chat(top_k: int, answer_mode: str):
    meta = st.session_state.doc_meta

    # Header bar
    st.markdown(f"""
    <div class="qfy-chat-bar">
        <span>ðŸ“„</span>
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
    if prompt := st.chat_input("Ask a question about the documentâ€¦"):
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


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
#   Entry point
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
_, _, top_k, answer_mode = _render_sidebar()

if st.session_state.doc_ingested:
    _render_chat(top_k, answer_mode)
else:
    _render_landing()

"""
Scholaris — AI Research Paper Chatbot
Streamlit frontend  (run: streamlit run frontend/app.py)
"""
from __future__ import annotations

import sys
import os

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import io
import json
import time
from datetime import datetime

import requests
import streamlit as st

from config import BACKEND_URL

# ─────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Scholaris · AI Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* ── Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Sora', sans-serif; }

/* ── App shell ── */
.stApp { background: #0d0f1a; color: #e8eaf0; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #12141f !important;
    border-right: 1px solid #1e2235;
}
section[data-testid="stSidebar"] * { color: #c9cde0 !important; }

/* ── Header brand ── */
.brand-header {
    display: flex; align-items: center; gap: 10px;
    padding: 4px 0 18px 0;
    border-bottom: 1px solid #1e2235;
    margin-bottom: 16px;
}
.brand-icon { font-size: 28px; }
.brand-name {
    font-size: 22px; font-weight: 700; letter-spacing: -0.5px;
    background: linear-gradient(135deg, #7c6ff7, #5eead4);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.brand-tagline { font-size: 11px; color: #5c6070 !important; margin-top: -2px; }

/* ── Session list items ── */
.session-item {
    padding: 9px 12px; border-radius: 8px; margin-bottom: 4px;
    border: 1px solid transparent; cursor: pointer;
    transition: all .15s;
}
.session-item:hover { background: #1a1e30; border-color: #2a2f48; }
.session-item.active { background: #1e2540; border-color: #7c6ff7; }
.session-title { font-size: 13px; font-weight: 500; color: #d0d4ea !important; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.session-meta  { font-size: 10px; color: #4a5068 !important; margin-top: 2px; }

/* ── Chat bubbles ── */
.chat-user {
    background: linear-gradient(135deg, #2d1f6e, #1e2a5e);
    border: 1px solid #3a2fa0;
    border-radius: 16px 16px 4px 16px;
    padding: 12px 16px; margin: 6px 0; max-width: 82%;
    margin-left: auto;
}
.chat-assistant {
    background: #141829;
    border: 1px solid #1e2540;
    border-radius: 16px 16px 16px 4px;
    padding: 14px 18px; margin: 6px 0; max-width: 88%;
}
.chat-role {
    font-size: 10px; font-weight: 600; letter-spacing: 1px;
    text-transform: uppercase; margin-bottom: 6px;
}
.chat-user .chat-role   { color: #9d8fff; }
.chat-assistant .chat-role { color: #5eead4; }
.chat-ts { font-size: 10px; color: #3a4060; margin-top: 6px; text-align: right; }

/* ── Source chips ── */
.source-chip {
    display: inline-block; background: #1a1e30; border: 1px solid #2a2f48;
    border-radius: 20px; padding: 3px 10px; font-size: 11px;
    color: #8899cc !important; margin: 3px 3px 0 0;
    font-family: 'JetBrains Mono', monospace;
}

/* ── Inputs ── */
.stTextInput > div > div > input, .stTextArea textarea {
    background: #141829 !important; color: #e8eaf0 !important;
    border: 1px solid #1e2540 !important; border-radius: 10px !important;
    font-family: 'Sora', sans-serif !important;
}
.stTextInput > div > div > input:focus, .stTextArea textarea:focus {
    border-color: #7c6ff7 !important;
    box-shadow: 0 0 0 2px rgba(124,111,247,.2) !important;
}

/* ── Buttons ── */
.stButton > button {
    border-radius: 8px !important; font-weight: 600 !important;
    font-family: 'Sora', sans-serif !important;
    transition: all .15s !important;
}
.stButton > button:hover { transform: translateY(-1px); }

/* ── File uploader ── */
.stFileUploader { border: 1px dashed #2a2f48 !important; border-radius: 12px !important; }

/* ── Expander (sources) ── */
.streamlit-expanderHeader {
    background: #141829 !important; border-radius: 8px !important;
    color: #8899cc !important; font-size: 12px !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
    background: #141829 !important; color: #e8eaf0 !important;
    border: 1px solid #1e2540 !important; border-radius: 10px !important;
}

/* ── Divider ── */
hr { border-color: #1e2235 !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #0d0f1a; }
::-webkit-scrollbar-thumb { background: #2a2f48; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# API helpers
# ─────────────────────────────────────────────────────────────────

def api(method: str, path: str, timeout: int = 120, retries: int = 6, **kwargs):
    url = f"{BACKEND_URL}{path}"
    last_error = None

    for attempt in range(retries + 1):
        try:
            resp = getattr(requests, method)(url, timeout=timeout, **kwargs)
            resp.raise_for_status()
            ct = resp.headers.get("content-type", "")
            return resp.text if "text/plain" in ct else resp.json()
        except requests.exceptions.ConnectionError as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1 + attempt)
                continue
            st.error("⚠️ Cannot connect to Scholaris backend yet. Please wait a few seconds and refresh.")
            return None
        except requests.exceptions.HTTPError as e:
            detail = ""
            try:
                detail = e.response.json().get("detail", "")
            except Exception:
                pass
            st.error(f"API error: {e} — {detail}")
            return None

    if last_error:
        st.error("⚠️ Cannot connect to Scholaris backend yet. Please wait a few seconds and refresh.")
    return None


# ─────────────────────────────────────────────────────────────────
# Session state init
# ─────────────────────────────────────────────────────────────────

def _init():
    defaults = {
        "active_session_id": None,
        "active_session":    None,
        "papers":            [],
        "selected_paper_id": None,
        "upload_done":       False,
        "sidebar_refresh":   0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def refresh_session():
    if st.session_state.active_session_id:
        s = api("get", f"/history/{st.session_state.active_session_id}")
        if s:
            st.session_state.active_session = s


def load_session(sid: str):
    s = api("get", f"/history/{sid}")
    if s:
        st.session_state.active_session_id = sid
        st.session_state.active_session    = s


def new_chat():
    st.session_state.active_session_id = None
    st.session_state.active_session    = None


def format_ts(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %H:%M")
    except Exception:
        return iso[:16]


# ─────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div class="brand-header">
      <div class="brand-icon">🔬</div>
      <div>
        <div class="brand-name">Scholaris</div>
        <div class="brand-tagline">AI Research Paper Assistant</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── New chat ──────────────────────────────────────────────────
    if st.button("✦  New Chat", use_container_width=True, type="primary"):
        new_chat()
        st.rerun()

    st.markdown("---")

    # ── History list ─────────────────────────────────────────────
    st.markdown("**💬 Conversations**")

    sessions = api("get", "/history") or []

    if not sessions:
        st.caption("No conversations yet.")
    else:
        for s in sessions:
            sid      = s["session_id"]
            is_active = sid == st.session_state.active_session_id
            css_cls  = "session-item active" if is_active else "session-item"
            ts       = format_ts(s["updated_at"])
            paper_lbl = f" · {s['paper_title'][:22]}…" if s.get("paper_title") else ""

            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(
                    f'<div class="{css_cls}">'
                    f'  <div class="session-title">{s["title"]}</div>'
                    f'  <div class="session-meta">{ts}{paper_lbl} · {s["message_count"]} msgs</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button("open", key=f"open_{sid}", help="Open conversation"):
                    load_session(sid)
                    st.rerun()
            with col2:
                if st.button("🗑", key=f"del_{sid}", help="Delete this conversation"):
                    api("delete", f"/history/{sid}")
                    if st.session_state.active_session_id == sid:
                        new_chat()
                    st.rerun()

    st.markdown("---")

    # ── History actions ───────────────────────────────────────────
    st.markdown("**📥 Export History**")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Export All", use_container_width=True):
            md = api("get", "/history/export/all")
            if md:
                st.download_button(
                    "⬇ Download",
                    data=md,
                    file_name="scholaris_history.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
    with col_b:
        if st.session_state.active_session_id:
            if st.button("Export Chat", use_container_width=True):
                md = api("get", f"/history/{st.session_state.active_session_id}/export")
                if md:
                    title_slug = (st.session_state.active_session or {}).get("title", "chat")[:30]
                    st.download_button(
                        "⬇ Download",
                        data=md,
                        file_name=f"scholaris_{title_slug}.md",
                        mime="text/markdown",
                        use_container_width=True,
                    )

    st.markdown("---")

    # ── Danger zone ───────────────────────────────────────────────
    with st.expander("⚠️ Danger Zone"):
        st.caption("This will permanently delete all conversations.")
        if st.button("🗑 Delete ALL History", type="secondary", use_container_width=True):
            api("delete", "/history")
            new_chat()
            st.success("All history cleared.")
            st.rerun()


# ─────────────────────────────────────────────────────────────────
# Main area — tabs
# ─────────────────────────────────────────────────────────────────

tab_chat, tab_upload, tab_papers = st.tabs(["💬 Chat", "📄 Upload Paper", "📚 My Papers"])

# ══════════════════════════════════════════════════════════════════
# TAB 1 — CHAT
# ══════════════════════════════════════════════════════════════════

with tab_chat:
    # Paper filter selector
    papers = api("get", "/papers") or []
    paper_options = {"🌐 All Papers": None}
    for p in papers:
        label = f"{p['title'][:50]} ({p.get('year','?')})"
        paper_options[label] = p["paper_id"]

    selected_label = st.selectbox(
        "Search within:",
        options=list(paper_options.keys()),
        key="paper_filter",
        label_visibility="collapsed",
    )
    selected_paper_id = paper_options[selected_label]

    st.markdown("---")

    # ── Render existing messages ──────────────────────────────────

    session = st.session_state.active_session

    if session:
        msgs = session.get("messages", [])
        if not msgs:
            st.markdown(
                '<p style="color:#3a4060;text-align:center;margin-top:40px;">'
                'Ask your first question below…</p>',
                unsafe_allow_html=True,
            )
        for msg in msgs:
            ts   = format_ts(msg.get("timestamp", ""))
            role = msg["role"]
            if role == "user":
                st.markdown(
                    f'<div class="chat-user">'
                    f'  <div class="chat-role">You</div>'
                    f'  <div>{msg["content"]}</div>'
                    f'  <div class="chat-ts">{ts}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="chat-assistant">'
                    f'  <div class="chat-role">Scholaris</div>'
                    f'  <div>{msg["content"]}</div>'
                    f'  <div class="chat-ts">{ts}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                sources = msg.get("sources", [])
                if sources:
                    with st.expander(f"📎 {len(sources)} source excerpt(s)"):
                        for s in sources:
                            score = s.get("score", 0)
                            chip_color = "#5eead4" if score > 0.8 else "#7c6ff7" if score > 0.6 else "#4a5068"
                            st.markdown(
                                f'<span class="source-chip" style="border-color:{chip_color}">'
                                f'{s.get("title","?")[:35]} · p.{s.get("page_hint","?")} · {score:.2f}'
                                f'</span>',
                                unsafe_allow_html=True,
                            )
                            st.caption(s["text"][:280] + "…")
    else:
        # Welcome screen
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;">
          <div style="font-size:48px;margin-bottom:16px;">🔬</div>
          <h2 style="color:#7c6ff7;font-weight:700;margin-bottom:8px;">Welcome to Scholaris</h2>
          <p style="color:#5c6070;max-width:480px;margin:0 auto;">
            Upload a research paper, then ask questions, explore methodology,
            compare findings, and export your conversation — all in one place.
          </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Chat input ────────────────────────────────────────────────

    if not papers:
        st.info("📄 Upload a paper first (use the **Upload Paper** tab) to start chatting.")
    else:
        with st.form("chat_form", clear_on_submit=True):
            query = st.text_area(
                "Ask anything about your paper(s)…",
                placeholder="e.g. What is the main contribution? What dataset was used?",
                height=90,
                key="chat_input",
                label_visibility="collapsed",
            )
            col_send, col_clear = st.columns([5, 1])
            with col_send:
                submitted = st.form_submit_button("Send ➤", use_container_width=True, type="primary")
            with col_clear:
                clear = st.form_submit_button("Clear", use_container_width=True)

        if clear and st.session_state.active_session_id:
            api("delete", f"/history/{st.session_state.active_session_id}")
            new_chat()
            st.rerun()

        if submitted and query.strip():
            with st.spinner("Thinking…"):
                payload = {
                    "query":      query.strip(),
                    "paper_id":   selected_paper_id,
                    "session_id": st.session_state.active_session_id,
                }
                result = api("post", "/chat", json=payload)
            if result:
                # Update active session
                st.session_state.active_session_id = result["session_id"]
                refresh_session()
                st.rerun()


# ══════════════════════════════════════════════════════════════════
# TAB 2 — UPLOAD
# ══════════════════════════════════════════════════════════════════

with tab_upload:
    st.markdown("### 📄 Upload a Research Paper")
    st.caption("Supported: PDF, DOCX, TXT · Max 50 MB · Scanned PDFs use OCR.Space automatically")

    uploaded = st.file_uploader(
        "Drop your file here",
        type=["pdf", "docx", "doc", "txt"],
        label_visibility="collapsed",
    )

    if uploaded:
        st.markdown(f"**File:** `{uploaded.name}` ({uploaded.size / 1024:.1f} KB)")

        if st.button("⚡ Ingest Document", type="primary"):
            with st.spinner("Processing… extracting text, chunking, embedding — this may take a minute."):
                result = api(
                    "post", "/upload",
                    timeout=600,
                    files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type or "application/octet-stream")},
                )
            if result:
                st.success("✅ Document ingested successfully!")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Chunks", result.get("chunk_count", "—"))
                col2.metric("Pages",  result.get("page_count", "—"))
                col3.metric("Year",   result.get("year", "—") or "—")
                col4.metric("Type",   result.get("doc_type", "—").upper())

                st.markdown(f"**Title:** {result.get('title','—')}")
                if result.get("authors"):
                    st.markdown(f"**Authors:** {', '.join(result['authors'])}")
                if result.get("doi"):
                    st.markdown(f"**DOI:** `{result['doi']}`")
                if result.get("keywords"):
                    kws = " ".join(f'`{k}`' for k in result["keywords"])
                    st.markdown(f"**Keywords:** {kws}")

                st.caption(f"Paper ID: `{result['paper_id']}`")
                st.balloons()


# ══════════════════════════════════════════════════════════════════
# TAB 3 — MY PAPERS
# ══════════════════════════════════════════════════════════════════

with tab_papers:
    st.markdown("### 📚 Ingested Papers")

    papers = api("get", "/papers") or []

    if not papers:
        st.info("No papers ingested yet. Use the **Upload Paper** tab to add one.")
    else:
        for p in papers:
            with st.expander(f"📄 {p.get('title','Unknown')[:70]} — {p.get('year','?')}"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    if p.get("authors"):
                        st.markdown(f"**Authors:** {', '.join(p['authors'])}")
                    st.markdown(f"**Paper ID:** `{p['paper_id']}`")
                    if p.get("year"):
                        st.markdown(f"**Year:** {p['year']}")
                with col2:
                    # Summarize
                    if st.button("✦ Summarize", key=f"sum_{p['paper_id']}"):
                        with st.spinner("Generating summary…"):
                            r = api("post", f"/summarize/{p['paper_id']}")
                        if r:
                            st.markdown(r.get("summary", ""))
                    # Delete
                    if st.button("🗑 Delete", key=f"dp_{p['paper_id']}"):
                        api("delete", f"/papers/{p['paper_id']}")
                        st.success("Paper deleted.")
                        st.rerun()

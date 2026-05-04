"""
FinSight — Agentic Financial Research Analyst
Streamlit UI
"""

import os
import sys
import time
import json
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinSight",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg: #0a0e1a;
    --surface: #111827;
    --surface2: #1a2235;
    --border: #1e2d45;
    --accent: #00d4ff;
    --accent2: #7c3aed;
    --green: #10b981;
    --red: #ef4444;
    --text: #e2e8f0;
    --muted: #64748b;
}

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
    background-color: var(--bg);
    color: var(--text);
}

.stApp { background-color: var(--bg); }

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border);
}

/* Logo */
.finsight-logo {
    font-size: 1.8rem;
    font-weight: 700;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, #00d4ff, #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.2rem;
}
.finsight-tagline {
    font-size: 0.75rem;
    color: var(--muted);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 1.5rem;
}

/* Metric cards */
.metric-card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin: 0.4rem 0;
}
.metric-label {
    font-size: 0.72rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.3rem;
}
.metric-value {
    font-size: 1.4rem;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
}
.metric-green { color: var(--green); }
.metric-red { color: var(--red); }
.metric-blue { color: var(--accent); }

/* Chat messages */
.user-msg {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 12px 12px 4px 12px;
    padding: 1rem 1.2rem;
    margin: 0.8rem 0;
    margin-left: 15%;
}
.agent-msg {
    background: linear-gradient(135deg, rgba(0,212,255,0.05), rgba(124,58,237,0.05));
    border: 1px solid rgba(0,212,255,0.2);
    border-radius: 12px 12px 12px 4px;
    padding: 1rem 1.2rem;
    margin: 0.8rem 0;
    margin-right: 5%;
}
.msg-meta {
    font-size: 0.7rem;
    color: var(--muted);
    margin-bottom: 0.5rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Query type badge */
.badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-left: 0.5rem;
}
.badge-stock { background: rgba(16,185,129,0.15); color: var(--green); border: 1px solid rgba(16,185,129,0.3); }
.badge-ratios { background: rgba(0,212,255,0.1); color: var(--accent); border: 1px solid rgba(0,212,255,0.25); }
.badge-news { background: rgba(251,191,36,0.1); color: #fbbf24; border: 1px solid rgba(251,191,36,0.25); }
.badge-sec { background: rgba(124,58,237,0.15); color: #a78bfa; border: 1px solid rgba(124,58,237,0.3); }
.badge-portfolio { background: rgba(239,68,68,0.1); color: #f87171; border: 1px solid rgba(239,68,68,0.25); }
.badge-general { background: rgba(100,116,139,0.15); color: var(--muted); border: 1px solid var(--border); }

/* Input box */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
    font-family: 'Space Grotesk', sans-serif !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 1px rgba(0,212,255,0.3) !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #00d4ff, #7c3aed) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

/* Ingest button */
.ingest-btn > button {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
}

/* Spinner */
.stSpinner > div { border-top-color: var(--accent) !important; }

/* Divider */
hr { border-color: var(--border) !important; }

/* Stats chip */
.stat-chip {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.4rem 0.8rem;
    font-size: 0.75rem;
    color: var(--muted);
    display: inline-block;
    margin: 0.2rem;
    font-family: 'JetBrains Mono', monospace;
}

/* Thinking indicator */
.thinking {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--muted);
    font-size: 0.8rem;
    padding: 0.5rem 0;
}

/* Section headers */
.section-header {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--muted);
    margin-bottom: 0.8rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
}

/* Warning box */
.warning-box {
    background: rgba(251,191,36,0.05);
    border: 1px solid rgba(251,191,36,0.2);
    border-radius: 8px;
    padding: 0.8rem 1rem;
    font-size: 0.8rem;
    color: #fbbf24;
    margin: 0.5rem 0;
}

/* Success box */
.success-box {
    background: rgba(16,185,129,0.05);
    border: 1px solid rgba(16,185,129,0.2);
    border-radius: 8px;
    padding: 0.8rem 1rem;
    font-size: 0.8rem;
    color: var(--green);
}
</style>
""", unsafe_allow_html=True)


# ── Session state ────────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "api_key_set" not in st.session_state:
    st.session_state.api_key_set = bool(os.getenv("OPENAI_API_KEY"))


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="finsight-logo">FinSight</div>', unsafe_allow_html=True)
    st.markdown('<div class="finsight-tagline">Agentic Financial Research</div>', unsafe_allow_html=True)

    # API Key
    st.markdown('<div class="section-header">Configuration</div>', unsafe_allow_html=True)
    api_key_input = st.text_input(
        "OpenAI API Key",
        type="password",
        value=os.getenv("OPENAI_API_KEY", ""),
        placeholder="sk-...",
        help="Your key is only stored in session memory."
    )
    if api_key_input:
        os.environ["OPENAI_API_KEY"] = api_key_input
        st.session_state.api_key_set = True
        st.markdown('<div class="success-box">✓ API key loaded</div>', unsafe_allow_html=True)

    st.markdown("---")

    # SEC Filing Ingestion
    st.markdown('<div class="section-header">SEC Filing Ingestion</div>', unsafe_allow_html=True)
    st.caption("Index SEC filings into the vector store for RAG queries.")

    ingest_ticker = st.text_input("Ticker to ingest", placeholder="e.g. AAPL", key="ingest_ticker_input").upper()
    ingest_type = st.selectbox("Filing type", ["10-K", "10-Q", "8-K"])
    ingest_limit = st.slider("# of filings", 1, 5, 2)

    if st.button("⬇ Ingest Filings", use_container_width=True):
        if not ingest_ticker:
            st.warning("Enter a ticker first.")
        elif not st.session_state.api_key_set:
            st.warning("Set your API key first.")
        else:
            with st.spinner(f"Fetching {ingest_type} filings for {ingest_ticker}..."):
                try:
                    from rag.pipeline import ingest_ticker as do_ingest
                    result = do_ingest(ingest_ticker, ingest_type, ingest_limit)
                    if result.get("success"):
                        st.success(
                            f"✓ {result['total_chunks_added']} chunks indexed "
                            f"from {len(result['filings'])} filing(s)"
                        )
                    else:
                        st.error(result.get("message", "Ingestion failed."))
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown("---")

    # Vector Store Stats
    st.markdown('<div class="section-header">Vector Store</div>', unsafe_allow_html=True)
    if st.button("🔍 Refresh Stats", use_container_width=True):
        try:
            from rag.pipeline import get_collection_stats
            stats = get_collection_stats()
            st.markdown(
                f'<div class="stat-chip">📄 {stats.get("total_chunks", 0)} chunks</div>',
                unsafe_allow_html=True
            )
            if stats.get("tickers_ingested"):
                st.markdown(
                    f'<div class="stat-chip">🏢 {", ".join(stats["tickers_ingested"])}</div>',
                    unsafe_allow_html=True
                )
        except Exception as e:
            st.error(f"Stats error: {e}")

    st.markdown("---")

    # Example queries
    st.markdown('<div class="section-header">Example Queries</div>', unsafe_allow_html=True)
    examples = [
        "What is Apple's current stock price and P/E ratio?",
        "Fetch the latest news for Tesla",
        "Score a portfolio: AAPL 40%, MSFT 30%, GOOGL 30%",
        "What are the risk factors in Apple's latest 10-K?",
        "Compare P/E ratios of MSFT and GOOGL",
        "What SEC filings are available for Amazon?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True, key=f"ex_{ex[:20]}"):
            st.session_state["prefill_query"] = ex

    st.markdown("---")
    if st.button("🗑 Clear Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

    st.markdown(
        '<div style="font-size:0.65rem;color:#334155;margin-top:1rem;text-align:center;">'
        'FinSight v1.0 · For research only · Not financial advice'
        '</div>',
        unsafe_allow_html=True
    )


# ── Main area ────────────────────────────────────────────────────────────────
col_title, col_status = st.columns([4, 1])
with col_title:
    st.markdown("## 📊 Research Dashboard")
    st.caption("Ask anything about stocks, filings, ratios, news, or your portfolio.")
with col_status:
    if st.session_state.api_key_set:
        st.markdown('<div class="success-box" style="margin-top:1rem;">● Live</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="warning-box" style="margin-top:1rem;">○ No API Key</div>', unsafe_allow_html=True)

st.markdown("---")

# ── Chat history ─────────────────────────────────────────────────────────────
chat_container = st.container()
with chat_container:
    if not st.session_state.chat_history:
        st.markdown(
            """
            <div style="text-align:center;padding:3rem 0;color:#334155;">
                <div style="font-size:3rem;margin-bottom:1rem;">📈</div>
                <div style="font-size:1.1rem;font-weight:600;color:#64748b;">Start your research</div>
                <div style="font-size:0.85rem;color:#475569;margin-top:0.5rem;">
                    Ask about stocks, financial ratios, SEC filings, news, or portfolio risk
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        for turn in st.session_state.chat_history:
            # User message
            st.markdown(
                f'<div class="user-msg">'
                f'<div class="msg-meta">You</div>'
                f'{turn["query"]}'
                f'</div>',
                unsafe_allow_html=True
            )

            # Query type badge
            qtype = turn.get("query_type", "general")
            badge_class = f"badge-{qtype}" if qtype in ("stock","ratios","news","sec_filing","portfolio") else "badge-general"
            ticker_info = f" · {turn['ticker']}" if turn.get("ticker") else ""
            iterations = turn.get("iteration_count", 0)

            st.markdown(
                f'<div class="agent-msg">'
                f'<div class="msg-meta">'
                f'FinSight Agent'
                f'<span class="badge {badge_class}">{qtype}</span>'
                f'<span style="margin-left:0.5rem;font-size:0.65rem;color:#334155;">'
                f'{ticker_info} · {iterations} tool call(s)'
                f'</span>'
                f'</div>',
                unsafe_allow_html=True
            )
            st.markdown(turn["answer"])
            st.markdown('</div>', unsafe_allow_html=True)


# ── Query input ───────────────────────────────────────────────────────────────
st.markdown("---")

# Handle prefilled query from sidebar examples
prefill = st.session_state.pop("prefill_query", "")

with st.form(key="query_form", clear_on_submit=True):
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        user_query = st.text_input(
            "Your research query",
            value=prefill,
            placeholder="e.g. What is Tesla's P/E ratio and recent news?",
            label_visibility="collapsed",
        )
    with col_btn:
        submitted = st.form_submit_button("Ask →", use_container_width=True)


if submitted and user_query.strip():
    if not st.session_state.api_key_set:
        st.error("Please set your OpenAI API key in the sidebar first.")
    else:
        with st.spinner("🤖 FinSight agent is researching..."):
            try:
                from agents.graph import run_query
                t0 = time.time()
                result = run_query(user_query.strip())
                elapsed = round(time.time() - t0, 1)

                st.session_state.chat_history.append({
                    "query": user_query.strip(),
                    "answer": result["final_answer"],
                    "query_type": result.get("query_type", "general"),
                    "ticker": result.get("ticker"),
                    "iteration_count": result.get("iteration_count", 0),
                    "elapsed": elapsed,
                })
                st.rerun()

            except Exception as e:
                st.error(f"Agent error: {e}")
                import traceback
                st.code(traceback.format_exc())

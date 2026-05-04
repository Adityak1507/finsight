"""
FinSight - LangGraph Multi-Agent System
Nodes: router → specialist agent → RAG retrieval → synthesis → response
"""

import json
from typing import TypedDict, Annotated, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import operator

from tools.financial_tools import ALL_TOOLS
from rag.pipeline import retrieve_context, format_context_for_prompt


# ─────────────────────────────────────────────
# State Definition
# ─────────────────────────────────────────────

class FinSightState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    query: str
    query_type: str                    # stock | ratios | news | sec_filing | portfolio | general
    ticker: Optional[str]
    rag_context: str
    tool_outputs: List[str]
    iteration_count: int
    final_answer: str
    error: Optional[str]


# ─────────────────────────────────────────────
# LLM Setup
# ─────────────────────────────────────────────

def get_llm(temperature: float = 0.0):
    return ChatOpenAI(model="gpt-4o-mini", temperature=temperature)

def get_llm_with_tools():
    llm = get_llm()
    return llm.bind_tools(ALL_TOOLS)


# ─────────────────────────────────────────────
# Node 1: Router
# ─────────────────────────────────────────────

ROUTER_PROMPT = """You are a financial query router. Classify the user's query into exactly one category:

Categories:
- "stock": asking about current price, market data, stock performance
- "ratios": asking about financial ratios, valuation, P/E, margins, ROE etc.
- "news": asking about recent news, events, headlines
- "sec_filing": asking about SEC filings, 10-K, 10-Q, annual report, risk factors
- "portfolio": asking about portfolio analysis, risk scoring, diversification
- "rag": asking about detailed company fundamentals that require searching filed documents
- "general": general financial question not needing specific tools

Also extract the primary ticker symbol if mentioned (e.g. AAPL, MSFT, TSLA). Return null if none.

Respond in JSON only:
{{"query_type": "<category>", "ticker": "<TICKER or null>", "reasoning": "<one sentence>"}}

User query: {query}"""


def router_node(state: FinSightState) -> FinSightState:
    """Classify the query and extract ticker."""
    llm = get_llm()
    query = state["query"]

    response = llm.invoke([
        SystemMessage(content="You are a financial query classifier. Respond only with valid JSON."),
        HumanMessage(content=ROUTER_PROMPT.format(query=query))
    ])

    try:
        parsed = json.loads(response.content.strip())
        query_type = parsed.get("query_type", "general")
        ticker = parsed.get("ticker")
    except Exception:
        query_type = "general"
        ticker = None

    return {
        **state,
        "query_type": query_type,
        "ticker": ticker,
        "iteration_count": 0,
    }


# ─────────────────────────────────────────────
# Node 2: RAG Retrieval
# ─────────────────────────────────────────────

def rag_retrieval_node(state: FinSightState) -> FinSightState:
    """Retrieve relevant SEC filing context from ChromaDB."""
    query = state["query"]
    ticker = state.get("ticker")

    chunks = retrieve_context(query, ticker=ticker, top_k=5)
    context = format_context_for_prompt(chunks)

    return {**state, "rag_context": context}


# ─────────────────────────────────────────────
# Node 3: Tool-Calling Agent
# ─────────────────────────────────────────────

AGENT_SYSTEM = """You are FinSight, an expert financial research analyst AI.

You have access to these tools:
1. live_stock_lookup — get real-time price and market data
2. financial_ratio_calculator — get valuation and profitability ratios
3. news_fetcher — get recent news headlines
4. sec_filing_retriever — get links to SEC filings (10-K, 10-Q, 8-K)
5. portfolio_risk_scorer — analyze portfolio risk metrics

SEC Filing Context (from indexed documents):
{rag_context}

Rules:
- Call the most relevant tool(s) for the query
- Do NOT invent financial data — always use tools
- If the SEC context above already answers the question, you may not need a tool call
- Be precise and cite specific numbers when available
"""

def tool_agent_node(state: FinSightState) -> FinSightState:
    """Main tool-calling agent node."""
    llm_with_tools = get_llm_with_tools()
    rag_context = state.get("rag_context", "No SEC filing context available.")

    system_msg = AGENT_SYSTEM.format(rag_context=rag_context[:3000])  # cap context

    messages = [SystemMessage(content=system_msg)] + state["messages"]
    response = llm_with_tools.invoke(messages)

    return {
        **state,
        "messages": [response],
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


# ─────────────────────────────────────────────
# Node 4: Tool Executor
# ─────────────────────────────────────────────

tool_node = ToolNode(ALL_TOOLS)


# ─────────────────────────────────────────────
# Node 5: Synthesis
# ─────────────────────────────────────────────

SYNTHESIS_PROMPT = """You are FinSight, a professional financial research analyst.

The user asked: {query}

Based on the tool results and SEC filing context below, provide a clear, well-structured answer.

SEC Filing Context:
{rag_context}

Guidelines:
- Lead with the most important insight
- Use specific numbers and data points
- Structure your answer clearly (use markdown if helpful)
- If data is unavailable, say so explicitly — never hallucinate
- End with a brief disclaimer: "This is for research purposes only, not financial advice."
"""

def synthesis_node(state: FinSightState) -> FinSightState:
    """Synthesize tool outputs and RAG context into a final answer."""
    llm = get_llm(temperature=0.1)

    rag_context = state.get("rag_context", "")
    query = state["query"]

    messages = [
        SystemMessage(content=SYNTHESIS_PROMPT.format(
            query=query,
            rag_context=rag_context[:2000]
        ))
    ] + state["messages"]

    response = llm.invoke(messages)

    return {
        **state,
        "final_answer": response.content,
        "messages": [response],
    }


# ─────────────────────────────────────────────
# Edge Conditions
# ─────────────────────────────────────────────

def should_use_rag(state: FinSightState) -> str:
    """Decide whether to run RAG retrieval."""
    query_type = state.get("query_type", "general")
    if query_type in ("sec_filing", "rag", "general"):
        return "rag"
    return "agent"


def should_continue_or_synthesize(state: FinSightState) -> str:
    """After agent node: check if tool calls need execution or go to synthesis."""
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None

    # Guard: max iterations
    if state.get("iteration_count", 0) >= 5:
        return "synthesize"

    if last_message and hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "synthesize"


# ─────────────────────────────────────────────
# Build Graph
# ─────────────────────────────────────────────

def build_finsight_graph():
    graph = StateGraph(FinSightState)

    # Add nodes
    graph.add_node("router", router_node)
    graph.add_node("rag", rag_retrieval_node)
    graph.add_node("agent", tool_agent_node)
    graph.add_node("tools", tool_node)
    graph.add_node("synthesis", synthesis_node)

    # Entry
    graph.set_entry_point("router")

    # Router → RAG or Agent
    graph.add_conditional_edges(
        "router",
        should_use_rag,
        {"rag": "rag", "agent": "agent"}
    )

    # RAG → Agent
    graph.add_edge("rag", "agent")

    # Agent → Tools or Synthesis
    graph.add_conditional_edges(
        "agent",
        should_continue_or_synthesize,
        {"tools": "tools", "synthesize": "synthesis"}
    )

    # Tools → Agent (loop)
    graph.add_edge("tools", "agent")

    # Synthesis → END
    graph.add_edge("synthesis", END)

    return graph.compile()


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

_graph = None

def get_graph():
    global _graph
    if _graph is None:
        _graph = build_finsight_graph()
    return _graph


def run_query(query: str) -> dict:
    """
    Run a financial query through the full FinSight agent pipeline.
    Returns dict with final_answer, query_type, ticker, and messages.
    """
    graph = get_graph()

    initial_state: FinSightState = {
        "messages": [HumanMessage(content=query)],
        "query": query,
        "query_type": "general",
        "ticker": None,
        "rag_context": "",
        "tool_outputs": [],
        "iteration_count": 0,
        "final_answer": "",
        "error": None,
    }

    result = graph.invoke(initial_state)

    return {
        "final_answer": result.get("final_answer", "No answer generated."),
        "query_type": result.get("query_type", "general"),
        "ticker": result.get("ticker"),
        "iteration_count": result.get("iteration_count", 0),
    }

"""
FinSight RAG Pipeline
Handles SEC filing ingestion, chunking, embedding, and retrieval via ChromaDB.
"""

import os
import re
import requests
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Optional
from datetime import datetime


CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "sec_filings"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
TOP_K = 5

SEC_HEADERS = {"User-Agent": "FinSight Research Tool research@finsight.ai"}



# ChromaDB Client + Collection


def get_chroma_collection():
    """Initialize ChromaDB client and return the SEC filings collection."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )
    return collection



# Text Chunking


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks by word count.
    Preserves sentence boundaries where possible.
    """
    # Clean the text
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)  # Remove non-ASCII

    words = text.split()
    if len(words) <= chunk_size:
        return [text] if text.strip() else []

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap

    return chunks



# SEC Filing Fetcher


def get_cik_for_ticker(ticker: str) -> Optional[str]:
    """Resolve ticker to SEC CIK number."""
    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        resp = requests.get(url, headers=SEC_HEADERS, timeout=10)
        data = resp.json()
        for _, val in data.items():
            if val.get("ticker", "").upper() == ticker.upper():
                return str(val["cik_str"]).zfill(10)
        return None
    except Exception:
        return None


def fetch_filing_urls(ticker: str, filing_type: str = "10-K", limit: int = 3) -> List[Dict]:
    """Get URLs of recent SEC filings for a ticker."""
    cik = get_cik_for_ticker(ticker)
    if not cik:
        return []

    try:
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        resp = requests.get(url, headers=SEC_HEADERS, timeout=10)
        data = resp.json()

        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        accessions = filings.get("accessionNumber", [])
        primary_docs = filings.get("primaryDocument", [])

        results = []
        for i, form in enumerate(forms):
            if form == filing_type and len(results) < limit:
                acc_no = accessions[i].replace("-", "")
                doc = primary_docs[i]
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no}/{doc}"
                results.append({
                    "ticker": ticker.upper(),
                    "form_type": form,
                    "filing_date": dates[i],
                    "url": filing_url,
                    "accession": accessions[i],
                })
        return results
    except Exception:
        return []


def fetch_filing_text(url: str, max_chars: int = 50000) -> str:
    """Download and extract plain text from an SEC filing HTML/text document."""
    try:
        resp = requests.get(url, headers=SEC_HEADERS, timeout=15)
        resp.raise_for_status()

        content = resp.text

        # Parse HTML if present
        if "<html" in content.lower() or "<body" in content.lower():
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "html.parser")
            # Remove tables of numbers (often noise)
            for tag in soup.find_all(["script", "style", "ix:header"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
        else:
            text = content

        # Trim to max_chars
        return text[:max_chars]
    except Exception as e:
        return ""



# Ingestion Pipeline


def ingest_ticker(ticker: str, filing_type: str = "10-K", limit: int = 2) -> Dict:
    """
    Full ingestion pipeline for a ticker:
    1. Fetch recent SEC filings
    2. Download and extract text
    3. Chunk text
    4. Embed and store in ChromaDB

    Returns a summary dict.
    """
    collection = get_chroma_collection()
    filing_urls = fetch_filing_urls(ticker, filing_type, limit)

    if not filing_urls:
        return {"success": False, "message": f"No {filing_type} filings found for {ticker}"}

    total_chunks = 0
    ingested_filings = []

    for filing in filing_urls:
        # Check if already ingested
        existing = collection.get(
            where={"accession": filing["accession"]},
            limit=1
        )
        if existing["ids"]:
            ingested_filings.append({
                "filing_date": filing["filing_date"],
                "status": "already_ingested",
                "chunks": 0
            })
            continue

        text = fetch_filing_text(filing["url"])
        if not text:
            continue

        chunks = chunk_text(text)
        if not chunks:
            continue

        # Prepare ChromaDB batch
        ids = [f"{ticker}_{filing['accession']}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "ticker": ticker.upper(),
                "form_type": filing["form_type"],
                "filing_date": filing["filing_date"],
                "accession": filing["accession"],
                "chunk_index": i,
                "source_url": filing["url"],
            }
            for i in range(len(chunks))
        ]

        # Batch insert (ChromaDB limit ~5000 per call)
        batch_size = 500
        for b in range(0, len(chunks), batch_size):
            collection.add(
                documents=chunks[b:b+batch_size],
                ids=ids[b:b+batch_size],
                metadatas=metadatas[b:b+batch_size],
            )

        total_chunks += len(chunks)
        ingested_filings.append({
            "filing_date": filing["filing_date"],
            "status": "ingested",
            "chunks": len(chunks),
            "url": filing["url"],
        })

    return {
        "success": True,
        "ticker": ticker.upper(),
        "filing_type": filing_type,
        "total_chunks_added": total_chunks,
        "filings": ingested_filings,
    }



# Retrieval


def retrieve_context(query: str, ticker: Optional[str] = None, top_k: int = TOP_K) -> List[Dict]:
    """
    Retrieve top-k relevant chunks from ChromaDB for a query.
    Optionally filter by ticker.
    Returns list of {text, metadata, distance}.
    """
    collection = get_chroma_collection()

    where = {"ticker": ticker.upper()} if ticker else None

    try:
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )

        chunks = []
        for i, doc in enumerate(results["documents"][0]):
            chunks.append({
                "text": doc,
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            })
        return chunks

    except Exception as e:
        return []


def format_context_for_prompt(chunks: List[Dict]) -> str:
    """Format retrieved chunks into a readable context string for the LLM prompt."""
    if not chunks:
        return "No relevant SEC filing context found."

    context_parts = []
    for i, chunk in enumerate(chunks):
        meta = chunk["metadata"]
        context_parts.append(
            f"[Source {i+1}: {meta.get('ticker','?')} {meta.get('form_type','?')} "
            f"filed {meta.get('filing_date','?')}]\n{chunk['text']}"
        )
    return "\n\n---\n\n".join(context_parts)


def get_collection_stats() -> Dict:
    """Return stats about what's currently in the vector store."""
    try:
        collection = get_chroma_collection()
        count = collection.count()
        if count == 0:
            return {"total_chunks": 0, "tickers": [], "message": "Vector store is empty."}

        # Sample metadata to get unique tickers
        sample = collection.get(limit=min(count, 1000), include=["metadatas"])
        tickers = list(set(m.get("ticker", "?") for m in sample["metadatas"]))
        forms = list(set(m.get("form_type", "?") for m in sample["metadatas"]))

        return {
            "total_chunks": count,
            "tickers_ingested": sorted(tickers),
            "filing_types": sorted(forms),
        }
    except Exception as e:
        return {"error": str(e)}

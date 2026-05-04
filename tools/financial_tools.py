"""
FinSight - 5 Core Financial Tools
Tools: financial ratio calculator, live stock lookup,
       news fetcher, SEC filing retriever, portfolio risk scorer
"""

import json
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from langchain.tools import tool
from bs4 import BeautifulSoup


# ─────────────────────────────────────────────
# TOOL 1: Live Stock Lookup
# ─────────────────────────────────────────────
@tool
def live_stock_lookup(ticker: str) -> str:
    """
    Fetch real-time stock price, market cap, volume, 52-week range,
    and basic info for a given ticker symbol.
    Input: ticker symbol e.g. 'AAPL', 'MSFT', 'TSLA'
    """
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        price = info.get("currentPrice") or info.get("regularMarketPrice", "N/A")
        prev_close = info.get("previousClose", "N/A")
        change = round(price - prev_close, 2) if price != "N/A" and prev_close != "N/A" else "N/A"
        pct_change = round((change / prev_close) * 100, 2) if change != "N/A" else "N/A"

        result = {
            "ticker": ticker.upper(),
            "company_name": info.get("longName", "N/A"),
            "current_price": price,
            "previous_close": prev_close,
            "change": change,
            "change_pct": f"{pct_change}%",
            "market_cap": info.get("marketCap", "N/A"),
            "volume": info.get("volume", "N/A"),
            "avg_volume": info.get("averageVolume", "N/A"),
            "52_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
            "52_week_low": info.get("fiftyTwoWeekLow", "N/A"),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "currency": info.get("currency", "USD"),
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Could not fetch stock data for {ticker}: {str(e)}"})


# ─────────────────────────────────────────────
# TOOL 2: Financial Ratio Calculator
# ─────────────────────────────────────────────
@tool
def financial_ratio_calculator(ticker: str) -> str:
    """
    Calculate key financial ratios for a stock: P/E, P/B, EV/EBITDA,
    Debt-to-Equity, ROE, ROA, Current Ratio, Gross Margin, and more.
    Input: ticker symbol e.g. 'AAPL'
    """
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        ratios = {
            "ticker": ticker.upper(),
            "valuation_ratios": {
                "pe_ratio": info.get("trailingPE", "N/A"),
                "forward_pe": info.get("forwardPE", "N/A"),
                "peg_ratio": info.get("pegRatio", "N/A"),
                "price_to_book": info.get("priceToBook", "N/A"),
                "price_to_sales": info.get("priceToSalesTrailing12Months", "N/A"),
                "ev_to_ebitda": info.get("enterpriseToEbitda", "N/A"),
                "ev_to_revenue": info.get("enterpriseToRevenue", "N/A"),
            },
            "profitability_ratios": {
                "gross_margin": f"{round(info.get('grossMargins', 0) * 100, 2)}%" if info.get('grossMargins') else "N/A",
                "operating_margin": f"{round(info.get('operatingMargins', 0) * 100, 2)}%" if info.get('operatingMargins') else "N/A",
                "net_margin": f"{round(info.get('profitMargins', 0) * 100, 2)}%" if info.get('profitMargins') else "N/A",
                "roe": f"{round(info.get('returnOnEquity', 0) * 100, 2)}%" if info.get('returnOnEquity') else "N/A",
                "roa": f"{round(info.get('returnOnAssets', 0) * 100, 2)}%" if info.get('returnOnAssets') else "N/A",
            },
            "liquidity_and_leverage": {
                "current_ratio": info.get("currentRatio", "N/A"),
                "quick_ratio": info.get("quickRatio", "N/A"),
                "debt_to_equity": info.get("debtToEquity", "N/A"),
                "total_debt": info.get("totalDebt", "N/A"),
                "free_cashflow": info.get("freeCashflow", "N/A"),
            },
            "growth_metrics": {
                "revenue_growth_yoy": f"{round(info.get('revenueGrowth', 0) * 100, 2)}%" if info.get('revenueGrowth') else "N/A",
                "earnings_growth_yoy": f"{round(info.get('earningsGrowth', 0) * 100, 2)}%" if info.get('earningsGrowth') else "N/A",
                "revenue_ttm": info.get("totalRevenue", "N/A"),
                "ebitda": info.get("ebitda", "N/A"),
            },
            "dividend_info": {
                "dividend_yield": f"{round(info.get('dividendYield', 0) * 100, 2)}%" if info.get('dividendYield') else "N/A",
                "payout_ratio": f"{round(info.get('payoutRatio', 0) * 100, 2)}%" if info.get('payoutRatio') else "N/A",
            }
        }
        return json.dumps(ratios, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Could not calculate ratios for {ticker}: {str(e)}"})


# ─────────────────────────────────────────────
# TOOL 3: Financial News Fetcher
# ─────────────────────────────────────────────
@tool
def news_fetcher(query: str) -> str:
    """
    Fetch recent financial news headlines and summaries for a company or topic.
    Input: company name or ticker or topic e.g. 'Apple AAPL earnings', 'Fed interest rates'
    """
    try:
        # Try yfinance news first
        ticker_guess = query.split()[0].upper()
        stock = yf.Ticker(ticker_guess)
        news = stock.news

        if news:
            articles = []
            for item in news[:8]:
                articles.append({
                    "title": item.get("title", "N/A"),
                    "publisher": item.get("publisher", "N/A"),
                    "link": item.get("link", "N/A"),
                    "published": datetime.fromtimestamp(
                        item.get("providerPublishTime", 0)
                    ).strftime("%Y-%m-%d %H:%M") if item.get("providerPublishTime") else "N/A",
                    "summary": item.get("summary", "No summary available"),
                })
            return json.dumps({
                "query": query,
                "source": "Yahoo Finance",
                "articles_found": len(articles),
                "articles": articles
            }, indent=2)
        else:
            return json.dumps({
                "query": query,
                "message": "No recent news found. Try a different ticker or topic.",
                "articles": []
            })
    except Exception as e:
        return json.dumps({"error": f"News fetch failed: {str(e)}"})


# ─────────────────────────────────────────────
# TOOL 4: SEC Filing Retriever
# ─────────────────────────────────────────────
@tool
def sec_filing_retriever(ticker: str, filing_type: str = "10-K") -> str:
    """
    Retrieve recent SEC filings metadata and key sections for a company.
    Supports filing types: '10-K' (annual), '10-Q' (quarterly), '8-K' (current events).
    Input: ticker symbol and filing type e.g. ticker='AAPL', filing_type='10-K'
    """
    try:
        # Use SEC EDGAR full-text search API
        headers = {"User-Agent": "FinSight Research Tool research@finsight.ai"}

        # Get CIK number from ticker
        cik_url = f"https://data.sec.gov/submissions/CIK{_get_cik(ticker, headers)}.json"

        cik = _get_cik(ticker, headers)
        if not cik:
            return json.dumps({"error": f"Could not find CIK for ticker {ticker}"})

        sub_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        response = requests.get(sub_url, headers=headers, timeout=10)
        data = response.json()

        company_name = data.get("name", ticker)
        filings = data.get("filings", {}).get("recent", {})

        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        accession = filings.get("accessionNumber", [])
        primary_doc = filings.get("primaryDocument", [])

        results = []
        for i, form in enumerate(forms):
            if form == filing_type and len(results) < 5:
                acc_no = accession[i].replace("-", "")
                doc = primary_doc[i]
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no}/{doc}"
                results.append({
                    "form_type": form,
                    "filing_date": dates[i],
                    "accession_number": accession[i],
                    "document_url": filing_url,
                })

        return json.dumps({
            "ticker": ticker.upper(),
            "company_name": company_name,
            "filing_type": filing_type,
            "filings_found": len(results),
            "recent_filings": results,
            "note": "Use the document URLs to access full filing content."
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": f"SEC filing retrieval failed: {str(e)}"})


def _get_cik(ticker: str, headers: dict) -> str | None:
    """Helper to get CIK from ticker symbol."""
    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        response = requests.get(url, headers=headers, timeout=10)
        tickers_data = response.json()
        for key, val in tickers_data.items():
            if val.get("ticker", "").upper() == ticker.upper():
                return str(val["cik_str"]).zfill(10)
        return None
    except:
        return None


# ─────────────────────────────────────────────
# TOOL 5: Portfolio Risk Scorer
# ─────────────────────────────────────────────
@tool
def portfolio_risk_scorer(portfolio_json: str) -> str:
    """
    Score and analyze portfolio risk given a JSON string of holdings.
    Calculates beta, volatility, Sharpe ratio, correlation matrix, and concentration risk.
    Input: JSON string like '[{"ticker": "AAPL", "weight": 0.4}, {"ticker": "MSFT", "weight": 0.6}]'
    Weights should sum to 1.0.
    """
    try:
        holdings = json.loads(portfolio_json)
        if not holdings:
            return json.dumps({"error": "Empty portfolio provided."})

        tickers = [h["ticker"].upper() for h in holdings]
        weights = np.array([h["weight"] for h in holdings])

        # Normalize weights if needed
        weights = weights / weights.sum()

        # Fetch 1-year historical data
        end = datetime.today()
        start = end - timedelta(days=365)
        prices = yf.download(tickers, start=start, end=end, progress=False)["Close"]

        if isinstance(prices, pd.Series):
            prices = prices.to_frame(tickers[0])

        # Drop columns with all NaN
        prices = prices.dropna(axis=1, how="all").dropna()
        valid_tickers = list(prices.columns)

        if prices.empty:
            return json.dumps({"error": "Could not fetch price data for portfolio."})

        # Daily returns
        returns = prices.pct_change().dropna()

        # Portfolio metrics
        port_returns = (returns * weights[:len(valid_tickers)]).sum(axis=1)
        annual_return = port_returns.mean() * 252
        annual_vol = port_returns.std() * np.sqrt(252)
        sharpe = (annual_return - 0.05) / annual_vol if annual_vol > 0 else 0

        # Individual stock betas vs S&P 500
        sp500 = yf.download("^GSPC", start=start, end=end, progress=False)["Close"]
        sp500_returns = sp500.pct_change().dropna()
        sp500_returns = sp500_returns.reindex(returns.index).dropna()
        aligned_returns = returns.reindex(sp500_returns.index)

        betas = {}
        for ticker in valid_tickers:
            if ticker in aligned_returns.columns:
                cov = np.cov(aligned_returns[ticker].dropna(), sp500_returns)[0, 1]
                var = np.var(sp500_returns)
                betas[ticker] = round(cov / var, 3) if var > 0 else "N/A"

        port_beta = sum(
            betas.get(t, 0) * w
            for t, w in zip(valid_tickers, weights[:len(valid_tickers)])
            if isinstance(betas.get(t), float)
        )

        # Concentration risk (Herfindahl Index)
        hhi = sum(w**2 for w in weights) * 10000

        # Correlation matrix
        corr = returns[valid_tickers].corr().round(3).to_dict()

        # Risk classification
        if annual_vol < 0.10:
            risk_level = "LOW"
        elif annual_vol < 0.20:
            risk_level = "MODERATE"
        elif annual_vol < 0.35:
            risk_level = "HIGH"
        else:
            risk_level = "VERY HIGH"

        result = {
            "portfolio_summary": {
                "holdings": [
                    {"ticker": t, "weight": f"{round(w*100, 1)}%", "beta": betas.get(t, "N/A")}
                    for t, w in zip(valid_tickers, weights[:len(valid_tickers)])
                ],
                "total_tickers": len(valid_tickers),
            },
            "risk_metrics": {
                "risk_level": risk_level,
                "annual_volatility": f"{round(annual_vol * 100, 2)}%",
                "annual_expected_return": f"{round(annual_return * 100, 2)}%",
                "sharpe_ratio": round(sharpe, 3),
                "portfolio_beta": round(port_beta, 3),
                "concentration_risk_hhi": round(hhi, 1),
                "hhi_interpretation": (
                    "Highly concentrated (>2500)" if hhi > 2500
                    else "Moderately concentrated (1000-2500)" if hhi > 1000
                    else "Well diversified (<1000)"
                ),
            },
            "correlation_matrix": corr,
            "risk_warnings": _generate_risk_warnings(annual_vol, port_beta, hhi, sharpe),
        }
        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Portfolio risk scoring failed: {str(e)}"})


def _generate_risk_warnings(vol, beta, hhi, sharpe):
    warnings = []
    if vol > 0.30:
        warnings.append("⚠️ Very high portfolio volatility — consider adding defensive assets.")
    if beta > 1.5:
        warnings.append("⚠️ High market sensitivity (beta > 1.5) — portfolio amplifies market swings.")
    if hhi > 2500:
        warnings.append("⚠️ High concentration risk — consider diversifying across more assets.")
    if sharpe < 0:
        warnings.append("⚠️ Negative Sharpe ratio — portfolio returns don't justify the risk taken.")
    if not warnings:
        warnings.append("✅ Portfolio metrics look reasonable. Always consult a financial advisor.")
    return warnings


# Export all tools as a list
ALL_TOOLS = [
    live_stock_lookup,
    financial_ratio_calculator,
    news_fetcher,
    sec_filing_retriever,
    portfolio_risk_scorer,
]

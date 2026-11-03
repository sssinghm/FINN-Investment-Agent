"""FINN API and static web application."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .companies import COMPANIES, COMPANY_BY_TICKER
from .data_gateway import (
    classify_announcement, evaluate_alert_rules, fetch_nse_announcements,
    fetch_price_history, now_ist,
)
from .research_engine import coverage_summary, research
from .store import get_alert_rules, recent_research, save_alert_rules, save_research_run, init_db

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

app = FastAPI(title="FINN — Financial Investment Agent", version="0.1.0", description="Evidence-first investment intelligence prototype")
app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")


class ResearchRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=24)
    question: str = Field(default="Give me a business and financial overview.", max_length=1200)
    mode: str = Field(default="deep_dive", max_length=32)


class AlertRuleUpdate(BaseModel):
    price_move_pct: float = Field(default=3.0, ge=0.1, le=30)
    volume_multiple: float = Field(default=2.0, ge=1.0, le=20)
    window_days: int = Field(default=1, ge=1, le=30)
    categories: list[str] = Field(default_factory=lambda: ["results", "M&A", "management_change", "litigation", "fund_raise"])
    collapse_routine: bool = True


@app.on_event("startup")
def startup():
    init_db()


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(FRONTEND / "index.html")


@app.get("/api/health")
def health():
    return {
        "status": "ok", "app": "FINN", "version": "0.1.0",
        "timestamp": now_ist().isoformat(), "portfolio_count": len(COMPANIES),
        "price_provider": "Yahoo Finance chart endpoint (best-effort, cached, synthetic fallback labeled)",
        "announcement_provider": "NSE public corporate-announcements feed (best-effort, synthetic fallback labeled)",
        "research_coverage": coverage_summary(),
    }


@app.get("/api/companies")
def companies(search: str | None = Query(default=None, max_length=60), sector: str | None = None):
    rows = COMPANIES
    if search:
        q = search.lower().strip()
        rows = [c for c in rows if q in c["ticker"].lower() or q in c["name"].lower() or q in c["sector"].lower()]
    if sector:
        rows = [c for c in rows if c["sector"].lower() == sector.lower()]
    return {"items": rows, "count": len(rows), "sectors": sorted({c["sector"] for c in COMPANIES})}


@app.get("/api/portfolio")
def portfolio():
    return {"items": COMPANIES, "count": len(COMPANIES), "updated_at": now_ist().isoformat()}


@app.get("/api/feed")
def feed(days: int = Query(default=1, ge=1, le=30), ticker: str | None = None,
         category: str | None = None, priority: str | None = None):
    records, mode, warning = fetch_nse_announcements(days)
    if ticker:
        records = [r for r in records if r["ticker"].upper() == ticker.upper()]
    if category and category.lower() != "all":
        records = [r for r in records if r["category"].lower() == category.lower()]
    if priority and priority.lower() != "all":
        records = [r for r in records if r["priority"].lower() == priority.lower()]
    priority_order = {"High": 0, "Medium": 1, "Routine": 2}
    records.sort(key=lambda r: r.get("published_at", ""), reverse=True)
    records.sort(key=lambda r: priority_order.get(r.get("priority"), 3))
    # Keep the result compact while leaving the full source count visible.
    return {"items": records, "count": len(records), "source_mode": mode,
            "is_demo": mode == "demo", "warning": warning,
            "window_days": days, "updated_at": now_ist().isoformat()}


@app.get("/api/company/{ticker}")
def company(ticker: str):
    ticker = ticker.upper().strip()
    if not re.fullmatch(r"[A-Z0-9&._-]{1,24}", ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format")
    profile = COMPANY_BY_TICKER.get(ticker)
    if not profile:
        # Generalizes to an arbitrary NSE ticker; research coverage is separate from portfolio membership.
        profile = {"ticker": ticker, "yahoo": f"{ticker}.NS", "name": ticker,
                   "sector": "Not in demo registry", "exchange": "NSE", "market_cap_band": "Unknown",
                   "description": "Company profile is not in the curated demo registry. FINN can still check research coverage and source availability."}
    price = None
    if ticker in COMPANY_BY_TICKER:
        price = fetch_price_history(ticker, "3mo")
    return {"company": profile, "price": price, "coverage": coverage_summary(),
            "research_sources": [{"label": "Screener company page", "url": f"https://www.screener.in/company/{ticker}/"},
                                 {"label": "NSE corporate announcements", "url": "https://www.nseindia.com/companies-listing/corporate-filings-announcements"}]}


@app.get("/api/prices/{ticker}")
def prices(ticker: str, period: str = Query(default="3mo", pattern="^(1mo|3mo|6mo|1y)$")):
    try:
        return fetch_price_history(ticker.upper(), period)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/alerts/rules")
def alert_rules():
    return get_alert_rules()


@app.put("/api/alerts/rules")
def update_alert_rules(update: AlertRuleUpdate):
    allowed_categories = {"results", "M&A", "fund_raise", "management_change", "litigation", "insider_trading", "earnings_call", "investor_meetings", "credit_rating", "dividend", "bonus_split", "capex", "press_release", "postal_ballot", "agm_egm", "pledging", "unclassified"}
    payload = update.model_dump()
    payload["categories"] = [c for c in payload["categories"] if c in allowed_categories]
    return save_alert_rules(payload)


@app.get("/api/alerts/preview")
def alert_preview():
    rules = get_alert_rules()
    items = []
    # Three names provide a quick portfolio preview without making 18 upstream calls on this screen.
    for ticker in ["TCS", "RELIANCE", "BHARTIARTL"]:
        try:
            p = fetch_price_history(ticker, "3mo")
            for alert in evaluate_alert_rules(p, rules):
                alert["company"] = COMPANY_BY_TICKER[ticker]["name"]
                alert["source_note"] = p.get("source_note")
                items.append(alert)
        except Exception:
            continue
    return {"items": items, "count": len(items), "rules": rules,
            "source_mode": "demo" if any(i["source_mode"] == "demo" for i in items) else "live"}


@app.post("/api/research")
def run_research(request: ResearchRequest):
    ticker = request.ticker.upper().strip()
    if not re.fullmatch(r"[A-Z0-9&._-]{1,24}", ticker):
        raise HTTPException(status_code=400, detail="Enter a valid NSE ticker, for example TCS or RELIANCE")
    try:
        result = research(ticker, request.question, request.mode)
        result["research_id"] = save_research_run(ticker, request.question, result["status"], result)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Research request failed safely: {str(exc)[:160]}") from exc


@app.get("/api/research/history")
def research_history():
    return {"items": recent_research(12)}


@app.get("/api/research/coverage")
def research_coverage():
    return coverage_summary()


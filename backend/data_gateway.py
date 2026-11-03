"""Public-source adapters with transparent fallbacks for the FINN prototype.

Live adapters are best-effort and never disguise synthetic samples as real data.
"""
from __future__ import annotations

import math
import os
import random
import re
import time
from datetime import datetime, timedelta
from statistics import mean
from typing import Any
from zoneinfo import ZoneInfo

import requests

from .companies import COMPANIES, COMPANY_BY_TICKER

IST = ZoneInfo("Asia/Kolkata")
OFFLINE = os.getenv("FINN_OFFLINE_MODE", "0").strip() == "1"
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
NSE_LANDING = "https://www.nseindia.com/companies-listing/corporate-filings-announcements"
NSE_API = "https://www.nseindia.com/api/corporate-announcements"

# Small process cache: avoid repeated upstream requests during one demo session.
_CACHE: dict[str, tuple[float, Any]] = {}


def now_ist() -> datetime:
    return datetime.now(IST)


def _cache_get(key: str, ttl: int):
    item = _CACHE.get(key)
    if item and time.time() - item[0] < ttl:
        return item[1]
    return None


def _cache_set(key: str, value: Any):
    _CACHE[key] = (time.time(), value)


def classify_announcement(text: str) -> tuple[str, str]:
    t = (text or "").lower()
    rules = [
        ("results", ["financial results", "quarterly results", "outcome of board meeting", "audited results", "unaudited results", "earnings"]),
        ("M&A", ["acquisition", "merger", "demerger", "joint venture", "acquire stake", "sale of stake"]),
        ("management_change", ["resignation", "appointment of", "change in management", "chief executive", "chief financial officer", "managing director"]),
        ("litigation", ["court", "litigation", "regulatory order", "penalty", "fine", "show cause", "insolvency"]),
        ("fund_raise", ["qualified institutions placement", "qip", "rights issue", "preferential issue", "commercial paper", "buyback", "fund raising"]),
        ("insider_trading", ["insider trading", "disclosure under regulation 7", "promoter acquisition", "promoter sale"]),
        ("earnings_call", ["earnings call", "conference call", "concall", "transcript of the call"]),
        ("investor_meetings", ["investor meet", "investor meeting", "institutional investor", "investor conference"]),
        ("credit_rating", ["credit rating", "rating rationale", "rating upgraded", "rating downgraded"]),
        ("dividend", ["dividend", "interim dividend", "final dividend"]),
        ("bonus_split", ["stock split", "sub-division", "bonus issue", "bonus shares"]),
        ("capex", ["capital expenditure", "capex", "new plant", "capacity expansion", "manufacturing facility"]),
        ("pledging", ["pledge", "pledging", "release of encumbrance"]),
        ("agm_egm", ["annual general meeting", "extraordinary general meeting", "agm", "egm"]),
        ("postal_ballot", ["postal ballot", "remote e-voting"]),
        ("press_release", ["press release", "order win", "new product", "partnership", "business update"]),
    ]
    for category, needles in rules:
        if any(n in t for n in needles):
            return category, _priority_for(category, t)
    return "unclassified", "Routine"


def _priority_for(category: str, text: str) -> str:
    if category in {"M&A", "litigation", "results", "management_change", "fund_raise", "credit_rating"}:
        return "High"
    if category in {"capex", "dividend", "pledging", "insider_trading", "bonus_split"}:
        return "Medium"
    if any(s in text for s in ["material", "significant", "large", "order win"]):
        return "Medium"
    return "Routine"


def _demo_announcements(days: int = 1) -> list[dict[str, Any]]:
    """Synthetic scenarios for UX testing; never presented as genuine exchange filings."""
    now = now_ist()
    examples = [
        ("TCS", "Quarterly results", "RESULTS", "Revenue growth moderated while the operating margin moved lower in this illustrative scenario.", "High", "Compare the reported margin with management's prior-quarter commentary."),
        ("RELIANCE", "Board to consider investment proposal", "capex", "Illustrative capital-allocation announcement; check the original filing before drawing conclusions.", "High", "Review the amount, funding source and expected commissioning timeline."),
        ("HDFCBANK", "Investor call scheduled", "earnings_call", "Illustrative investor communication with a source-first follow-up path.", "Routine", "Use the transcript to find management's explanation for key balance-sheet movements."),
        ("SUNPHARMA", "Regulatory matter disclosed", "litigation", "Illustrative disclosure card showing how a legal event would be surfaced without presuming an outcome.", "High", "Inspect the stated exposure, status and any disclosed next steps."),
        ("BHARTIARTL", "Daily volume alert", "market_alert", "Illustrative volume threshold crossed: 2.4× the previous 20-session average.", "Medium", "Check the price series and any contemporaneous primary disclosure; no causal link is assumed."),
        ("INFY", "Management commentary updated", "management_change", "Illustrative leadership-change card with a place to add a sourced professional background.", "High", "Verify the appointment, effective date and official company biography."),
        ("NTPC", "Routine compliance certificate", "unclassified", "Illustrative routine filing retained in the archive rather than promoted into the main feed.", "Routine", "Open the source only if compliance detail is relevant to your workflow."),
        ("ICICIBANK", "Daily price move alert", "market_alert", "Illustrative daily close moved beyond a configurable ±3% threshold.", "Medium", "Confirm the price change against the source series and review relevant filings."),
    ]
    out = []
    for i, (ticker, subject, category, summary, priority, why) in enumerate(examples):
        if i >= 5 and days <= 1:
            continue
        ts = now - timedelta(minutes=19 + i * 53 if days <= 1 else i * 245)
        c = COMPANY_BY_TICKER[ticker]
        out.append({
            "id": f"demo-{ticker.lower()}-{i}", "ticker": ticker, "company": c["name"],
            "subject": subject, "category": category, "summary": summary,
            "priority": priority, "priority_reason": why,
            "published_at": ts.isoformat(), "source_url": None,
            "source_name": "Illustrative demo record", "source_mode": "demo",
            "is_demo": True, "source_note": "Synthetic scenario — not an actual company announcement or market event.",
        })
    return out


def fetch_nse_announcements(days: int = 1) -> tuple[list[dict[str, Any]], str, str | None]:
    if OFFLINE:
        return _demo_announcements(days), "demo", "Offline mode enabled"
    key = f"nse-announcements-{days}"
    cached = _cache_get(key, 300)
    if cached is not None:
        return cached, "live", None

    today = now_ist().date()
    from_day = today - timedelta(days=max(1, days) - 1)
    params = {
        "index": "equities",
        "from_date": from_day.strftime("%d-%m-%Y"),
        "to_date": today.strftime("%d-%m-%Y"),
    }
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": NSE_LANDING,
    })
    try:
        # Use the public filing page to establish a normal read-only session. If access is denied,
        # stop and fall back transparently; no CAPTCHA or access controls are bypassed.
        landing = session.get(NSE_LANDING, timeout=7)
        if landing.status_code >= 400:
            raise RuntimeError(f"NSE landing page returned HTTP {landing.status_code}")
        response = session.get(NSE_API, params=params, timeout=8)
        if response.status_code in (401, 403, 429):
            raise RuntimeError(f"NSE source unavailable (HTTP {response.status_code})")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise RuntimeError("Unexpected NSE announcement payload")
        portfolio = set(COMPANY_BY_TICKER)
        records = []
        for row in payload:
            ticker = str(row.get("symbol") or "").strip().upper()
            if ticker not in portfolio:
                continue
            company = COMPANY_BY_TICKER[ticker]
            subject = str(row.get("desc") or row.get("subject") or "Corporate announcement").strip()
            category, priority = classify_announcement(subject)
            date_text = row.get("an_dt") or row.get("sort_date") or row.get("dt")
            parsed = _parse_nse_date(date_text)
            link = row.get("attchmntFile") or row.get("attachment")
            records.append({
                "id": str(row.get("seq_id") or f"nse-{ticker}-{parsed.isoformat() if parsed else subject[:20]}"),
                "ticker": ticker, "company": str(row.get("sm_name") or company["name"]),
                "subject": subject, "category": category,
                "summary": str(row.get("attchmntText") or subject).strip(),
                "priority": priority,
                "priority_reason": _priority_reason(category, subject, priority),
                "published_at": parsed.isoformat() if parsed else now_ist().isoformat(),
                "source_url": link, "source_name": "NSE corporate announcement",
                "source_mode": "live", "is_demo": False, "source_note": None,
            })
        records.sort(key=lambda x: (x["priority"] == "High", x["priority"] == "Medium", x["published_at"]), reverse=True)
        _cache_set(key, records)
        return records, "live", None
    except Exception as exc:
        msg = str(exc)
        demo = _demo_announcements(days)
        return demo, "demo", f"NSE feed unavailable; showing labeled illustrative records. Detail: {msg[:160]}"


def _priority_reason(category: str, subject: str, priority: str) -> str:
    if category == "results": return "Results filings can change the view of growth, margins and earnings quality; review the figures before assessing materiality."
    if category == "M&A": return "An acquisition or disposal can affect capital allocation, leverage and the business mix."
    if category == "management_change": return "Leadership changes can affect execution; verify the role, effective date and transition details."
    if category == "litigation": return "Legal and regulatory disclosures may create financial or operational exposure; the outcome is not assumed."
    if priority == "Routine": return "Routine disclosure retained for completeness; no material impact is inferred from the title alone."
    return f"Classified as {category}; priority is a triage cue, not a prediction of share-price direction."


def _parse_nse_date(value: Any) -> datetime | None:
    if not value:
        return None
    s = str(value).strip()
    patterns = ["%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M", "%d-%b-%Y", "%d%m%Y%H%M%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]
    for p in patterns:
        try:
            result = datetime.strptime(s, p)
            return result.replace(tzinfo=IST)
        except ValueError:
            pass
    return None


def _base_price(ticker: str) -> float:
    values = {"TCS": 3120, "INFY": 1570, "HCLTECH": 1640, "HDFCBANK": 985, "ICICIBANK": 1410,
              "SBIN": 920, "RELIANCE": 1480, "NTPC": 365, "ITC": 405, "HINDUNILVR": 2450,
              "TATAMOTORS": 710, "M&M": 3350, "SUNPHARMA": 1780, "CIPLA": 1610, "LT": 3680,
              "BHARTIARTL": 1980, "TATASTEEL": 165, "ADANIENT": 2150}
    return values.get(ticker, 1000.0)


def _demo_price_history(ticker: str, days: int = 65) -> dict[str, Any]:
    company = COMPANY_BY_TICKER[ticker]
    rng = random.Random(sum(ord(ch) for ch in ticker))
    end = now_ist().date()
    dates = []
    d = end - timedelta(days=days * 1.55)
    while d <= end:
        if d.weekday() < 5:
            dates.append(d)
        d += timedelta(days=1)
    dates = dates[-days:]
    price = _base_price(ticker)
    closes, volumes = [], []
    for i, day in enumerate(dates):
        drift = 0.00015 + 0.0015 * math.sin(i / 8 + len(ticker))
        move = drift + rng.gauss(0, 0.0085)
        price *= (1 + move)
        closes.append(round(price, 2))
        volumes.append(int(700_000 + rng.random() * 2_500_000))
    prices = []
    for i, day in enumerate(dates):
        prev = closes[i - 1] if i else closes[i] / (1 + rng.gauss(0, 0.004))
        change = (closes[i] / prev - 1) * 100 if prev else 0
        prices.append({"date": day.isoformat(), "close": closes[i], "volume": volumes[i], "change_pct": round(change, 2)})
    avg_volume = mean(volumes[-21:-1]) if len(volumes) >= 21 else mean(volumes[:-1] or volumes)
    return {
        "ticker": ticker, "company": company["name"], "symbol": company["yahoo"],
        "prices": prices, "latest_close": closes[-1] if closes else None,
        "previous_close": closes[-2] if len(closes) > 1 else None,
        "day_change_pct": prices[-1]["change_pct"] if prices else 0,
        "volume": volumes[-1] if volumes else None,
        "avg_volume_20d": round(avg_volume), "volume_multiple": round(volumes[-1] / avg_volume, 2) if volumes and avg_volume else None,
        "source_mode": "demo", "source_name": "Illustrative generated price series",
        "source_note": "Synthetic price and volume values for interface testing only. Not actual market data.",
        "currency": "INR", "last_updated": now_ist().isoformat(),
    }


def fetch_price_history(ticker: str, period: str = "3mo") -> dict[str, Any]:
    ticker = ticker.upper().strip()
    if ticker not in COMPANY_BY_TICKER:
        raise ValueError(f"Ticker {ticker} is not in the initial demo registry")
    if OFFLINE:
        return _demo_price_history(ticker)
    cache_key = f"yahoo-{ticker}-{period}"
    cached = _cache_get(cache_key, 900)
    if cached is not None:
        return cached
    symbol = COMPANY_BY_TICKER[ticker]["yahoo"]
    try:
        response = requests.get(YAHOO_URL.format(symbol=symbol), params={"range": period, "interval": "1d", "events": "div,splits"}, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        response.raise_for_status()
        payload = response.json().get("chart", {})
        if payload.get("error") or not payload.get("result"):
            raise RuntimeError(str(payload.get("error") or "No price history returned"))
        chart = payload["result"][0]
        timestamps = chart.get("timestamp") or []
        quote = (chart.get("indicators", {}).get("quote") or [{}])[0]
        closes_raw = quote.get("close") or []
        volumes_raw = quote.get("volume") or []
        prices = []
        for ts, close, vol in zip(timestamps, closes_raw, volumes_raw):
            if close is None:
                continue
            dt = datetime.fromtimestamp(ts, IST).date().isoformat()
            prices.append({"date": dt, "close": round(float(close), 2), "volume": int(vol or 0), "change_pct": 0.0})
        for i in range(len(prices)):
            if i:
                p0, p1 = prices[i-1]["close"], prices[i]["close"]
                prices[i]["change_pct"] = round((p1 / p0 - 1) * 100, 2) if p0 else 0.0
        if len(prices) < 2:
            raise RuntimeError("Not enough valid daily observations")
        vol_window = [p["volume"] for p in prices[-21:-1] if p["volume"] > 0]
        avg_volume = mean(vol_window) if vol_window else None
        meta = chart.get("meta", {})
        item = {
            "ticker": ticker, "company": COMPANY_BY_TICKER[ticker]["name"], "symbol": symbol,
            "prices": prices, "latest_close": prices[-1]["close"], "previous_close": prices[-2]["close"],
            "day_change_pct": prices[-1]["change_pct"], "volume": prices[-1]["volume"],
            "avg_volume_20d": round(avg_volume) if avg_volume else None,
            "volume_multiple": round(prices[-1]["volume"] / avg_volume, 2) if avg_volume else None,
            "source_mode": "live", "source_name": "Yahoo Finance chart endpoint", "source_note": None,
            "currency": meta.get("currency", "INR"), "last_updated": now_ist().isoformat(),
        }
        _cache_set(cache_key, item)
        return item
    except Exception as exc:
        item = _demo_price_history(ticker)
        item["source_note"] = f"Yahoo data unavailable; showing labeled synthetic price history. Detail: {str(exc)[:120]}"
        return item


def portfolio_summary() -> dict[str, Any]:
    # Use stable values within a session; upstream source status is reported in each ticker view.
    cards = []
    live_count = 0
    for c in COMPANIES:
        p = fetch_price_history(c["ticker"], "3mo")
        live_count += p["source_mode"] == "live"
        cards.append({
            "ticker": c["ticker"], "name": c["name"], "sector": c["sector"],
            "price": p["latest_close"], "change_pct": p["day_change_pct"],
            "volume_multiple": p["volume_multiple"], "source_mode": p["source_mode"],
        })
    return {"companies": cards, "count": len(cards), "live_price_count": live_count,
            "source_mode": "live" if live_count == len(cards) else ("mixed" if live_count else "demo"),
            "updated_at": now_ist().isoformat()}


def evaluate_alert_rules(price_payload: dict[str, Any], rules: dict[str, Any]) -> list[dict[str, Any]]:
    ticker = price_payload["ticker"]
    out = []
    price_threshold = float(rules.get("price_move_pct", 3.0))
    vol_threshold = float(rules.get("volume_multiple", 2.0))
    change = float(price_payload.get("day_change_pct") or 0)
    volume_multiple = price_payload.get("volume_multiple")
    if abs(change) >= price_threshold:
        out.append({"type": "price_move", "ticker": ticker, "priority": "Medium", "value": change,
                    "threshold": price_threshold, "message": f"Daily close moved {change:+.2f}%, beyond your ±{price_threshold:g}% threshold.",
                    "source_mode": price_payload["source_mode"]})
    if volume_multiple is not None and float(volume_multiple) >= vol_threshold:
        out.append({"type": "volume_spike", "ticker": ticker, "priority": "Medium", "value": volume_multiple,
                    "threshold": vol_threshold, "message": f"Volume reached {float(volume_multiple):.2f}× the recent average, above your {vol_threshold:g}× threshold.",
                    "source_mode": price_payload["source_mode"]})
    return out

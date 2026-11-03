import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.companies import COMPANIES
from backend.data_gateway import classify_announcement, evaluate_alert_rules, _demo_price_history
from backend.research_engine import research


def test_portfolio_has_18_companies():
    assert len(COMPANIES) == 18
    assert len({company["ticker"] for company in COMPANIES}) == 18


def test_classification_results():
    category, priority = classify_announcement("Outcome of Board Meeting - Quarterly Financial Results")
    assert category == "results"
    assert priority == "High"


def test_demo_prices_labeled():
    result = _demo_price_history("TCS", 35)
    assert result["source_mode"] == "demo"
    assert "Synthetic" in result["source_note"]
    assert len(result["prices"]) >= 20


def test_research_uses_indexed_tcs_primary_source_excerpt():
    result = research("TCS", "What is the revenue trend?")
    assert result["status"] == "grounded"
    assert result["sources"]
    revenue = next(m for m in result["financial_metrics"] if m["metric"] == "Revenue from operations")
    assert revenue["latest_value"] == 267021
    assert revenue["yoy_change_pct"] == 4.6


def test_research_refuses_to_invent_for_uncovered_ticker():
    result = research("UNKNOWNXYZ", "What is the revenue trend?")
    assert result["status"] == "coverage_gap"
    assert result["sources"] == []
    assert "won't fill that gap" in result["executive_summary"]


def test_alert_rules_trigger_thresholds():
    prices = {"ticker":"TCS", "day_change_pct":-4.1, "volume_multiple":2.8, "source_mode":"demo"}
    result = evaluate_alert_rules(prices, {"price_move_pct":3, "volume_multiple":2})
    assert {a["type"] for a in result} == {"price_move", "volume_spike"}

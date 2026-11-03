from types import SimpleNamespace

from backend import research_engine


def test_gemini_call_uses_configured_compatibility_endpoint(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")
    monkeypatch.setenv(
        "GEMINI_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"executive_summary":"Grounded summary [S1]",'
                                '"key_findings":["Finding [S1]"],"risks":[], '
                                '"limitations":[],"used_sources":["S1"]}'
                            )
                        }
                    }
                ]
            }

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(research_engine.requests, "post", fake_post)

    evidence = [
        {
            "title": "TCS Annual Report",
            "period": "FY2026",
            "page": 10,
            "section": "Financial highlights",
            "text": "Revenue from operations increased.",
        }
    ]

    result = research_engine._call_llm("TCS", "Summarise revenue", evidence)

    assert result is not None
    assert result["executive_summary"] == "Grounded summary [S1]"
    assert captured["url"] == (
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    )
    assert captured["headers"]["Authorization"] == "Bearer test-gemini-key"
    assert captured["json"]["model"] == "gemini-3.8-flash"


def test_gemini_call_stays_disabled_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = research_engine._call_llm(
        "TCS",
        "Summarise revenue",
        [{"title": "Source", "text": "Evidence"}],
    )
    assert result is None

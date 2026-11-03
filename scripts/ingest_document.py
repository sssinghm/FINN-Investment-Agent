#!/usr/bin/env python3
"""Fetch and index one primary-source PDF or HTML document for FINN research.

Example:
  python scripts/ingest_document.py --ticker TCS --type annual_report --period FY2025 \
      --url 'https://example.com/annual-report.pdf' --title 'TCS Annual Report FY2025'

Only use public company / exchange source URLs. The script is intentionally explicit:
it does not silently ingest broker notes, news articles, or third-party research.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data" / "documents" / "index.json"
ALLOWED_TYPES = {"annual_report", "quarterly_results", "earnings_call", "investor_presentation", "exchange_filing"}


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}: self.skip += 1
        elif tag in {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "section"}: self.parts.append("\n")
    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self.skip: self.skip -= 1
        elif tag in {"p", "div", "tr", "li", "h1", "h2", "h3", "h4", "section"}: self.parts.append("\n")
    def handle_data(self, data):
        if not self.skip and data.strip(): self.parts.append(data.strip())
    def text(self):
        raw = "\n".join(self.parts)
        raw = re.sub(r"[\t\r ]+", " ", raw)
        raw = re.sub(r"\n\s*\n\s*\n+", "\n\n", raw)
        return raw.strip()


def split_chunks(text: str, max_chars: int = 1400, overlap: int = 180) -> list[dict]:
    paragraphs = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks = []; current = ""; page = None
    for para in paragraphs:
        if len(current) + len(para) + 1 <= max_chars:
            current = f"{current}\n{para}".strip()
            continue
        if current:
            chunks.append({"text": current, "page": page, "section": None})
        tail = current[-overlap:] if current else ""
        current = f"{tail}\n{para}".strip()
        while len(current) > max_chars:
            chunks.append({"text": current[:max_chars], "page": page, "section": None})
            current = current[max_chars-overlap:]
    if current:
        chunks.append({"text": current, "page": page, "section": None})
    return chunks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticker", required=True, help="NSE symbol, e.g. TCS")
    parser.add_argument("--type", required=True, dest="document_type", choices=sorted(ALLOWED_TYPES))
    parser.add_argument("--period", default="", help="Financial period, e.g. FY2025 or Q1 FY2026")
    parser.add_argument("--url", required=True, help="Public primary-source PDF or HTML URL")
    parser.add_argument("--title", default="", help="Readable document title")
    parser.add_argument("--source-name", default="Company / exchange primary source")
    args = parser.parse_args()

    parsed = urlparse(args.url)
    if parsed.scheme != "https" or not parsed.hostname:
        parser.error("Source URL must be an HTTPS URL")
    if parsed.hostname in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        parser.error("Local URLs are not accepted")
    try:
        response = requests.get(args.url, headers={"User-Agent":"FINN-research-prototype/0.1 (manual public document ingestion)"}, timeout=25)
        response.raise_for_status()
        raw = response.content
    except Exception as exc:
        print(f"Download failed: {exc}", file=sys.stderr); return 2

    content_type = response.headers.get("content-type", "").lower()
    pages = []
    if raw[:4] == b"%PDF" or "application/pdf" in content_type or parsed.path.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(raw))
            for index, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                if text.strip(): pages.append((index, text))
        except Exception as exc:
            print(f"Could not extract PDF text: {exc}", file=sys.stderr); return 3
    else:
        try:
            extractor = TextExtractor(); extractor.feed(raw.decode("utf-8", errors="replace"))
            pages = [(None, extractor.text())]
        except Exception as exc:
            print(f"Could not extract HTML text: {exc}", file=sys.stderr); return 3

    all_chunks = []
    for page_no, text in pages:
        for chunk in split_chunks(text):
            chunk["page"] = page_no
            all_chunks.append(chunk)
    all_chunks = [c for c in all_chunks if len(c["text"].strip()) > 80]
    if not all_chunks:
        print("No readable text found. Scanned PDFs may need OCR before ingestion.", file=sys.stderr); return 4

    doc_id = hashlib.sha1(f"{args.ticker.upper()}|{args.document_type}|{args.period}|{args.url}".encode()).hexdigest()[:14]
    record = {"id": doc_id, "ticker": re.sub(r"[^A-Z0-9&._-]", "", args.ticker.upper()),
              "document_type": args.document_type, "period": args.period or None,
              "title": args.title or parsed.path.rsplit("/", 1)[-1] or args.ticker.upper(),
              "source_url": args.url, "source_name": args.source_name,
              "ingested_at": datetime.now(timezone.utc).isoformat(), "chunks": all_chunks}
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    try:
        docs = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else []
        if not isinstance(docs, list): docs = []
    except (json.JSONDecodeError, OSError): docs = []
    docs = [doc for doc in docs if doc.get("id") != doc_id]
    docs.append(record)
    INDEX.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Indexed {len(all_chunks)} text chunks for {record['ticker']} — {record['title']}")
    print(f"Source: {args.url}")
    print("Check the extracted passages and source period before relying on any analysis.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

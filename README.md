# FINN — Financial Investment Agent

**A mobile-first financial investment intelligence prototype built for the ENAM AI Engineer Build Challenge.**

**Live application:** https://finn-investment-agent-ssjv.onrender.com
**GitHub repository:** https://github.com/sssinghm/FINN-Investment-Agent

## 1. Overview

FINN is a mobile-first investment intelligence agent designed around two complementary workflows:

- **Push — Proactive intelligence:** Prioritized corporate-announcement briefings and configurable end-of-day price and volume alerts.
- **Pull — On-demand research:** Company research using retrieved passages from indexed primary-source financial documents, with Gemini-powered synthesis and source references.

The central product idea is to help investors filter information, identify what deserves attention, and investigate important developments without navigating multiple disconnected sources.

## 2. Core Features

### Push — Briefing and alerts

- Prioritized corporate-announcement feed.
- Configurable price-movement thresholds.
- Unusual-volume detection against recent trading history.
- Source context and links for individual signals.
- Company-level navigation from signals to deeper research.

Default demonstration thresholds:
- Daily price movement: ±3%.
- Unusual volume: 2× the previous 20-session average.
- Announcement window: 24 hours.

Alert calculations use end-of-day data, not intraday monitoring.

### Pull — Financial research

- On-demand company research.
- Retrieval from indexed primary-source documents.
- Source-linked findings and evidence excerpts.
- Gemini-powered research synthesis.
- Explicit coverage-gap handling when evidence is unavailable.
- Research history and company coverage information.

Currently indexed research coverage:
- TCS
- Infosys (INFY)
- Reliance Industries (RELIANCE)
- HDFC Bank (HDFCBANK)

The document collection includes FY2025–26 annual-report material. Indexed excerpts are not equivalent to complete financial-statement extraction.

## 3. Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | Responsive HTML, CSS and JavaScript |
| Research retrieval | Primary-source document indexing and retrieval |
| LLM synthesis | Google Gemini API |
| Model | gemini-3.6-flash |
| API integration | Gemini OpenAI-compatible endpoint |
| Document extraction | PDF/HTML ingestion |
| Local application data | Lightweight local storage |
| Testing | Pytest |
| Deployment | Render |
| Source control | Git and GitHub |

## 4. Architecture

FINN follows a lightweight application architecture:

1. Public data adapters retrieve end-of-day prices and corporate announcements.
2. The backend classifies, prioritizes and prepares briefing signals.
3. The document-ingestion pipeline extracts text from primary-source PDFs and HTML documents.
4. Extracted content is split into indexed passages with document metadata and source URLs.
5. The research engine retrieves relevant passages for a user's query.
6. Gemini synthesizes an answer using the retrieved evidence.
7. FINN displays findings, source references and evidence limitations.

When Gemini is unavailable, the application can fall back to deterministic analysis rather than treating an unsuccessful model request as a successful AI response.

## 5. AI Model Configuration

FINN uses Google's Gemini API through its OpenAI-compatible Chat Completions interface.

Environment configuration:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.6-flash
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
FINN_OFFLINE_MODE=0
```

API credentials are supplied through environment variables and must never be committed to the repository.

## 6. Data Sources and Limitations

- **Price data:** Best-effort public Yahoo Finance chart endpoint.
- **Corporate announcements:** Best-effort public NSE announcement endpoint.
- **Company fundamentals:** Company annual reports and other primary-source documents.
- **Research synthesis:** Gemini using retrieved indexed evidence.

Important limitations:

- Public price and exchange endpoints are not guaranteed APIs.
- When upstream sources are unavailable, the application can display clearly labelled illustrative or DEMO records.
- The application is designed around end-of-day data, not real-time intraday monitoring.
- The indexed annual reports are extracted into passages; coverage and extraction accuracy require validation against the original documents.
- Citation relevance and financial figures should be checked against their source documents before relying on them.
- Free-tier hosting uses temporary local storage; saved application state may not persist across restarts or redeployments.
- The prototype does not execute trades or provide investment advice.

## 7. Local Setup

Requirements:
- Python 3.10 or later.
- Internet connection for external data sources, document ingestion and Gemini synthesis.

Clone the repository:

```bash
git clone https://github.com/sssinghm/FINN-Investment-Agent.git
cd FINN-Investment-Agent
```

Create and activate the virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Create the environment file:

```powershell
Copy-Item .env.example .env
```

Add your Gemini API configuration to `.env`.

Start FINN:

```bash
uvicorn backend.app:app --reload
```

Open:

- Application: http://127.0.0.1:8000
- API documentation: http://127.0.0.1:8000/docs
- Health endpoint: http://127.0.0.1:8000/api/health

## 8. Document Ingestion

FINN supports ingestion of publicly accessible primary-source documents.

Example:

```bash
python scripts/ingest_document.py \
  --ticker INFY \
  --type annual_report \
  --period FY2026 \
  --url "PUBLIC_DOCUMENT_URL" \
  --title "Infosys Annual Report FY2026" \
  --source-name "Infosys Investor Relations"
```

Supported document types:

- annual_report
- earnings_call
- exchange_filing
- investor_presentation
- quarterly_results

The ingestion process extracts readable PDF or HTML content, divides it into passages and stores document metadata and extracted content in `data/documents/index.json`.

Scanned PDFs without extractable text are not automatically OCR-processed.

## 9. Important API Endpoints

| Endpoint | Purpose |
|---|---|
| GET `/api/health` | Application health |
| GET `/api/companies` | Company list |
| GET `/api/portfolio` | Portfolio information |
| GET `/api/feed?days=1` | Prioritized briefing |
| GET `/api/prices/{ticker}` | Price and volume history |
| GET `/api/alerts/rules` | Alert configuration |
| PUT `/api/alerts/rules` | Update alert configuration |
| GET `/api/alerts/preview` | Alert preview |
| POST `/api/research` | On-demand financial research |
| GET `/api/research/coverage` | Indexed document coverage |
| GET `/api/research/history` | Research history |

## 10. Testing

Run the automated test suite:

```bash
python -m pytest -q
```

Tests cover application functionality, research configuration and related application logic.

## 11. Deployment

The application is deployed as a Render Web Service connected to the GitHub repository.

The Gemini API key and other deployment-specific settings are configured through Render environment variables rather than stored in source code.

## 12. Future Improvements

- More extensive extraction and validation of quarterly financial statements.
- Stronger citation-to-claim validation.
- Wider coverage of company annual reports and earnings-call transcripts.
- Scheduled data refresh with reliable source monitoring.
- Persistent storage for user preferences and research history.
- Evaluation datasets for financial extraction and research-answer quality.

## Disclaimer

FINN is a prototype developed for an investment-intelligence workflow challenge. It is not investment advice, does not execute trades and does not guarantee the completeness or accuracy of retrieved financial information. Users should verify material findings directly against official company and exchange disclosures.
# Submission covering note — FINN

**Subject:** ENAM - IIT screening - 2027

Dear ENAM Team,

I built **FINN**, a mobile-first investment-intelligence prototype organized around two connected workflows: a prioritized Push briefing for corporate announcements and end-of-day price/volume signals, and a Pull research view grounded in indexed primary-source documents.

The main product decision was to make the briefing an attention filter rather than an unranked list of filings. Each signal exposes its category, priority and source context, and a company alert can lead into a deeper research question. The research engine preserves source provenance and reports a coverage gap when relevant evidence is not indexed instead of filling the gap with unsupported company facts.

For the prototype, I used a small FastAPI backend with a responsive frontend, a lightweight local store, and a retrieval pipeline. Price and exchange announcement connectors are best-effort because the public endpoints are not guaranteed APIs. When a source is unavailable, the UI labels illustrative fallback records rather than representing them as real market events. I preloaded a curated set of metrics from TCS's official FY2025–26 annual-report performance-trend table to demonstrate source-linked research on first launch; this is an excerpt pack, not a full financial-statement extraction.

I deliberately left out live intraday monitoring, automated trading, broad automated ingestion of every company document, and production authentication. The next steps would be validating results-table extraction across a wider company set, adding scheduled refresh after upstream reliability is established, and building an evaluation set for extraction accuracy and citation quality.

- **Prototype:** [add deployed URL]
- **Repository:** [add GitHub repository URL]
- **AI build history:** [attach/export the relevant ChatGPT or coding-agent build conversation]

Thank you for reviewing the prototype.

Best regards,
[Your Name]

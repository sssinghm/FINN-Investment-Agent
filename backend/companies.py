"""Curated mock portfolio. Symbols map to NSE symbols and Yahoo Finance tickers."""

COMPANIES = [
    {"ticker": "TCS", "yahoo": "TCS.NS", "name": "Tata Consultancy Services", "sector": "IT Services", "exchange": "NSE", "market_cap_band": "Large", "description": "Global IT services, consulting and business solutions."},
    {"ticker": "INFY", "yahoo": "INFY.NS", "name": "Infosys", "sector": "IT Services", "exchange": "NSE", "market_cap_band": "Large", "description": "Digital services and consulting for enterprise clients."},
    {"ticker": "HCLTECH", "yahoo": "HCLTECH.NS", "name": "HCL Technologies", "sector": "IT Services", "exchange": "NSE", "market_cap_band": "Large", "description": "Technology services, engineering and software."},
    {"ticker": "HDFCBANK", "yahoo": "HDFCBANK.NS", "name": "HDFC Bank", "sector": "Banking", "exchange": "NSE", "market_cap_band": "Large", "description": "Private-sector bank serving retail and corporate customers."},
    {"ticker": "ICICIBANK", "yahoo": "ICICIBANK.NS", "name": "ICICI Bank", "sector": "Banking", "exchange": "NSE", "market_cap_band": "Large", "description": "Private-sector banking and financial services."},
    {"ticker": "SBIN", "yahoo": "SBIN.NS", "name": "State Bank of India", "sector": "Banking", "exchange": "NSE", "market_cap_band": "Large", "description": "Public-sector bank with retail, corporate and treasury businesses."},
    {"ticker": "RELIANCE", "yahoo": "RELIANCE.NS", "name": "Reliance Industries", "sector": "Energy & Retail", "exchange": "NSE", "market_cap_band": "Large", "description": "Diversified group spanning energy, retail, telecom and digital services."},
    {"ticker": "NTPC", "yahoo": "NTPC.NS", "name": "NTPC", "sector": "Utilities", "exchange": "NSE", "market_cap_band": "Large", "description": "Power generation and energy transition investments."},
    {"ticker": "ITC", "yahoo": "ITC.NS", "name": "ITC", "sector": "Consumer Staples", "exchange": "NSE", "market_cap_band": "Large", "description": "Consumer products, paperboards, packaging and hospitality."},
    {"ticker": "HINDUNILVR", "yahoo": "HINDUNILVR.NS", "name": "Hindustan Unilever", "sector": "Consumer Staples", "exchange": "NSE", "market_cap_band": "Large", "description": "Consumer goods across home care, personal care and foods."},
    {"ticker": "TATAMOTORS", "yahoo": "TATAMOTORS.NS", "name": "Tata Motors", "sector": "Automotive", "exchange": "NSE", "market_cap_band": "Large", "description": "Passenger vehicles, commercial vehicles and automotive services."},
    {"ticker": "M&M", "yahoo": "M&M.NS", "name": "Mahindra & Mahindra", "sector": "Automotive", "exchange": "NSE", "market_cap_band": "Large", "description": "SUVs, tractors and mobility-related businesses."},
    {"ticker": "SUNPHARMA", "yahoo": "SUNPHARMA.NS", "name": "Sun Pharmaceutical", "sector": "Pharmaceuticals", "exchange": "NSE", "market_cap_band": "Large", "description": "Specialty and generic medicines."},
    {"ticker": "CIPLA", "yahoo": "CIPLA.NS", "name": "Cipla", "sector": "Pharmaceuticals", "exchange": "NSE", "market_cap_band": "Large", "description": "Pharmaceutical products with a focus on respiratory and chronic therapies."},
    {"ticker": "LT", "yahoo": "LT.NS", "name": "Larsen & Toubro", "sector": "Industrials", "exchange": "NSE", "market_cap_band": "Large", "description": "Engineering, construction, technology and manufacturing."},
    {"ticker": "BHARTIARTL", "yahoo": "BHARTIARTL.NS", "name": "Bharti Airtel", "sector": "Telecom", "exchange": "NSE", "market_cap_band": "Large", "description": "Telecommunications and digital connectivity services."},
    {"ticker": "TATASTEEL", "yahoo": "TATASTEEL.NS", "name": "Tata Steel", "sector": "Metals", "exchange": "NSE", "market_cap_band": "Large", "description": "Steel production and downstream steel products."},
    {"ticker": "ADANIENT", "yahoo": "ADANIENT.NS", "name": "Adani Enterprises", "sector": "Diversified", "exchange": "NSE", "market_cap_band": "Large", "description": "Incubation platform with interests across infrastructure-linked businesses."},
]

COMPANY_BY_TICKER = {c["ticker"]: c for c in COMPANIES}

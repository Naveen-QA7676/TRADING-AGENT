"""
Sector knowledge: rotation patterns, key indicators, macro drivers,
and which stocks to focus on in each sector during different regimes.
"""

SECTOR_MAP = {
    "BANKING": {
        "indices": ["NIFTY BANK", "NIFTY FINANCIAL SERVICES", "NIFTY PSU BANK"],
        "key_stocks": ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN", "BANDHANBNK"],
        "key_indicators": ["RBI rate decision", "NIM trends", "NPA data", "CASA ratio", "credit growth"],
        "macro_drivers": ["interest rates", "inflation", "RBI policy", "credit cycle"],
        "sector_etf": "BANKBEES",
        "typically_leads": ["market rally"],
        "correlation": "High positive with market",
    },
    "IT": {
        "indices": ["NIFTY IT"],
        "key_stocks": ["TCS", "INFY", "HCLTECH", "WIPRO", "TECHM", "MPHASIS"],
        "key_indicators": ["US tech sector", "USD/INR", "deal wins", "attrition", "quarterly guidance"],
        "macro_drivers": ["USD strength", "US tech spending", "recession risk", "AI adoption"],
        "typically_leads": ["USD weakness benefits"],
        "correlation": "High positive with US tech (NASDAQ)",
    },
    "ENERGY": {
        "indices": ["NIFTY ENERGY", "NIFTY OIL GAS"],
        "key_stocks": ["RELIANCE", "ONGC", "BPCL", "IOC", "GAIL", "HINDPETRO"],
        "key_indicators": ["crude oil price", "refining margins", "gas prices", "government subsidy"],
        "macro_drivers": ["crude oil (WTI/Brent)", "OPEC decisions", "geopolitics", "renewable transition"],
        "correlation": "Positive with crude oil prices",
    },
    "FMCG": {
        "indices": ["NIFTY FMCG"],
        "key_stocks": ["HINDUNILVR", "ITC", "NESTLEIND", "DABUR", "MARICO", "BRITANNIA"],
        "key_indicators": ["rural demand", "volume growth", "pricing power", "raw material costs"],
        "macro_drivers": ["monsoon", "rural wages", "inflation", "urban discretionary spending"],
        "typically_leads": ["defensive stocks during bearish markets"],
        "correlation": "Negative with market (defensive)",
    },
    "AUTO": {
        "indices": ["NIFTY AUTO"],
        "key_stocks": ["MARUTI", "M&M", "TATAMOTORS", "BAJAJ-AUTO", "HEROMOTOCO", "EICHERMOT"],
        "key_indicators": ["monthly sales data", "EV adoption", "commodity costs", "fuel prices"],
        "macro_drivers": ["commodity prices (steel, aluminium)", "interest rates", "EV transition", "monsoon"],
        "typically_leads": ["economic recovery cycles"],
        "correlation": "Moderate positive with market",
    },
    "PHARMA": {
        "indices": ["NIFTY PHARMA"],
        "key_stocks": ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "AUROPHARMA", "LUPIN"],
        "key_indicators": ["USFDA approvals", "API prices", "domestic prescription volume", "export data"],
        "macro_drivers": ["USD/INR", "USFDA policy", "patent cliffs", "healthcare spending"],
        "typically_leads": ["defensive period during market stress"],
        "correlation": "Low/negative with cyclicals (defensive)",
    },
    "METALS": {
        "indices": ["NIFTY METAL"],
        "key_stocks": ["TATASTEEL", "JSWSTEEL", "HINDALCO", "VEDL", "NATIONALUM", "SAIL"],
        "key_indicators": ["LME prices", "Chinese demand", "domestic steel consumption", "coal prices"],
        "macro_drivers": ["global commodity cycle", "China economy", "infrastructure spending", "US dollar"],
        "typically_leads": ["commodity bull cycles"],
        "correlation": "High positive with global commodity prices",
    },
    "INFRA": {
        "indices": ["NIFTY INFRA"],
        "key_stocks": ["LT", "ADANIPORTS", "GMRINFRA", "IRB", "NCC", "KNRCON"],
        "key_indicators": ["government capex", "order book", "execution pace", "debt levels"],
        "macro_drivers": ["government spending", "infrastructure budget", "interest rates"],
        "typically_leads": ["budget and government spending announcements"],
        "correlation": "Moderate positive with market",
    },
    "REALTY": {
        "indices": ["NIFTY REALTY"],
        "key_stocks": ["DLF", "PHOENIXLTD", "OBEROIRLTY", "PRESTIGE", "GODREJPROP", "LODHA"],
        "key_indicators": ["RBI rates", "housing demand", "unsold inventory", "new launches"],
        "macro_drivers": ["interest rates (critical)", "urban income growth", "migration to cities"],
        "typically_leads": ["rate cut cycles"],
        "correlation": "Strongly negative with interest rates",
    },
    "CONSUMER_DISC": {
        "indices": ["NIFTY CONSUMER DURABLES"],
        "key_stocks": ["ASIANPAINT", "TITAN", "HAVELLS", "VOLTAS", "VGUARD", "CROMPTON"],
        "key_indicators": ["urban consumption", "real estate demand", "summer season (AC/fan)"],
        "macro_drivers": ["urban incomes", "GST", "raw material inflation"],
        "typically_leads": ["urban consumption boom"],
        "correlation": "Moderate positive with market",
    },
}

SECTOR_ROTATION_CYCLE = {
    "EARLY_EXPANSION": ["BANKING", "AUTO", "CONSUMER_DISC"],
    "LATE_EXPANSION": ["ENERGY", "METALS", "INFRA"],
    "EARLY_CONTRACTION": ["FMCG", "PHARMA"],
    "LATE_CONTRACTION": ["BANKING", "IT"],
}

NIFTY_STOCK_WEIGHTS = {
    "RELIANCE": 9.8,
    "HDFC BANK": 12.3,
    "ICICI BANK": 8.2,
    "INFOSYS": 6.1,
    "TCS": 4.1,
    "AXIS BANK": 2.8,
    "KOTAK BANK": 3.5,
    "LT": 3.2,
    "SBI": 2.9,
    "M&M": 1.8,
}

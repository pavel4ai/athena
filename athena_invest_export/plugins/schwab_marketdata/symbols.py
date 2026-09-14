"""Schwab symbol formatting helpers.

The Streamer uses Schwab-standard symbol formats that differ by asset class.
These helpers build/validate them so callers never hand-assemble the strings.

Formats (from the Streamer spec):
  Equity/ETF/Forex : plain symbol ("AAPL", "SPY", "EUR/USD")
  Option           : RRRRRRYYMMDDsWWWWWddd
                     6-char space-padded root, YYMMDD expiry, C/P, 5-digit
                     whole strike, 3-digit decimal strike.
                     e.g. "AAPL  251219C00200000"
  Future           : '/' + root + month_code + 2-digit year   e.g. "/ESZ25"
  Future Option    : '.' + '/' + root + month + year + C/P + strike
                     e.g. "./OZCZ23C565"
"""

from __future__ import annotations

# CME month codes (shared by futures and futures options)
FUTURES_MONTH_CODES = {
    1: "F", 2: "G", 3: "H", 4: "J", 5: "K", 6: "M",
    7: "N", 8: "Q", 9: "U", 10: "V", 11: "X", 12: "Z",
}

COMMON_FUTURES_ROOTS = {
    "ES": "E-Mini S&P 500", "NQ": "E-Mini Nasdaq 100",
    "CL": "Light Sweet Crude Oil", "GC": "Gold", "HO": "Heating Oil",
    "BZ": "Brent Crude Oil", "YM": "Mini Dow Jones Industrial Average",
}


def format_option_symbol(root: str, year: int, month: int, day: int,
                         side: str, strike: float) -> str:
    """Build a Schwab option symbol: RRRRRRYYMMDDsWWWWWddd.

    side: 'C' or 'P'. strike e.g. 200.0 -> 00200000 (5 whole + 3 decimal).
    """
    side = side.upper()
    if side not in ("C", "P"):
        raise ValueError("side must be 'C' or 'P'")
    root6 = f"{root.upper():<6}"  # left-justified, space-padded to 6
    yy = year % 100
    whole = int(strike)
    decimal = round((strike - whole) * 1000)
    return f"{root6}{yy:02d}{month:02d}{day:02d}{side}{whole:05d}{decimal:03d}"


def format_futures_symbol(root: str, month: int, year: int) -> str:
    """Build a Schwab future symbol: /<root><monthcode><yy>. e.g. /ESZ25."""
    if month not in FUTURES_MONTH_CODES:
        raise ValueError(f"month must be 1-12, got {month}")
    return f"/{root.upper()}{FUTURES_MONTH_CODES[month]}{year % 100:02d}"


def format_futures_option_symbol(root: str, month: int, year: int,
                                 side: str, strike: float) -> str:
    """Build a Schwab futures-option symbol: ./<root><month><yy><CP><strike>."""
    side = side.upper()
    if side not in ("C", "P"):
        raise ValueError("side must be 'C' or 'P'")
    if month not in FUTURES_MONTH_CODES:
        raise ValueError(f"month must be 1-12, got {month}")
    strike_str = f"{int(strike)}" if strike == int(strike) else f"{strike}"
    return f"./{root.upper()}{FUTURES_MONTH_CODES[month]}{year % 100:02d}{side}{strike_str}"


def service_for_symbol(symbol: str) -> str:
    """Best-effort guess of the Level 1 service for a raw symbol string."""
    s = symbol.strip().upper()
    if s.startswith("./"):
        return "LEVELONE_FUTURES_OPTIONS"
    if s.startswith("/"):
        return "LEVELONE_FUTURES"
    if "/" in s:  # currency pair like EUR/USD
        return "LEVELONE_FOREX"
    if len(s) > 12 and (s[-9] in ("C", "P")):  # option symbol pattern
        return "LEVELONE_OPTIONS"
    return "LEVELONE_EQUITIES"

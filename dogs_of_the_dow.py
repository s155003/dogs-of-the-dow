"""
===============================================================
 Dogs of the Dow - Alpaca Paper Trading Bot
===============================================================
 Strategy:
 - Each year, buy the 10 highest dividend-yield stocks
 in the Dow Jones Industrial Average
 - Equal weight across all 10 positions
 - Rebalance once per year (first 5 days of January)
 - Sell any holdings that drop out of the top 10

 Requirements:
 pip install alpaca-trade-api yfinance pandas numpy

 Setup:
 Set the following environment variables (or use a .env file):
 ALPACA_API_KEY - your Alpaca paper API key
 ALPACA_SECRET_KEY - your Alpaca paper secret key

 Paper Trading Base URL:
 https://paper-api.alpaca.markets

 Usage:
 python dogs_of_the_dow.py

 On first run, the bot will immediately execute a rebalance
 so you can test it right away without waiting for January.
===============================================================
"""

import os
import time
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime
from alpaca_trade_api.rest import REST


# ---------------------------------------------------------------
# CONFIG - Edit these to match your paper account & preferences
# ---------------------------------------------------------------

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = "https://paper-api.alpaca.markets"

# Total USD to deploy across the 10 Dogs (match your paper account cash)
TOTAL_PORTFOLIO_VALUE = 10_000 # USD

# How often the bot wakes up to check if it's rebalance time (seconds)
CHECK_INTERVAL = 60 * 60 * 24 # once per day

# Rebalance during the first N days of January each year
REBALANCE_MONTH = 1
REBALANCE_DAY_WINDOW = 5 # Jan 1 - Jan 5

# Set to True to force a rebalance every time the bot runs (useful for testing)
FORCE_REBALANCE_ON_STARTUP = True


# ---------------------------------------------------------------
# DOW 30 COMPONENTS (update this list if the index changes)
# ---------------------------------------------------------------

DOW_30 = [
 "AAPL", "AMGN", "AXP", "BA", "CAT",
 "CRM", "CSCO", "CVX", "DIS", "DOW",
 "GS", "HD", "HON", "IBM", "INTC",
 "JNJ", "JPM", "KO", "MCD", "MMM",
 "MRK", "MSFT", "NKE", "PG", "TRV",
 "UNH", "V", "VZ", "WBA", "WMT",
]


# ---------------------------------------------------------------
# ALPACA CLIENT
# ---------------------------------------------------------------

api = REST(API_KEY, SECRET_KEY, BASE_URL)


# ---------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------

def log(msg: str):
 """Timestamped print."""
 print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def get_dividend_yields(tickers: list) -> dict:
 """Return {ticker: dividend_yield} for each ticker via yfinance."""
 yields = {}
 for ticker in tickers:
 try:
 info = yf.Ticker(ticker).info
 div_yield = info.get("dividendYield") or 0.0
 yields[ticker] = div_yield
 except Exception as exc:
 log(f"  Could not fetch yield for {ticker}: {exc}")
 yields[ticker] = 0.0
 return yields


def get_dogs(n: int = 10) -> list:
 """Return the top-n highest dividend yield Dow stocks."""
 log("Fetching dividend yields for all 30 Dow components...")
 yields = get_dividend_yields(DOW_30)

 ranked = sorted(yields.items(), key=lambda x: x[1], reverse=True)

 log(f"\n{'Rank':<6}{'Ticker':<8}{'Yield':>8}")
 log("-" * 24)
 for i, (ticker, y) in enumerate(ranked, 1):
 marker = " <- Dog" if i <= n else ""
 log(f" {i:<4}{ticker:<8}{y:>7.2%}{marker}")

 dogs = [t for t, _ in ranked[:n]]
 log(f"\n Selected Dogs: {dogs}\n")
 return dogs


def get_latest_price(ticker: str) -> float | None:
 """Fetch the most recent closing price for a ticker."""
 try:
 df = yf.download(ticker, period="2d", interval="1d",
 progress=False, auto_adjust=True)
 if df.empty:
 return None
 return float(df["Close"].iloc[-1])
 except Exception as exc:
 log(f"  Price fetch failed for {ticker}: {exc}")
 return None


def get_all_positions() -> dict:
 """Return {symbol: qty} for all current Alpaca positions."""
 try:
 positions = api.list_positions()
 return {p.symbol: int(p.qty) for p in positions}
 except Exception as exc:
 log(f" Could not fetch positions: {exc}")
 return {}


def get_account_cash() -> float:
 """Return available buying power from the Alpaca account."""
 try:
 account = api.get_account()
 return float(account.buying_power)
 except Exception as exc:
 log(f" Could not fetch account info: {exc}")
 return 0.0


def place_order(symbol: str, qty: int, side: str):
 """Submit a market order. side = 'buy' | 'sell'."""
 if qty < 1:
 log(f"  Skipping {symbol} - computed qty < 1")
 return
 try:
 api.submit_order(
 symbol=symbol,
 qty=qty,
 side=side,
 type="market",
 time_in_force="gtc",
 )
 action = "Bought" if side == "buy" else "Sold"
 log(f" {action} {qty} share(s) of {symbol}")
 except Exception as exc:
 log(f" Order failed for {symbol} ({side} {qty}): {exc}")


# ---------------------------------------------------------------
# REBALANCE LOGIC
# ---------------------------------------------------------------

def rebalance():
 """
 Core Dogs of the Dow rebalance:
 1. Identify the 10 Dogs (highest yield Dow stocks)
 2. Sell any current holdings NOT in the Dogs list
 3. Buy / adjust Dogs to equal-weight target
 """
 log("=" * 60)
 log(" Starting Dogs of the Dow Rebalance")
 log("=" * 60)

 dogs = get_dogs(n=10)
 target_per_stock = TOTAL_PORTFOLIO_VALUE / len(dogs)
 current_positions = get_all_positions()

 # -- Step 1: Liquidate non-Dog holdings ----------------------
 log(" Selling positions NOT in this year's Dogs list...")
 sold_any = False
 for symbol, qty in current_positions.items():
 if symbol not in dogs:
 log(f" {symbol} is no longer a Dog - selling {qty} share(s)")
 place_order(symbol, qty, "sell")
 time.sleep(1)
 sold_any = True
 if not sold_any:
 log(" (No non-Dog positions to sell)")

 # Brief pause to let sell orders settle in paper trading
 if sold_any:
 log(" Waiting 5 s for sell orders to process...")
 time.sleep(5)

 # Refresh positions after sells
 current_positions = get_all_positions()

 # -- Step 2: Buy / trim each Dog to target weight -------------
 log("\n Adjusting Dogs positions to equal-weight targets...")
 for ticker in dogs:
 price = get_latest_price(ticker)
 if price is None:
 log(f"  No price for {ticker} - skipping")
 continue

 target_shares = int(target_per_stock // price)
 current_qty = current_positions.get(ticker, 0)
 diff = target_shares - current_qty

 log(f" {ticker:<6} price=${price:>8.2f} "
 f"target={target_shares} current={current_qty} diff={diff:+d}")

 if diff > 0:
 place_order(ticker, diff, "buy")
 elif diff < 0:
 place_order(ticker, abs(diff), "sell")
 else:
 log(f" Already at target - no action needed")

 time.sleep(1) # avoid rate limits

 log("\n Rebalance complete!")
 log(f" Portfolio target: ${TOTAL_PORTFOLIO_VALUE:,.2f} "
 f"| ~${target_per_stock:,.2f} per stock")
 log("=" * 60 + "\n")


# ---------------------------------------------------------------
# REBALANCE SCHEDULE
# ---------------------------------------------------------------

def is_rebalance_day() -> bool:
 """True during the first REBALANCE_DAY_WINDOW days of January."""
 today = datetime.now()
 return (
 today.month == REBALANCE_MONTH
 and 1 <= today.day <= REBALANCE_DAY_WINDOW
 )


# ---------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------

def main():
 log(" Dogs of the Dow - Alpaca Paper Trading Bot")
 log(f" Portfolio size : ${TOTAL_PORTFOLIO_VALUE:,.2f}")
 log(f" Rebalance window: Jan 1-{REBALANCE_DAY_WINDOW}")
 log(f" Force on startup: {FORCE_REBALANCE_ON_STARTUP}\n")

 # Validate API connection
 try:
 account = api.get_account()
 log(f" Connected to Alpaca - Account status: {account.status}")
 log(f" Buying power: ${float(account.buying_power):,.2f}\n")
 except Exception as exc:
 log(f" Cannot connect to Alpaca: {exc}")
 log(" Check your API_KEY, SECRET_KEY, and BASE_URL.")
 return

 last_rebalance_year = None

 # Immediate rebalance on startup for easy testing
 if FORCE_REBALANCE_ON_STARTUP:
 log(" FORCE_REBALANCE_ON_STARTUP is True - rebalancing now...")
 rebalance()
 last_rebalance_year = datetime.now().year

 # Main scheduling loop
 while True:
 current_year = datetime.now().year

 if is_rebalance_day() and last_rebalance_year != current_year:
 log(" It's rebalance season! Starting annual rebalance...")
 rebalance()
 last_rebalance_year = current_year
 else:
 next_year = current_year if is_rebalance_day() else current_year + 1
 log(f" Holding. Next scheduled rebalance: Jan 1, {next_year}")

 time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
 main()

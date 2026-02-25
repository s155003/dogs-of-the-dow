Dogs of the Dow - Alpaca Paper Trading Bot
An automated Python trading bot that implements the classic Dogs of the Dow investment strategy, connected to Alpaca Markets paper trading API for risk-free backtesting and simulation.

What is Dogs of the Dow?
Dogs of the Dow is a simple, time-tested investment strategy first popularized by Michael O'Higgins in 1991. The rules are straightforward:

At the start of each year, look at all 30 stocks in the Dow Jones Industrial Average
Rank them by dividend yield (highest to lowest)
Buy the top 10 — these are the "Dogs"
Hold them in equal weight for the full year
Rebalance on January 1st and repeat

The theory behind it: high dividend yields in blue-chip companies often signal that the stock is temporarily undervalued relative to its peers. Since Dow components are all large, established companies, they are unlikely to collapse — making a recovery more probable than not.

Features

Automatically fetches live dividend yields for all 30 Dow components via Yahoo Finance
Ranks and selects the top 10 Dogs each rebalance cycle
Sells any holdings that fall out of the top 10
Buys and trims positions to maintain equal weighting
Connects to Alpaca Markets paper trading for safe, real-market simulation
Configurable portfolio size, rebalance window, and startup behavior
Clean timestamped logging throughout

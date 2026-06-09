# Nifty-200 Swing Trading Research Framework

Backtesting framework for 20 swing-trading strategies on Indian equities (Nifty 200, NSE cash, daily timeframe). Includes realistic transaction costs, an automatic rejection filter, Monte Carlo robustness, equity curves, trade logs, and a ranked leaderboard.

> **This is research software, not financial advice. It does not prove any strategy works.** On random data it correctly rejects everything — edge must be earned on real data.

---

## ⚠️ Read this first — honest limitations

1. **Survivorship bias is NOT solved with the default (free) data.** `yfinance` returns only *currently listed* stocks — no delisted names, no point-in-time index membership. Results will look better than reality. Fix it by swapping the `load_data()` function for a point-in-time data vendor.
2. The seed universe is ~30 current Nifty names, not the full 200. Extend the `NIFTY` list in `framework.py`.
3. Cross-sectional strategies (B1, G3, H2) are specified in `docs/STRATEGY_SPECS.md` but their rank-based portfolio loop is left as a marked extension.
4. No fabricated returns — the leaderboard fills only when *you* run it on real data.

---

## Quick start

```bash
# 1. clone (after you push to GitHub) OR just use the folder
git clone https://github.com/<your-username>/nifty-swing-research.git
cd nifty-swing-research

# 2. create virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# 3. install
pip install -r requirements.txt

# 4. run
python -m swing_research.framework --start 2005-01-01 --capital 1000000 --topk 10
```

Run a subset of strategies:
```bash
python -m swing_research.framework --strategies A1,D1,H1
```

## Outputs (in `outputs/`)

| File | Contents |
|------|----------|
| `leaderboard.csv` | Ranked strategies that survived the filter |
| `all_metrics.csv` | Every strategy + pass/reject + reason |
| `trades_<NAME>.csv` | Full trade log per strategy |
| `equity_<NAME>.png` | Equity curve |

## Rejection filter

A strategy is **rejected** if any of:
- Max Drawdown > 25%
- Profit Factor < 1.5
- Sharpe < 1.0
- Number of trades < 100
- CAGR < Nifty CAGR (same window)

## Strategy categories (20 total)

A: Trend Following · B: Momentum · C: Breakout · D: Mean Reversion · E: Volatility Expansion · F: Institutional Accumulation · G: Relative Strength · H: Multi-factor

Full rules: see [`docs/STRATEGY_SPECS.md`](docs/STRATEGY_SPECS.md).

## Transaction costs modelled (NSE cash, delivery)

STT, exchange charges, SEBI fee, stamp duty, GST, and 15 bps slippage per side. Set brokerage in `round_trip_cost()` if not zero-delivery.

## License

MIT — see [LICENSE](LICENSE).

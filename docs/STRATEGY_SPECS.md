# 20 Swing Trading Strategy Specifications — Nifty 200, Daily

> **Survivorship-bias warning.** These specs are engine-agnostic. The accompanying
> code uses yfinance, which returns **current survivors only** and **no delisted
> stocks / no point-in-time constituents**. Results will be optimistically biased.
> Swap `load_data()` for a point-in-time vendor before trusting any number.

Common conventions used below:
- **ATR** = 14-day Average True Range unless stated.
- **Risk per trade (R)** = (Entry − Stop) × shares = a fixed fraction of equity.
- **Position size** = `floor( (equity * risk_pct) / (entry - stop) )`, capped by
  `max_position_pct * equity / entry` and by available cash.
- **Max portfolio exposure** = sum of open position notional ≤ stated cap.
- **Capital allocation**: equal-risk per signal; if more signals than capacity,
  rank by the strategy's primary score and take the top N.

---

## Category A — Trend Following

### A1. Donchian 50/20 Channel Trend
- **Entry:** Close makes new 50-day high AND price > 200-DMA.
- **Exit:** Close < 20-day low (trailing Donchian stop), or 200-DMA cross-down.
- **Stop:** Initial stop = entry − 2.5×ATR; trail with 20-day low.
- **Risk/trade:** 1.0% of equity. **Max position:** 12%. **Max exposure:** 100%.
- **Allocation:** Up to 10 concurrent positions, equal risk.

### A2. Triple-EMA Stack (8/21/55)
- **Entry:** EMA8 > EMA21 > EMA55, all rising, on a pullback close to EMA21.
- **Exit:** EMA8 crosses below EMA21.
- **Stop:** entry − 2×ATR. **Risk:** 0.75%. **Max position:** 10%. **Exposure:** 90%.

### A3. 200-DMA Regime + ADX Trend
- **Entry:** Price > 200-DMA AND ADX(14) > 25 AND +DI > −DI; enter on close above prior day high.
- **Exit:** ADX < 20 OR close < 50-DMA.
- **Stop:** 3×ATR chandelier from highest high since entry. **Risk:** 1.0%. **Max pos:** 12%. **Exposure:** 100%.

---

## Category B — Momentum

### B1. 12-1 Cross-Sectional Momentum
- **Entry:** Rank universe by 12-month return skipping last month; long top decile, rebalanced weekly. Price > 100-DMA gate.
- **Exit:** Falls out of top decile OR < 100-DMA.
- **Stop:** 20% hard catastrophe stop. **Risk:** equal-weight, 1/N. **Max pos:** 8%. **Exposure:** 100%.

### B2. ROC Acceleration
- **Entry:** ROC(20) > 0, ROC(20) > ROC(60), and RSI(14) crossing up through 55.
- **Exit:** RSI < 45 OR ROC(20) < 0.
- **Stop:** entry − 2×ATR. **Risk:** 1.0%. **Max pos:** 10%. **Exposure:** 90%.

### B3. 52-Week High Momentum
- **Entry:** Close within 3% of 52-week high AND 50-DMA > 200-DMA.
- **Exit:** Close drops >12% from highest close since entry.
- **Stop:** entry − 2.5×ATR. **Risk:** 1.0%. **Max pos:** 12%. **Exposure:** 100%.

---

## Category C — Breakout

### C1. Volatility-Contraction Breakout (VCP-lite)
- **Entry:** 50-day ATR/price at 6-month low (squeeze) AND close breaks 20-day high on volume > 1.5× 50-day avg.
- **Exit:** Close < 10-day low OR +4R target.
- **Stop:** entry − 1.5×ATR (tight, post-squeeze). **Risk:** 0.75%. **Max pos:** 10%. **Exposure:** 80%.

### C2. Opening-Range / Prior-High Breakout (daily proxy)
- **Entry:** Close > max(high) of last 10 days AND today's range > 1.5× ATR.
- **Exit:** 3-day low trailing stop OR +3R.
- **Stop:** entry − 2×ATR. **Risk:** 1.0%. **Max pos:** 10%. **Exposure:** 90%.

### C3. Cup-Base 65-Day Breakout
- **Entry:** Close > 65-day high after ≥40 days of sideways base (range < 25%).
- **Exit:** Close < 21-DMA.
- **Stop:** entry − 2.5×ATR. **Risk:** 1.0%. **Max pos:** 12%. **Exposure:** 100%.

---

## Category D — Mean Reversion

### D1. RSI(2) Pullback in Uptrend
- **Entry:** Price > 200-DMA AND RSI(2) < 10. Enter on close.
- **Exit:** Close > 5-DMA OR RSI(2) > 70 OR 6-day time stop.
- **Stop:** entry − 3×ATR (wide; MR needs room). **Risk:** 1.0%. **Max pos:** 12%. **Exposure:** 80%.

### D2. Bollinger Band Lower-Touch Reversion
- **Entry:** Price > 200-DMA AND close < lower BB(20,2) AND close > prior close (turn confirm).
- **Exit:** Close ≥ BB middle band (20-SMA).
- **Stop:** entry − 2.5×ATR. **Risk:** 1.0%. **Max pos:** 10%. **Exposure:** 80%.

### D3. 3-Down-Days Reversion
- **Entry:** Price > 200-DMA AND 3 consecutive lower closes AND close > 5% below 10-DMA.
- **Exit:** Up day close OR 4-day time stop.
- **Stop:** entry − 2.5×ATR. **Risk:** 0.75%. **Max pos:** 10%. **Exposure:** 70%.

---

## Category E — Volatility Expansion

### E1. NR7 / Inside-Day Expansion
- **Entry:** Yesterday = narrowest range of last 7 (NR7) or inside day; today breaks its high; price > 50-DMA.
- **Exit:** 3-day low trail OR +3R.
- **Stop:** entry − 1.5×ATR. **Risk:** 0.75%. **Max pos:** 10%. **Exposure:** 80%.

### E2. Bollinger Squeeze Release
- **Entry:** BB width at 6-month low ("squeeze"); fires when close exits upper band, price > 100-DMA.
- **Exit:** Close < 20-SMA OR +4R.
- **Stop:** entry − 2×ATR. **Risk:** 1.0%. **Max pos:** 10%. **Exposure:** 90%.

### E3. ATR-Expansion Thrust
- **Entry:** Today's true range > 2× ATR(20) AND close in top 25% of day's range AND close > 50-DMA.
- **Exit:** 2-day low trail OR +2.5R.
- **Stop:** entry − 2×ATR. **Risk:** 1.0%. **Max pos:** 10%. **Exposure:** 80%.

---

## Category F — Institutional Accumulation

### F1. OBV Trend + Price Base
- **Entry:** OBV makes new 50-day high while price still ≤5% below its 50-day high (accumulation divergence); price > 200-DMA.
- **Exit:** OBV < 20-day low OR close < 50-DMA.
- **Stop:** entry − 2.5×ATR. **Risk:** 1.0%. **Max pos:** 12%. **Exposure:** 100%.

### F2. Volume-Dry-Up + Pocket Pivot
- **Entry:** ≥10 days of below-average volume ("dry-up") then an up-day whose volume > max down-day volume of last 10 days; price > 50-DMA.
- **Exit:** Close < 21-DMA.
- **Stop:** entry − 2×ATR. **Risk:** 1.0%. **Max pos:** 10%. **Exposure:** 90%.

### F3. Accumulation/Distribution Line Breakout
- **Entry:** A/D line new 60-day high AND price > 50-DMA AND price > 200-DMA.
- **Exit:** A/D line < 30-day low.
- **Stop:** entry − 2.5×ATR. **Risk:** 1.0%. **Max pos:** 12%. **Exposure:** 100%.

---

## Category G — Relative Strength

### G1. RS-vs-Nifty Leadership
- **Entry:** Stock/Nifty ratio makes new 60-day high AND price > 200-DMA.
- **Exit:** RS ratio < 30-day low.
- **Stop:** entry − 2.5×ATR. **Risk:** 1.0%. **Max pos:** 12%. **Exposure:** 100%.

### G2. Mansfield Relative Strength Cross
- **Entry:** Mansfield RS (RS ratio vs its 52-wk MA) crosses above zero AND price > 30-week MA.
- **Exit:** Mansfield RS < 0.
- **Stop:** entry − 3×ATR. **Risk:** 1.0%. **Max pos:** 12%. **Exposure:** 100%.

### G3. Top-Quartile RS Rotation
- **Entry:** Weekly: rank universe by 6-month RS vs Nifty; hold top quartile that are also > 200-DMA.
- **Exit:** Leaves top quartile.
- **Stop:** 18% catastrophe stop. **Risk:** 1/N equal weight. **Max pos:** 8%. **Exposure:** 100%.

---

## Category H — Multi-Factor Systems

### H1. Trend + Momentum + Volume (3-gate)
- **Entry:** price > 200-DMA (trend) AND ROC(60) in top 30% of universe (momentum) AND OBV rising (volume). Enter on 20-day-high breakout.
- **Exit:** Any gate fails OR close < 50-DMA.
- **Stop:** entry − 2.5×ATR. **Risk:** 1.0%. **Max pos:** 12%. **Exposure:** 100%.

### H2. Quality-Momentum Composite
- **Entry:** Composite score = z(6m return) + z(12m return) − z(60d volatility); long top decile; gate price > 100-DMA.
- **Exit:** Score leaves top 30% OR < 100-DMA.
- **Stop:** 20% catastrophe. **Risk:** 1/N. **Max pos:** 8%. **Exposure:** 100%.

### H3. Regime-Switched Trend/MR
- **Entry:** If Nifty > 200-DMA (risk-on): run A1 Donchian trend. If Nifty < 200-DMA (risk-off): run D1 RSI(2) reversion only on price>200-DMA names, half size.
- **Exit:** Per active sub-strategy.
- **Stop:** Per sub-strategy. **Risk:** 1.0% (trend) / 0.5% (MR). **Max pos:** 12%. **Exposure:** 100% on / 50% off.

---

## Rejection Filter (applied automatically in code)
A strategy is **REJECTED** if any of:
- Max Drawdown > 25%
- Profit Factor < 1.5
- Sharpe < 1.0
- Number of trades < 100
- CAGR < benchmark (Nifty) CAGR over the same window

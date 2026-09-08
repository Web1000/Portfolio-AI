# Methodology

## Value investing

Annual operating cash flow and capital expenditure must cover 330–380 days in a 10-K or 10-K/A. The most recent fiscal end is preferred over filing date, preventing a newly filed comparative year from replacing a newer period. Amendments win within a period and concept. Capex, shares, and debt are matched to that fiscal end. Unsupported or missing concepts stay unavailable.

The supported mappings are intentionally limited to common US-GAAP concepts. This is not a universal XBRL parser. Annual entries can contain restatements; this application uses the latest available facts, not a point-in-time backtest dataset.

```
owner-earnings proxy = operating cash flow − capital expenditure
proxy per share = owner-earnings proxy / fiscal-end shares outstanding
modeled value per share = positive proxy per share × 12
margin of safety = (modeled value per share − stock quote) / modeled value per share
debt ratio = reported debt / positive owner-earnings proxy
```

The cash-flow proxy is closer to free cash flow than a complete Buffett owner-earnings calculation. It does not separate maintenance and growth capex. The multiple is a fixed teaching assumption, without growth, discount-rate, or terminal-value estimates. Negative earnings do not produce a positive valuation. Missing or zero shares and quotes cannot produce a margin of safety.

Debt uses reported aggregate long-term debt when available, otherwise current plus noncurrent components, then adds separately reported short-term borrowings. Company taxonomy differences, commercial paper, leases, and absent concepts can make this incomplete. The report flags unavailable short-term data. Fiscal-end shares can differ from the share count underlying a later market quote; splits and repurchases are not adjusted. A USD quote is required because the supported cash-flow facts are in USD.

### Educational score rubric

| Category | Maximum | Rule |
| --- | ---: | --- |
| Business understanding | 20 | Model review of supplied profile, or labeled demo fixture |
| Cash flow | 25 | Positive proxy / positive operating cash flow: ≥45% → 25, ≥35% → 22, ≥25% → 18, ≥15% → 12, ≥5% → 6, otherwise 2; nonpositive proxy → 0 |
| Moat evidence | 25 | Model review of supplied evidence; instructed to give zero without competitive evidence |
| Debt | 15 | Debt / positive proxy: <0.5 → 15, <1 → 11, <2 → 7, <4 → 3, otherwise 0 |
| Valuation | 15 | Margin of safety: ≥15% → 15, ≥12% → 12, ≥9% → 9, ≥6% → 6, ≥3% → 3, otherwise 0 |

Unavailable inputs produce unavailable subscores and suppress the total. For complete reports: 85+ is “Strong rubric score,” 70–84 “Watchlist,” 50–69 “Mixed,” and below 50 “Weak rubric score.” These labels are not buy/sell signals or probabilities. A separate note states whether the margin meets the 15% threshold.

An SEC identity/industry profile is insufficient to establish moat, management quality, or a full business model. Live narrative prompts explicitly constrain those claims. The demo's qualitative scores are prepared illustrations, not model evaluations.

## Technical analysis

- MA20 and MA50 use simple rolling averages. A bullish label requires price above both averages and MA20 above MA50. Price below both is bearish; unavailable averages mean unknown.
- RSI uses simple averages of gains/losses over the last 14 changes, not Wilder smoothing. Flat prices return 50; uninterrupted decline can return 0.
- One-month return uses 21 closing-price intervals, requiring 22 observations.
- Volatility uses the sample standard deviation of 20 logarithmic daily returns, multiplied by √252 and expressed as a percentage. This convention is imperfect for continuously traded crypto assets.
- Pivot levels compare five bars on each side. Distinct levels nearest the current price are reported. Confirmation requires future bars relative to each historical pivot; these are retrospective chart levels, not backtested real-time signals.
- Volume compares the latest bar to the mean of the latest 20 bars, including that bar. Above 1.5× is high, below 0.6× low; an all-zero average is unknown.

Raw Yahoo OHLC bars are not a total-return series. Corporate actions, partial trading days, delayed data, and missing bars can distort signals. Missing volume is treated as zero at ingestion. Indicator calculations are deterministic; narratives do not establish predictive validity.

## Market explainer

Word-boundary patterns select crypto, ETF, or concept branches, with stock as the fallback. In live mode, Google News RSS headlines and an explicitly identified instrument's Yahoo snapshot provide context. The model writes a draft, then simplifies it while preserving uncertainty and sources. This classifier is intentionally simple and can miss ambiguous questions or uncommon instruments.

Headlines are not full articles. Related news does not prove price-move causation. When providers return no evidence, the prompt states that current price moves and causes must not be asserted. Model responses can still be incorrect and require human review.

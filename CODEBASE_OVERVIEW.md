# Codebase Overview

Last reviewed: 2026-08-08

## What This Project Is

This is a Streamlit stock portfolio tracker. It stores portfolio state in CSV files under `data/`:

- `data/consolidated.csv`: current holdings
- `data/trades.csv`: trade history

The app supports consolidated portfolio views, trade entry, pre-populating existing holdings, trade history, and live stock charts using yfinance and Plotly.

## Main Files

- `app.py`: Streamlit application, page routing, forms, tables, charts, and yfinance lookups.
- `utils/data_manager.py`: CSV initialization, reads, writes, deletes, and lookup helpers.
- `utils/calculations.py`: trade calculations, previews, pre-population, delete-and-rebuild logic.
- `utils/ui_helpers.py`: display helpers for currency/number formatting, row numbers, dropdown options, and CSS.
- `tests/`: pytest coverage for data management, calculations, integrations, and newer UI-related helper behavior.

## Runtime Flow

`app.py` creates a `DataManager` and `TradeCalculator` at startup. The sidebar selects one of five pages:

1. Consolidated Record
2. Trade Entry
3. Pre-populate Database
4. Trade History
5. Stock Charts

Trade submission flows through `TradeCalculator.process_trade()`. That method currently writes the trade to `trades.csv` first, then dispatches to buy, sell, or transfer processing.

## Data Model

`consolidated.csv` columns:

- `Account`
- `StockName`
- `StockSymbol`
- `Quantity`
- `AveragePricePerShare`
- `CapitalGainLoss`
- `DateOfAcquisition`

`trades.csv` columns:

- `Account`
- `StockName`
- `StockSymbol`
- `DateOfTrade`
- `TradeType`
- `SharesTraded`
- `PricePerShare`
- `Commission`

## Calculation Behavior

Buy trades:

- Add commission into trade cost.
- Increase quantity.
- Recalculate average price per share.
- Preserve the original acquisition date for existing holdings.

Sell trades:

- Validate that the holding exists and has enough shares.
- Reduce quantity.
- Keep average cost unchanged.
- Add realized gain/loss to `CapitalGainLoss`.

Transfer trades:

- Currently only record history.
- They do not move shares between accounts yet.

Pre-populated holdings:

- Create a consolidated row directly.
- Do not create a matching trade history row.

Delete trade:

- Removes the selected row from `trades.csv`.
- Rebuilds the affected account+symbol consolidated holding by replaying remaining trades chronologically.

## Tests

Use the local virtualenv:

```bash
venv/bin/python -m pytest -q
```

Current result from review: `101 passed`.

There are pandas future warnings around concatenation and assigning values into columns with incompatible inferred dtypes. They are not failing today, but they are worth addressing.

## Important Risks

- `TradeCalculator.process_trade()` writes trade history before calculation succeeds. A failed sell can remain in `trades.csv` even though holdings were not updated.
- Stock Charts undercounts positions when the same symbol exists in multiple accounts because it often uses the first matching row instead of aggregating by symbol.
- Trade History calculates sell gain/loss using the current consolidated average cost, not the historical average cost at the time of the sell.
- Transfers are incomplete: there is no destination account and no actual movement of shares.
- Once an account exists, some forms only allow choosing an existing account and do not offer a clean way to add a new one.
- Zero-quantity holdings remain in consolidated records after full sells, which may or may not be desired.

## Worktree Note

At review time, the worktree already had uncommitted changes:

```text
 M app.py
?? BUGS.md
?? utils/ui_helpers.py
```

Those were treated as existing user work.

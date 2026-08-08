# Known Bugs and Risks

Last reviewed: 2026-08-08

This document records the current issues found during a code review of the Streamlit stock tracker.

## High Priority

### 1. Invalid sell trades are saved to history

**Status:** Confirmed

`TradeCalculator.process_trade()` writes the trade to `trades.csv` before validating and processing the sell. If the sell fails because the holding does not exist or there are insufficient shares, the failed trade remains in trade history even though the consolidated record is unchanged.

**Location:** [utils/calculations.py](/Users/marcchami/Developer/dad-stock-tracker/utils/calculations.py:147)

**Impact:** Trade history can contain transactions that never actually happened, and rebuilding a holding can produce misleading results.

**Suggested fix:** Validate and process the trade first, then persist it only after the calculation succeeds. Ideally, make the consolidated-record update and trade-history write atomic, or provide rollback if the second write fails.

### 2. Charts undercount holdings when the same stock exists in multiple accounts

**Status:** Confirmed

The Stock Charts page groups by stock symbol for the selector, but then selects only the first matching consolidated row with `.iloc[0]`. Shares, cost basis, current value, and gain/loss therefore ignore additional accounts holding the same symbol.

**Locations:** [app.py](/Users/marcchami/Developer/dad-stock-tracker/app.py:916), [app.py](/Users/marcchami/Developer/dad-stock-tracker/app.py:973), [app.py](/Users/marcchami/Developer/dad-stock-tracker/app.py:1043)

**Impact:** Portfolio metrics and the portfolio overview can be materially wrong for multi-account portfolios.

**Suggested fix:** Aggregate rows by symbol before calculating chart metrics, summing quantity, cost basis, current value, and gain/loss. Keep the account-level view available where needed.

## Medium Priority

### 3. Trade History calculates old sell gains using the current average cost

**Status:** Confirmed limitation

For each sell, Trade History looks up the current consolidated record and uses its current `AveragePricePerShare`. Later purchases can change that average cost, so an older sale is displayed with the wrong cost basis and gain/loss.

**Location:** [app.py](/Users/marcchami/Developer/dad-stock-tracker/app.py:798)

**Impact:** Historical tax and performance information is inaccurate in the UI.

**Suggested fix:** Store the average cost and calculated gain/loss on the sell transaction when it is processed, or replay trades chronologically when displaying history.

### 4. Transfers do not move shares between accounts

**Status:** Confirmed incomplete behavior

`process_transfer_trade()` only records a history entry and does not reduce holdings in a source account or add them to a destination account. The form also has no destination-account field.

**Locations:** [utils/calculations.py](/Users/marcchami/Developer/dad-stock-tracker/utils/calculations.py:137), [app.py](/Users/marcchami/Developer/dad-stock-tracker/app.py:630)

**Impact:** A transfer can make the trade history look complete while the consolidated portfolio remains unchanged. The current price validation also rejects a zero-price transfer.

**Suggested fix:** Add source and destination accounts, preserve the transferred cost basis, update both consolidated records, and allow a transfer price of zero when appropriate.

### 5. The trade forms cannot add a new account after one exists

**Status:** Confirmed UX defect

Once any account exists, Trade Entry and Pre-populate Database show only a selectbox populated from existing accounts. There is no way in those forms to type a new account name.

**Locations:** [app.py](/Users/marcchami/Developer/dad-stock-tracker/app.py:411), [app.py](/Users/marcchami/Developer/dad-stock-tracker/app.py:685)

**Impact:** Users must edit the CSV manually or use a workaround to start tracking a new account.

**Suggested fix:** Add an “Other/New account” option that reveals a text input, or use a combined select-and-create control.

## Lower Priority / Needs Product Decision

### 6. Zero-quantity holdings remain in the consolidated record

**Status:** Needs confirmation

Selling an entire holding updates its quantity to zero but leaves the consolidated row in place. Sell options exclude it, but Consolidated Record and chart-related code may still display or calculate it.

**Impact:** Empty positions may appear in the portfolio and can create confusing zero-value rows or edge cases in percentage calculations.

**Suggested fix:** Decide whether zero-quantity positions should be retained for audit history. If retained, filter them from active portfolio views and guard against zero cost basis; if not, delete the row after a full sale.

### 7. Plain symbols may resolve to a TSX ticker before a US ticker

**Status:** Potential issue; likely intentional for the app’s Canadian use case

Symbol resolution tries the `.TO` form first for plain symbols. A US ticker that shares its symbol with a Canadian listing could therefore resolve to the TSX listing unexpectedly.

**Impact:** The stored symbol and fetched market data could refer to the wrong exchange.

**Suggested fix:** Let the user choose the exchange when ambiguous, or make the default exchange explicit in the UI.

## Verification Gap

The automated test suite could not be run during review because `pytest` is not installed in the current Python environment. Install the dependencies from [requirements-test.txt](/Users/marcchami/Developer/dad-stock-tracker/requirements-test.txt) and run `pytest -q` before closing these items.

## Open Question

`questions.txt` asks whether pre-populated holdings should also be added to trade history. This is a product decision rather than a confirmed bug; document the chosen behavior and update the workflow accordingly.

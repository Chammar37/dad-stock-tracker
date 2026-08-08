# Feature Specifications

This document groups the client requests into implementation-sized features. Items marked as verification are already present in the current app and should be protected by tests.

## Feature 1: Trade Entry Identity and Stock Selection

### Goal

Make stock entry consistent for Buy and Sell trades, with the symbol as the primary identifier.

### To Do

- [ ] For an existing account and symbol, allow symbol-only entry.
- [ ] Reuse the existing consolidated stock name automatically.
- [ ] For a new symbol, allow or require a stock name.
- [ ] Make the Sell dropdown store the symbol as its value instead of parsing the display label.
- [ ] Keep Sell options limited to the selected account and positive quantities.
- [ ] Keep Sell options sorted by symbol ascending.
- [ ] Resolve and store canonical symbols consistently, including exchange suffixes.

### Acceptance Criteria

- An existing holding can be bought or sold by entering/selecting its symbol once.
- The stock name and available quantity appear automatically.
- A new holding can be entered with both a name and symbol.
- Selecting a Sell option does not require re-entering the stock.
- Zero-quantity holdings are excluded and symbols appear A-Z.

## Feature 2: Trade Submission and Form Lifecycle

### Goal

Make Buy and Sell submission predictable and prevent invalid or duplicate-looking trades.

### To Do

- [ ] Fix the Sell quantity state so `0.0` cannot replace the default integer quantity.
- [ ] Normalize quantity widget state when trade type, account, or selected symbol changes.
- [ ] Display integer fields as `0`, not `0.00`.
- [ ] Keep Preview non-persisting.
- [ ] Validate the trade before adding it to Trade History.
- [ ] After success, display exactly `Trade Completed`.
- [ ] Clear all Trade Entry fields after a successful Process Trade.
- [ ] Preserve entered fields after Preview so the user can review or adjust them.

### Acceptance Criteria

- A valid Sell can be previewed and processed with one stock selection.
- A Sell never fails because the quantity is represented as `0.0`.
- Failed trades do not appear in Trade History.
- Successful trades show `Trade Completed` and reset the form.
- Preview does not write to either CSV file.

## Feature 3: Pre-populate Confirmation

### Goal

Make the calculated cost/share visible and confirmable before an existing holding is saved.

### To Do

- [ ] Keep Name, Symbol, and Cost/share together in a bold summary.
- [ ] Calculate Cost/share as `Book Cost / Quantity`.
- [ ] Update the summary as Quantity or Book Cost changes.
- [ ] Add an explicit confirmation control if the client requires an approval action.
- [ ] Validate account, symbol, quantity, book cost, and acquisition date.

### Acceptance Criteria

- The calculated cost/share is visible before `Add Holding` is clicked.
- The value updates immediately when quantity or book cost changes.
- A holding cannot be saved with an invalid quantity, cost, or date.
- Existing account selection and new-account entry both work.

## Feature 4: Consolidated Record Management

### Goal

Allow users to correct and remove consolidated records safely.

### To Do

- [ ] Add Edit controls to the Consolidated Record view.
- [ ] Add Delete controls with confirmation.
- [ ] Validate edited quantity, average price, gain/loss, symbol, account, and date.
- [ ] Define how manual edits interact with Trade History rebuilds.
- [ ] Keep display row numbers one-based and sequential.

### Acceptance Criteria

- A user can edit an existing row and see the change after refresh.
- A user must confirm before deleting a row.
- Invalid edits are rejected without changing the CSV.
- Row numbers start at `1` after filtering and refresh.
- The app clearly communicates whether a manual edit is an adjustment or a replacement of calculated data.

## Feature 5: Trade History Financial Details and Dates

### Goal

Make Trade History useful for reviewing transaction amounts and historical records.

### To Do

- [ ] Ensure all new trades save `DateOfTrade`.
- [ ] Add Cost to the displayed history.
- [ ] Add Gross Proceeds to the displayed history.
- [ ] Add Net Proceeds where useful.
- [ ] Confirm whether Cost includes commission.
- [ ] Store average cost at the time of sale for accurate historical gain/loss.
- [ ] Backfill or explicitly label missing historical dates.

### Acceptance Criteria

- New Buy and Sell rows always show their trade date.
- Buy rows show cost.
- Sell rows show gross proceeds and, where included, net proceeds.
- Historical Sell gain/loss does not change when later Buy trades change the current average cost.
- Missing legacy dates are never silently presented as if they were known.

## Feature 6: Portfolio Data Correction and Average-Cost Audit

### Goal

Correct legacy records without hiding uncertainty in the source data.

### To Do

- [ ] Obtain acquisition dates for CM, NTR, SIA, and other affected holdings.
- [ ] Backfill missing `DateOfAcquisition` values.
- [ ] Obtain the BHC account, canonical symbol, quantity, book cost, commissions, and expected average price.
- [ ] Recalculate BHC using the agreed commission treatment.
- [ ] Check for duplicate symbols or account/symbol mismatches.
- [ ] Add a regression test for the corrected BHC scenario.

### Acceptance Criteria

- All corrected dates are traceable to client-provided or trade-history data.
- BHC has one clearly identified account/symbol record.
- The stored average price matches the agreed formula and source values.
- The correction survives a rebuild or is explicitly documented as a manual adjustment.

## Feature 7: Verification and Regression Coverage

### Already Implemented: Protect With Tests

- [x] Pre-populate Name/Symbol/Cost grouping.
- [x] Buy Name/Symbol/Average Price grouping.
- [x] Sell Name/Symbol/available quantity grouping.
- [x] One-based consolidated row numbering.
- [x] Sell dropdown positive-quantity filtering.
- [x] Sell dropdown symbol sorting.
- [x] Green and bold Preview button styling.
- [x] Red Process Trade button styling.

### To Do

- [ ] Run the full test suite after installing `requirements-test.txt`.
- [ ] Add integration coverage for the new Sell selection state flow.
- [ ] Add integration coverage for complete form reset after successful submission.
- [ ] Add tests for consolidated edit/delete behavior.
- [ ] Add tests for Trade History cost/proceeds and historical average cost.
- [ ] Add data migration tests for legacy missing dates.

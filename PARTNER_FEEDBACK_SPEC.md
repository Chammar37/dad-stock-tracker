# Partner Feedback - Implementation Specification

**Date:** 2025-12-29
**Status:** Ready for Implementation
**Priority:** High

---

## Overview

This document outlines UI/UX improvements and bug fixes requested by non-technical partner. Requirements have been clarified through detailed technical interview.

---

## 1. Pre-populate Database Page

### 1.1 Visual Grouping - Name/Symbol/Cost
**Status:** 🔴 Not Implemented

**Requirement:**
Display stock name, symbol, and calculated cost per share as a **bold, grouped summary** below the form.

**Behavior:**
- Trigger: Immediately after stock symbol is resolved (e.g., user types "AAPL" → resolves to "Apple Inc.")
- Update: Cost per share recalculates dynamically as user enters quantity and book cost
- Location: Below the input fields in the form
- Styling: Bold text, visually grouped (consider using `st.info()` or custom markdown)

**Example Display:**
```
📊 AAPL - Apple Inc. @ $150.25/share
```

**Implementation Notes:**
- Keep input fields in their current positions
- This is additional display output, not repositioning inputs
- Cost calculation: Book Cost ÷ Quantity

---

## 2. Consolidated Record Page

### 2.1 Row Numbering
**Status:** 🔴 Not Implemented

**Requirement:**
Add a row number column to the consolidated holdings table, starting from 1.

**Behavior:**
- Column name: "#" or "No."
- Position: First column (leftmost)
- Numbering: Sequential starting at 1, increments by 1
- Persists through filtering (filtered rows maintain original numbering)

**Implementation:**
```python
display_df.insert(0, '#', range(1, len(display_df) + 1))
```

### 2.2 Missing Dates
**Status:** ✅ Already Addressed

**Resolution:**
Date validation has been implemented to prevent future missing dates. Existing bad data (CM, NTR, SIA) requires manual CSV cleanup by partner.

---

## 3. Trade Entry - BUY Page

### 3.1 Add Preview Button
**Status:** 🔴 Not Implemented

**Requirement:**
Add a Preview button for BUY trades, matching the layout and behavior of SELL trades.

**Button Configuration:**
- **Preview Button:**
  - Color: Green (use `type="secondary"` with custom styling if needed)
  - Position: Left column (col1)
  - Label: "Preview Trade"

- **Process Trade Button:**
  - Color: Red (use `type="primary"`)
  - Position: Right column (col2)
  - Label: "Process Trade"

**Layout:**
```python
col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    preview_submitted = st.form_submit_button("Preview Trade", type="secondary")  # Style green
with col_btn2:
    submitted = st.form_submit_button("Process Trade", type="primary")  # Style red
```

### 3.2 Preview Calculations Display
**Status:** 🔴 Not Implemented

**Requirement:**
When Preview button is clicked, show calculations in a highlighted success box with metrics.

**Display Format:**
Use `st.success()` with `st.columns()` for metrics layout.

**Metrics to Show (Best Practices for Financial Advisors):**
1. **Total Cost of Trade**
   `(Shares × Price per Share) + Commission`

2. **New Total Shares**
   `Current Quantity + Shares Traded`

3. **New Average Price Per Share**
   `(Total Cost of Existing + Cost of Trade) / New Quantity`

4. **New Total Book Value**
   `New Quantity × New Average Price`

**Example Layout:**
```python
st.success("Preview - Buy Trade")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Cost", format_currency(total_cost))
with col2:
    st.metric("New Total Shares", new_quantity)
with col3:
    st.metric("New Avg Price", format_currency(new_avg_price))
with col4:
    st.metric("New Book Value", format_currency(new_book_value))
```

### 3.3 Visual Grouping - Name/Symbol/Avg Price
**Status:** 🔴 Not Implemented

**Requirement:**
Display stock name, symbol, and calculated average price as **bold summary** after symbol resolution.

**Behavior:**
- Trigger: After user enters stock symbol and it resolves
- Location: Below symbol input field (in col1)
- Styling: Bold text, use `st.caption()` or `st.markdown()`
- Shows current avg price if existing holding, or will show new avg after preview

**Example Display:**
```
📊 AAPL - Apple Inc. @ $145.50/share (current avg)
```

### 3.4 Form Clear After Processing
**Status:** 🔴 Bug - Needs Fix

**Requirement:**
After successfully processing a BUY trade, fully clear all form fields.

**Current Behavior:** Form does not clear after successful processing
**Expected Behavior:** All fields reset to defaults (empty strings, default commission value)

**Implementation:**
```python
if success:
    st.success(message)
    # Clear all session state keys related to the form
    for key in ["stock_symbol_buy", "shares_traded_buy", "price_per_share_buy", ...]:
        st.session_state.pop(key, None)
    st.rerun()
```

---

## 4. Trade Entry - SELL Page

### 4.1 Button Colors
**Status:** 🔴 Not Implemented

**Requirement:**
- Preview button: Green (`type="secondary"` with green styling)
- Process Trade button: Red (`type="primary"`)
- Preview button should also be **bold**

**Note:** Partner explicitly requested this color scheme despite red typically signaling danger/stop.

### 4.2 Dropdown Selection Bug Fix
**Status:** 🔴 Critical Bug

**Current Behavior:**
After successfully processing a SELL trade, the form does not clear. When attempting a second sell, the stock dropdown shows "Please select a stock to sell/transfer" error even after selecting a stock.

**Root Cause:**
Form state not properly resetting after successful submission. Session state keys are not being cleared.

**Expected Behavior:**
After successful sell processing, form should fully clear all fields and reset to initial state.

**Implementation Strategy:**
```python
if success:
    st.success(message)
    # Clear ALL form-related session state
    session_keys_to_clear = [
        "sell_stock_select",
        "shares_input",
        "price_per_share_sell",
        "commission_sell",
        "date_of_trade_sell",
        # Add any other sell form keys
    ]
    for key in session_keys_to_clear:
        st.session_state.pop(key, None)
    st.rerun()
```

**Testing:**
1. Process a sell successfully
2. Verify form clears completely
3. Attempt to enter another sell
4. Verify dropdown works without "Please select" error

### 4.3 Dropdown Sorting & Filtering
**Status:** 🔴 Not Implemented

**Requirement:**
Stock dropdown for sell trades should be:
1. **Sorted** in ascending order by stock symbol (A → Z)
2. **Filtered** to exclude zero-quantity holdings

**Current Implementation:**
```python
# In get_available_stocks_for_sell()
df = df[df['Quantity'] > 0]  # ✅ Already filters zero-quantity

# Need to add sorting:
available_stocks = []
for _, row in df.iterrows():
    # ... existing code ...
    available_stocks.append((symbol, display_name, quantity))

# ADD SORTING:
available_stocks.sort(key=lambda x: x[0])  # Sort by symbol (index 0)
return available_stocks
```

### 4.4 Visual Grouping - Name/Symbol
**Status:** 🔴 Not Implemented

**Requirement:**
After selecting a stock from dropdown, display stock name and symbol as **bold summary**.

**Behavior:**
- Trigger: Immediately after stock selection from dropdown
- Location: Below dropdown (in col1)
- Styling: Bold text

**Example Display:**
```
📊 AAPL - Apple Inc. (100 shares available)
```

### 4.5 Preview Display
**Status:** 🟡 Partially Implemented

**Current Status:** Preview exists but needs styling update
**Required Changes:**
- Display in `st.success()` box (green background)
- Make metrics bold
- Ensure consistent layout with BUY preview

---

## 5. Trade History Page

### 5.1 Add Capital Gain/Loss Column
**Status:** 🔴 Not Implemented

**Requirement:**
Add a new calculated column showing capital gain/loss for each trade.

**Column Configuration:**
- **Name:** "Gain/Loss"
- **Position:** Between "Price/Share" and "Commission"
- **Column Order:** `...| Symbol | Date | Type | Shares | Price/Share | Gain/Loss | Commission`

**Calculation Logic:**
```python
def calculate_trade_gain_loss(row):
    """Calculate gain/loss for a single trade row."""
    if row['TradeType'] == 'S':  # Sell trade
        # Need to fetch avg cost at time of sale from consolidated record
        # This is complex - requires historical tracking

        # For now, calculate based on CURRENT avg cost (limitation):
        shares = row['SharesTraded']
        price = row['PricePerShare']
        commission = row['Commission']

        net_proceeds = (shares * price) - commission

        # Get current avg cost from consolidated (not perfect but workable)
        record = data_manager.get_consolidated_record(row['Account'], row['StockSymbol'])
        if record:
            avg_cost = record['AveragePricePerShare']
            cost_basis = shares * avg_cost
            gain_loss = net_proceeds - cost_basis
            return format_currency(gain_loss)

    return '-'  # For Buy, Transfer, or if data unavailable
```

**Display Rules:**
- **Sell trades:** Show calculated gain/loss as currency (e.g., "$1,234.56" or "-$500.00")
- **Buy trades:** Show "-"
- **Transfer trades:** Show "-"

**Formatting:**
- Positive gains: Green text (optional enhancement)
- Losses (negative): Red text (optional enhancement)
- Use `format_currency()` helper function

**Important Limitation:**
This calculation uses the CURRENT average cost, not the average cost AT THE TIME OF THE SALE. For 100% accuracy, would need to implement historical cost tracking. Document this limitation.

**Alternative Approach (More Accurate):**
Store the average cost at time of sale in trades.csv when processing sell trades. This would require schema change:
```python
# Add new column to trades.csv: AvgCostAtSale
# Update process_sell_trade() to save this value
```

---

## 6. Color Scheme Reference

### Button Styling
**Challenge:** Streamlit's native button types are limited (primary, secondary). Custom colors require CSS.

**Recommended Approach:**
```python
# Custom CSS injection
st.markdown("""
<style>
    /* Green Preview buttons */
    .stButton button[kind="secondary"] {
        background-color: #28a745 !important;
        color: white !important;
        font-weight: bold !important;
    }

    /* Red Process buttons */
    .stButton button[kind="primary"] {
        background-color: #dc3545 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)
```

**Alternative:** Use Streamlit's built-in colors with custom labels:
- Preview: `type="secondary"` (default gray/blue)
- Process: `type="primary"` (default blue)

Then rely on labels and position to differentiate.

---

## 7. Implementation Priority

### Phase 1: Critical Bugs (Do First)
1. ✅ **Sell form not clearing after success** - Breaks user workflow
2. ✅ **Sell dropdown sorting** - UX improvement, easy fix

### Phase 2: High-Value Features
3. ✅ **Add Preview to BUY trades** - Consistency, important for user confidence
4. ✅ **Capital Gain/Loss in Trade History** - Core financial functionality
5. ✅ **Row numbers in Consolidated** - Simple, improves readability

### Phase 3: Polish & UX
6. ✅ **Visual grouping (Name/Symbol/Cost)** - All three pages
7. ✅ **Button color styling** - Visual consistency
8. ✅ **Update Sell preview styling** - Match BUY preview

---

## 8. Testing Checklist

### Pre-populate Page
- [ ] Enter stock symbol, verify Name/Symbol/Cost displays after resolution
- [ ] Change quantity/book cost, verify cost per share updates dynamically
- [ ] Verify bold styling applied
- [ ] Test with TSX stocks (.TO suffix)

### Consolidated Record
- [ ] Verify row numbers appear starting from 1
- [ ] Apply filters, verify numbering doesn't reset
- [ ] Test with empty consolidated (edge case)

### Trade Entry - BUY
- [ ] Verify Preview button appears (green)
- [ ] Verify Process Trade button (red)
- [ ] Click Preview, verify all 4 metrics display correctly
- [ ] Process trade successfully, verify form fully clears
- [ ] Attempt second buy immediately, verify form is clean
- [ ] Verify Name/Symbol/Avg price summary appears after symbol resolution

### Trade Entry - SELL
- [ ] Verify dropdown sorted alphabetically by symbol
- [ ] Verify zero-quantity holdings excluded
- [ ] Process sell successfully, verify form fully clears
- [ ] Attempt second sell, verify dropdown works without error
- [ ] Verify Preview button styling (green, bold)
- [ ] Verify Process button styling (red)
- [ ] Click Preview, verify display in success box

### Trade History
- [ ] Verify Gain/Loss column appears between Price/Share and Commission
- [ ] Verify Sell trades show calculated gain/loss
- [ ] Verify Buy trades show "-"
- [ ] Verify Transfer trades show "-"
- [ ] Test with trade that has no consolidated record (edge case)

---

## 9. Known Limitations

### Capital Gain/Loss Calculation
**Limitation:** Uses CURRENT average cost from consolidated record, not the average cost AT THE TIME of the sale.

**Impact:** If user deletes/modifies holdings after a sell, the displayed gain/loss will be inaccurate.

**Workaround:** Document this clearly in UI (tooltip or help text)

**Future Enhancement:** Store `AvgCostAtSale` in trades.csv during sell processing for historical accuracy.

---

## 10. Dependencies & Requirements

- Streamlit version: (current version in requirements.txt)
- No new packages required
- CSS customization may require `unsafe_allow_html=True`

---

## 11. Rollback Plan

All changes are UI/UX focused with minimal data structure changes. Rollback strategy:
1. Keep backup of app.py before modifications
2. Git commit after each major feature
3. Test in dev environment before production deploy

---

## Questions for Partner (If Any)

None - all requirements clarified through interview.

---

**Prepared by:** AI Assistant
**Reviewed by:** [Pending]
**Approved by:** [Pending]

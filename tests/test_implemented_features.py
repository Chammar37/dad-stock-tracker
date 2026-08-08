"""Regression tests for client-requested behavior already implemented in the app."""

import pandas as pd

from utils.ui_helpers import (
    BUTTON_STYLES_CSS,
    add_row_numbers,
    build_available_stock_options,
    build_holding_summary,
    format_number,
)


def test_preview_and_process_button_styles_are_defined():
    """Preview is green/bold and Process Trade is red in the shared CSS."""
    assert "button[kind=\"secondary\"]" in BUTTON_STYLES_CSS
    assert "background-color: #28a745" in BUTTON_STYLES_CSS
    assert "font-weight: bold" in BUTTON_STYLES_CSS
    assert "button[kind=\"primary\"]" in BUTTON_STYLES_CSS
    assert "background-color: #dc3545" in BUTTON_STYLES_CSS


def test_format_number_displays_zero_without_decimal_places():
    assert format_number(0) == "0"
    assert format_number(0.0) == "0"


def test_sell_options_are_filtered_and_sorted_by_symbol():
    holdings = pd.DataFrame([
        {
            "Account": "TFSA",
            "StockName": "Zero Quantity",
            "StockSymbol": "ZZZ",
            "Quantity": 0,
        },
        {
            "Account": "TFSA",
            "StockName": "Microsoft",
            "StockSymbol": "MSFT",
            "Quantity": 5,
        },
        {
            "Account": "TFSA",
            "StockName": "Apple",
            "StockSymbol": "AAPL",
            "Quantity": 10,
        },
        {
            "Account": "RRSP",
            "StockName": "Other Account",
            "StockSymbol": "AAA",
            "Quantity": 20,
        },
    ])

    options = build_available_stock_options(holdings, account="TFSA")

    assert [symbol for symbol, _, _ in options] == ["AAPL", "MSFT"]
    assert all(quantity > 0 for _, _, quantity in options)
    assert "shares in TFSA" in options[0][1]


def test_consolidated_row_numbers_start_at_one_and_are_sequential():
    holdings = pd.DataFrame({"StockSymbol": ["AAPL", "MSFT", "RSI.TO"]})

    numbered = add_row_numbers(holdings)

    assert numbered["#"].tolist() == [1, 2, 3]
    assert list(holdings.columns) == ["StockSymbol"]


def test_prepopulate_summary_groups_name_symbol_and_cost():
    summary = build_holding_summary("AMZN", "Amazon.com Inc.", " @ $150.00/share")

    assert summary == "**📊 AMZN - Amazon.com Inc. @ $150.00/share**"


def test_buy_summary_groups_name_symbol_and_current_average():
    summary = build_holding_summary(
        "AAPL", "Apple Inc.", " @ $150.50/share (current avg)"
    )

    assert summary == "**📊 AAPL - Apple Inc. @ $150.50/share (current avg)**"


def test_sell_summary_groups_name_symbol_and_available_quantity():
    summary = build_holding_summary("AAPL", "Apple Inc.", " (100 shares available)")

    assert summary == "**📊 AAPL - Apple Inc. (100 shares available)**"

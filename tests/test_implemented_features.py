"""Regression tests for client-requested behavior already implemented in the app."""

import pandas as pd

from utils.ui_helpers import (
    BUTTON_STYLES_CSS,
    NEW_ACCOUNT_OPTION,
    add_row_numbers,
    build_account_options,
    build_available_stock_options,
    build_holding_summary,
    build_stock_option_lookup,
    build_trade_quantity_context,
    calculate_cost_per_share,
    find_existing_holding_by_symbol,
    format_number,
    normalize_trade_quantity_state,
    reset_invalid_selectbox_value,
    reset_prepopulate_state,
    resolve_account_input,
    reset_trade_entry_state,
)


def test_preview_and_process_button_styles_are_defined():
    """Preview is green/bold and Process Trade is red in the shared CSS."""
    assert "button[kind=\"secondary\"]" in BUTTON_STYLES_CSS
    assert "background-color: #28a745" in BUTTON_STYLES_CSS
    assert "font-weight: bold" in BUTTON_STYLES_CSS
    assert "button[kind=\"primary\"]" in BUTTON_STYLES_CSS
    assert "background-color: #dc3545" in BUTTON_STYLES_CSS


def test_number_input_stepper_buttons_are_hidden():
    assert 'div[data-testid="stNumberInput"] button' in BUTTON_STYLES_CSS
    assert "display: none !important" in BUTTON_STYLES_CSS


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


def test_stock_option_lookup_keeps_symbol_as_selectbox_value():
    options = [
        ("AAPL", "AAPL - Apple (10 shares in TFSA)", 10),
        ("MSFT", "MSFT - Microsoft (5 shares in TFSA)", 5),
    ]

    lookup = build_stock_option_lookup(options)

    assert list(lookup.keys()) == ["AAPL", "MSFT"]
    assert lookup["AAPL"]["display"] == "AAPL - Apple (10 shares in TFSA)"
    assert lookup["AAPL"]["quantity"] == 10


def test_invalid_selectbox_value_resets_before_widget_creation():
    session_state = {"sell_stock_select": "MSFT"}

    did_reset = reset_invalid_selectbox_value(
        session_state,
        "sell_stock_select",
        ["", "AAPL"],
    )

    assert did_reset
    assert session_state["sell_stock_select"] == ""


def test_valid_selectbox_value_is_preserved_before_widget_creation():
    session_state = {"sell_stock_select": "AAPL"}

    did_reset = reset_invalid_selectbox_value(
        session_state,
        "sell_stock_select",
        ["", "AAPL"],
    )

    assert not did_reset
    assert session_state["sell_stock_select"] == "AAPL"


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


def test_existing_holding_lookup_matches_canonical_or_base_symbol():
    holdings = pd.DataFrame([
        {
            "Account": "TFSA",
            "StockName": "Rogers Sugar",
            "StockSymbol": "RSI.TO",
            "Quantity": 10,
        },
        {
            "Account": "RRSP",
            "StockName": "Rogers Sugar",
            "StockSymbol": "RSI.TO",
            "Quantity": 20,
        },
    ])

    base_match = find_existing_holding_by_symbol(holdings, "TFSA", "rsi")
    canonical_match = find_existing_holding_by_symbol(holdings, "TFSA", "RSI.TO")

    assert base_match["StockSymbol"] == "RSI.TO"
    assert canonical_match["Account"] == "TFSA"
    assert find_existing_holding_by_symbol(holdings, "TFSA", "MSFT") is None


def test_existing_holding_lookup_prefers_exact_canonical_symbol():
    holdings = pd.DataFrame([
        {
            "Account": "TFSA",
            "StockName": "Apple US",
            "StockSymbol": "AAPL",
            "Quantity": 10,
        },
        {
            "Account": "TFSA",
            "StockName": "Apple Canada",
            "StockSymbol": "AAPL.TO",
            "Quantity": 20,
        },
    ])

    exact_match = find_existing_holding_by_symbol(holdings, "TFSA", "AAPL.TO")

    assert exact_match["StockName"] == "Apple Canada"


def test_existing_holding_lookup_rejects_ambiguous_base_symbol():
    holdings = pd.DataFrame([
        {
            "Account": "TFSA",
            "StockName": "Apple US",
            "StockSymbol": "AAPL",
            "Quantity": 10,
        },
        {
            "Account": "TFSA",
            "StockName": "Apple Canada",
            "StockSymbol": "AAPL.TO",
            "Quantity": 20,
        },
    ])

    base_match = find_existing_holding_by_symbol(holdings, "TFSA", "AAPL")

    assert base_match["StockSymbol"] == "AAPL"


def test_existing_holding_lookup_requires_unambiguous_base_symbol():
    holdings = pd.DataFrame([
        {
            "Account": "TFSA",
            "StockName": "Test TSX",
            "StockSymbol": "TEST.TO",
            "Quantity": 10,
        },
        {
            "Account": "TFSA",
            "StockName": "Test Venture",
            "StockSymbol": "TEST.V",
            "Quantity": 20,
        },
    ])

    assert find_existing_holding_by_symbol(holdings, "TFSA", "TEST") is None


def test_reset_trade_entry_state_clears_only_trade_entry_keys():
    session_state = {
        "trade_account": "TFSA",
        "trade_new_account": "Cash",
        "buy_stock_symbol": "AAPL",
        "sell_stock_select": "AAPL",
        "shares_input": 10,
        "trade_price_per_share": 150.0,
        "trade_commission": 9.99,
        "unrelated": "keep me",
    }

    reset_trade_entry_state(session_state)

    assert session_state == {"unrelated": "keep me"}


def test_prepopulate_cost_per_share_calculates_only_for_valid_values():
    assert calculate_cost_per_share(20, 3000.00) == 150.00
    assert calculate_cost_per_share(0, 3000.00) is None
    assert calculate_cost_per_share(20, 0) is None
    assert calculate_cost_per_share("bad", 3000.00) is None


def test_reset_prepopulate_state_clears_only_prepopulate_keys():
    session_state = {
        "prepopulate_account": "TFSA",
        "prepopulate_new_account": "Cash",
        "prepopulate_stock_symbol": "AAPL",
        "prepopulate_quantity": 10,
        "prepopulate_book_cost": 1000.0,
        "prepopulate_date": "2024-01-01",
        "unrelated": "keep me",
    }

    reset_prepopulate_state(session_state)

    assert session_state == {"unrelated": "keep me"}


def test_account_options_allow_existing_or_new_account():
    options = build_account_options(["RRSP", "TFSA"])

    assert options == ["RRSP", "TFSA", NEW_ACCOUNT_OPTION]
    assert resolve_account_input("TFSA") == "TFSA"
    assert resolve_account_input(NEW_ACCOUNT_OPTION, "  Cash  ") == "Cash"


def test_trade_quantity_context_normalizes_values():
    context = build_trade_quantity_context("s", " TFSA ", "aapl")

    assert context == ("S", "TFSA", "AAPL")


def test_trade_quantity_state_resets_only_when_context_changes():
    session_state = {}
    first_context = build_trade_quantity_context("B", "TFSA", "AAPL")

    did_reset = normalize_trade_quantity_state(session_state, first_context)
    assert did_reset
    assert session_state["shares_input"] == 1
    assert session_state["shares_input_context"] == first_context

    session_state["shares_input"] = 25
    did_reset = normalize_trade_quantity_state(session_state, first_context)
    assert not did_reset
    assert session_state["shares_input"] == 25

    next_context = build_trade_quantity_context("S", "TFSA", "AAPL")
    did_reset = normalize_trade_quantity_state(session_state, next_context)
    assert did_reset
    assert session_state["shares_input"] == 1
    assert session_state["shares_input_context"] == next_context


def test_trade_quantity_state_resets_for_account_or_symbol_change():
    session_state = {
        "shares_input": 40,
        "shares_input_context": build_trade_quantity_context("S", "TFSA", "AAPL"),
    }

    account_context = build_trade_quantity_context("S", "RRSP", "AAPL")
    assert normalize_trade_quantity_state(session_state, account_context)
    assert session_state["shares_input"] == 1

    session_state["shares_input"] = 15
    symbol_context = build_trade_quantity_context("S", "RRSP", "MSFT")
    assert normalize_trade_quantity_state(session_state, symbol_context)
    assert session_state["shares_input"] == 1


def test_trade_quantity_state_coerces_bad_same_context_value_to_one():
    context = build_trade_quantity_context("B", "TFSA", "AAPL")
    session_state = {
        "shares_input": 0.0,
        "shares_input_context": context,
    }

    did_reset = normalize_trade_quantity_state(session_state, context)

    assert not did_reset
    assert session_state["shares_input"] == 1


def test_trade_quantity_state_preserves_first_submit_after_stock_selection():
    selected_context = build_trade_quantity_context("S", "TFSA", "AAPL")
    session_state = {}

    assert normalize_trade_quantity_state(session_state, selected_context)
    assert session_state["shares_input"] == 1

    session_state["shares_input"] = 37
    did_reset = normalize_trade_quantity_state(session_state, selected_context)

    assert not did_reset
    assert session_state["shares_input"] == 37

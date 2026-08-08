"""Pure helpers used by the Streamlit views and their tests."""

from typing import Optional

import pandas as pd


BUTTON_STYLES_CSS = """
<style>
    /* Green Preview buttons (secondary type) */
    div[data-testid="column"]:first-child button[kind="secondary"] {
        background-color: #28a745 !important;
        color: white !important;
        font-weight: bold !important;
        border: none !important;
    }
    div[data-testid="column"]:first-child button[kind="secondary"]:hover {
        background-color: #218838 !important;
    }

    /* Red Process Trade buttons (primary type) */
    div[data-testid="column"]:last-child button[kind="primary"] {
        background-color: #dc3545 !important;
        color: white !important;
        border: none !important;
    }
    div[data-testid="column"]:last-child button[kind="primary"]:hover {
        background-color: #c82333 !important;
    }
</style>
"""

NEW_ACCOUNT_OPTION = "Add new account..."


def format_currency(value) -> str:
    """Format a value as currency."""
    if pd.isna(value):
        return "$0.00"
    return f"${value:,.2f}"


def format_number(value) -> str:
    """Format quantities without unnecessary trailing decimal zeroes."""
    if pd.isna(value):
        return "0"

    if abs(value) < 1:
        return f"{value:.4f}".rstrip("0").rstrip(".")
    if abs(value) < 10:
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{value:,.0f}"


def build_available_stock_options(
    df: pd.DataFrame, account: Optional[str] = None
) -> list[tuple[str, str, int]]:
    """Build sorted, positive-quantity stock options for Sell/Transfer."""
    if df.empty:
        return []

    filtered_df = df.copy()
    if account:
        filtered_df = filtered_df[filtered_df["Account"] == account]

    filtered_df["Quantity"] = (
        pd.to_numeric(filtered_df["Quantity"], errors="coerce")
        .fillna(0)
        .round()
        .astype(int)
    )
    filtered_df = filtered_df[filtered_df["Quantity"] > 0]

    options = []
    for _, row in filtered_df.iterrows():
        symbol = str(row["StockSymbol"])
        name = str(row["StockName"])
        quantity = int(row["Quantity"])
        account_name = str(row["Account"])
        display_name = f"{symbol} - {name} ({quantity:d} shares in {account_name})"
        options.append((symbol, display_name, quantity))

    return sorted(options, key=lambda option: option[0])


def build_stock_option_lookup(
    options: list[tuple[str, str, int]]
) -> dict[str, dict[str, object]]:
    """Build lookup metadata for symbol-valued stock selectboxes."""
    return {
        symbol: {
            "display": display,
            "quantity": int(quantity),
        }
        for symbol, display, quantity in options
    }


def reset_invalid_selectbox_value(
    session_state,
    key: str,
    valid_values: list[str],
    default_value: str = "",
) -> bool:
    """Reset a keyed selectbox when its stored value is no longer valid."""
    current_value = session_state.get(key, default_value)
    if current_value not in valid_values:
        session_state[key] = default_value
        return True
    return False


def build_account_options(accounts: list[str]) -> list[str]:
    """Return account select options with a create-new choice."""
    return list(accounts) + [NEW_ACCOUNT_OPTION]


def resolve_account_input(selected_account: str, new_account: str = "") -> str:
    """Resolve an existing-or-new account selection into the account name."""
    if selected_account == NEW_ACCOUNT_OPTION:
        return new_account.strip()
    return str(selected_account or "").strip()


def find_existing_holding_by_symbol(
    df: pd.DataFrame, account: str, symbol: str
) -> Optional[dict]:
    """Find an existing holding by account and entered symbol."""
    if df.empty or not account or not symbol:
        return None

    entered = symbol.strip().upper()
    filtered_df = df[df["Account"].astype(str) == account]
    exact_matches = []
    base_matches = []

    for _, row in filtered_df.iterrows():
        canonical = str(row["StockSymbol"]).strip().upper()
        if entered == canonical:
            exact_matches.append(row.to_dict())
            continue
        if "." not in entered and entered == canonical.split(".", 1)[0]:
            base_matches.append(row.to_dict())

    if exact_matches:
        return exact_matches[0]
    if len(base_matches) == 1:
        return base_matches[0]

    return None


def add_row_numbers(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with one-based display row numbers."""
    display_df = df.copy()
    display_df.insert(0, "#", range(1, len(display_df) + 1))
    return display_df


def build_holding_summary(
    symbol: str, name: str, detail: Optional[str] = None
) -> str:
    """Build the bold grouped Name/Symbol/detail summary shown in forms."""
    suffix = f"{detail}" if detail else ""
    return f"**📊 {symbol} - {name}{suffix}**"


def calculate_cost_per_share(quantity, book_cost) -> Optional[float]:
    """Calculate cost/share for a pre-populated holding when inputs are valid."""
    try:
        quantity_value = int(quantity)
        book_cost_value = float(book_cost)
    except (TypeError, ValueError):
        return None

    if quantity_value <= 0 or book_cost_value <= 0:
        return None
    return book_cost_value / quantity_value


def build_trade_quantity_context(
    trade_type: str, account: str, stock_symbol: str
) -> tuple[str, str, str]:
    """Build the identity that controls when trade quantity should reset."""
    return (
        str(trade_type or "").strip().upper(),
        str(account or "").strip(),
        str(stock_symbol or "").strip().upper(),
    )


def normalize_trade_quantity_state(
    session_state,
    context: tuple[str, str, str],
    quantity_key: str = "shares_input",
    context_key: str = "shares_input_context",
) -> bool:
    """
    Reset trade quantity to integer 1 when the selected trade context changes.

    Returns True when a reset happened. Same-context reruns, including preview
    submissions, keep the user's current quantity.
    """
    previous_context = session_state.get(context_key)
    if previous_context != context:
        session_state[quantity_key] = 1
        session_state[context_key] = context
        return True

    value = session_state.get(quantity_key, 1)
    try:
        session_state[quantity_key] = max(1, int(value))
    except (TypeError, ValueError):
        session_state[quantity_key] = 1
    return False


TRADE_ENTRY_STATE_KEYS = [
    "trade_account",
    "trade_new_account",
    "buy_stock_symbol",
    "buy_stock_name",
    "sell_stock_select",
    "shares_input",
    "shares_input_context",
    "trade_price_per_share",
    "trade_commission",
]

PREPOPULATE_STATE_KEYS = [
    "prepopulate_account",
    "prepopulate_new_account",
    "prepopulate_stock_symbol",
    "prepopulate_quantity",
    "prepopulate_book_cost",
    "prepopulate_date",
]


def reset_trade_entry_state(session_state) -> None:
    """Clear trade-entry widgets after a successful processed trade."""
    for key in TRADE_ENTRY_STATE_KEYS:
        session_state.pop(key, None)


def reset_prepopulate_state(session_state) -> None:
    """Clear pre-populate widgets after a successful add."""
    for key in PREPOPULATE_STATE_KEYS:
        session_state.pop(key, None)

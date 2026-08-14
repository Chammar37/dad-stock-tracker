"""Pure helpers used by the Streamlit views and their tests."""

from typing import Optional

import pandas as pd


BUTTON_STYLES_CSS = """
<style>
    :root {
        --dst-bg: #0b1020;
        --dst-surface: #121a2c;
        --dst-surface-raised: #172136;
        --dst-border: #293550;
        --dst-text: #f4f7fb;
        --dst-muted: #9aa8bd;
        --dst-brand: #6366f1;
        --dst-brand-hover: #7c83f7;
        --dst-positive: #34d399;
        --dst-negative: #f87171;
        --dst-radius: 12px;
    }

    /* Application shell */
    .stApp {
        background: var(--dst-bg);
        color: var(--dst-text);
    }
    [data-testid="stAppViewContainer"] > .main .block-container {
        max-width: 1440px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }
    [data-testid="stSidebar"] {
        background: #0e1526;
        border-right: 1px solid var(--dst-border);
    }
    [data-testid="stSidebar"] [data-testid="stHeadingWithActionElements"] h1 {
        font-size: 1.22rem !important;
        line-height: 1.3 !important;
        letter-spacing: -0.02em !important;
    }
    h1, h2, h3, [data-testid="stMarkdownContainer"] strong {
        color: var(--dst-text);
    }
    h1 {
        font-size: clamp(1.8rem, 3vw, 2.35rem) !important;
        letter-spacing: -0.035em !important;
        margin-bottom: 0.2rem !important;
    }
    h2, h3 {
        letter-spacing: -0.02em !important;
    }
    h3 {
        font-size: 1.08rem !important;
        margin-top: 0.65rem !important;
    }
    [data-testid="stCaptionContainer"],
    [data-testid="stMarkdownContainer"] p {
        color: var(--dst-muted);
    }

    /* Panels, forms, and table containment */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--dst-border) !important;
        border-radius: var(--dst-radius) !important;
        background: var(--dst-surface) !important;
    }
    [data-testid="stForm"] {
        padding: 1.25rem !important;
        border: 1px solid var(--dst-border) !important;
        border-radius: var(--dst-radius) !important;
        background: var(--dst-surface) !important;
    }
    [data-testid="stDataFrame"],
    [data-testid="stPlotlyChart"] {
        border: 1px solid var(--dst-border);
        border-radius: var(--dst-radius);
        overflow: hidden;
        background: var(--dst-surface);
    }
    [data-testid="stPlotlyChart"] .modebar {
        padding: 0.25rem !important;
        border: 1px solid var(--dst-border) !important;
        border-radius: 8px !important;
        background: rgba(18, 26, 44, 0.92) !important;
    }
    [data-testid="stPlotlyChart"] .modebar-btn path {
        fill: var(--dst-muted) !important;
    }
    [data-testid="stPlotlyChart"] .modebar-btn:hover path {
        fill: var(--dst-text) !important;
    }
    [data-testid="stAlert"] {
        border-radius: 10px;
        border-width: 1px;
    }

    /* Financial metric cards */
    [data-testid="stMetric"] {
        min-height: 112px;
        padding: 1rem 1.1rem;
        border: 1px solid var(--dst-border);
        border-radius: var(--dst-radius);
        background: var(--dst-surface);
    }
    [data-testid="stMetricLabel"] {
        color: var(--dst-muted);
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.025em;
    }
    [data-testid="stMetricValue"] {
        color: var(--dst-text);
        font-variant-numeric: tabular-nums;
        letter-spacing: -0.025em;
    }

    /* Inputs */
    [data-baseweb="select"] > div,
    [data-baseweb="input"] > div,
    [data-testid="stDateInput"] [data-baseweb="input"] > div {
        border-color: var(--dst-border) !important;
        border-radius: 9px !important;
        background: var(--dst-surface-raised) !important;
    }
    [data-baseweb="select"] > div:focus-within,
    [data-baseweb="input"] > div:focus-within {
        border-color: var(--dst-brand) !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.28) !important;
    }

    /* Stable button semantics: primary, neutral secondary, destructive tertiary. */
    button[kind^="primary"] {
        background-color: var(--dst-brand) !important;
        color: white !important;
        border: 1px solid var(--dst-brand) !important;
        border-radius: 9px !important;
        font-weight: 650 !important;
        min-height: 2.65rem;
    }
    button[kind^="primary"]:hover {
        background-color: var(--dst-brand-hover) !important;
        border-color: var(--dst-brand-hover) !important;
    }
    button[kind^="secondary"] {
        background-color: var(--dst-surface-raised) !important;
        color: var(--dst-text) !important;
        border: 1px solid var(--dst-border) !important;
        border-radius: 9px !important;
        font-weight: 600 !important;
        min-height: 2.65rem;
    }
    button[kind^="secondary"]:hover {
        border-color: var(--dst-brand) !important;
        color: white !important;
    }
    button[kind^="tertiary"] {
        background-color: rgba(248, 113, 113, 0.12) !important;
        color: #fecaca !important;
        border: 1px solid rgba(248, 113, 113, 0.55) !important;
        border-radius: 9px !important;
        font-weight: 650 !important;
        min-height: 2.65rem;
    }
    button[kind^="tertiary"]:hover {
        background-color: rgba(248, 113, 113, 0.22) !important;
        border-color: var(--dst-negative) !important;
    }
    button:focus-visible {
        outline: 3px solid rgba(129, 140, 248, 0.72) !important;
        outline-offset: 2px !important;
    }

    /* Numeric values are entered directly; hide increment/decrement steppers. */
    div[data-testid="stNumberInput"] button {
        display: none !important;
    }

    @media (max-width: 1150px) and (min-width: 641px) {
        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) {
            flex-wrap: wrap;
        }
        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"])
        > [data-testid="stColumn"] {
            flex: 1 1 calc(50% - 0.5rem) !important;
            min-width: 240px !important;
        }
    }

    @media (max-width: 640px) {
        [data-testid="stAppViewContainer"] > .main .block-container {
            width: 100%;
            max-width: 100%;
            padding: 1.25rem 1rem 3rem;
        }
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap;
            gap: 0.75rem;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            flex: 1 1 100% !important;
            width: 100% !important;
            min-width: 0 !important;
        }
        [data-testid="stMetric"] {
            min-height: 96px;
        }
        [data-testid="stDataFrame"],
        [data-testid="stPlotlyChart"] {
            max-width: 100%;
        }
        h1 {
            font-size: 1.75rem !important;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            scroll-behavior: auto !important;
            transition-duration: 0.01ms !important;
            animation-duration: 0.01ms !important;
        }
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

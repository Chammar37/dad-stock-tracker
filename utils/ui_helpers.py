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

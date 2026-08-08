"""Streamlit AppTest coverage for stateful UI flows."""

from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
TRADE_COLUMNS = [
    "Account", "StockName", "StockSymbol", "DateOfTrade",
    "TradeType", "SharesTraded", "PricePerShare", "Commission",
    "Cost", "GrossProceeds", "NetProceeds",
    "AverageCostAtSale", "CapitalGainLoss",
]
CONSOLIDATED_COLUMNS = [
    "Account", "StockName", "StockSymbol", "Quantity",
    "AveragePricePerShare", "CapitalGainLoss", "DateOfAcquisition",
]


class FakeTicker:
    """Small yfinance stand-in for deterministic symbol resolution."""

    def __init__(self, symbol):
        self.symbol = symbol

    @property
    def info(self):
        if self.symbol in {"AAPL.TO", "AAPL"}:
            return {"shortName": "Apple Inc."}
        return {}


def write_data_files(tmp_path, consolidated_rows):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    pd.DataFrame(consolidated_rows, columns=CONSOLIDATED_COLUMNS).to_csv(
        data_dir / "consolidated.csv", index=False
    )
    pd.DataFrame(columns=TRADE_COLUMNS).to_csv(data_dir / "trades.csv", index=False)


def test_sell_selectbox_uses_symbol_string_value(tmp_path, monkeypatch):
    write_data_files(tmp_path, [{
        "Account": "TFSA",
        "StockName": "Apple Inc.",
        "StockSymbol": "AAPL",
        "Quantity": 10,
        "AveragePricePerShare": 100.0,
        "CapitalGainLoss": 0.0,
        "DateOfAcquisition": "2024-01-01",
    }])
    monkeypatch.chdir(tmp_path)

    app = AppTest.from_file(APP_PATH, default_timeout=5).run()
    app.sidebar.selectbox[0].set_value("Trade Entry")
    app = app.run()
    app.selectbox[0].set_value("S")
    app = app.run()
    app.selectbox[2].set_value("AAPL")
    app = app.run()

    assert not app.exception
    assert app.selectbox[2].value == "AAPL"
    assert app.session_state.filtered_state["sell_stock_select"] == "AAPL"
    assert app.session_state.filtered_state["shares_input_context"] == (
        "S", "TFSA", "AAPL"
    )


def test_prepopulate_updates_cost_summary_and_resets_after_success(
    tmp_path, monkeypatch
):
    write_data_files(tmp_path, [])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("yfinance.Ticker", FakeTicker)

    app = AppTest.from_file(APP_PATH, default_timeout=5).run()
    app.sidebar.selectbox[0].set_value("Pre-populate Database")
    app = app.run()
    app.text_input[0].set_value("TFSA")
    app = app.run()
    app.text_input[1].set_value("AAPL")
    app = app.run()
    app.number_input[0].set_value(20)
    app = app.run()
    app.number_input[1].set_value(3000.0)
    app = app.run()

    assert any(
        "**📊 AAPL.TO - Apple Inc. @ $150.00/share**" == markdown.value
        for markdown in app.markdown
    )

    app.button[0].click()
    app = app.run()

    assert not app.exception
    assert any("Holding added successfully!" in success.value for success in app.success)
    assert app.text_input[0].label == "Stock Symbol"
    assert app.text_input[0].value == ""
    assert app.number_input[0].value == 0
    assert app.number_input[1].value == 0.0

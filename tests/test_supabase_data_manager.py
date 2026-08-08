from datetime import date

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

from utils.calculations import TradeCalculator
from utils.supabase_data_manager import SupabaseDataManager


@pytest.fixture
def sqlite_engine():
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as connection:
        connection.execute(text("""
            create table holdings (
                id integer primary key autoincrement,
                account text not null,
                stock_name text not null,
                stock_symbol text not null,
                quantity integer not null default 0,
                average_price_per_share numeric not null default 0,
                capital_gain_loss numeric not null default 0,
                date_of_acquisition date,
                created_at timestamp not null default current_timestamp,
                updated_at timestamp not null default current_timestamp,
                unique (account, stock_symbol)
            )
        """))
        connection.execute(text("""
            create table trades (
                id integer primary key autoincrement,
                account text not null,
                stock_name text not null,
                stock_symbol text not null,
                date_of_trade date,
                trade_type text not null check (trade_type in ('B', 'S', 'T')),
                shares_traded integer not null check (shares_traded > 0),
                price_per_share numeric not null,
                commission numeric not null default 0,
                cost numeric,
                gross_proceeds numeric,
                net_proceeds numeric,
                average_cost_at_sale numeric,
                capital_gain_loss numeric,
                created_at timestamp not null default current_timestamp
            )
        """))
    return engine


@pytest.fixture
def supabase_manager(sqlite_engine):
    return SupabaseDataManager(engine=sqlite_engine)


def test_supabase_manager_reads_and_writes_same_interface(supabase_manager):
    holding = {
        "StockName": "Apple Inc.",
        "Quantity": 100,
        "AveragePricePerShare": 150.50,
        "CapitalGainLoss": 0.0,
        "DateOfAcquisition": "2024-01-15",
    }
    assert supabase_manager.update_consolidated_record("TFSA", "AAPL", holding)
    assert supabase_manager.add_trade({
        "Account": "TFSA",
        "StockName": "Apple Inc.",
        "StockSymbol": "AAPL",
        "DateOfTrade": "2024-01-15",
        "TradeType": "B",
        "SharesTraded": 100,
        "PricePerShare": 150.00,
        "Commission": 9.99,
        "Cost": 15009.99,
    })

    consolidated = supabase_manager.read_consolidated()
    trades = supabase_manager.read_trades()

    assert list(consolidated.columns) == SupabaseDataManager.consolidated_headers()
    assert list(trades.columns) == SupabaseDataManager.trade_headers()
    assert consolidated.iloc[0]["Quantity"] == 100
    assert trades.iloc[0]["StockSymbol"] == "AAPL"
    assert abs(trades.iloc[0]["Cost"] - 15009.99) < 0.01


def test_valid_trade_and_holding_update_commit_together(supabase_manager):
    calculator = TradeCalculator(supabase_manager)
    trade = {
        "Account": "TFSA",
        "StockName": "Tesla Inc.",
        "StockSymbol": "TSLA",
        "DateOfTrade": date.today().strftime("%Y-%m-%d"),
        "TradeType": "B",
        "SharesTraded": 10,
        "PricePerShare": 250.00,
        "Commission": 9.99,
    }

    success, message = calculator.process_trade(trade)

    assert success, message
    assert len(supabase_manager.read_consolidated()) == 1
    assert len(supabase_manager.read_trades()) == 1
    assert supabase_manager.get_consolidated_record("TFSA", "TSLA")["Quantity"] == 10


def test_failed_trade_history_insert_rolls_back_holding_update(supabase_manager, monkeypatch):
    calculator = TradeCalculator(supabase_manager)
    trade = {
        "Account": "TFSA",
        "StockName": "Tesla Inc.",
        "StockSymbol": "TSLA",
        "DateOfTrade": date.today().strftime("%Y-%m-%d"),
        "TradeType": "B",
        "SharesTraded": 10,
        "PricePerShare": 250.00,
        "Commission": 9.99,
    }
    monkeypatch.setattr(supabase_manager, "add_trade", lambda trade_data: False)

    success, message = calculator.process_trade(trade)

    assert not success
    assert "Failed to record trade" in message
    assert supabase_manager.read_consolidated().empty
    assert supabase_manager.read_trades().empty


def test_invalid_sell_does_not_insert_trade(supabase_manager):
    calculator = TradeCalculator(supabase_manager)
    assert supabase_manager.update_consolidated_record("TFSA", "AAPL", {
        "StockName": "Apple Inc.",
        "Quantity": 10,
        "AveragePricePerShare": 150.00,
        "CapitalGainLoss": 0.0,
        "DateOfAcquisition": "2024-01-15",
    })

    success, message = calculator.process_trade({
        "Account": "TFSA",
        "StockName": "Apple Inc.",
        "StockSymbol": "AAPL",
        "DateOfTrade": date.today().strftime("%Y-%m-%d"),
        "TradeType": "S",
        "SharesTraded": 11,
        "PricePerShare": 175.00,
        "Commission": 9.99,
    })

    assert not success
    assert "Insufficient shares" in message
    assert supabase_manager.read_trades().empty
    assert supabase_manager.get_consolidated_record("TFSA", "AAPL")["Quantity"] == 10


def test_write_methods_replace_existing_rows(supabase_manager):
    consolidated = pd.DataFrame([{
        "Account": "TFSA",
        "StockName": "Apple Inc.",
        "StockSymbol": "AAPL",
        "Quantity": 100,
        "AveragePricePerShare": 150.50,
        "CapitalGainLoss": 0.0,
        "DateOfAcquisition": "2024-01-15",
    }])
    trades = pd.DataFrame([{
        "Account": "TFSA",
        "StockName": "Apple Inc.",
        "StockSymbol": "AAPL",
        "DateOfTrade": "2024-01-15",
        "TradeType": "B",
        "SharesTraded": 100,
        "PricePerShare": 150.00,
        "Commission": 9.99,
    }])

    assert supabase_manager.write_consolidated(consolidated)
    assert supabase_manager.write_trades(trades)

    assert len(supabase_manager.read_consolidated()) == 1
    assert len(supabase_manager.read_trades()) == 1


def test_write_methods_preserve_unknown_legacy_dates(supabase_manager):
    consolidated = pd.DataFrame([{
        "Account": "TFSA",
        "StockName": "Apple Inc.",
        "StockSymbol": "AAPL",
        "Quantity": 100,
        "AveragePricePerShare": 150.50,
        "CapitalGainLoss": 0.0,
        "DateOfAcquisition": pd.NaT,
    }])
    trades = pd.DataFrame([{
        "Account": "TFSA",
        "StockName": "Apple Inc.",
        "StockSymbol": "AAPL",
        "DateOfTrade": pd.NaT,
        "TradeType": "B",
        "SharesTraded": 100,
        "PricePerShare": 150.00,
        "Commission": 9.99,
    }])

    assert supabase_manager.write_consolidated(consolidated)
    assert supabase_manager.write_trades(trades)
    assert pd.isna(supabase_manager.read_consolidated().iloc[0]["DateOfAcquisition"])
    assert pd.isna(supabase_manager.read_trades().iloc[0]["DateOfTrade"])

from contextlib import contextmanager
from datetime import date
from decimal import Decimal
import os
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from .data_manager import DataManager


class SupabaseDataManager:
    """SQLAlchemy-backed DataManager implementation for Supabase Postgres."""

    HOLDING_COLUMNS = [
        "Account", "StockName", "StockSymbol", "Quantity",
        "AveragePricePerShare", "CapitalGainLoss", "DateOfAcquisition"
    ]
    TRADE_COLUMNS = DataManager.trade_headers()

    HOLDING_SELECT = """
        select
            account as "Account",
            stock_name as "StockName",
            stock_symbol as "StockSymbol",
            quantity as "Quantity",
            average_price_per_share as "AveragePricePerShare",
            capital_gain_loss as "CapitalGainLoss",
            date_of_acquisition as "DateOfAcquisition"
        from holdings
    """
    TRADE_SELECT_BASE = """
        select
            account as "Account",
            stock_name as "StockName",
            stock_symbol as "StockSymbol",
            date_of_trade as "DateOfTrade",
            trade_type as "TradeType",
            shares_traded as "SharesTraded",
            price_per_share as "PricePerShare",
            commission as "Commission",
            cost as "Cost",
            gross_proceeds as "GrossProceeds",
            net_proceeds as "NetProceeds",
            average_cost_at_sale as "AverageCostAtSale",
            capital_gain_loss as "CapitalGainLoss"
        from trades
    """
    TRADE_SELECT = TRADE_SELECT_BASE + " order by id"

    def __init__(self, engine=None, connection_name: str = "supabase"):
        self.connection_name = connection_name
        self.engine = engine or self._load_engine_from_streamlit()
        self._active_connection = None

    def _load_engine_from_streamlit(self):
        load_dotenv()
        try:
            connection = st.connection(self.connection_name, type="sql")
            if hasattr(connection, "engine"):
                return connection.engine
        except Exception:
            pass

        try:
            url = (
                st.secrets.get("connections", {})
                .get(self.connection_name, {})
                .get("url")
            )
        except Exception:
            url = None
        url = url or os.environ.get("SUPABASE_DATABASE_URL")
        if not url:
            raise RuntimeError(
                "Supabase storage is selected but neither connections.supabase.url "
                "nor SUPABASE_DATABASE_URL is configured"
            )
        return create_engine(url)

    @contextmanager
    def transaction(self):
        if self._active_connection is not None:
            yield self
            return

        with self.engine.begin() as connection:
            self._active_connection = connection
            try:
                yield self
            finally:
                self._active_connection = None

    def _execute(self, statement, params=None):
        connection = self._active_connection
        if connection is not None:
            return connection.execute(statement, params or {})

        with self.engine.begin() as transient_connection:
            return transient_connection.execute(statement, params or {})

    def _read_sql(self, query: str, params=None) -> pd.DataFrame:
        connection = self._active_connection or self.engine
        return pd.read_sql_query(text(query), connection, params=params or {})

    @staticmethod
    def _to_date_value(value):
        if value is None or pd.isna(value):
            return None
        if isinstance(value, pd.Timestamp):
            return value.date()
        if isinstance(value, date):
            return value
        return pd.to_datetime(value, errors="coerce").date()

    @staticmethod
    def _clean_value(value):
        if value is None or pd.isna(value):
            return None
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, pd.Timestamp):
            return value.date()
        return value

    @staticmethod
    def consolidated_headers() -> List[str]:
        return DataManager.consolidated_headers()

    @staticmethod
    def trade_headers() -> List[str]:
        return DataManager.trade_headers()

    def read_consolidated(self) -> pd.DataFrame:
        try:
            df = self._read_sql(self.HOLDING_SELECT)
            for column in self.HOLDING_COLUMNS:
                if column not in df.columns:
                    df[column] = pd.NA
            if "DateOfAcquisition" in df.columns:
                df["DateOfAcquisition"] = pd.to_datetime(df["DateOfAcquisition"], errors="coerce")
            if "Quantity" in df.columns:
                df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0).round().astype(int)
            for column in ["AveragePricePerShare", "CapitalGainLoss"]:
                if column in df.columns:
                    df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0).astype(float)
            return df[self.HOLDING_COLUMNS]
        except Exception as e:
            st.error(f"Error reading consolidated data: {e}")
            return pd.DataFrame(columns=self.HOLDING_COLUMNS)

    def read_trades(self) -> pd.DataFrame:
        try:
            df = self._read_sql(self.TRADE_SELECT)
            for column in self.TRADE_COLUMNS:
                if column not in df.columns:
                    df[column] = pd.NA
            if "DateOfTrade" in df.columns:
                df["DateOfTrade"] = pd.to_datetime(df["DateOfTrade"], errors="coerce")
            if "SharesTraded" in df.columns:
                df["SharesTraded"] = pd.to_numeric(df["SharesTraded"], errors="coerce").fillna(0).round().astype(int)
            for column in [
                "PricePerShare", "Commission", "Cost", "GrossProceeds",
                "NetProceeds", "AverageCostAtSale", "CapitalGainLoss"
            ]:
                if column in df.columns:
                    df[column] = pd.to_numeric(df[column], errors="coerce")
            return df[self.TRADE_COLUMNS]
        except Exception as e:
            st.error(f"Error reading trades data: {e}")
            return pd.DataFrame(columns=self.TRADE_COLUMNS)

    def write_consolidated(self, df: pd.DataFrame) -> bool:
        try:
            with self.transaction():
                self._execute(text("delete from holdings"))
                for _, row in df.iterrows():
                    success = self.update_consolidated_record(
                        row["Account"],
                        row["StockSymbol"],
                        {
                            "StockName": row["StockName"],
                            "Quantity": int(row["Quantity"]),
                            "AveragePricePerShare": float(row["AveragePricePerShare"]),
                            "CapitalGainLoss": float(row.get("CapitalGainLoss", 0)),
                            "DateOfAcquisition": row["DateOfAcquisition"],
                        },
                    )
                    if not success:
                        raise RuntimeError("Failed to write consolidated row")
            return True
        except Exception as e:
            st.error(f"Error writing consolidated data: {e}")
            return False

    def write_trades(self, df: pd.DataFrame) -> bool:
        try:
            with self.transaction():
                self._execute(text("delete from trades"))
                for _, row in df.iterrows():
                    if not self.add_trade(row.to_dict()):
                        raise RuntimeError("Failed to write trade row")
            return True
        except Exception as e:
            st.error(f"Error writing trades data: {e}")
            return False

    def add_trade(self, trade_data: Dict) -> bool:
        try:
            if "DateOfTrade" not in trade_data or not trade_data["DateOfTrade"]:
                st.error("Trade date is required and cannot be empty")
                return False

            self._execute(
                text("""
                    insert into trades (
                        account, stock_name, stock_symbol, date_of_trade, trade_type,
                        shares_traded, price_per_share, commission, cost,
                        gross_proceeds, net_proceeds, average_cost_at_sale,
                        capital_gain_loss
                    ) values (
                        :account, :stock_name, :stock_symbol, :date_of_trade, :trade_type,
                        :shares_traded, :price_per_share, :commission, :cost,
                        :gross_proceeds, :net_proceeds, :average_cost_at_sale,
                        :capital_gain_loss
                    )
                """),
                {
                    "account": trade_data.get("Account"),
                    "stock_name": trade_data.get("StockName"),
                    "stock_symbol": trade_data.get("StockSymbol"),
                    "date_of_trade": self._to_date_value(trade_data.get("DateOfTrade")),
                    "trade_type": str(trade_data.get("TradeType", "")).upper(),
                    "shares_traded": int(trade_data.get("SharesTraded")),
                    "price_per_share": float(trade_data.get("PricePerShare")),
                    "commission": float(trade_data.get("Commission", 0)),
                    "cost": self._clean_value(trade_data.get("Cost")),
                    "gross_proceeds": self._clean_value(trade_data.get("GrossProceeds")),
                    "net_proceeds": self._clean_value(trade_data.get("NetProceeds")),
                    "average_cost_at_sale": self._clean_value(trade_data.get("AverageCostAtSale")),
                    "capital_gain_loss": self._clean_value(trade_data.get("CapitalGainLoss")),
                },
            )
            return True
        except Exception as e:
            st.error(f"Error adding trade: {e}")
            return False

    def delete_trade(self, trade_index: int) -> bool:
        try:
            trade_id = self._trade_id_at_index(trade_index)
            if trade_id is None:
                st.error(f"Invalid trade index: {trade_index}")
                return False
            self._execute(text("delete from trades where id = :id"), {"id": trade_id})
            return True
        except Exception as e:
            st.error(f"Error deleting trade: {e}")
            return False

    def _trade_id_at_index(self, trade_index: int) -> Optional[int]:
        if trade_index < 0:
            return None
        df = self._read_sql("select id from trades order by id")
        if trade_index >= len(df):
            return None
        return int(df.iloc[trade_index]["id"])

    def get_trade_at_index(self, trade_index: int) -> Optional[Dict]:
        try:
            trades_df = self.read_trades()
            if trade_index < 0 or trade_index >= len(trades_df):
                return None
            return trades_df.loc[trade_index].to_dict()
        except Exception as e:
            st.error(f"Error getting trade: {e}")
            return None

    def delete_consolidated_record(self, account: str, stock_symbol: str) -> bool:
        try:
            result = self._execute(
                text("delete from holdings where account = :account and stock_symbol = :stock_symbol"),
                {"account": account, "stock_symbol": stock_symbol},
            )
            if result.rowcount == 0:
                st.error(f"Consolidated record not found for {stock_symbol} in {account}")
                return False
            return True
        except Exception as e:
            st.error(f"Error deleting consolidated record: {e}")
            return False

    def validate_consolidated_record(self, record_data: Dict) -> tuple[bool, str]:
        return DataManager.validate_consolidated_record(self, record_data)

    def get_trades_for_account_symbol(self, account: str, stock_symbol: str) -> pd.DataFrame:
        try:
            df = self._read_sql(
                self.TRADE_SELECT_BASE + """
                    where account = :account and stock_symbol = :stock_symbol
                    order by date_of_trade, id
                """,
                {"account": account, "stock_symbol": stock_symbol},
            )
            for column in self.TRADE_COLUMNS:
                if column not in df.columns:
                    df[column] = pd.NA
            if "DateOfTrade" in df.columns:
                df["DateOfTrade"] = pd.to_datetime(df["DateOfTrade"], errors="coerce")
            if "SharesTraded" in df.columns:
                df["SharesTraded"] = pd.to_numeric(df["SharesTraded"], errors="coerce").fillna(0).round().astype(int)
            for column in [
                "PricePerShare", "Commission", "Cost", "GrossProceeds",
                "NetProceeds", "AverageCostAtSale", "CapitalGainLoss"
            ]:
                if column in df.columns:
                    df[column] = pd.to_numeric(df[column], errors="coerce")
            return df[self.TRADE_COLUMNS]
        except Exception as e:
            st.error(f"Error getting trades for account/symbol: {e}")
            return pd.DataFrame(columns=self.TRADE_COLUMNS)

    def update_consolidated_record(self, account: str, stock_symbol: str, updated_data: Dict) -> bool:
        try:
            if "DateOfAcquisition" in updated_data and not updated_data["DateOfAcquisition"]:
                st.error("Date of acquisition is required and cannot be empty")
                return False

            candidate = {"Account": account, "StockSymbol": stock_symbol, **updated_data}
            is_valid, error = self.validate_consolidated_record(candidate)
            if not is_valid:
                st.error(error)
                return False

            existing = self.get_consolidated_record(account, stock_symbol)
            params = {
                "account": account,
                "stock_name": updated_data["StockName"],
                "stock_symbol": stock_symbol,
                "quantity": int(updated_data["Quantity"]),
                "average_price_per_share": float(updated_data["AveragePricePerShare"]),
                "capital_gain_loss": float(updated_data.get("CapitalGainLoss", 0)),
                "date_of_acquisition": self._to_date_value(updated_data["DateOfAcquisition"]),
            }
            if existing:
                self._execute(
                    text("""
                        update holdings
                        set stock_name = :stock_name,
                            quantity = :quantity,
                            average_price_per_share = :average_price_per_share,
                            capital_gain_loss = :capital_gain_loss,
                            date_of_acquisition = :date_of_acquisition,
                            updated_at = current_timestamp
                        where account = :account and stock_symbol = :stock_symbol
                    """),
                    params,
                )
            else:
                self._execute(
                    text("""
                        insert into holdings (
                            account, stock_name, stock_symbol, quantity,
                            average_price_per_share, capital_gain_loss,
                            date_of_acquisition
                        ) values (
                            :account, :stock_name, :stock_symbol, :quantity,
                            :average_price_per_share, :capital_gain_loss,
                            :date_of_acquisition
                        )
                    """),
                    params,
                )
            return True
        except Exception as e:
            st.error(f"Error updating consolidated record: {e}")
            return False

    def replace_consolidated_record(
        self,
        old_account: str,
        old_stock_symbol: str,
        new_account: str,
        new_stock_symbol: str,
        updated_data: Dict,
    ) -> bool:
        try:
            candidate = {"Account": new_account, "StockSymbol": new_stock_symbol, **updated_data}
            is_valid, error = self.validate_consolidated_record(candidate)
            if not is_valid:
                st.error(error)
                return False

            existing_old = self.get_consolidated_record(old_account, old_stock_symbol)
            if not existing_old:
                st.error(f"Consolidated record not found for {old_stock_symbol} in {old_account}")
                return False

            same_key = old_account == new_account and old_stock_symbol == new_stock_symbol
            if not same_key and self.get_consolidated_record(new_account, new_stock_symbol):
                st.error(f"Consolidated record already exists for {new_stock_symbol} in {new_account}")
                return False

            self._execute(
                text("""
                    update holdings
                    set account = :new_account,
                        stock_name = :stock_name,
                        stock_symbol = :new_stock_symbol,
                        quantity = :quantity,
                        average_price_per_share = :average_price_per_share,
                        capital_gain_loss = :capital_gain_loss,
                        date_of_acquisition = :date_of_acquisition,
                        updated_at = current_timestamp
                    where account = :old_account and stock_symbol = :old_stock_symbol
                """),
                {
                    "old_account": old_account,
                    "old_stock_symbol": old_stock_symbol,
                    "new_account": new_account,
                    "new_stock_symbol": new_stock_symbol,
                    "stock_name": updated_data["StockName"],
                    "quantity": int(updated_data["Quantity"]),
                    "average_price_per_share": float(updated_data["AveragePricePerShare"]),
                    "capital_gain_loss": float(updated_data.get("CapitalGainLoss", 0)),
                    "date_of_acquisition": self._to_date_value(updated_data["DateOfAcquisition"]),
                },
            )
            return True
        except Exception as e:
            st.error(f"Error replacing consolidated record: {e}")
            return False

    def get_consolidated_record(self, account: str, stock_symbol: str) -> Optional[Dict]:
        try:
            df = self._read_sql(
                self.HOLDING_SELECT + """
                    where account = :account and stock_symbol = :stock_symbol
                """,
                {"account": account, "stock_symbol": stock_symbol},
            )
            if df.empty:
                return None
            row = df.iloc[0].to_dict()
            return {key: self._clean_value(value) for key, value in row.items()}
        except Exception as e:
            st.error(f"Error getting consolidated record: {e}")
            return None

    def get_accounts(self) -> List[str]:
        try:
            df = self._read_sql("select distinct account from holdings order by account")
            return df["account"].tolist() if not df.empty else []
        except Exception as e:
            st.error(f"Error getting accounts: {e}")
            return []

    def get_stock_symbols(self) -> List[str]:
        try:
            df = self._read_sql("select distinct stock_symbol from holdings order by stock_symbol")
            return df["stock_symbol"].tolist() if not df.empty else []
        except Exception as e:
            st.error(f"Error getting stock symbols: {e}")
            return []

    def migrate_integer_quantities(self) -> bool:
        return True

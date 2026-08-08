import pandas as pd
import os
from typing import Dict, List, Optional
import streamlit as st
from datetime import datetime
from contextlib import contextmanager

class DataManager:
    """Handles all CSV file operations for the stock tracker app."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.consolidated_path = os.path.join(data_dir, "consolidated.csv")
        self.trades_path = os.path.join(data_dir, "trades.csv")
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize CSV files if they don't exist
        self._initialize_files()

    @contextmanager
    def transaction(self):
        """Best-effort atomic block for CSV writes using in-memory snapshots."""
        original_consolidated = self.read_consolidated()
        original_trades = self.read_trades()
        try:
            yield self
        except Exception:
            self.write_consolidated(original_consolidated)
            self.write_trades(original_trades)
            raise
    
    def _initialize_files(self):
        """Initialize CSV files with headers if they don't exist."""
        # Consolidated CSV headers
        consolidated_headers = [
            "Account", "StockName", "StockSymbol", "Quantity", 
            "AveragePricePerShare", "CapitalGainLoss", "DateOfAcquisition"
        ]
        
        # Trades CSV headers
        trades_headers = self.trade_headers()
        
        if not os.path.exists(self.consolidated_path):
            pd.DataFrame(columns=consolidated_headers).to_csv(
                self.consolidated_path, index=False
            )
        
        if not os.path.exists(self.trades_path):
            pd.DataFrame(columns=trades_headers).to_csv(
                self.trades_path, index=False
            )
    

    def read_consolidated(self) -> pd.DataFrame:
        """Read the consolidated holdings data."""
        try:
            df = pd.read_csv(self.consolidated_path)
            # Convert date column to datetime
            if 'DateOfAcquisition' in df.columns:
                df['DateOfAcquisition'] = pd.to_datetime(df['DateOfAcquisition'], errors='coerce')
            # Ensure integer quantities
            if 'Quantity' in df.columns:
                df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0).round().astype(int)
            for column in ['AveragePricePerShare', 'CapitalGainLoss']:
                if column in df.columns:
                    df[column] = pd.to_numeric(df[column], errors='coerce').fillna(0.0).astype(float)
            return df
        except Exception as e:
            st.error(f"Error reading consolidated data: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def consolidated_headers() -> List[str]:
        """Columns used by the consolidated holdings CSV."""
        return [
            "Account", "StockName", "StockSymbol", "Quantity",
            "AveragePricePerShare", "CapitalGainLoss", "DateOfAcquisition"
        ]

    @staticmethod
    def trade_headers() -> List[str]:
        """Columns used by the trade history CSV."""
        return [
            "Account", "StockName", "StockSymbol", "DateOfTrade",
            "TradeType", "SharesTraded", "PricePerShare", "Commission",
            "Cost", "GrossProceeds", "NetProceeds",
            "AverageCostAtSale", "CapitalGainLoss"
        ]

    def read_trades(self) -> pd.DataFrame:
        """Read the trades history data."""
        try:
            df = pd.read_csv(self.trades_path)
            for column in self.trade_headers():
                if column not in df.columns:
                    df[column] = pd.NA
            # Convert date column to datetime
            if 'DateOfTrade' in df.columns:
                df['DateOfTrade'] = pd.to_datetime(df['DateOfTrade'], errors='coerce')
            # Ensure integer shares traded
            if 'SharesTraded' in df.columns:
                df['SharesTraded'] = pd.to_numeric(df['SharesTraded'], errors='coerce').fillna(0).round().astype(int)
            for column in [
                'PricePerShare', 'Commission', 'Cost', 'GrossProceeds',
                'NetProceeds', 'AverageCostAtSale', 'CapitalGainLoss'
            ]:
                if column in df.columns:
                    df[column] = pd.to_numeric(df[column], errors='coerce')
            return df[self.trade_headers()]
        except Exception as e:
            st.error(f"Error reading trades data: {e}")
            return pd.DataFrame()
    
    def write_consolidated(self, df: pd.DataFrame) -> bool:
        """Write consolidated holdings data to CSV."""
        try:
            df.to_csv(self.consolidated_path, index=False)
            return True
        except Exception as e:
            st.error(f"Error writing consolidated data: {e}")
            return False
    
    def write_trades(self, df: pd.DataFrame) -> bool:
        """Write trades data to CSV."""
        try:
            for column in self.trade_headers():
                if column not in df.columns:
                    df[column] = pd.NA
            df = df[self.trade_headers()]
            df.to_csv(self.trades_path, index=False)
            return True
        except Exception as e:
            st.error(f"Error writing trades data: {e}")
            return False
    
    def add_trade(self, trade_data: Dict) -> bool:
        """Add a new trade to the trades CSV."""
        try:
            # Validate that DateOfTrade exists and is not empty
            if 'DateOfTrade' not in trade_data or not trade_data['DateOfTrade']:
                st.error("Trade date is required and cannot be empty")
                return False

            trades_df = self.read_trades()
            new_trade = pd.DataFrame([trade_data])
            updated_trades = pd.concat([trades_df, new_trade], ignore_index=True)
            return self.write_trades(updated_trades)
        except Exception as e:
            st.error(f"Error adding trade: {e}")
            return False

    def delete_trade(self, trade_index: int) -> bool:
        """Delete a trade by its index in the trades CSV."""
        try:
            trades_df = self.read_trades()
            if trade_index < 0 or trade_index >= len(trades_df):
                st.error(f"Invalid trade index: {trade_index}")
                return False

            # Remove the trade at the specified index
            updated_trades = trades_df.drop(index=trade_index).reset_index(drop=True)
            return self.write_trades(updated_trades)
        except Exception as e:
            st.error(f"Error deleting trade: {e}")
            return False

    def get_trade_at_index(self, trade_index: int) -> Optional[Dict]:
        """Get a trade by its index."""
        try:
            trades_df = self.read_trades()
            if trade_index < 0 or trade_index >= len(trades_df):
                return None
            return trades_df.loc[trade_index].to_dict()
        except Exception as e:
            st.error(f"Error getting trade: {e}")
            return None

    def delete_consolidated_record(self, account: str, stock_symbol: str) -> bool:
        """Delete a specific consolidated record."""
        try:
            df = self.read_consolidated()
            mask = (df['Account'] == account) & (df['StockSymbol'] == stock_symbol)
            if not mask.any():
                st.error(f"Consolidated record not found for {stock_symbol} in {account}")
                return False
            updated_df = df[~mask]  # Keep everything except this record
            return self.write_consolidated(updated_df)
        except Exception as e:
            st.error(f"Error deleting consolidated record: {e}")
            return False

    def validate_consolidated_record(self, record_data: Dict) -> tuple[bool, str]:
        """Validate editable consolidated-record values before writing."""
        required_text = ["Account", "StockName", "StockSymbol"]
        for field in required_text:
            if not str(record_data.get(field, "")).strip():
                return False, f"{field} is required"

        try:
            quantity = int(record_data.get("Quantity"))
        except (TypeError, ValueError):
            return False, "Quantity must be a whole number"
        if quantity < 0:
            return False, "Quantity cannot be negative"

        try:
            average_price = float(record_data.get("AveragePricePerShare"))
        except (TypeError, ValueError):
            return False, "Average price/share must be a number"
        if average_price < 0:
            return False, "Average price/share cannot be negative"

        try:
            float(record_data.get("CapitalGainLoss", 0))
        except (TypeError, ValueError):
            return False, "Gain/loss must be a number"

        date_value = record_data.get("DateOfAcquisition")
        if not date_value or pd.isna(date_value):
            return False, "Date of acquisition is required"
        if pd.isna(pd.to_datetime(date_value, errors="coerce")):
            return False, "Date of acquisition must be a valid date"

        return True, ""

    def get_trades_for_account_symbol(self, account: str, stock_symbol: str) -> pd.DataFrame:
        """Get all trades for a specific account and stock symbol, sorted by date."""
        try:
            trades_df = self.read_trades()
            mask = (trades_df['Account'] == account) & (trades_df['StockSymbol'] == stock_symbol)
            relevant_trades = trades_df[mask].copy()

            # Sort by date (oldest first)
            if not relevant_trades.empty and 'DateOfTrade' in relevant_trades.columns:
                relevant_trades = relevant_trades.sort_values('DateOfTrade')

            return relevant_trades
        except Exception as e:
            st.error(f"Error getting trades for account/symbol: {e}")
            return pd.DataFrame()
    
    def update_consolidated_record(self, account: str, stock_symbol: str,
                                 updated_data: Dict) -> bool:
        """Update a specific consolidated record."""
        try:
            # Validate that DateOfAcquisition exists and is not empty
            if 'DateOfAcquisition' in updated_data and not updated_data['DateOfAcquisition']:
                st.error("Date of acquisition is required and cannot be empty")
                return False

            candidate = {
                "Account": account,
                "StockSymbol": stock_symbol,
                **updated_data,
            }
            is_valid, error = self.validate_consolidated_record(candidate)
            if not is_valid:
                st.error(error)
                return False

            df = self.read_consolidated()

            # Find the record to update
            mask = (df['Account'] == account) & (df['StockSymbol'] == stock_symbol)

            if mask.any():
                # Update existing record
                for key, value in updated_data.items():
                    df.loc[mask, key] = value
            else:
                # Add new record
                new_record = {
                    'Account': account,
                    'StockSymbol': stock_symbol,
                    **updated_data
                }
                new_df = pd.DataFrame([new_record])
                df = pd.concat([df, new_df], ignore_index=True)

            return self.write_consolidated(df)
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
        """Atomically replace or rename a consolidated record after validation."""
        try:
            candidate = {
                "Account": new_account,
                "StockSymbol": new_stock_symbol,
                **updated_data,
            }
            is_valid, error = self.validate_consolidated_record(candidate)
            if not is_valid:
                st.error(error)
                return False

            df = self.read_consolidated()
            old_mask = (
                (df["Account"] == old_account)
                & (df["StockSymbol"] == old_stock_symbol)
            )
            if not old_mask.any():
                st.error(
                    f"Consolidated record not found for {old_stock_symbol} in {old_account}"
                )
                return False

            new_mask = (
                (df["Account"] == new_account)
                & (df["StockSymbol"] == new_stock_symbol)
            )
            same_key = old_account == new_account and old_stock_symbol == new_stock_symbol
            if not same_key and new_mask.any():
                st.error(
                    f"Consolidated record already exists for {new_stock_symbol} in {new_account}"
                )
                return False

            replacement = {
                "Account": new_account,
                "StockSymbol": new_stock_symbol,
                **updated_data,
            }
            for key, value in replacement.items():
                df.loc[old_mask, key] = value

            return self.write_consolidated(df)
        except Exception as e:
            st.error(f"Error replacing consolidated record: {e}")
            return False
    
    def get_consolidated_record(self, account: str, stock_symbol: str) -> Optional[Dict]:
        """Get a specific consolidated record."""
        try:
            df = self.read_consolidated()
            mask = (df['Account'] == account) & (df['StockSymbol'] == stock_symbol)
            
            if mask.any():
                return df[mask].iloc[0].to_dict()
            return None
        except Exception as e:
            st.error(f"Error getting consolidated record: {e}")
            return None
    
    def get_accounts(self) -> List[str]:
        """Get list of unique accounts."""
        try:
            df = self.read_consolidated()
            return sorted(df['Account'].unique().tolist()) if not df.empty else []
        except Exception as e:
            st.error(f"Error getting accounts: {e}")
            return []
    
    def get_stock_symbols(self) -> List[str]:
        """Get list of unique stock symbols."""
        try:
            df = self.read_consolidated()
            return sorted(df['StockSymbol'].unique().tolist()) if not df.empty else []
        except Exception as e:
            st.error(f"Error getting stock symbols: {e}")
            return []

    def migrate_integer_quantities(self) -> bool:
        """
        One-time migration to ensure all quantities are integers.
        Converts any float quantities to integers in both consolidated and trades CSVs.
        """
        try:
            # Migrate consolidated.csv
            consolidated_df = pd.read_csv(self.consolidated_path)
            if 'Quantity' in consolidated_df.columns:
                consolidated_df['Quantity'] = pd.to_numeric(
                    consolidated_df['Quantity'], errors='coerce'
                ).fillna(0).round().astype(int)
                consolidated_df.to_csv(self.consolidated_path, index=False)

            # Migrate trades.csv
            trades_df = pd.read_csv(self.trades_path)
            if 'SharesTraded' in trades_df.columns:
                trades_df['SharesTraded'] = pd.to_numeric(
                    trades_df['SharesTraded'], errors='coerce'
                ).fillna(0).round().astype(int)
                trades_df.to_csv(self.trades_path, index=False)

            return True
        except Exception as e:
            # Silent fail - this is a one-time migration
            return False

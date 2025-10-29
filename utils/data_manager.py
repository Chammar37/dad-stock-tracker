import pandas as pd
import os
from typing import Dict, List, Optional
import streamlit as st

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
    
    def _initialize_files(self):
        """Initialize CSV files with headers if they don't exist."""
        # Consolidated CSV headers
        consolidated_headers = [
            "Account", "StockName", "StockSymbol", "Quantity", 
            "AveragePricePerShare", "CapitalGainLoss", "DateOfAcquisition"
        ]
        
        # Trades CSV headers
        trades_headers = [
            "Account", "StockName", "StockSymbol", "DateOfTrade", 
            "TradeType", "SharesTraded", "PricePerShare", "Commission"
        ]
        
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
            return df
        except Exception as e:
            st.error(f"Error reading consolidated data: {e}")
            return pd.DataFrame()
    
    def read_trades(self) -> pd.DataFrame:
        """Read the trades history data."""
        try:
            df = pd.read_csv(self.trades_path)
            # Convert date column to datetime
            if 'DateOfTrade' in df.columns:
                df['DateOfTrade'] = pd.to_datetime(df['DateOfTrade'], errors='coerce')
            # Ensure integer shares traded
            if 'SharesTraded' in df.columns:
                df['SharesTraded'] = pd.to_numeric(df['SharesTraded'], errors='coerce').fillna(0).round().astype(int)
            return df
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
            df.to_csv(self.trades_path, index=False)
            return True
        except Exception as e:
            st.error(f"Error writing trades data: {e}")
            return False
    
    def add_trade(self, trade_data: Dict) -> bool:
        """Add a new trade to the trades CSV."""
        try:
            trades_df = self.read_trades()
            new_trade = pd.DataFrame([trade_data])
            updated_trades = pd.concat([trades_df, new_trade], ignore_index=True)
            return self.write_trades(updated_trades)
        except Exception as e:
            st.error(f"Error adding trade: {e}")
            return False
    
    def update_consolidated_record(self, account: str, stock_symbol: str, 
                                 updated_data: Dict) -> bool:
        """Update a specific consolidated record."""
        try:
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

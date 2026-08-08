"""
Tests for DataManager class.
"""
import pytest
import pandas as pd
import os


class TestDataManagerInitialization:
    """Test DataManager initialization and file creation."""

    def test_creates_data_directory(self, temp_data_dir):
        """Test that DataManager creates data directory if it doesn't exist."""
        from utils.data_manager import DataManager
        dm = DataManager(data_dir=temp_data_dir)
        assert os.path.exists(temp_data_dir)

    def test_creates_csv_files(self, data_manager):
        """Test that DataManager creates CSV files with headers."""
        assert os.path.exists(data_manager.consolidated_path)
        assert os.path.exists(data_manager.trades_path)

        # Check files have headers
        consolidated = pd.read_csv(data_manager.consolidated_path)
        trades = pd.read_csv(data_manager.trades_path)

        assert list(consolidated.columns) == [
            'Account', 'StockName', 'StockSymbol', 'Quantity',
            'AveragePricePerShare', 'CapitalGainLoss', 'DateOfAcquisition'
        ]
        assert list(trades.columns) == [
            'Account', 'StockName', 'StockSymbol', 'DateOfTrade',
            'TradeType', 'SharesTraded', 'PricePerShare', 'Commission',
            'Cost', 'GrossProceeds', 'NetProceeds',
            'AverageCostAtSale', 'CapitalGainLoss'
        ]


class TestDataManagerRead:
    """Test reading data from CSV files."""

    def test_read_empty_consolidated(self, data_manager):
        """Test reading empty consolidated file."""
        df = data_manager.read_consolidated()
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_read_empty_trades(self, data_manager):
        """Test reading empty trades file."""
        df = data_manager.read_trades()
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_read_populated_consolidated(self, populated_data_manager):
        """Test reading populated consolidated file."""
        df = populated_data_manager.read_consolidated()
        assert len(df) == 3
        assert df['Quantity'].dtype == int  # Should be integer

    def test_read_populated_trades(self, populated_data_manager):
        """Test reading populated trades file."""
        df = populated_data_manager.read_trades()
        assert len(df) == 3
        assert df['SharesTraded'].dtype == int  # Should be integer


class TestDataManagerWrite:
    """Test writing data to CSV files."""

    def test_write_consolidated(self, data_manager, sample_consolidated_data):
        """Test writing consolidated data."""
        success = data_manager.write_consolidated(sample_consolidated_data)
        assert success

        df = data_manager.read_consolidated()
        assert len(df) == 3
        assert df.iloc[0]['StockSymbol'] == 'AAPL'

    def test_write_trades(self, data_manager, sample_trades_data):
        """Test writing trades data."""
        success = data_manager.write_trades(sample_trades_data)
        assert success

        df = data_manager.read_trades()
        assert len(df) == 3


class TestDataManagerTradeOperations:
    """Test trade-related operations."""

    def test_add_trade(self, data_manager, buy_trade_data):
        """Test adding a trade."""
        success = data_manager.add_trade(buy_trade_data)
        assert success

        trades = data_manager.read_trades()
        assert len(trades) == 1
        assert trades.iloc[0]['StockSymbol'] == 'TSLA'

    def test_add_trade_validates_date(self, data_manager):
        """Test that add_trade validates DateOfTrade exists."""
        invalid_trade = {
            'Account': 'TFSA',
            'StockSymbol': 'AAPL',
            'TradeType': 'B',
            'SharesTraded': 10,
            'PricePerShare': 150.00,
            'Commission': 9.99
            # Missing DateOfTrade
        }
        success = data_manager.add_trade(invalid_trade)
        assert not success

    def test_delete_trade(self, populated_data_manager):
        """Test deleting a trade by index."""
        # Should have 3 trades initially
        trades_before = populated_data_manager.read_trades()
        assert len(trades_before) == 3

        # Delete trade at index 1
        success = populated_data_manager.delete_trade(1)
        assert success

        trades_after = populated_data_manager.read_trades()
        assert len(trades_after) == 2

    def test_delete_trade_invalid_index(self, populated_data_manager):
        """Test deleting trade with invalid index fails gracefully."""
        success = populated_data_manager.delete_trade(999)
        assert not success

    def test_get_trade_at_index(self, populated_data_manager):
        """Test retrieving a trade by index."""
        trade = populated_data_manager.get_trade_at_index(0)
        assert trade is not None
        assert trade['StockSymbol'] == 'AAPL'
        assert trade['TradeType'] == 'B'

    def test_get_trade_at_invalid_index(self, populated_data_manager):
        """Test retrieving trade with invalid index."""
        trade = populated_data_manager.get_trade_at_index(999)
        assert trade is None


class TestDataManagerConsolidatedOperations:
    """Test consolidated record operations."""

    def test_update_consolidated_record_new(self, data_manager):
        """Test updating consolidated record creates new entry."""
        updated_data = {
            'StockName': 'Tesla Inc.',
            'Quantity': 10,
            'AveragePricePerShare': 250.00,
            'CapitalGainLoss': 0.0,
            'DateOfAcquisition': '2024-06-01'
        }

        success = data_manager.update_consolidated_record('TFSA', 'TSLA', updated_data)
        assert success

        df = data_manager.read_consolidated()
        assert len(df) == 1
        assert df.iloc[0]['StockSymbol'] == 'TSLA'

    def test_update_consolidated_record_existing(self, populated_data_manager):
        """Test updating existing consolidated record."""
        updated_data = {
            'StockName': 'Apple Inc.',
            'Quantity': 150,  # Updated from 100
            'AveragePricePerShare': 160.00,  # Updated from 150.50
            'CapitalGainLoss': 100.0,
            'DateOfAcquisition': '2024-01-15'
        }

        success = populated_data_manager.update_consolidated_record('TFSA', 'AAPL', updated_data)
        assert success

        record = populated_data_manager.get_consolidated_record('TFSA', 'AAPL')
        assert record['Quantity'] == 150
        assert record['AveragePricePerShare'] == 160.00

    def test_update_consolidated_validates_date(self, data_manager):
        """Test that update validates DateOfAcquisition."""
        invalid_data = {
            'StockName': 'Tesla Inc.',
            'Quantity': 10,
            'AveragePricePerShare': 250.00,
            'CapitalGainLoss': 0.0,
            'DateOfAcquisition': ''  # Empty date
        }

        success = data_manager.update_consolidated_record('TFSA', 'TSLA', invalid_data)
        assert not success

    def test_update_consolidated_rejects_invalid_quantity(self, data_manager):
        """Test that invalid edited quantity is rejected without writing."""
        invalid_data = {
            'StockName': 'Tesla Inc.',
            'Quantity': -1,
            'AveragePricePerShare': 250.00,
            'CapitalGainLoss': 0.0,
            'DateOfAcquisition': '2024-06-01'
        }

        success = data_manager.update_consolidated_record('TFSA', 'TSLA', invalid_data)

        assert not success
        assert data_manager.read_consolidated().empty

    def test_delete_consolidated_record_rejects_missing_record(self, data_manager):
        """Test deleting a missing consolidated record fails explicitly."""
        success = data_manager.delete_consolidated_record('TFSA', 'MISSING')

        assert not success

    def test_get_consolidated_record(self, populated_data_manager):
        """Test retrieving a consolidated record."""
        record = populated_data_manager.get_consolidated_record('TFSA', 'AAPL')
        assert record is not None
        assert record['Quantity'] == 100
        assert record['AveragePricePerShare'] == 150.50

    def test_get_consolidated_record_not_found(self, populated_data_manager):
        """Test retrieving non-existent record returns None."""
        record = populated_data_manager.get_consolidated_record('TFSA', 'NONEXISTENT')
        assert record is None

    def test_delete_consolidated_record(self, populated_data_manager):
        """Test deleting a consolidated record."""
        # Should have 3 records initially
        df_before = populated_data_manager.read_consolidated()
        assert len(df_before) == 3

        success = populated_data_manager.delete_consolidated_record('TFSA', 'AAPL')
        assert success

        df_after = populated_data_manager.read_consolidated()
        assert len(df_after) == 2

        # Verify AAPL is gone
        record = populated_data_manager.get_consolidated_record('TFSA', 'AAPL')
        assert record is None

    def test_replace_consolidated_record_renames_key_atomically(self, populated_data_manager):
        """Test replacing account/symbol updates one row in a single operation."""
        updated_data = {
            'StockName': 'Apple Canada',
            'Quantity': 100,
            'AveragePricePerShare': 150.50,
            'CapitalGainLoss': 0.0,
            'DateOfAcquisition': '2024-01-15'
        }

        success = populated_data_manager.replace_consolidated_record(
            'TFSA', 'AAPL', 'TFSA', 'AAPL.TO', updated_data
        )

        assert success
        assert populated_data_manager.get_consolidated_record('TFSA', 'AAPL') is None
        replacement = populated_data_manager.get_consolidated_record('TFSA', 'AAPL.TO')
        assert replacement is not None
        assert replacement['StockName'] == 'Apple Canada'

    def test_replace_consolidated_record_rejects_duplicate_destination(self, populated_data_manager):
        """Test duplicate destination account/symbol does not remove the original."""
        updated_data = {
            'StockName': 'Apple Inc.',
            'Quantity': 100,
            'AveragePricePerShare': 150.50,
            'CapitalGainLoss': 0.0,
            'DateOfAcquisition': '2024-01-15'
        }

        success = populated_data_manager.replace_consolidated_record(
            'TFSA', 'AAPL', 'TFSA', 'MSFT', updated_data
        )

        assert not success
        assert populated_data_manager.get_consolidated_record('TFSA', 'AAPL') is not None
        assert populated_data_manager.get_consolidated_record('TFSA', 'MSFT') is not None

    def test_replace_consolidated_record_rejects_invalid_replacement_without_data_loss(self, populated_data_manager):
        """Test invalid replacement data leaves the original row unchanged."""
        updated_data = {
            'StockName': 'Apple Inc.',
            'Quantity': -1,
            'AveragePricePerShare': 150.50,
            'CapitalGainLoss': 0.0,
            'DateOfAcquisition': '2024-01-15'
        }

        success = populated_data_manager.replace_consolidated_record(
            'TFSA', 'AAPL', 'TFSA', 'AAPL.TO', updated_data
        )

        assert not success
        original = populated_data_manager.get_consolidated_record('TFSA', 'AAPL')
        assert original is not None
        assert original['Quantity'] == 100
        assert populated_data_manager.get_consolidated_record('TFSA', 'AAPL.TO') is None

    def test_replace_consolidated_record_write_failure_leaves_original_file(self, populated_data_manager, monkeypatch):
        """Test failed write does not pre-delete the original record."""
        updated_data = {
            'StockName': 'Apple Canada',
            'Quantity': 100,
            'AveragePricePerShare': 150.50,
            'CapitalGainLoss': 0.0,
            'DateOfAcquisition': '2024-01-15'
        }

        monkeypatch.setattr(populated_data_manager, "write_consolidated", lambda df: False)

        success = populated_data_manager.replace_consolidated_record(
            'TFSA', 'AAPL', 'TFSA', 'AAPL.TO', updated_data
        )

        assert not success
        assert populated_data_manager.get_consolidated_record('TFSA', 'AAPL') is not None
        assert populated_data_manager.get_consolidated_record('TFSA', 'AAPL.TO') is None


class TestDataManagerHelpers:
    """Test helper methods."""

    def test_get_accounts(self, populated_data_manager):
        """Test getting list of unique accounts."""
        accounts = populated_data_manager.get_accounts()
        assert isinstance(accounts, list)
        assert 'TFSA' in accounts
        assert 'RRSP' in accounts
        assert len(accounts) == 2  # TFSA and RRSP

    def test_get_accounts_empty(self, data_manager):
        """Test getting accounts from empty data."""
        accounts = data_manager.get_accounts()
        assert accounts == []

    def test_get_stock_symbols(self, populated_data_manager):
        """Test getting list of unique stock symbols."""
        symbols = populated_data_manager.get_stock_symbols()
        assert isinstance(symbols, list)
        assert 'AAPL' in symbols
        assert 'MSFT' in symbols
        assert 'RSI.TO' in symbols
        assert len(symbols) == 3

    def test_get_stock_symbols_empty(self, data_manager):
        """Test getting symbols from empty data."""
        symbols = data_manager.get_stock_symbols()
        assert symbols == []

    def test_get_trades_for_account_symbol(self, populated_data_manager):
        """Test getting trades for specific account and symbol."""
        trades = populated_data_manager.get_trades_for_account_symbol('TFSA', 'AAPL')
        assert len(trades) == 2  # Buy and Sell
        assert trades.iloc[0]['TradeType'] == 'B'
        assert trades.iloc[1]['TradeType'] == 'S'

    def test_get_trades_for_account_symbol_sorted(self, populated_data_manager):
        """Test that trades are sorted by date."""
        trades = populated_data_manager.get_trades_for_account_symbol('TFSA', 'AAPL')
        # First trade should be earlier date
        date1 = pd.to_datetime(trades.iloc[0]['DateOfTrade'])
        date2 = pd.to_datetime(trades.iloc[1]['DateOfTrade'])
        assert date1 <= date2


class TestDataManagerMigration:
    """Test data migration functionality."""

    def test_migrate_integer_quantities(self, data_manager):
        """Test migrating float quantities to integers."""
        # Create data with float quantities
        consolidated_data = pd.DataFrame([{
            'Account': 'TFSA',
            'StockName': 'Test',
            'StockSymbol': 'TEST',
            'Quantity': 100.5,  # Float
            'AveragePricePerShare': 50.0,
            'CapitalGainLoss': 0.0,
            'DateOfAcquisition': '2024-01-01'
        }])

        trades_data = pd.DataFrame([{
            'Account': 'TFSA',
            'StockName': 'Test',
            'StockSymbol': 'TEST',
            'DateOfTrade': '2024-01-01',
            'TradeType': 'B',
            'SharesTraded': 50.7,  # Float
            'PricePerShare': 50.0,
            'Commission': 9.99
        }])

        data_manager.write_consolidated(consolidated_data)
        data_manager.write_trades(trades_data)

        # Run migration
        success = data_manager.migrate_integer_quantities()
        assert success

        # Check that values are now integers
        consolidated = data_manager.read_consolidated()
        trades = data_manager.read_trades()

        # Pandas uses banker's rounding: .5 rounds to nearest even
        assert consolidated.iloc[0]['Quantity'] == 100  # Rounded from 100.5 (to nearest even)
        assert trades.iloc[0]['SharesTraded'] == 51  # Rounded from 50.7

"""
Pytest fixtures and configuration for stock tracker tests.
"""
import pytest
import pandas as pd
import os
import tempfile
import shutil
from datetime import date, datetime

# Add parent directory to path to import modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.data_manager import DataManager
from utils.calculations import TradeCalculator


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir)


@pytest.fixture
def data_manager(temp_data_dir):
    """Create a DataManager instance with temporary data directory."""
    return DataManager(data_dir=temp_data_dir)


@pytest.fixture
def calculator(data_manager):
    """Create a TradeCalculator instance with test DataManager."""
    return TradeCalculator(data_manager)


@pytest.fixture
def sample_consolidated_data():
    """Sample consolidated holdings data."""
    return pd.DataFrame([
        {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'Quantity': 100,
            'AveragePricePerShare': 150.50,
            'CapitalGainLoss': 0.0,
            'DateOfAcquisition': '2024-01-15'
        },
        {
            'Account': 'TFSA',
            'StockName': 'Microsoft Corporation',
            'StockSymbol': 'MSFT',
            'Quantity': 50,
            'AveragePricePerShare': 350.75,
            'CapitalGainLoss': 500.00,
            'DateOfAcquisition': '2024-02-20'
        },
        {
            'Account': 'RRSP',
            'StockName': 'Rogers Sugar Inc.',
            'StockSymbol': 'RSI.TO',
            'Quantity': 200,
            'AveragePricePerShare': 5.25,
            'CapitalGainLoss': -100.00,
            'DateOfAcquisition': '2024-03-10'
        }
    ])


@pytest.fixture
def sample_trades_data():
    """Sample trade history data."""
    return pd.DataFrame([
        {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': '2024-01-15',
            'TradeType': 'B',
            'SharesTraded': 100,
            'PricePerShare': 150.00,
            'Commission': 9.99
        },
        {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': '2024-04-10',
            'TradeType': 'S',
            'SharesTraded': 25,
            'PricePerShare': 175.00,
            'Commission': 9.99
        },
        {
            'Account': 'TFSA',
            'StockName': 'Microsoft Corporation',
            'StockSymbol': 'MSFT',
            'DateOfTrade': '2024-02-20',
            'TradeType': 'B',
            'SharesTraded': 50,
            'PricePerShare': 350.00,
            'Commission': 9.99
        }
    ])


@pytest.fixture
def populated_data_manager(data_manager, sample_consolidated_data, sample_trades_data):
    """DataManager pre-populated with sample data."""
    data_manager.write_consolidated(sample_consolidated_data)
    data_manager.write_trades(sample_trades_data)
    return data_manager


@pytest.fixture
def buy_trade_data():
    """Sample buy trade data."""
    return {
        'Account': 'TFSA',
        'StockName': 'Tesla Inc.',
        'StockSymbol': 'TSLA',
        'DateOfTrade': date.today().strftime('%Y-%m-%d'),
        'TradeType': 'B',
        'SharesTraded': 10,
        'PricePerShare': 250.00,
        'Commission': 9.99
    }


@pytest.fixture
def sell_trade_data():
    """Sample sell trade data."""
    return {
        'Account': 'TFSA',
        'StockName': 'Apple Inc.',
        'StockSymbol': 'AAPL',
        'DateOfTrade': date.today().strftime('%Y-%m-%d'),
        'TradeType': 'S',
        'SharesTraded': 25,
        'PricePerShare': 175.00,
        'Commission': 9.99
    }


@pytest.fixture
def existing_holding_data():
    """Sample existing holding data for pre-population."""
    return {
        'Account': 'RRSP',
        'StockName': 'Amazon.com Inc.',
        'StockSymbol': 'AMZN',
        'Quantity': 20,
        'BookCost': 3000.00,
        'DateOfAcquisition': '2023-12-01'
    }

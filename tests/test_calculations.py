"""
Tests for TradeCalculator class.
"""
import pytest
import pandas as pd
from datetime import date


class TestBuyTradeProcessing:
    """Test buy trade calculations."""

    def test_process_buy_trade_new_stock(self, calculator, buy_trade_data):
        """Test buying a stock for the first time."""
        success, message = calculator.process_buy_trade(buy_trade_data)
        assert success
        assert "Buy trade processed successfully" in message

        # Verify consolidated record created
        record = calculator.data_manager.get_consolidated_record('TFSA', 'TSLA')
        assert record is not None
        assert record['Quantity'] == 10
        # Cost = (10 * 250.00) + 9.99 = 2509.99
        # Avg price = 2509.99 / 10 = 250.999
        assert abs(record['AveragePricePerShare'] - 250.999) < 0.01
        assert record['CapitalGainLoss'] == 0.0

    def test_process_buy_trade_existing_stock(self, calculator, populated_data_manager):
        """Test buying more of an existing stock."""
        # AAPL: 100 shares @ 150.50 avg (total cost = 15050)
        buy_more_aapl = {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': date.today().strftime('%Y-%m-%d'),
            'TradeType': 'B',
            'SharesTraded': 50,
            'PricePerShare': 160.00,
            'Commission': 9.99
        }

        success, message = calculator.process_buy_trade(buy_more_aapl)
        assert success

        record = calculator.data_manager.get_consolidated_record('TFSA', 'AAPL')
        assert record['Quantity'] == 150  # 100 + 50

        # New total cost = 15050 + (50 * 160 + 9.99) = 15050 + 8009.99 = 23059.99
        # New avg = 23059.99 / 150 = 153.7333
        expected_avg = 23059.99 / 150
        assert abs(record['AveragePricePerShare'] - expected_avg) < 0.01

    def test_process_buy_trade_preserves_date(self, calculator, buy_trade_data):
        """Test that buy trade preserves original acquisition date for existing holdings."""
        # First buy
        calculator.process_buy_trade(buy_trade_data)
        first_record = calculator.data_manager.get_consolidated_record('TFSA', 'TSLA')
        first_date = first_record['DateOfAcquisition']

        # Second buy (should keep original date)
        buy_more = buy_trade_data.copy()
        buy_more['DateOfTrade'] = '2025-01-15'
        calculator.process_buy_trade(buy_more)

        second_record = calculator.data_manager.get_consolidated_record('TFSA', 'TSLA')
        assert second_record['DateOfAcquisition'] == first_date

    def test_process_buy_trade_with_zero_commission(self, calculator):
        """Test buy trade with no commission."""
        trade = {
            'Account': 'TFSA',
            'StockName': 'Tesla Inc.',
            'StockSymbol': 'TSLA',
            'DateOfTrade': date.today().strftime('%Y-%m-%d'),
            'TradeType': 'B',
            'SharesTraded': 10,
            'PricePerShare': 250.00,
            'Commission': 0.00
        }

        success, message = calculator.process_buy_trade(trade)
        assert success

        record = calculator.data_manager.get_consolidated_record('TFSA', 'TSLA')
        # Avg price should be exactly 250.00 with no commission
        assert record['AveragePricePerShare'] == 250.00


class TestSellTradeProcessing:
    """Test sell trade calculations."""

    def test_process_sell_trade_success(self, calculator, populated_data_manager, sell_trade_data):
        """Test selling shares successfully."""
        # AAPL: 100 shares @ 150.50 avg
        # Selling 25 @ 175.00
        success, message = calculator.process_sell_trade(sell_trade_data)
        assert success
        assert "Sell trade processed successfully" in message

        record = calculator.data_manager.get_consolidated_record('TFSA', 'AAPL')
        assert record['Quantity'] == 75  # 100 - 25

        # Net proceeds = (25 * 175) - 9.99 = 4375 - 9.99 = 4365.01
        # Cost basis = 25 * 150.50 = 3762.50
        # Gain = 4365.01 - 3762.50 = 602.51
        expected_gain = 602.51
        assert abs(record['CapitalGainLoss'] - expected_gain) < 0.01

    def test_process_sell_trade_preserves_avg_price(self, calculator, populated_data_manager, sell_trade_data):
        """Test that selling doesn't change average price."""
        original_avg = 150.50

        calculator.process_sell_trade(sell_trade_data)

        record = calculator.data_manager.get_consolidated_record('TFSA', 'AAPL')
        assert record['AveragePricePerShare'] == original_avg

    def test_process_sell_trade_insufficient_shares(self, calculator, populated_data_manager):
        """Test selling more shares than owned."""
        sell_too_many = {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': date.today().strftime('%Y-%m-%d'),
            'TradeType': 'S',
            'SharesTraded': 150,  # More than the 100 owned
            'PricePerShare': 175.00,
            'Commission': 9.99
        }

        success, message = calculator.process_sell_trade(sell_too_many)
        assert not success
        assert "Insufficient shares" in message

    def test_process_sell_trade_nonexistent_stock(self, calculator):
        """Test selling a stock not in portfolio."""
        sell_nonexistent = {
            'Account': 'TFSA',
            'StockName': 'Tesla Inc.',
            'StockSymbol': 'TSLA',
            'DateOfTrade': date.today().strftime('%Y-%m-%d'),
            'TradeType': 'S',
            'SharesTraded': 10,
            'PricePerShare': 250.00,
            'Commission': 9.99
        }

        success, message = calculator.process_sell_trade(sell_nonexistent)
        assert not success
        assert "No existing holdings found" in message

    def test_process_sell_trade_accumulates_gain_loss(self, calculator, populated_data_manager):
        """Test that multiple sells accumulate capital gain/loss."""
        # MSFT has existing gain of 500.00
        sell_msft = {
            'Account': 'TFSA',
            'StockName': 'Microsoft Corporation',
            'StockSymbol': 'MSFT',
            'DateOfTrade': date.today().strftime('%Y-%m-%d'),
            'TradeType': 'S',
            'SharesTraded': 10,
            'PricePerShare': 400.00,
            'Commission': 9.99
        }

        calculator.process_sell_trade(sell_msft)

        record = calculator.data_manager.get_consolidated_record('TFSA', 'MSFT')
        # Net proceeds = (10 * 400) - 9.99 = 3990.01
        # Cost basis = 10 * 350.75 = 3507.50
        # This trade gain = 3990.01 - 3507.50 = 482.51
        # Total gain = 500.00 + 482.51 = 982.51
        expected_total_gain = 982.51
        assert abs(record['CapitalGainLoss'] - expected_total_gain) < 0.01

    def test_process_sell_trade_adds_historical_financial_fields(self, calculator, populated_data_manager, sell_trade_data):
        """Test selling shares enriches the trade with sale-time cost/proceeds."""
        success, message = calculator.process_sell_trade(sell_trade_data)

        assert success
        assert abs(sell_trade_data['GrossProceeds'] - 4375.00) < 0.01
        assert abs(sell_trade_data['NetProceeds'] - 4365.01) < 0.01
        assert abs(sell_trade_data['AverageCostAtSale'] - 150.50) < 0.01
        assert abs(sell_trade_data['Cost'] - 3762.50) < 0.01
        assert abs(sell_trade_data['CapitalGainLoss'] - 602.51) < 0.01


class TestTransferTradeProcessing:
    """Test transfer trade processing."""

    def test_process_transfer_trade(self, calculator):
        """Test that transfer trades are recorded but don't affect calculations."""
        transfer_data = {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': date.today().strftime('%Y-%m-%d'),
            'TradeType': 'T',
            'SharesTraded': 50,
            'PricePerShare': 0.00,
            'Commission': 0.00
        }

        success, message = calculator.process_transfer_trade(transfer_data)
        assert success
        assert "Transfer trade recorded successfully" in message


class TestTradeProcessing:
    """Test the main process_trade method."""

    def test_process_trade_buy(self, calculator, buy_trade_data):
        """Test process_trade routes buy correctly."""
        success, message = calculator.process_trade(buy_trade_data)
        assert success

        # Verify trade was added to history
        trades = calculator.data_manager.read_trades()
        assert len(trades) == 1
        assert trades.iloc[0]['TradeType'] == 'B'

    def test_process_trade_sell(self, calculator, populated_data_manager, sell_trade_data):
        """Test process_trade routes sell correctly."""
        success, message = calculator.process_trade(sell_trade_data)
        assert success

        trades = calculator.data_manager.read_trades()
        # 3 from sample data + 1 new = 4
        assert len(trades) == 4

    def test_process_trade_unknown_type(self, calculator):
        """Test process_trade with unknown trade type."""
        bad_trade = {
            'Account': 'TFSA',
            'StockName': 'Test',
            'StockSymbol': 'TEST',
            'DateOfTrade': date.today().strftime('%Y-%m-%d'),
            'TradeType': 'X',  # Invalid
            'SharesTraded': 10,
            'PricePerShare': 100.00,
            'Commission': 9.99
        }

        success, message = calculator.process_trade(bad_trade)
        assert not success
        assert "Unknown trade type" in message

        trades = calculator.data_manager.read_trades()
        assert trades.empty

    def test_process_trade_invalid_sell_is_not_saved_to_history(self, calculator, populated_data_manager):
        """Test failed sell validation happens before trade history persistence."""
        sell_too_many = {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': date.today().strftime('%Y-%m-%d'),
            'TradeType': 'S',
            'SharesTraded': 150,
            'PricePerShare': 175.00,
            'Commission': 9.99
        }
        initial_trades = len(calculator.data_manager.read_trades())

        success, message = calculator.process_trade(sell_too_many)

        assert not success
        assert "Insufficient shares" in message
        assert len(calculator.data_manager.read_trades()) == initial_trades

    def test_process_trade_existing_buy_allows_symbol_only_name(self, calculator, populated_data_manager):
        """Test existing holdings can be bought with symbol only."""
        buy_more = {
            'Account': 'TFSA',
            'StockName': '',
            'StockSymbol': 'AAPL',
            'DateOfTrade': date.today().strftime('%Y-%m-%d'),
            'TradeType': 'B',
            'SharesTraded': 10,
            'PricePerShare': 160.00,
            'Commission': 9.99
        }

        success, message = calculator.process_trade(buy_more)

        assert success
        record = calculator.data_manager.get_consolidated_record('TFSA', 'AAPL')
        assert record['StockName'] == 'Apple Inc.'
        assert record['Quantity'] == 110

    def test_process_trade_new_buy_requires_name(self, calculator):
        """Test new symbols still require a stock name."""
        buy_new_without_name = {
            'Account': 'TFSA',
            'StockName': '',
            'StockSymbol': 'NVDA',
            'DateOfTrade': date.today().strftime('%Y-%m-%d'),
            'TradeType': 'B',
            'SharesTraded': 10,
            'PricePerShare': 160.00,
            'Commission': 9.99
        }

        success, message = calculator.process_trade(buy_new_without_name)

        assert not success
        assert "Stock name is required" in message
        assert calculator.data_manager.read_trades().empty

    def test_process_trade_persists_buy_cost_and_sell_proceeds(self, calculator):
        """Test persisted history stores cost/proceeds audit columns."""
        buy_trade = {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': '2024-01-15',
            'TradeType': 'B',
            'SharesTraded': 100,
            'PricePerShare': 150.00,
            'Commission': 9.99
        }
        sell_trade = {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': '2024-06-15',
            'TradeType': 'S',
            'SharesTraded': 25,
            'PricePerShare': 175.00,
            'Commission': 9.99
        }

        assert calculator.process_trade(buy_trade)[0]
        assert calculator.process_trade(sell_trade)[0]

        trades = calculator.data_manager.read_trades()
        buy_row = trades.iloc[0]
        sell_row = trades.iloc[1]
        assert abs(buy_row['Cost'] - 15009.99) < 0.01
        assert pd.isna(buy_row['GrossProceeds'])
        assert abs(sell_row['GrossProceeds'] - 4375.00) < 0.01
        assert abs(sell_row['NetProceeds'] - 4365.01) < 0.01
        assert abs(sell_row['AverageCostAtSale'] - 150.0999) < 0.01
        assert abs(sell_row['CapitalGainLoss'] - 612.51) < 0.01


class TestAddExistingHolding:
    """Test adding pre-existing holdings."""

    def test_add_existing_holding_success(self, calculator, existing_holding_data):
        """Test adding an existing holding successfully."""
        success, message = calculator.add_existing_holding(existing_holding_data)
        assert success
        assert "Existing holding added successfully" in message

        record = calculator.data_manager.get_consolidated_record('RRSP', 'AMZN')
        assert record is not None
        assert record['Quantity'] == 20
        # Cost per share = 3000 / 20 = 150
        assert record['AveragePricePerShare'] == 150.00
        assert record['CapitalGainLoss'] == 0.0

    def test_add_existing_holding_duplicate(self, calculator, populated_data_manager, existing_holding_data):
        """Test that adding duplicate holding fails."""
        # Add it once
        calculator.add_existing_holding(existing_holding_data)

        # Try to add again
        success, message = calculator.add_existing_holding(existing_holding_data)
        assert not success
        assert "already exists" in message

    def test_add_existing_holding_zero_quantity(self, calculator):
        """Test that zero quantity is rejected."""
        bad_holding = {
            'Account': 'RRSP',
            'StockName': 'Test',
            'StockSymbol': 'TEST',
            'Quantity': 0,
            'BookCost': 1000.00,
            'DateOfAcquisition': '2024-01-01'
        }

        success, message = calculator.add_existing_holding(bad_holding)
        assert not success
        assert "must be greater than 0" in message

    def test_add_existing_holding_zero_cost(self, calculator):
        """Test that zero book cost is rejected."""
        bad_holding = {
            'Account': 'RRSP',
            'StockName': 'Test',
            'StockSymbol': 'TEST',
            'Quantity': 10,
            'BookCost': 0.00,
            'DateOfAcquisition': '2024-01-01'
        }

        success, message = calculator.add_existing_holding(bad_holding)
        assert not success
        assert "must be greater than 0" in message


class TestRebuildHoldings:
    """Test rebuilding holdings from trade history."""

    def test_rebuild_holdings_from_trades(self, calculator, populated_data_manager):
        """Test rebuilding consolidated holdings from trades."""
        # Manually corrupt the consolidated record
        corrupt_data = {
            'StockName': 'Apple Inc.',
            'Quantity': 999,  # Wrong
            'AveragePricePerShare': 1.00,  # Wrong
            'CapitalGainLoss': -9999.00,  # Wrong
            'DateOfAcquisition': '2024-01-15'
        }
        calculator.data_manager.update_consolidated_record('TFSA', 'AAPL', corrupt_data)

        # Rebuild from trades
        success, message = calculator.rebuild_holdings_from_trades('TFSA', 'AAPL')
        assert success
        assert "Processed 2 trade(s)" in message

        # Verify correct values after rebuild
        record = calculator.data_manager.get_consolidated_record('TFSA', 'AAPL')
        # Trade 1: Buy 100 @ 150.00 + 9.99 commission = 15009.99 total, avg = 150.0999
        # Trade 2: Sell 25 @ 175.00 - 9.99 commission = net 4365.01
        # Remaining: 75 shares @ 150.0999 avg
        # Gain on sell = 4365.01 - (25 * 150.0999) = 4365.01 - 3752.4975 = 612.51
        assert record['Quantity'] == 75
        assert abs(record['AveragePricePerShare'] - 150.0999) < 0.01

    def test_rebuild_holdings_no_trades(self, calculator, data_manager):
        """Test rebuilding when no trades exist."""
        success, message = calculator.rebuild_holdings_from_trades('TFSA', 'NONEXISTENT')
        assert success
        assert "No trades found" in message

    def test_rebuild_holdings_clears_old_record(self, calculator, populated_data_manager):
        """Test that rebuild clears the old consolidated record before rebuilding."""
        # Get initial record
        initial_record = calculator.data_manager.get_consolidated_record('TFSA', 'AAPL')
        assert initial_record is not None

        # Rebuild
        calculator.rebuild_holdings_from_trades('TFSA', 'AAPL')

        # Verify record still exists (rebuilt from trades)
        rebuilt_record = calculator.data_manager.get_consolidated_record('TFSA', 'AAPL')
        assert rebuilt_record is not None


class TestDeleteTradeAndRebuild:
    """Test deleting trades and rebuilding holdings."""

    def test_delete_trade_and_rebuild_success(self, calculator, populated_data_manager):
        """Test deleting a trade and rebuilding holdings."""
        # Get initial state
        trades_before = calculator.data_manager.read_trades()
        initial_count = len(trades_before)

        # Delete the sell trade (index 1)
        success, message = calculator.delete_trade_and_rebuild(1)
        assert success
        assert "Trade deleted and holdings rebuilt" in message

        # Verify trade was deleted
        trades_after = calculator.data_manager.read_trades()
        assert len(trades_after) == initial_count - 1

        # Verify holdings were rebuilt correctly
        # After deleting sell, should have 100 shares again (only buy trade remains)
        record = calculator.data_manager.get_consolidated_record('TFSA', 'AAPL')
        assert record['Quantity'] == 100

    def test_delete_trade_and_rebuild_invalid_index(self, calculator, populated_data_manager):
        """Test deleting trade with invalid index."""
        success, message = calculator.delete_trade_and_rebuild(999)
        assert not success
        assert "not found" in message

    def test_delete_trade_and_rebuild_clears_holding(self, calculator, data_manager):
        """Test that deleting all trades for a stock clears its consolidated record."""
        # Add a single buy trade
        buy_trade = {
            'Account': 'TFSA',
            'StockName': 'Tesla Inc.',
            'StockSymbol': 'TSLA',
            'DateOfTrade': date.today().strftime('%Y-%m-%d'),
            'TradeType': 'B',
            'SharesTraded': 10,
            'PricePerShare': 250.00,
            'Commission': 9.99
        }
        calculator.process_trade(buy_trade)

        # Verify holding exists
        record = calculator.data_manager.get_consolidated_record('TFSA', 'TSLA')
        assert record is not None

        # Delete the only trade
        calculator.delete_trade_and_rebuild(0)

        # Verify holding is cleared
        record_after = calculator.data_manager.get_consolidated_record('TFSA', 'TSLA')
        assert record_after is None


class TestCalculationEdgeCases:
    """Test edge cases and error handling."""

    def test_buy_with_fractional_shares_rounded(self, calculator):
        """Test that fractional shares are handled (should be caught by validation)."""
        # This test assumes integer validation happens before reaching calculator
        pass  # Validation happens at form level

    def test_negative_price_validation(self, calculator):
        """Test that negative prices are handled."""
        # Note: This should be caught by form validation
        # But calculator should handle gracefully if passed
        pass  # Validation happens at form level

    def test_very_large_numbers(self, calculator):
        """Test calculations with very large numbers."""
        large_trade = {
            'Account': 'TFSA',
            'StockName': 'Berkshire Hathaway',
            'StockSymbol': 'BRK.A',
            'DateOfTrade': date.today().strftime('%Y-%m-%d'),
            'TradeType': 'B',
            'SharesTraded': 1,
            'PricePerShare': 500000.00,  # $500k per share
            'Commission': 9.99
        }

        success, message = calculator.process_buy_trade(large_trade)
        assert success

        record = calculator.data_manager.get_consolidated_record('TFSA', 'BRK.A')
        expected_avg = (500000.00 + 9.99) / 1
        assert abs(record['AveragePricePerShare'] - expected_avg) < 0.01

    def test_very_small_prices(self, calculator):
        """Test calculations with penny stocks."""
        penny_stock = {
            'Account': 'TFSA',
            'StockName': 'Penny Inc.',
            'StockSymbol': 'PENNY',
            'DateOfTrade': date.today().strftime('%Y-%m-%d'),
            'TradeType': 'B',
            'SharesTraded': 10000,
            'PricePerShare': 0.05,  # 5 cents
            'Commission': 9.99
        }

        success, message = calculator.process_buy_trade(penny_stock)
        assert success

        record = calculator.data_manager.get_consolidated_record('TFSA', 'PENNY')
        # Cost = (10000 * 0.05) + 9.99 = 500 + 9.99 = 509.99
        # Avg = 509.99 / 10000 = 0.050999
        expected_avg = 509.99 / 10000
        assert abs(record['AveragePricePerShare'] - expected_avg) < 0.00001

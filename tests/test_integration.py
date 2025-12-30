"""
Integration tests for complete trade workflows.
"""
import pytest
from datetime import date, timedelta


class TestCompleteBuyWorkflow:
    """Test complete buy trade workflow from start to finish."""

    def test_buy_new_stock_complete_flow(self, calculator):
        """Test buying a new stock from empty portfolio."""
        # 1. Start with empty portfolio
        consolidated = calculator.data_manager.read_consolidated()
        assert consolidated.empty

        # 2. Process buy trade
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

        success, message = calculator.process_trade(buy_trade)
        assert success

        # 3. Verify trade history
        trades = calculator.data_manager.read_trades()
        assert len(trades) == 1
        assert trades.iloc[0]['TradeType'] == 'B'

        # 4. Verify consolidated record
        record = calculator.data_manager.get_consolidated_record('TFSA', 'AAPL')
        assert record['Quantity'] == 100
        expected_avg = (100 * 150.00 + 9.99) / 100
        assert abs(record['AveragePricePerShare'] - expected_avg) < 0.01
        assert record['CapitalGainLoss'] == 0.0

    def test_buy_additional_shares_workflow(self, calculator):
        """Test buying additional shares of existing holding."""
        # 1. First buy
        first_buy = {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': '2024-01-15',
            'TradeType': 'B',
            'SharesTraded': 100,
            'PricePerShare': 150.00,
            'Commission': 9.99
        }
        calculator.process_trade(first_buy)

        # 2. Second buy at different price
        second_buy = {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': '2024-02-15',
            'TradeType': 'B',
            'SharesTraded': 50,
            'PricePerShare': 160.00,
            'Commission': 9.99
        }
        calculator.process_trade(second_buy)

        # 3. Verify cumulative position
        record = calculator.data_manager.get_consolidated_record('TFSA', 'AAPL')
        assert record['Quantity'] == 150

        # Calculate expected avg
        cost1 = (100 * 150.00) + 9.99
        cost2 = (50 * 160.00) + 9.99
        total_cost = cost1 + cost2
        expected_avg = total_cost / 150
        assert abs(record['AveragePricePerShare'] - expected_avg) < 0.01


class TestCompleteSellWorkflow:
    """Test complete sell trade workflow."""

    def test_sell_partial_shares_workflow(self, calculator):
        """Test selling part of a position."""
        # 1. Buy shares
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
        calculator.process_trade(buy_trade)

        # 2. Sell some shares at profit
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
        success, message = calculator.process_trade(sell_trade)
        assert success

        # 3. Verify remaining position
        record = calculator.data_manager.get_consolidated_record('TFSA', 'AAPL')
        assert record['Quantity'] == 75

        # 4. Verify capital gain
        avg_cost = (100 * 150.00 + 9.99) / 100
        net_proceeds = (25 * 175.00) - 9.99
        expected_gain = net_proceeds - (25 * avg_cost)
        assert abs(record['CapitalGainLoss'] - expected_gain) < 0.01

        # 5. Verify trade history
        trades = calculator.data_manager.read_trades()
        assert len(trades) == 2
        assert trades.iloc[1]['TradeType'] == 'S'

    def test_sell_all_shares_workflow(self, calculator):
        """Test selling entire position."""
        # 1. Buy shares
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
        calculator.process_trade(buy_trade)

        # 2. Sell all shares
        sell_trade = {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': '2024-06-15',
            'TradeType': 'S',
            'SharesTraded': 100,
            'PricePerShare': 175.00,
            'Commission': 9.99
        }
        calculator.process_trade(sell_trade)

        # 3. Verify position is zero
        record = calculator.data_manager.get_consolidated_record('TFSA', 'AAPL')
        assert record['Quantity'] == 0

        # 4. Capital gain should be recorded
        assert record['CapitalGainLoss'] != 0.0


class TestMultipleAccountsWorkflow:
    """Test trading across multiple accounts."""

    def test_same_stock_different_accounts(self, calculator):
        """Test owning same stock in different accounts."""
        # 1. Buy AAPL in TFSA
        tfsa_buy = {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': '2024-01-15',
            'TradeType': 'B',
            'SharesTraded': 100,
            'PricePerShare': 150.00,
            'Commission': 9.99
        }
        calculator.process_trade(tfsa_buy)

        # 2. Buy AAPL in RRSP at different price
        rrsp_buy = {
            'Account': 'RRSP',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': '2024-01-20',
            'TradeType': 'B',
            'SharesTraded': 50,
            'PricePerShare': 155.00,
            'Commission': 9.99
        }
        calculator.process_trade(rrsp_buy)

        # 3. Verify separate holdings
        tfsa_record = calculator.data_manager.get_consolidated_record('TFSA', 'AAPL')
        rrsp_record = calculator.data_manager.get_consolidated_record('RRSP', 'AAPL')

        assert tfsa_record['Quantity'] == 100
        assert rrsp_record['Quantity'] == 50

        # Different average prices
        assert tfsa_record['AveragePricePerShare'] != rrsp_record['AveragePricePerShare']


class TestDeleteAndRebuildWorkflow:
    """Test deleting trades and rebuilding holdings."""

    def test_delete_middle_trade_and_rebuild(self, calculator):
        """Test deleting a trade from the middle of history."""
        # 1. Execute series of trades
        trades = [
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
                'DateOfTrade': '2024-02-15',
                'TradeType': 'B',
                'SharesTraded': 50,
                'PricePerShare': 160.00,
                'Commission': 9.99
            },
            {
                'Account': 'TFSA',
                'StockName': 'Apple Inc.',
                'StockSymbol': 'AAPL',
                'DateOfTrade': '2024-03-15',
                'TradeType': 'S',
                'SharesTraded': 25,
                'PricePerShare': 175.00,
                'Commission': 9.99
            }
        ]

        for trade in trades:
            calculator.process_trade(trade)

        # 2. Get state before deletion
        record_before = calculator.data_manager.get_consolidated_record('TFSA', 'AAPL')
        assert record_before['Quantity'] == 125  # 100 + 50 - 25

        # 3. Delete the middle trade (second buy)
        success, message = calculator.delete_trade_and_rebuild(1)
        assert success

        # 4. Verify holdings recalculated correctly
        record_after = calculator.data_manager.get_consolidated_record('TFSA', 'AAPL')
        # Should be: Buy 100 - Sell 25 = 75
        assert record_after['Quantity'] == 75

        # 5. Verify avg price recalculated
        # Only first buy: (100 * 150 + 9.99) / 100 = 150.0999
        # After sell of 25, still 150.0999 avg
        expected_avg = (100 * 150.00 + 9.99) / 100
        assert abs(record_after['AveragePricePerShare'] - expected_avg) < 0.01

    def test_delete_all_trades_clears_holding(self, calculator):
        """Test that deleting all trades for a stock clears the holding."""
        # 1. Single buy trade
        buy_trade = {
            'Account': 'TFSA',
            'StockName': 'Tesla Inc.',
            'StockSymbol': 'TSLA',
            'DateOfTrade': '2024-01-15',
            'TradeType': 'B',
            'SharesTraded': 10,
            'PricePerShare': 250.00,
            'Commission': 9.99
        }
        calculator.process_trade(buy_trade)

        # 2. Verify holding exists
        record = calculator.data_manager.get_consolidated_record('TFSA', 'TSLA')
        assert record is not None

        # 3. Delete the trade
        calculator.delete_trade_and_rebuild(0)

        # 4. Verify holding is cleared
        record_after = calculator.data_manager.get_consolidated_record('TFSA', 'TSLA')
        assert record_after is None


class TestComplexTradingScenario:
    """Test complex real-world trading scenarios."""

    def test_dollar_cost_averaging_workflow(self, calculator):
        """Test dollar-cost averaging strategy."""
        # Buy same stock monthly at different prices
        monthly_buys = [
            ('2024-01-15', 150.00),
            ('2024-02-15', 145.00),
            ('2024-03-15', 155.00),
            ('2024-04-15', 160.00),
            ('2024-05-15', 158.00),
        ]

        for trade_date, price in monthly_buys:
            trade = {
                'Account': 'RRSP',
                'StockName': 'S&P 500 ETF',
                'StockSymbol': 'SPY',
                'DateOfTrade': trade_date,
                'TradeType': 'B',
                'SharesTraded': 10,
                'PricePerShare': price,
                'Commission': 0.00  # Commission-free
            }
            calculator.process_trade(trade)

        # Verify total position
        record = calculator.data_manager.get_consolidated_record('RRSP', 'SPY')
        assert record['Quantity'] == 50  # 10 shares × 5 months

        # Calculate expected avg
        total_cost = sum(10 * price for _, price in monthly_buys)
        expected_avg = total_cost / 50
        assert abs(record['AveragePricePerShare'] - expected_avg) < 0.01

    def test_profit_taking_workflow(self, calculator):
        """Test taking profits incrementally."""
        # 1. Initial buy
        buy_trade = {
            'Account': 'TFSA',
            'StockName': 'Tesla Inc.',
            'StockSymbol': 'TSLA',
            'DateOfTrade': '2024-01-01',
            'TradeType': 'B',
            'SharesTraded': 100,
            'PricePerShare': 200.00,
            'Commission': 9.99
        }
        calculator.process_trade(buy_trade)

        # 2. Sell 25% when price goes up 20%
        sell_25 = {
            'Account': 'TFSA',
            'StockName': 'Tesla Inc.',
            'StockSymbol': 'TSLA',
            'DateOfTrade': '2024-03-01',
            'TradeType': 'S',
            'SharesTraded': 25,
            'PricePerShare': 240.00,
            'Commission': 9.99
        }
        calculator.process_trade(sell_25)

        # 3. Sell another 25% when price goes up more
        sell_another_25 = {
            'Account': 'TFSA',
            'StockName': 'Tesla Inc.',
            'StockSymbol': 'TSLA',
            'DateOfTrade': '2024-06-01',
            'TradeType': 'S',
            'SharesTraded': 25,
            'PricePerShare': 280.00,
            'Commission': 9.99
        }
        calculator.process_trade(sell_another_25)

        # 4. Verify position and gains
        record = calculator.data_manager.get_consolidated_record('TFSA', 'TSLA')
        assert record['Quantity'] == 50  # 100 - 25 - 25

        # Both sells should show profit
        assert record['CapitalGainLoss'] > 0


class TestErrorRecoveryWorkflow:
    """Test error handling and recovery scenarios."""

    def test_insufficient_shares_error_handling(self, calculator):
        """Test that overselling is caught and prevented."""
        # 1. Buy shares
        buy_trade = {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': '2024-01-15',
            'TradeType': 'B',
            'SharesTraded': 50,
            'PricePerShare': 150.00,
            'Commission': 9.99
        }
        calculator.process_trade(buy_trade)

        # 2. Try to sell more than owned
        oversell = {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': '2024-02-15',
            'TradeType': 'S',
            'SharesTraded': 100,  # More than the 50 owned
            'PricePerShare': 175.00,
            'Commission': 9.99
        }
        success, message = calculator.process_trade(oversell)
        assert not success
        assert "Insufficient shares" in message

        # 3. Verify position unchanged
        record = calculator.data_manager.get_consolidated_record('TFSA', 'AAPL')
        assert record['Quantity'] == 50  # Still have original 50

        # 4. Verify trade history
        trades = calculator.data_manager.read_trades()
        # Note: Current implementation adds trade to history before validation
        # So failed trade IS recorded (known limitation)
        assert len(trades) == 2
        # But consolidated wasn't updated due to validation failure
        assert record['Quantity'] == 50

    def test_nonexistent_stock_sell_error(self, calculator):
        """Test selling a stock that doesn't exist in portfolio."""
        sell_nonexistent = {
            'Account': 'TFSA',
            'StockName': 'Tesla Inc.',
            'StockSymbol': 'TSLA',
            'DateOfTrade': '2024-01-15',
            'TradeType': 'S',
            'SharesTraded': 10,
            'PricePerShare': 250.00,
            'Commission': 9.99
        }

        success, message = calculator.process_trade(sell_nonexistent)
        assert not success
        assert "No existing holdings found" in message


class TestDataIntegrity:
    """Test data integrity across operations."""

    def test_trades_and_consolidated_stay_in_sync(self, calculator):
        """Test that trade history and consolidated records stay synchronized."""
        # Execute multiple trades
        trades = [
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
                'StockName': 'Microsoft Corporation',
                'StockSymbol': 'MSFT',
                'DateOfTrade': '2024-02-15',
                'TradeType': 'B',
                'SharesTraded': 50,
                'PricePerShare': 350.00,
                'Commission': 9.99
            },
            {
                'Account': 'RRSP',
                'StockName': 'Apple Inc.',
                'StockSymbol': 'AAPL',
                'DateOfTrade': '2024-03-15',
                'TradeType': 'B',
                'SharesTraded': 75,
                'PricePerShare': 155.00,
                'Commission': 9.99
            }
        ]

        for trade in trades:
            calculator.process_trade(trade)

        # Verify counts match
        trades_df = calculator.data_manager.read_trades()
        consolidated_df = calculator.data_manager.read_consolidated()

        assert len(trades_df) == 3
        assert len(consolidated_df) == 3  # 3 unique account+symbol combinations

        # Verify accounts match
        trade_accounts = set(trades_df['Account'].unique())
        consolidated_accounts = set(consolidated_df['Account'].unique())
        assert trade_accounts == consolidated_accounts


class TestSuccessMessages:
    """Test that success messages only appear when operations succeed."""

    def test_buy_trade_success_message(self, calculator):
        """Test that buy trade returns success message on successful processing."""
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

        success, message = calculator.process_trade(buy_trade)

        # Verify success flag is True
        assert success

        # Verify success message contains expected keywords
        assert "successfully" in message.lower()
        assert "buy" in message.lower()

        # Verify message includes key information
        assert "100" in message  # Quantity
        assert "150.09" in message or "150.1" in message  # Avg price

    def test_sell_trade_success_message(self, calculator, populated_data_manager):
        """Test that sell trade returns success message on successful processing."""
        # AAPL: 100 shares @ 150.50 avg in populated_data_manager
        sell_trade = {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': '2024-02-15',
            'TradeType': 'S',
            'SharesTraded': 25,
            'PricePerShare': 175.00,
            'Commission': 9.99
        }

        success, message = calculator.process_trade(sell_trade)

        # Verify success flag is True
        assert success

        # Verify success message contains expected keywords
        assert "successfully" in message.lower()
        assert "sell" in message.lower()

        # Verify message includes key information
        assert "75" in message  # Remaining quantity
        assert "602.51" in message or "602.5" in message  # Gain

    def test_failed_sell_returns_error_message(self, calculator, populated_data_manager):
        """Test that failed sell returns error message, not success message."""
        # Try to sell more shares than owned
        sell_too_many = {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': '2024-02-15',
            'TradeType': 'S',
            'SharesTraded': 150,  # More than the 100 owned
            'PricePerShare': 175.00,
            'Commission': 9.99
        }

        success, message = calculator.process_trade(sell_too_many)

        # Verify success flag is False
        assert not success

        # Verify error message contains expected keywords
        assert "insufficient" in message.lower() or "error" in message.lower()

        # Verify no success message appears
        assert "successfully" not in message.lower()

    def test_failed_sell_nonexistent_stock_returns_error(self, calculator):
        """Test that selling non-existent stock returns error, not success."""
        sell_nonexistent = {
            'Account': 'TFSA',
            'StockName': 'Tesla Inc.',
            'StockSymbol': 'TSLA',
            'DateOfTrade': '2024-02-15',
            'TradeType': 'S',
            'SharesTraded': 10,
            'PricePerShare': 250.00,
            'Commission': 9.99
        }

        success, message = calculator.process_trade(sell_nonexistent)

        # Verify success flag is False
        assert not success

        # Verify error message
        assert "no existing holdings" in message.lower() or "not found" in message.lower()

        # Verify no success message appears
        assert "successfully" not in message.lower()

    def test_transfer_trade_success_message(self, calculator):
        """Test that transfer trade returns success message."""
        transfer_trade = {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': '2024-01-15',
            'TradeType': 'T',
            'SharesTraded': 50,
            'PricePerShare': 0.00,
            'Commission': 0.00
        }

        success, message = calculator.process_trade(transfer_trade)

        # Verify success flag is True
        assert success

        # Verify success message
        assert "successfully" in message.lower()
        assert "transfer" in message.lower()


class TestCSVVerification:
    """Test that CSV files are correctly updated after trade operations."""

    def test_buy_trade_updates_both_csv_files(self, calculator):
        """Test that a buy trade updates both trades.csv and consolidated.csv correctly."""
        # Start with empty data
        assert calculator.data_manager.read_consolidated().empty
        assert calculator.data_manager.read_trades().empty

        # Submit a buy trade
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

        success, _ = calculator.process_trade(buy_trade)
        assert success

        # Read and verify trades.csv
        trades_df = calculator.data_manager.read_trades()
        assert len(trades_df) == 1

        trade_row = trades_df.iloc[0]
        assert trade_row['Account'] == 'TFSA'
        assert trade_row['StockName'] == 'Apple Inc.'
        assert trade_row['StockSymbol'] == 'AAPL'
        assert str(trade_row['DateOfTrade']).startswith('2024-01-15')
        assert trade_row['TradeType'] == 'B'
        assert int(trade_row['SharesTraded']) == 100
        assert float(trade_row['PricePerShare']) == 150.00
        assert float(trade_row['Commission']) == 9.99

        # Read and verify consolidated.csv
        consolidated_df = calculator.data_manager.read_consolidated()
        assert len(consolidated_df) == 1

        holding_row = consolidated_df.iloc[0]
        assert holding_row['Account'] == 'TFSA'
        assert holding_row['StockName'] == 'Apple Inc.'
        assert holding_row['StockSymbol'] == 'AAPL'
        assert int(holding_row['Quantity']) == 100
        assert abs(float(holding_row['AveragePricePerShare']) - 150.0999) < 0.01
        assert float(holding_row['CapitalGainLoss']) == 0.0
        assert str(holding_row['DateOfAcquisition']).startswith('2024-01-15')

    def test_sell_trade_updates_csv_correctly(self, calculator):
        """Test that a sell trade updates CSV files with correct values."""
        # First, buy some shares
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
        calculator.process_trade(buy_trade)

        # Now sell some shares
        sell_trade = {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': '2024-02-15',
            'TradeType': 'S',
            'SharesTraded': 25,
            'PricePerShare': 175.00,
            'Commission': 9.99
        }
        success, _ = calculator.process_trade(sell_trade)
        assert success

        # Verify trades.csv has both trades
        trades_df = calculator.data_manager.read_trades()
        assert len(trades_df) == 2

        # Verify the sell trade in CSV
        sell_row = trades_df.iloc[1]
        assert sell_row['TradeType'] == 'S'
        assert int(sell_row['SharesTraded']) == 25
        assert float(sell_row['PricePerShare']) == 175.00

        # Verify consolidated.csv is updated correctly
        consolidated_df = calculator.data_manager.read_consolidated()
        assert len(consolidated_df) == 1

        holding_row = consolidated_df.iloc[0]
        assert int(holding_row['Quantity']) == 75  # 100 - 25
        assert abs(float(holding_row['AveragePricePerShare']) - 150.0999) < 0.01  # Unchanged

        # Verify capital gain/loss is calculated
        # Net proceeds = (25 * 175) - 9.99 = 4365.01
        # Cost basis = 25 * 150.0999 = 3752.4975
        # Gain = 4365.01 - 3752.4975 = 612.51
        assert abs(float(holding_row['CapitalGainLoss']) - 612.51) < 0.01

    def test_multiple_trades_csv_accumulation(self, calculator):
        """Test that multiple trades accumulate correctly in CSV files."""
        trades = [
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
                'StockName': 'Microsoft Corporation',
                'StockSymbol': 'MSFT',
                'DateOfTrade': '2024-02-01',
                'TradeType': 'B',
                'SharesTraded': 50,
                'PricePerShare': 350.00,
                'Commission': 9.99
            },
            {
                'Account': 'RRSP',
                'StockName': 'Apple Inc.',
                'StockSymbol': 'AAPL',
                'DateOfTrade': '2024-03-01',
                'TradeType': 'B',
                'SharesTraded': 75,
                'PricePerShare': 155.00,
                'Commission': 9.99
            }
        ]

        # Process all trades
        for trade in trades:
            success, _ = calculator.process_trade(trade)
            assert success

        # Verify trades.csv has all 3 trades
        trades_df = calculator.data_manager.read_trades()
        assert len(trades_df) == 3

        # Verify consolidated.csv has 3 holdings (TFSA/AAPL, TFSA/MSFT, RRSP/AAPL)
        consolidated_df = calculator.data_manager.read_consolidated()
        assert len(consolidated_df) == 3

        # Verify each holding exists with correct values
        tfsa_aapl = consolidated_df[
            (consolidated_df['Account'] == 'TFSA') &
            (consolidated_df['StockSymbol'] == 'AAPL')
        ]
        assert len(tfsa_aapl) == 1
        assert int(tfsa_aapl.iloc[0]['Quantity']) == 100

        tfsa_msft = consolidated_df[
            (consolidated_df['Account'] == 'TFSA') &
            (consolidated_df['StockSymbol'] == 'MSFT')
        ]
        assert len(tfsa_msft) == 1
        assert int(tfsa_msft.iloc[0]['Quantity']) == 50

        rrsp_aapl = consolidated_df[
            (consolidated_df['Account'] == 'RRSP') &
            (consolidated_df['StockSymbol'] == 'AAPL')
        ]
        assert len(rrsp_aapl) == 1
        assert int(rrsp_aapl.iloc[0]['Quantity']) == 75

    def test_failed_trade_does_not_update_consolidated_csv(self, calculator, populated_data_manager):
        """Test that a failed sell trade does not corrupt consolidated.csv."""
        # Get initial consolidated state
        initial_consolidated = calculator.data_manager.read_consolidated()
        initial_count = len(initial_consolidated)

        initial_aapl = calculator.data_manager.get_consolidated_record('TFSA', 'AAPL')
        initial_quantity = int(initial_aapl['Quantity'])

        # Try to sell more than owned (should fail)
        sell_too_many = {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': '2024-02-15',
            'TradeType': 'S',
            'SharesTraded': 150,  # More than the 100 owned
            'PricePerShare': 175.00,
            'Commission': 9.99
        }

        success, _ = calculator.process_trade(sell_too_many)
        assert not success  # Trade should fail

        # Verify consolidated.csv is unchanged
        final_consolidated = calculator.data_manager.read_consolidated()
        assert len(final_consolidated) == initial_count

        final_aapl = calculator.data_manager.get_consolidated_record('TFSA', 'AAPL')
        assert int(final_aapl['Quantity']) == initial_quantity

    def test_transfer_trade_only_updates_trades_csv(self, calculator):
        """Test that transfer trades only appear in trades.csv, not consolidated.csv."""
        # Submit a transfer trade
        transfer_trade = {
            'Account': 'TFSA',
            'StockName': 'Apple Inc.',
            'StockSymbol': 'AAPL',
            'DateOfTrade': '2024-01-15',
            'TradeType': 'T',
            'SharesTraded': 50,
            'PricePerShare': 0.00,
            'Commission': 0.00
        }

        success, _ = calculator.process_trade(transfer_trade)
        assert success

        # Verify it appears in trades.csv
        trades_df = calculator.data_manager.read_trades()
        assert len(trades_df) == 1
        assert trades_df.iloc[0]['TradeType'] == 'T'

        # Verify consolidated.csv is still empty (transfer doesn't create holdings)
        consolidated_df = calculator.data_manager.read_consolidated()
        assert consolidated_df.empty

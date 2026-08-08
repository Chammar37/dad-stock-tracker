from typing import Dict, Optional, Tuple
import streamlit as st
from datetime import datetime
from .data_manager import DataManager

class TradeCalculator:
    """Handles all trade calculations according to the specified formulas."""
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager

    def validate_trade(self, trade_data: Dict) -> Tuple[bool, str]:
        """Validate trade data before writing history or holdings."""
        trade_type = trade_data.get('TradeType', '').upper()
        if trade_type not in {'B', 'S', 'T'}:
            return False, f"Unknown trade type: {trade_type}. Use B (Buy), S (Sell), or T (Transfer)"

        for field in ['Account', 'StockSymbol', 'DateOfTrade']:
            if not str(trade_data.get(field, '')).strip():
                return False, f"{field} is required"

        try:
            shares_traded = int(trade_data.get('SharesTraded'))
        except (TypeError, ValueError):
            return False, "Shares traded must be a whole number"
        if shares_traded < 1:
            return False, f"Shares traded must be greater than zero. You entered {trade_data.get('SharesTraded')}"

        try:
            price_per_share = float(trade_data.get('PricePerShare'))
        except (TypeError, ValueError):
            return False, "Price per share must be a number"
        if trade_type != 'T' and price_per_share <= 0:
            return False, "Price per share must be greater than 0"
        if trade_type == 'T' and price_per_share < 0:
            return False, "Price per share cannot be negative"

        try:
            commission = float(trade_data.get('Commission', 0))
        except (TypeError, ValueError):
            return False, "Commission must be a number"
        if commission < 0:
            return False, "Commission cannot be negative"

        if trade_type == 'B' and not str(trade_data.get('StockName', '')).strip():
            record = self.data_manager.get_consolidated_record(
                trade_data['Account'], trade_data['StockSymbol']
            )
            if not record:
                return False, "Stock name is required for new buy trades"

        if trade_type == 'S':
            record = self.data_manager.get_consolidated_record(
                trade_data['Account'], trade_data['StockSymbol']
            )
            if not record:
                return False, f"No existing holdings found for {trade_data['StockSymbol']} in {trade_data['Account']}"
            current_quantity = int(record['Quantity'])
            if shares_traded > current_quantity:
                return False, f"Insufficient shares. You have {current_quantity} shares, trying to sell {shares_traded}"

        return True, ""

    def enrich_trade_financials(self, trade_data: Dict) -> Dict:
        """Add display/audit financial fields to a trade history row."""
        enriched = trade_data.copy()
        trade_type = enriched.get('TradeType', '').upper()
        shares_traded = int(enriched['SharesTraded'])
        price_per_share = float(enriched['PricePerShare'])
        commission = float(enriched.get('Commission', 0))

        cost = None
        gross_proceeds = None
        net_proceeds = None
        average_cost_at_sale = None
        capital_gain_loss = None

        if trade_type == 'B':
            cost = (shares_traded * price_per_share) + commission
        elif trade_type == 'S':
            record = self.data_manager.get_consolidated_record(
                enriched['Account'], enriched['StockSymbol']
            )
            average_cost_at_sale = float(record['AveragePricePerShare'])
            gross_proceeds = shares_traded * price_per_share
            net_proceeds = gross_proceeds - commission
            cost = shares_traded * average_cost_at_sale
            capital_gain_loss = net_proceeds - cost

        enriched.update({
            'Cost': round(cost, 2) if cost is not None else None,
            'GrossProceeds': round(gross_proceeds, 2) if gross_proceeds is not None else None,
            'NetProceeds': round(net_proceeds, 2) if net_proceeds is not None else None,
            'AverageCostAtSale': (
                round(average_cost_at_sale, 4)
                if average_cost_at_sale is not None else None
            ),
            'CapitalGainLoss': (
                round(capital_gain_loss, 2)
                if capital_gain_loss is not None else None
            ),
        })
        return enriched
    
    def process_buy_trade(self, trade_data: Dict) -> Tuple[bool, str]:
        """
        Process a buy trade according to the specified formula.
        
        Formula:
        - Cost of trade = (Shares traded × price per share) + commission
        - Total cost of existing stocks = Quantity × Average price per share
        - New quantity = Quantity + Shares traded
        - New average price per share = (Total cost of existing stocks + Cost of trade) / New quantity
        """
        try:
            account = trade_data['Account']
            stock_symbol = trade_data['StockSymbol']
            shares_traded = int(trade_data['SharesTraded'])
            price_per_share = float(trade_data['PricePerShare'])
            commission = float(trade_data.get('Commission', 0))
            
            # Get existing consolidated record
            existing_record = self.data_manager.get_consolidated_record(account, stock_symbol)
            
            if existing_record:
                stock_name = (
                    str(trade_data.get('StockName', '')).strip()
                    or existing_record['StockName']
                )
                # Existing stock - update calculations
                current_quantity = int(existing_record['Quantity'])
                current_avg_price = float(existing_record['AveragePricePerShare'])
                current_capital_gain_loss = float(existing_record.get('CapitalGainLoss', 0))
                
                # Calculate new values
                cost_of_trade = (shares_traded * price_per_share) + commission
                total_cost_existing = current_quantity * current_avg_price
                new_quantity = int(current_quantity + shares_traded)
                new_avg_price = (total_cost_existing + cost_of_trade) / new_quantity
                
                # Update consolidated record
                updated_data = {
                    'StockName': stock_name,
                    'Quantity': int(new_quantity),
                    'AveragePricePerShare': round(new_avg_price, 4),
                    'CapitalGainLoss': current_capital_gain_loss,  # No change for buy
                    'DateOfAcquisition': existing_record['DateOfAcquisition']  # Keep original date
                }
                
            else:
                # New stock - initialize
                cost_of_trade = (shares_traded * price_per_share) + commission
                new_avg_price = cost_of_trade / shares_traded
                
                updated_data = {
                    'StockName': trade_data['StockName'],
                    'Quantity': int(shares_traded),
                    'AveragePricePerShare': round(new_avg_price, 4),
                    'CapitalGainLoss': 0,
                    'DateOfAcquisition': trade_data['DateOfTrade']
                }
            
            # Update consolidated record
            success = self.data_manager.update_consolidated_record(
                account, stock_symbol, updated_data
            )
            
            if success:
                return True, f"Buy trade processed successfully. New quantity: {updated_data['Quantity']}, New avg price: {updated_data['AveragePricePerShare']:.4f}"
            else:
                return False, "Failed to update consolidated record"
                
        except Exception as e:
            return False, f"Error processing buy trade: {str(e)}"
    
    def process_sell_trade(self, trade_data: Dict) -> Tuple[bool, str]:
        """
        Process a sell trade according to the specified formula.
        
        Formula:
        - Net proceeds = (Shares traded × price per share) - commission
        - Capital Gain or Loss = Net proceeds - (Shares traded × average price per share)
        - New quantity = Quantity - Shares traded
        """
        try:
            account = trade_data['Account']
            stock_symbol = trade_data['StockSymbol']
            shares_traded = int(trade_data['SharesTraded'])
            price_per_share = float(trade_data['PricePerShare'])
            commission = float(trade_data.get('Commission', 0))
            
            # Get existing consolidated record
            existing_record = self.data_manager.get_consolidated_record(account, stock_symbol)
            
            if not existing_record:
                return False, f"No existing holdings found for {stock_symbol} in {account}"
            
            current_quantity = int(existing_record['Quantity'])
            current_avg_price = float(existing_record['AveragePricePerShare'])
            current_capital_gain_loss = float(existing_record.get('CapitalGainLoss', 0))
            
            # Validate sufficient shares
            if shares_traded > current_quantity:
                return False, f"Insufficient shares. You have {current_quantity} shares, trying to sell {shares_traded}"
            
            # Calculate new values
            enriched_trade = self.enrich_trade_financials(trade_data)
            net_proceeds = float(enriched_trade['NetProceeds'])
            trade_capital_gain_loss = float(enriched_trade['CapitalGainLoss'])
            new_quantity = int(current_quantity - shares_traded)
            new_capital_gain_loss = current_capital_gain_loss + trade_capital_gain_loss

            trade_data.update(enriched_trade)
            
            # Update consolidated record
            updated_data = {
                'StockName': trade_data['StockName'],
                'Quantity': int(new_quantity),
                'AveragePricePerShare': current_avg_price,  # No change for sell
                'CapitalGainLoss': round(new_capital_gain_loss, 2),
                'DateOfAcquisition': existing_record['DateOfAcquisition']  # Keep original date
            }
            
            # Update consolidated record
            success = self.data_manager.update_consolidated_record(
                account, stock_symbol, updated_data
            )
            
            if success:
                return True, f"Sell trade processed successfully. Remaining quantity: {new_quantity}, Trade gain/loss: {trade_capital_gain_loss:.2f}, Total gain/loss: {new_capital_gain_loss:.2f}"
            else:
                return False, "Failed to update consolidated record"
                
        except Exception as e:
            return False, f"Error processing sell trade: {str(e)}"
    
    def process_transfer_trade(self, trade_data: Dict) -> Tuple[bool, str]:
        """
        Process a transfer trade - just record in trade history without affecting calculations.
        """
        try:
            # For transfers, we just record the trade without changing consolidated calculations
            return True, "Transfer trade recorded successfully (no calculations performed)"
        except Exception as e:
            return False, f"Error processing transfer trade: {str(e)}"
    
    def process_trade(self, trade_data: Dict) -> Tuple[bool, str]:
        """
        Process any type of trade based on the trade type.
        """
        trade_type = trade_data.get('TradeType', '').upper()

        is_valid, validation_error = self.validate_trade(trade_data)
        if not is_valid:
            return False, validation_error

        original_consolidated = self.data_manager.read_consolidated()

        # Then process based on trade type
        if trade_type == 'B':
            trade_data.update(self.enrich_trade_financials(trade_data))
            process_success, message = self.process_buy_trade(trade_data)
        elif trade_type == 'S':
            process_success, message = self.process_sell_trade(trade_data)
        elif trade_type == 'T':
            process_success, message = self.process_transfer_trade(trade_data)
        else:
            return False, f"Unknown trade type: {trade_type}. Use B (Buy), S (Sell), or T (Transfer)"

        if not process_success:
            return False, message

        trade_success = self.data_manager.add_trade(trade_data)
        if not trade_success:
            self.data_manager.write_consolidated(original_consolidated)
            return False, "Failed to record trade in trade history"

        return True, message
    
    def add_existing_holding(self, holding_data: Dict) -> Tuple[bool, str]:
        """
        Add an existing holding to the consolidated record (for pre-population).

        Formula:
        - Cost per share = Book cost / Quantity
        """
        try:
            account = holding_data['Account']
            stock_symbol = holding_data['StockSymbol']
            quantity = int(holding_data['Quantity'])
            book_cost = float(holding_data['BookCost'])

            if quantity <= 0:
                return False, "Quantity must be greater than 0"

            if book_cost <= 0:
                return False, "Book cost must be greater than 0"

            # Calculate cost per share
            cost_per_share = book_cost / quantity

            # Check if holding already exists
            existing_record = self.data_manager.get_consolidated_record(account, stock_symbol)
            if existing_record:
                return False, f"Holding for {stock_symbol} in {account} already exists. Use trade entry to add more shares."

            # Create new consolidated record
            updated_data = {
                'StockName': holding_data['StockName'],
                'Quantity': int(quantity),
                'AveragePricePerShare': round(cost_per_share, 4),
                'CapitalGainLoss': 0,
                'DateOfAcquisition': holding_data['DateOfAcquisition']
            }

            success = self.data_manager.update_consolidated_record(
                account, stock_symbol, updated_data
            )

            if success:
                return True, f"Existing holding added successfully. Quantity: {quantity}, Cost per share: ${cost_per_share:.4f}"
            else:
                return False, "Failed to add existing holding"

        except Exception as e:
            return False, f"Error adding existing holding: {str(e)}"

    def rebuild_holdings_from_trades(self, account: str, stock_symbol: str) -> Tuple[bool, str]:
        """
        Rebuild consolidated holdings for a specific account+symbol from trade history.
        Clears the existing consolidated record and replays all trades in chronological order.
        This ensures 100% accurate calculations after deleting a trade.
        """
        try:
            # Get all trades for this account+symbol (sorted by date)
            relevant_trades = self.data_manager.get_trades_for_account_symbol(account, stock_symbol)

            # Clear existing consolidated record
            self.data_manager.delete_consolidated_record(account, stock_symbol)

            if relevant_trades.empty:
                return True, f"No trades found for {stock_symbol} in {account}. Consolidated record cleared."

            # Replay each trade in chronological order
            trades_processed = 0
            for _, trade_row in relevant_trades.iterrows():
                trade_data = trade_row.to_dict()
                trade_type = trade_data.get('TradeType', '').upper()

                # Process each trade type (these methods only update consolidated, not trades.csv)
                if trade_type == 'B':
                    success, _ = self.process_buy_trade(trade_data)
                elif trade_type == 'S':
                    success, _ = self.process_sell_trade(trade_data)
                elif trade_type == 'T':
                    success, _ = self.process_transfer_trade(trade_data)
                else:
                    continue

                if success:
                    trades_processed += 1

            return True, f"Rebuilt {stock_symbol} in {account}: Processed {trades_processed} trade(s)"

        except Exception as e:
            return False, f"Error rebuilding holdings: {str(e)}"

    def delete_trade_and_rebuild(self, trade_index: int) -> Tuple[bool, str]:
        """
        Delete a trade and rebuild consolidated holdings for the affected account+symbol.
        This ensures 100% accurate calculations by replaying all remaining trades.
        """
        try:
            # Get the trade info before deleting it
            trade = self.data_manager.get_trade_at_index(trade_index)
            if not trade:
                return False, f"Trade #{trade_index} not found"

            account = trade['Account']
            stock_symbol = trade['StockSymbol']

            # Delete the trade from trades.csv
            delete_success = self.data_manager.delete_trade(trade_index)
            if not delete_success:
                return False, "Failed to delete trade from history"

            # Rebuild consolidated holdings from remaining trades
            rebuild_success, rebuild_message = self.rebuild_holdings_from_trades(account, stock_symbol)

            if rebuild_success:
                return True, f"Trade deleted and holdings rebuilt. {rebuild_message}"
            else:
                return False, f"Trade deleted but rebuild failed: {rebuild_message}"

        except Exception as e:
            return False, f"Error deleting trade and rebuilding: {str(e)}"

    def preview_buy_trade(self, account: str, stock_symbol: str, shares_traded: int,
                         price_per_share: float, commission: float) -> Dict:
        """
        Calculate preview values for a buy trade without persisting.

        Returns:
            Dict with keys: cost_of_trade, new_quantity, new_avg_price, new_book_value
        """
        try:
            # Calculate cost of this trade
            cost_of_trade = (shares_traded * price_per_share) + commission

            # Check if we already own this stock
            record = self.data_manager.get_consolidated_record(account, stock_symbol)

            if record:
                # Existing holding - calculate new averages
                current_quantity = int(record['Quantity'])
                current_avg_price = float(record['AveragePricePerShare'])
                total_cost_existing = current_quantity * current_avg_price
                new_quantity = current_quantity + shares_traded
                new_avg_price = (total_cost_existing + cost_of_trade) / new_quantity
                new_book_value = new_quantity * new_avg_price
            else:
                # New holding
                new_quantity = shares_traded
                new_avg_price = cost_of_trade / shares_traded
                new_book_value = cost_of_trade

            return {
                'cost_of_trade': cost_of_trade,
                'new_quantity': new_quantity,
                'new_avg_price': new_avg_price,
                'new_book_value': new_book_value
            }
        except Exception as e:
            raise ValueError(f"Error calculating buy preview: {str(e)}")

    def preview_sell_trade(self, account: str, stock_symbol: str, shares_traded: int,
                          price_per_share: float, commission: float) -> Tuple[bool, Dict, str]:
        """
        Calculate preview values for a sell trade without persisting.

        Returns:
            Tuple of (success, preview_dict, error_message)
            preview_dict has keys: net_proceeds, trade_gain_loss, new_quantity, new_total_gain_loss
        """
        try:
            # Fetch existing holding
            record = self.data_manager.get_consolidated_record(account, stock_symbol)
            if not record:
                return False, {}, f"No existing holdings found for {stock_symbol} in {account}"

            current_quantity = int(record['Quantity'])
            current_avg_price = float(record['AveragePricePerShare'])
            current_capital_gain_loss = float(record.get('CapitalGainLoss', 0))

            # Validate sufficient shares
            if shares_traded > current_quantity:
                return False, {}, f"Insufficient shares. You have {current_quantity}, trying to sell {shares_traded}"

            # Calculate preview values
            net_proceeds = (shares_traded * price_per_share) - commission
            trade_capital_gain_loss = net_proceeds - (shares_traded * current_avg_price)
            new_quantity = current_quantity - shares_traded
            new_capital_gain_loss = current_capital_gain_loss + trade_capital_gain_loss

            gross_proceeds = shares_traded * price_per_share
            cost_basis = shares_traded * current_avg_price

            return True, {
                'gross_proceeds': gross_proceeds,
                'net_proceeds': net_proceeds,
                'cost_basis': cost_basis,
                'average_cost_at_sale': current_avg_price,
                'trade_gain_loss': trade_capital_gain_loss,
                'new_quantity': new_quantity,
                'new_total_gain_loss': new_capital_gain_loss
            }, ""
        except Exception as e:
            return False, {}, f"Error calculating sell preview: {str(e)}"

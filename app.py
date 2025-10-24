import streamlit as st
import pandas as pd
from datetime import datetime, date
import sys
import os

# Add the utils directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))

from utils.data_manager import DataManager
from utils.calculations import TradeCalculator

# Page configuration
st.set_page_config(
    page_title="Stock Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize data manager and calculator
@st.cache_resource
def get_data_manager():
    return DataManager()

@st.cache_resource
def get_trade_calculator():
    return TradeCalculator(get_data_manager())

data_manager = get_data_manager()
calculator = get_trade_calculator()

# Sidebar navigation
st.sidebar.title("📈 Stock Tracker")
page = st.sidebar.selectbox(
    "Navigate",
    ["Consolidated Record", "Trade Entry", "Pre-populate Database", "Trade History"]
)

# Helper functions
def format_currency(value):
    """Format currency values."""
    if pd.isna(value):
        return "$0.00"
    return f"${value:,.2f}"

def format_number(value):
    """Format number values."""
    if pd.isna(value):
        return "0"
    return f"{value:,.0f}"

# Page 1: Consolidated Record (Dashboard)
if page == "Consolidated Record":
    st.title("📊 Consolidated Record")
    st.markdown("View all your stock holdings across all accounts")
    
    # Load consolidated data
    df = data_manager.read_consolidated()
    
    if df.empty:
        st.info("No holdings found. Use 'Pre-populate Database' to add existing holdings or 'Trade Entry' to record trades.")
    else:
        # Summary statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_holdings = len(df)
            st.metric("Total Holdings", total_holdings)
        
        with col2:
            total_quantity = df['Quantity'].sum()
            st.metric("Total Shares", format_number(total_quantity))
        
        with col3:
            total_value = (df['Quantity'] * df['AveragePricePerShare']).sum()
            st.metric("Total Value", format_currency(total_value))
        
        with col4:
            total_gain_loss = df['CapitalGainLoss'].sum()
            st.metric("Total Gain/Loss", format_currency(total_gain_loss))
        
        # Filters
        st.subheader("Filters")
        col1, col2 = st.columns(2)
        
        with col1:
            accounts = ['All'] + data_manager.get_accounts()
            selected_account = st.selectbox("Filter by Account", accounts)
        
        with col2:
            symbols = ['All'] + data_manager.get_stock_symbols()
            selected_symbol = st.selectbox("Filter by Stock Symbol", symbols)
        
        # Apply filters
        filtered_df = df.copy()
        if selected_account != 'All':
            filtered_df = filtered_df[filtered_df['Account'] == selected_account]
        if selected_symbol != 'All':
            filtered_df = filtered_df[filtered_df['StockSymbol'] == selected_symbol]
        
        # Display table
        if not filtered_df.empty:
            # Format the dataframe for display
            display_df = filtered_df.copy()
            display_df['Quantity'] = display_df['Quantity'].apply(format_number)
            display_df['AveragePricePerShare'] = display_df['AveragePricePerShare'].apply(format_currency)
            display_df['CapitalGainLoss'] = display_df['CapitalGainLoss'].apply(format_currency)
            display_df['DateOfAcquisition'] = pd.to_datetime(display_df['DateOfAcquisition']).dt.strftime('%Y-%m-%d')
            
            # Rename columns for better display
            display_df = display_df.rename(columns={
                'Account': 'Account',
                'StockName': 'Stock Name',
                'StockSymbol': 'Symbol',
                'Quantity': 'Quantity',
                'AveragePricePerShare': 'Avg Price/Share',
                'CapitalGainLoss': 'Gain/Loss',
                'DateOfAcquisition': 'Date Acquired'
            })
            
            st.dataframe(display_df, width='stretch')
        else:
            st.info("No holdings match the selected filters.")

# Page 2: Trade Entry
elif page == "Trade Entry":
    st.title("📝 Trade Entry")
    st.markdown("Record new stock trades")
    
    # Get existing accounts for dropdown
    existing_accounts = data_manager.get_accounts()
    
    with st.form("trade_form"):
        st.subheader("Trade Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Account selection
            if existing_accounts:
                account = st.selectbox("Account", existing_accounts)
            else:
                account = st.text_input("Account", placeholder="e.g., TFSA, RRSP, Personal")
            
            stock_name = st.text_input("Stock Name", placeholder="e.g., Apple Inc.")
            stock_symbol = st.text_input("Stock Symbol", placeholder="e.g., AAPL").upper()
            trade_date = st.date_input("Date of Trade", value=date.today())
        
        with col2:
            trade_type = st.selectbox("Trade Type", ["B", "S", "T"], 
                                    format_func=lambda x: {"B": "Buy", "S": "Sell", "T": "Transfer"}[x])
            shares_traded = st.number_input("Shares Traded", min_value=0.0, step=0.01, format="%.2f")
            price_per_share = st.number_input("Price per Share ($)", min_value=0.0, step=0.01, format="%.2f")
            commission = st.number_input("Commission ($)", min_value=0.0, step=0.01, format="%.2f", value=0.0)
        
        submitted = st.form_submit_button("Process Trade", type="primary")
        
        if submitted:
            # Validation
            if not account.strip():
                st.error("Please enter an account name.")
            elif not stock_name.strip():
                st.error("Please enter a stock name.")
            elif not stock_symbol.strip():
                st.error("Please enter a stock symbol.")
            elif shares_traded <= 0:
                st.error("Shares traded must be greater than 0.")
            elif price_per_share <= 0:
                st.error("Price per share must be greater than 0.")
            else:
                # Prepare trade data
                trade_data = {
                    'Account': account.strip(),
                    'StockName': stock_name.strip(),
                    'StockSymbol': stock_symbol.strip(),
                    'DateOfTrade': trade_date.strftime('%Y-%m-%d'),
                    'TradeType': trade_type,
                    'SharesTraded': shares_traded,
                    'PricePerShare': price_per_share,
                    'Commission': commission
                }
                
                # Process the trade
                with st.spinner("Processing trade..."):
                    success, message = calculator.process_trade(trade_data)
                
                if success:
                    st.success(message)
                    st.rerun()  # Refresh the page to show updated data
                else:
                    st.error(message)

# Page 3: Pre-populate Database
elif page == "Pre-populate Database":
    st.title("📥 Pre-populate Database")
    st.markdown("Add existing stock holdings to the database")
    
    with st.form("prepopulate_form"):
        st.subheader("Existing Holding Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Account selection
            existing_accounts = data_manager.get_accounts()
            if existing_accounts:
                account = st.selectbox("Account", existing_accounts)
            else:
                account = st.text_input("Account", placeholder="e.g., TFSA, RRSP, Personal")
            
            stock_name = st.text_input("Stock Name", placeholder="e.g., Apple Inc.")
            stock_symbol = st.text_input("Stock Symbol", placeholder="e.g., AAPL").upper()
            quantity = st.number_input("Quantity", min_value=0.0, step=0.01, format="%.2f")
        
        with col2:
            book_cost = st.number_input("Book Cost ($)", min_value=0.0, step=0.01, format="%.2f")
            acquisition_date = st.date_input("Date of Acquisition")
            
            # Show calculated cost per share
            if quantity > 0 and book_cost > 0:
                cost_per_share = book_cost / quantity
                st.metric("Cost per Share", format_currency(cost_per_share))
        
        submitted = st.form_submit_button("Add Holding", type="primary")
        
        if submitted:
            # Validation
            if not account.strip():
                st.error("Please enter an account name.")
            elif not stock_name.strip():
                st.error("Please enter a stock name.")
            elif not stock_symbol.strip():
                st.error("Please enter a stock symbol.")
            elif quantity <= 0:
                st.error("Quantity must be greater than 0.")
            elif book_cost <= 0:
                st.error("Book cost must be greater than 0.")
            else:
                # Prepare holding data
                holding_data = {
                    'Account': account.strip(),
                    'StockName': stock_name.strip(),
                    'StockSymbol': stock_symbol.strip(),
                    'Quantity': quantity,
                    'BookCost': book_cost,
                    'DateOfAcquisition': acquisition_date.strftime('%Y-%m-%d')
                }
                
                # Add the holding
                with st.spinner("Adding holding..."):
                    success, message = calculator.add_existing_holding(holding_data)
                
                if success:
                    st.success(message)
                    st.rerun()  # Refresh the page
                else:
                    st.error(message)

# Page 4: Trade History
elif page == "Trade History":
    st.title("📋 Trade History")
    st.markdown("View all recorded trades")
    
    # Load trades data
    df = data_manager.read_trades()
    
    if df.empty:
        st.info("No trades found. Use 'Trade Entry' to record trades.")
    else:
        # Filters
        st.subheader("Filters")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            accounts = ['All'] + data_manager.get_accounts()
            selected_account = st.selectbox("Filter by Account", accounts, key="history_account")
        
        with col2:
            symbols = ['All'] + data_manager.get_stock_symbols()
            selected_symbol = st.selectbox("Filter by Stock Symbol", symbols, key="history_symbol")
        
        with col3:
            trade_types = ['All', 'B', 'S', 'T']
            selected_type = st.selectbox("Filter by Trade Type", trade_types, 
                                       format_func=lambda x: {"All": "All", "B": "Buy", "S": "Sell", "T": "Transfer"}[x])
        
        # Apply filters
        filtered_df = df.copy()
        if selected_account != 'All':
            filtered_df = filtered_df[filtered_df['Account'] == selected_account]
        if selected_symbol != 'All':
            filtered_df = filtered_df[filtered_df['StockSymbol'] == selected_symbol]
        if selected_type != 'All':
            filtered_df = filtered_df[filtered_df['TradeType'] == selected_type]
        
        # Display table
        if not filtered_df.empty:
            # Format the dataframe for display
            display_df = filtered_df.copy()
            display_df['SharesTraded'] = display_df['SharesTraded'].apply(format_number)
            display_df['PricePerShare'] = display_df['PricePerShare'].apply(format_currency)
            display_df['Commission'] = display_df['Commission'].apply(format_currency)
            display_df['DateOfTrade'] = pd.to_datetime(display_df['DateOfTrade']).dt.strftime('%Y-%m-%d')
            
            # Rename columns for better display
            display_df = display_df.rename(columns={
                'Account': 'Account',
                'StockName': 'Stock Name',
                'StockSymbol': 'Symbol',
                'DateOfTrade': 'Date',
                'TradeType': 'Type',
                'SharesTraded': 'Shares',
                'PricePerShare': 'Price/Share',
                'Commission': 'Commission'
            })
            
            # Format trade type
            display_df['Type'] = display_df['Type'].map({'B': 'Buy', 'S': 'Sell', 'T': 'Transfer'})
            
            st.dataframe(display_df, width='stretch')
            
            # Summary statistics
            st.subheader("Summary")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_trades = len(filtered_df)
                st.metric("Total Trades", total_trades)
            
            with col2:
                total_shares = filtered_df['SharesTraded'].sum()
                st.metric("Total Shares Traded", format_number(total_shares))
            
            with col3:
                total_commission = filtered_df['Commission'].sum()
                st.metric("Total Commission", format_currency(total_commission))
        else:
            st.info("No trades match the selected filters.")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**Stock Tracker v1.0**")
st.sidebar.markdown("Built with Streamlit")

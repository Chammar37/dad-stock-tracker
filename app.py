import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sys
import os
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Add the utils directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))

from utils.data_manager import DataManager
from utils.calculations import TradeCalculator

# Chart Theme Configuration
CHART_COLORS = {
    'primary': '#4A90E2',
    'primary_transparent': 'rgba(74, 144, 226, 0.1)',
    'primary_semi': 'rgba(74, 144, 226, 0.6)',
    'primary_dark': 'rgba(74, 144, 226, 0.8)',
    'title': '#2C3E50',
    'text': '#7F8C8D',
    'grid': 'rgba(127, 140, 141, 0.2)'
}

CHART_FONTS = {
    'title_large': dict(size=20, color=CHART_COLORS['title']),
    'title_medium': dict(size=16, color=CHART_COLORS['title']),
    'axis_title': dict(size=14, color=CHART_COLORS['text']),
    'axis_title_small': dict(size=12, color=CHART_COLORS['text']),
    'tick_large': dict(size=12, color=CHART_COLORS['text']),
    'tick_small': dict(size=10, color=CHART_COLORS['text'])
}

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
    ["Consolidated Record", "Trade Entry", "Pre-populate Database", "Trade History", "Stock Charts"]
)

# Helper functions
def format_currency(value):
    """Format currency values."""
    if pd.isna(value):
        return "$0.00"
    return f"${value:,.2f}"

def format_number(value):
    """Format number values with appropriate decimal places."""
    if pd.isna(value):
        return "0"
    
    # If the value is less than 1, show up to 4 decimal places
    if abs(value) < 1:
        return f"{value:.4f}".rstrip('0').rstrip('.')
    # If the value is less than 10, show 2 decimal places
    elif abs(value) < 10:
        return f"{value:.2f}".rstrip('0').rstrip('.')
    # For larger values, show no decimal places
    else:
        return f"{value:,.0f}"

# Chart Helper Functions
def get_common_chart_layout(height=500):
    """Returns common layout settings for charts."""
    return {
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'hovermode': 'x unified',
        'height': height
    }

def get_axis_style(title_text, is_large=True):
    """Returns styled axis configuration."""
    return {
        'title': dict(
            text=title_text, 
            font=CHART_FONTS['axis_title'] if is_large else CHART_FONTS['axis_title_small']
        ),
        'tickfont': CHART_FONTS['tick_large'] if is_large else CHART_FONTS['tick_small'],
        'gridcolor': CHART_COLORS['grid'],
        'showgrid': True,
        'zeroline': False
    }

def create_price_chart(data, symbol, stock_name, timeframe):
    """Creates a styled price line chart."""
    fig = go.Figure()
    
    # Main price line
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['Close'],
        mode='lines',
        name=symbol,
        line=dict(
            color=CHART_COLORS['primary'],
            width=3,
            shape='spline',
            smoothing=0.3
        ),
        hovertemplate='<b>%{x}</b><br>Price: $%{y:.2f}<extra></extra>'
    ))
    
    # Fill under line
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['Close'],
        mode='lines',
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip',
        fill='tonexty',
        fillcolor=CHART_COLORS['primary_transparent']
    ))
    
    # Apply layout
    layout = get_common_chart_layout(height=500)
    layout.update({
        'title': dict(
            text=f"{symbol} - {stock_name} ({timeframe})",
            font=CHART_FONTS['title_large'],
            x=0.5,
            xanchor='center'
        ),
        'xaxis': get_axis_style("Date", is_large=True),
        'yaxis': {**get_axis_style("Price ($)", is_large=True), 'tickformat': '$.2f'},
        'margin': dict(l=50, r=50, t=80, b=50),
        'showlegend': True,
        'legend': dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=CHART_FONTS['tick_large']
        )
    })
    
    fig.update_layout(layout)
    return fig

def create_volume_chart(data, symbol, timeframe):
    """Creates a styled volume bar chart."""
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=data.index,
        y=data['Volume'],
        name="Volume",
        marker_color=CHART_COLORS['primary_semi'],
        marker_line_color=CHART_COLORS['primary_dark'],
        marker_line_width=1,
        hovertemplate='<b>%{x}</b><br>Volume: %{y:,}<extra></extra>'
    ))
    
    # Apply layout
    layout = get_common_chart_layout(height=300)
    layout.update({
        'title': dict(
            text=f"{symbol} Volume ({timeframe})",
            font=CHART_FONTS['title_medium'],
            x=0.5,
            xanchor='center'
        ),
        'xaxis': get_axis_style("Date", is_large=False),
        'yaxis': get_axis_style("Volume", is_large=False),
        'margin': dict(l=50, r=50, t=60, b=50),
        'showlegend': False
    })
    
    fig.update_layout(layout)
    return fig

# Helper function to get available stocks for sell/transfer
def get_available_stocks_for_sell(account: str = None) -> list:
    """
    Get stocks available for selling/transferring from consolidated view.
    Returns list of tuples: (symbol, display_name, quantity)
    """
    try:
        df = data_manager.read_consolidated()
        if df.empty:
            return []
        
        # Filter by account if specified
        if account:
            df = df[df['Account'] == account]
        
        # Only include stocks with quantity > 0 (use small epsilon for floating point precision)
        df = df[df['Quantity'] > 0.0001]
        
        available_stocks = []
        for _, row in df.iterrows():
            symbol = row['StockSymbol']
            name = row['StockName']
            quantity = row['Quantity']
            account_name = row['Account']
            
            # Format quantity display based on size
            if quantity < 1:
                qty_display = f"{quantity:.3f}"
            else:
                qty_display = f"{quantity:.0f}"
            
            display_name = f"{symbol} - {name} ({qty_display} shares in {account_name})"
            available_stocks.append((symbol, display_name, quantity))
        
        return available_stocks
    except:
        return []

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
    
    # Trade type selection (outside form for immediate updates)
    trade_type = st.selectbox("Trade Type", ["B", "S", "T"], 
                            format_func=lambda x: {"B": "Buy", "S": "Sell", "T": "Transfer"}[x])
    
    with st.form("trade_form"):
        st.subheader("Trade Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Account selection
            if existing_accounts:
                account = st.selectbox("Account", existing_accounts)
            else:
                account = st.text_input("Account", placeholder="e.g., TFSA, RRSP, Personal")
            
            # Initialize variables
            stock_symbol = ""
            stock_name = ""
            max_quantity = None
            
            # Conditional stock input based on trade type
            if trade_type in ["S", "T"]:  # Sell or Transfer
                # Get available stocks for this account
                available_stocks = get_available_stocks_for_sell(account if account else None)
                
                if available_stocks:
                    # Create options for dropdown
                    stock_options = [f"{display}" for _, display, _ in available_stocks]
                    stock_options.insert(0, "Select a stock to sell/transfer...")
                    
                    selected_stock_display = st.selectbox(
                        "Select Stock to Sell/Transfer",
                        stock_options,
                        key="sell_stock_select"
                    )
                    
                    if selected_stock_display != "Select a stock to sell/transfer...":
                        # Extract symbol and name from selection
                        for symbol, display, quantity in available_stocks:
                            if display == selected_stock_display:
                                stock_symbol = symbol
                                # Extract stock name from display
                                stock_name = display.split(" - ")[1].split(" (")[0]
                                max_quantity = float(quantity)  # Ensure it's a float
                                break
                        
                        # Show available quantity
                        st.info(f"Available: {max_quantity:.0f} shares")
                    else:
                        stock_symbol = ""
                        stock_name = ""
                        max_quantity = 0.0  # Ensure it's a float
                else:
                    st.warning("No stocks available for selling/transferring in this account.")
                    stock_symbol = ""
                    stock_name = ""
                    max_quantity = 0.0  # Ensure it's a float
            else:  # Buy
                stock_name = st.text_input("Stock Name", placeholder="e.g., Apple Inc.")
                stock_symbol = st.text_input("Stock Symbol", placeholder="e.g., AAPL").upper()
                max_quantity = None  # No limit for buying
            
            trade_date = st.date_input("Date of Trade", value=date.today())
        
        with col2:
            # Shares traded with conditional max value
            if trade_type in ["S", "T"] and max_quantity is not None and max_quantity > 0:
                # Determine appropriate step size based on max quantity
                if max_quantity < 1:
                    step_size = 0.001  # For very small quantities like Bitcoin
                elif max_quantity < 10:
                    step_size = 0.01   # For small quantities
                else:
                    step_size = 0.01   # For larger quantities
                
                shares_traded = st.number_input(
                    "Shares Traded", 
                    min_value=0.0, 
                    max_value=float(max_quantity),  # Ensure it's a float
                    step=step_size, 
                    format="%.3f" if max_quantity < 1 else "%.2f",
                    help=f"Maximum: {max_quantity:.3f} shares" if max_quantity < 1 else f"Maximum: {max_quantity:.0f} shares"
                )
            else:
                shares_traded = st.number_input("Shares Traded", min_value=0.0, step=0.01, format="%.2f")
            
            price_per_share = st.number_input("Price per Share ($)", min_value=0.0, step=0.01, format="%.2f")
            commission = st.number_input("Commission ($)", min_value=0.0, step=0.01, format="%.2f", value=0.0)
        
        submitted = st.form_submit_button("Process Trade", type="primary")
        
        if submitted:
            # Ensure shares_traded is a proper float
            try:
                shares_traded = float(shares_traded)
            except (ValueError, TypeError):
                shares_traded = 0.0
            
            # Validation with better error handling
            if not account.strip():
                st.error("Please enter an account name.")
            elif trade_type in ["S", "T"] and (not stock_symbol.strip() or stock_symbol == ""):
                st.error("Please select a stock to sell/transfer.")
            elif trade_type == "B" and (not stock_name.strip() or not stock_symbol.strip()):
                st.error("Please enter both stock name and symbol for buying.")
            elif shares_traded <= 0 or shares_traded < 0.0001:  # Handle very small decimal values
                st.error(f"Shares traded must be greater than 0. You entered: {shares_traded}")
            elif trade_type in ["S", "T"] and max_quantity is not None and shares_traded > max_quantity + 0.0001:  # Add small epsilon for precision
                if max_quantity < 1:
                    st.error(f"Cannot sell/transfer more than {max_quantity:.3f} shares. You tried to sell: {shares_traded:.3f} shares.")
                else:
                    st.error(f"Cannot sell/transfer more than {max_quantity:.0f} shares. You tried to sell: {shares_traded:.0f} shares.")
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
                    st.info("Redirecting to Consolidated Record to view updated holdings...")
                    # Set session state to redirect to Consolidated Record
                    st.session_state.page = "Consolidated Record"
                    st.rerun()
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
                    st.info("Redirecting to Consolidated Record to view updated holdings...")
                    # Set session state to redirect to Consolidated Record
                    st.session_state.page = "Consolidated Record"
                    st.rerun()
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

# Page 5: Stock Charts
elif page == "Stock Charts":
    st.title("📈 Stock Charts")
    st.markdown("Live stock charts for your holdings")
    
    # Load consolidated data
    df = data_manager.read_consolidated()
    
    if df.empty:
        st.info("No holdings found. Add some stocks to your portfolio to see charts.")
    else:
        # Get unique stock symbols from holdings
        symbols = df['StockSymbol'].unique().tolist()
        
        # Timeframe selection
        col1, col2 = st.columns([1, 3])
        
        with col1:
            timeframe = st.selectbox(
                "Timeframe",
                ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
                index=2  # Default to 1mo
            )
        
        with col2:
            selected_symbol = st.selectbox(
                "Select Stock",
                symbols,
                format_func=lambda x: f"{x} - {df[df['StockSymbol']==x]['StockName'].iloc[0]}"
            )
        
        # Fetch stock data
        @st.cache_data(ttl=300)  # Cache for 5 minutes
        def get_stock_data(symbol, period):
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period=period)
                
                if data.empty:
                    st.warning(f"No data available for {symbol} with period {period}")
                    return None, None
                
                info = ticker.info
                return data, info
            except Exception as e:
                st.error(f"Error fetching data for {symbol}: {e}")
                return None, None
        
        with st.spinner(f"Loading {selected_symbol} data..."):
            data, info = get_stock_data(selected_symbol, timeframe)
        
        if data is not None and not data.empty:
            # Get current price and change
            current_price = data['Close'].iloc[-1]
            prev_close = data['Close'].iloc[-2] if len(data) > 1 else current_price
            price_change = current_price - prev_close
            price_change_pct = (price_change / prev_close) * 100
            
            # Display current price info
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Current Price", f"${current_price:.2f}")
            
            with col2:
                st.metric("Change", f"${price_change:.2f}", f"{price_change_pct:.2f}%")
            
            with col3:
                # Get holding info
                holding = df[df['StockSymbol'] == selected_symbol].iloc[0]
                st.metric("Your Shares", f"{holding['Quantity']:.0f}")
            
            with col4:
                total_value = holding['Quantity'] * current_price
                st.metric("Total Value", f"${total_value:,.2f}")
            
            # Create charts using helper functions
            stock_name = df[df['StockSymbol']==selected_symbol]['StockName'].iloc[0]
            fig = create_price_chart(data, selected_symbol, stock_name, timeframe)
            st.plotly_chart(fig, use_container_width=True)
            
            # Volume chart
            if 'Volume' in data.columns:
                fig_volume = create_volume_chart(data, selected_symbol, timeframe)
                st.plotly_chart(fig_volume, use_container_width=True)
            
            # Portfolio performance section
            st.subheader("Portfolio Performance")
            
            # Calculate portfolio performance for this stock
            holding = df[df['StockSymbol'] == selected_symbol].iloc[0]
            avg_cost = holding['AveragePricePerShare']
            shares = holding['Quantity']
            cost_basis = shares * avg_cost
            current_value = shares * current_price
            unrealized_gain = current_value - cost_basis
            unrealized_gain_pct = (unrealized_gain / cost_basis) * 100
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Cost Basis", f"${cost_basis:,.2f}")
            
            with col2:
                st.metric("Current Value", f"${current_value:,.2f}")
            
            with col3:
                st.metric("Unrealized Gain/Loss", f"${unrealized_gain:,.2f}", f"{unrealized_gain_pct:.2f}%")
            
            # Stock info
            if info:
                st.subheader("Stock Information")
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'marketCap' in info:
                        market_cap = info['marketCap'] / 1e9  # Convert to billions
                        st.metric("Market Cap", f"${market_cap:.1f}B")
                    
                    if 'peRatio' in info and info['peRatio']:
                        st.metric("P/E Ratio", f"{info['peRatio']:.2f}")
                
                with col2:
                    if 'dividendYield' in info and info['dividendYield']:
                        dividend_yield = info['dividendYield'] * 100
                        st.metric("Dividend Yield", f"{dividend_yield:.2f}%")
                    
                    if 'beta' in info and info['beta']:
                        st.metric("Beta", f"{info['beta']:.2f}")
        
        else:
            st.error(f"Could not fetch data for {selected_symbol}. Please check the symbol and try again.")
        
        # Portfolio overview
        st.subheader("Portfolio Overview")
        
        # Create a simple portfolio performance chart
        portfolio_data = []
        for symbol in symbols:
            holding = df[df['StockSymbol'] == symbol].iloc[0]
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period="1d")
                if not data.empty:
                    current_price = data['Close'].iloc[-1]
                else:
                    continue
                portfolio_data.append({
                    'Symbol': symbol,
                    'Shares': holding['Quantity'],
                    'Avg Cost': holding['AveragePricePerShare'],
                    'Current Price': current_price,
                    'Cost Basis': holding['Quantity'] * holding['AveragePricePerShare'],
                    'Current Value': holding['Quantity'] * current_price,
                    'Gain/Loss': (holding['Quantity'] * current_price) - (holding['Quantity'] * holding['AveragePricePerShare'])
                })
            except:
                continue
        
        if portfolio_data:
            portfolio_df = pd.DataFrame(portfolio_data)
            
            # Portfolio summary
            total_cost_basis = portfolio_df['Cost Basis'].sum()
            total_current_value = portfolio_df['Current Value'].sum()
            total_gain_loss = total_current_value - total_cost_basis
            total_gain_loss_pct = (total_gain_loss / total_cost_basis) * 100
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Cost Basis", f"${total_cost_basis:,.2f}")
            
            with col2:
                st.metric("Total Current Value", f"${total_current_value:,.2f}")
            
            with col3:
                st.metric("Total Gain/Loss", f"${total_gain_loss:,.2f}")
            
            with col4:
                st.metric("Total Return", f"{total_gain_loss_pct:.2f}%")
            
            # Portfolio allocation pie chart
            fig_pie = px.pie(
                portfolio_df, 
                values='Current Value', 
                names='Symbol',
                title="Portfolio Allocation by Value"
            )
            st.plotly_chart(fig_pie, use_container_width=True)


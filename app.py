import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sys
import os
import hmac
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from dotenv import load_dotenv


load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))

# Add the utils directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))

from utils.data_manager_factory import create_data_manager
from utils.calculations import TradeCalculator
from utils.ui_helpers import (
    BUTTON_STYLES_CSS,
    add_row_numbers,
    build_account_options,
    build_available_stock_options,
    build_holding_summary,
    build_stock_option_lookup,
    build_trade_quantity_context,
    calculate_cost_per_share,
    find_existing_holding_by_symbol,
    format_currency,
    format_number,
    normalize_trade_quantity_state,
    NEW_ACCOUNT_OPTION,
    reset_invalid_selectbox_value,
    reset_prepopulate_state,
    resolve_account_input,
    reset_trade_entry_state,
)

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

# Custom CSS for button colors
st.markdown(BUTTON_STYLES_CSS, unsafe_allow_html=True)


def get_configured_app_password() -> str | None:
    try:
        configured_password = st.secrets.get("auth", {}).get("app_password")
    except Exception:
        configured_password = None
    return configured_password or os.environ.get("STOCK_TRACKER_APP_PASSWORD")


def require_app_password():
    configured_password = get_configured_app_password()
    if not configured_password or st.session_state.get("authenticated"):
        return

    st.title("Stock Tracker")
    password = st.text_input("Password", type="password")
    if st.button("Sign in"):
        if hmac.compare_digest(password, configured_password):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Invalid password")
    st.stop()


require_app_password()

# Initialize data manager and calculator
# Note: No caching here because these objects read/write CSV files that change frequently
# Caching would prevent seeing updates from new trades
data_manager = create_data_manager()
calculator = TradeCalculator(data_manager)

# One-time migration to integerize quantities in CSVs
try:
    data_manager.migrate_integer_quantities()
except Exception:
    pass

# Sidebar navigation
st.sidebar.title("📈 Stock Tracker")
page = st.sidebar.selectbox(
    "Navigate",
    ["Consolidated Record", "Trade Entry", "Pre-populate Database", "Trade History", "Stock Charts"]
)

# Helper function to resolve TSX symbols (tries .TO first, then falls back to plain symbol)
@st.cache_data(ttl=86400)
def resolve_stock_symbol(symbol: str) -> tuple[str | None, str | None]:
    """
    Resolves a stock symbol, trying TSX (.TO) first, then falling back to plain symbol.
    Returns tuple of (resolved_symbol, stock_name) or (None, None) if not found.
    """
    if not symbol:
        return None, None
    
    symbol = symbol.strip().upper()
    
    # If symbol already has an exchange suffix, use it as-is
    if '.' in symbol:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            if isinstance(info, dict) and info:
                name = info.get('shortName') or info.get('longName') or info.get('symbol')
                if name and isinstance(name, str) and name.strip():
                    return symbol, name.strip()
        except Exception:
            pass
        return None, None
    
    # Try TSX first (.TO suffix) for Canadian stocks
    tsx_symbol = f"{symbol}.TO"
    try:
        ticker = yf.Ticker(tsx_symbol)
        info = ticker.info
        if isinstance(info, dict) and info:
            name = info.get('shortName') or info.get('longName') or info.get('symbol')
            if name and isinstance(name, str) and name.strip():
                return tsx_symbol, name.strip()
    except Exception:
        pass
    
    # Fallback to plain symbol (for US stocks or if TSX lookup failed)
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if isinstance(info, dict) and info:
            name = info.get('shortName') or info.get('longName') or info.get('symbol')
            if name and isinstance(name, str) and name.strip():
                return symbol, name.strip()
    except Exception:
        pass
    
    return None, None

# Lookup helper for stock names from symbol (backward compatibility)
@st.cache_data(ttl=86400)
def lookup_stock_name(symbol: str) -> str | None:
    """Lookup stock name, resolving TSX symbols automatically."""
    _, name = resolve_stock_symbol(symbol)
    return name

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
        return build_available_stock_options(data_manager.read_consolidated(), account)
    except Exception:
        return []

# Page 1: Consolidated Record (Dashboard)
if page == "Consolidated Record":
    st.title("Consolidated Record")
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
            display_df = add_row_numbers(filtered_df)

            display_df['Quantity'] = display_df['Quantity'].apply(format_number)
            display_df['AveragePricePerShare'] = display_df['AveragePricePerShare'].apply(format_currency)
            display_df['CapitalGainLoss'] = display_df['CapitalGainLoss'].apply(format_currency)
            # Handle empty dates - show blank instead of NaT
            display_df['DateOfAcquisition'] = pd.to_datetime(display_df['DateOfAcquisition'], errors='coerce').apply(
                lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else ''
            )

            # Rename columns for better display (# column already named)
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

            st.subheader("Modify Consolidated Records")
            st.caption("Manual edits replace the selected consolidated row. Trade-history rebuilds can overwrite these edits for rows rebuilt from trades.")

            edit_options = []
            for idx in filtered_df.index:
                row = df.loc[idx]
                label = f"{row['Account']} | {row['StockSymbol']} | {row['StockName']}"
                edit_options.append((idx, label))

            selected_record = st.selectbox(
                "Select record to modify",
                options=[None] + edit_options,
                format_func=lambda option: "Select a record..." if option is None else option[1],
                key="consolidated_edit_select",
            )

            if selected_record is not None:
                selected_idx = selected_record[0]
                row = df.loc[selected_idx]

                with st.form("edit_consolidated_form"):
                    edit_col1, edit_col2 = st.columns(2)
                    with edit_col1:
                        edit_account = st.text_input("Account", value=str(row['Account']))
                        edit_symbol = st.text_input("Symbol", value=str(row['StockSymbol'])).upper()
                        edit_name = st.text_input("Stock Name", value=str(row['StockName']))
                        edit_quantity = st.number_input(
                            "Quantity",
                            min_value=0,
                            step=1,
                            format="%d",
                            value=int(row['Quantity']),
                        )
                    with edit_col2:
                        edit_average = st.number_input(
                            "Avg Price/Share",
                            min_value=0.0,
                            step=0.0001,
                            format="%.4f",
                            value=float(row['AveragePricePerShare']),
                        )
                        edit_gain_loss = st.number_input(
                            "Gain/Loss",
                            step=0.01,
                            format="%.2f",
                            value=float(row['CapitalGainLoss']),
                        )
                        existing_date = pd.to_datetime(row['DateOfAcquisition'], errors='coerce')
                        edit_date = st.date_input(
                            "Date Acquired",
                            value=existing_date.date() if pd.notna(existing_date) else date.today(),
                        )

                    save_edit = st.form_submit_button("Save Changes", type="primary")

                    if save_edit:
                        updated_data = {
                            'StockName': edit_name.strip(),
                            'Quantity': int(edit_quantity),
                            'AveragePricePerShare': float(edit_average),
                            'CapitalGainLoss': float(edit_gain_loss),
                            'DateOfAcquisition': edit_date.strftime('%Y-%m-%d'),
                        }
                        delete_old_key = (
                            str(row['Account']) != edit_account.strip()
                            or str(row['StockSymbol']) != edit_symbol.strip()
                        )

                        if delete_old_key:
                            saved = data_manager.replace_consolidated_record(
                                str(row['Account']),
                                str(row['StockSymbol']),
                                edit_account.strip(),
                                edit_symbol.strip(),
                                updated_data,
                            )
                        else:
                            saved = data_manager.update_consolidated_record(
                                str(row['Account']), str(row['StockSymbol']), updated_data
                            )

                        if saved:
                            st.success("Consolidated record updated")
                            st.rerun()

                confirm_delete = st.checkbox(
                    f"Confirm delete {row['StockSymbol']} from {row['Account']}",
                    key=f"confirm_delete_{selected_idx}",
                )
                if st.button("Delete Record", type="primary", disabled=not confirm_delete):
                    deleted = data_manager.delete_consolidated_record(
                        str(row['Account']), str(row['StockSymbol'])
                    )
                    if deleted:
                        st.success("Consolidated record deleted")
                        st.rerun()
        else:
            st.info("No holdings match the selected filters.")

# Page 2: Trade Entry
elif page == "Trade Entry":
    st.title("Trade Entry")
    st.markdown("Record new stock trades")

    # Display success message if one was stored from previous submission
    if "trade_success_message" in st.session_state:
        st.success(st.session_state.trade_success_message)
        del st.session_state.trade_success_message

    # Get existing accounts for dropdown
    existing_accounts = data_manager.get_accounts()
    
    # Trade type selection (outside form for immediate updates)
    trade_type = st.selectbox("Trade Type", ["B", "S", "T"], 
                            format_func=lambda x: {"B": "Buy", "S": "Sell", "T": "Transfer"}[x])
    
    st.subheader("Trade Details")

    selector_col1, selector_col2 = st.columns(2)

    with selector_col1:
        # Account selection lives outside the form so Sell options refresh immediately.
        if existing_accounts:
            selected_account = st.selectbox(
                "Account",
                build_account_options(existing_accounts),
                key="trade_account",
            )
            new_account = ""
            if selected_account == NEW_ACCOUNT_OPTION:
                new_account = st.text_input(
                    "New Account",
                    placeholder="e.g., TFSA, RRSP, Personal",
                    key="trade_new_account",
                )
            account = resolve_account_input(selected_account, new_account)
        else:
            account = st.text_input(
                "Account",
                placeholder="e.g., TFSA, RRSP, Personal",
                key="trade_account",
            )

    stock_symbol = ""
    stock_name = ""
    manual_stock_name = ""
    max_quantity = None
    resolved_symbol = None
    resolved_name = None

    with selector_col2:
        if trade_type in ["S", "T"]:
            available_stocks = get_available_stocks_for_sell(account if account else None)

            if available_stocks:
                stock_lookup = build_stock_option_lookup(available_stocks)
                stock_symbols = list(stock_lookup.keys())
                sell_options = [""] + stock_symbols
                reset_invalid_selectbox_value(
                    st.session_state,
                    "sell_stock_select",
                    sell_options,
                )

                selected_stock_symbol = st.selectbox(
                    "Select Stock to Sell/Transfer",
                    options=sell_options,
                    format_func=lambda symbol: (
                        "Select a stock to sell/transfer..."
                        if not symbol else str(stock_lookup[symbol]["display"])
                    ),
                    key="sell_stock_select",
                )

                if selected_stock_symbol:
                    stock_symbol = selected_stock_symbol
                    max_quantity = int(stock_lookup[stock_symbol]["quantity"])
                    record = data_manager.get_consolidated_record(account, stock_symbol)
                    stock_name = record["StockName"] if record else stock_symbol

                    st.markdown(build_holding_summary(
                        stock_symbol,
                        stock_name,
                        f" ({max_quantity:d} shares available)",
                    ))
                else:
                    max_quantity = 0
            else:
                reset_invalid_selectbox_value(
                    st.session_state,
                    "sell_stock_select",
                    [""],
                )
                st.warning("No stocks available for selling/transferring in this account.")
                max_quantity = 0
        else:
            reset_invalid_selectbox_value(
                st.session_state,
                "sell_stock_select",
                [""],
            )
            stock_symbol = st.text_input(
                "Stock Symbol",
                placeholder="e.g., AAPL",
                key="buy_stock_symbol",
            ).upper()
            existing_holding = find_existing_holding_by_symbol(
                data_manager.read_consolidated(), account if account else "", stock_symbol
            )
            if existing_holding:
                resolved_symbol = existing_holding["StockSymbol"]
                resolved_name = existing_holding["StockName"]

            if stock_symbol:
                if not existing_holding:
                    resolved_symbol, resolved_name = resolve_stock_symbol(stock_symbol)

                if resolved_name:
                    final_symbol = resolved_symbol if resolved_symbol else stock_symbol
                    record = existing_holding or data_manager.get_consolidated_record(
                        account if account else "", final_symbol
                    )
                    avg_price_display = ""
                    if record:
                        avg_price = float(record["AveragePricePerShare"])
                        avg_price_display = f" @ {format_currency(avg_price)}/share (current avg)"

                    st.markdown(build_holding_summary(final_symbol, resolved_name, avg_price_display))
                else:
                    manual_stock_name = st.text_input(
                        "Stock Name",
                        placeholder="Enter name for a new stock",
                        key="buy_stock_name",
                    )

    quantity_context = build_trade_quantity_context(trade_type, account, stock_symbol)
    normalize_trade_quantity_state(st.session_state, quantity_context)

    with st.form("trade_form", clear_on_submit=False):
        form_col1, form_col2 = st.columns(2)

        with form_col1:
            trade_date = st.date_input("Date of Trade", value=date.today())

        with form_col2:
            # Calculate max based on selection
            if trade_type in ["S", "T"] and max_quantity is not None and max_quantity > 0:
                shares_max = int(max_quantity)
                shares_help = f"Maximum: {shares_max} shares"
            else:
                shares_max = None
                shares_help = None

            shares_traded = st.number_input(
                "Shares Traded",
                min_value=1,
                max_value=shares_max,
                step=1,
                format="%d",
                help=shares_help,
                key="shares_input"
            )

            price_per_share = st.number_input(
                "Price per Share ($)",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                key="trade_price_per_share",
            )
            commission = st.number_input(
                "Commission ($)",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                value=9.99,
                key="trade_commission",
            )

        # Preview and Process buttons for Buy and Sell trades
        col_btn1, col_btn2 = st.columns(2)
        preview_submitted = False
        with col_btn1:
            if trade_type in ["B", "S"]:
                preview_help = "Preview calculations without saving" if trade_type == "B" else "Validate and preview this sell without saving"
                preview_submitted = st.form_submit_button(
                    "Preview Trade",
                    type="secondary",
                    help=preview_help
                )
        with col_btn2:
            submitted = st.form_submit_button("Process Trade", type="primary")
        
        # Handle preview for Buy and Sell without persisting
        if preview_submitted:
            # shares_traded already has the correct value from the widget
            try:
                shares_traded = int(shares_traded)
            except (ValueError, TypeError):
                shares_traded = 1
                st.warning("Invalid input for number of shares. Setting shares traded to 1.")

            # Common validation
            if not account.strip():
                st.error("Please enter an account name.")
            elif trade_type == "B" and (not stock_symbol.strip()):
                st.error("Please enter a stock symbol for buying.")
            elif trade_type == "S" and (not stock_symbol.strip()):
                st.error("Please select a stock to sell.")
            elif shares_traded < 1:
                st.error(f"Shares traded must be at least 1. You entered: {shares_traded}")
            elif price_per_share <= 0:
                st.error("Price per share must be greater than 0.")
            elif trade_type == "S" and (max_quantity is None or shares_traded > int(max_quantity)):
                st.error(f"Cannot sell more than {int(max_quantity) if max_quantity is not None else 0} shares.")
            else:
                # BUY PREVIEW
                if trade_type == "B":
                    # Use resolved symbol for buy trades
                    final_symbol = resolved_symbol if resolved_symbol else stock_symbol.strip()

                    # Use calculator's preview function
                    try:
                        preview = calculator.preview_buy_trade(
                            account=account.strip(),
                            stock_symbol=final_symbol,
                            shares_traded=shares_traded,
                            price_per_share=float(price_per_share),
                            commission=float(commission)
                        )

                        # Display preview in success box
                        st.success("✅ Preview - Buy Trade")
                        col_a, col_b, col_c, col_d = st.columns(4)
                        with col_a:
                            st.metric("Total Cost of Trade", format_currency(preview['cost_of_trade']))
                        with col_b:
                            st.metric("Traded Shares", format_number(preview['traded_shares']))
                        with col_c:
                            st.metric("New Avg Price/Share", format_currency(preview['new_avg_price']))
                        with col_d:
                            st.metric("New Book Value", format_currency(preview['new_book_value']))
                        st.caption(f"Total shares after trade: {format_number(preview['new_quantity'])}")
                    except Exception as e:
                        st.error(f"Error calculating preview: {str(e)}")

                # SELL PREVIEW
                elif trade_type == "S":
                    # Use calculator's preview function
                    success, preview, error = calculator.preview_sell_trade(
                        account=account.strip(),
                        stock_symbol=stock_symbol.strip(),
                        shares_traded=shares_traded,
                        price_per_share=float(price_per_share),
                        commission=float(commission)
                    )

                    if not success:
                        st.error(error)
                    else:
                        # Display preview in success box
                        st.success("✅ Preview - Sell Trade")
                        col_a, col_b, col_c, col_d = st.columns(4)
                        with col_a:
                            st.metric("Gross Proceeds", format_currency(preview['gross_proceeds']))
                        with col_b:
                            st.metric("Net Proceeds", format_currency(preview['net_proceeds']))
                        with col_c:
                            st.metric("Traded Shares", format_number(preview['traded_shares']))
                        with col_d:
                            st.metric("Trade Gain/Loss", format_currency(preview['trade_gain_loss']))
                        st.caption(f"Cost basis: {format_currency(preview['cost_basis'])} | Remaining quantity: {format_number(preview['new_quantity'])} | Total Gain/Loss after trade: {format_currency(preview['new_total_gain_loss'])}")

        if submitted:
            # shares_traded already has the correct value from the widget
            try:
                shares_traded = int(shares_traded)
            except (ValueError, TypeError):
                shares_traded = 1

            # Validation with better error handling
            if not account.strip():
                st.error("Please enter an account name.")
            elif trade_type in ["S", "T"] and (not stock_symbol.strip() or stock_symbol == ""):
                st.error("Please select a stock to sell/transfer.")
            elif trade_type == "B" and (not stock_symbol.strip()):
                st.error("Please enter a stock symbol for buying.")
            elif trade_type == "B" and not resolved_name and not manual_stock_name.strip():
                st.error("Please enter a stock name for a new holding.")
            elif not trade_date:
                st.error("Please select a valid trade date.")
            elif shares_traded < 1:
                st.error(f"Shares traded must be at least 1. You entered: {shares_traded}")
            elif trade_type in ["S", "T"] and max_quantity is not None and shares_traded > int(max_quantity):
                st.error(f"Cannot sell/transfer more than {int(max_quantity)} shares. You tried to sell: {shares_traded} shares.")
            elif price_per_share <= 0:
                st.error("Price per share must be greater than 0.")
            else:
                # For Buy trades, use resolved symbol (with .TO if TSX), otherwise use the symbol from selection
                if trade_type == "B" and resolved_symbol:
                    final_symbol = resolved_symbol
                    final_name = resolved_name or manual_stock_name or stock_symbol
                else:
                    final_symbol = stock_symbol.strip()
                    final_name = stock_name or manual_stock_name or stock_symbol
                
                # Prepare trade data
                trade_data = {
                    'Account': account.strip(),
                    'StockName': (final_name or final_symbol).strip(),
                    'StockSymbol': final_symbol.strip(),
                    'DateOfTrade': trade_date.strftime('%Y-%m-%d'),
                    'TradeType': trade_type,
                    'SharesTraded': int(shares_traded),
                    'PricePerShare': price_per_share,
                    'Commission': commission
                }
                
                # Process the trade
                with st.spinner("Processing trade..."):
                    success, message = calculator.process_trade(trade_data)

                if success:
                    # Store success message in session state to show after rerun
                    st.session_state.trade_success_message = "Trade Completed"
                    # Clear only after successful processing (do not clear on preview)
                    reset_trade_entry_state(st.session_state)
                    # Force page refresh to clear form
                    st.rerun()
                else:
                    st.error(message)

# Page 3: Pre-populate Database
elif page == "Pre-populate Database":
    st.title("Pre-populate Database")
    st.markdown("Add existing stock holdings to the database")

    if st.session_state.pop("prepopulate_reset_requested", False):
        reset_prepopulate_state(st.session_state)

    if "prepopulate_success_message" in st.session_state:
        st.success(st.session_state.prepopulate_success_message)
        del st.session_state.prepopulate_success_message

    st.subheader("Existing Holding Details")

    col1, col2 = st.columns(2)

    with col1:
        existing_accounts = data_manager.get_accounts()
        if existing_accounts:
            selected_account = st.selectbox(
                "Account",
                build_account_options(existing_accounts),
                key="prepopulate_account",
            )
            new_account = ""
            if selected_account == NEW_ACCOUNT_OPTION:
                new_account = st.text_input(
                    "New Account",
                    placeholder="e.g., TFSA, RRSP, Personal",
                    key="prepopulate_new_account",
                )
            account = resolve_account_input(selected_account, new_account)
        else:
            account = st.text_input(
                "Account",
                placeholder="e.g., TFSA, RRSP, Personal",
                key="prepopulate_account",
            )

        stock_symbol = st.text_input(
            "Stock Symbol",
            placeholder="e.g., AAPL",
            key="prepopulate_stock_symbol",
        ).upper()
        resolved_symbol = None
        resolved_name = None
        if stock_symbol:
            resolved_symbol, resolved_name = resolve_stock_symbol(stock_symbol)

        quantity = st.number_input(
            "Quantity",
            min_value=0,
            step=1,
            format="%d",
            key="prepopulate_quantity",
        )

    with col2:
        book_cost = st.number_input(
            "Book Cost ($)",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            key="prepopulate_book_cost",
        )
        acquisition_date = st.date_input(
            "Date of Acquisition",
            key="prepopulate_date",
        )

    if stock_symbol and resolved_name:
        final_symbol = resolved_symbol if resolved_symbol else stock_symbol
        cost_per_share = calculate_cost_per_share(quantity, book_cost)
        cost_per_share_display = (
            f" @ {format_currency(cost_per_share)}/share"
            if cost_per_share is not None else ""
        )

        st.markdown(build_holding_summary(
            final_symbol,
            resolved_name,
            cost_per_share_display,
        ))

    submitted = st.button("Add Holding", type="primary")

    if submitted:
        if not account.strip():
            st.error("Please enter an account name.")
        elif not stock_symbol.strip():
            st.error("Please enter a stock symbol.")
        elif not acquisition_date:
            st.error("Please select a valid acquisition date.")
        elif quantity < 1:
            st.error("Quantity must be at least 1.")
        elif book_cost <= 0:
            st.error("Book cost must be greater than 0.")
        else:
            final_symbol = resolved_symbol if resolved_symbol else stock_symbol.strip()
            final_name = resolved_name or stock_symbol

            holding_data = {
                'Account': account.strip(),
                'StockName': final_name.strip(),
                'StockSymbol': final_symbol.strip(),
                'Quantity': int(quantity),
                'BookCost': book_cost,
                'DateOfAcquisition': acquisition_date.strftime('%Y-%m-%d')
            }

            with st.spinner("Adding holding..."):
                success, message = calculator.add_existing_holding(holding_data)

            if success:
                st.session_state.prepopulate_success_message = (
                    f"✅ Holding added successfully! {message}"
                )
                st.session_state.prepopulate_reset_requested = True
                st.rerun()
            else:
                st.error(message)

# Page 4: Trade History
elif page == "Trade History":
    st.title("Trade History")
    st.markdown("View all recorded trades")

    # Display success message if one was stored from previous action
    if "history_success_message" in st.session_state:
        st.success(st.session_state.history_success_message)
        del st.session_state.history_success_message

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

            # Calculate Capital Gain/Loss for each trade
            def calculate_trade_gain_loss(row):
                """Calculate gain/loss for a single trade row."""
                stored_gain_loss = row.get('CapitalGainLoss')
                if pd.notna(stored_gain_loss):
                    return float(stored_gain_loss)
                if row['TradeType'] == 'S':  # Sell trade only
                    try:
                        shares = int(row['SharesTraded'])
                        price = float(row['PricePerShare'])
                        commission = float(row['Commission'])
                        net_proceeds = (shares * price) - commission

                        # Get current avg cost from consolidated (limitation: not historical)
                        record = data_manager.get_consolidated_record(row['Account'], row['StockSymbol'])
                        if record:
                            avg_cost = float(record['AveragePricePerShare'])
                            cost_basis = shares * avg_cost
                            gain_loss = net_proceeds - cost_basis
                            return gain_loss
                    except:
                        pass
                return None

            def calculate_cost(row):
                stored_cost = row.get('Cost')
                if pd.notna(stored_cost):
                    return float(stored_cost)
                try:
                    shares = int(row['SharesTraded'])
                    price = float(row['PricePerShare'])
                    commission = float(row['Commission'])
                    if row['TradeType'] == 'B':
                        return (shares * price) + commission
                    if row['TradeType'] == 'S':
                        average_at_sale = row.get('AverageCostAtSale')
                        if pd.notna(average_at_sale):
                            return shares * float(average_at_sale)
                except:
                    pass
                return None

            def calculate_gross_proceeds(row):
                stored_gross = row.get('GrossProceeds')
                if pd.notna(stored_gross):
                    return float(stored_gross)
                if row['TradeType'] in ['B', 'S']:
                    return int(row['SharesTraded']) * float(row['PricePerShare'])
                return None

            def calculate_net_proceeds(row):
                stored_net = row.get('NetProceeds')
                if pd.notna(stored_net):
                    return float(stored_net)
                if row['TradeType'] == 'B':
                    return calculate_gross_proceeds(row) + float(row['Commission'])
                if row['TradeType'] == 'S':
                    return calculate_gross_proceeds(row) - float(row['Commission'])
                return None

            display_df['Cost'] = display_df.apply(calculate_cost, axis=1)
            display_df['GrossProceeds'] = display_df.apply(calculate_gross_proceeds, axis=1)
            display_df['NetProceeds'] = display_df.apply(calculate_net_proceeds, axis=1)
            display_df['CapitalGainLoss'] = display_df.apply(calculate_trade_gain_loss, axis=1)

            # Format columns
            display_df['SharesTraded'] = display_df['SharesTraded'].apply(format_number)
            display_df['PricePerShare'] = display_df['PricePerShare'].apply(format_currency)
            display_df['Cost'] = display_df['Cost'].apply(lambda x: format_currency(x) if pd.notna(x) else '-')
            display_df['GrossProceeds'] = display_df['GrossProceeds'].apply(lambda x: format_currency(x) if pd.notna(x) else '-')
            display_df['NetProceeds'] = display_df['NetProceeds'].apply(lambda x: format_currency(x) if pd.notna(x) else '-')
            display_df['CapitalGainLoss'] = display_df['CapitalGainLoss'].apply(lambda x: format_currency(x) if pd.notna(x) else '-')
            display_df['Commission'] = display_df['Commission'].apply(format_currency)
            # Handle empty dates - show blank instead of 'No Date'
            display_df['DateOfTrade'] = pd.to_datetime(display_df['DateOfTrade'], errors='coerce').apply(
                lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else ''
            )

            # Rename columns for better display
            display_df = display_df.rename(columns={
                'Account': 'Account',
                'StockName': 'Stock Name',
                'StockSymbol': 'Symbol',
                'DateOfTrade': 'Trade Date',
                'TradeType': 'Type',
                'SharesTraded': 'Shares',
                'PricePerShare': 'Price/Share',
                'Cost': 'Cost',
                'GrossProceeds': 'Gross Proceeds',
                'NetProceeds': 'Net Proceeds',
                'CapitalGainLoss': 'Gain/Loss',
                'Commission': 'Commission'
            })

            # Format trade type
            display_df['Type'] = display_df['Type'].map({'B': 'Buy', 'S': 'Sell', 'T': 'Transfer'})
            display_df = display_df[[
                'Account', 'Stock Name', 'Symbol', 'Trade Date', 'Type', 'Shares',
                'Price/Share', 'Commission', 'Cost', 'Gross Proceeds',
                'Net Proceeds', 'Gain/Loss'
            ]]

            st.dataframe(display_df, width='stretch')

            # Delete trade section
            st.subheader("Delete Trade")
            st.info("ℹ️ Deleting a trade will automatically recalculate your consolidated holdings by replaying all remaining trades in order. This ensures 100% accurate calculations.")

            # Create a dropdown with trade descriptions
            trade_options = []
            for idx in filtered_df.index:
                row = df.loc[idx]
                # Handle empty dates gracefully
                date_val = pd.to_datetime(row['DateOfTrade'], errors='coerce')
                trade_date = date_val.strftime('%Y-%m-%d') if pd.notna(date_val) else '-'
                trade_type_full = {'B': 'Buy', 'S': 'Sell', 'T': 'Transfer'}.get(row['TradeType'], row['TradeType'])
                description = f"#{idx} | {trade_date} | {trade_type_full} | {row['StockSymbol']} | {int(row['SharesTraded'])} shares @ ${row['PricePerShare']:.2f}"
                trade_options.append((idx, description))

            if trade_options:
                selected_trade = st.selectbox(
                    "Select trade to delete",
                    options=[None] + trade_options,
                    format_func=lambda x: "Select a trade..." if x is None else x[1],
                    key="delete_trade_select"
                )

                if selected_trade is not None:
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        if st.button("Delete Trade", type="primary"):
                            trade_idx = selected_trade[0]
                            with st.spinner("Deleting trade and rebuilding holdings..."):
                                success, message = calculator.delete_trade_and_rebuild(trade_idx)
                            if success:
                                # Store success message to show after rerun
                                st.session_state.history_success_message = f"✅ {message}"
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")

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
    st.title("Stock Charts")
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

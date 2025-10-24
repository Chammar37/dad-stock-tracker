# Stock Tracker App

A personal stock tracking application built with Streamlit that helps you manage your stock portfolio across multiple accounts (TFSA, RRSP, Personal, etc.).

## Features

- **Consolidated Record**: View all holdings across all accounts with automatic calculations
- **Trade Entry**: Record buy/sell/transfer trades with automatic cost basis updates
- **Pre-populate Database**: Add existing holdings to get started quickly
- **Trade History**: View all past trades with filtering capabilities

## Installation

1. Clone or download this repository
2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```bash
   streamlit run app.py
   ```

2. Open your browser to the URL shown in the terminal (usually http://localhost:8501)

## Getting Started

1. **Pre-populate Database**: If you have existing holdings, use this page to add them
2. **Trade Entry**: Record new trades as they happen
3. **Consolidated Record**: View your current portfolio status
4. **Trade History**: Review all your past trades

## Data Storage

The app stores data in CSV files in the `data/` directory:
- `consolidated.csv`: Current holdings and their cost basis
- `trades.csv`: Complete trade history

## Calculations

The app automatically calculates:
- **Average cost per share** when buying stocks
- **Capital gains/losses** when selling stocks
- **Portfolio value** and performance metrics

## Account Types

The app supports multiple account types such as:
- TFSA (Tax-Free Savings Account)
- RRSP (Registered Retirement Savings Plan)
- Personal accounts
- Any other account type you specify

import yfinance as yf
import pandas as pd
import sys 
from tabulate import tabulate  # Add this import at the top of your file

# Suppress potential SettingWithCopyWarning from pandas if chained assignment occurs internally
pd.options.mode.chained_assignment = None # default='warn'

def calculate_stock_metrics_multiyear(ticker_symbol):
    """
    Calculates specific financial metrics for a given stock ticker using yfinance for multiple years.

    Args:
        ticker_symbol (str): The stock ticker symbol (e.g., 'AAPL', 'MSFT').

    Returns:
        dict: A dictionary containing the calculated metrics for each year.
    """
    print(f"\nFetching data for {ticker_symbol}...")
    try:
        stock = yf.Ticker(ticker_symbol)

        # Fetch necessary data components
        info = stock.info
        financials = stock.financials
        balance_sheet = stock.balance_sheet
        cashflow = stock.cashflow

        if financials.empty or balance_sheet.empty or cashflow.empty:
            if 'longName' not in info and 'shortName' not in info:
                print(f"Error: Could not retrieve basic info for {ticker_symbol}. It might be an invalid ticker.")
                return None
            else:
                print(f"Warning: Could not retrieve full financial statements for {ticker_symbol}. Some metrics may be unavailable.")

    except Exception as e:
        print(f"Error fetching data for {ticker_symbol}: {e}")
        return None

    metrics_by_year = {}

    # Iterate through each year (column) in the financials, balance_sheet, and cashflow
    for year in financials.columns:
        metrics = {
            'Enterprise Value (EV)': info.get('enterpriseValue'),
            'Free Cash Flow (FCF)': None,
            'EBITDA': None,
            'Total Debt': None,
            'Total Equity': None,
            'EBIT': None,
            'Tax Rate': None,
            'NOPAT': None,
            'Invested Capital': None,
            'EV/FCF Yield': None,
            'Total Debt / EBITDA': None,
            'EV / EBITDA': None,
            'ROIC': None,
        }

        # Calculate Free Cash Flow (FCF)
        try:
            fcf = cashflow.loc['Free Cash Flow', year] - cashflow.loc['Capital Expenditure', year]
            metrics['Free Cash Flow (FCF)'] = fcf
        except KeyError:
            metrics['Free Cash Flow (FCF)'] = None

        # Calculate EBITDA
        try:
            metrics['EBITDA'] = financials.loc['EBITDA', year]
        except KeyError:
            metrics['EBITDA'] = None

        # Calculate Total Debt
        try:
            metrics['Total Debt'] = balance_sheet.loc['Total Debt', year]
        except KeyError:
            metrics['Total Debt'] = None

        # Calculate Total Equity
        try:
            metrics['Total Equity'] = balance_sheet.loc['Total Equity Gross Minority Interest', year]
        except KeyError:
            metrics['Total Equity'] = None

        # Calculate EBIT
        try:
            metrics['EBIT'] = financials.loc['EBIT', year]
        except KeyError:
            metrics['EBIT'] = None

        # Calculate Tax Rate and NOPAT
        try:
            ebt = financials.loc['Pretax Income', year]
            tax_expense = financials.loc['Tax Provision', year]
            if ebt and tax_expense:
                tax_rate = tax_expense / ebt
                metrics['Tax Rate'] = max(0, min(1, tax_rate))  # Clamp between 0 and 1
                metrics['NOPAT'] = metrics['EBIT'] * (1 - metrics['Tax Rate'])
        except KeyError:
            metrics['Tax Rate'] = None
            metrics['NOPAT'] = None

        # --- Find Operating Leases ---
        if not balance_sheet.empty:
            op_leases = balance_sheet.loc['Long Term Capital Lease Obligation',year] + balance_sheet.loc['Current Capital Lease Obligation',year]
            metrics['Operating Lease Liabilities'] = op_leases
        else:
            print("Warning: Cannot check for Operating Leases due to missing balance sheet.")
            metrics['Operating Lease Liabilities'] = 0 # Default

        # Calculate Invested Capital
        try:
            metrics['Invested Capital'] = metrics['Total Debt'] + metrics['Total Equity'] + metrics['Operating Lease Liabilities']
        except TypeError:
            metrics['Invested Capital'] = None

        # Calculate Ratios
        ev = metrics['Enterprise Value (EV)']
        fcf = metrics['Free Cash Flow (FCF)']
        ebitda = metrics['EBITDA']
        invested_capital = metrics['Invested Capital']
        nopat = metrics['NOPAT']

        if fcf and ev:
            metrics['EV/FCF Yield'] = fcf / ev
        if metrics['Total Debt'] and ebitda:
            metrics['Total Debt / EBITDA'] = metrics['Total Debt'] / ebitda
        if ev and ebitda:
            metrics['EV / EBITDA'] = ev / ebitda
        if nopat and invested_capital:
            metrics['ROIC'] = nopat / invested_capital

        metrics_by_year[year] = metrics

    return metrics_by_year

def display_metrics_multiyear(metrics_by_year):
    """Displays the calculated metrics for each year in a proper table format."""
    if not metrics_by_year:
        print("No metrics to display.")
        return

    print("\n--- Calculated Metrics ---")

    # Collect all years and metrics
    years = list(metrics_by_year.keys())
    metrics_keys = list(metrics_by_year[years[0]].keys()) if years else []

    # Prepare the table data
    table = []
    for key in metrics_keys:
        row = [key]
        for year in years:
            value = metrics_by_year[year].get(key, "N/A")
            if isinstance(value, (int, float)):
                if "Rate" in key or "ROIC" in key or "Yield" in key:
                    # Format as percentage
                    row.append(f"{value:.2%}")
                elif "Total Debt / EBITDA" in key:
                    # Format as ratio
                    row.append(f"{value:.2f}")
                elif "EV / EBITDA" in key:
                    # Format as ratio
                    row.append(f"{value:.1f}")
                else:
                    # Format as currency with commas
                    row.append(f"{value:,.0f}")
            else:
                row.append(str(value))
        table.append(row)

    # Prepare the header row (years)
    header = [""] + [str(year.year) for year in years]  # Convert years to string

    # Print the table using tabulate
    print(tabulate(table, headers=header, tablefmt="grid"))


if __name__ == "__main__":
    while True:
        ticker = input("Enter the stock ticker symbol (or type 'quit' to exit): ").strip().upper()
        if ticker == 'QUIT':
            break
        if not ticker:
            continue

        calculated_data = calculate_stock_metrics_multiyear(ticker)

        if calculated_data:
            display_metrics_multiyear(calculated_data)
        else:
            print(f"Could not process ticker {ticker}.")
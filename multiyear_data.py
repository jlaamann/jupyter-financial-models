import yfinance as yf
import pandas as pd
import sys 

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
            'Ticker': ticker_symbol,
            'Year': year.year,  # Convert to year only
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

        # Calculate Invested Capital
        try:
            metrics['Invested Capital'] = metrics['Total Debt'] + metrics['Total Equity']
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


def display_metrics(metrics):
    """Nicely prints the calculated metrics."""
    if metrics is None:
        print("No metrics to display.")
        return

    print("\n--- Calculated Metrics ---")
    print(f"Ticker: {metrics.get('Ticker', 'N/A')}")

    print("\nKey Ratios:")
    print(f"  EV/FCF Yield (FCF/EV): {metrics.get('EV/FCF Yield', 'N/A'):.2%}" if isinstance(metrics.get('EV/FCF Yield'), (int, float)) else f"  EV/FCF Yield (FCF/EV): {metrics.get('EV/FCF Yield', 'N/A')}")
    print(f"  Total Debt / EBITDA:   {metrics.get('Total Debt / EBITDA', 'N/A'):.2f}" if isinstance(metrics.get('Total Debt / EBITDA'), (int, float)) else f"  Total Debt / EBITDA:   {metrics.get('Total Debt / EBITDA', 'N/A')}")
    print(f"  EV / EBITDA:           {metrics.get('EV / EBITDA', 'N/A'):.2f}" if isinstance(metrics.get('EV / EBITDA'), (int, float)) else f"  EV / EBITDA:           {metrics.get('EV / EBITDA', 'N/A')}")
    print(f"  ROIC (NOPAT/Inv Cap):  {metrics.get('ROIC', 'N/A'):.2%}" if isinstance(metrics.get('ROIC'), (int, float)) else f"  ROIC (NOPAT/Inv Cap):  {metrics.get('ROIC', 'N/A')}")
    print(f"  ROE:  {metrics.get('ROE', 'N/A'):.2%}" if isinstance(metrics.get('ROE'), (int, float)) else f"  ROE:  {metrics.get('ROE', 'N/A')}")
    print(f"  ROA:  {metrics.get('ROA', 'N/A'):.2%}" if isinstance(metrics.get('ROA'), (int, float)) else f"  ROA:  {metrics.get('ROA', 'N/A')}")
    print(f"  EBITDA margin:  {metrics.get('EBITDA_MARGIN', 'N/A'):.2%}" if isinstance(metrics.get('EBITDA_MARGIN'), (int, float)) else f"  EBITDA_MARGIN:  {metrics.get('EBITDA_MARGIN', 'N/A')}")

    if metrics.get('Operating Lease Liabilities', 0) == 0:
         print("     (Note: ROIC calculated excluding Operating Lease Liabilities as they were not found)")


    print("\nComponents Used (Latest Available Data):")
    print(f"  Enterprise Value (EV):       {metrics.get('Enterprise Value (EV)', 'N/A'):,.0f}" if isinstance(metrics.get('Enterprise Value (EV)'), (int, float)) else f"  Enterprise Value (EV):       {metrics.get('Enterprise Value (EV)', 'N/A')}")
    print(f"  Free Cash Flow (FCF):        {metrics.get('Free Cash Flow (FCF)', 'N/A'):,.0f}" if isinstance(metrics.get('Free Cash Flow (FCF)'), (int, float)) else f"  Free Cash Flow (FCF):        {metrics.get('Free Cash Flow (FCF)', 'N/A')}")
    print(f"  EBITDA:                      {metrics.get('EBITDA', 'N/A'):,.0f}" if isinstance(metrics.get('EBITDA'), (int, float)) else f"  EBITDA:                      {metrics.get('EBITDA', 'N/A')}")
    print(f"  Total Debt:                  {metrics.get('Total Debt', 'N/A'):,.0f}" if isinstance(metrics.get('Total Debt'), (int, float)) else f"  Total Debt:                  {metrics.get('Total Debt', 'N/A')}")
    print(f"  Total Equity:                {metrics.get('Total Equity', 'N/A'):,.0f}" if isinstance(metrics.get('Total Equity'), (int, float)) else f"  Total Equity:                {metrics.get('Total Equity', 'N/A')}")
    print(f"  EBIT:                        {metrics.get('EBIT', 'N/A'):,.0f}" if isinstance(metrics.get('EBIT'), (int, float)) else f"  EBIT:                        {metrics.get('EBIT', 'N/A')}")
    print(f"  Est. Tax Rate (for NOPAT):   {metrics.get('Tax Rate', 'N/A'):.2%}" if isinstance(metrics.get('Tax Rate'), (int, float)) else f"  Est. Tax Rate (for NOPAT):   {metrics.get('Tax Rate', 'N/A')}")
    print(f"  NOPAT:                       {metrics.get('NOPAT', 'N/A'):,.0f}" if isinstance(metrics.get('NOPAT'), (int, float)) else f"  NOPAT:                       {metrics.get('NOPAT', 'N/A')}")
    print(f"  Operating Lease Liabilities: {metrics.get('Operating Lease Liabilities', 'N/A'):,.0f}" if isinstance(metrics.get('Operating Lease Liabilities'), (int, float)) else f"  Operating Lease Liabilities: {metrics.get('Operating Lease Liabilities', 'N/A')}")
    print(f"  Invested Capital:            {metrics.get('Invested Capital', 'N/A'):,.0f}" if isinstance(metrics.get('Invested Capital'), (int, float)) else f"  Invested Capital:            {metrics.get('Invested Capital', 'N/A')}")
    print("--- End of Report ---")


def display_metrics_multiyear(metrics_by_year):
    """Displays the calculated metrics for each year in a table format."""
    if not metrics_by_year:
        print("No metrics to display.")
        return

    print("\n--- Calculated Metrics ---")

    # Collect all years and metrics
    years = list(metrics_by_year.keys())
    metrics_keys = list(metrics_by_year[years[0]].keys()) if years else []

    # Prepare the header row (years)
    header = ["Metric"] + [str(year.year) for year in years]  # Convert years to string
    print("\t".join(header))

    # Prepare each metric row
    for key in metrics_keys:
        row = [key]
        for year in years:
            value = metrics_by_year[year].get(key, "N/A")
            if isinstance(value, (int, float)):
                if "Rate" in key or "ROIC" in key or "Yield" in key:
                    # Format as percentage
                    row.append(f"{value:.2%}")
                else:
                    # Format as currency with commas
                    row.append(f"{value:,.0f}")
            else:
                row.append(str(value))
        print("\t".join(row))


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
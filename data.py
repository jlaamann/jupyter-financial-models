import yfinance as yf
import pandas as pd
import sys 

# Suppress potential SettingWithCopyWarning from pandas if chained assignment occurs internally
pd.options.mode.chained_assignment = None # default='warn'

def calculate_stock_metrics(ticker_symbol):
    """
    Calculates specific financial metrics for a given stock ticker using yfinance.

    Args:
        ticker_symbol (str): The stock ticker symbol (e.g., 'AAPL', 'MSFT').

    Returns:
        dict: A dictionary containing the calculated metrics."""
    print(f"\nFetching data for {ticker_symbol}...")
    try:
        stock = yf.Ticker(ticker_symbol)

        # Fetch necessary data components
        info = stock.info
        # Ensure financials, balance_sheet, cashflow are loaded (can sometimes be empty)
        financials = stock.financials
        balance_sheet = stock.balance_sheet
        cashflow = stock.cashflow
        quarterly_financials = stock.quarterly_financials

        # Check if essential dataframes are empty
        if financials.empty or balance_sheet.empty or cashflow.empty:
             # Check if the ticker is valid by trying to get basic info
            if 'longName' not in info and 'shortName' not in info:
                 print(f"Error: Could not retrieve basic info for {ticker_symbol}. It might be an invalid ticker.")
                 return None
            else:
                 print(f"Warning: Could not retrieve full financial statements for {ticker_symbol}. Some metrics may be unavailable.")
                 # Allow proceeding, some metrics might still be calculable from 'info'

    except Exception as e:
        print(f"Error fetching data for {ticker_symbol}: {e}")
        # A common issue is yfinance sometimes returns simplejson.errors.JSONDecodeError for invalid tickers
        # or during temporary API issues. Let's check if basic info exists.
        try:
            # Quick check if info was fetched at all
            _ = stock.info['symbol']
            print("Data fetching failed unexpectedly, though ticker seems potentially valid.")
        except Exception:
            print(f"Ticker {ticker_symbol} might be invalid or delisted.")
        return None

    metrics = {
        'Ticker': ticker_symbol,
        'Enterprise Value (EV)': None,
        'Free Cash Flow (FCF)': None,
        'EBITDA': None,
        'Total Debt': None,
        'Total Equity': None,
        'EBIT': None,
        'Tax Rate': None,
        'NOPAT': None,
        'Operating Lease Liabilities': 0, 
        'Invested Capital': None,
        'EV/FCF Yield': None,
        'Total Debt / EBITDA': None,
        'EV / EBITDA': None,
        'ROIC': None,
    }

    ttm_data = quarterly_financials.iloc[:, :4].sum(axis=1)

    # --- 1. Get Enterprise Value (EV) ---
    ev = info.get('enterpriseValue')
    metrics['Enterprise Value (EV)'] = ev

    # --- 2. Get Free Cash Flow (FCF) ---
    fcf = cashflow.iloc[:, 0].get('Free Cash Flow')
    metrics['Free Cash Flow (FCF)'] = fcf

    # --- 3. Get EBITDA ---
    # ebitda = financials.iloc[:, 0].get('EBITDA')
    metrics['EBITDA'] = ttm_data.get('EBITDA')

    # --- 4. Get Total Debt ---
    if not balance_sheet.empty:
        latest_bs = balance_sheet.iloc[:, 0]
        short_term_debt = latest_bs.get('Short Long Term Debt', 0) # Debt due within one year
        long_term_debt = latest_bs.get('Long Term Debt', 0)

        # Sometimes 'Total Debt' exists directly
        total_debt_direct = info.get('totalDebt')

        if total_debt_direct is not None:
             total_debt = total_debt_direct
        elif short_term_debt is not None and long_term_debt is not None:
             total_debt = short_term_debt + long_term_debt
        else:
             print("Warning: Could not determine Total Debt from balance sheet items.")
             total_debt = None
        metrics['Total Debt'] = total_debt
    else:
        print("Warning: Cannot get Total Debt due to missing balance sheet.")
        metrics['Total Debt'] = None


    # --- 5. Get Total Equity ---
    if not balance_sheet.empty:
        latest_bs = balance_sheet.iloc[:, 0]
        total_equity = latest_bs.get('Total Equity Gross Minority Interest')
        metrics['Total Equity'] = total_equity
    else:
        print("Warning: Cannot get Total Equity due to missing balance sheet.")
        metrics['Total Equity'] = None


    # --- 6. Calculate NOPAT (Net Operating Profit After Tax) ---
    # NOPAT = EBIT * (1 - Tax Rate)
    # Tax Rate = Tax Expense / Earnings Before Tax (EBT)
    if not financials.empty:
        ebit = ttm_data.get('EBIT')
        tax_expense = ttm_data.get('Tax Provision')
        ebt = ttm_data.get('Pretax Income') # Earnings Before Tax

        metrics['EBIT'] = ebit # Store EBIT for reference

        if ebit is not None and tax_expense is not None and ebt is not None and ebt != 0:
            tax_rate = tax_expense / ebt
            # Clamp tax rate between 0 and 1 (sensible bounds)
            tax_rate = max(0, min(1, tax_rate))
            nopat = ebit * (1 - tax_rate)
            metrics['Tax Rate'] = tax_rate
            metrics['NOPAT'] = nopat
        elif ebit is not None:
             print(f"Warning: Could not calculate tax rate (Tax Exp: {tax_expense}, EBT: {ebt}). NOPAT calculation might be inaccurate or unavailable.")
        else:
            print("Warning: Cannot calculate NOPAT because EBIT is missing.")
    else:
        print("Warning: Cannot calculate NOPAT due to missing financials statement.")


    # --- 7. Find Operating Leases ---
    if not balance_sheet.empty:
        latest_bs = balance_sheet.iloc[:, 0]
        # Look for standard names post-ASC 842/IFRS 16
        op_leases = latest_bs.get('Long Term Capital Lease Obligation') + latest_bs.get('Current Capital Lease Obligation') 
        metrics['Operating Lease Liabilities'] = op_leases
    else:
        print("Warning: Cannot check for Operating Leases due to missing balance sheet.")
        metrics['Operating Lease Liabilities'] = 0 # Default


    # --- 8. Calculate Invested Capital for ROIC ---
    # Invested Capital = Total Debt + Total Equity + Operating Leases
    total_debt = metrics['Total Debt']
    total_equity = metrics['Total Equity']
    op_leases = metrics['Operating Lease Liabilities']

    if total_debt is not None and total_equity is not None:
        invested_capital = total_debt + total_equity
        if op_leases > 0:
            invested_capital += op_leases
        metrics['Invested Capital'] = invested_capital
    else:
        print("Warning: Could not calculate Invested Capital due to missing Debt or Equity.")


    # --- 9. Calculate Final Ratios ---
    ev = metrics['Enterprise Value (EV)']
    fcf = metrics['Free Cash Flow (FCF)']
    ebitda = metrics['EBITDA']
    total_debt = metrics['Total Debt']
    nopat = metrics['NOPAT']
    invested_capital = metrics['Invested Capital']

    # EV/FCF Yield (FCF / EV)
    try:
        if fcf is not None and ev is not None and ev != 0:
            metrics['EV/FCF Yield'] = fcf / ev
        elif ev == 0:
            metrics['EV/FCF Yield'] = float('inf') if fcf is not None and fcf > 0 else 0
    except ZeroDivisionError:
         metrics['EV/FCF Yield'] = float('inf') # Or None or 'N/A'
    except TypeError: # Handles cases where components are None
         pass # Keep default None

    # Total Debt / EBITDA
    try:
        if total_debt is not None and ebitda is not None and ebitda != 0:
            metrics['Total Debt / EBITDA'] = total_debt / ebitda
        elif ebitda == 0:
             metrics['Total Debt / EBITDA'] = float('inf') if total_debt is not None and total_debt > 0 else 0
    except ZeroDivisionError:
        metrics['Total Debt / EBITDA'] = float('inf')
    except TypeError:
        pass

    # EV / EBITDA
    try:
        if ev is not None and ebitda is not None and ebitda != 0:
            metrics['EV / EBITDA'] = ev / ebitda
        elif ebitda == 0:
            metrics['EV / EBITDA'] = float('inf') if ev is not None and ev > 0 else 0
    except ZeroDivisionError:
        metrics['EV / EBITDA'] = float('inf')
    except TypeError:
        pass

    # ROIC (Return on Invested Capital)
    try:
        if nopat is not None and invested_capital is not None and invested_capital != 0:
            metrics['ROIC'] = nopat / invested_capital
        elif invested_capital == 0:
             metrics['ROIC'] = float('inf') if nopat is not None and nopat > 0 else 0
    except ZeroDivisionError:
        metrics['ROIC'] = float('inf')
    except TypeError:
        pass

    metrics['ROE'] = info.get('returnOnEquity')
    metrics['ROA'] = info.get('returnOnAssets')
    metrics['EBITDA_MARGIN'] = info.get('ebitdaMargins')

    return metrics

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


if __name__ == "__main__":
    while True:
        ticker = input("Enter the stock ticker symbol (or type 'quit' to exit): ").strip().upper()
        if ticker == 'QUIT':
            break
        if not ticker:
            continue

        calculated_data = calculate_stock_metrics(ticker)

        if calculated_data:
            display_metrics(calculated_data)
        else:
            # Error message already printed in the function
            print(f"Could not process ticker {ticker}.")
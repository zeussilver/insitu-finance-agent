import yfinance as yf
import pandas as pd
from typing import Optional

def get_financial_info() -> Optional[float]:
    """Fetch AMZN's latest quarterly net income.

    Returns:
        Latest quarterly net income as a float in USD
        None if data fetch fails or net income not found
    """
    try:
        ticker = yf.Ticker("AMZN")
        quarterly_financials = ticker.quarterly_financials
        
        if quarterly_financials.empty:
            return None
            
        # Look for net income in the financials
        possible_keys = ['Net Income', 'NetIncome']
        net_income_row = None
        
        for key in possible_keys:
            if key in quarterly_financials.index:
                net_income_row = quarterly_financials.loc[key]
                break
                
        if net_income_row is None:
            return None
            
        # Get the most recent quarter (first column)
        latest_net_income = net_income_row.iloc[0]
        
        # Handle cases where value might be NaN
        if pd.isna(latest_net_income):
            return None
            
        return float(latest_net_income)
        
    except Exception:
        return None

if __name__ == "__main__":
    # Test 1: Should return a numeric value
    result = get_financial_info()
    assert result is not None, "Should return a value for AMZN"
    
    # Test 2: Should be a positive number (AMZN typically profitable)
    assert result > 0, "Net income should be positive"
    print(f"Latest AMZN quarterly net income: ${result:,.2f}")
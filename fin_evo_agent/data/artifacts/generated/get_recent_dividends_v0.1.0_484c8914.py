import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict

def get_recent_dividends(dividend_data: List[Dict[str, str]], years: int = 3) -> List[Dict[str, str]]:
    """Filter dividend history for the specified number of recent years.

    Args:
        dividend_data: List of dividend records with 'date' (YYYY-MM-DD) and 'amount' keys
        years: Number of years to look back (default 3)

    Returns:
        Filtered list of dividend records from the last N years
    """
    # Use pandas to handle date calculations more accurately
    current_date = pd.Timestamp.now()
    cutoff_date = current_date - pd.DateOffset(years=years)
    
    recent_dividends = []
    
    for record in dividend_data:
        dividend_date = pd.Timestamp(record['date'])
        if dividend_date >= cutoff_date:
            recent_dividends.append(record)
    
    return recent_dividends

if __name__ == "__main__":
    # Sample dividend data (in practice, this would come from external source)
    sample_dividends = [
        {'date': '2021-05-07', 'amount': '0.22'},
        {'date': '2021-08-06', 'amount': '0.22'},
        {'date': '2021-11-05', 'amount': '0.22'},
        {'date': '2022-02-04', 'amount': '0.22'},
        {'date': '2022-05-06', 'amount': '0.23'},
        {'date': '2022-08-05', 'amount': '0.23'},
        {'date': '2022-11-04', 'amount': '0.23'},
        {'date': '2023-02-10', 'amount': '0.23'},
        {'date': '2023-05-12', 'amount': '0.24'},
        {'date': '2023-08-11', 'amount': '0.24'},
        {'date': '2023-11-10', 'amount': '0.24'},
        {'date': '2024-02-09', 'amount': '0.24'}
    ]
    
    result = get_recent_dividends(sample_dividends, 3)
    assert len(result) > 0
    assert all(datetime.strptime(r['date'], '%Y-%m-%d') >= datetime.now() - timedelta(days=365*3) 
               for r in result)
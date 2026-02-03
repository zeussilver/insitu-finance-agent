def get_financial_info(financial_data: dict, company: str = "AAPL", period: str = "2023Q1") -> float:
    """Get net income from provided financial data.

    Args:
        financial_data: Dictionary containing financial data with structure 
                        {company: {period: {"net_income": value}}}
        company: Company ticker symbol (default "AAPL")
        period: Financial period in format YYYYQQ (default "2023Q1")

    Returns:
        Net income value for the specified company and period
    """
    try:
        return float(financial_data[company][period]["net_income"])
    except (KeyError, TypeError):
        return 0.0

if __name__ == "__main__":
    # Test with sample data
    test_data = {
        "AAPL": {
            "2023Q1": {"net_income": 24160000000},
            "2023Q2": {"net_income": 24159000000}
        }
    }
    result = get_financial_info(test_data, "AAPL", "2023Q1")
    assert result == 24160000000.0
    
    # Test with missing data
    empty_data = {}
    result2 = get_financial_info(empty_data, "AAPL", "2023Q1")
    assert result2 == 0.0
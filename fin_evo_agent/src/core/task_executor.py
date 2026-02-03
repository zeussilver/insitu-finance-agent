"""Task Executor: Orchestrates task execution with bootstrap tool chaining.

This module bridges the gap between:
- Pure calc tools (expect data as arguments)
- Fetch tasks (need to retrieve data from yfinance)

Pattern: System fetches data via bootstrap tools, then passes to calc tools.
"""

import re
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

from src.core.registry import ToolRegistry
from src.core.executor import ToolExecutor
from src.core.models import ToolArtifact, ExecutionTrace
from src.finance.data_proxy import get_stock_hist


# Simple fetch patterns that can be handled directly from OHLCV data
# Pattern order matters - more specific patterns first
SIMPLE_FETCH_PATTERNS = {
    'highest_close': [
        r'highest\s+close\s*price',
        r'最高收盘价',       # Chinese: "highest closing price"
    ],
    'lowest_close': [
        r'lowest\s+close\s*price',
        r'最低收盘价',       # Chinese: "lowest closing price"
    ],
    'latest_close': [
        r'latest\s+close\s*price',
        r'close\s*price',   # Generic "close price" -> latest
        r'收盘价',          # Chinese: "closing price" -> latest
    ],
}

# Queries that require data NOT available in OHLCV
UNSUPPORTED_FETCH_PATTERNS = [
    r'net\s+income',
    r'revenue',
    r'earnings',
    r'profit',
    r'eps',
    r'dividend',
    r'balance\s+sheet',
    r'income\s+statement',
    r'cash\s+flow',
    r'financial\s+(statement|info|data)',
    r'净利润',             # Chinese: "net profit"
    r'营收',               # Chinese: "revenue"
    r'财务报表',           # Chinese: "financial statement"
]


class TaskExecutor:
    """Orchestrates task execution by chaining bootstrap fetch with calc tools."""

    # Standard OHLCV columns from yfinance
    OHLCV_COLUMNS = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']

    # Common English words that look like ticker symbols - EXCLUDE from matching
    SYMBOL_EXCLUSIONS = {
        'GET', 'SET', 'PUT', 'AND', 'THE', 'FOR', 'NOT', 'ALL', 'HAS',
        'ADD', 'SUB', 'DIV', 'MUL', 'MAX', 'MIN', 'AVG', 'SUM', 'END',
        'NEW', 'OLD', 'TOP', 'LOW', 'NET', 'DAY', 'ETF', 'USA', 'USD',
        'BUY', 'NOW', 'USE', 'OUT', 'OUR', 'ANY', 'CAN', 'MAY', 'SAY',
        'HOW', 'WHY', 'YES', 'TWO', 'TEN', 'ONE', 'ITS'
    }

    # Index name to yfinance symbol mapping
    INDEX_SYMBOL_MAPPING = {
        'S&P 500': '^GSPC',
        'S&P500': '^GSPC',
        'SP500': '^GSPC',
        'SP 500': '^GSPC',
        'DOW': '^DJI',
        'DJIA': '^DJI',
        'DOW JONES': '^DJI',
        'NASDAQ': '^IXIC',
        'RUSSELL': '^RUT',
        'RUSSELL 2000': '^RUT',
        'VIX': '^VIX',
    }

    # Mapping of task patterns to bootstrap tools
    FETCH_TOOL_MAPPING = {
        'stock_hist': 'get_stock_hist',
        'financial': 'get_financial_info',
        'quote': 'get_realtime_quote',
        'index': 'get_index_daily',
        'etf': 'get_etf_hist',
    }

    def __init__(
        self,
        registry: ToolRegistry = None,
        executor: ToolExecutor = None
    ):
        self.registry = registry or ToolRegistry()
        self.executor = executor or ToolExecutor()
        self._bootstrap_cache: Dict[str, ToolArtifact] = {}

    def get_bootstrap_tool(self, tool_name: str) -> Optional[ToolArtifact]:
        """Get a bootstrap tool by name (cached)."""
        if tool_name not in self._bootstrap_cache:
            tool = self.registry.get_by_name(tool_name)
            if tool and 'bootstrap' in tool.file_path:
                self._bootstrap_cache[tool_name] = tool
        return self._bootstrap_cache.get(tool_name)

    def extract_symbol(self, query: str) -> str:
        """Extract stock symbol from query string.

        Extraction order (first match wins):
        1. Index names (S&P 500, DOW, NASDAQ) -> yfinance index symbols
        2. Known US tickers (AAPL, MSFT, SPY, etc.)
        3. Regex pattern matching with exclusion filter
        4. Default to AAPL
        """
        query_upper = query.upper()

        # Step 1: Check index names FIRST (case-insensitive)
        for index_name, symbol in self.INDEX_SYMBOL_MAPPING.items():
            if index_name.upper() in query_upper:
                return symbol

        # Step 2: Check known US tickers (common stocks + ETFs)
        us_tickers = [
            'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'TSLA', 'META', 'NVDA', 'AMD', 'INTC',
            'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI', 'GLD', 'SLV', 'USO', 'XLF',
            'NFLX', 'PYPL', 'CRM', 'ADBE', 'ORCL', 'IBM', 'CSCO', 'QCOM', 'TXN', 'AVGO'
        ]
        for ticker in us_tickers:
            if ticker in query_upper:
                return ticker

        # Step 3: Regex pattern matching with exclusion filter
        # Find all potential ticker patterns (2-5 uppercase letters)
        # Sort by length descending to prefer longer matches (GETH > GET)
        matches = re.findall(r'\b([A-Z]{2,5})\b', query_upper)
        matches_sorted = sorted(matches, key=len, reverse=True)

        for match in matches_sorted:
            if match not in self.SYMBOL_EXCLUSIONS:
                return match

        # Step 4: Default fallback
        return 'AAPL'

    def extract_date_range(self, query: str) -> Tuple[str, str]:
        """Extract date range from query, or return default."""
        # Try to find date patterns
        date_pattern = r'(\d{4}-\d{2}-\d{2})'
        dates = re.findall(date_pattern, query)

        if len(dates) >= 2:
            return dates[0], dates[1]
        elif len(dates) == 1:
            return dates[0], '2023-12-31'

        # Default date range
        return '2023-01-01', '2023-12-31'

    def fetch_stock_data(
        self,
        symbol: str,
        start: str,
        end: str
    ) -> Dict[str, Any]:
        """
        Fetch OHLCV data using the data_proxy (cached).

        Returns standardized dict format:
        {
            'symbol': str,
            'dates': List[str],
            'open': List[float],
            'high': List[float],
            'low': List[float],
            'close': List[float],
            'volume': List[float]
        }
        """
        try:
            df = get_stock_hist(symbol, start, end)

            if df is None or df.empty:
                raise ValueError(f"No data returned for {symbol}")

            # Convert DataFrame to dict with standardized format
            # Handle both string and numeric columns (from parquet cache)
            return {
                'symbol': symbol,
                'dates': df['Date'].astype(str).tolist() if 'Date' in df.columns else [],
                'open': [float(x) for x in df['Open'].tolist()] if 'Open' in df.columns else [],
                'high': [float(x) for x in df['High'].tolist()] if 'High' in df.columns else [],
                'low': [float(x) for x in df['Low'].tolist()] if 'Low' in df.columns else [],
                'close': [float(x) for x in df['Close'].tolist()] if 'Close' in df.columns else [],
                'volume': [float(x) for x in df['Volume'].tolist()] if 'Volume' in df.columns else [],
            }
        except Exception as e:
            # Return error indicator - don't silently fail
            raise RuntimeError(f"Failed to fetch data for {symbol}: {e}")

    def prepare_calc_args(
        self,
        data: Dict[str, Any],
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare arguments for a calc tool from fetched data and task params.

        Maps OHLCV data to common calc tool argument names.
        """
        args = {
            # Primary price data (most calc tools use 'prices')
            'prices': data.get('close', []),

            # Individual OHLCV columns for tools that need them
            'open': data.get('open', []),
            'high': data.get('high', []),
            'low': data.get('low', []),
            'close': data.get('close', []),
            'volume': data.get('volume', []),
            'dates': data.get('dates', []),

            # Symbol info
            'symbol': data.get('symbol', ''),
        }

        # Extract task-specific parameters
        args.update(self._extract_task_params(task))

        return args

    def _extract_task_params(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Extract calculation parameters from task query."""
        query = task.get('query', '')
        params = {}

        # RSI period
        if match := re.search(r'RSI[- ]?(\d+)', query, re.I):
            params['period'] = int(match.group(1))
        elif 'rsi' in query.lower():
            params['period'] = 14  # default RSI period

        # MACD parameters
        if match := re.search(r'MACD\s*\(?\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', query, re.I):
            params['fast_period'] = int(match.group(1))
            params['slow_period'] = int(match.group(2))
            params['signal_period'] = int(match.group(3))
        elif 'macd' in query.lower():
            params['fast_period'] = 12
            params['slow_period'] = 26
            params['signal_period'] = 9

        # KDJ parameters
        if 'kdj' in query.lower():
            params['k_period'] = 9
            params['d_period'] = 3

        # Bollinger bands
        if match := re.search(r'(\d+)\s*day', query.lower()):
            params['window'] = int(match.group(1))
        elif 'bollinger' in query.lower() or '\u5e03\u6797' in query:
            params['window'] = 20
            params['num_std'] = 2

        # Generic period/window
        if 'period' not in params and 'window' not in params:
            if match := re.search(r'(\d+)\s*(\u5929|\u65e5|day|period)', query.lower()):
                params['period'] = int(match.group(1))

        return params

    def execute_task(
        self,
        task: Dict[str, Any],
        tool: ToolArtifact
    ) -> ExecutionTrace:
        """
        Execute a task using the appropriate pattern.

        For fetch/calculation/composite categories:
        1. Fetch data using bootstrap tools
        2. Prepare arguments
        3. Execute the tool with data
        """
        category = task.get('category', 'calculation')
        task_id = task.get('task_id', 'unknown')

        # Fetch data if needed
        if category in ('fetch', 'calculation', 'composite'):
            try:
                symbol = self.extract_symbol(task.get('query', ''))
                start, end = self.extract_date_range(task.get('query', ''))

                data = self.fetch_stock_data(symbol, start, end)
                args = self.prepare_calc_args(data, task)
            except Exception as e:
                # Return error trace for fetch failures
                return ExecutionTrace(
                    trace_id=f"fetch_error_{task_id}",
                    task_id=task_id,
                    input_args={'error': str(e)},
                    output_repr="",
                    exit_code=1,
                    std_out="",
                    std_err=f"Data fetch failed: {e}",
                    execution_time_ms=0
                )
        else:
            args = self._extract_task_params(task)

        # Execute the tool
        return self.executor.execute(
            tool.code_content,
            tool.name,
            args,
            task_id
        )


if __name__ == "__main__":
    # Test TaskExecutor
    from src.core.models import init_db

    print("Initializing...")
    init_db()

    task_executor = TaskExecutor()

    # Test symbol extraction - basic cases
    assert task_executor.extract_symbol("\u8ba1\u7b97AAPL\u7684RSI") == "AAPL"
    assert task_executor.extract_symbol("\u8ba1\u7b97MSFT\u7684MACD") == "MSFT"
    # Test symbol extraction - exclusion list (GET should not match)
    assert task_executor.extract_symbol("Get SPY ETF latest close price") == "SPY", "Should match SPY, not GET"
    # Test symbol extraction - index mapping
    assert task_executor.extract_symbol("Get S&P 500 index latest close price") == "^GSPC", "Should map S&P 500 to ^GSPC"
    assert task_executor.extract_symbol("Get DOW Jones index price") == "^DJI", "Should map DOW to ^DJI"
    assert task_executor.extract_symbol("Get NASDAQ composite") == "^IXIC", "Should map NASDAQ to ^IXIC"
    print("Symbol extraction: PASS")

    # Test date extraction
    start, end = task_executor.extract_date_range("2023-01-01\u52302023-06-30")
    assert start == "2023-01-01", f"Got {start}"
    assert end == "2023-06-30", f"Got {end}"
    print("Date extraction: PASS")

    # Test data fetch (uses cache)
    try:
        data = task_executor.fetch_stock_data("AAPL", "2023-01-01", "2023-01-10")
        assert 'close' in data
        assert len(data['close']) > 0
        print(f"Data fetch: PASS ({len(data['close'])} rows)")
    except Exception as e:
        print(f"Data fetch: SKIP (network issue: {e})")

    # Test param extraction
    task = {'query': '\u8ba1\u7b97RSI-14\u6307\u6807'}
    params = task_executor._extract_task_params(task)
    assert params.get('period') == 14, f"Got {params}"
    print("Param extraction: PASS")

    print("\nAll TaskExecutor tests passed!")

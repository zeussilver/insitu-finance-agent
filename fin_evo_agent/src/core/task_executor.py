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

# Queries that require financial data (now supported via yfinance)
# These are no longer blocked - fetch tools can now handle them
FINANCIAL_FETCH_PATTERNS = [
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

    # Known US tickers (common stocks + ETFs) - class level for reuse
    US_TICKERS = [
        'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'TSLA', 'META', 'NVDA', 'AMD', 'INTC',
        'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI', 'GLD', 'SLV', 'USO', 'XLF',
        'NFLX', 'PYPL', 'CRM', 'ADBE', 'ORCL', 'IBM', 'CSCO', 'QCOM', 'TXN', 'AVGO'
    ]

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
        for ticker in self.US_TICKERS:
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

    # Additional exclusions for multi-symbol extraction context
    MULTI_SYMBOL_EXCLUSIONS = {
        'EQUAL', 'WEIGHT', 'RETURN', 'OVER', 'LAST', 'DAYS', 'PRICE',
        'CALCULATE', 'BETWEEN', 'PORTFOLIO', 'CORRELATION',
    }

    def extract_multiple_symbols(self, query: str) -> List[str]:
        """Extract multiple stock symbols from query.

        Used for multi-asset tasks like correlation and portfolio calculations.

        Returns:
            List of symbols found in the query. Falls back to single symbol extraction
            if only one symbol is found.
        """
        symbols = []
        query_upper = query.upper()

        # Combine exclusion lists
        all_exclusions = self.SYMBOL_EXCLUSIONS | self.MULTI_SYMBOL_EXCLUSIONS

        # Step 1: Check index names FIRST (case-insensitive)
        for index_name, symbol in self.INDEX_SYMBOL_MAPPING.items():
            if index_name.upper() in query_upper and symbol not in symbols:
                symbols.append(symbol)

        # Step 2: Check known US tickers (common stocks + ETFs)
        # Skip tickers that are substrings of already-found tickers (e.g., GOOG if GOOGL found)
        for ticker in self.US_TICKERS:
            if ticker in query_upper and ticker not in symbols:
                # Check if this ticker is a substring of an already-found ticker
                is_substring = any(
                    ticker != existing and ticker in existing
                    for existing in symbols
                )
                if not is_substring:
                    symbols.append(ticker)

        # Step 3: Regex pattern matching with exclusion filter
        # Find all potential ticker patterns (2-5 uppercase letters)
        # Skip this step for multi-symbol - known tickers should suffice
        # (avoids false positives like 'EQUAL', 'GOOG' when GOOGL is present)

        # Return found symbols, or fall back to single extraction
        if len(symbols) >= 2:
            return symbols
        else:
            return [self.extract_symbol(query)]

    def is_multi_asset_task(self, query: str) -> bool:
        """Detect if a task requires multiple assets.

        Multi-asset tasks include:
        - Correlation calculations (between two assets)
        - Portfolio calculations (multiple assets)
        """
        query_lower = query.lower()
        return 'correlation' in query_lower or 'portfolio' in query_lower

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

    def _fetch_multi_asset_data(
        self,
        symbols: List[str],
        start: str,
        end: str,
        query: str
    ) -> Dict[str, Any]:
        """
        Fetch data for multiple symbols.

        Returns a dict with:
        - For correlation: prices1, prices2 (close prices for first two symbols)
        - For portfolio: symbol names as keys (close prices) + 'symbols' list

        Args:
            symbols: List of stock symbols to fetch
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            query: Original query string (to determine data format)
        """
        query_lower = query.lower()
        all_data = {}

        # Fetch data for each symbol
        for i, sym in enumerate(symbols):
            try:
                sym_data = self.fetch_stock_data(sym, start, end)
                close_prices = sym_data.get('close', [])

                # For correlation: use prices1, prices2
                if 'correlation' in query_lower:
                    all_data[f'prices{i + 1}'] = close_prices

                # For portfolio: use symbol name as key
                if 'portfolio' in query_lower:
                    # Clean symbol name (remove ^ for indices)
                    clean_name = sym.replace('^', '')
                    all_data[clean_name] = close_prices

            except Exception as e:
                print(f"[TaskExecutor] Warning: Failed to fetch {sym}: {e}")
                # Continue with other symbols

        # Add symbols list for portfolio tasks
        if 'portfolio' in query_lower:
            all_data['symbols'] = [s.replace('^', '') for s in symbols]

        return all_data

    def prepare_calc_args(
        self,
        data: Dict[str, Any],
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare arguments for a calc tool from fetched data and task params.

        Maps OHLCV data to common calc tool argument names.
        Handles multi-asset data for correlation and portfolio tasks.
        """
        query = task.get('query', '').lower()

        # Check if it's a multi-asset task
        if 'correlation' in query:
            # Correlation needs prices1 and prices2
            args = {
                'prices1': data.get('prices1', []),
                'prices2': data.get('prices2', []),
            }
            # Extract task-specific parameters
            args.update(self._extract_task_params(task))
            return args

        elif 'portfolio' in query:
            # Portfolio task - map symbol keys to numbered params
            args = {}
            price_index = 1
            for key, value in data.items():
                if isinstance(value, list) and key not in ('symbols', 'dates'):
                    args[f'prices{price_index}'] = value  # Convert to prices1, prices2, prices3
                    price_index += 1
            # Extract task-specific parameters
            args.update(self._extract_task_params(task))
            return args

        elif 'divergence' in query:
            # Divergence task - map volume to volumes (plural)
            args = {
                'prices': data.get('close', []),
                'volumes': data.get('volume', []),  # Map singular to plural
            }
            args.update(self._extract_task_params(task))
            return args

        # Standard single-asset case
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

        # Extract year from query (e.g., "2023", "2024")
        year_match = re.search(r'\b(20\d{2})\b', query)
        if year_match:
            params['year'] = int(year_match.group(1))

        # Extract quarter from query (e.g., "Q1", "Q2", "1st quarter")
        quarter_match = re.search(r'Q(\d)|(\d)(?:st|nd|rd|th)?\s*quarter', query, re.IGNORECASE)
        if quarter_match:
            params['quarter'] = int(quarter_match.group(1) or quarter_match.group(2))

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

        # Bollinger bands - only extract window if query mentions bollinger
        if 'bollinger' in query.lower() or '布林' in query:
            if match := re.search(r'(\d+)[-\s]*day', query.lower()):
                params['window'] = int(match.group(1))
            else:
                params['window'] = 20
            params['num_std'] = 2

        # Generic period/window (for divergence, volatility, and other tasks)
        if 'period' not in params and 'window' not in params:
            if match := re.search(r'(\d+)[-\s]*(天|日|day|period)', query.lower()):
                params['period'] = int(match.group(1))

        return params

    def _handle_simple_fetch(
        self,
        query: str,
        data: Dict[str, Any]
    ) -> Optional[float]:
        """
        Handle simple fetch queries directly from OHLCV data.

        Returns:
            - float: The requested value if query matches a simple pattern
            - None: If query doesn't match (should fall through to tool execution)

        Note: Financial data queries (net income, revenue, etc.) are now supported
        via yfinance fetch tools and will fall through to tool execution.
        """
        query_lower = query.lower()

        # Financial queries now fall through to tool execution
        # (Previously raised ValueError, but fetch tools can now handle them)
        for pattern in FINANCIAL_FETCH_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return None  # Fall through to tool execution

        # Get close prices from data
        close_prices = data.get('close', [])
        if not close_prices:
            return None

        # Check simple fetch patterns (order: highest, lowest, latest)
        for pattern_type, patterns in SIMPLE_FETCH_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    if pattern_type == 'highest_close':
                        return max(close_prices)
                    elif pattern_type == 'lowest_close':
                        return min(close_prices)
                    elif pattern_type == 'latest_close':
                        return close_prices[-1]

        # No match - fall through to tool execution
        return None

    def execute_task(
        self,
        task: Dict[str, Any],
        tool: ToolArtifact
    ) -> ExecutionTrace:
        """
        Execute a task using the appropriate pattern.

        For fetch/calculation/composite categories:
        1. Fetch data using bootstrap tools (single or multiple symbols)
        2. Try simple fetch handling (latest/highest/lowest close)
        3. If not simple, execute the tool with data
        """
        category = task.get('category', 'calculation')
        task_id = task.get('task_id', 'unknown')
        query = task.get('query', '')

        # Fetch data if needed
        if category in ('fetch', 'calculation', 'composite'):
            try:
                start, end = self.extract_date_range(query)

                # Check if it's a multi-asset task
                if self.is_multi_asset_task(query):
                    symbols = self.extract_multiple_symbols(query)
                    data = self._fetch_multi_asset_data(symbols, start, end, query)
                    symbol = ','.join(symbols)  # For trace logging
                else:
                    symbol = self.extract_symbol(query)
                    symbols = [symbol]
                    data = self.fetch_stock_data(symbol, start, end)

                # Try simple fetch handling first (no tool execution needed)
                # Note: Simple fetch only works for single-asset queries
                if not self.is_multi_asset_task(query):
                    try:
                        simple_result = self._handle_simple_fetch(query, data)
                        if simple_result is not None:
                            # Return success trace with direct result
                            return ExecutionTrace(
                                trace_id=f"simple_fetch_{task_id}",
                                task_id=task_id,
                                input_args={'query': query, 'symbol': symbol},
                                output_repr=str(simple_result),
                                exit_code=0,
                                std_out=str(simple_result),
                                std_err="",
                                execution_time_ms=0
                            )
                    except Exception as e:
                        # Error in simple fetch handling - fall through to tool execution
                        print(f"[TaskExecutor] Simple fetch error: {e}")

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

    # Test simple fetch handling
    mock_data = {'close': [100.0, 101.0, 102.0, 99.0, 105.0], 'symbol': 'AAPL'}

    # Test English variants
    assert task_executor._handle_simple_fetch("Get latest close price", mock_data) == 105.0
    assert task_executor._handle_simple_fetch("Get AAPL close price", mock_data) == 105.0
    assert task_executor._handle_simple_fetch("Get highest close price in last 30 days", mock_data) == 105.0
    assert task_executor._handle_simple_fetch("Get lowest close price", mock_data) == 99.0

    # Test Chinese variants
    assert task_executor._handle_simple_fetch("获取收盘价", mock_data) == 105.0
    assert task_executor._handle_simple_fetch("获取最高收盘价", mock_data) == 105.0
    assert task_executor._handle_simple_fetch("获取最低收盘价", mock_data) == 99.0

    # Test non-simple queries return None (fall through to tool execution)
    assert task_executor._handle_simple_fetch("Calculate RSI", mock_data) is None
    assert task_executor._handle_simple_fetch("计算MACD", mock_data) is None
    print("Simple fetch handling: PASS")

    # Test financial queries now fall through (return None) instead of raising
    result = task_executor._handle_simple_fetch("Get AAPL 2023 Q1 net income", mock_data)
    assert result is None, "Financial queries should fall through to tool execution"
    print("Financial query handling: PASS")

    # Test multi-asset task detection
    assert task_executor.is_multi_asset_task("Calculate correlation between S&P 500 and AAPL") == True
    assert task_executor.is_multi_asset_task("Calculate portfolio return (AAPL,GOOGL,AMZN)") == True
    assert task_executor.is_multi_asset_task("Calculate AAPL RSI-14") == False
    print("Multi-asset task detection: PASS")

    # Test multi-symbol extraction
    symbols = task_executor.extract_multiple_symbols("Calculate correlation between S&P 500 and AAPL")
    assert '^GSPC' in symbols, f"Should find S&P 500 as ^GSPC, got {symbols}"
    assert 'AAPL' in symbols, f"Should find AAPL, got {symbols}"
    assert len(symbols) >= 2, f"Should find at least 2 symbols, got {symbols}"
    print(f"Multi-symbol extraction (correlation): PASS - {symbols}")

    symbols = task_executor.extract_multiple_symbols("Calculate equal-weight portfolio return (AAPL,GOOGL,AMZN)")
    assert 'AAPL' in symbols, f"Should find AAPL, got {symbols}"
    assert 'GOOGL' in symbols, f"Should find GOOGL, got {symbols}"
    assert 'AMZN' in symbols, f"Should find AMZN, got {symbols}"
    assert len(symbols) == 3, f"Should find exactly 3 symbols, got {symbols}"
    assert 'GOOG' not in symbols, f"Should NOT find GOOG (GOOGL is present), got {symbols}"
    assert 'EQUAL' not in symbols, f"Should NOT find EQUAL (common word), got {symbols}"
    print(f"Multi-symbol extraction (portfolio): PASS - {symbols}")

    # Test prepare_calc_args for correlation
    correlation_data = {
        'prices1': [100.0, 101.0, 102.0],
        'prices2': [50.0, 51.0, 52.0],
    }
    correlation_task = {'query': 'Calculate correlation between S&P 500 and AAPL'}
    args = task_executor.prepare_calc_args(correlation_data, correlation_task)
    assert 'prices1' in args, f"Should have prices1, got {args.keys()}"
    assert 'prices2' in args, f"Should have prices2, got {args.keys()}"
    print("Prepare args (correlation): PASS")

    # Test prepare_calc_args for portfolio
    portfolio_data = {
        'AAPL': [100.0, 101.0, 102.0],
        'GOOGL': [200.0, 202.0, 204.0],
        'AMZN': [150.0, 151.0, 152.0],
        'symbols': ['AAPL', 'GOOGL', 'AMZN'],
    }
    portfolio_task = {'query': 'Calculate equal-weight portfolio return (AAPL,GOOGL,AMZN)'}
    args = task_executor.prepare_calc_args(portfolio_data, portfolio_task)
    # Now maps symbol keys to numbered params (prices1, prices2, prices3)
    assert 'prices1' in args, f"Should have prices1, got {args.keys()}"
    assert 'prices2' in args, f"Should have prices2, got {args.keys()}"
    assert 'prices3' in args, f"Should have prices3, got {args.keys()}"
    assert 'symbols' not in args, f"Should NOT have symbols (excluded), got {args.keys()}"
    print("Prepare args (portfolio): PASS")

    print("\nAll TaskExecutor tests passed!")

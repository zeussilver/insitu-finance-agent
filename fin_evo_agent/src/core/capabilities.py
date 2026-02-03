"""Capability-based permission system for tool validation.

Each tool category has specific capabilities that determine:
- Which modules it can import
- What operations it can perform
- How it should be verified
"""

from enum import Enum
from typing import Set, Dict, List


class ToolCapability(str, Enum):
    """Tool execution capabilities."""
    CALCULATE = "calculate"       # Pure computation (pandas/numpy)
    FETCH = "fetch"               # Read from yfinance (cached)
    CACHE_WRITE = "cache_write"   # Write to data/cache/
    NETWORK_READ = "network_read" # Network requests (yfinance)
    FILE_READ = "file_read"       # Read from data/ directory


class ToolCategory(str, Enum):
    """Tool categories based on capabilities."""
    FETCH = "fetch"           # Can call yfinance, must implement caching
    CALCULATE = "calculation" # Pure functions, data as arguments
    COMPOSITE = "composite"   # Can combine multiple tools


# Modules allowed for each capability
CAPABILITY_MODULES: Dict[ToolCapability, Set[str]] = {
    ToolCapability.CALCULATE: {
        'pandas', 'numpy', 'datetime', 'json', 'math',
        'decimal', 'collections', 're', 'typing'
    },
    ToolCapability.FETCH: {
        'pandas', 'numpy', 'datetime', 'json',
        'yfinance', 'hashlib', 'typing', 'warnings'
    },
    ToolCapability.CACHE_WRITE: {
        'pathlib'
    },
    ToolCapability.NETWORK_READ: {
        'yfinance'
    },
    ToolCapability.FILE_READ: {
        'pathlib', 'json'
    },
}


# Capabilities granted to each tool category
CATEGORY_CAPABILITIES: Dict[ToolCategory, Set[ToolCapability]] = {
    ToolCategory.FETCH: {
        ToolCapability.FETCH,
        ToolCapability.NETWORK_READ,
        ToolCapability.CACHE_WRITE,
        ToolCapability.CALCULATE,  # Can also do basic calculations
    },
    ToolCategory.CALCULATE: {
        ToolCapability.CALCULATE,
    },
    ToolCategory.COMPOSITE: {
        ToolCapability.CALCULATE,
        # Optionally can have FETCH capability if needed
    },
}


def get_allowed_modules(capabilities: Set[ToolCapability]) -> Set[str]:
    """Get all allowed modules for a set of capabilities."""
    modules = set()
    for cap in capabilities:
        modules.update(CAPABILITY_MODULES.get(cap, set()))
    return modules


def get_category_modules(category) -> Set[str]:
    """Get all allowed modules for a tool category.

    Args:
        category: Can be ToolCategory enum or string ('fetch', 'calculation', 'composite')
    """
    if isinstance(category, str):
        try:
            category = ToolCategory(category)
        except ValueError:
            # Default to calculation for unknown categories
            category = ToolCategory.CALCULATE
    capabilities = CATEGORY_CAPABILITIES.get(category, set())
    return get_allowed_modules(capabilities)


def get_category_capabilities(category: str) -> Set[ToolCapability]:
    """Get capabilities for a category (string version for flexibility)."""
    try:
        cat = ToolCategory(category)
        return CATEGORY_CAPABILITIES.get(cat, set())
    except ValueError:
        # Default to CALCULATE if unknown category
        return CATEGORY_CAPABILITIES[ToolCategory.CALCULATE]


# Modules that are ALWAYS banned regardless of capability
ALWAYS_BANNED_MODULES: Set[str] = {
    'os', 'sys', 'subprocess', 'shutil', 'builtins',
    'importlib', 'ctypes', 'socket', 'http', 'urllib',
    'pickle', 'shelve', 'multiprocessing', 'threading',
    'pty', 'tty', 'fcntl', 'posix', 'nt', 'msvcrt',
    'code', 'codeop', 'commands', 'popen2', 'signal'
}


# Calls that are ALWAYS banned regardless of capability
ALWAYS_BANNED_CALLS: Set[str] = {
    'eval', 'exec', 'compile', '__import__',
    'globals', 'locals', 'vars', 'dir',
    'getattr', 'setattr', 'delattr',
    'hasattr', 'open', 'file', 'input', 'raw_input',
    'execfile', 'reload', 'breakpoint'
}


# Attributes that are ALWAYS banned
ALWAYS_BANNED_ATTRIBUTES: Set[str] = {
    '__class__', '__bases__', '__subclasses__', '__mro__',
    '__dict__', '__globals__', '__code__', '__builtins__',
    '__getattribute__', '__setattr__', '__delattr__',
    '__reduce__', '__reduce_ex__', '__getstate__', '__setstate__',
    '__init_subclass__', '__class_getitem__',
    'func_globals', 'func_code',
}


# Additional banned modules for CALCULATE-only tools
CALC_BANNED_MODULES: Set[str] = {
    'yfinance', 'akshare', 'talib', 'requests',
    'urllib3', 'httpx', 'aiohttp'
}


def get_banned_modules_for_category(category: str) -> Set[str]:
    """Get banned modules for a specific category."""
    banned = ALWAYS_BANNED_MODULES.copy()

    if category == 'calculation':
        # CALCULATE tools cannot use network/fetch modules
        banned.update(CALC_BANNED_MODULES)

    return banned


if __name__ == "__main__":
    # Test module mappings
    print("=== Capability Module Mappings ===")
    for cap in ToolCapability:
        modules = CAPABILITY_MODULES.get(cap, set())
        print(f"{cap.value}: {sorted(modules)}")

    print("\n=== Category Allowed Modules ===")
    for cat in ToolCategory:
        modules = get_category_modules(cat)
        print(f"{cat.value}: {sorted(modules)}")

    print("\n=== Category Banned Modules ===")
    for cat in ['fetch', 'calculation', 'composite']:
        banned = get_banned_modules_for_category(cat)
        print(f"{cat}: {len(banned)} banned modules")

    print("\nCapability system tests passed!")

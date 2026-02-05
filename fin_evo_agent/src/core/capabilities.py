"""Capability-based permission system for tool validation.

Each tool category has specific capabilities that determine:
- Which modules it can import
- What operations it can perform
- How it should be verified

This module now delegates to the centralized constraints module for actual
constraint values, while maintaining the same API for backwards compatibility.
"""

from enum import Enum
from typing import Set, Dict, List
from src.core.constraints import get_constraints


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


# Capabilities granted to each tool category (kept for semantic meaning)
CATEGORY_CAPABILITIES: Dict[ToolCategory, Set[ToolCapability]] = {
    ToolCategory.FETCH: {
        ToolCapability.FETCH,
        ToolCapability.NETWORK_READ,
        ToolCapability.CACHE_WRITE,
        ToolCapability.CALCULATE,
    },
    ToolCategory.CALCULATE: {
        ToolCapability.CALCULATE,
    },
    ToolCategory.COMPOSITE: {
        ToolCapability.CALCULATE,
    },
}


def get_category_modules(category) -> Set[str]:
    """Get all allowed modules for a tool category.

    Args:
        category: Can be ToolCategory enum or string ('fetch', 'calculation', 'composite')

    Delegates to centralized constraints for actual module lists.
    """
    if isinstance(category, ToolCategory):
        category = category.value

    constraints = get_constraints()
    return constraints.get_allowed_modules(category)


def get_category_capabilities(category: str) -> Set[ToolCapability]:
    """Get capabilities for a category (string version for flexibility)."""
    try:
        cat = ToolCategory(category)
        return CATEGORY_CAPABILITIES.get(cat, set())
    except ValueError:
        return CATEGORY_CAPABILITIES[ToolCategory.CALCULATE]


def get_banned_modules_for_category(category: str) -> Set[str]:
    """Get banned modules for a specific category.

    Delegates to centralized constraints.
    """
    constraints = get_constraints()
    return constraints.get_banned_modules(category)


# Properties that delegate to centralized constraints for backwards compatibility
@property
def ALWAYS_BANNED_MODULES() -> Set[str]:
    """Get always banned modules from centralized config."""
    return get_constraints().always_banned_modules


@property
def ALWAYS_BANNED_CALLS() -> Set[str]:
    """Get always banned calls from centralized config."""
    return get_constraints().always_banned_calls


@property
def ALWAYS_BANNED_ATTRIBUTES() -> Set[str]:
    """Get always banned attributes from centralized config."""
    return get_constraints().always_banned_attributes


# Module-level accessors for backwards compatibility
def _get_always_banned_modules() -> Set[str]:
    return get_constraints().always_banned_modules

def _get_always_banned_calls() -> Set[str]:
    return get_constraints().always_banned_calls

def _get_always_banned_attributes() -> Set[str]:
    return get_constraints().always_banned_attributes

# For backwards compatibility, also expose as module-level constants
# These delegate to centralized config on access
ALWAYS_BANNED_MODULES = _get_always_banned_modules()
ALWAYS_BANNED_CALLS = _get_always_banned_calls()
ALWAYS_BANNED_ATTRIBUTES = _get_always_banned_attributes()


if __name__ == "__main__":
    # Test module mappings - now delegating to centralized constraints
    print("=== Capability System (Centralized Constraints) ===")

    print("\n=== Category Allowed Modules ===")
    for cat in ToolCategory:
        modules = get_category_modules(cat)
        print(f"{cat.value}: {sorted(modules)}")

    print("\n=== Category Banned Modules ===")
    for cat in ['fetch', 'calculation', 'composite']:
        banned = get_banned_modules_for_category(cat)
        print(f"{cat}: {len(banned)} banned modules")

    print("\n=== Always Banned (from constraints.yaml) ===")
    constraints = get_constraints()
    print(f"Modules: {len(constraints.always_banned_modules)}")
    print(f"Calls: {len(constraints.always_banned_calls)}")
    print(f"Attributes: {len(constraints.always_banned_attributes)}")

    print("\nCapability system tests passed!")

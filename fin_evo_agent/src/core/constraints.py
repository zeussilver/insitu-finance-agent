"""Centralized runtime constraints loaded from YAML configuration.

Single source of truth for all capability and execution rules.
All modules should import constraints from this module.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Set, List, Optional
import yaml


@dataclass
class ExecutionConstraints:
    """Execution limits for tool sandboxing."""
    timeout_sec: int = 30
    memory_mb: int = 512
    max_retries: int = 3
    retry_delay_sec: float = 1.0


@dataclass
class CategoryConstraints:
    """Constraints for a specific tool category."""
    allowed_modules: Set[str] = field(default_factory=set)
    banned_modules: Set[str] = field(default_factory=set)


@dataclass
class VerificationConstraints:
    """Verification pipeline configuration."""
    max_retries: int = 3
    retry_delay_sec: float = 1.0
    schema_extraction_accuracy_gate: float = 0.95


@dataclass
class EvolutionGatesConstraints:
    """Evolution gates configuration."""
    default_mode: str = "dev"  # 'prod' or 'dev'
    checkpoint_timeout_sec: int = 60
    approval_timeout_sec: int = 300


@dataclass
class Constraints:
    """Root constraints container loaded from YAML."""
    execution: ExecutionConstraints = field(default_factory=ExecutionConstraints)
    capabilities: Dict[str, CategoryConstraints] = field(default_factory=dict)
    always_banned_modules: Set[str] = field(default_factory=set)
    always_banned_calls: Set[str] = field(default_factory=set)
    always_banned_attributes: Set[str] = field(default_factory=set)
    verification: VerificationConstraints = field(default_factory=VerificationConstraints)
    evolution_gates: EvolutionGatesConstraints = field(default_factory=EvolutionGatesConstraints)

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "Constraints":
        """Load constraints from YAML file with validation."""
        if not yaml_path.exists():
            raise FileNotFoundError(f"Constraints file not found: {yaml_path}")

        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        return cls._parse(data)

    @classmethod
    def _parse(cls, data: dict) -> "Constraints":
        """Parse and validate YAML data into Constraints object."""
        # Parse execution constraints
        exec_data = data.get('execution', {})
        execution = ExecutionConstraints(
            timeout_sec=exec_data.get('timeout_sec', 30),
            memory_mb=exec_data.get('memory_mb', 512),
            max_retries=exec_data.get('max_retries', 3),
            retry_delay_sec=exec_data.get('retry_delay_sec', 1.0),
        )

        # Validate execution constraints
        if execution.timeout_sec <= 0:
            raise ValueError("execution.timeout_sec must be positive")
        if execution.memory_mb <= 0:
            raise ValueError("execution.memory_mb must be positive")

        # Parse category capabilities
        capabilities = {}
        caps_data = data.get('capabilities', {})
        for category, cat_data in caps_data.items():
            capabilities[category] = CategoryConstraints(
                allowed_modules=set(cat_data.get('allowed_modules', [])),
                banned_modules=set(cat_data.get('banned_modules', [])),
            )

        # Parse always-banned lists
        always_banned_modules = set(data.get('always_banned_modules', []))
        always_banned_calls = set(data.get('always_banned_calls', []))
        always_banned_attributes = set(data.get('always_banned_attributes', []))

        # Parse verification constraints
        verif_data = data.get('verification', {})
        verification = VerificationConstraints(
            max_retries=verif_data.get('max_retries', 3),
            retry_delay_sec=verif_data.get('retry_delay_sec', 1.0),
            schema_extraction_accuracy_gate=verif_data.get('schema_extraction_accuracy_gate', 0.95),
        )

        # Parse evolution gates constraints
        gates_data = data.get('evolution_gates', {})
        evolution_gates = EvolutionGatesConstraints(
            default_mode=gates_data.get('default_mode', 'dev'),
            checkpoint_timeout_sec=gates_data.get('checkpoint_timeout_sec', 60),
            approval_timeout_sec=gates_data.get('approval_timeout_sec', 300),
        )

        return cls(
            execution=execution,
            capabilities=capabilities,
            always_banned_modules=always_banned_modules,
            always_banned_calls=always_banned_calls,
            always_banned_attributes=always_banned_attributes,
            verification=verification,
            evolution_gates=evolution_gates,
        )

    def get_allowed_modules(self, category: str) -> Set[str]:
        """Get allowed modules for a category."""
        cat_constraints = self.capabilities.get(category)
        if cat_constraints:
            return cat_constraints.allowed_modules
        # Default to calculation if category not found
        return self.capabilities.get('calculation', CategoryConstraints()).allowed_modules

    def get_banned_modules(self, category: str) -> Set[str]:
        """Get banned modules for a category (always banned + category-specific)."""
        banned = self.always_banned_modules.copy()
        cat_constraints = self.capabilities.get(category)
        if cat_constraints:
            banned.update(cat_constraints.banned_modules)
        return banned

    def get_always_banned_calls(self) -> Set[str]:
        """Get always banned function calls."""
        return self.always_banned_calls

    def get_always_banned_attributes(self) -> Set[str]:
        """Get always banned magic attributes."""
        return self.always_banned_attributes


# Global singleton - loaded on first access
_constraints: Optional[Constraints] = None


def get_constraints() -> Constraints:
    """Get the global constraints singleton."""
    global _constraints
    if _constraints is None:
        _constraints = load_constraints()
    return _constraints


def load_constraints(yaml_path: Optional[Path] = None) -> Constraints:
    """Load constraints from YAML file.

    Args:
        yaml_path: Path to constraints YAML. If None, uses default location.

    Returns:
        Loaded Constraints object.
    """
    if yaml_path is None:
        # Default path relative to this file
        this_dir = Path(__file__).parent
        yaml_path = this_dir.parent.parent / "configs" / "constraints.yaml"

    return Constraints.from_yaml(yaml_path)


def reload_constraints(yaml_path: Optional[Path] = None) -> Constraints:
    """Reload constraints from YAML (useful for testing)."""
    global _constraints
    _constraints = load_constraints(yaml_path)
    return _constraints


if __name__ == "__main__":
    # Test loading constraints
    print("=== Loading Constraints ===")
    constraints = get_constraints()

    print(f"\nExecution timeout: {constraints.execution.timeout_sec}s")
    print(f"Execution memory: {constraints.execution.memory_mb}MB")

    print("\n=== Category Modules ===")
    for category in ['calculation', 'fetch', 'composite']:
        allowed = constraints.get_allowed_modules(category)
        banned = constraints.get_banned_modules(category)
        print(f"{category}:")
        print(f"  allowed: {sorted(allowed)}")
        print(f"  banned: {len(banned)} modules")

    print("\n=== Always Banned ===")
    print(f"Modules: {len(constraints.always_banned_modules)}")
    print(f"Calls: {len(constraints.always_banned_calls)}")
    print(f"Attributes: {len(constraints.always_banned_attributes)}")

    print("\nConstraints loaded successfully!")

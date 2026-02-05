"""Verification Gateway: Single enforcement point for all tool registration.

All tool registration MUST go through this gateway. Direct registry.register()
calls from evolution modules are prohibited.

The gateway ensures:
1. All tools pass multi-stage verification before registration
2. Rollback checkpoints are created for recoverability
3. All registration attempts are logged (success/failure)
4. No verification bypass is possible
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.verifier import MultiStageVerifier, VerificationReport
from src.core.registry import ToolRegistry
from src.core.models import ToolArtifact
from src.core.contracts import ToolContract, get_contract, infer_contract_from_query
from src.core.gates import EvolutionGate, EvolutionGatekeeper, CheckpointManager
from src.config import ROOT_DIR


class VerificationError(Exception):
    """Raised when tool fails verification."""

    def __init__(self, message: str, report: Optional[VerificationReport] = None):
        super().__init__(message)
        self.report = report


class VerificationGateway:
    """Single enforcement point for all tool registration.

    All tool registration MUST go through this gateway's submit() method.
    This ensures:
    - Every tool passes multi-stage verification
    - Rollback checkpoints are created
    - All attempts are logged for audit trail
    """

    def __init__(
        self,
        verifier: MultiStageVerifier = None,
        registry: ToolRegistry = None,
        gatekeeper: EvolutionGatekeeper = None,
    ):
        """Initialize the gateway.

        Args:
            verifier: Multi-stage verifier instance
            registry: Tool registry instance
            gatekeeper: Evolution gatekeeper for approval tiers
        """
        self.verifier = verifier or MultiStageVerifier()
        self.registry = registry or ToolRegistry()
        self.gatekeeper = gatekeeper or EvolutionGatekeeper()
        self.checkpoint_manager = CheckpointManager()

        # Set up logging
        self.logs_dir = ROOT_DIR / "data" / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging for gateway operations."""
        self.logger = logging.getLogger("VerificationGateway")
        self.logger.setLevel(logging.INFO)

        # File handler
        log_path = self.logs_dir / "gateway.log"
        if not self.logger.handlers:
            handler = logging.FileHandler(log_path)
            handler.setFormatter(logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s'
            ))
            self.logger.addHandler(handler)

    def _log_attempt(
        self,
        action: str,
        tool_name: str,
        category: str,
        success: bool,
        details: Dict[str, Any] = None
    ):
        """Log a registration attempt."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "tool_name": tool_name,
            "category": category,
            "success": success,
            "details": details or {}
        }

        # Write to structured log file
        log_path = self.logs_dir / "gateway_attempts.jsonl"
        with open(log_path, 'a') as f:
            f.write(json.dumps(log_entry, default=str) + "\n")

        # Also log to standard logger
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"{action} | {tool_name} ({category}) | {status}")

    def submit(
        self,
        code: str,
        category: str,
        contract: Optional[ToolContract] = None,
        contract_id: Optional[str] = None,
        task: Optional[str] = None,
        task_id: str = "unknown",
        real_data: Optional[Dict[str, Any]] = None,
        force: bool = False,
    ) -> Tuple[bool, Optional[ToolArtifact], VerificationReport]:
        """Submit a tool for verification and registration.

        This is the ONLY approved way to register tools. All tool registration
        MUST go through this method.

        Args:
            code: Python source code for the tool
            category: Tool category ('fetch', 'calculation', 'composite')
            contract: Optional explicit contract for validation
            contract_id: Optional contract ID to look up
            task: Optional task description for contract inference
            task_id: Task identifier for tracing
            real_data: Optional real data for integration testing (fetch tools)
            force: If True, skip gatekeeper approval (for testing only)

        Returns:
            (success, tool, report) - tool is None if verification failed

        Raises:
            VerificationError: If verification fails
        """
        # Extract function name for logging
        import re
        match = re.search(r'^def\s+(\w+)\s*\(', code, re.MULTILINE)
        func_name = match.group(1) if match else "unknown"

        # Resolve contract
        if contract is None and contract_id:
            contract = get_contract(contract_id)
        elif contract is None and task:
            contract = infer_contract_from_query(task)

        # Log the submission attempt
        self._log_attempt(
            "SUBMIT",
            func_name,
            category,
            success=False,  # Will update if successful
            details={"contract_id": contract.contract_id if contract else None}
        )

        # Create rollback checkpoint
        checkpoint_id = self.checkpoint_manager.create_checkpoint(
            action="submit_tool",
            context={
                "tool_name": func_name,
                "category": category,
                "contract_id": contract.contract_id if contract else None,
            }
        )

        try:
            # Run multi-stage verification
            passed, report = self.verifier.verify_all_stages(
                code=code,
                category=category,
                task_id=task_id,
                contract=contract,
                real_data=real_data,
            )

            if not passed:
                # Verification failed - log and checkpoint as failed
                self.checkpoint_manager.mark_failed(checkpoint_id, "Verification failed")
                self._log_attempt(
                    "VERIFICATION_FAILED",
                    func_name,
                    category,
                    success=False,
                    details={
                        "checkpoint_id": checkpoint_id,
                        "report": report.to_dict()
                    }
                )
                return False, None, report

            # Verification passed - register the tool
            # This goes through gatekeeper for approval tier check
            if not force:
                action = "create_tool" if not self._tool_exists(func_name) else "modify_tool"
                approved, _ = self.gatekeeper.execute(
                    action,
                    {"tool_name": func_name, "category": category},
                    lambda: None  # Dummy - actual work done below
                )

                if not approved:
                    self.checkpoint_manager.mark_failed(checkpoint_id, "Gatekeeper denied")
                    self._log_attempt(
                        "GATEKEEPER_DENIED",
                        func_name,
                        category,
                        success=False,
                        details={"checkpoint_id": checkpoint_id, "action": action}
                    )
                    return False, None, report

            # Register the tool
            # Determine permissions based on category
            if category == 'fetch':
                from src.core.models import Permission
                permissions = [Permission.NETWORK_READ.value, Permission.CALC_ONLY.value]
            else:
                from src.core.models import Permission
                permissions = [Permission.CALC_ONLY.value]

            tool = self.registry.register(
                name=func_name,
                code=code,
                args_schema=self._extract_args_schema(code),
                permissions=permissions,
            )

            # Update schema with additional fields after registration
            if tool:
                from src.core.capabilities import get_category_capabilities
                capabilities = [cap.value for cap in get_category_capabilities(category)]

                self.registry.update_schema(
                    tool.id,
                    category=category,
                )

                # Update verification-related fields
                self._update_tool_verification_fields(
                    tool.id,
                    capabilities=capabilities,
                    contract_id=contract.contract_id if contract else None,
                    verification_stage=report.final_stage.value,
                )

            # Mark checkpoint as complete
            self.checkpoint_manager.mark_complete(checkpoint_id)

            # Log success
            self._log_attempt(
                "REGISTERED",
                func_name,
                category,
                success=True,
                details={
                    "checkpoint_id": checkpoint_id,
                    "tool_id": tool.id,
                    "version": tool.semantic_version,
                    "final_stage": report.final_stage.name,
                }
            )

            return True, tool, report

        except Exception as e:
            # Unexpected error - mark checkpoint failed
            self.checkpoint_manager.mark_failed(checkpoint_id, str(e))
            self._log_attempt(
                "ERROR",
                func_name,
                category,
                success=False,
                details={"checkpoint_id": checkpoint_id, "error": str(e)}
            )
            raise

    def _tool_exists(self, name: str) -> bool:
        """Check if a tool already exists in registry."""
        try:
            tool = self.registry.get_by_name(name)
            return tool is not None
        except Exception:
            return False

    def _update_tool_verification_fields(
        self,
        tool_id: int,
        capabilities: list,
        contract_id: Optional[str],
        verification_stage: int
    ):
        """Update tool with verification-related fields."""
        from sqlmodel import Session
        from src.core.models import get_engine, ToolArtifact

        engine = get_engine()
        with Session(engine) as session:
            tool = session.get(ToolArtifact, tool_id)
            if tool:
                tool.capabilities = capabilities
                tool.contract_id = contract_id
                tool.verification_stage = verification_stage
                session.add(tool)
                session.commit()

    def _extract_args_schema(self, code: str) -> Dict[str, str]:
        """Extract argument schema from function signature."""
        import re
        import ast

        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    schema = {}
                    for arg in node.args.args:
                        arg_name = arg.arg
                        if arg_name == 'self':
                            continue
                        # Try to get annotation
                        if arg.annotation:
                            if isinstance(arg.annotation, ast.Name):
                                schema[arg_name] = arg.annotation.id
                            elif isinstance(arg.annotation, ast.Constant):
                                schema[arg_name] = str(arg.annotation.value)
                            else:
                                schema[arg_name] = "Any"
                        else:
                            schema[arg_name] = "Any"
                    return schema
        except:
            pass

        return {}

    def verify_only(
        self,
        code: str,
        category: str,
        contract: Optional[ToolContract] = None,
        task_id: str = "unknown",
    ) -> Tuple[bool, VerificationReport]:
        """Run verification without registering.

        Useful for pre-checks before committing to registration.

        Args:
            code: Python source code
            category: Tool category
            contract: Optional contract for validation
            task_id: Task identifier

        Returns:
            (passed, report)
        """
        return self.verifier.verify_all_stages(
            code=code,
            category=category,
            task_id=task_id,
            contract=contract,
        )

    def get_registration_stats(self) -> Dict[str, Any]:
        """Get statistics on gateway operations."""
        log_path = self.logs_dir / "gateway_attempts.jsonl"

        if not log_path.exists():
            return {"total": 0, "success": 0, "failed": 0, "success_rate": 0.0}

        total = 0
        success = 0

        with open(log_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    total += 1
                    if entry.get("success"):
                        success += 1
                except:
                    pass

        return {
            "total": total,
            "success": success,
            "failed": total - success,
            "success_rate": success / total if total > 0 else 0.0
        }


# Global gateway instance
_gateway: Optional[VerificationGateway] = None


def get_gateway() -> VerificationGateway:
    """Get the global gateway instance."""
    global _gateway
    if _gateway is None:
        _gateway = VerificationGateway()
    return _gateway


if __name__ == "__main__":
    print("=== Verification Gateway Test ===\n")

    gateway = VerificationGateway()

    # Test code - RSI calculation
    test_code = '''
import pandas as pd
import numpy as np

def calc_rsi(prices: list, period: int = 14) -> float:
    """Calculate RSI indicator."""
    if len(prices) < period + 1:
        return 50.0

    s = pd.Series(prices)
    delta = s.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.inf)
    rsi = 100 - (100 / (1 + rs))

    return float(rsi.iloc[-1])

if __name__ == "__main__":
    prices = [44, 44.5, 44.25, 43.75, 44.5, 44.25, 44.5, 45, 45.5, 46, 46.5, 47, 46.5, 47, 47.5]
    result = calc_rsi(prices, 5)
    assert 0 <= result <= 100, f"RSI out of range: {result}"
    print("Test passed!")
'''

    # Test verify_only
    print("1. Testing verify_only...")
    passed, report = gateway.verify_only(
        code=test_code,
        category="calculation",
        task_id="test_001"
    )
    print(f"   Verification: {'PASS' if passed else 'FAIL'}")
    print(f"   Final stage: {report.final_stage.name}")

    # Test full submit (with force to skip approval in dev mode)
    print("\n2. Testing submit...")
    success, tool, report = gateway.submit(
        code=test_code,
        category="calculation",
        contract_id="calc_rsi",
        task_id="test_002",
        force=True
    )

    if success:
        print(f"   Tool registered: {tool.name} v{tool.semantic_version}")
    else:
        print(f"   Registration failed")

    # Test with unsafe code
    print("\n3. Testing unsafe code submission...")
    unsafe_code = '''
import os
def unsafe_func():
    os.system("ls")
'''
    success, tool, report = gateway.submit(
        code=unsafe_code,
        category="calculation",
        task_id="test_unsafe",
        force=True
    )
    print(f"   Unsafe code blocked: {'Yes (expected)' if not success else 'No (unexpected)'}")

    # Show stats
    print("\n4. Gateway statistics:")
    stats = gateway.get_registration_stats()
    print(f"   Total attempts: {stats['total']}")
    print(f"   Success: {stats['success']}")
    print(f"   Failed: {stats['failed']}")
    print(f"   Success rate: {stats['success_rate']:.1%}")

    print("\nGateway tests complete!")

"""Evolution gates for risk-based approval of tool mutations.

Three-tier classification system:
- AUTO: Execute immediately (low risk)
- CHECKPOINT: Log + create rollback point (medium risk)
- APPROVAL: Require human approval (high risk)
"""

import os
import json
import time
from enum import Enum, auto
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Callable

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.config import ROOT_DIR


class EvolutionGate(Enum):
    """Gate tiers for evolution actions."""
    AUTO = 1        # Execute immediately
    CHECKPOINT = 2  # Log + rollback point
    APPROVAL = 3    # Require human approval


class GateMode(Enum):
    """Gate enforcement modes."""
    DEV = "dev"     # Relaxed - APPROVAL becomes warning only
    PROD = "prod"   # Strict - full enforcement


# Action classifications
ACTION_GATES: Dict[str, EvolutionGate] = {
    # AUTO tier - low risk read operations
    "read_cached_data": EvolutionGate.AUTO,
    "execute_calculation": EvolutionGate.AUTO,
    "list_tools": EvolutionGate.AUTO,
    "get_tool_info": EvolutionGate.AUTO,

    # CHECKPOINT tier - tool mutations with rollback
    "create_tool": EvolutionGate.CHECKPOINT,
    "modify_tool": EvolutionGate.CHECKPOINT,
    "execute_fetch": EvolutionGate.CHECKPOINT,
    "refine_tool": EvolutionGate.CHECKPOINT,

    # APPROVAL tier - permanent changes
    "persist_tool": EvolutionGate.APPROVAL,
    "delete_tool": EvolutionGate.APPROVAL,
    "modify_verification_rules": EvolutionGate.APPROVAL,
    "modify_constraints": EvolutionGate.APPROVAL,
}


class CheckpointManager:
    """Manages rollback checkpoints for CHECKPOINT-tier actions."""

    def __init__(self, checkpoint_dir: Optional[Path] = None):
        """Initialize checkpoint manager."""
        self.checkpoint_dir = checkpoint_dir or (ROOT_DIR / "data" / "checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def create_checkpoint(self, action: str, context: Dict[str, Any]) -> str:
        """Create a rollback checkpoint before action execution.

        Args:
            action: Action being performed
            context: Context data to save for rollback

        Returns:
            Checkpoint ID
        """
        checkpoint_id = f"cp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{action[:20]}"
        checkpoint_path = self.checkpoint_dir / f"{checkpoint_id}.json"

        checkpoint_data = {
            "id": checkpoint_id,
            "action": action,
            "context": context,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
        }

        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2, default=str)

        return checkpoint_id

    def mark_complete(self, checkpoint_id: str) -> None:
        """Mark checkpoint as successfully completed."""
        checkpoint_path = self.checkpoint_dir / f"{checkpoint_id}.json"
        if checkpoint_path.exists():
            with open(checkpoint_path, 'r') as f:
                data = json.load(f)
            data["status"] = "completed"
            data["completed_at"] = datetime.now().isoformat()
            with open(checkpoint_path, 'w') as f:
                json.dump(data, f, indent=2)

    def mark_failed(self, checkpoint_id: str, error: str) -> None:
        """Mark checkpoint as failed."""
        checkpoint_path = self.checkpoint_dir / f"{checkpoint_id}.json"
        if checkpoint_path.exists():
            with open(checkpoint_path, 'r') as f:
                data = json.load(f)
            data["status"] = "failed"
            data["error"] = error
            data["failed_at"] = datetime.now().isoformat()
            with open(checkpoint_path, 'w') as f:
                json.dump(data, f, indent=2)


class EvolutionGatekeeper:
    """Gatekeeper for evolution actions with risk-based approval."""

    def __init__(
        self,
        mode: Optional[GateMode] = None,
        checkpoint_timeout_sec: int = 60,
        approval_timeout_sec: int = 300,
        approval_callback: Optional[Callable[[str, Dict], bool]] = None,
    ):
        """Initialize gatekeeper.

        Args:
            mode: Gate enforcement mode (default from env or DEV)
            checkpoint_timeout_sec: Timeout for checkpoint creation
            approval_timeout_sec: Timeout for human approval
            approval_callback: Custom approval function (for testing)
        """
        if mode is None:
            env_mode = os.getenv("EVOLUTION_GATE_MODE", "dev").lower()
            mode = GateMode.PROD if env_mode == "prod" else GateMode.DEV

        self.mode = mode
        self.checkpoint_timeout_sec = checkpoint_timeout_sec
        self.approval_timeout_sec = approval_timeout_sec
        self.approval_callback = approval_callback
        self.checkpoint_manager = CheckpointManager()

        # Logging
        self.logs_dir = ROOT_DIR / "data" / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def classify(self, action: str, context: Optional[Dict] = None) -> EvolutionGate:
        """Classify action into gate tier.

        Args:
            action: Action identifier
            context: Additional context for classification

        Returns:
            Appropriate gate tier
        """
        return ACTION_GATES.get(action, EvolutionGate.CHECKPOINT)

    def _log_action(
        self,
        action: str,
        gate: EvolutionGate,
        context: Dict,
        result: str,
        checkpoint_id: Optional[str] = None
    ) -> None:
        """Log action for audit trail."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "gate": gate.name,
            "mode": self.mode.value,
            "context": context,
            "result": result,
            "checkpoint_id": checkpoint_id,
        }

        log_path = self.logs_dir / "evolution_gates.log"
        with open(log_path, 'a') as f:
            f.write(json.dumps(log_entry, default=str) + "\n")

    def _request_cli_approval(self, action: str, context: Dict) -> bool:
        """Request human approval via CLI."""
        print("\n" + "=" * 60)
        print(f"[APPROVAL REQUIRED] Action: {action}")
        print(f"Context: {json.dumps(context, indent=2, default=str)}")
        print("=" * 60)

        try:
            response = input(f"Approve this action? (y/n) [{self.approval_timeout_sec}s timeout]: ")
            return response.lower().strip() in ('y', 'yes')
        except (EOFError, KeyboardInterrupt):
            print("\nApproval cancelled.")
            return False

    def execute(
        self,
        action: str,
        context: Dict[str, Any],
        func: Callable[[], Any],
    ) -> tuple[bool, Any]:
        """Execute action through gate with appropriate checks.

        Args:
            action: Action identifier
            context: Context for logging/approval
            func: Function to execute if approved

        Returns:
            (success, result) tuple
        """
        gate = self.classify(action, context)

        # AUTO tier - execute immediately
        if gate == EvolutionGate.AUTO:
            self._log_action(action, gate, context, "executed")
            result = func()
            return True, result

        # CHECKPOINT tier - create checkpoint, then execute
        if gate == EvolutionGate.CHECKPOINT:
            checkpoint_id = self.checkpoint_manager.create_checkpoint(action, context)
            self._log_action(action, gate, context, "checkpoint_created", checkpoint_id)

            try:
                result = func()
                self.checkpoint_manager.mark_complete(checkpoint_id)
                self._log_action(action, gate, context, "completed", checkpoint_id)
                return True, result
            except Exception as e:
                self.checkpoint_manager.mark_failed(checkpoint_id, str(e))
                self._log_action(action, gate, context, f"failed: {e}", checkpoint_id)
                raise

        # APPROVAL tier - require approval (or warn in dev mode)
        if gate == EvolutionGate.APPROVAL:
            if self.mode == GateMode.DEV:
                # Dev mode: warn but proceed
                print(f"[WARNING] APPROVAL-tier action '{action}' auto-approved in dev mode")
                self._log_action(action, gate, context, "auto_approved_dev_mode")
                checkpoint_id = self.checkpoint_manager.create_checkpoint(action, context)
                try:
                    result = func()
                    self.checkpoint_manager.mark_complete(checkpoint_id)
                    return True, result
                except Exception as e:
                    self.checkpoint_manager.mark_failed(checkpoint_id, str(e))
                    raise

            # Prod mode: require approval
            if self.approval_callback:
                approved = self.approval_callback(action, context)
            else:
                approved = self._request_cli_approval(action, context)

            if not approved:
                self._log_action(action, gate, context, "denied")
                return False, None

            # Approved - create checkpoint and execute
            checkpoint_id = self.checkpoint_manager.create_checkpoint(action, context)
            self._log_action(action, gate, context, "approved", checkpoint_id)

            try:
                result = func()
                self.checkpoint_manager.mark_complete(checkpoint_id)
                return True, result
            except Exception as e:
                self.checkpoint_manager.mark_failed(checkpoint_id, str(e))
                self._log_action(action, gate, context, f"failed_after_approval: {e}", checkpoint_id)
                raise

        return False, None


if __name__ == "__main__":
    print("=== Evolution Gates Test ===")

    # Test gate classification
    print("\nGate Classifications:")
    for action, gate in ACTION_GATES.items():
        print(f"  {action}: {gate.name}")

    # Test gatekeeper in dev mode
    print("\n=== Testing Gatekeeper (DEV mode) ===")
    gatekeeper = EvolutionGatekeeper(mode=GateMode.DEV)

    # AUTO tier action
    success, result = gatekeeper.execute(
        "read_cached_data",
        {"symbol": "AAPL"},
        lambda: {"data": "cached"}
    )
    print(f"AUTO tier: success={success}")

    # CHECKPOINT tier action
    success, result = gatekeeper.execute(
        "create_tool",
        {"tool_name": "calc_ma", "category": "calculation"},
        lambda: {"tool_id": "t123"}
    )
    print(f"CHECKPOINT tier: success={success}")

    # APPROVAL tier action (auto-approved in dev mode)
    success, result = gatekeeper.execute(
        "persist_tool",
        {"tool_name": "calc_ma", "version": "0.1.0"},
        lambda: {"persisted": True}
    )
    print(f"APPROVAL tier (dev mode): success={success}")

    print("\nEvolution gates tests passed!")

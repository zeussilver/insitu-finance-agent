"""SimpleDeduplicator: Contract-based tool deduplication.

When multiple tools exist for the same contract_id, keep the best one
based on a scoring function and mark the rest as DEPRECATED.

Strategy: Multi-criteria scoring (verification stage > success rate >
speed > version). Intentionally simpler than Yunjue's LLM-guided merger.
"""

import logging
from typing import List, Tuple

from sqlmodel import Session

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
from src.core.models import ToolArtifact, ToolStatus, BatchMergeRecord, get_engine
from src.core.registry import ToolRegistry


class SimpleDeduplicator:
    """Contract-based tool deduplication.

    Scoring criteria (in priority order):
    1. verification_stage (higher = passed more verification stages)
    2. success_count / (success_count + failure_count) = success rate
    3. Lower average execution time (faster is better)
    4. Newer version (tie-breaker)
    """

    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.logger = logging.getLogger("SimpleDeduplicator")

    def check_and_resolve(
        self,
        new_tool_id: int,
        contract_id: str,
    ) -> str:
        """Check if deduplication is needed after a new tool is registered.

        Returns:
            "kept"       - new tool is the best, others deprecated
            "superseded" - new tool is worse, it gets deprecated
            "no_action"  - only one tool for this contract, nothing to do
        """
        candidates = self.registry.find_by_contract_id(contract_id)

        # Filter out already-deprecated tools
        active = [t for t in candidates if t.status != ToolStatus.DEPRECATED]

        if len(active) <= 1:
            return "no_action"

        # Score all active candidates
        scored = [(self.score_tool(t), t) for t in active]
        scored.sort(reverse=True)  # Best first

        best_tool = scored[0][1]
        rest = [t for _, t in scored[1:]]

        # Deprecate non-best tools
        for tool in rest:
            self._deprecate_tool(tool, f"Superseded by {best_tool.name} (id={best_tool.id})")

        # Record the merge decision
        self.create_merge_record(best_tool, rest, contract_id)

        if best_tool.id == new_tool_id:
            self.logger.info(f"New tool {new_tool_id} is best for {contract_id}")
            return "kept"
        else:
            self.logger.info(f"New tool {new_tool_id} superseded by {best_tool.name}")
            return "superseded"

    def score_tool(self, tool: ToolArtifact) -> Tuple[int, float, float, str]:
        """Score a tool for ranking. Higher tuple is better.

        Returns tuple for lexicographic comparison:
            (verification_stage, success_rate, -avg_exec_time, version)
        """
        stage = tool.verification_stage or 0

        # success_rate: derive from execution traces (approximated by status)
        # For now, tools that passed verification get 1.0, others 0.5
        rate = 1.0 if tool.status == ToolStatus.PROVISIONAL else 0.5

        # avg_exec_time: lower is better, so negate for sorting
        # Not tracked per-tool yet, use 0.0 as neutral
        avg_time = 0.0

        version = tool.semantic_version or "0.0.0"

        return (stage, rate, avg_time, version)

    def _deprecate_tool(self, tool: ToolArtifact, reason: str) -> None:
        """Mark a tool as DEPRECATED with reason."""
        engine = get_engine()
        with Session(engine) as session:
            db_tool = session.get(ToolArtifact, tool.id)
            if db_tool and db_tool.status != ToolStatus.DEPRECATED:
                db_tool.status = ToolStatus.DEPRECATED
                session.add(db_tool)
                session.commit()
                self.logger.info(f"Deprecated tool {tool.name} (id={tool.id}): {reason}")

    def create_merge_record(
        self,
        kept_tool: ToolArtifact,
        deprecated_tools: List[ToolArtifact],
        contract_id: str,
    ) -> BatchMergeRecord:
        """Create a BatchMergeRecord documenting the dedup decision."""
        engine = get_engine()
        with Session(engine) as session:
            record = BatchMergeRecord(
                source_tool_ids=[t.id for t in deprecated_tools],
                canonical_tool_id=kept_tool.id,
                strategy="contract_dedup",
                regression_stats={
                    "contract_id": contract_id,
                    "deprecated_count": len(deprecated_tools),
                    "kept_tool_name": kept_tool.name,
                    "kept_tool_version": kept_tool.semantic_version,
                },
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

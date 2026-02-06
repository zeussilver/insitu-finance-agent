"""BatchEvolutionManager: Parallel synthesis with sequential registration.

Orchestrates batch tool evolution:
- Phase 1: Parallel synthesis via ThreadPoolExecutor (LLM calls are I/O-bound)
- Phase 2: Sequential registration + deduplication (SQLite single-writer)
- Phase 3: Metrics recording

All tool registration routes through gateway.submit() — no direct registry writes.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Optional

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
from src.core.contracts import infer_contract_from_query
from src.core.gateway import VerificationGateway
from src.core.registry import ToolRegistry
from src.evolution.synthesizer import Synthesizer
from src.evolution.merger import SimpleDeduplicator


@dataclass
class EvolutionResult:
    """Result of synthesizing one tool."""
    task_id: str
    task_query: str
    category: str
    contract_id: Optional[str]
    success: bool
    tool_id: Optional[int] = None
    tool_name: Optional[str] = None
    error: Optional[str] = None
    synthesis_time_sec: float = 0.0
    reused: bool = False
    verification_stage_reached: int = 0


@dataclass
class BatchEvolutionReport:
    """Aggregated report for one batch evolution round."""
    batch_id: str
    round_number: int
    total_tasks: int
    synthesis_success: int = 0
    registration_success: int = 0
    reused_count: int = 0
    dedup_merged: int = 0
    total_time_sec: float = 0.0
    results: List[EvolutionResult] = field(default_factory=list)

    @property
    def synthesis_rate(self) -> float:
        return self.synthesis_success / self.total_tasks if self.total_tasks > 0 else 0.0

    @property
    def registration_rate(self) -> float:
        return self.registration_success / self.total_tasks if self.total_tasks > 0 else 0.0

    @property
    def reuse_rate(self) -> float:
        return self.reused_count / self.total_tasks if self.total_tasks > 0 else 0.0


class BatchEvolutionManager:
    """Orchestrate parallel tool synthesis with sequential registration.

    Design decisions:
    - Synthesis is parallelized (LLM API calls are I/O-bound)
    - Registration happens inside the worker thread via gateway.submit()
      (called by synthesize_with_refine internally). SQLite handles
      concurrent writes with its internal locking.
    - Deduplication runs after synthesis completes for each task
    - max_workers=3 for DashScope rate limit safety
    """

    def __init__(
        self,
        synthesizer: Synthesizer,
        gateway: VerificationGateway,
        deduplicator: SimpleDeduplicator,
        registry: ToolRegistry,
        metrics_collector=None,
        max_workers: int = 3,
        task_timeout_sec: int = 300,
    ):
        self.synthesizer = synthesizer
        self.gateway = gateway
        self.deduplicator = deduplicator
        self.registry = registry
        self.metrics = metrics_collector
        self.max_workers = max_workers
        self.task_timeout_sec = task_timeout_sec
        self.logger = logging.getLogger("BatchEvolutionManager")

    def evolve_batch(
        self,
        tasks: List[dict],
        round_number: int = 1,
    ) -> BatchEvolutionReport:
        """Run one round of batch evolution.

        Phase 1: Parallel synthesis (ThreadPoolExecutor)
        Phase 2: Deduplication pass
        Phase 3: Metrics recording
        """
        batch_id = f"batch_{round_number}_{int(time.time())}"
        report = BatchEvolutionReport(
            batch_id=batch_id,
            round_number=round_number,
            total_tasks=len(tasks),
        )
        start_time = time.time()

        # === Phase 1: Parallel Synthesis ===
        pending_results = []  # results that need dedup

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {}
            for task in tasks:
                # Check warm-start reuse
                existing = self._find_existing_tool(task)
                if existing:
                    self.logger.info(f"Reuse existing tool for {task['task_id']}: {existing.name}")
                    result = EvolutionResult(
                        task_id=task["task_id"],
                        task_query=task["query"],
                        category=task.get("category", ""),
                        contract_id=existing.contract_id,
                        success=True,
                        tool_id=existing.id,
                        tool_name=existing.name,
                        synthesis_time_sec=0.0,
                        reused=True,
                        verification_stage_reached=existing.verification_stage or 0,
                    )
                    report.results.append(result)
                    report.synthesis_success += 1
                    report.registration_success += 1
                    report.reused_count += 1
                    continue

                # Submit for parallel synthesis
                future = pool.submit(self._synthesize_one, task)
                futures[future] = task

            # Collect results as they complete
            for future in as_completed(futures):
                task = futures[future]
                try:
                    result = future.result(timeout=self.task_timeout_sec + 30)
                    if result.success:
                        report.synthesis_success += 1
                        report.registration_success += 1
                        pending_results.append(result)
                    report.results.append(result)
                except Exception as e:
                    self.logger.error(f"Synthesis failed for {task['task_id']}: {e}")
                    report.results.append(EvolutionResult(
                        task_id=task["task_id"],
                        task_query=task["query"],
                        category=task.get("category", ""),
                        contract_id=None,
                        success=False,
                        error=str(e),
                    ))

        # === Phase 2: Deduplication ===
        for result in pending_results:
            if result.tool_id and result.contract_id:
                dedup_action = self.deduplicator.check_and_resolve(
                    result.tool_id, result.contract_id
                )
                if dedup_action == "superseded":
                    report.dedup_merged += 1

        # === Phase 3: Metrics ===
        report.total_time_sec = time.time() - start_time
        if self.metrics:
            self.metrics.record_batch(report, self.registry)

        return report

    def evolve_multi_round(
        self,
        tasks: List[dict],
        num_rounds: int = 3,
    ) -> List[BatchEvolutionReport]:
        """Run multiple evolution rounds, each building on the previous.

        Round N+1 benefits from tools registered in Round N:
        - Registry lookup may find existing tool → skip synthesis
        - Warm-start reuse rate should increase across rounds
        """
        reports = []
        for round_num in range(1, num_rounds + 1):
            self.logger.info(f"=== Evolution Round {round_num}/{num_rounds} ===")
            report = self.evolve_batch(tasks, round_number=round_num)
            reports.append(report)
            self.logger.info(
                f"Round {round_num}: {report.synthesis_rate:.0%} synthesis, "
                f"{report.reuse_rate:.0%} reuse, {report.total_time_sec:.1f}s"
            )
        return reports

    def _find_existing_tool(self, task: dict) -> Optional[object]:
        """Check if a tool already exists for this task (warm-start reuse).

        Checks by contract_id first, then by inferred tool name.
        """
        contract_id = task.get("contract_id")
        if contract_id:
            candidates = self.registry.find_by_contract_id(contract_id)
            active = [t for t in candidates if t.status.value != "deprecated" and t.status.value != "failed"]
            if active:
                return active[0]

        # Fallback: try schema-based lookup
        category = task.get("category", "calculation")
        tool = self.registry.find_by_schema(category=category)
        # Only return if we get a very specific match (avoid false positives)
        return None

    def _synthesize_one(self, task: dict) -> EvolutionResult:
        """Synthesize one tool. Runs in a worker thread.

        Uses synthesize_with_refine() which calls gateway.submit() internally.
        SQLite handles concurrent writes via its internal locking.
        """
        start = time.time()
        try:
            category = task.get("category", "calculation")
            contract = infer_contract_from_query(task["query"], category)

            tool, trace = self.synthesizer.synthesize_with_refine(
                task["query"],
                category=category,
                contract=contract,
            )

            elapsed = time.time() - start
            return EvolutionResult(
                task_id=task["task_id"],
                task_query=task["query"],
                category=category,
                contract_id=tool.contract_id if tool else (contract.contract_id if contract else None),
                success=tool is not None,
                tool_id=tool.id if tool else None,
                tool_name=tool.name if tool else None,
                error=None if tool else "Verification failed",
                synthesis_time_sec=elapsed,
                verification_stage_reached=tool.verification_stage if tool else 0,
            )
        except Exception as e:
            elapsed = time.time() - start
            return EvolutionResult(
                task_id=task["task_id"],
                task_query=task["query"],
                category=task.get("category", ""),
                contract_id=None,
                success=False,
                error=str(e),
                synthesis_time_sec=elapsed,
            )

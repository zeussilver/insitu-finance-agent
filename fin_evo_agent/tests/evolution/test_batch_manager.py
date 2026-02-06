"""Tests for BatchEvolutionManager.

Uses mock synthesizer/gateway/deduplicator — no LLM calls.
"""

import time
from dataclasses import dataclass
from typing import Optional, Tuple
from unittest.mock import MagicMock, patch

import pytest

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
from src.evolution.batch_manager import (
    BatchEvolutionManager,
    BatchEvolutionReport,
    EvolutionResult,
)
from src.core.models import ToolStatus


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

@dataclass
class MockTool:
    id: int
    name: str
    contract_id: Optional[str] = None
    status: ToolStatus = ToolStatus.PROVISIONAL
    verification_stage: int = 4
    semantic_version: str = "0.1.0"


class MockSynthesizer:
    """Deterministic synthesizer that sleeps to simulate LLM latency."""

    def __init__(self, fail_queries=None, delay: float = 0.05):
        self.fail_queries = fail_queries or set()
        self.call_count = 0
        self.delay = delay

    def synthesize_with_refine(self, query, category=None, contract=None):
        self.call_count += 1
        time.sleep(self.delay)
        if query in self.fail_queries:
            return None, MagicMock()
        tool = MockTool(
            id=self.call_count,
            name=f"tool_{self.call_count}",
            contract_id=contract.contract_id if contract else "test_contract",
        )
        return tool, MagicMock()


class MockDeduplicator:
    def __init__(self, action: str = "no_action"):
        self.action = action
        self.calls = []

    def check_and_resolve(self, tool_id, contract_id):
        self.calls.append((tool_id, contract_id))
        return self.action


class MockRegistry:
    def __init__(self, existing_tools=None):
        self._tools = existing_tools or {}

    def find_by_contract_id(self, contract_id):
        return self._tools.get(contract_id, [])

    def find_by_schema(self, **kwargs):
        return None


def _make_tasks(n: int, category: str = "calculation") -> list:
    return [
        {
            "task_id": f"task_{i:03d}",
            "query": f"Query {i}",
            "category": category,
            "contract_id": f"contract_{i:03d}",
        }
        for i in range(1, n + 1)
    ]


def _build_manager(
    synthesizer=None,
    deduplicator=None,
    registry=None,
    max_workers=3,
) -> BatchEvolutionManager:
    synth = synthesizer or MockSynthesizer()
    gateway = MagicMock()
    dedup = deduplicator or MockDeduplicator()
    reg = registry or MockRegistry()
    return BatchEvolutionManager(
        synthesizer=synth,
        gateway=gateway,
        deduplicator=dedup,
        registry=reg,
        metrics_collector=None,
        max_workers=max_workers,
    )


# ---------------------------------------------------------------------------
# TestEvolveBatch
# ---------------------------------------------------------------------------

class TestEvolveBatch:

    @patch("src.evolution.batch_manager.infer_contract_from_query", return_value=MagicMock(contract_id="c"))
    def test_report_counts_are_accurate(self, mock_infer):
        tasks = _make_tasks(5)
        mgr = _build_manager()
        report = mgr.evolve_batch(tasks)
        assert report.total_tasks == 5
        assert report.synthesis_success == 5
        assert report.registration_success == 5
        assert report.reused_count == 0
        assert len(report.results) == 5

    @patch("src.evolution.batch_manager.infer_contract_from_query", return_value=MagicMock(contract_id="c"))
    def test_handles_synthesis_failure(self, mock_infer):
        synth = MockSynthesizer(fail_queries={"Query 2", "Query 4"})
        mgr = _build_manager(synthesizer=synth)
        tasks = _make_tasks(5)
        report = mgr.evolve_batch(tasks)
        assert report.synthesis_success == 3
        assert report.total_tasks == 5
        failed = [r for r in report.results if not r.success]
        assert len(failed) == 2

    @patch("src.evolution.batch_manager.infer_contract_from_query", return_value=MagicMock(contract_id="c"))
    def test_parallel_faster_than_sequential(self, mock_infer):
        """3 tasks with 0.1s delay each should complete in < 0.25s with 3 workers."""
        synth = MockSynthesizer(delay=0.1)
        mgr = _build_manager(synthesizer=synth, max_workers=3)
        tasks = _make_tasks(3)
        start = time.time()
        report = mgr.evolve_batch(tasks)
        elapsed = time.time() - start
        # Sequential would be >= 0.3s. Parallel should be ~0.1s + overhead
        assert elapsed < 0.25, f"Expected < 0.25s, got {elapsed:.3f}s"
        assert report.synthesis_success == 3

    @patch("src.evolution.batch_manager.infer_contract_from_query", return_value=MagicMock(contract_id="c"))
    def test_deduplication_called_for_successful_tools(self, mock_infer):
        dedup = MockDeduplicator(action="no_action")
        mgr = _build_manager(deduplicator=dedup)
        tasks = _make_tasks(3)
        mgr.evolve_batch(tasks)
        # dedup should be called once per successful tool with tool_id and contract_id
        assert len(dedup.calls) == 3

    @patch("src.evolution.batch_manager.infer_contract_from_query", return_value=MagicMock(contract_id="c"))
    def test_dedup_superseded_increments_count(self, mock_infer):
        dedup = MockDeduplicator(action="superseded")
        mgr = _build_manager(deduplicator=dedup)
        tasks = _make_tasks(2)
        report = mgr.evolve_batch(tasks)
        assert report.dedup_merged == 2

    def test_warm_start_reuses_existing_tool(self):
        existing = MockTool(id=99, name="existing_calc", contract_id="contract_001", status=ToolStatus.PROVISIONAL)
        registry = MockRegistry(existing_tools={"contract_001": [existing]})
        synth = MockSynthesizer()
        mgr = _build_manager(synthesizer=synth, registry=registry)
        tasks = _make_tasks(1)  # task_001 with contract_001
        report = mgr.evolve_batch(tasks)
        assert report.reused_count == 1
        assert report.synthesis_success == 1
        assert report.registration_success == 1
        assert report.results[0].reused is True
        assert report.results[0].tool_name == "existing_calc"
        # Synthesizer should NOT have been called
        assert synth.call_count == 0

    def test_warm_start_filters_deprecated(self):
        """Deprecated tools should not be reused."""
        existing = MockTool(id=99, name="old_tool", contract_id="contract_001", status=ToolStatus.DEPRECATED)
        registry = MockRegistry(existing_tools={"contract_001": [existing]})
        synth = MockSynthesizer()
        mgr = _build_manager(synthesizer=synth, registry=registry)
        tasks = _make_tasks(1)
        with patch("src.evolution.batch_manager.infer_contract_from_query", return_value=MagicMock(contract_id="c")):
            report = mgr.evolve_batch(tasks)
        # Should NOT reuse the deprecated tool — should synthesize
        assert report.reused_count == 0
        assert synth.call_count == 1

    @patch("src.evolution.batch_manager.infer_contract_from_query", return_value=MagicMock(contract_id="c"))
    def test_synthesis_exception_handled(self, mock_infer):
        """If synthesize_with_refine raises, the task should still appear in results."""
        synth = MagicMock()
        synth.synthesize_with_refine.side_effect = RuntimeError("LLM down")
        mgr = _build_manager(synthesizer=synth)
        tasks = _make_tasks(1)
        report = mgr.evolve_batch(tasks)
        assert report.total_tasks == 1
        assert report.synthesis_success == 0
        assert len(report.results) == 1
        assert "LLM down" in report.results[0].error


# ---------------------------------------------------------------------------
# TestEvolveMultiRound
# ---------------------------------------------------------------------------

class TestEvolveMultiRound:

    @patch("src.evolution.batch_manager.infer_contract_from_query", return_value=MagicMock(contract_id="c"))
    def test_returns_correct_number_of_reports(self, mock_infer):
        mgr = _build_manager()
        tasks = _make_tasks(2)
        reports = mgr.evolve_multi_round(tasks, num_rounds=3)
        assert len(reports) == 3
        for i, report in enumerate(reports, 1):
            assert report.round_number == i


# ---------------------------------------------------------------------------
# TestEvolutionResult & BatchEvolutionReport
# ---------------------------------------------------------------------------

class TestDataclasses:

    def test_synthesis_rate(self):
        report = BatchEvolutionReport(
            batch_id="test",
            round_number=1,
            total_tasks=10,
            synthesis_success=8,
        )
        assert report.synthesis_rate == 0.8

    def test_reuse_rate(self):
        report = BatchEvolutionReport(
            batch_id="test",
            round_number=1,
            total_tasks=10,
            reused_count=6,
        )
        assert report.reuse_rate == 0.6

    def test_zero_tasks_rates(self):
        report = BatchEvolutionReport(
            batch_id="test",
            round_number=1,
            total_tasks=0,
        )
        assert report.synthesis_rate == 0.0
        assert report.registration_rate == 0.0
        assert report.reuse_rate == 0.0

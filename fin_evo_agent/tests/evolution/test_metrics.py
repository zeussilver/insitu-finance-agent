"""Tests for EvolutionMetrics — JSONL persistence, summary table, CSV export."""

import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import pytest

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
from src.evolution.metrics import EvolutionMetrics, RoundMetrics


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@dataclass
class MockResult:
    task_id: str = "t1"
    synthesis_time_sec: float = 5.0
    reused: bool = False
    success: bool = True


@dataclass
class MockReport:
    """Mimics BatchEvolutionReport shape."""
    batch_id: str = "batch_1"
    round_number: int = 1
    total_tasks: int = 10
    synthesis_success: int = 8
    registration_success: int = 8
    reused_count: int = 2
    dedup_merged: int = 1
    total_time_sec: float = 60.0
    results: list = field(default_factory=lambda: [
        MockResult(task_id="t1", synthesis_time_sec=5.0, reused=False),
        MockResult(task_id="t2", synthesis_time_sec=3.0, reused=False),
        MockResult(task_id="t3", synthesis_time_sec=0.0, reused=True),
    ])


@pytest.fixture
def tmp_log_dir(tmp_path):
    return tmp_path / "logs"


@pytest.fixture
def metrics(tmp_log_dir):
    return EvolutionMetrics(log_dir=tmp_log_dir)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRecordBatch:

    def test_creates_metrics_file(self, metrics, tmp_log_dir):
        report = MockReport()
        metrics.record_batch(report)
        assert (tmp_log_dir / "evolution_metrics.jsonl").exists()

    def test_persists_one_line_per_batch(self, metrics, tmp_log_dir):
        metrics.record_batch(MockReport(round_number=1))
        metrics.record_batch(MockReport(round_number=2, batch_id="batch_2"))
        lines = (tmp_log_dir / "evolution_metrics.jsonl").read_text().strip().split("\n")
        assert len(lines) == 2

    def test_avg_synthesis_time_excludes_reused(self, metrics):
        report = MockReport()
        rm = metrics.record_batch(report)
        # Only non-reused: 5.0 and 3.0 -> avg = 4.0
        assert rm.avg_synthesis_time_sec == 4.0

    def test_round_metrics_fields(self, metrics):
        report = MockReport()
        rm = metrics.record_batch(report)
        assert rm.round_number == 1
        assert rm.total_tasks == 10
        assert rm.synthesis_success == 8
        assert rm.reused_from_registry == 2
        assert rm.dedup_merged == 1

    def test_in_memory_rounds_updated(self, metrics):
        metrics.record_batch(MockReport(round_number=1))
        metrics.record_batch(MockReport(round_number=2, batch_id="b2"))
        assert len(metrics.rounds) == 2


class TestGetAllRounds:

    def test_loads_from_disk(self, metrics, tmp_log_dir):
        metrics.record_batch(MockReport(round_number=1))
        metrics.record_batch(MockReport(round_number=2, batch_id="b2"))
        # Create a fresh instance to read from disk
        fresh = EvolutionMetrics(log_dir=tmp_log_dir)
        rounds = fresh.get_all_rounds()
        assert len(rounds) == 2
        assert rounds[0].round_number == 1
        assert rounds[1].round_number == 2

    def test_empty_file_returns_empty(self, metrics):
        assert metrics.get_all_rounds() == []


class TestRoundMetrics:

    def test_synthesis_rate(self):
        rm = RoundMetrics(
            round_number=1, batch_id="b", timestamp="",
            total_tasks=10, synthesis_success=8, registration_success=8,
            reused_from_registry=0, dedup_merged=0,
            total_time_sec=0, avg_synthesis_time_sec=0,
            failures_by_stage={}, total_tools_in_registry=0,
            active_tools=0, deprecated_tools=0,
        )
        assert rm.synthesis_rate == 0.8

    def test_reuse_rate(self):
        rm = RoundMetrics(
            round_number=1, batch_id="b", timestamp="",
            total_tasks=10, synthesis_success=8, registration_success=8,
            reused_from_registry=6, dedup_merged=0,
            total_time_sec=0, avg_synthesis_time_sec=0,
            failures_by_stage={}, total_tools_in_registry=0,
            active_tools=0, deprecated_tools=0,
        )
        assert rm.reuse_rate == 0.6

    def test_evolution_efficiency(self):
        rm = RoundMetrics(
            round_number=1, batch_id="b", timestamp="",
            total_tasks=10, synthesis_success=8, registration_success=8,
            reused_from_registry=0, dedup_merged=0,
            total_time_sec=0, avg_synthesis_time_sec=0,
            failures_by_stage={}, total_tools_in_registry=20,
            active_tools=15, deprecated_tools=5,
        )
        assert rm.evolution_efficiency == 0.75

    def test_zero_division_safe(self):
        rm = RoundMetrics(
            round_number=1, batch_id="b", timestamp="",
            total_tasks=0, synthesis_success=0, registration_success=0,
            reused_from_registry=0, dedup_merged=0,
            total_time_sec=0, avg_synthesis_time_sec=0,
            failures_by_stage={}, total_tools_in_registry=0,
            active_tools=0, deprecated_tools=0,
        )
        assert rm.synthesis_rate == 0.0
        assert rm.reuse_rate == 0.0
        assert rm.evolution_efficiency == 1.0


class TestSummaryTable:

    def test_generates_markdown(self, metrics):
        metrics.record_batch(MockReport(round_number=1))
        metrics.record_batch(MockReport(round_number=2, batch_id="b2"))
        table = metrics.generate_summary_table()
        assert "| Round |" in table
        assert "| 1 " in table
        assert "| 2 " in table

    def test_empty_message(self, metrics):
        assert "No evolution rounds" in metrics.generate_summary_table()


class TestExportCSV:

    def test_creates_csv(self, metrics, tmp_log_dir):
        metrics.record_batch(MockReport(round_number=1))
        csv_path = tmp_log_dir / "export.csv"
        metrics.export_for_plotting(csv_path)
        content = csv_path.read_text()
        assert "round,synthesis_rate,reuse_rate" in content
        lines = content.strip().split("\n")
        assert len(lines) == 2  # header + 1 data row

    def test_empty_no_file(self, metrics, tmp_log_dir):
        csv_path = tmp_log_dir / "export.csv"
        metrics.export_for_plotting(csv_path)
        assert not csv_path.exists()

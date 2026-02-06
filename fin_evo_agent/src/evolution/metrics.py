"""EvolutionMetrics: Collect and persist evolution metrics across rounds.

Storage: JSONL file at data/logs/evolution_metrics.jsonl
Each line is one RoundMetrics serialized as JSON.

Usage in paper:
- Table: Round-by-round synthesis rate, reuse rate, efficiency
- Figure: Line chart of reuse_rate across rounds (shows self-evolution)
"""

import csv
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])


@dataclass
class RoundMetrics:
    """Metrics for a single evolution round."""
    round_number: int
    batch_id: str
    timestamp: str

    # Synthesis metrics
    total_tasks: int
    synthesis_success: int
    registration_success: int
    reused_from_registry: int
    dedup_merged: int

    # Time metrics
    total_time_sec: float
    avg_synthesis_time_sec: float

    # Failure distribution
    failures_by_stage: Dict[str, int]

    # Tool library state AFTER this round
    total_tools_in_registry: int
    active_tools: int
    deprecated_tools: int

    @property
    def synthesis_rate(self) -> float:
        return self.synthesis_success / self.total_tasks if self.total_tasks > 0 else 0.0

    @property
    def reuse_rate(self) -> float:
        return self.reused_from_registry / self.total_tasks if self.total_tasks > 0 else 0.0

    @property
    def evolution_efficiency(self) -> float:
        """Active tools / total ever created. Higher = less waste."""
        total = self.active_tools + self.deprecated_tools
        return self.active_tools / total if total > 0 else 1.0


class EvolutionMetrics:
    """Collect and persist evolution metrics across rounds."""

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or Path("data/logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.log_dir / "evolution_metrics.jsonl"
        self.rounds: List[RoundMetrics] = []
        self.logger = logging.getLogger("EvolutionMetrics")

    def record_batch(self, report, registry=None) -> RoundMetrics:
        """Convert a BatchEvolutionReport into RoundMetrics and persist.

        Args:
            report: BatchEvolutionReport from batch_manager
            registry: ToolRegistry for counting library state (optional)
        """
        # Compute average synthesis time
        synth_times = [r.synthesis_time_sec for r in report.results if not r.reused]
        avg_time = sum(synth_times) / len(synth_times) if synth_times else 0.0

        # Count tool library state
        total_tools = 0
        active = 0
        deprecated = 0
        if registry:
            try:
                all_tools = registry.list_all()
                total_tools = len(all_tools)
                for t in all_tools:
                    if t.status.value == "deprecated":
                        deprecated += 1
                    elif t.status.value != "failed":
                        active += 1
            except Exception:
                pass

        metrics = RoundMetrics(
            round_number=report.round_number,
            batch_id=report.batch_id,
            timestamp=datetime.now().isoformat(),
            total_tasks=report.total_tasks,
            synthesis_success=report.synthesis_success,
            registration_success=report.registration_success,
            reused_from_registry=report.reused_count,
            dedup_merged=report.dedup_merged,
            total_time_sec=report.total_time_sec,
            avg_synthesis_time_sec=round(avg_time, 2),
            failures_by_stage={},  # TODO: populate from verification results
            total_tools_in_registry=total_tools,
            active_tools=active,
            deprecated_tools=deprecated,
        )

        self.rounds.append(metrics)
        self._persist(metrics)
        return metrics

    def _persist(self, metrics: RoundMetrics) -> None:
        """Append one JSON line to the metrics file."""
        with open(self.metrics_file, "a") as f:
            f.write(json.dumps(asdict(metrics)) + "\n")

    def get_all_rounds(self) -> List[RoundMetrics]:
        """Load all recorded rounds from disk."""
        if not self.metrics_file.exists():
            return []
        rounds = []
        with open(self.metrics_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    rounds.append(RoundMetrics(**data))
        return rounds

    def generate_summary_table(self) -> str:
        """Generate a markdown table summarizing all rounds."""
        rounds = self.get_all_rounds()
        if not rounds:
            return "No evolution rounds recorded."

        lines = [
            "| Round | Synthesis Rate | Reuse Rate | Active Tools | Dedup | Time (s) |",
            "|------:|---------------:|-----------:|-------------:|------:|---------:|",
        ]
        for r in rounds:
            lines.append(
                f"| {r.round_number} "
                f"| {r.synthesis_rate:.0%} "
                f"| {r.reuse_rate:.0%} "
                f"| {r.active_tools} "
                f"| {r.dedup_merged} "
                f"| {r.total_time_sec:.1f} |"
            )
        return "\n".join(lines)

    def export_for_plotting(self, output_path: Path) -> None:
        """Export metrics as CSV for matplotlib/plotly visualization."""
        rounds = self.get_all_rounds()
        if not rounds:
            return

        fieldnames = [
            "round", "synthesis_rate", "reuse_rate",
            "active_tools", "dedup_merged", "time_sec",
        ]
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rounds:
                writer.writerow({
                    "round": r.round_number,
                    "synthesis_rate": f"{r.synthesis_rate:.4f}",
                    "reuse_rate": f"{r.reuse_rate:.4f}",
                    "active_tools": r.active_tools,
                    "dedup_merged": r.dedup_merged,
                    "time_sec": f"{r.total_time_sec:.1f}",
                })

"""SQLModel data models for the Yunjue Agent system.

Architecture: "Metadata in DB, Payload on Disk"
- ToolArtifact: Tool code metadata (actual code stored as .py files)
- ExecutionTrace: Execution history for debugging and refinement
- ErrorReport: LLM-analyzed error reports
- ToolPatch: Repair records linking errors to fixes
- BatchMergeRecord: Tool consolidation records (stub for Phase 1b)
"""

from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Column, create_engine
from sqlalchemy import JSON, Text

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
from src.config import DB_URL


# --- Enumerations ---

class ToolStatus(str, Enum):
    """Tool lifecycle status."""
    PROVISIONAL = "provisional"  # Generated, passed self-tests only
    VERIFIED = "verified"        # Passed batch merge verification
    DEPRECATED = "deprecated"    # Superseded by a more general tool
    FAILED = "failed"            # Repair failed or security risk


class Permission(str, Enum):
    """Tool execution permissions."""
    CALC_ONLY = "calc_only"       # Pure computation (pandas/numpy)
    NETWORK_READ = "network_read"  # Allow yfinance/Requests GET
    FILE_WRITE = "file_write"      # Allow cache writes (restricted)


# --- Table 1: ToolArtifact ---

class ToolArtifact(SQLModel, table=True):
    """Tool metadata table. Code files stored on disk."""
    __tablename__ = "tool_artifacts"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    semantic_version: str = Field(default="0.1.0")

    # Physical storage pointer
    file_path: str = Field(description="Relative path under artifacts/")
    content_hash: str = Field(index=True, unique=True)

    # Metadata (redundant storage for convenience)
    code_content: str = Field(sa_column=Column(Text))
    args_schema: Dict = Field(default={}, sa_column=Column(JSON))
    dependencies: List[int] = Field(default=[], sa_column=Column(JSON))
    permissions: List[str] = Field(default=[Permission.CALC_ONLY.value], sa_column=Column(JSON))
    status: ToolStatus = Field(default=ToolStatus.PROVISIONAL, index=True)
    parent_tool_ids: List[int] = Field(default=[], sa_column=Column(JSON))
    test_cases: List[Dict] = Field(default=[], sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Table 2: ExecutionTrace ---

class ExecutionTrace(SQLModel, table=True):
    """Execution history for debugging and refinement."""
    __tablename__ = "execution_traces"

    trace_id: str = Field(primary_key=True)
    task_id: str = Field(index=True)
    tool_id: Optional[int] = Field(default=None, foreign_key="tool_artifacts.id")

    # Input/Output snapshots
    input_args: Dict = Field(default={}, sa_column=Column(JSON))
    output_repr: str = Field(default="", sa_column=Column(Text))

    # Execution context
    exit_code: int = Field(default=0)
    std_out: Optional[str] = Field(default=None, sa_column=Column(Text))
    std_err: Optional[str] = Field(default=None, sa_column=Column(Text))
    execution_time_ms: int = Field(default=0)

    # LLM and environment info
    llm_config: Dict = Field(default={}, sa_column=Column(JSON))
    env_snapshot: Dict = Field(default={}, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Table 3: ErrorReport ---

class ErrorReport(SQLModel, table=True):
    """LLM-analyzed error reports."""
    __tablename__ = "error_reports"

    id: Optional[int] = Field(default=None, primary_key=True)
    trace_id: str = Field(foreign_key="execution_traces.trace_id", index=True)
    error_type: str = Field(description="Full exception type name")
    root_cause: str = Field(sa_column=Column(Text), description="LLM analysis")

    occurred_at: datetime = Field(default_factory=datetime.utcnow)


# --- Table 4: ToolPatch ---

class ToolPatch(SQLModel, table=True):
    """Repair records linking errors to fixes."""
    __tablename__ = "tool_patches"

    id: Optional[int] = Field(default=None, primary_key=True)
    error_report_id: int = Field(foreign_key="error_reports.id")
    base_tool_id: int = Field(foreign_key="tool_artifacts.id")

    patch_diff: str = Field(sa_column=Column(Text), description="Git diff or description")
    rationale: str = Field(sa_column=Column(Text), description="Thinking chain summary")
    resulting_tool_id: Optional[int] = Field(default=None, foreign_key="tool_artifacts.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Table 5: BatchMergeRecord ---

class BatchMergeRecord(SQLModel, table=True):
    """Tool consolidation records (stub for Phase 1b)."""
    __tablename__ = "batch_merge_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    source_tool_ids: List[int] = Field(default=[], sa_column=Column(JSON))
    canonical_tool_id: Optional[int] = Field(default=None, foreign_key="tool_artifacts.id")
    strategy: str = Field(default="generalization")
    regression_stats: Dict = Field(default={}, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Database Initialization ---

def init_db():
    """Create all tables in the database."""
    engine = create_engine(DB_URL)
    SQLModel.metadata.create_all(engine)
    return engine


def get_engine():
    """Get database engine."""
    return create_engine(DB_URL)


if __name__ == "__main__":
    # Run to initialize database
    init_db()
    print("[System] Database initialized successfully.")

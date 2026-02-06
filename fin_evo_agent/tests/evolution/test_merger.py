"""Tests for SimpleDeduplicator (merger.py)."""

import sys
sys.path.insert(0, str(__file__).rsplit("/", 4)[0])

import pytest
from unittest.mock import MagicMock, patch
from src.core.models import ToolArtifact, ToolStatus, BatchMergeRecord
from src.evolution.merger import SimpleDeduplicator


def _make_tool(
    id: int,
    name: str = "test_tool",
    version: str = "0.1.0",
    verification_stage: int = 3,
    status: ToolStatus = ToolStatus.PROVISIONAL,
    contract_id: str = "calc_rsi",
) -> ToolArtifact:
    """Create a mock ToolArtifact for testing."""
    tool = MagicMock(spec=ToolArtifact)
    tool.id = id
    tool.name = name
    tool.semantic_version = version
    tool.verification_stage = verification_stage
    tool.status = status
    tool.contract_id = contract_id
    tool.code_content = "def test(): pass"
    return tool


class TestScoreTool:
    def setup_method(self):
        self.registry = MagicMock()
        self.dedup = SimpleDeduplicator(self.registry)

    def test_higher_verification_stage_wins(self):
        tool_high = _make_tool(1, verification_stage=4)
        tool_low = _make_tool(2, verification_stage=2)
        assert self.dedup.score_tool(tool_high) > self.dedup.score_tool(tool_low)

    def test_higher_success_rate_wins_on_same_stage(self):
        tool_prov = _make_tool(1, verification_stage=3, status=ToolStatus.PROVISIONAL)
        tool_dep = _make_tool(2, verification_stage=3, status=ToolStatus.DEPRECATED)
        assert self.dedup.score_tool(tool_prov) > self.dedup.score_tool(tool_dep)

    def test_newer_version_breaks_tie(self):
        tool_new = _make_tool(1, version="0.2.0", verification_stage=3)
        tool_old = _make_tool(2, version="0.1.0", verification_stage=3)
        assert self.dedup.score_tool(tool_new) > self.dedup.score_tool(tool_old)

    def test_none_verification_stage_treated_as_zero(self):
        tool = _make_tool(1, verification_stage=None)
        # Should not raise; stage defaults to 0
        score = self.dedup.score_tool(tool)
        assert score[0] == 0


class TestCheckAndResolve:
    def setup_method(self):
        self.registry = MagicMock()
        self.dedup = SimpleDeduplicator(self.registry)

    def test_single_tool_returns_no_action(self):
        tool = _make_tool(1)
        self.registry.find_by_contract_id.return_value = [tool]
        assert self.dedup.check_and_resolve(1, "calc_rsi") == "no_action"

    @patch("src.evolution.merger.get_engine")
    def test_new_tool_is_best_returns_kept(self, mock_engine):
        # New tool has higher verification stage
        new_tool = _make_tool(2, name="calc_rsi_v2", verification_stage=4)
        old_tool = _make_tool(1, name="calc_rsi_v1", verification_stage=2)
        self.registry.find_by_contract_id.return_value = [old_tool, new_tool]

        # Mock the session for _deprecate_tool and create_merge_record
        mock_session = MagicMock()
        mock_engine.return_value.connect.return_value.__enter__ = MagicMock()
        mock_session.get.return_value = old_tool
        mock_engine.return_value.__enter__ = MagicMock(return_value=mock_session)

        with patch("src.evolution.merger.Session") as MockSession:
            mock_ctx = MagicMock()
            MockSession.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            MockSession.return_value.__exit__ = MagicMock(return_value=False)
            mock_ctx.get.return_value = old_tool

            result = self.dedup.check_and_resolve(2, "calc_rsi")
            assert result == "kept"

    @patch("src.evolution.merger.get_engine")
    def test_new_tool_is_worse_returns_superseded(self, mock_engine):
        new_tool = _make_tool(2, name="calc_rsi_v2", verification_stage=1)
        old_tool = _make_tool(1, name="calc_rsi_v1", verification_stage=4)
        self.registry.find_by_contract_id.return_value = [old_tool, new_tool]

        with patch("src.evolution.merger.Session") as MockSession:
            mock_ctx = MagicMock()
            MockSession.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            MockSession.return_value.__exit__ = MagicMock(return_value=False)
            mock_ctx.get.return_value = new_tool

            result = self.dedup.check_and_resolve(2, "calc_rsi")
            assert result == "superseded"

    def test_deprecated_tools_not_counted(self):
        active = _make_tool(1, verification_stage=3)
        deprecated = _make_tool(2, verification_stage=4, status=ToolStatus.DEPRECATED)
        self.registry.find_by_contract_id.return_value = [active, deprecated]
        # Only 1 active tool → no_action
        assert self.dedup.check_and_resolve(1, "calc_rsi") == "no_action"

    def test_empty_candidates_returns_no_action(self):
        self.registry.find_by_contract_id.return_value = []
        assert self.dedup.check_and_resolve(1, "calc_rsi") == "no_action"

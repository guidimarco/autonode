"""Tests for the CLI entry point argument parsing."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

TESTDATA = Path(__file__).resolve().parent / "testdata"


def test_workflow_cli_passes_args_to_run_workflow(tmp_path: Path) -> None:
    """Verifica che i flag CLI vengano passati correttamente a run_workflow."""
    wf = TESTDATA / "workflow.yaml"
    ag = TESTDATA / "agents.yaml"
    prompt = "Fix the bug"

    captured: dict[str, object] = {}

    def fake_run_workflow(raw: dict[str, object]) -> MagicMock:
        captured.update(raw)
        raise SystemExit(0)

    args = [
        "--workflow",
        str(wf),
        "--agents",
        str(ag),
        "--prompt",
        prompt,
        "--repo",
        ".",
    ]

    patch_target = "autonode.presentation.workflow.handlers.run_workflow"
    with patch(patch_target, side_effect=fake_run_workflow):
        with pytest.raises(SystemExit):
            from autonode.presentation.cli import _run_workflow_cli

            _run_workflow_cli(args)

    assert captured.get("workflow") == str(wf)
    assert captured.get("agents") == str(ag)
    assert captured.get("prompt") == prompt


def test_main_routes_cleanup_to_cleanup_cli() -> None:
    """Verifica che `main()` chiami il ramo cleanup quando il primo arg è 'cleanup'."""
    with patch("autonode.presentation.cli._run_cleanup_cli") as mock_cleanup:
        with patch.object(sys, "argv", ["autonode", "cleanup"]):
            from autonode.presentation.cli import main

            main()
    mock_cleanup.assert_called_once()


def test_main_routes_mcp_to_mcp_cli() -> None:
    """Verifica che `main()` chiami il ramo MCP quando il primo arg è 'mcp'."""
    with patch("autonode.presentation.cli._run_mcp_cli") as mock_mcp:
        with patch.object(sys, "argv", ["autonode", "mcp"]):
            from autonode.presentation.cli import main

            main()
    mock_mcp.assert_called_once_with([])


def test_main_routes_workflow_with_full_argv() -> None:
    """Verifica che `main()` passi sys.argv[1:] (non [2:]) al workflow handler."""
    captured_args: list[list[str]] = []

    def fake_workflow_cli(args: list[str]) -> None:
        captured_args.append(args)

    with patch("autonode.presentation.cli._run_workflow_cli", side_effect=fake_workflow_cli):
        with patch.object(sys, "argv", ["autonode", "--prompt", "hello"]):
            from autonode.presentation.cli import main

            main()

    assert captured_args == [["--prompt", "hello"]]

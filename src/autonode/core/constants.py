"""
Centralized defaults: config paths relative to repo root, checkpoint DB, token budget.

Infrastructure and presentation import these strings; the graph state uses token fields
for future kill-switch telemetry (0 budget = no limit until wired).
"""

from __future__ import annotations

# Paths relative to repository root (use Path(repo_root) / path).
DEFAULT_WORKFLOW_CONFIG_PATH: str = "config/workflow.yaml"
DEFAULT_AGENTS_CONFIG_PATH: str = "config/agents.yaml"

# SQLite checkpointer default (override with AUTONODE_DB_PATH).
DEFAULT_CHECKPOINT_DB_PATH: str = "/app/.autonode/db/autonode.db"

# Global session token cap: 0 = not enforced until telemetry applies a positive budget.
DEFAULT_TOKEN_BUDGET: int = 0

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from autonode.core.sandbox import session_paths
from autonode.infrastructure.paths.repo_resolution import ensure_git_repo_under_root
from autonode.infrastructure.persistence.session_status_store import write_session_status

load_dotenv()

_REPO_ROOT = Path(__file__).resolve().parents[3]

log = logging.getLogger(__name__)

app = FastAPI()


class ExecuteRequest(BaseModel):
    prompt: str = Field(min_length=5)
    repo_path: str


def _ensure_session_directories(session_id: str) -> None:
    Path(session_paths.session_op_root(session_id)).mkdir(parents=True, exist_ok=True)
    Path(session_paths.session_outputs_path(session_id)).mkdir(parents=True, exist_ok=True)
    Path(session_paths.session_logs_dir(session_id)).mkdir(parents=True, exist_ok=True)


def _execute_workflow_background(container: Any, raw: dict[str, Any]) -> None:
    from autonode.presentation.workflow.handlers import run_workflow as run_autonode_workflow

    sid = str(raw["thread_id"])
    try:
        run_autonode_workflow(container.run_workflow_use_case, raw)
    except ValidationError as exc:
        log.exception("Validazione workflow fallita (background)")
        write_session_status(
            sid,
            {
                "status": "failed",
                "error": str(exc),
            },
        )


@app.post("/execute", status_code=202)
def execute(
    payload: ExecuteRequest,
    background_tasks: BackgroundTasks,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> JSONResponse:
    expected_api_key = os.environ.get("AUTONODE_API_KEY", "")
    if not expected_api_key or x_api_key != expected_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not hasattr(app.state, "container"):
        raise HTTPException(status_code=500, detail="Container not initialized")
    container = app.state.container

    try:
        repo_resolved = ensure_git_repo_under_root(payload.repo_path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    session_id = str(uuid.uuid4())
    _ensure_session_directories(session_id)
    write_session_status(
        session_id,
        {
            "status": "accepted",
            "repo_path": str(repo_resolved),
        },
    )

    raw: dict[str, Any] = {
        "prompt": payload.prompt,
        "repo_path": str(repo_resolved),
        "thread_id": session_id,
        "workflow_path": str(_REPO_ROOT / "config" / "workflow.yaml"),
        "agents_path": str(_REPO_ROOT / "config" / "agents.yaml"),
    }
    background_tasks.add_task(_execute_workflow_background, container, raw)

    return JSONResponse(status_code=202, content={"session_id": session_id})

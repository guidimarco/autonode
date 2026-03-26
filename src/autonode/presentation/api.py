from __future__ import annotations

import logging
import os
import uuid
from dotenv import load_dotenv
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, ValidationError

from autonode.presentation.workflow.handlers import run_workflow as run_autonode_workflow

load_dotenv()

_REPO_ROOT = Path(__file__).resolve().parents[3]

log = logging.getLogger(__name__)


class ExecuteRequest(BaseModel):
    prompt: str = Field(min_length=5)
    repo_path: str


app = FastAPI()


@app.post("/execute")
def execute(
    payload: ExecuteRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict[str, str]:
    expected_api_key = os.environ.get("AUTONODE_API_KEY", "")
    if not expected_api_key or x_api_key != expected_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not hasattr(app.state, "container"):
        raise HTTPException(status_code=500, detail="Container not initialized")
    container = app.state.container

    raw = {
        "prompt": payload.prompt,
        "repo_path": payload.repo_path,
        "thread_id": str(uuid.uuid4()),
        "workflow_path": str(_REPO_ROOT / "config" / "workflow.yaml"),
        "agents_path": str(_REPO_ROOT / "config" / "agents.yaml"),
    }
    try:
        result = run_autonode_workflow(container.run_workflow_use_case, raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        log.exception("Internal error while executing workflow")
        raise HTTPException(status_code=500, detail="Internal Server Error") from exc

    return {
        "session_id": result.session_id,
        "branch_name": result.branch_name,
        "verdict": result.verdict,
        "final_output": result.final_output,
    }

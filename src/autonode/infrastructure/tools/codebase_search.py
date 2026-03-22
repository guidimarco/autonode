"""
Codebase text search tool: bounded matches (50) under the sandbox root.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from langchain_core.tools import BaseTool, tool

from autonode.infrastructure.tools.ignore_rules import SKIP_DIR_NAMES, should_skip
from autonode.infrastructure.tools.path_guard import resolved_root

_MAX_RESULTS = 50
_MAX_QUERY_LEN = 500
_MAX_LINE_PREVIEW = 300
_MAX_FILE_BYTES = 512 * 1024


def _rg_glob_excludes() -> list[str]:
    out: list[str] = []
    for name in sorted(SKIP_DIR_NAMES):
        out.extend(["--glob", f"!**/{name}/**"])
    return out


def _search_with_ripgrep(root: Path, query: str) -> tuple[list[str], bool] | None:
    """
    Return (lines, truncated) using ripgrep, or None if rg is unavailable / failed.
    Reads at most _MAX_RESULTS + 1 lines from stdout to detect truncation
    without loading all output.
    """
    rg = shutil.which("rg")
    if not rg:
        return None

    cmd = [
        rg,
        "-n",
        "--no-heading",
        "--fixed-strings",
        "--max-columns",
        "500",
        *_rg_glob_excludes(),
        "--",
        query,
        str(root),
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except OSError:
        return None

    assert proc.stdout is not None
    lines_out: list[str] = []
    try:
        for _ in range(_MAX_RESULTS + 1):
            line = proc.stdout.readline()
            if not line:
                break
            lines_out.append(line.rstrip("\n"))
    finally:
        proc.stdout.close()
        if proc.poll() is None:
            proc.kill()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()

    rc = proc.returncode
    if rc is not None and rc not in (0, 1):
        return None

    truncated = len(lines_out) > _MAX_RESULTS
    return lines_out[:_MAX_RESULTS], truncated


def _search_with_python(root: Path, query: str) -> tuple[list[str], bool]:
    matches: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if should_skip(path):
            continue
        try:
            st = path.stat()
        except OSError:
            continue
        if st.st_size > _MAX_FILE_BYTES:
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b"\x00" in data[:4096]:
            continue
        text = data.decode("utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), 1):
            if query not in line:
                continue
            rel = path.relative_to(root)
            preview = line.strip()
            if len(preview) > _MAX_LINE_PREVIEW:
                preview = preview[:_MAX_LINE_PREVIEW] + "…"
            matches.append(f"{rel}:{lineno}:{preview}")
            if len(matches) > _MAX_RESULTS:
                return matches[:_MAX_RESULTS], True
    return matches, False


def make_search_codebase_tool(root_dir: str) -> BaseTool:
    """Factory: LangChain tool for bounded substring search under ``root_dir``."""

    root_abs = resolved_root(root_dir)

    @tool
    def search_codebase(query: str) -> str:
        """
        Cerca una stringa in tutti i file testuali sotto la root del task (limite 50 risultati).
        Restituisce path:relative, numero di riga e anteprima della riga.
        """
        q = (query or "").strip()
        if not q:
            return "ERRORE: query vuota."
        if len(q) > _MAX_QUERY_LEN:
            return f"ERRORE: query troppo lunga (max {_MAX_QUERY_LEN} caratteri)."

        rg_result = _search_with_ripgrep(root_abs, q)
        if rg_result is not None:
            lines, truncated = rg_result
        else:
            lines, truncated = _search_with_python(root_abs, q)

        if not lines:
            return (
                "Nessun risultato per la query indicata "
                "(entro la sandbox e le regole di esclusione)."
            )

        body = "\n".join(lines)
        if truncated:
            body += (
                f"\n\n_AVVISO: risultati limitati a {_MAX_RESULTS} occorrenze; "
                "raffina la query o restringi il percorso con altri tool._"
            )
        return body

    return search_codebase

"""
Codebase text search tool: bounded multi-query matches under the sandbox root.
"""

from __future__ import annotations

import shutil
import subprocess
from collections import OrderedDict
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


def _normalize_queries(queries: list[str]) -> list[str]:
    unique: OrderedDict[str, None] = OrderedDict()
    for raw in queries:
        q = (raw or "").strip()
        if not q:
            continue
        if len(q) > _MAX_QUERY_LEN:
            raise ValueError(f"query troppo lunga (max {_MAX_QUERY_LEN} caratteri): '{q[:60]}'")
        unique[q] = None
    return list(unique.keys())


def _search_with_ripgrep(root: Path, queries: list[str]) -> tuple[list[str], bool] | None:
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
    ]
    for q in queries:
        cmd.extend(["-e", q])
    cmd.extend(["--", str(root)])

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


def _search_with_python(root: Path, queries: list[str]) -> tuple[list[str], bool]:
    matches: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or should_skip(path):
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
        rel = path.relative_to(root)
        for lineno, line in enumerate(text.splitlines(), 1):
            if not any(q in line for q in queries):
                continue
            preview = line.strip()
            if len(preview) > _MAX_LINE_PREVIEW:
                preview = preview[:_MAX_LINE_PREVIEW] + "..."
            matches.append(f"{rel}:{lineno}:{preview}")
            if len(matches) > _MAX_RESULTS:
                return matches[:_MAX_RESULTS], True
    return matches, False


def _group_hits(lines: list[str], queries: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {q: [] for q in queries}
    seen: set[tuple[str, str]] = set()
    for line in lines:
        for q in queries:
            if q in line:
                key = (q, line)
                if key in seen:
                    continue
                grouped[q].append(line)
                seen.add(key)
    return grouped


def _render_grouped(grouped: dict[str, list[str]], truncated: bool) -> str:
    blocks: list[str] = []
    for q, hits in grouped.items():
        blocks.append(f"## query: {q}")
        if hits:
            blocks.extend(hits)
        else:
            blocks.append("(nessun risultato)")
        blocks.append("")
    body = "\n".join(blocks).rstrip()
    if truncated:
        body += (
            f"\n\n_AVVISO: risultati limitati a {_MAX_RESULTS} righe complessive; "
            "raffina le query o restringi il percorso con altri tool._"
        )
    return body


def make_search_codebase_tool(root_dir: str) -> BaseTool:
    """Factory: LangChain tool for bounded multi-query search under ``root_dir``."""

    root_abs = resolved_root(root_dir)

    @tool
    def search_codebase(queries: list[str]) -> str:
        """
        Cerca piu stringhe in tutti i file testuali sotto la root del task.
        Restituisce path relativo, numero di riga e anteprima, raggruppati per query.
        """
        try:
            normalized = _normalize_queries(queries or [])
        except ValueError as e:
            return f"ERRORE: {e}"

        if not normalized:
            return "ERRORE: queries vuote."

        rg_result = _search_with_ripgrep(root_abs, normalized)
        if rg_result is not None:
            lines, truncated = rg_result
        else:
            lines, truncated = _search_with_python(root_abs, normalized)

        if not lines:
            return (
                "Nessun risultato per le query indicate "
                "(entro la sandbox e le regole di esclusione)."
            )

        grouped = _group_hits(lines, normalized)
        return _render_grouped(grouped, truncated)

    return search_codebase

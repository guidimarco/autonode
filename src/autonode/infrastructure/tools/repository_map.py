"""
Repository map tool: Markdown tree with heuristic declaration lines (Python, PHP, JS/TS).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from langchain_core.tools import BaseTool, tool

from autonode.infrastructure.tools.ignore_rules import should_skip
from autonode.infrastructure.tools.path_guard import resolve_under_root, resolved_root

# Text-like extensions we scan for declaration hints (agnostic heuristics).
_SCAN_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".pyw",
        ".php",
        ".phtml",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".ts",
        ".tsx",
    },
)

_MAX_FILE_BYTES = 256 * 1024
_MAX_TREE_FILES = 2000

# Lines that look like top-level or member declarations in Python / PHP / JS-family.
_DECL_LINE = re.compile(
    r"""^\s*(?:
        (?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function|class|interface|type|enum)\s+
        |(?:declare\s+)?(?:namespace|module)\s+
        |(?:async\s+)?def\s+\w
        |class\s+\w
        |interface\s+\w
        |trait\s+\w
        |(?:public|private|protected|static|abstract|final)\s+(?:static\s+)?(?:function|class)\s+
        |function\s+\w
        |namespace\s+\w
    )""",
    re.VERBOSE | re.IGNORECASE,
)


def _declaration_lines_in_file(path: Path) -> list[str]:
    try:
        raw = path.read_bytes()
    except OSError:
        return []
    if len(raw) > _MAX_FILE_BYTES:
        return [f"(file troppo grande per analisi, >{_MAX_FILE_BYTES} bytes)"]
    text = raw.decode("utf-8", errors="replace")
    hits: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//", "/*", "*", "<!--")):
            continue
        if _DECL_LINE.match(line):
            snippet = stripped[:240]
            hits.append(f"`{snippet}`")
        if len(hits) >= 80:
            hits.append("… (ulteriori righe omesse in questo file)")
            break
    return hits


def _build_markdown_tree(
    root_dir: Path,
    target: Path,
    *,
    max_files: int,
) -> tuple[str, bool]:
    lines: list[str] = []
    files_seen = 0
    truncated = False

    if not target.exists():
        return f"ERRORE: path inesistente: {target}", False

    lines.append(f"# Repository map (root: `{root_dir}`)")
    lines.append("")
    lines.append(f"## Scope: `{target.relative_to(root_dir) if target != root_dir else '.'}`")
    lines.append("")

    if target.is_file():
        rel = target.relative_to(root_dir)
        if should_skip(target):
            lines.append(f"- `{rel}` _(skipped: blacklist)_")
            return "\n".join(lines), False
        files_seen += 1
        lines.append(f"### `{rel}`")
        if target.suffix.lower() in _SCAN_EXTENSIONS:
            decls = _declaration_lines_in_file(target)
            if decls:
                lines.extend(f"- {d}" for d in decls)
            else:
                lines.append("- _(nessuna keyword di dichiarazione rilevata)_")
        else:
            lines.append("- _(estensione non analizzata per keyword)_")
        return "\n".join(lines), False

    # Directory walk (top-down so we can prune blacklisted dirs)
    for dirpath, dirnames, filenames in os.walk(target, topdown=True):
        pdir = Path(dirpath)
        dirnames[:] = [d for d in sorted(dirnames) if not should_skip((pdir / d).resolve())]
        for name in sorted(filenames):
            fp = (pdir / name).resolve()
            if should_skip(fp):
                continue
            rel = fp.relative_to(root_dir)
            files_seen += 1
            if files_seen > max_files:
                truncated = True
                break
            lines.append(f"### `{rel}`")
            if fp.suffix.lower() in _SCAN_EXTENSIONS:
                decls = _declaration_lines_in_file(fp)
                if decls:
                    lines.extend(f"- {d}" for d in decls)
                else:
                    lines.append("- _(nessuna keyword di dichiarazione rilevata)_")
            else:
                lines.append("- _(file non analizzato per keyword)_")
            lines.append("")
        if truncated:
            break

    if truncated:
        lines.append(
            f"\n_(Mappa troncata: superato limite di {max_files} file. Restringi `target_path`.)_",
        )

    return "\n".join(lines), truncated


def make_get_repository_map_tool(root_dir: str) -> BaseTool:
    """
    Factory: LangChain tool that lists a scoped tree and declaration hints for
    Python / PHP / JS-family files.
    """

    root_abs = resolved_root(root_dir)

    @tool
    def get_repository_map(target_path: str = ".") -> str:
        """
        Restituisce una mappa Markdown della cartella (o file) indicata, sotto la root del task.
        Per file .py/.php/.js/.ts/… elenca righe che sembrano dichiarazioni
        (class, def, function, …).
        Usa target_path per restringere (es. "src/autonode") e ridurre i token.
        """
        try:
            target = resolve_under_root(root_dir, target_path)
        except ValueError as e:
            return f"ERRORE: {e}"

        text, _trunc = _build_markdown_tree(root_abs, target, max_files=_MAX_TREE_FILES)
        return text

    return get_repository_map

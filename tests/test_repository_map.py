"""Tests for get_repository_map tool."""

from __future__ import annotations

from pathlib import Path

from autonode.infrastructure.tools.repository_map import make_get_repository_map_tool


def test_get_repository_map_extracts_python_php_js_keywords(tmp_path: Path) -> None:
    root = tmp_path
    (root / "pkg").mkdir()
    (root / "pkg" / "mod.py").write_text(
        "class Foo:\n    def bar(self):\n        pass\n",
        encoding="utf-8",
    )
    (root / "pkg" / "api.php").write_text(
        "<?php\ninterface PaymentGateway {\n    public function charge();\n}\n",
        encoding="utf-8",
    )
    (root / "pkg" / "app.js").write_text(
        "export function run() {}\nexport class App {}\n",
        encoding="utf-8",
    )

    tool = make_get_repository_map_tool(str(root))
    out = tool.invoke({"target_path": "pkg"})

    assert "class Foo" in out or "`class Foo`" in out
    assert "def bar" in out or "def bar" in out.replace("`", "")
    assert "interface PaymentGateway" in out or "PaymentGateway" in out
    assert "export function run" in out or "function run" in out
    assert "class App" in out


def test_get_repository_map_skips_blacklisted_dirs(tmp_path: Path) -> None:
    root = tmp_path
    (root / "node_modules" / "x").mkdir(parents=True)
    (root / "node_modules" / "x" / "bad.js").write_text("export const BAD=1\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "ok.py").write_text("def ok():\n    pass\n", encoding="utf-8")

    tool = make_get_repository_map_tool(str(root))
    out = tool.invoke({"target_path": "."})
    assert "node_modules" not in out or "bad.js" not in out
    assert "ok.py" in out
    assert "def ok" in out or "`def ok" in out


def test_get_repository_map_rejects_traversal(tmp_path: Path) -> None:
    root = tmp_path
    root.mkdir(exist_ok=True)
    tool = make_get_repository_map_tool(str(root))
    out = tool.invoke({"target_path": ".."})
    assert "ERRORE" in out

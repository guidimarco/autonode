import subprocess
import sys


def _py_m(tool: str, *args: str) -> list[str]:
    """Invoke a dev CLI via the current interpreter (works when venv bin is not on PATH)."""
    return [sys.executable, "-m", tool, *args]


def _run_commands(commands: list[list[str]]) -> bool:
    failed = False

    for cmd in commands:
        print(f"\nRunning: {' '.join(cmd)}")
        result = subprocess.run(cmd)

        if result.returncode != 0:
            failed = True

    return failed


def lint() -> None:
    commands = [
        _py_m("ruff", "check", "."),
        _py_m("mypy", "."),
        _py_m("black", "--check", "."),
    ]

    failed = _run_commands(commands)

    if failed:
        print("\nLinting failed.")
        sys.exit(1)

    print("\nAll checks passed.")


def fix() -> None:
    commands = [
        _py_m("ruff", "check", ".", "--fix"),
        _py_m("black", "."),
    ]

    failed = _run_commands(commands)

    if failed:
        sys.exit(1)

    print("\nFix applied. Running lint to verify...\n")
    lint()

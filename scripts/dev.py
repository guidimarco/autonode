import subprocess
import sys


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
        ["ruff", "check", "."],
        ["mypy", "."],
        ["black", "--check", "."],
    ]

    failed = _run_commands(commands)

    if failed:
        print("\nLinting failed.")
        sys.exit(1)

    print("\nAll checks passed.")


def fix() -> None:
    commands = [
        ["ruff", "check", ".", "--fix"],
        ["black", "."],
    ]

    failed = _run_commands(commands)

    if failed:
        sys.exit(1)

    print("\nFix applied. Running lint to verify...\n")
    lint()

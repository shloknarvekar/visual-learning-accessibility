"""Run every check CI runs: contracts, formatting, API lint and tests, web lint and build.

Usage, from the repository root with the API virtualenv active:
    python scripts/verify.py
    python scripts/verify.py --skip-web-build
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_DIR = REPO_ROOT / "services" / "api"


def npm_command(*args: str) -> list[str]:
    executable = shutil.which("npm")
    if executable is None:
        sys.exit("npm was not found on PATH.")
    return [executable, *args]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-web-build", action="store_true", help="skip the Next.js build")
    args = parser.parse_args()

    python = sys.executable
    steps: list[tuple[str, list[str], Path]] = [
        ("Contracts: examples match schema", npm_command("run", "contracts:validate"), REPO_ROOT),
        ("Contracts: generated types current", npm_command("run", "contracts:check"), REPO_ROOT),
        ("Formatting: Prettier", npm_command("run", "format:check"), REPO_ROOT),
        ("API: ruff lint", [python, "-m", "ruff", "check", "."], API_DIR),
        ("API: ruff format", [python, "-m", "ruff", "format", "--check", "."], API_DIR),
        ("API: tests", [python, "-m", "pytest"], API_DIR),
        ("Web: lint", npm_command("run", "lint:web"), REPO_ROOT),
    ]
    if not args.skip_web_build:
        steps.append(("Web: build", npm_command("run", "build:web"), REPO_ROOT))

    failures = []
    for name, command, cwd in steps:
        print(f"\n==> {name}", flush=True)
        if subprocess.run(command, cwd=cwd, check=False).returncode != 0:
            failures.append(name)

    print()
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print(f"All {len(steps)} checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

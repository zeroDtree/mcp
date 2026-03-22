import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).parent))

from config_loader import load_server_config, run_server

config = load_server_config("code_lint")
mcp = FastMCP("CodeLint")

# Built-in linter definitions: name -> base command
_BUILTIN_LINTERS: Dict[str, List[str]] = {
    "pylint": ["pylint", "-E"],
    "ruff": ["ruff", "check"],
}


def _is_available(command: str) -> bool:
    return shutil.which(command) is not None


def _run_linter(name: str, command: List[str], filepath: str) -> Dict[str, Any]:
    if not _is_available(command[0]):
        return {
            "success": False,
            "issues": [],
            "message": f"Linter '{name}' not found. Install it with: pip install {name}",
        }
    try:
        result = subprocess.run(
            command + [filepath],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return {"success": True, "issues": [], "message": f"No issues found by {name}"}

        output = (result.stdout + result.stderr).strip()
        return {"success": False, "issues": output.splitlines(), "message": f"{name} found issues"}

    except Exception as e:
        return {"success": False, "issues": [], "message": f"Error running {name}: {e}"}


# Registry: name -> command list (supports custom linters added at runtime)
_linter_registry: Dict[str, List[str]] = dict(_BUILTIN_LINTERS)


def _lint_filepath(filepath: str, linters: Optional[List[str]] = None) -> Dict[str, Any]:
    if not os.path.exists(filepath):
        return {"success": False, "results": {}, "message": f"File not found: {filepath}"}

    targets = linters or list(_linter_registry.keys())
    results: Dict[str, Any] = {}

    for name in targets:
        command = _linter_registry.get(name)
        if command is None:
            results[name] = {"success": False, "issues": [], "message": f"Unknown linter: {name}"}
            continue
        results[name] = _run_linter(name, command, filepath)

    return {
        "success": all(r.get("success", False) for r in results.values()),
        "results": results,
        "message": f"Linting completed for {filepath}",
    }


# ---------------- MCP Tools ----------------


@mcp.tool()
def lint_python_file(filepath: str, linters: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Lint a Python file by its absolute path.

    Args:
        filepath: Absolute path to the Python file.
        linters: Optional list of linter names. Available: pylint, ruff.

    Returns:
        Linting results as a dictionary.
    """
    return _lint_filepath(filepath, linters)


@mcp.tool()
def lint_python_code(code: str, linters: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Lint Python source code provided as a string.

    Args:
        code: Python source code.
        linters: Optional list of linter names. Available: pylint, ruff.

    Returns:
        Linting results as a dictionary.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        temp_path = f.name
    try:
        return _lint_filepath(temp_path, linters)
    finally:
        os.unlink(temp_path)


@mcp.tool()
def list_available_linters() -> Dict[str, Any]:
    """
    List all registered linters and whether they are installed.

    Returns:
        A dict mapping linter name to its availability status.
    """
    return {name: {"available": _is_available(cmd[0]), "command": cmd} for name, cmd in _linter_registry.items()}


@mcp.tool()
def add_custom_linter(name: str, command: List[str]) -> Dict[str, Any]:
    """
    Register a custom linter.

    Args:
        name: Name of the linter.
        command: Command used to invoke the linter (e.g. ["mypy", "--strict"]).

    Returns:
        Success status and availability of the linter binary.
    """
    _linter_registry[name] = command
    available = _is_available(command[0])
    return {
        "success": True,
        "available": available,
        "message": f"Registered linter '{name}'"
        + ("" if available else f" (warning: '{command[0]}' not found in PATH)"),
    }


if __name__ == "__main__":
    run_server(mcp, config)

from fastmcp import FastMCP
import subprocess
import tempfile
import os
from typing import Dict, Any, List, Optional

mcp = FastMCP("CodeLint")


class ExternalLinter:
    """Generic CLI-based linter"""

    def __init__(self, name: str, command: List[str]):
        self.name = name
        self.command = command

    def run(self, filepath: str) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                self.command + [filepath],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "issues": [],
                    "message": f"No issues found by {self.name}",
                }

            output = (result.stdout + result.stderr).strip()
            return {
                "success": False,
                "issues": output.splitlines(),
                "message": f"{self.name} found issues",
            }

        except Exception as e:
            return {
                "success": False,
                "issues": [],
                "message": f"Error running {self.name}: {str(e)}",
            }


class CodeLintService:
    """Core lint service"""

    def __init__(self):
        self.linters: Dict[str, ExternalLinter] = {
            "pylint": ExternalLinter("pylint", ["pylint", "-E"]),
        }

    def lint_file(self, filepath: str, linters: Optional[List[str]] = None) -> Dict[str, Any]:
        if not os.path.exists(filepath):
            return {"success": False, "message": f"File not found: {filepath}"}

        linters = linters or list(self.linters.keys())
        results = {}

        for name in linters:
            linter = self.linters.get(name)
            if not linter:
                results[name] = {
                    "success": False,
                    "message": f"Unknown linter: {name}",
                }
                continue

            results[name] = linter.run(filepath)

        success = all(r.get("success", False) for r in results.values())

        return {
            "success": success,
            "results": results,
            "message": f"Linting completed for {filepath}",
        }

    def lint_code(self, code: str, linters: Optional[List[str]] = None) -> Dict[str, Any]:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            return self.lint_file(temp_path, linters)
        finally:
            os.unlink(temp_path)

    def add_linter(self, name: str, command: List[str]):
        self.linters[name] = ExternalLinter(name, command)

    def list_linters(self) -> List[str]:
        return list(self.linters.keys())


service = CodeLintService()

# ---------------- MCP Tools ----------------


@mcp.tool()
def lint_python_file(filepath: str, linters: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Lint a Python file by absolute file path.

    Args:
        filepath: Absolute path to the Python file.
        linters: Optional list of linter names to run.

    Returns:
        Linting results as a dictionary.
    """
    return service.lint_file(filepath, linters)


@mcp.tool()
def lint_python_code(code: str, linters: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Lint Python source code provided as a string.

    Args:
        code: Python source code.
        linters: Optional list of linter names to run.

    Returns:
        Linting results as a dictionary.
    """
    return service.lint_code(code, linters)


@mcp.tool()
def list_available_linters() -> List[str]:
    """
    List all available linters.

    Returns:
        A list of linter names.
    """
    return service.list_linters()


@mcp.tool()
def add_custom_linter(name: str, command: List[str]) -> Dict[str, Any]:
    """
    Register a custom linter.

    Args:
        name: Name of the custom linter.
        command: Command used to invoke the linter.

    Returns:
        Success status and message.
    """
    service.add_linter(name, command)
    return {"success": True, "message": f"Added linter: {name}"}


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8001,
    )

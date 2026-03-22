import math
import sys
from pathlib import Path

from fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).parent))

from config_loader import load_server_config, run_server

config = load_server_config("math")
mcp = FastMCP("Math")


# ----------------- Basic Float Operations -----------------
@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


@mcp.tool()
def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide a by b."""
    if b == 0:
        raise ValueError("Division by zero is not allowed.")
    return a / b


@mcp.tool()
def power(a: float, b: float) -> float:
    """Raise a to the power of b."""
    return a**b


@mcp.tool()
def sqrt(a: float) -> float:
    """Square root of a."""
    if a < 0:
        raise ValueError("Cannot take square root of a negative number.")
    return math.sqrt(a)


@mcp.tool()
def factorial(a: int) -> int:
    """Factorial of a non-negative integer."""
    if a < 0:
        raise ValueError("Factorial is not defined for negative numbers.")
    return math.factorial(a)


@mcp.tool()
def absolute(a: float) -> float:
    """Absolute value of a."""
    return abs(a)


# ----------------- Integer Operations -----------------
@mcp.tool()
def int_divide(a: int, b: int) -> int:
    """Integer (floor) division."""
    if b == 0:
        raise ValueError("Division by zero is not allowed.")
    return a // b


@mcp.tool()
def modulo(a: int, b: int) -> int:
    """Modulo (remainder) of a divided by b."""
    if b == 0:
        raise ValueError("Modulo by zero is not allowed.")
    return a % b


@mcp.tool()
def gcd(a: int, b: int) -> int:
    """Greatest common divisor of a and b."""
    return math.gcd(a, b)


@mcp.tool()
def lcm(a: int, b: int) -> int:
    """Least common multiple of a and b."""
    return math.lcm(a, b)


@mcp.tool()
def fast_power(base: int, exponent: int, mod: int = None) -> int:
    """
    Fast exponentiation using Python's built-in pow().
    If mod is provided, computes (base ** exponent) % mod efficiently.
    """
    if exponent < 0:
        raise ValueError("Exponent must be non-negative for fast_power.")
    return pow(base, exponent, mod)


# ----------------- Bitwise Operations -----------------
@mcp.tool()
def bit_and(a: int, b: int) -> int:
    """Bitwise AND of a and b."""
    return a & b


@mcp.tool()
def bit_or(a: int, b: int) -> int:
    """Bitwise OR of a and b."""
    return a | b


@mcp.tool()
def bit_xor(a: int, b: int) -> int:
    """Bitwise XOR of a and b."""
    return a ^ b


@mcp.tool()
def bit_left_shift(a: int, b: int) -> int:
    """Left shift a by b bits."""
    return a << b


@mcp.tool()
def bit_right_shift(a: int, b: int) -> int:
    """Right shift a by b bits."""
    return a >> b


# ----------------- Trigonometric & Logarithmic -----------------
@mcp.tool()
def sin(a: float) -> float:
    """Sine of a (in radians)."""
    return math.sin(a)


@mcp.tool()
def cos(a: float) -> float:
    """Cosine of a (in radians)."""
    return math.cos(a)


@mcp.tool()
def tan(a: float) -> float:
    """Tangent of a (in radians)."""
    return math.tan(a)


@mcp.tool()
def log(a: float, base: float = math.e) -> float:
    """Logarithm of a to the given base (default: natural log)."""
    if a <= 0:
        raise ValueError("Logarithm is only defined for positive numbers.")
    if base <= 0 or base == 1:
        raise ValueError("Logarithm base must be positive and not equal to 1.")
    return math.log(a, base)


@mcp.tool()
def log10(a: float) -> float:
    """Base-10 logarithm of a."""
    if a <= 0:
        raise ValueError("Logarithm is only defined for positive numbers.")
    return math.log10(a)


@mcp.tool()
def ceil(a: float) -> int:
    """Ceiling of a (smallest integer >= a)."""
    return math.ceil(a)


@mcp.tool()
def floor(a: float) -> int:
    """Floor of a (largest integer <= a)."""
    return math.floor(a)


@mcp.tool()
def round_to(a: float, ndigits: int = 0) -> float:
    """Round a to ndigits decimal places."""
    return round(a, ndigits)


if __name__ == "__main__":
    run_server(mcp, config)

from fastmcp import FastMCP
import math

mcp = FastMCP("Math")

# ----------------- Basic Float Operations -----------------
@mcp.tool()
def add(a: float, b: float) -> float:
    return a + b


@mcp.tool()
def subtract(a: float, b: float) -> float:
    return a - b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    return a * b


@mcp.tool()
def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("Division by zero is not allowed.")
    return a / b


@mcp.tool()
def power(a: float, b: float) -> float:
    return a**b


@mcp.tool()
def sqrt(a: float) -> float:
    if a < 0:
        raise ValueError("Cannot take square root of a negative number.")
    return math.sqrt(a)


@mcp.tool()
def factorial(a: int) -> int:
    if a < 0:
        raise ValueError("Factorial is not defined for negative numbers.")
    return math.factorial(a)


@mcp.tool()
def absolute(a: float) -> float:
    return abs(a)


# ----------------- Integer-specific Operations -----------------
@mcp.tool()
def int_divide(a: int, b: int) -> int:
    """Integer division"""
    if b == 0:
        raise ValueError("Division by zero is not allowed.")
    return a // b


@mcp.tool()
def modulo(a: int, b: int) -> int:
    """Modulo (remainder)"""
    if b == 0:
        raise ValueError("Modulo by zero is not allowed.")
    return a % b


@mcp.tool()
def gcd(a: int, b: int) -> int:
    """Greatest common divisor"""
    return math.gcd(a, b)


@mcp.tool()
def lcm(a: int, b: int) -> int:
    """Least common multiple"""
    if a == 0 or b == 0:
        return 0
    return abs(a * b) // math.gcd(a, b)


@mcp.tool()
def fast_power(base: int, exponent: int, mod: int = None) -> int:
    """
    Fast exponentiation.
    If mod is provided, computes (base ** exponent) % mod efficiently.
    """
    if exponent < 0:
        raise ValueError("Exponent must be non-negative for fast_power.")

    result = 1
    b = base
    e = exponent

    while e > 0:
        if e % 2 == 1:
            result *= b
            if mod is not None:
                result %= mod
        b *= b
        if mod is not None:
            b %= mod
        e //= 2

    return result


@mcp.tool()
def bit_and(a: int, b: int) -> int:
    return a & b


@mcp.tool()
def bit_or(a: int, b: int) -> int:
    return a | b


@mcp.tool()
def bit_xor(a: int, b: int) -> int:
    return a ^ b


@mcp.tool()
def bit_left_shift(a: int, b: int) -> int:
    return a << b


@mcp.tool()
def bit_right_shift(a: int, b: int) -> int:
    return a >> b


if __name__ == "__main__":
    mcp.run(transport="streamable-http", port=8000, host="0.0.0.0")

"""Тесты SymPy-инструментов: корректность и запрет произвольного кода."""
from assistant.sympy_tools import execute_tool


def test_solve_eq():
    assert execute_tool("solve_eq", {"equation": "2*x+3=7", "var": "x"}) == "[2]"


def test_simplify():
    assert execute_tool("simplify_expr", {"expr": "2*x+3*x"}) == "5*x"


def test_diff():
    assert execute_tool("diff_expr", {"expr": "x^2", "var": "x"}) == "2*x"


def test_integrate_definite():
    assert execute_tool("integrate_expr",
                        {"expr": "2*x", "var": "x", "a": "0", "b": "1"}) == "1"


def test_check_substitute():
    out = execute_tool("check_substitute", {"expr": "x^2+1", "var": "x", "value": "2"})
    assert out.startswith("5")


def test_rejects_code_like_inputs():
    bad = ["__import__('os')", "open('f')", "exec('1')", "eval('1')", "[x][0]",
           "x.y", "lambda x: x", "x" * 501, "1;2", "class X", "a`b"]
    for s in bad:
        out = execute_tool("simplify_expr", {"expr": s})
        assert out.startswith("ERROR"), s


def test_rejects_bad_equation_and_var():
    assert execute_tool("solve_eq", {"equation": "x+1", "var": "x"}).startswith("ERROR")
    assert execute_tool("solve_eq", {"equation": "x=1=2", "var": "x"}).startswith("ERROR")
    assert execute_tool("solve_eq", {"equation": "x=1", "var": "x;y"}).startswith("ERROR")
    assert execute_tool("solve_eq", {"equation": "x=1", "var": "import"}).startswith("ERROR")


def test_rejects_unknown_tool_and_args():
    assert execute_tool("nope", {}).startswith("ERROR")
    assert execute_tool("simplify_expr", {"expr": "1", "z": "2"}).startswith("ERROR")
    assert execute_tool("simplify_expr", ["x"]).startswith("ERROR")
    assert execute_tool("simplify_expr", {"expr": 5}).startswith("ERROR")

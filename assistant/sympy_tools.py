"""Ограниченные структурированные функции SymPy.

Модель НЕ может выполнять произвольный код: на вход принимаются только
короткие математические строки, которые разбираются sympy.parse_expr,
затем дерево проверяется по белому списку узлов. Никаких exec/eval/subprocess.
"""
import concurrent.futures
import re

import sympy
from sympy.parsing.sympy_parser import convert_xor, parse_expr, standard_transformations

MAX_LEN = 500
TOOL_TIMEOUT_S = 30

# Жёсткий префикс-фильтр: ничего похожего на код Python.
_REJECT_SUBSTRINGS = ("__", "import", "exec", "eval", "open", "lambda", "class",
                      ";", "@", "$", "`", "\\", "[", "]", "{", "}", ".", "'", '"')
_VAR_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{0,7}$")
_RESERVED = {"import", "exec", "eval", "open", "lambda", "class", "def", "return",
             "for", "while", "if", "else", "with", "as", "from", "pass", "None",
             "True", "False", "I", "oo"}

ALLOWED_FUNCS = {
    "sin": sympy.sin, "cos": sympy.cos, "tan": sympy.tan,
    "asin": sympy.asin, "acos": sympy.acos, "atan": sympy.atan,
    "exp": sympy.exp, "log": sympy.log, "ln": sympy.log,
    "sqrt": sympy.sqrt, "Abs": sympy.Abs, "abs": sympy.Abs,
    "factorial": sympy.factorial, "floor": sympy.floor, "ceiling": sympy.ceiling,
    "pi": sympy.pi, "E": sympy.E,
}
ALLOWED_NODES = (sympy.Symbol, sympy.Integer, sympy.Float, sympy.Rational,
                 sympy.Add, sympy.Mul, sympy.Pow, sympy.Number,
                 sympy.sin, sympy.cos, sympy.tan,
                 sympy.asin, sympy.acos, sympy.atan,
                 sympy.exp, sympy.log, sympy.sqrt, sympy.Abs,
                 sympy.factorial, sympy.floor, sympy.ceiling,
                 sympy.pi.__class__, sympy.E.__class__)

TRANSFORMS = standard_transformations + (convert_xor,)


class ToolError(Exception):
    pass


def _check_text(s: str) -> str:
    if not isinstance(s, str):
        raise ToolError("аргумент должен быть строкой")
    s = s.strip()
    if not s or len(s) > MAX_LEN:
        raise ToolError("пустое выражение или длиннее 500 символов")
    low = s.lower()
    for bad in _REJECT_SUBSTRINGS:
        if bad in low:
            raise ToolError(f"запрещённая конструкция: {bad!r}")
    return s


def _check_var(name: str) -> sympy.Symbol:
    if not isinstance(name, str) or not _VAR_RE.match(name.strip()):
        raise ToolError(f"плохая переменная: {name!r}")
    name = name.strip()
    if name in _RESERVED:
        raise ToolError(f"запрещённое имя: {name!r}")
    return sympy.Symbol(name)


def _check_tree(expr: sympy.Basic) -> None:
    for node in sympy.preorder_traversal(expr):
        if not isinstance(node, ALLOWED_NODES):
            raise ToolError(f"запрещённый узел: {type(node).__name__}")
        if isinstance(node, sympy.Symbol) and (
                node.name in _RESERVED or not _VAR_RE.match(node.name)):
            raise ToolError(f"запрещённый символ: {node.name!r}")


def _parse(s: str) -> sympy.Basic:
    s = _check_text(s)
    try:
        expr = parse_expr(s, local_dict=dict(ALLOWED_FUNCS), transformations=TRANSFORMS)
    except Exception as e:
        raise ToolError(f"не разобрано: {e}")
    if not isinstance(expr, sympy.Basic):
        raise ToolError("не математическое выражение")
    _check_tree(expr)
    return expr


def _split_eq(s: str):
    s = _check_text(s)
    if s.count("=") != 1:
        raise ToolError("нужно ровно одно '='")
    return _parse(s.split("=")[0]), _parse(s.split("=")[1])


def _run(fn, *args):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(fn, *args)
        try:
            return fut.result(timeout=TOOL_TIMEOUT_S)
        except concurrent.futures.TimeoutError:
            raise ToolError("превышен лимит времени (30 с)")


# --- пять инструментов ---

def solve_eq(equation: str, var: str) -> str:
    lhs, rhs = _split_eq(equation)
    v = _check_var(var)
    sols = _run(sympy.solve, lhs - rhs, v)
    return str(sols)


def simplify_expr(expr: str) -> str:
    return str(_run(sympy.simplify, _parse(expr)))


def diff_expr(expr: str, var: str) -> str:
    return str(_run(sympy.diff, _parse(expr), _check_var(var)))


def integrate_expr(expr: str, var: str, a: str = "", b: str = "") -> str:
    e, v = _parse(expr), _check_var(var)
    if (a == "") != (b == ""):
        raise ToolError("нужны обе границы или ни одной")
    if a == "":
        return str(_run(sympy.integrate, e, v))
    lo, hi = _parse(a), _parse(b)
    return str(_run(sympy.integrate, e, (v, lo, hi)))


def check_substitute(expr: str, var: str, value: str) -> str:
    e, v, val = _parse(expr), _check_var(var), _parse(value)
    res = _run(lambda: sympy.simplify(e.subs(v, val)))
    out = str(res)
    try:
        out += f" ~ {float(res):.6g}"
    except (TypeError, ValueError):
        pass
    return out


TOOLS = {
    "solve_eq": (solve_eq, ("equation", "var")),
    "simplify_expr": (simplify_expr, ("expr",)),
    "diff_expr": (diff_expr, ("expr", "var")),
    "integrate_expr": (integrate_expr, ("expr", "var", "a", "b")),
    "check_substitute": (check_substitute, ("expr", "var", "value")),
}

TOOL_HELP = """\
solve_eq(equation, var) — решить уравнение, напр. equation="2*x+3=7", var="x"
simplify_expr(expr) — упростить выражение
diff_expr(expr, var) — производная по var
integrate_expr(expr, var, a, b) — интеграл; a,b пустые = неопределённый, иначе определённый от a до b
check_substitute(expr, var, value) — подставить var=value и вычислить (для проверки)"""


def execute_tool(name: str, args: dict) -> str:
    """Выполнить инструмент по имени. Ошибки возвращаются строкой ERROR:..."""
    try:
        if name not in TOOLS:
            raise ToolError(f"нет инструмента {name!r}")
        fn, params = TOOLS[name]
        if not isinstance(args, dict):
            raise ToolError("args должен быть объектом")
        call = {}
        for p in params:
            v = args.get(p, "")
            if not isinstance(v, str):
                raise ToolError(f"аргумент {p!r} должен быть строкой")
            call[p] = v
        extra = set(args) - set(params)
        if extra:
            raise ToolError(f"лишние аргументы: {sorted(extra)}")
        return fn(**call)
    except ToolError as e:
        return f"ERROR: {e}"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"

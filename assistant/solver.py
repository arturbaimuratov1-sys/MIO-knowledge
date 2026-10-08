"""Решатель задач: режим без инструментов и режим с SymPy."""
import json
import re
import time

from . import llm
from .sympy_tools import TOOL_HELP, execute_tool

FORMAT_RULE = """Строго соблюдай формат из пяти разделов:
ДАНО: ...
МЕТОД И ДОПУЩЕНИЯ: ...
РЕШЕНИЕ: ...
ПРОВЕРКА: ...
ОТВЕТ: ...
Раздел ОТВЕТ — одна строка с итоговым значением."""

PLAIN_SYSTEM = ("Ты — школьный помощник по математике и физике. Отвечай по-русски. "
                "Решай задачу по шагам.\n" + FORMAT_RULE)

PLAN_SYSTEM = ("""Ты — планировщик вычислений. В ответ выведи ТОЛЬКО toolcall-блоки, без какого-либо другого текста.
Каждый блок строго такого вида:
```toolcall
{"name": "solve_eq", "args": {"equation": "2*x+3=7", "var": "x"}}
```
Доступные инструменты:
""" + TOOL_HELP + """
Правила: аргументы — только строки; выражения — математический синтаксис (2*x+3, sin(x), x^2).
Пример: задача "Реши уравнение x^2 = 9" -> один блок solve_eq с equation="x^2=9", var="x".
ЗАПРЕЩЕНО писать что-либо кроме toolcall-блоков.""")

FINAL_SYSTEM = ("""Ты — школьный помощник по математике и физике. Отвечай по-русски.
Вычисления уже выполнены инструментами SymPy, их результаты даны ниже — используй их.
""" + FORMAT_RULE + """
В разделе ПРОВЕРКА опирайся на результаты инструментов и добавь пометку:
это проверка вычислений, а не доказательство правильности всего рассуждения.""")

TOOLCALL_RE = re.compile(r"```toolcall\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_calls(text: str) -> list:
    calls = []
    for m in TOOLCALL_RE.finditer(text):
        try:
            obj = json.loads(m.group(1))
            if isinstance(obj, dict) and isinstance(obj.get("args"), dict):
                calls.append({"name": str(obj.get("name", "")), "args": obj["args"]})
        except (json.JSONDecodeError, ValueError):
            continue
    return calls


def solve(problem: str, use_tools: bool, max_tokens: int = 512) -> dict:
    t0 = time.perf_counter()
    tool_calls, tool_results = [], []
    if not use_tools:
        answer = llm.chat(
            [{"role": "system", "content": PLAIN_SYSTEM},
             {"role": "user", "content": problem}],
            max_tokens=max_tokens)
        return {"answer": answer, "tool_calls": [], "tool_results": [],
                "rounds": 1, "time_s": time.perf_counter() - t0}

    # Фаза 1: планирование вычислений (до 2 попыток получить toolcall-блоки).
    calls = []
    for attempt in range(2):
        plan_text = llm.chat(
            [{"role": "system", "content": PLAN_SYSTEM},
             {"role": "user", "content": problem}],
            max_tokens=256)
        calls = _extract_calls(plan_text)
        if calls:
            break
    # Фаза 2: выполнение инструментов.
    results = []
    for c in calls[:6]:
        res = execute_tool(c["name"], c["args"])
        tool_calls.append(c)
        tool_results.append(res)
        results.append(f'{c["name"]}({c["args"]}) -> {res}')
    if results:
        tools_context = "Результаты инструментов SymPy:\n" + "\n".join(results)
    else:
        tools_context = ("Инструменты не были вызваны (планировщик не выдал вызовов). "
                         "Реши задачу самостоятельно.")
    # Фаза 3: итоговый ответ.
    answer = llm.chat(
        [{"role": "system", "content": FINAL_SYSTEM},
         {"role": "user", "content": f"Задача: {problem}\n\n{tools_context}"}],
        max_tokens=max_tokens)
    return {"answer": answer, "tool_calls": tool_calls,
            "tool_results": tool_results, "rounds": 3,
            "time_s": time.perf_counter() - t0}

"""Сравнение: модель без инструментов vs модель с SymPy.

Запуск из корня проекта:
    .\\.venv\\Scripts\\python.exe -m assistant.run_eval
Результаты: eval/results.json
"""
import json
import os
import re
import sys

from . import server, solver

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_PATH = os.path.join(ROOT, "assistant", "eval_tasks.json")
OUT_PATH = os.path.join(ROOT, "eval", "results.json")

ANSWER_RE = re.compile(r"ОТВЕТ\s*:\s*(.+)", re.IGNORECASE)
NUM_RE = re.compile(r"-?\d+(?:[.,]\d+)?")


def _normalize(s: str) -> str:
    s = s.lower().replace("boxed", "").replace("$", "").replace("\\", "")
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r",(?!\s)", ".", s)  # десятичная запятая, но не разделитель списка
    return s.replace(" ", "")


def grade(task: dict, text: str) -> dict:
    m = ANSWER_RE.findall(text)
    zone = m[-1] if m else text
    norm = _normalize(zone)
    if "match_any" in task:
        ok = any(_normalize(a) in norm for a in task["match_any"])
        return {"pass": ok, "format_ok": bool(m), "got": zone.strip()[:200]}
    found = []
    for tok in NUM_RE.findall(norm.replace(",", " ")):
        try:
            found.append(float(tok))
        except ValueError:
            pass
    tol = task.get("tol", 0.02)
    ok = True
    for want in task["numbers"]:
        hit = any(abs(f - want) <= tol * max(1.0, abs(want)) + 1e-9 for f in found)
        ok = ok and hit
    return {"pass": ok, "format_ok": bool(m), "got": zone.strip()[:200]}


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    tasks = json.load(open(TASKS_PATH, encoding="utf-8"))["tasks"]
    if limit:
        tasks = tasks[:limit]
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    proc = server.start()
    print("server up, tasks:", len(tasks), flush=True)
    results = []
    try:
        for t in tasks:
            row = {"id": t["id"], "category": t["category"]}
            for mode in ("plain", "tools"):
                r = solver.solve(t["problem"], use_tools=(mode == "tools"))
                g = grade(t, r["answer"])
                row[mode] = {"pass": g["pass"], "format_ok": g["format_ok"],
                             "time_s": round(r["time_s"], 1),
                             "tool_calls": len(r["tool_calls"]),
                             "got": g["got"], "answer": r["answer"]}
                print(f'{t["id"]} {mode}: {"PASS" if g["pass"] else "FAIL"} '
                      f'{r["time_s"]:.0f}s tools={len(r["tool_calls"])}', flush=True)
            results.append(row)
    finally:
        server.stop(proc)
    json.dump(results, open(OUT_PATH, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    # Сводка по категориям.
    cats = {}
    for r in results:
        c = cats.setdefault(r["category"], {"n": 0, "plain": 0, "tools": 0,
                                            "t_plain": 0.0, "t_tools": 0.0,
                                            "calls": 0})
        c["n"] += 1
        c["plain"] += r["plain"]["pass"]
        c["tools"] += r["tools"]["pass"]
        c["t_plain"] += r["plain"]["time_s"]
        c["t_tools"] += r["tools"]["time_s"]
        c["calls"] += r["tools"]["tool_calls"]
    print("--- summary (acc_plain/acc_tools, avg_s) ---")
    for name, c in cats.items():
        print(f'{name}: {c["plain"]}/{c["n"]} vs {c["tools"]}/{c["n"]} | '
              f'{c["t_plain"]/c["n"]:.0f}s vs {c["t_tools"]/c["n"]:.0f}s | '
              f'tool_calls={c["calls"]}')


if __name__ == "__main__":
    main()

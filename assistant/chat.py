"""Терминальный диалог: задача -> решение на русском.

Запуск из корня проекта:
    .\\.venv\\Scripts\\python.exe -m assistant.chat
Команды: /plain — переключить режим без инструментов, /tools — с SymPy, /quit — выход.
"""
import sys

from . import server, solver


def main() -> None:
    if server.is_up():
        print("llama-server уже запущен, подключаюсь.")
        proc = None
    else:
        print("Запускаю llama-server (CPU, локальная модель)...")
        proc = server.start()
        print("Сервер готов.")
    use_tools = True
    print("Режим: с SymPy. Введи задачу (/plain, /tools, /quit).")
    try:
        while True:
            try:
                text = input("\nЗадача> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue
            if text == "/quit":
                break
            if text == "/plain":
                use_tools = False
                print("Режим: без инструментов.")
                continue
            if text == "/tools":
                use_tools = True
                print("Режим: с SymPy.")
                continue
            r = solver.solve(text, use_tools=use_tools)
            print(f"\n--- решение ({r['time_s']:.1f} с, "
                  f"инструментов: {len(r['tool_calls'])}) ---")
            print(r["answer"])
    finally:
        if proc is not None:
            server.stop(proc)
            print("\nСервер остановлен.")


if __name__ == "__main__":
    sys.exit(main())

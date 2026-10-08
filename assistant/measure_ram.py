"""Замер CPU-only peak RAM: llama-server + Python во время решения.

Запуск из корня проекта:
    .\\.venv\\Scripts\\python.exe -m assistant.measure_ram
"""
import threading
import time

import psutil

from . import server, solver


def main() -> None:
    proc = server.start()
    srv = psutil.Process(proc.pid)
    time.sleep(2)
    load_mib = srv.memory_info().rss / 1024**2
    me = psutil.Process()
    peak = {"srv": load_mib, "me": 0.0, "total": 0.0}
    stop = threading.Event()

    def sampler():
        while not stop.is_set():
            try:
                s = srv.memory_info().rss / 1024**2
            except psutil.NoSuchProcess:
                s = 0.0
            m = me.memory_info().rss / 1024**2
            peak["srv"] = max(peak["srv"], s)
            peak["me"] = max(peak["me"], m)
            peak["total"] = max(peak["total"], s + m)
            time.sleep(0.2)

    th = threading.Thread(target=sampler, daemon=True)
    th.start()
    try:
        r = solver.solve(
            "Сколько теплоты нужно, чтобы нагреть 1 кг воды на 10 градусов? "
            "Удельная теплоёмкость воды 4200 Дж/(кг·°C).",
            use_tools=True)
    finally:
        stop.set()
        th.join()
        server.stop(proc)
    print(f"solve_time_s: {r['time_s']:.1f}, tool_calls: {len(r['tool_calls'])}")
    print(f"server_rss_after_load_mib: {load_mib:.0f}")
    print(f"peak_server_mib: {peak['srv']:.0f}")
    print(f"peak_python_mib: {peak['me']:.0f}")
    print(f"peak_total_mib: {peak['total']:.0f}")


if __name__ == "__main__":
    main()

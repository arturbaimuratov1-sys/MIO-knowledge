"""Управление локальным llama-server (CPU-only, offline)."""
import subprocess
import time
import urllib.request

from . import config


def is_up() -> bool:
    try:
        with urllib.request.urlopen(config.SERVER_URL + "/health", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def start() -> subprocess.Popen:
    """Запускает llama-server на локальной GGUF-модели. Возвращает процесс."""
    if is_up():
        raise RuntimeError("llama-server уже запущен")
    cmd = [
        config.SERVER_EXE,
        "-m", config.MODEL_GGUF,
        "-c", str(config.CTX_TOKENS),
        "--host", config.SERVER_HOST,
        "--port", str(config.SERVER_PORT),
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=config.ROOT,
    )
    for _ in range(120):
        if is_up():
            return proc
        if proc.poll() is not None:
            raise RuntimeError(f"llama-server завершился с кодом {proc.returncode}")
        time.sleep(1)
    proc.terminate()
    raise RuntimeError("llama-server не ответил за 120 с")


def stop(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()

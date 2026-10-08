"""Пути и константы помощника."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LLAMACPP_DIR = os.path.join(ROOT, "third_party", "llamacpp")
SERVER_EXE = os.path.join(LLAMACPP_DIR, "llama-server.exe")
MODEL_GGUF = os.path.join(ROOT, "models", "qwen3-1.7b-q4_k_m.gguf")

CTX_TOKENS = 2048
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

# Qwen3: суффикс /no_think отключает режим рассуждений (аналог enable_thinking=False).
NO_THINK_SUFFIX = "/no_think"

"""Проверка базовой модели Qwen3-1.7B на GPU.

Использование (из корня проекта):
    .\\.venv\\Scripts\\python.exe scripts\\check_model.py

Повторный запуск строго из локального cache (без сети):
    $env:HF_HUB_OFFLINE = '1'
    .\\.venv\\Scripts\\python.exe scripts\\check_model.py
"""
import os
import sys
import time

# Единый локальный cache весов внутри проекта — без дубликатов.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("HF_HOME", os.path.join(_PROJECT_ROOT, ".hf-cache"))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import torch  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

REPO_ID = "Qwen/Qwen3-1.7B"
REVISION = "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e"
QUESTION = "What is 2+2? Answer with one short sentence."
MAX_NEW_TOKENS = 32


def mib(x: int) -> float:
    return x / 1024**2


def main() -> None:
    if not torch.cuda.is_available():
        print("CUDA недоступна — проверять нечего.")
        raise SystemExit(1)

    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    print(f"model: {REPO_ID}@{REVISION}")
    print(f"device: {torch.cuda.get_device_name(0)}")
    print(f"dtype: {'BF16' if dtype == torch.bfloat16 else 'FP16'}")

    try:
        tok = AutoTokenizer.from_pretrained(REPO_ID, revision=REVISION)
        model = AutoModelForCausalLM.from_pretrained(REPO_ID, revision=REVISION, dtype=dtype)
        model.to("cuda")
    except torch.cuda.OutOfMemoryError as e:
        print(f"CUDA out of memory при загрузке: {e}")
        print(f"allocated: {mib(torch.cuda.memory_allocated()):.0f} MiB, "
              f"reserved: {mib(torch.cuda.memory_reserved()):.0f} MiB")
        raise SystemExit(2)

    for p in model.parameters():
        p.requires_grad_(False)
    model.eval()

    prompt = tok.apply_chat_template(
        [{"role": "user", "content": QUESTION}],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    inputs = tok(prompt, return_tensors="pt").to("cuda")

    torch.cuda.reset_peak_memory_stats()
    try:
        with torch.inference_mode():
            t0 = time.perf_counter()
            out = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)
            torch.cuda.synchronize()
            dt = time.perf_counter() - t0
    except torch.cuda.OutOfMemoryError as e:
        print(f"CUDA out of memory при генерации: {e}")
        print(f"allocated: {mib(torch.cuda.memory_allocated()):.0f} MiB, "
              f"reserved: {mib(torch.cuda.memory_reserved()):.0f} MiB")
        raise SystemExit(2)

    new_tokens = out[0][inputs["input_ids"].shape[1]:]
    answer = tok.decode(new_tokens, skip_special_tokens=True)
    print(f"question: {QUESTION}")
    print(f"answer: {answer}")
    print(f"new_tokens: {len(new_tokens)}, gen_time_s: {dt:.2f}")
    print(f"peak_allocated_mib: {mib(torch.cuda.max_memory_allocated()):.0f}, "
          f"peak_reserved_mib: {mib(torch.cuda.max_memory_reserved()):.0f}")


if __name__ == "__main__":
    main()

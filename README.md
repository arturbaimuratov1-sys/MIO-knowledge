# kpack-lab

Локальная лаборатория для экспериментов с LLM (Qwen + LoRA/PEFT).
Пока: только окружение и проверка GPU. Обучение и скачивание моделей — позже.

## Окружение

- Python 3.11 (.venv в корне проекта)
- PyTorch с CUDA (сборка cu128) + Transformers, Datasets, PEFT, Accelerate, pytest

## Использование (из корня проекта, свежий shell)

```powershell
.\.venv\Scripts\Activate.ps1
python check_gpu.py
```

Проверка зависимостей:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Состав

- `check_gpu.py` — проверка видимости RTX 4060 и малой операции на GPU
- `tests/test_env.py` — базовая проверка импортов и доступности CUDA
- `requirements.txt` — закреплённые зависимости (torch ставится из CUDA-индекса PyTorch)
- `scripts/check_model.py` — загрузка Qwen3-1.7B на GPU и пробная генерация
- `MODEL_REVISION.txt` — точная revision модели
- `.hf-cache/` — единый локальный HF-кэш (HF_HOME), без дубликатов весов

## Проверка модели

```powershell
.\.venv\Scripts\python.exe scripts\check_model.py
# строго из кэша, без сети:
$env:HF_HUB_OFFLINE = '1'
.\.venv\Scripts\python.exe scripts\check_model.py
```

## Физмат-помощник (CPU-only, offline)

- `models/qwen3-1.7b-q4_k_m.gguf` — Qwen3-1.7B, GGUF Q4_K_M (контекст 2048)
- `models/qwen3-1.7b-f16.gguf` — промежуточный F16 (для других квантов)
- `third_party/llamacpp/` — llama.cpp b11476, CPU-сборка Windows (GPU не используется)
- `assistant/` — Python: диалог, SymPy-инструменты, сравнение, замер RAM
- `assistant/eval_tasks.json` — 30 задач с эталонами (НЕ для обучения)
- `eval/results.json` — результаты сравнения

Команды из корня проекта:

```powershell
# диалог в терминале (ответы на русском, /plain, /tools, /quit)
.\.venv\Scripts\python.exe -m assistant.chat
# сравнение без инструментов / с SymPy
.\.venv\Scripts\python.exe -m assistant.run_eval
# замер peak RAM (llama-server + Python)
.\.venv\Scripts\python.exe -m assistant.measure_ram
# все тесты
.\.venv\Scripts\python.exe -m pytest -q
```

## Модели и HF-кеш в Git LFS

Веса GGUF, снимок Qwen HF-кеша и Windows-бинарники llama.cpp хранятся через Git LFS.
Файлы больше 2 ГБ разбиты на части до 1 ГиБ; исходные большие файлы собираются локально.

После клонирования установите Git LFS, затем из корня проекта:

```powershell
git lfs install
git lfs pull
python scripts/restore_lfs_models.py
```

Скрипт проверяет SHA-256 и размер собранных файлов; совпадающие существующие файлы пропускает,
отличающиеся не перезаписывает. Манифест: `models-lfs-manifest.json`.
HF-снимок: `Qwen/Qwen3-1.7B@70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`.
Веса занимают примерно 9,4 ГБ в LFS; сборка требует дополнительно около 7,5 ГБ места.
`models.zip` дублирует GGUF и оставлен локально. `.venv`, Python/pytest-кеши,
HF-логи и служебные файлы не включены. Игнорирование каталогов моделей и кеша сохраняется;
добавленные явно файлы уже отслеживаются Git. Новые веса добавляйте осознанно.

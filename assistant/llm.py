"""HTTP-клиент к llama-server (OpenAI-совместимый /chat/completions)."""
import requests

from . import config


def chat(messages: list, max_tokens: int = 512, temperature: float = 0.0,
         timeout: int = 600) -> str:
    """Отправляет сообщения и возвращает текст ответа. Thinking выключен."""
    msgs = []
    for m in messages:
        m = dict(m)
        if m.get("role") == "user" and config.NO_THINK_SUFFIX not in m.get("content", ""):
            m["content"] = m["content"] + "\n" + config.NO_THINK_SUFFIX
        msgs.append(m)
    r = requests.post(
        config.SERVER_URL + "/v1/chat/completions",
        json={
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

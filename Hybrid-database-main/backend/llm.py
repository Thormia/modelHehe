"""Client tối giản cho API chat completions tương thích OpenAI (Ollama /v1, vLLM, ...)."""
import json
import re

import httpx


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, base_url, model, api_key="ollama", timeout=180.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def chat(self, messages, temperature=0.0, max_tokens=1024, json_mode=False):
        payload = {"model": self.model, "messages": messages, "temperature": temperature,
                   "max_tokens": max_tokens, "stream": False}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            r = httpx.post(f"{self.base_url}/chat/completions", json=payload, timeout=self.timeout,
                           headers={"Authorization": f"Bearer {self.api_key}"})
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"] or ""
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
            raise LLMError(f"{self.model} @ {self.base_url}: {e}") from e


def parse_json_object(text):
    """Lấy JSON object từ output của LLM (bỏ ```json ... ```, chữ thừa trước/sau). Trả None nếu không có."""
    if not text:
        return None
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        o = json.loads(t)
        return o if isinstance(o, dict) else None
    except ValueError:
        pass
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", t):
        try:
            o, _ = dec.raw_decode(t, m.start())
            if isinstance(o, dict):
                return o
        except ValueError:
            continue
    return None

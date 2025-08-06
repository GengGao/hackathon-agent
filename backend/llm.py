import httpx
import json
from typing import List, Dict

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "gpt-oss-20b"

def generate(prompt: str, system: str = "", temperature: float = 0.7, max_tokens: int = 1024) -> str:
    """
    Calls Ollama's /generate endpoint.
    """
    payload = {
        "model": MODEL,
        "prompt": f"{system}\n\n{prompt}",
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(OLLAMA_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
        # Ollama returns a dict with "response"
        return data.get("response", "")
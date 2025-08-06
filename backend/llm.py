import litellm
from typing import Dict

# ---------------------------------------------------------
# Configuration – keep it in one place so you can switch later
# ---------------------------------------------------------
OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"          # <- Ollama's OpenAI‐compatible endpoint
OLLAMA_MODEL    = "ollama/gpt-oss-20b"               # format "provider/model"
DUMMY_API_KEY   = "sk-no-key"                       # Ollama ignores it

def generate(prompt: str, system: str = "", temperature: float = 0.7, max_tokens: int = 1024) -> str:
    """
    Calls LiteLLM → which forwards to Ollama.
    Returns the plain text response (no streaming).
    """
    # Build the OpenAI‑compatible message list
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    # LiteLLM handles the HTTP request internally
    response = litellm.completion(
        model=OLLAMA_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=DUMMY_API_KEY,               # required param; ignored by Ollama
        api_base=OLLAMA_BASE_URL,           # <‑‑ critical: point to local Ollama
    )
    # `response` is a litellm.utils.OpenAIResponse object
    # Grab the assistant message
    return response.choices[0].message.content
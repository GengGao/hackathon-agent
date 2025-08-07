import litellm
from typing import Dict

# ---------------------------------------------------------
# Configuration – keep it in one place so you can switch later
# ---------------------------------------------------------
OLLAMA_BASE_URL = "http://127.0.0.1:11434"          # <- Ollama's base URL (without /v1)
OLLAMA_MODEL    = "gpt-oss:20b"                     # Just the model name for Ollama
DUMMY_API_KEY   = "sk-no-key"                       # Ollama ignores it

async def generate_async(prompt: str,
                         system: str = "",
                         temperature: float = 0.7,
                         max_tokens: int = 1024) -> str:
    """
    Async call that returns the full completion text.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        # litellm already supports async via `acompletion`
        resp = await litellm.acompletion(
            model=f"ollama/{OLLAMA_MODEL}",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=DUMMY_API_KEY,
            api_base=OLLAMA_BASE_URL,
        )
        return resp.choices[0].message.content
    except Exception as e:
        print(f"Error calling LiteLLM: {e}")
        print(f"Model: ollama/{OLLAMA_MODEL}")
        print(f"API Base: {OLLAMA_BASE_URL}")
        raise
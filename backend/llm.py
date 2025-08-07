import litellm
from typing import Dict, AsyncGenerator, Union
import asyncio
import json
from openai import AsyncOpenAI

# ---------------------------------------------------------
# Configuration – keep it in one place so you can switch later
# ---------------------------------------------------------
OLLAMA_BASE_URL = "http://127.0.0.1:11434"          # <- Ollama's base URL (without /v1)
OLLAMA_MODEL    = "gpt-oss:20b"                     # Just the model name for Ollama
DUMMY_API_KEY   = "sk-no-key"                       # Ollama ignores it

# Configure LiteLLM for Ollama
litellm.set_verbose = False
litellm.api_base = OLLAMA_BASE_URL

# Initialize OpenAI client for direct Ollama API calls
client = AsyncOpenAI(
    base_url=f"{OLLAMA_BASE_URL}/v1",
    api_key=DUMMY_API_KEY
)


async def generate_stream(prompt: str,
                         system: str = "",
                         temperature: float = 0.7,
                         max_tokens: int = 1024) -> AsyncGenerator[Union[str, Dict], None]:
    """
    Async generator that yields tokens from the LLM response using OpenAI SDK directly.
    Handles thinking responses from gpt-oss:20b model.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:

        # Use OpenAI SDK directly for streaming
        response = await client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
        )

        thinking_mode = False
        buffer = ""

        async for chunk in response:
            delta = chunk.choices[0].delta

            # Check for reasoning/thinking content first
            if hasattr(delta, 'reasoning') and delta.reasoning:
                yield {"type": "thinking", "content": delta.reasoning}

            # Then check for regular content
            if delta.content is not None and delta.content:
                yield {"type": "content", "content": delta.content}

        # If we get here, the model worked successfully
        return

    except Exception as e:
        print(f"Error calling OpenAI SDK: {e}")
        print(f"Model: {OLLAMA_MODEL}")
        print(f"API Base: {OLLAMA_BASE_URL}/v1")
        raise

        # # Use LiteLLM for streaming (COMMENTED OUT)
        # response = litellm.completion(
        #     model=f"ollama/{OLLAMA_MODEL}",
        #     messages=messages,
        #     temperature=temperature,
        #     max_tokens=max_tokens,
        #     stream=True,
        #     api_base=OLLAMA_BASE_URL,
        #     api_key=DUMMY_API_KEY,
        #     thinking=False
        # )
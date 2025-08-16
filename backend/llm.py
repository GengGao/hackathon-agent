from typing import Dict, AsyncGenerator, Union, List, Any, Callable, Optional
import asyncio
import json
from openai import AsyncOpenAI
import os

# ---------------------------------------------------------
# Configuration – provider-agnostic LLM wiring
# ---------------------------------------------------------
# Default base URLs for providers. LMStudio commonly exposes an OpenAI-compatible
# HTTP API on a different port; if your LMStudio install uses another URL, set
# LLM_PROVIDER_BASE_URL via env or use the provider endpoint to change it at runtime.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234")

# Default model names per-provider (used as fallbacks)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "openai/gpt-oss-20b")

# Dummy API key for OpenAI-compatible local runtimes
DUMMY_API_KEY = os.getenv("DUMMY_API_KEY", "sk-no-key")

# Available models for current provider (populated at init)
AVAILABLE_MODELS = []

# Provider state
# allowed values: "ollama" or "lmstudio"
DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
current_provider = DEFAULT_PROVIDER

# Global variable to track current model selection
current_model = OLLAMA_MODEL if current_provider == "ollama" else LMSTUDIO_MODEL

# HTTP client (OpenAI-compatible) created per-provider
client: Optional[AsyncOpenAI] = None

async def initialize_models():
    """Initialize available models on startup and attempt to restore persisted selection."""
    # recreate client from persisted provider/base_url if present
    await maybe_restore_provider()
    await fetch_available_models()
    # Attempt restore
    try:
        from models.db import get_setting  # local import to avoid circular
        saved = get_setting("current_model")
        if saved and saved in AVAILABLE_MODELS:
            global current_model
            current_model = saved
    except Exception as e:
        if DEBUG_STREAM:
            print(f"[initialize_models] restore failed: {e}")
    if DEBUG_STREAM:
        print(f"Initialized models: {AVAILABLE_MODELS}; current={current_model}")

async def fetch_available_models():
    """Fetch available models from Ollama and update AVAILABLE_MODELS."""
    global AVAILABLE_MODELS
    try:
        if client is None:
            _ = create_client_for_current_provider()
        response = await client.models.list()
        # Try to derive a sensible list from response
        try:
            models = [m.id for m in response.data if m.id.startswith("gpt-oss") or m.id.startswith("openai/")]

        except Exception:
            # Some runtimes return a plain list
            models = [getattr(m, 'id', str(m)) for m in response]

        AVAILABLE_MODELS = models if len(models) > 0 else ["gpt-oss:20b", "gpt-oss:120b"]
        return AVAILABLE_MODELS
    except Exception as e:
        # Fallback to default models if Ollama is not available
        if current_provider == "ollama":
            AVAILABLE_MODELS = [OLLAMA_MODEL]
        else:
            AVAILABLE_MODELS = [LMSTUDIO_MODEL]
        if DEBUG_STREAM:
            print(f"Failed to fetch models from Ollama: {e}. Using fallback models.")
        return AVAILABLE_MODELS

# Initialize OpenAI client for direct Ollama API calls
def create_client_for_current_provider(base_url: Optional[str] = None) -> AsyncOpenAI:
    """Create (or recreate) the AsyncOpenAI client for the active provider.

    Note: This function mutates the module-global `client` variable.
    """
    global client
    base = base_url
    if base is None:
        base = OLLAMA_BASE_URL if current_provider == "ollama" else LMSTUDIO_BASE_URL
    client = AsyncOpenAI(base_url=f"{base}/v1", api_key=DUMMY_API_KEY)
    return client

# Create initial client
create_client_for_current_provider()

# Debug streaming disabled by default; enable with DEBUG_STREAM=1/true/yes
DEBUG_STREAM = os.getenv("DEBUG_STREAM", "0").lower() in ("1", "true", "yes")

async def generate_stream(
    prompt: str,
    system: str = "",
    temperature: float = 0.7,
    max_tokens: int = 1024,
    tools: Optional[List[Dict[str, Any]]] = None,
    execute_tool: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
    max_tool_rounds: int = 10,
    # Loop guards for reasoning/thinking tokens
    max_reasoning_chars_per_round: int = 1000,
    max_reasoning_repeats: int = 10,
    max_reasoning_only_chunks: int = 200,
    # When provided, use these chat messages directly (system/user/assistant history)
    # instead of constructing from prompt/system. Each item should match OpenAI's
    # chat message schema: {"role": "system|user|assistant|tool", "content": str, ...}
    seed_messages: Optional[List[Dict[str, Any]]] = None,
) -> AsyncGenerator[Union[str, Dict], None]:
    """
    Async generator that yields tokens from the LLM response using OpenAI SDK directly.
    Handles thinking responses and streaming tool calls when available.
    """
    # Build initial messages. If seed_messages is provided, use it as-is.
    messages: List[Dict[str, Any]] = []
    if seed_messages and len(seed_messages) > 0:
        messages = list(seed_messages)
    else:
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

    try:
        round_index = 0
        while True:
            round_index += 1
            # Stream assistant response for this round
            response = await client.chat.completions.create(
                model=current_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                stream=True,
            )

            # Accumulate potential tool calls announced during streaming
            tool_calls_args_buffers: Dict[int, str] = {}
            tool_calls_names: Dict[int, str] = {}
            tool_calls_ids: Dict[int, str] = {}
            finish_reason: Optional[str] = None

            any_yield_this_round = False
            any_content_this_round = False

            # Reasoning loop-guard state
            reasoning_total_chars = 0
            last_reasoning_norm: Optional[str] = None
            reasoning_repeat_count = 0
            suppress_reasoning = False
            reasoning_only_counter = 0
            seen_content_in_round = False

            async for chunk in response:
                choice = chunk.choices[0]
                delta = choice.delta
                finish_reason = getattr(choice, "finish_reason", None) or finish_reason
                if DEBUG_STREAM:
                    try:
                        print("[stream] chunk: ", chunk.model_dump())
                    except Exception:
                        print("[stream] chunk received")

                # Thinking parsing
                reasoning_text = None
                content_text = None
                try:
                    if hasattr(delta, 'reasoning') and delta.reasoning:
                        reasoning_text = delta.reasoning
                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        reasoning_text = delta.reasoning_content
                    if hasattr(delta, 'content') and delta.content:
                        content_text = delta.content
                except Exception:
                    pass

                if isinstance(delta, dict):
                    reasoning_text = reasoning_text or delta.get('reasoning') or delta.get('reasoning_content')
                    content_text = content_text or delta.get('content')

                if reasoning_text and not seen_content_in_round:
                    # Loop guard: normalize and track repeats/length
                    norm = (reasoning_text or "").strip().lower().replace("  ", " ")
                    if norm and norm == last_reasoning_norm:
                        reasoning_repeat_count += 1
                    else:
                        reasoning_repeat_count = 0
                        last_reasoning_norm = norm

                    reasoning_total_chars += len(reasoning_text or "")
                    reasoning_only_counter += 1 if not content_text else 0

                    if (
                        reasoning_total_chars > max_reasoning_chars_per_round
                        or reasoning_repeat_count > max_reasoning_repeats
                        or reasoning_only_counter > max_reasoning_only_chunks
                    ):
                        suppress_reasoning = True

                    if not suppress_reasoning:
                        any_yield_this_round = True
                        yield {"type": "thinking", "content": reasoning_text}
                if content_text:
                    any_yield_this_round = True
                    any_content_this_round = True
                    # Reset reasoning-only counter when content appears
                    reasoning_only_counter = 0
                    seen_content_in_round = True
                    yield {"type": "content", "content": content_text}

                # Tool calls (streaming) parsing
                tool_calls_delta = None
                try:
                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        tool_calls_delta = delta.tool_calls
                except Exception:
                    pass
                if tool_calls_delta is None and isinstance(delta, dict):
                    tool_calls_delta = delta.get('tool_calls')

                if tool_calls_delta:
                    for tc in tool_calls_delta:
                        try:
                            idx = getattr(tc, 'index', None)
                            func = getattr(tc, 'function', None)
                            tc_id = getattr(tc, 'id', None)
                            # When using dicts
                            if idx is None and isinstance(tc, dict):
                                idx = tc.get('index')
                                func = tc.get('function')
                                tc_id = tc.get('id', tc_id)
                            if idx is None:
                                continue
                            name_val = None
                            args_val = None
                            if func is not None:
                                # object style
                                if hasattr(func, 'name'):
                                    name_val = func.name
                                if hasattr(func, 'arguments'):
                                    args_val = func.arguments
                                # dict style
                                if isinstance(func, dict):
                                    name_val = name_val or func.get('name')
                                    args_val = args_val or func.get('arguments')
                            if name_val is not None:
                                tool_calls_names[idx] = name_val
                            if args_val is not None:
                                tool_calls_args_buffers[idx] = tool_calls_args_buffers.get(idx, '') + (args_val or '')
                            if tc_id:
                                tool_calls_ids[idx] = tc_id
                        except Exception:
                            continue

            # If nothing was yielded and no tool calls were announced, try a non-stream fallback
            if not any_yield_this_round and not tool_calls_args_buffers:
                try:
                    fallback = await client.chat.completions.create(
                        model=current_model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        tools=None,
                        stream=False,
                    )
                    content = fallback.choices[0].message.content or ""
                    if content:
                        yield {"type": "content", "content": content}
                except Exception:
                    pass

            # If we only saw thinking (no content) and no tool calls, ask once more non-stream for final content
            if any_yield_this_round and not any_content_this_round and not tool_calls_args_buffers:
                try:
                    fallback2 = await client.chat.completions.create(
                        model=current_model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        tools=None,
                        stream=False,
                    )
                    content2 = fallback2.choices[0].message.content or ""
                    if content2:
                        yield {"type": "content", "content": content2}
                except Exception:
                    pass

            # After streaming round ends, decide whether to execute tools
            if tool_calls_args_buffers and execute_tool and round_index <= max_tool_rounds:
                # Append assistant tool_calls message
                tool_calls_list = []
                for idx, args_str in tool_calls_args_buffers.items():
                    tool_calls_list.append({
                        "id": tool_calls_ids.get(idx, f"call_{round_index}_{idx}"),
                        "type": "function",
                        "function": {"name": tool_calls_names.get(idx, ""), "arguments": args_str or "{}"},
                    })
                messages.append({"role": "assistant", "content": "", "tool_calls": tool_calls_list})

                # Yield tool_calls event for UI transparency
                yield {"type": "tool_calls", "tool_calls": [
                    {
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "arguments": tc["function"].get("arguments", "{}")
                    } for tc in tool_calls_list
                ]}

                # Execute and append tool results
                for tc in tool_calls_list:
                    fn = tc["function"]["name"]
                    raw_args = tc["function"]["arguments"] or "{}"
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except Exception:
                        args = {}
                    result = execute_tool(fn, args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(result, ensure_ascii=False),
                    })
                # Continue next round to produce final content (or further tool calls)
                continue
            else:
                break

        return

    except Exception as e:
        print(f"Error calling OpenAI SDK: {e}")
        print(f"Model: {current_model}")
        print(f"API Base: {OLLAMA_BASE_URL}/v1")
        raise


async def check_ollama_status():
    """Check if Ollama is running and return status information."""
    try:
        # Fetch latest available models from Ollama
        available_models = await fetch_available_models()

        return {
            "connected": True,
            "provider": current_provider,
            "base_url": (OLLAMA_BASE_URL if current_provider == "ollama" else LMSTUDIO_BASE_URL),
            "model": current_model,
            "available_models": available_models
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "provider": current_provider,
            "base_url": (OLLAMA_BASE_URL if current_provider == "ollama" else LMSTUDIO_BASE_URL),
            "model": current_model,
            "available_models": AVAILABLE_MODELS  # Use cached/fallback models
        }


def get_current_model():
    """Get the currently selected model."""
    return current_model


def get_available_models():
    """Get the list of available models."""
    return AVAILABLE_MODELS


def get_provider():
    return current_provider


def get_provider_base_url():
    return OLLAMA_BASE_URL if current_provider == "ollama" else LMSTUDIO_BASE_URL


async def maybe_restore_provider():
    """Try to restore persisted provider/base_url and model from DB settings."""
    global current_provider, current_model, OLLAMA_BASE_URL, LMSTUDIO_BASE_URL
    try:
        from models.db import get_setting
        prov = get_setting("llm_provider")
        base = get_setting("llm_base_url")
        saved_model = get_setting("current_model")
        if prov in ("ollama", "lmstudio"):
            current_provider = prov
        if base:
            if current_provider == "ollama":
                OLLAMA_BASE_URL = base
            else:
                LMSTUDIO_BASE_URL = base
        if saved_model:
            current_model = saved_model
        # recreate client with restored values
        create_client_for_current_provider()
    except Exception:
        # ignore restore errors
        create_client_for_current_provider()


async def set_provider(provider_name: str, base_url: Optional[str] = None) -> bool:
    """Set the provider to 'ollama' or 'lmstudio'. Optionally set base_url.

    Persists selection into settings where possible.
    """
    global current_provider, OLLAMA_BASE_URL, LMSTUDIO_BASE_URL
    provider = (provider_name or "").lower()
    if provider not in ("ollama", "lmstudio"):
        return False
    current_provider = provider
    if base_url:
        if provider == "ollama":
            OLLAMA_BASE_URL = base_url
        else:
            LMSTUDIO_BASE_URL = base_url
    # recreate client
    create_client_for_current_provider(base_url if base_url else None)
    # attempt to persist
    try:
        from models.db import set_setting
        set_setting("llm_provider", current_provider)
        if base_url:
            set_setting("llm_base_url", base_url)
    except Exception:
        if DEBUG_STREAM:
            print("[set_provider] failed to persist provider settings")
    # refresh available models
    try:
        await fetch_available_models()
    except Exception:
        pass
    return True


async def set_model(model_name: str):
    """Set the model to use for generation and persist selection."""
    global current_model
    try:
        await fetch_available_models()
    except Exception:
        pass
    if model_name in AVAILABLE_MODELS:
        current_model = model_name
        try:
            from models.db import set_setting
            set_setting("current_model", model_name)
        except Exception as e:
            if DEBUG_STREAM:
                print(f"[set_model] persist failed: {e}")
        return True
    return False

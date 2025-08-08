import litellm
from typing import Dict, AsyncGenerator, Union, List, Any, Callable, Optional
import asyncio
import json
from openai import AsyncOpenAI
import json
import os

# ---------------------------------------------------------
# Configuration – keep it in one place so you can switch later
# ---------------------------------------------------------
OLLAMA_BASE_URL = "http://127.0.0.1:11434"          # <- Ollama's base URL (without /v1)
OLLAMA_MODEL    = "gpt-oss:20b"                     # Just the model name for Ollama
DUMMY_API_KEY   = "sk-no-key"                       # Ollama ignores it

# Available models - will be fetched from Ollama
AVAILABLE_MODELS = []

# Global variable to track current model
current_model = OLLAMA_MODEL

async def initialize_models():
    """Initialize available models on startup."""
    await fetch_available_models()
    print(f"Initialized models: {AVAILABLE_MODELS}")

async def fetch_available_models():
    """Fetch available models from Ollama and update AVAILABLE_MODELS."""
    global AVAILABLE_MODELS
    try:
        response = await client.models.list()
        # Filter for gpt-oss models specifically
        ollama_models = [model.id for model in response.data if model.id.startswith("gpt-oss")]
        AVAILABLE_MODELS = ollama_models if ollama_models else ["gpt-oss:20b", "gpt-oss:120b"]  # fallback
        return AVAILABLE_MODELS
    except Exception as e:
        # Fallback to default models if Ollama is not available
        AVAILABLE_MODELS = ["gpt-oss:20b", "gpt-oss:120b"]
        print(f"Failed to fetch models from Ollama: {e}. Using fallback models.")
        return AVAILABLE_MODELS

# Configure LiteLLM for Ollama
litellm.set_verbose = False
litellm.api_base = OLLAMA_BASE_URL

# Initialize OpenAI client for direct Ollama API calls
client = AsyncOpenAI(
    base_url=f"{OLLAMA_BASE_URL}/v1",
    api_key=DUMMY_API_KEY
)

# DEBUG_STREAM = os.getenv("DEBUG_STREAM", "0") in ("1", "true", "True")
DEBUG_STREAM = True

async def generate_stream(
    prompt: str,
                         system: str = "",
                         temperature: float = 0.7,
    max_tokens: int = 1024,
    tools: Optional[List[Dict[str, Any]]] = None,
    execute_tool: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
    max_tool_rounds: int = 5,
    # Loop guards for reasoning/thinking tokens
    max_reasoning_chars_per_round: int = 1000,
    max_reasoning_repeats: int = 5,
    max_reasoning_only_chunks: int = 100,
) -> AsyncGenerator[Union[str, Dict], None]:
    """
    Async generator that yields tokens from the LLM response using OpenAI SDK directly.
    Handles thinking responses and streaming tool calls when available.
    """
    messages: List[Dict[str, Any]] = []
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
            "model": current_model,
            "available_models": available_models
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "model": current_model,
            "available_models": AVAILABLE_MODELS  # Use cached/fallback models
        }


def get_current_model():
    """Get the currently selected model."""
    return current_model


def get_available_models():
    """Get the list of available models."""
    return AVAILABLE_MODELS


async def set_model(model_name: str):
    """Set the model to use for generation."""
    global current_model

    # Refresh available models from Ollama to ensure we have the latest list
    try:
        await fetch_available_models()
    except Exception:
        pass  # Continue with cached models if fetch fails

    if model_name in AVAILABLE_MODELS:
        current_model = model_name
        return True
    return False

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
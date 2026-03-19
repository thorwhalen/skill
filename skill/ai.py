"""Optional AI facade for semantic search and LLM-powered features.

All imports are lazy. This module works without any AI dependencies —
it gracefully degrades when providers are not installed.
"""

from skill.config import load_config


def is_ai_available() -> bool:
    """Check if an AI provider is available.

    Returns True if any supported provider can be imported and
    an API key is configured (or detectable from environment).

    >>> isinstance(is_ai_available(), bool)
    True
    """
    for loader in (_try_aisuite, _try_anthropic, _try_openai):
        if loader() is not None:
            return True
    return False


def chat(
    prompt: str,
    *,
    system: str | None = None,
    model: str | None = None,
    temperature: float = 0.0,
) -> str:
    """Send a chat completion request to the configured AI provider.

    Provider resolution order: aisuite -> anthropic -> openai.

    Raises ImportError with actionable install instructions if no
    provider is available.
    """
    config = load_config()
    model = model or config.ai_provider_model

    # Try aisuite first (supports provider:model convention)
    client = _try_aisuite()
    if client is not None:
        return _chat_aisuite(client, prompt, system=system, model=model, temperature=temperature)

    # Try direct anthropic SDK
    client = _try_anthropic()
    if client is not None:
        # Strip provider prefix if present
        _, _, model_id = model.partition(':')
        model_id = model_id or model
        return _chat_anthropic(client, prompt, system=system, model=model_id, temperature=temperature)

    # Try direct openai SDK
    client = _try_openai()
    if client is not None:
        _, _, model_id = model.partition(':')
        model_id = model_id or model
        return _chat_openai(client, prompt, system=system, model=model_id, temperature=temperature)

    raise ImportError(
        "No AI provider found. Install one of:\n"
        "  pip install skill[ai]       # installs aisuite\n"
        "  pip install skill[anthropic] # installs aisuite + anthropic\n"
        "  pip install skill[openai]    # installs aisuite + openai\n"
    )


# ---------------------------------------------------------------------------
# Provider loaders (lazy, return None on failure)
# ---------------------------------------------------------------------------

def _try_aisuite():
    try:
        import aisuite
        return aisuite.Client()
    except (ImportError, Exception):
        return None


def _try_anthropic():
    try:
        import anthropic
        return anthropic.Anthropic()
    except (ImportError, Exception):
        return None


def _try_openai():
    try:
        import openai
        return openai.OpenAI()
    except (ImportError, Exception):
        return None


# ---------------------------------------------------------------------------
# Provider-specific chat implementations
# ---------------------------------------------------------------------------

def _chat_aisuite(client, prompt, *, system, model, temperature):
    messages = []
    if system:
        messages.append({'role': 'system', 'content': system})
    messages.append({'role': 'user', 'content': prompt})
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content


def _chat_anthropic(client, prompt, *, system, model, temperature):
    kwargs = dict(
        model=model,
        max_tokens=4096,
        messages=[{'role': 'user', 'content': prompt}],
        temperature=temperature,
    )
    if system:
        kwargs['system'] = system
    resp = client.messages.create(**kwargs)
    return resp.content[0].text


def _chat_openai(client, prompt, *, system, model, temperature):
    messages = []
    if system:
        messages.append({'role': 'system', 'content': system})
    messages.append({'role': 'user', 'content': prompt})
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content

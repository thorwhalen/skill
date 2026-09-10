# skill.ai

Optional AI facade for semantic search and LLM-powered features.

All imports are lazy. This module works without any AI dependencies —
it gracefully degrades when providers are not installed.

### Functions

| [`chat`](#skill.ai.chat)(prompt, \*[, system, model, temperature])   | Send a chat completion request to the configured AI provider.   |
|---------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|
| [`is_ai_available`](#skill.ai.is_ai_available)()                                | Check if an AI provider is available.                           |

### skill.ai.chat(prompt, , system=None, model=None, temperature=0.0)

Send a chat completion request to the configured AI provider.

Provider resolution order: aisuite -> anthropic -> openai.

Raises ImportError with actionable install instructions if no
provider is available.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

### skill.ai.is_ai_available()

Check if an AI provider is available.

Returns True if any supported provider can be imported and
an API key is configured (or detectable from environment).

* **Return type:**
  [`bool`](https://docs.python.org/3/library/functions.html#bool)

```pycon
>>> isinstance(is_ai_available(), bool)
True
```

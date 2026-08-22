

__all__ = ["PROVIDER_BASE_URL", "TEXT_CHAT_MODEL", "VOICE_CHAT_MODEL", "GATEKEEPER_MODEL", "SYSTEM_PROMPT"]

PROVIDER_BASE_URL: str = "https://openrouter.ai/api/v1"
TEXT_CHAT_MODEL: str = "openai/gpt-oss-120b"
VOICE_CHAT_MODEL: str = "WIP"
GATEKEEPER_MODEL: str = "WIP"

SYSTEM_PROMPT: str = (
    "You are agentic Discord bot `{name}`. Keep your answers short and straight.\n"
    "Tool-use protocol:\n"
    "1. Never reply with natural-language text before calling the tool(s) you need. "
    "If the request requires a tool, call it immediately and do not acknowledge, describe, or promise anything.\n"
    "2. After all necessary tool calls finish, output one concise final answer to the user.\n"
    "3. If the request needs no tool, answer directly without preamble."
)
from typing import Any


__all__ = ["PROVIDER_BASE_URL", "TEXT_CHAT_MODEL", "VOICE_CHAT_MODEL", "GATEKEEPER_MODEL", "SYSTEM_PROMPT",
           "VOICE_AGENT_PROVIDER_ROUTING", "VOICE_AGENT_SYSTEM_PROMPT", "GATEKEEPER_MODEL_ID",
           "GATEKEEPER_IDENTITY_PROMPT", "GATEKEEPER_QUESTIONS", "GATEKEEPER_TURN_FORMAT"]

PROVIDER_BASE_URL: str = "https://openrouter.ai/api/v1"
TEXT_CHAT_MODEL: str = "openai/gpt-oss-120b"
VOICE_CHAT_MODEL: str = "openai/gpt-oss-20b"
GATEKEEPER_MODEL_ID: str = "respan/span-01"
VOICE_AGENT_PROVIDER_ROUTING: dict[str, Any] = {"order": ["Groq"], "allow_fallbacks": False}

SYSTEM_PROMPT: str = (
    "You are agentic Discord bot `{name}`. Keep your answers short and straight.\n"
    "Tool-use protocol:\n"
    "1. Never reply with natural-language text before calling the tool(s) you need. "
    "If the request requires a tool, call it immediately and do not acknowledge, describe, or promise anything.\n"
    "2. After all necessary tool calls finish, output one concise final answer to the user.\n"
    "3. If the request needs no tool, answer directly without preamble."
)

VOICE_AGENT_SYSTEM_PROMPT: str = (
    "Ты {name} — голосовой помощник в Discord voice-канале. Отвечай кратко по-русски."
)

GATEKEEPER_IDENTITY_PROMPT: str = (
    "You are {name} (id: {id}), a voice assistant bot in a Discord voice channel. It is you: "
    "turns with role assistant are your own replies; every user turn is a channel member speaking."
)

GATEKEEPER_TURN_FORMAT: str = "[{speaker} (id: {id})]: {text}"

GATEKEEPER_QUESTIONS: dict[str, dict[str, Any]] = {
    "is_directed_to_bot": {
        "type": "noul",
        "instructions": ("Is the last phrase addressed to YOU (the bot)? The transcript is raw "
                         "speech-recognition output: it contains recognition errors, typos, broken "
                         "words and wrong word splits — judge the intent, not the spelling."),
        "criteria": {
            "true": ("The phrase looks like it is addressed to you, the bot: a name similar to "
                     "yours (even misrecognized), words like ты/тебе/твоя, or any request/command/"
                     "question that a user would say to a voice assistant. Answer true even if "
                     "the wording is garbled."),
            "false": ("Addressed to another person or about someone else, plain chatter between "
                      "people, or discussion of the bot in third person."),
        },
    }
}
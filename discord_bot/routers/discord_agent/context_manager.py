from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

__all__ = ["ContextMessage", "ContextManager"]

class ContextMessage(BaseModel):
    role: str
    text: str
    tokens: int

class ContextManager(BaseModel):
    messages: list[ContextMessage] = Field(default_factory=list)
    compress_threshold: int = 100000
    drop_tokens: int = 20000
    total_tokens: int = 0

    def add_message(self, role: str, text: str, auto_drop: bool = True) -> None:
        """Adds a message and drops old messages if limits are exceeded."""
        token_count = self._calculate_string_tokens(text)
        new_msg = ContextMessage(role=role, text=text, tokens=token_count)
        self.messages.append(new_msg)
        self.total_tokens += token_count
        
        if auto_drop and self.total_tokens > self.compress_threshold:
            self.drop(self.drop_tokens)

    def drop(self, tokens_to_free: int) -> int:
        """Drops oldest messages until target tokens are freed."""
        if tokens_to_free <= 0 or not self.messages:
            return 0
        accumulated_freed: int = 0
        messages_to_remove: int = 0
        for msg in self.messages:
            accumulated_freed += msg.tokens
            messages_to_remove += 1
            if accumulated_freed >= tokens_to_free:
                break
        if messages_to_remove > 0:
            del self.messages[:messages_to_remove]
            self.total_tokens -= accumulated_freed
        return accumulated_freed

    def to_openai_messages(self) -> list[dict[str, Any]]:
        """Converts stored context messages to standard OpenAI structure."""
        return [
            {
                "role": msg.role,
                "content": msg.text
            }
            for msg in self.messages
        ]

    def _calculate_string_tokens(self, text: str) -> int:
        """Approximates token length without heavy external libraries."""
        return max(1, len(text) // 3)
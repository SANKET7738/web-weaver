from typing import Any, Literal


Role = Literal["system", "user", "assistant"]
Message = dict[str, Any]


class ChatHistory:
    """Small helper for OpenAI-compatible multimodal chat histories."""

    def __init__(self, max_history_size: int = 1000):
        self.max_history_size = max_history_size
        self.messages: list[Message] = []

    def add_message(self, role: Role, message: str) -> None:
        message_dict: Message = {
            "role": role,
            "content": [
                {
                    "type": "text",
                    "text": message,
                }
            ],
        }
        self.messages.append(message_dict)
        if len(self.messages) > self.max_history_size:
            self.messages = self.messages[-self.max_history_size :]

    def get_message_history(self) -> list[Message]:
        return self.messages

    def reset_chat_history(self) -> None:
        self.messages = []

import json
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError


ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)
Message = dict[str, Any]


class BaseLLMClient(ABC):
    """Common interface for model clients used by Web Weaver."""

    @abstractmethod
    def prompt_llm(
        self,
        model: str,
        message_history: list[Message] | None = None,
        question: str | None = None,
        base64_images: list[str] | None = None,
        response_model: type[ResponseModelT] | None = None,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        top_p: float | None = None,
        retries: int = 20,
        retry_delay: int = 5,
    ) -> Any:
        """Prompt an LLM with either message history or a single question."""

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Return an exact or estimated token count for text."""

    def validate_response(
        self,
        response_content: str,
        response_model: type[ResponseModelT],
    ) -> tuple[ResponseModelT, dict[str, Any]]:
        """Parse JSON response content and validate it with a Pydantic model."""
        try:
            response_json = json.loads(response_content)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Failed to parse response as JSON: {error}\nResponse: {response_content}"
            ) from error

        try:
            validated_response = response_model.model_validate(response_json)
        except ValidationError as error:
            raise ValueError(
                f"Response validation failed: {error}\nJSON: {response_json}"
            ) from error

        return validated_response, response_json

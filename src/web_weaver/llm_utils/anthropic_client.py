import json
import os
import time
from datetime import datetime
from typing import Any

from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from web_weaver.llm_utils.base import BaseLLMClient, Message, ResponseModelT


class AnthropicClient(BaseLLMClient):
    """Anthropic Messages API client implementing Web Weaver's LLM interface."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float | None = None,
        max_retries: int = 2,
    ):
        load_dotenv()
        resolved_api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or None
        self.client = Anthropic(
            api_key=resolved_api_key,
            timeout=timeout,
            max_retries=max_retries,
        )

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
        messages, system_prompt = self._prepare_messages(
            message_history=message_history,
            question=question,
            base64_images=base64_images,
        )
        attempts = 0
        last_error: Exception | None = None

        while attempts <= retries:
            try:
                request_start_time = datetime.now()
                completion_params = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
                if top_p is not None:
                    completion_params["top_p"] = top_p
                if system_prompt:
                    completion_params["system"] = system_prompt
                if response_model:
                    completion_params.update(self._structured_output_params(response_model))

                completion = self.client.messages.create(**completion_params)
                request_end_time = datetime.now()
                metadata = self._extract_metadata(
                    completion=completion,
                    request_start_time=request_start_time,
                    request_end_time=request_end_time,
                    model=model,
                    messages=messages,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    retries_attempted=attempts,
                    structured_output=response_model is not None,
                )

                if response_model:
                    return self._handle_structured_response(
                        completion=completion,
                        response_model=response_model,
                        metadata=metadata,
                    )

                response_text = self._extract_text(completion)
                metadata["processing"].update(
                    {
                        "raw_response_length": len(response_text),
                        "json_parse_success": False,
                        "extracted_answer_length": len(response_text),
                    }
                )
                return {
                    "response": response_text,
                    "metadata": metadata,
                }
            except Exception as error:
                last_error = error
                attempts += 1
                if attempts <= retries:
                    time.sleep(retry_delay)
                else:
                    raise last_error

    def count_tokens(self, text: str) -> int:
        return int(len(text.split()) * 1.3)

    def _prepare_messages(
        self,
        *,
        message_history: list[Message] | None,
        question: str | None,
        base64_images: list[str] | None,
    ) -> tuple[list[Message], str | None]:
        if message_history:
            return self._convert_message_history(message_history)

        if not question:
            raise ValueError("Either message_history or question must be provided")

        content: list[dict[str, Any]] = [{"type": "text", "text": question}]
        for base64_image in base64_images or []:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": base64_image,
                    },
                }
            )
        return [{"role": "user", "content": content}], None

    def _convert_message_history(
        self, message_history: list[Message]
    ) -> tuple[list[Message], str | None]:
        anthropic_messages: list[Message] = []
        system_parts: list[str] = []

        for message in message_history:
            role = message.get("role")
            content = message.get("content", "")
            if role == "system":
                system_parts.append(self._content_to_text(content))
                continue
            if role not in {"user", "assistant"}:
                raise ValueError(f"Unsupported Anthropic message role: {role}")
            anthropic_messages.append(
                {
                    "role": role,
                    "content": self._convert_content(content),
                }
            )

        system_prompt = "\n\n".join(part for part in system_parts if part) or None
        if not anthropic_messages:
            raise ValueError("Anthropic messages must include at least one user/assistant message")
        return anthropic_messages, system_prompt

    def _convert_content(self, content: Any) -> list[dict[str, Any]]:
        if isinstance(content, str):
            return [{"type": "text", "text": content}]
        if not isinstance(content, list):
            return [{"type": "text", "text": str(content)}]

        converted: list[dict[str, Any]] = []
        for item in content:
            if not isinstance(item, dict):
                converted.append({"type": "text", "text": str(item)})
                continue

            item_type = item.get("type")
            if item_type == "text":
                converted.append({"type": "text", "text": item.get("text", "")})
            elif item_type == "image_url":
                converted.append(self._convert_image_url(item))
            elif item_type == "image":
                converted.append(item)
            else:
                converted.append({"type": "text", "text": str(item)})

        return converted

    def _convert_image_url(self, item: dict[str, Any]) -> dict[str, Any]:
        image_url = item.get("image_url", {}).get("url", "")
        prefix = "data:"
        marker = ";base64,"
        if not image_url.startswith(prefix) or marker not in image_url:
            raise ValueError("AnthropicClient only supports base64 data image URLs")

        media_type = image_url[len(prefix) : image_url.index(marker)]
        data = image_url.split(marker, 1)[1]
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": data,
            },
        }

    def _content_to_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                else:
                    text_parts.append(str(item))
            return "\n".join(text_parts)
        return str(content)

    def _structured_output_params(self, response_model: type[BaseModel]) -> dict[str, Any]:
        tool_name = "emit_structured_response"
        return {
            "tools": [
                {
                    "name": tool_name,
                    "description": "Emit the requested response as structured JSON.",
                    "input_schema": response_model.model_json_schema(),
                }
            ],
            "tool_choice": {"type": "tool", "name": tool_name},
        }

    def _handle_structured_response(
        self,
        *,
        completion: Any,
        response_model: type[ResponseModelT],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        for block in completion.content:
            if getattr(block, "type", None) == "tool_use":
                response_json = block.input
                try:
                    validated_response = response_model.model_validate(response_json)
                except ValidationError as error:
                    raise ValueError(
                        "Structured response validation failed: "
                        f"{error}\nResponse JSON: {json.dumps(response_json, indent=2)}"
                    ) from error
                metadata["processing"].update(
                    {
                        "json_parse_success": True,
                        "raw_response_length": len(json.dumps(response_json)),
                        "extracted_answer_length": len(str(validated_response)),
                    }
                )
                return {
                    "validated_response": validated_response,
                    "raw_json": response_json,
                    "metadata": metadata,
                }

        response_text = self._extract_text(completion)
        validated_response, response_json = self.validate_response(
            response_text,
            response_model,
        )
        metadata["processing"].update(
            {
                "json_parse_success": True,
                "raw_response_length": len(response_text),
                "extracted_answer_length": len(str(validated_response)),
            }
        )
        return {
            "validated_response": validated_response,
            "raw_json": response_json,
            "metadata": metadata,
        }

    def _extract_text(self, completion: Any) -> str:
        text_parts = [
            block.text
            for block in completion.content
            if getattr(block, "type", None) == "text" and getattr(block, "text", None)
        ]
        return "\n".join(text_parts)

    def _extract_metadata(
        self,
        *,
        completion: Any,
        request_start_time: datetime,
        request_end_time: datetime,
        model: str,
        messages: list[Message],
        system_prompt: str | None,
        temperature: float,
        top_p: float,
        max_tokens: int,
        retries_attempted: int,
        structured_output: bool,
    ) -> dict[str, Any]:
        usage = getattr(completion, "usage", None)
        return {
            "client_type": "anthropic",
            "tokens": {
                "prompt_tokens": getattr(usage, "input_tokens", None),
                "completion_tokens": getattr(usage, "output_tokens", None),
                "total_tokens": (
                    getattr(usage, "input_tokens", 0) + getattr(usage, "output_tokens", 0)
                    if usage
                    else None
                ),
                "available": usage is not None,
            },
            "model_info": {
                "model_used": getattr(completion, "model", model),
                "response_id": getattr(completion, "id", None),
                "stop_reason": getattr(completion, "stop_reason", None),
                "request_id": getattr(completion, "_request_id", None),
            },
            "timing": {
                "request_start": request_start_time.isoformat(),
                "response_end": request_end_time.isoformat(),
                "duration_ms": int(
                    (request_end_time - request_start_time).total_seconds() * 1000
                ),
            },
            "request_config": {
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens,
                "retries_attempted": retries_attempted,
                "structured_output": structured_output,
            },
            "processing": {
                "system_prompt_tokens": self.count_tokens(system_prompt or ""),
                "message_count": len(messages),
            },
        }

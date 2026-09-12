from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.config import Settings
from app.services.groq_service import (
    GroqConfigurationError,
    GroqProviderError,
    GroqResponseError,
    GroqService,
)


class StructuredGreeting(BaseModel):
    message: str
    confidence: float


class FakeCompletions:
    def __init__(self, content: str | None = None, error: Exception | None = None) -> None:
        self.content = content
        self.error = error
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self.content),
                )
            ]
        )


class FakeGroqClient:
    def __init__(self, completions: FakeCompletions) -> None:
        self.chat = SimpleNamespace(completions=completions)


def test_structured_response_uses_schema_and_validates_with_pydantic() -> None:
    completions = FakeCompletions('{"message":"Complaint captured.","confidence":0.9}')
    service = GroqService(
        client=FakeGroqClient(completions),
        settings=Settings(groq_model="test-model"),
    )

    result = service.generate_structured_response(
        "Capture the supplied complaint details.",
        StructuredGreeting,
    )

    assert result.message == "Complaint captured."
    assert result.confidence == pytest.approx(0.9)
    request = completions.calls[0]
    assert request["model"] == "test-model"
    assert request["temperature"] == 0.0
    response_format = request["response_format"]
    assert isinstance(response_format, dict)
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "StructuredGreeting"
    assert response_format["json_schema"]["strict"] is False
    assert response_format["json_schema"]["schema"] == StructuredGreeting.model_json_schema()


def test_custom_system_prompt_is_sent_without_changing_user_prompt() -> None:
    completions = FakeCompletions('{"message":"ok","confidence":1}')
    service = GroqService(
        client=FakeGroqClient(completions),
        settings=Settings(groq_model="test-model"),
    )

    service.complete(
        "Use the supplied text only.",
        StructuredGreeting,
        system_prompt="Return only validated JSON.",
    )

    messages = completions.calls[0]["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"].startswith("Return only validated JSON.")
    assert "never invent factual complaint information" in messages[0]["content"]
    assert messages[1] == {
        "role": "user",
        "content": "Use the supplied text only.",
    }


def test_missing_model_is_rejected_before_a_provider_call() -> None:
    with pytest.raises(GroqConfigurationError, match="GROQ_MODEL"):
        GroqService(client=FakeGroqClient(FakeCompletions()), settings=Settings())


def test_missing_api_key_is_rejected_when_constructing_real_client() -> None:
    with pytest.raises(GroqConfigurationError, match="GROQ_API_KEY"):
        GroqService(settings=Settings(groq_model="test-model"))


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("not-json", "invalid JSON"),
        ('{"message":"missing confidence"}', "did not validate"),
        ('["not", "an", "object"]', "must be a JSON object"),
    ],
)
def test_invalid_provider_payloads_raise_response_error(content: str, message: str) -> None:
    service = GroqService(
        client=FakeGroqClient(FakeCompletions(content)),
        settings=Settings(groq_model="test-model"),
    )

    with pytest.raises(GroqResponseError, match=message):
        service.complete("Return a greeting.", StructuredGreeting)


def test_provider_failure_is_wrapped_without_exposing_provider_details() -> None:
    completions = FakeCompletions(error=RuntimeError("provider failure"))
    service = GroqService(
        client=FakeGroqClient(completions),
        settings=Settings(groq_model="test-model"),
    )

    with pytest.raises(GroqProviderError, match="Unable to obtain") as error:
        service.complete("Return a greeting.", StructuredGreeting)

    assert "provider failure" not in str(error.value)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"user_prompt": ""},
        {"user_prompt": "prompt", "temperature": -0.1},
        {"user_prompt": "prompt", "temperature": 2.1},
    ],
)
def test_invalid_request_parameters_are_rejected(kwargs: dict[str, object]) -> None:
    service = GroqService(
        client=FakeGroqClient(FakeCompletions('{"message":"ok","confidence":1}')),
        settings=Settings(groq_model="test-model"),
    )

    with pytest.raises((ValueError, TypeError)):
        service.generate_structured_response(
            kwargs.pop("user_prompt"),
            StructuredGreeting,
            **kwargs,
        )

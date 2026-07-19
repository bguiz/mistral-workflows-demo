"""Unit tests for the minimal hello-world workflow."""

import asyncio
from types import SimpleNamespace

from workflows import hello


def test_hello_input_defaults_to_world() -> None:
    assert hello.HelloInput().name == "Bguiz"


def test_hello_input_accepts_custom_name() -> None:
    input_model = hello.HelloInput(name="Ada")

    assert input_model.model_dump() == {"name": "Ada"}


def test_greet_returns_welcome_message() -> None:
    result = asyncio.run(hello.greet("Ada"))

    assert result == "Hello, Ada! Welcome to Mistral Workflows."


def test_greet_is_registered_as_activity() -> None:
    activity_definition = getattr(hello.greet, "__temporal_activity_definition")

    assert activity_definition.name == "greet"
    assert activity_definition.is_async is True
    assert activity_definition.arg_types == [str]
    assert activity_definition.ret_type is str


def test_translate_greeting_calls_mistral_chat_with_random_language(
    monkeypatch,
) -> None:
    selected_language_options = []
    captured_requests = []

    def fake_choice(language_options):
        selected_language_options.append(language_options)
        return "ja-JP"

    async def fake_chat_complete(request):
        captured_requests.append(request)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="こんにちは、Adaさん！Mistral Workflowsへようこそ。"
                    )
                )
            ]
        )

    monkeypatch.setattr(hello.random, "choice", fake_choice)
    monkeypatch.setattr(hello, "mistralai_chat_complete", fake_chat_complete)

    result = asyncio.run(hello.translate_greeting("Hello, Ada!"))

    assert result == "こんにちは、Adaさん！Mistral Workflowsへようこそ。"
    assert selected_language_options == [hello.TRANSLATION_LANGUAGES]
    assert len(captured_requests) == 1
    assert captured_requests[0].model == hello._MODEL
    assert "ja-JP" in captured_requests[0].messages[0].content
    assert "Hello, Ada!" in captured_requests[0].messages[0].content


def test_translate_greeting_is_registered_as_activity() -> None:
    activity_definition = getattr(
        hello.translate_greeting,
        "__temporal_activity_definition",
    )

    assert activity_definition.name == "translate_greeting"
    assert activity_definition.is_async is True
    assert activity_definition.arg_types == [str]
    assert activity_definition.ret_type is str


def test_hello_workflow_metadata_matches_definition() -> None:
    workflow_spec = getattr(hello.HelloWorkflow, "__workflows_workflow_def")

    assert workflow_spec.name == "hello-world"
    assert workflow_spec.display_name == "Hello World"
    assert workflow_spec.description == "A minimal hello-world workflow."
    assert workflow_spec.input_schema["properties"]["name"]["default"] == "Bguiz"


def test_hello_workflow_runs_greet_activity(monkeypatch) -> None:
    calls = []

    async def fake_greet(name: str) -> str:
        calls.append(("greet", name))
        return f"Hello, {name}!"

    async def fake_translate_greeting(greeting: str) -> str:
        calls.append(("translate_greeting", greeting))
        return f"[translated] {greeting}"

    monkeypatch.setattr(hello, "greet", fake_greet)
    monkeypatch.setattr(hello, "translate_greeting", fake_translate_greeting)

    result = asyncio.run(hello.HelloWorkflow().run(hello.HelloInput(name="Ada")))

    assert calls == [
        ("greet", "Ada"),
        ("translate_greeting", "Hello, Ada!"),
    ]
    assert result == {"result": "[translated] Hello, Ada!"}

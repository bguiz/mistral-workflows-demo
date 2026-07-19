"""Minimal example workflow — edit this file or create new ones."""

import random
from datetime import timedelta

import mistralai.workflows as workflows
from mistralai.client import models as mistralai_models
from mistralai.workflows.plugins.mistralai import mistralai_chat_complete
from pydantic import BaseModel

_MODEL = "mistral-small-latest"
TRANSLATION_LANGUAGES = ("zh-CN", "ms-MY", "ta-IN", "ja-JP", "ko-KR", "vi-VN", "th-TH", "my-MM", "lo-LA" "km-KH")


class HelloInput(BaseModel):
    name: str = "Bguiz"


@workflows.activity()
async def greet(name: str) -> str:
    """A simple activity that returns a greeting."""
    return f"Hello, {name}! Welcome to Mistral Workflows."


@workflows.activity(
    retry_policy_max_attempts=2,
    retry_policy_backoff_coefficient=2.0,
    start_to_close_timeout=timedelta(seconds=10),
)
async def translate_greeting(greeting: str) -> str:
    """Translate a greeting into one randomly selected supported language."""
    language = random.choice(TRANSLATION_LANGUAGES)
    translation_prompt = (
        "You are a professional translator.\n"
        f"Translate this greeting into language: {language}.\n"
        "Return only the translated greeting text, with no extra commentary.\n"
        f"Greeting to translate:\n\n{greeting}"
    )
    request = mistralai_models.ChatCompletionRequest(
        model=_MODEL,
        messages=[mistralai_models.UserMessage(content=translation_prompt)],
    )
    response = await mistralai_chat_complete(request)
    message = response.choices[0].message
    if message is None:
        raise ValueError("Mistral returned no translated greeting message.")

    translated_greeting = message.content
    if not isinstance(translated_greeting, str) or not translated_greeting.strip():
        raise ValueError("Mistral returned an empty translated greeting.")

    return translated_greeting.strip()


@workflows.workflow.define(
    name="hello-world",
    workflow_display_name="Hello World",
    workflow_description="A minimal hello-world workflow.",
)
class HelloWorkflow:
    @workflows.workflow.entrypoint
    async def run(self, input: HelloInput) -> str:
        greeting = await greet(input.name)
        return await translate_greeting(greeting)

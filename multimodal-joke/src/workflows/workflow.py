"""Multimodal joke workflow."""

import mistralai.workflows as workflows
from mistralai.workflows import workflow

# Activities are imported via imports_passed_through so the Temporal sandbox
# does not try to re-import mistralai.client (which imports httpx, which
# triggers a sandbox restriction on urllib.request.Request.__mro_entries__).
# The activity functions themselves are safe to call from workflow code —
# the decorator intercepts the call and dispatches it via Temporal's task
# queue rather than executing the function body in the workflow thread.
with workflow.unsafe.imports_passed_through():
    from .activities import (
        greet,
        joke,
        joke_image,
        translate_content,
        text_to_speech,
    )
    from .models import (
        HelloInput,
        TranslationOutput,
        WorkflowResultOutput,
    )

@workflows.workflow.define(
    name="multimodal-joke",
    workflow_display_name="Multimodal Joke Demo",
    workflow_description="Demonstrates text, translation, text-to-speech, and image generation.",
)
class HelloWorkflow:
    @workflows.workflow.entrypoint
    async def run(self, input: HelloInput) -> WorkflowResultOutput:
        # workflow step 1 - greeting
        greeting = await greet(input.name)

        # workflow step 2 - joke text
        joke_object = await joke(input.name)

        # workflow step 3 - translation, with branching
        target_lang = input.language.strip().lower()
        if target_lang in ["en", "eng", "english"]:
            translation_result = TranslationOutput(
                greeting=greeting,
                joke=joke_object
            )
        else:
            # Only execute the translation if there is a need: non-English language
            translation_result = await translate_content(
                greeting=greeting,
                joke_setup=joke_object.setup,
                joke_punchline=joke_object.punchline,
                language=input.language
            )

        # workflow step 3 - text-to-speech
        tts_input_text = f"{translation_result.joke.setup} ... {translation_result.joke.punchline}"
        speech_object = await text_to_speech(text=tts_input_text)

        # workflow step 4 - image generation
        joke_image_object = await joke_image(translation_result.joke, input.language)

        # assemble combined result
        workflow_result = WorkflowResultOutput(
            greeting=translation_result.greeting,
            joke=translation_result.joke.model_dump(),
            speech=speech_object.model_dump(),
            images=joke_image_object.model_dump(),
        )

        return workflow_result

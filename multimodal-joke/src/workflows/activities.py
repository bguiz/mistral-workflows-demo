from __future__ import annotations

import json
import base64
import random
import io
import os
from typing import Any
from datetime import datetime, timedelta, timezone
from httpx import HTTPStatusError
from dotenv import load_dotenv

import cloudinary
import cloudinary.uploader
import mistralai.workflows as workflows
from mistralai.client import Mistral
from mistralai.client import models as mistralai_models
from mistralai.workflows.plugins.mistralai.activities import (
    chat_parse_to_model,
)
from mistralai.workflows.plugins.mistralai.utils import (
    get_mistral_client,
)
from mistralai.workflows.core.dependencies import Depends
from mistralai.workflows.plugins.mistralai import (
  mistralai_chat_complete,
  
)

from .models import (
    JokeOutput,
    ImageOutput,
    TranslationOutput,
    SpeechOutput,
)

load_dotenv()

_MODEL = "mistral-small-latest"
_IMAGE_MODEL = "mistral-large-latest"
_TTS_MODEL = "voxtral-mini-tts-2603"

cloudinary.config( 
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"), 
    api_key=os.getenv("CLOUDINARY_API_KEY"), 
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

@workflows.activity()
async def greet(name: str) -> str:
    """Simple greeting."""
    return f"Hello {name}, time for some jokes!"

@workflows.activity(
    retry_policy_max_attempts=2,
    retry_policy_backoff_coefficient=2.0,
    start_to_close_timeout=timedelta(seconds=10),
  )
async def joke(name: str) -> JokeOutput:
    """Send the user a personalised joke."""
    joke_prompt = (
        "You are professional comedian.\n"
        f"Tell a joke that involves 'Le Chaton Gros' and the user, named '{name}'.\n"
        "Return JSON matching the Joke schema: setup (str), punchline (str)"
    )
    request = mistralai_models.ChatCompletionRequest(
        model=_MODEL,
        messages=[mistralai_models.UserMessage(content=joke_prompt)],
    )
    result = await chat_parse_to_model(JokeOutput, request)
    return result

@workflows.activity(
    name="translate_content",
    retry_policy_max_attempts=1,
    retry_policy_backoff_coefficient=2.0,
    start_to_close_timeout=timedelta(seconds=15),
)
async def translate_content(greeting: str, joke_setup: str, joke_punchline: str, language: str) -> TranslationOutput:
    """Translate both greeting and joke into the target language."""
    translation_prompt = (
        f"You are a professional translator. Translate the following content into language: {language}.\n"
        "Keep the exact same tone and humour.\n\n"
        f"Greeting to translate: {greeting}\n"
        f"Joke Setup to translate: {joke_setup}\n"
        f"Joke Punchline to translate: {joke_punchline}\n\n"
        "Return JSON matching the TranslationOutput schema:\n"
        "- greeting (str)\n"
        "- joke (object)\n  - setup (str)\n  - punchline (str)"
    )
    
    req = mistralai_models.ChatCompletionRequest(
        model=_MODEL,
        messages=[mistralai_models.UserMessage(content=translation_prompt)],
    )
    
    result = await chat_parse_to_model(TranslationOutput, req)
    print("Translation result:")
    print(result)
    return result

def mistral_response_debug(resp):
    """Pretty-print model responses for debugging pruposes."""
    print("\n" + "="*40 + " MISTRAL RESPONSE DEBUG " + "="*40)
    try:
        readable_json = resp.model_dump_json(indent=2)
        print(readable_json)
    except Exception as serialize_err:
        print(f"Could not dump as JSON. Raw object: {resp}")
        print(f"Serialization error: {serialize_err}")
    print("="*104 + "\n")

@workflows.activity(
    retry_policy_max_attempts=1,
    retry_policy_backoff_coefficient=2.0,
    start_to_close_timeout=timedelta(seconds=300),
)
async def joke_image(
    joke: JokeOutput,
    language: str,
  ) -> ImageOutput:
    """Generates comic based on the joke."""
    
    image_prompt = (
        "Create an image prompt for a funny comic-book style line illustration, based on this joke.\n"
        f"Setup: {joke.setup}\n"
        f"Punchline: {joke.punchline}\n\n"
        "Describe the visual elements clearly, focusing on humour.\n"
        f"Minimise text. If any, specify language explicitly, e.g. Text must be in {language}, and in string quotes."
        "Use only 2 panels. Only generate 1 image file with both panels."
    )
    
    image_prompt_req = mistralai_models.ChatCompletionRequest(
        model=_MODEL,
        messages=[mistralai_models.UserMessage(content=image_prompt)],
    )

    image_prompt_resp = await mistralai_chat_complete(image_prompt_req)
    image_description = image_prompt_resp.choices[0].message.content
    print(image_description)

    image_file_req = mistralai_models.ChatCompletionRequest(
        model=_IMAGE_MODEL,
        messages=[mistralai_models.UserMessage(content=image_description)],
        tools=[{"type": "image_generation"}],
        # tool_choice="any",
        completion_args={
            "temperature": 0.3,
            "top_p": 0.95,
        }
    )

    try:
        image_file_resp = await mistralai_chat_complete(image_file_req)
    except HTTPStatusError as http_err:
        print(f"HTTP Error occurred: {http_err.response.status_code}")
        print(f"HTTP Error details: {http_err.response.text}")
        raise http_err

    mistral_response_debug(image_file_resp)

    # fairly complex parsing necessary to extract image URLs from responses 
    collected_image_urls = []
    for choice in image_file_resp.choices:
        if not choice or not hasattr(choice, 'messages') or not choice.messages:
            if hasattr(choice, 'message') and choice.message:
                messages_to_scan = [choice.message]
            else:
                continue
        else:
            messages_to_scan = choice.messages

        for message in messages_to_scan:
            if getattr(message, 'role', None) == "tool" and getattr(message, 'content', None):
                raw_content = message.content
                
                if isinstance(raw_content, str):
                    try:
                        parsed_content = json.loads(raw_content)
                    except json.JSONDecodeError:
                        continue
                else:
                    parsed_content = raw_content
                    
                if isinstance(parsed_content, dict):
                    possible_url = parsed_content.get("url")
                    if possible_url and possible_url not in collected_image_urls:
                        collected_image_urls.append(possible_url)

    if not collected_image_urls:
        raise ValueError("No valid image 'url' fields found inside message tool payloads.")

    return ImageOutput(
        image_description=image_description,
        image_urls=collected_image_urls,
    )

@workflows.activity(
    retry_policy_max_attempts=1,
    retry_policy_backoff_coefficient=2.0,
    start_to_close_timeout=timedelta(seconds=300),
)
async def text_to_speech(
    text: str,
    mistral_client: Mistral = Depends(get_mistral_client),
) -> SpeechOutput:
    # NOTE that mistralai_models.ChatCompletionRequest does not work for TTS models
    # so need to ditch the wrapper, and call the lower level method
    voices_resp = await mistral_client.audio.voices.list_async()
    mistral_response_debug(voices_resp)
    available_voices = voices_resp.data if hasattr(voices_resp, 'data') else voices_resp.items
    if not available_voices:
        raise ValueError("No voices found in your Mistral account!")
    selected_voice = random.choice(available_voices)

    tts_resp = await mistral_client.audio.speech.complete_async(
        model=_TTS_MODEL,              
        input=text, 
        voice_id=selected_voice.id,
        response_format="mp3",
    )
    # mistral_response_debug(tts_resp)
    tts_audio = base64.b64decode(tts_resp.audio_data)

    tts_audio_filename = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('-', '_').replace('T', '_').replace(':', '_').replace('+', '_')
    print(tts_audio_filename)
    upload_result = cloudinary.uploader.upload(
        io.BytesIO(tts_audio),
        # NOTE cloudinary classifies audio files as 'video' block type
        resource_type="video",
        public_id=tts_audio_filename,
        format="mp3",
    )
    audio_url = upload_result.get("secure_url")

    result = SpeechOutput(audio=audio_url)
    return result

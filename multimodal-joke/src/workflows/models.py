
from __future__ import annotations

from pydantic import BaseModel, Field

class HelloInput(BaseModel):
    name: str = "Your Name"
    language: str = "en"

class JokeOutput(BaseModel):
    """Output of Joke."""
    setup: str
    punchline: str

class TranslationOutput(BaseModel):
    greeting: str
    joke: JokeOutput

class ImageOutput(BaseModel):
    image_description: str
    image_urls: list[str]

class SpeechOutput(BaseModel):
    audio: str

class WorkflowResultOutput(BaseModel):
    greeting: str
    joke: JokeOutput
    speech: SpeechOutput
    images: ImageOutput

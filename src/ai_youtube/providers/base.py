from pathlib import Path
from typing import Protocol, TypeVar

from pydantic import BaseModel


OutputModel = TypeVar("OutputModel", bound=BaseModel)


class TextProvider(Protocol):
    def generate_structured(
        self, system_prompt: str, user_prompt: str, output_type: type[OutputModel]
    ) -> OutputModel: ...


class SpeechProvider(Protocol):
    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str,
        instructions: str,
        response_format: str,
        speed: float,
    ) -> Path: ...


class VisualProvider(Protocol):
    def generate(
        self,
        prompt: str,
        output_path: Path,
        width: int,
        height: int,
        label: str = "",
    ) -> Path: ...

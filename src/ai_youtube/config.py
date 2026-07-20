from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    openai_api_key: Optional[str] = None
    openai_text_model: Optional[str] = None
    openai_tts_model: Optional[str] = None
    openai_tts_voice: Optional[str] = None
    openai_image_model: Optional[str] = None
    pollo_api_key: Optional[str] = None
    youtube_client_secrets_file: Path = Path("secrets/youtube_client_secret.json")
    youtube_token_file: Path = Path("secrets/youtube_token.json")
    data_dir: Path = Path("data")
    storage_dir: Path = Path("storage")
    log_dir: Path = Path("logs")

    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_app_config() -> dict[str, Any]:
    return load_yaml(PROJECT_ROOT / "config" / "app.yaml")


def load_channel_config(channel_id: str) -> dict[str, Any]:
    path = PROJECT_ROOT / "config" / "channels" / f"{channel_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Channel config not found: {path}")
    return load_yaml(path)


def require_openai_api_key(settings: Settings) -> str:
    key = (settings.openai_api_key or "").strip()
    if not key:
        raise ValueError(
            "OPENAI_API_KEY가 없습니다. .env.example을 .env로 복사한 뒤 API 키를 입력하세요."
        )
    return key

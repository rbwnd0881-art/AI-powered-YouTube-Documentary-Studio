import json
import shutil
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ai_youtube.config import (
    Settings,
    load_app_config,
    load_channel_config,
    require_openai_api_key,
)
from ai_youtube.pipeline.orchestrator import create_job_plan
from ai_youtube.pipeline.stages.edit import YoutubeEditService
from ai_youtube.pipeline.stages.publish import ThumbnailRenderer, YoutubePublishingService
from ai_youtube.pipeline.stages.scenes import YoutubeSceneService
from ai_youtube.pipeline.stages.script import YoutubeScriptService
from ai_youtube.pipeline.stages.voice import YoutubeVoiceService
from ai_youtube.providers.openai_provider import (
    OpenAISpeechProvider,
    OpenAITextProvider,
    ScriptGenerationError,
    SpeechGenerationError,
)
from ai_youtube.providers.ffmpeg_provider import FFmpegEditor, VideoEditingError
from ai_youtube.providers.youtube_provider import (
    YoutubeOAuth,
    YoutubeUploader,
    YoutubeUploadError,
)

app = typer.Typer(help="AI YouTube automation CLI")
console = Console()
error_console = Console(stderr=True)


@app.command()
def doctor() -> None:
    """Check that the local project configuration can be loaded."""
    settings = Settings()
    config = load_app_config()
    console.print(f"[green]OK[/green] {config['app']['name']} ({settings.app_env})")
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        console.print("[green]OK[/green] FFmpeg")
    else:
        console.print("[yellow]NOTICE[/yellow] FFmpeg가 없습니다: brew install ffmpeg")


@app.command()
def pipeline(
    channel: str = typer.Option("channel_001", help="Channel config ID"),
    idea: str = typer.Option(..., help="Video idea"),
) -> None:
    """Create an execution plan without calling external APIs."""
    channel_config = load_channel_config(channel)
    plan = create_job_plan(channel_config, idea)
    console.print_json(data=plan)


@app.command("generate-script")
def generate_script(
    topic: str = typer.Option(..., "--topic", "-t", help="영상 주제"),
    channel: str = typer.Option("channel_001", help="채널 설정 ID"),
    output: Optional[Path] = typer.Option(None, help="저장할 JSON 파일 경로"),
) -> None:
    """Generate a reusable structured YouTube script from a topic."""
    try:
        settings = Settings()
        app_config = load_app_config()
        channel_config = load_channel_config(channel)
        script_config = app_config["script_generation"]

        provider = OpenAITextProvider(
            api_key=require_openai_api_key(settings),
            model=settings.openai_text_model or script_config["model"],
            timeout_seconds=float(script_config["timeout_seconds"]),
            max_retries=int(script_config["max_retries"]),
        )
        script = YoutubeScriptService(provider).generate(topic, channel_config)
        result = script.model_dump(mode="json")

        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            console.print(f"[green]대본 저장 완료:[/green] {output}")
        else:
            console.print_json(data=result)
    except (ValueError, FileNotFoundError, ScriptGenerationError, KeyError) as exc:
        error_console.print(f"[red]대본 생성 실패:[/red] {exc}")
        raise typer.Exit(code=1)


@app.command("generate-scenes")
def generate_scenes(
    script: Path = typer.Option(..., help="대본 JSON 파일"),
    output: Path = typer.Option(..., help="저장할 Scene JSON 파일"),
    channel: str = typer.Option("channel_001", help="채널 설정 ID"),
) -> None:
    """Create production-ready scenes with image, video, and subtitle prompts."""
    try:
        settings = Settings()
        app_config = load_app_config()
        channel_config = load_channel_config(channel)
        scene_config = app_config["scene_generation"]

        provider = OpenAITextProvider(
            api_key=require_openai_api_key(settings),
            model=settings.openai_text_model or scene_config["model"],
            timeout_seconds=float(scene_config["timeout_seconds"]),
            max_retries=int(scene_config["max_retries"]),
        )
        service = YoutubeSceneService(provider)
        parsed_script = service.load_script(script)
        scene_plan = service.generate(parsed_script, channel_config, scene_config)

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(scene_plan.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        console.print(f"[green]Scene 저장 완료:[/green] {output}")
        console.print(f"생성된 Scene: {len(scene_plan.scenes)}개")
    except (ValueError, FileNotFoundError, KeyError, ScriptGenerationError) as exc:
        error_console.print(f"[red]Scene 생성 실패:[/red] {exc}")
        raise typer.Exit(code=1)


@app.command("generate-voice")
def generate_voice(
    script: Path = typer.Option(..., help="대본 JSON 파일"),
    output: Path = typer.Option(..., help="저장할 음성 파일"),
    channel: str = typer.Option("channel_001", help="채널 설정 ID"),
    voice: Optional[str] = typer.Option(None, help="기본 음성을 일시적으로 변경"),
) -> None:
    """Convert a generated script JSON file into AI narration."""
    try:
        settings = Settings()
        app_config = load_app_config()
        channel_config = load_channel_config(channel)
        speech_config = app_config["speech_generation"]

        provider = OpenAISpeechProvider(
            api_key=require_openai_api_key(settings),
            model=settings.openai_tts_model or speech_config["model"],
            timeout_seconds=float(speech_config["timeout_seconds"]),
            max_retries=int(speech_config["max_retries"]),
        )
        service = YoutubeVoiceService(provider)
        parsed_script = service.load_script(script)
        result = service.generate(
            script=parsed_script,
            output_path=output,
            channel_config=channel_config,
            speech_config={
                **speech_config,
                "voice": settings.openai_tts_voice or speech_config["voice"],
            },
            voice_override=voice,
        )
        console.print(f"[green]AI 음성 저장 완료:[/green] {result}")
        console.print("[yellow]공개 시 AI 생성 음성임을 시청자에게 고지하세요.[/yellow]")
    except (
        ValueError,
        FileNotFoundError,
        KeyError,
        SpeechGenerationError,
    ) as exc:
        error_console.print(f"[red]음성 생성 실패:[/red] {exc}")
        raise typer.Exit(code=1)


@app.command("edit-video")
def edit_video(
    scenes: Path = typer.Option(..., help="Scene JSON 파일"),
    manifest: Path = typer.Option(..., help="미디어 매니페스트 JSON 파일"),
    output: Path = typer.Option(..., help="저장할 MP4 파일"),
) -> None:
    """Render subtitles, narration, BGM, SFX, and transitions with FFmpeg."""
    try:
        app_config = load_app_config()
        scene_plan = YoutubeEditService.load_scene_plan(scenes)
        edit_manifest = YoutubeEditService.load_manifest(manifest)
        result = FFmpegEditor(app_config["editing"]).render(
            scene_plan=scene_plan,
            manifest=edit_manifest,
            output_path=output,
        )
        console.print(f"[green]영상 편집 완료:[/green] {result}")
    except (ValueError, FileNotFoundError, KeyError, VideoEditingError) as exc:
        error_console.print(f"[red]영상 편집 실패:[/red] {exc}")
        raise typer.Exit(code=1)


@app.command("prepare-publish")
def prepare_publish(
    script: Path = typer.Option(..., help="대본 JSON 파일"),
    background: Path = typer.Option(..., help="썸네일 배경 이미지"),
    metadata_output: Path = typer.Option(..., help="저장할 메타데이터 JSON"),
    thumbnail_output: Path = typer.Option(..., help="저장할 JPG 썸네일"),
    channel: str = typer.Option("channel_001", help="채널 설정 ID"),
) -> None:
    """Generate title, description, tags, and a deterministic thumbnail."""
    try:
        settings = Settings()
        app_config = load_app_config()
        channel_config = load_channel_config(channel)
        publish_config = app_config["publishing_generation"]
        provider = OpenAITextProvider(
            api_key=require_openai_api_key(settings),
            model=settings.openai_text_model or publish_config["model"],
            timeout_seconds=float(publish_config["timeout_seconds"]),
            max_retries=int(publish_config["max_retries"]),
        )
        service = YoutubePublishingService(provider)
        parsed_script = service.load_script(script)
        metadata = service.generate_metadata(
            parsed_script, channel_config, publish_config
        )
        thumbnail = ThumbnailRenderer(publish_config["thumbnail"]).render(
            background_path=background,
            text=metadata.thumbnail_text,
            output_path=thumbnail_output,
            brand_config=channel_config["brand"],
        )
        metadata_output.parent.mkdir(parents=True, exist_ok=True)
        metadata_output.write_text(
            json.dumps(metadata.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        console.print(f"[green]메타데이터 저장 완료:[/green] {metadata_output}")
        console.print(f"[green]썸네일 저장 완료:[/green] {thumbnail}")
    except (
        ValueError,
        FileNotFoundError,
        KeyError,
        ScriptGenerationError,
        OSError,
    ) as exc:
        error_console.print(f"[red]게시 자료 생성 실패:[/red] {exc}")
        raise typer.Exit(code=1)


@app.command("upload-youtube")
def upload_youtube(
    video: Path = typer.Option(..., help="업로드할 MP4 영상"),
    metadata: Path = typer.Option(..., help="게시 메타데이터 JSON"),
    thumbnail: Path = typer.Option(..., help="업로드할 JPG 썸네일"),
    channel: str = typer.Option("channel_001", help="채널 설정 ID"),
    privacy: Optional[str] = typer.Option(None, help="private, unlisted 또는 public"),
    allow_public: bool = typer.Option(
        False, help="public 업로드를 명시적으로 허용"
    ),
) -> None:
    """Upload a video and custom thumbnail through the YouTube Data API."""
    try:
        settings = Settings()
        app_config = load_app_config()
        channel_config = load_channel_config(channel)
        upload_config = app_config["youtube_upload"]
        selected_privacy = privacy or channel_config["publishing"].get(
            "privacy", upload_config["privacy"]
        )
        if selected_privacy == "public" and not allow_public:
            raise ValueError(
                "공개 업로드에는 --allow-public 옵션이 필요합니다. 먼저 private를 권장합니다."
            )

        parsed_metadata = YoutubePublishingService.load_metadata(metadata)
        service = YoutubeOAuth(
            client_secrets_path=settings.youtube_client_secrets_file,
            token_path=settings.youtube_token_file,
            scope=str(upload_config["oauth_scope"]),
        ).build_service()
        result = YoutubeUploader(service).upload(
            video_path=video,
            thumbnail_path=thumbnail,
            metadata=parsed_metadata,
            category_id=str(channel_config["publishing"]["category_id"]),
            privacy=str(selected_privacy),
            notify_subscribers=bool(upload_config["notify_subscribers"]),
        )
        console.print(f"[green]YouTube 업로드 완료:[/green] {result.url}")
        console.print(f"공개 범위: {result.privacy}")
    except (
        ValueError,
        FileNotFoundError,
        KeyError,
        YoutubeUploadError,
    ) as exc:
        error_console.print(f"[red]YouTube 업로드 실패:[/red] {exc}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()

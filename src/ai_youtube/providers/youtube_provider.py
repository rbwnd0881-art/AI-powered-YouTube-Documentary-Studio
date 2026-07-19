"""YouTube Data API upload adapter with reusable OAuth credentials."""

import json
from pathlib import Path
from typing import Any, Callable, Optional

from ai_youtube.domain.models import PublishingMetadata, YoutubeUploadResult


YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"


class YoutubeUploadError(RuntimeError):
    """Raised when YouTube authorization or upload fails."""


class YoutubeOAuth:
    def __init__(
        self,
        client_secrets_path: Path,
        token_path: Path,
        scope: str = YOUTUBE_UPLOAD_SCOPE,
    ) -> None:
        self.client_secrets_path = client_secrets_path.resolve()
        self.token_path = token_path.resolve()
        self.scope = scope

    def build_service(self) -> Any:
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise YoutubeUploadError(
                "YouTube 패키지가 없습니다. '.venv/bin/python -m pip install "
                "-r requirements-youtube.txt'를 실행하세요."
            ) from exc

        if not self.client_secrets_path.is_file():
            raise FileNotFoundError(
                f"YouTube OAuth 클라이언트 파일이 없습니다: {self.client_secrets_path}"
            )

        credentials: Optional[Any] = None
        if self.token_path.is_file():
            credentials = Credentials.from_authorized_user_file(
                str(self.token_path), [self.scope]
            )
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        if not credentials or not credentials.valid:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.client_secrets_path), [self.scope]
            )
            credentials = flow.run_local_server(port=0, access_type="offline")

        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(credentials.to_json(), encoding="utf-8")
        return build("youtube", "v3", credentials=credentials, cache_discovery=False)


class YoutubeUploader:
    def __init__(
        self,
        service: Any,
        media_upload_factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.service = service
        self.media_upload_factory = media_upload_factory or self._default_media_upload

    @staticmethod
    def _default_media_upload(path: str, **kwargs: Any) -> Any:
        try:
            from googleapiclient.http import MediaFileUpload
        except ImportError as exc:
            raise YoutubeUploadError(
                "google-api-python-client가 설치되지 않았습니다."
            ) from exc
        return MediaFileUpload(path, **kwargs)

    def upload(
        self,
        video_path: Path,
        thumbnail_path: Path,
        metadata: PublishingMetadata,
        category_id: str,
        privacy: str = "private",
        notify_subscribers: bool = False,
    ) -> YoutubeUploadResult:
        if privacy not in {"private", "unlisted", "public"}:
            raise ValueError(f"지원하지 않는 공개 범위입니다: {privacy}")
        if not video_path.is_file():
            raise FileNotFoundError(f"업로드할 영상이 없습니다: {video_path}")
        if not thumbnail_path.is_file():
            raise FileNotFoundError(f"업로드할 썸네일이 없습니다: {thumbnail_path}")
        if thumbnail_path.stat().st_size > 2_000_000:
            raise ValueError("썸네일 파일은 2MB 이하여야 합니다.")

        body = {
            "snippet": {
                "title": metadata.title,
                "description": metadata.description,
                "tags": metadata.tags,
                "categoryId": str(category_id),
            },
            "status": {"privacyStatus": privacy},
        }
        video_media = self.media_upload_factory(
            str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4"
        )
        try:
            request = self.service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=video_media,
                notifySubscribers=notify_subscribers,
            )
            response = None
            while response is None:
                _, response = request.next_chunk()
            video_id = str(response["id"])
        except Exception as exc:
            details = getattr(exc, "content", None)
            if isinstance(details, bytes):
                try:
                    details = json.loads(details.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    details = details.decode("utf-8", errors="replace")
            raise YoutubeUploadError(
                f"YouTube 영상 업로드에 실패했습니다: {details or exc}"
            ) from exc

        try:
            thumbnail_media = self.media_upload_factory(
                str(thumbnail_path), resumable=False, mimetype="image/jpeg"
            )
            self.service.thumbnails().set(
                videoId=video_id, media_body=thumbnail_media
            ).execute()
        except Exception as exc:
            details = getattr(exc, "content", None)
            if isinstance(details, bytes):
                try:
                    details = json.loads(details.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    details = details.decode("utf-8", errors="replace")
            raise YoutubeUploadError(
                "영상은 업로드됐지만 썸네일 설정에 실패했습니다. "
                f"video_id={video_id}, 오류={details or exc}. 영상을 다시 업로드하지 마세요."
            ) from exc

        return YoutubeUploadResult(
            video_id=video_id,
            url=f"https://www.youtube.com/watch?v={video_id}",
            privacy=privacy,
            thumbnail_uploaded=True,
        )

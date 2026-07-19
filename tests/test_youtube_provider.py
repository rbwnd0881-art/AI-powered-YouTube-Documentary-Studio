from ai_youtube.domain.models import PublishingMetadata
from ai_youtube.providers.youtube_provider import YoutubeUploader


class FakeUploadRequest:
    def next_chunk(self):
        return None, {"id": "video123"}


class FakeVideos:
    def __init__(self):
        self.kwargs = None

    def insert(self, **kwargs):
        self.kwargs = kwargs
        return FakeUploadRequest()


class FakeThumbnailRequest:
    def execute(self):
        return {"items": []}


class FakeThumbnails:
    def __init__(self):
        self.kwargs = None

    def set(self, **kwargs):
        self.kwargs = kwargs
        return FakeThumbnailRequest()


class FakeYoutubeService:
    def __init__(self):
        self.video_resource = FakeVideos()
        self.thumbnail_resource = FakeThumbnails()

    def videos(self):
        return self.video_resource

    def thumbnails(self):
        return self.thumbnail_resource


def test_youtube_uploads_video_then_thumbnail(tmp_path):
    video = tmp_path / "final.mp4"
    thumbnail = tmp_path / "thumbnail.jpg"
    video.write_bytes(b"video")
    thumbnail.write_bytes(b"image")
    service = FakeYoutubeService()
    uploads = []

    def fake_media(path, **kwargs):
        uploads.append((path, kwargs))
        return {"path": path}

    result = YoutubeUploader(service, media_upload_factory=fake_media).upload(
        video_path=video,
        thumbnail_path=thumbnail,
        metadata=PublishingMetadata(
            title="테스트 제목",
            description="테스트 설명",
            tags=["테스트"],
            thumbnail_text="테스트",
        ),
        category_id="22",
        privacy="private",
    )
    assert result.video_id == "video123"
    assert result.privacy == "private"
    assert service.video_resource.kwargs["body"]["snippet"]["title"] == "테스트 제목"
    assert service.thumbnail_resource.kwargs["videoId"] == "video123"
    assert len(uploads) == 2

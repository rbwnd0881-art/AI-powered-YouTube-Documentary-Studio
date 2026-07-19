from typing import Any

from ai_youtube.domain.models import VideoJob


STAGES = [
    "script",
    "storyboard",
    "voice",
    "visuals",
    "edit",
    "thumbnail",
    "quality_check",
    "upload",
]


def create_job_plan(channel_config: dict[str, Any], idea: str) -> dict[str, Any]:
    channel_id = channel_config["channel"]["id"]
    job = VideoJob.create(channel_id=channel_id, idea=idea)
    return {"job": job.to_dict(), "stages": STAGES}


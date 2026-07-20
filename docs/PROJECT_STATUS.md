# Project Status

## Implemented

- Topic-to-script generation
- Script-to-speech generation
- Scene planning with image prompts, video prompts, and subtitles
- FFmpeg editing provider
- Publishing metadata and thumbnail generation
- YouTube OAuth upload provider
- Resumable one-command MVP video pipeline
- Deterministic placeholder image provider
- OpenAI Images API provider with configurable model, output saving, and documented
  transient-error retries
- Visual provider factory supporting `openai` and `placeholder`
- Verified local FFmpeg render (H.264 video and AAC audio)
- Unit tests for the implemented pipeline stages

## Latest Video Validation

- Date: 2026-07-19
- Topic: 문어는 심장이 3개다
- Result: 51.216-second vertical MP4 generated successfully
- Stages: script, scenes, prompts, TTS, placeholder images, FFmpeg render
- Output: `storage/channel_001/jobs/octopus-mvp-20260719/final.mp4`

## Latest Image Provider Validation

- Date: 2026-07-20
- Mocked API tests: provider selection, response format, output path, image resize,
  HTTP 429/5xx retry, HTTP 400/401 no-retry
- Real API image: generated and saved successfully as a 1080x1920 RGB PNG
- Output: `storage/channel_001/jobs/openai-image-mvp-20260720/scene_001.png`

## Next

1. Integrate generated images into a full MP4 run.
2. Add API cost tracking.
3. Add automated quality checks.

## Human Gates

- Review factual or sensitive script content.
- Review the private upload before making it public.

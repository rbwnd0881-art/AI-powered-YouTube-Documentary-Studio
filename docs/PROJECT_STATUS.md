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
- Minimal filename-ordered image-to-MP4 Video Composer
- Multi-scene image pipeline connecting the existing visual provider factory to the
  existing Video Composer
- Responses API Script Engine with validated four-scene structured output and
  localization parameter
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

## Latest Video Composer Validation

- Date: 2026-07-20
- Input: previously generated OpenAI image
- Result: playable 3-second H.264 MP4 generated successfully
- Resolution and frame rate: 1080x1920 at 30 FPS
- Ordering: three-color filename-order validation passed
- Output: `storage/channel_001/jobs/openai-image-mvp-20260720/shorts-m2.mp4`

## Latest Multi-Scene Validation

- Date: 2026-07-20
- Topic: Why an octopus has three hearts
- Provider: OpenAI
- Scenes and API requests: 4 scenes, exactly 4 image requests
- Images: four ordered 1080x1920 RGB PNG files
- Result: playable 12-second silent H.264 MP4 at 1080x1920 and 30 FPS
- FFmpeg full decode: passed
- Output: `storage/channel_001/jobs/octopus-m3-20260720/shorts-m3.mp4`
- Tests: 37 passed; Ruff passed

## Latest Script Engine Validation

- Date: 2026-07-20
- Topic: Why an octopus has three hearts
- Model and API: `gpt-4o-mini` through the Responses API
- Result: hook, narration, four ordered scene prompts, title, description, and
  keywords generated successfully
- API requests and usage: 1 request, 313 input tokens, 256 output tokens
- Output: `storage/channel_001/jobs/octopus-m4-20260720/script-m4.json`
- Tests: 43 passed; Ruff passed
- Limitation: narration duration is a prompt target until TTS measures actual audio;
  generated factual claims still require human review

## Next

1. Add API cost tracking.
2. Add automated quality checks.
3. Connect Script Engine output to the M3 pipeline in a later milestone.

## Human Gates

- Review factual or sensitive script content.
- Review the private upload before making it public.

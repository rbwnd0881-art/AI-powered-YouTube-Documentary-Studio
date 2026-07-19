# Project Status

## Implemented

- Topic-to-script generation
- Script-to-speech generation
- Scene planning with image prompts, video prompts, and subtitles
- FFmpeg editing provider
- Publishing metadata and thumbnail generation
- YouTube OAuth upload provider
- Unit tests for the implemented pipeline stages

## Next

1. Verify FFmpeg with a real local render.
2. Implement the media-provider adapter without coupling the pipeline to Pollo.
3. Add one resumable end-to-end pipeline command.
4. Add automated quality checks and cost tracking.
5. Add YouTube Analytics collection and feedback rules.

## Human Gates

- Review factual or sensitive script content.
- Review the private upload before making it public.

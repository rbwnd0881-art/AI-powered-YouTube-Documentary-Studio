# AI YouTube Automation

아이디어 입력부터 대본, 음성, 이미지·영상, 편집, 썸네일, YouTube 업로드까지 연결하는 다채널 자동화 시스템입니다.

현재 저장소는 **MVP용 확장형 골격**입니다. 공급자별 API 코드는 서로 분리하고, 채널별 차이는 `config/channels/*.yaml`로 관리합니다.

## 설계 원칙

- 하나의 파이프라인을 여러 채널에서 재사용합니다.
- OpenAI, Pollo, YouTube 같은 외부 서비스는 `providers` 뒤에 숨깁니다.
- 각 단계의 결과물을 작업 폴더에 저장해 실패한 단계부터 재실행할 수 있게 합니다.
- 초기에는 대본 승인과 공개 승인만 사람이 담당합니다.
- 반복 가능한 편집은 유료 AI 편집기 대신 FFmpeg를 사용합니다.

## 처리 흐름

```text
아이디어 → 대본 → 스토리보드 → 음성 → 이미지/영상 → FFmpeg 편집
        → 썸네일 → 품질검사 → 비공개 업로드 → 사람 승인 → 공개
```

## 폴더 구조

```text
.
├── assets/                 # 폰트, 음악, 오버레이, 편집 템플릿
├── config/
│   ├── app.yaml            # 공통 실행 설정
│   └── channels/           # 채널별 콘텐츠·스타일 설정
├── data/
│   └── jobs/               # 작업 상태 JSON (Git 제외)
├── docs/                   # 아키텍처와 프로젝트 진행 문서
├── logs/                   # 실행 로그 (Git 제외)
├── output/                 # 로컬 실행의 완성 영상 (Git 제외)
├── scripts/                # 설치·검사·실행 명령
├── src/ai_youtube/
│   ├── cli.py              # 명령줄 진입점
│   ├── config.py           # 환경변수와 YAML 로딩
│   ├── domain/             # 공통 데이터 모델
│   ├── pipeline/           # 제작 단계 및 오케스트레이션
│   ├── providers/          # 외부 API 어댑터
│   └── quality/            # 자동 품질검사
├── storage/                # 생성 미디어 (Git 제외)
└── tests/
```

전체 아키텍처와 현재 개발 상태는 `docs/ARCHITECTURE.md`와
`docs/PROJECT_STATUS.md`에서 관리합니다.

## 설치

권장 조건은 Python 3.11 이상과 FFmpeg입니다. 기본 골격은 Python 3.9에서도 동작합니다.

```bash
./scripts/setup.sh
cp .env.example .env
```

YouTube 업로드 기능을 구현할 때만 선택 의존성을 추가로 설치합니다.

```bash
.venv/bin/python -m pip install -r requirements-youtube.txt
```

`.env`에 필요한 API 키를 입력한 다음 환경을 검사합니다.

```bash
./scripts/check_env.sh
```

## 실행

현재 골격이 정상 작동하는지 확인합니다.

```bash
./scripts/run.sh doctor
./scripts/run.sh pipeline --channel channel_001 --idea "첫 번째 영상 아이디어"
```

두 번째 명령은 외부 API를 호출하지 않고 작업 ID와 실행 계획을 생성합니다.

## 주제 하나로 MVP 영상 생성

아래 명령 하나가 대본 생성, Scene 분리, AI 음성, AI 이미지, FFmpeg
합성을 순서대로 실행해 세로형 MP4를 만듭니다.

```bash
./scripts/run.sh mvp-video \
  --topic "우리가 꿈을 금방 잊어버리는 이유" \
  --channel channel_001
```

결과는 `storage/channel_001/jobs/실행시각/`에 저장됩니다. `script.json`,
`scenes.json`, `voice.mp3`, `media/`, `edit-manifest.json`, `final.mp4`,
`state.json`이 남으므로 실패 원인을 확인하거나 완료된 단계부터 이어갈 수 있습니다.

중단된 작업을 재개할 때는 처음 표시된 작업 폴더를 다시 지정합니다.

```bash
./scripts/run.sh mvp-video \
  --topic "우리가 꿈을 금방 잊어버리는 이유" \
  --channel channel_001 \
  --job-dir storage/channel_001/jobs/20260719-160000
```

기본 이미지 공급자는 OpenAI Images API입니다. `.env`의
`OPENAI_IMAGE_MODEL`과 `config/app.yaml`의 `image_generation`에서 모델, 품질,
API 해상도, 타임아웃을 설정합니다. API 비용 없이 파이프라인을 검사할 때는
`config/app.yaml`의 `providers.image`를 `placeholder`로 바꾸면 됩니다.

OpenAI 이미지와 Placeholder는 같은 `VisualProvider` 인터페이스를 사용하므로
파이프라인 코드를 바꾸지 않고 전환할 수 있습니다. OpenAI 요청은 HTTP 429와
HTTP 5xx만 제한적으로 재시도하며, 인증·프롬프트 검증·정책 오류는 재시도하지
않습니다.

## 이미지 폴더를 Shorts MP4로 합성

`VideoComposer`는 이미지 폴더의 지원 파일을 파일명 순으로 정렬해 무음 세로형
MP4로 합성합니다. 해상도, 이미지당 길이, FPS는 `config/app.yaml`의
`video_composer`에서 설정합니다. 컷, 자막, 음악, 효과는 추가하지 않습니다.

```python
from pathlib import Path

from ai_youtube.config import load_app_config
from ai_youtube.video_composer import VideoComposer

job_dir = Path("storage/channel_001/jobs/example")
video = VideoComposer(load_app_config()["video_composer"]).compose(
    image_dir=job_dir,
    output_dir=job_dir,
    output_filename="shorts.mp4",
)
print(video)
```

## 여러 Scene 이미지를 Shorts로 연결

`MultiSceneImagePipeline`은 고정된 Scene 프롬프트를 현재 이미지 Provider에 순서대로
전달하고 `scene_001.png` 형식으로 저장한 뒤 기존 `VideoComposer`를 호출합니다.
`config/app.yaml`의 `providers.image` 값에 따라 `openai` 또는 `placeholder`를 그대로
사용합니다. 비어 있지 않은 Job 폴더는 덮어쓰지 않습니다.

```python
from pathlib import Path

from ai_youtube.config import Settings, load_app_config
from ai_youtube.pipeline.multi_scene import MultiSceneImagePipeline
from ai_youtube.providers.factory import create_visual_provider
from ai_youtube.video_composer import VideoComposer

settings = Settings()
config = load_app_config()
pipeline = MultiSceneImagePipeline(
    create_visual_provider(
        config["providers"]["image"], settings, config["image_generation"]
    ),
    VideoComposer(config["video_composer"]),
)
result = pipeline.run(
    topic="Why an octopus has three hearts",
    scene_prompts=["hook prompt", "explanation 1", "explanation 2", "conclusion"],
    job_dir=Path("storage/channel_001/jobs/new-m3-job"),
)
print(result.video_path)
```

이미지 하나라도 실패하면 이후 Scene 처리와 MP4 합성을 중단합니다. 성공한 이미지
파일은 원인 확인을 위해 그대로 보존하며, Provider 자체의 기존 재시도 정책 외에
추가 Retry Engine은 사용하지 않습니다.

## 주제에서 구조화된 Shorts 대본 생성

`ScriptEngine`은 OpenAI Responses API의 구조화 출력을 사용해 Hook, 연속
내레이션, 네 개의 Scene 프롬프트, YouTube 제목·설명·키워드를 생성합니다.
기본 모델과 언어는 `config/app.yaml`의 `script_engine`에서 관리하며,
`OPENAI_SCRIPT_MODEL`로 모델만 변경할 수 있습니다.

```python
from ai_youtube.config import Settings, load_app_config
from ai_youtube.script_engine import ScriptEngine

settings = Settings()
config = load_app_config()["script_engine"]
engine = ScriptEngine(
    api_key=settings.openai_api_key,
    model=settings.openai_script_model or config["model"],
    timeout_seconds=config["timeout_seconds"],
    default_language=config["default_language"],
)
script = engine.generate("Why an octopus has three hearts")
print(script.model_dump_json(indent=2))
```

`language="ko-KR"`처럼 호출별 출력 언어를 지정할 수 있습니다. 현재 30~45초는
프롬프트 목표이며 실제 재생 시간은 향후 TTS 연결 후 검증해야 합니다. 생성된 사실
주장은 Research Engine이 추가되기 전까지 사람이 확인해야 합니다.

## 주제에서 대본 생성

1. `.env.example`을 `.env`로 복사합니다.
2. `.env`의 `OPENAI_API_KEY`에 OpenAI Platform API 키를 입력합니다.
3. 아래 명령을 실행합니다.

```bash
./scripts/run.sh generate-script \
  --topic "우리가 꿈을 금방 잊어버리는 이유" \
  --channel channel_001 \
  --output storage/channel_001/first-script.json
```

`--output`을 생략하면 JSON 결과가 터미널에 표시됩니다. 모델, 재시도 횟수,
타임아웃은 각각 `.env`와 `config/app.yaml`에서 변경할 수 있습니다.

> ChatGPT Plus 구독과 OpenAI API 사용료는 별도입니다. 실제 API 호출에는
> OpenAI Platform API 키와 결제 설정이 필요합니다.

## 대본에서 AI 음성 생성

기본값은 `gpt-4o-mini-tts`, `marin` 음성, MP3 형식입니다.

```bash
./scripts/run.sh generate-voice \
  --script storage/channel_001/first-script.json \
  --channel channel_001 \
  --output storage/channel_001/first-voice.mp3
```

다른 음성을 시험할 때는 설정 파일을 바꾸지 않고 `--voice`를 사용할 수 있습니다.

```bash
./scripts/run.sh generate-voice \
  --script storage/channel_001/first-script.json \
  --output storage/channel_001/first-voice.mp3 \
  --voice cedar
```

모델·기본 음성은 `.env`, 음성 형식·재시도·말투는 `config/app.yaml`, 채널별
음성과 속도는 `config/channels/*.yaml`에서 관리합니다. OpenAI 정책에 따라 영상
설명 등에 음성이 AI로 생성되었음을 명확히 고지해야 합니다.

## 대본에서 Scene 생성

대본을 훅, 본문 장면, 마무리 단위로 고정한 뒤 각 Scene에 이미지 프롬프트,
영상 프롬프트, 자막을 생성합니다.

```bash
./scripts/run.sh generate-scenes \
  --script storage/channel_001/first-script.json \
  --channel channel_001 \
  --output storage/channel_001/first-scenes.json
```

결과 JSON에는 `scene_number`, `source_id`, `narration`, `image_prompt`,
`video_prompt`, `subtitle`이 들어갑니다. 비주얼 스타일과 자막 최대 길이는
`config/app.yaml`의 `scene_generation`에서 변경합니다.

## 자동 영상 편집

MoviePy 대신 FFmpeg를 직접 사용합니다. macOS에서 FFmpeg가 없다면 설치합니다.

```bash
brew install ffmpeg
```

`assets/templates/edit-manifest.example.json`을 작업 폴더에 복사하고 내레이션,
BGM, 각 Scene 이미지·영상, 선택적 효과음 경로를 입력합니다. 경로는 매니페스트
파일이 있는 폴더를 기준으로 해석됩니다.

```bash
./scripts/run.sh edit-video \
  --scenes storage/channel_001/first-scenes.json \
  --manifest storage/channel_001/edit-manifest.json \
  --output storage/channel_001/final.mp4
```

편집기는 내레이션 길이를 기준으로 장면 시간을 자동 배분하고, 이미지와 영상을
같은 세로 해상도로 정규화한 뒤 자막, BGM, 효과음, 전환 효과를 합성합니다.
BGM과 효과음은 상업적 이용이 허용된 파일만 사용해야 합니다.

자막은 Pillow로 투명 PNG 오버레이를 만든 뒤 FFmpeg로 합성합니다. 따라서
`libass` 자막 필터가 빠진 기본 Homebrew FFmpeg에서도 동일하게 렌더링됩니다.

## 게시 자료와 썸네일 생성

OpenAI가 제목·설명·태그와 썸네일 문구를 만들고, Pillow가 기존 이미지를 이용해
1280×720 JPG 썸네일을 생성합니다. 별도 이미지 생성 비용은 들지 않습니다.

```bash
./scripts/run.sh prepare-publish \
  --script storage/channel_001/first-script.json \
  --background storage/channel_001/media/scene_001.png \
  --metadata-output storage/channel_001/publish.json \
  --thumbnail-output storage/channel_001/thumbnail.jpg
```

## YouTube 자동 업로드

### 최초 한 번 설정

1. Google Cloud Console에서 프로젝트를 생성합니다.
2. YouTube Data API v3를 활성화합니다.
3. OAuth 동의 화면을 설정하고 데스크톱 앱 OAuth 클라이언트를 만듭니다.
4. 받은 JSON 파일을 `secrets/youtube_client_secret.json`으로 저장합니다.
5. YouTube 선택 패키지를 설치합니다.

```bash
.venv/bin/python -m pip install -r requirements-youtube.txt
```

### 업로드 실행

```bash
./scripts/run.sh upload-youtube \
  --video storage/channel_001/final.mp4 \
  --metadata storage/channel_001/publish.json \
  --thumbnail storage/channel_001/thumbnail.jpg \
  --channel channel_001
```

최초 실행에서 브라우저 OAuth 승인이 한 번 필요합니다. 이후 토큰은
`secrets/youtube_token.json`에 저장되어 재사용됩니다. 기본값은 `private`이며,
공개 업로드는 다음처럼 명시적으로 허용해야 합니다.

```bash
./scripts/run.sh upload-youtube \
  --video storage/channel_001/final.mp4 \
  --metadata storage/channel_001/publish.json \
  --thumbnail storage/channel_001/thumbnail.jpg \
  --privacy public \
  --allow-public
```

## 채널 추가

`config/channels/channel_001.yaml`을 복사해 새 파일을 만들고 `id`, 언어, 화면 비율, 음성, 스타일만 변경합니다. 파이프라인 코드는 복사하지 않습니다.

## 보안

- 실제 키는 `.env`에만 저장하고 Git에 커밋하지 않습니다.
- YouTube OAuth 파일은 `secrets/`에 두며 해당 폴더는 Git에서 제외됩니다.
- 업로드 자동화는 처음에 항상 `private`로 실행합니다.

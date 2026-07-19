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

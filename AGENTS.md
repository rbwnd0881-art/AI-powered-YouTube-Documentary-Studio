# Project Atlas Repository Operating Manual

## 1. Purpose and Scope

This repository is an AI Documentary Studio for producing factual, engaging,
cinematic YouTube documentaries from idea to publication. Work is not complete merely
because the latest prompt has been answered. Every change must improve the production
system or move a documentary toward a verifiable, publishable state.

These instructions apply to every project and file in this repository unless the user
explicitly overrides them. More specific instructions in a nested `AGENTS.md`, if one
is later added, apply within that subtree.

## 2. Core Mission

Produce professional YouTube documentary projects that are:

- factually supportable;
- narratively compelling without misleading the audience;
- cinematic and visually coherent;
- technically reproducible;
- safe for commercial publication;
- maintainable across multiple channels and providers.

Always identify the next logical production step, but do not perform paid calls,
external publication, account changes, or major architectural changes without the
required user authorization.

## 3. Operating Principles

Apply these priorities in order:

1. Factual accuracy and source quality.
2. Audience clarity and narrative coherence.
3. Reproducibility and testability.
4. Automation with minimal human repetition.
5. Maintainability and provider portability.
6. Cost efficiency.
7. Production speed.

Do not trade factual accuracy for drama, retention, or visual impact. Do not add
complexity without a current production need. Preserve the existing architecture and
public interfaces unless a documented requirement makes change necessary.

## 4. Production Team Roles

Treat the following as mandatory review perspectives. They may be performed
sequentially by one agent or delegated when delegation is explicitly authorized. A
role label does not by itself authorize parallel agents, external actions, or paid API
calls.

### 4.1 Research Agent

Responsibilities:

- Define the research question, geographic scope, and time range.
- Search multiple independent and reliable sources.
- Prefer government archives, court records, official reports, academic research,
  primary documents, books from reputable publishers, historical newspapers, and
  attributable expert interviews.
- Build enough context for the requested documentary length rather than collecting
  isolated facts.
- Preserve publication title, author or institution, date, URL or archive identifier,
  page or section, access date, and relevant excerpt notes.
- Save durable findings in the documentary's research document or job directory.
- Identify contradictions, missing records, and claims requiring further verification.

Never rely on a single website for a material claim when independent corroboration is
available. Search breadth must be proportional to the importance and risk of the claim.

### 4.2 Fact Check Agent

Classify every material claim using these labels:

- `FACT`: directly supported by reliable evidence.
- `EVIDENCE`: the source, record, quotation, measurement, or observation supporting a
  claim.
- `INFERENCE`: a reasoned conclusion derived from identified facts and evidence.
- `SPECULATION`: an unverified possibility or interpretation.

Never present inference or speculation as fact. Mark uncertainty and conflicting
evidence explicitly. If a claim cannot be verified, remove it, narrow it, or state that
it remains unconfirmed.

### 4.3 Story Producer

Responsibilities:

- Convert verified research into a beginning, escalation, turning point, and ending.
- Establish the central question and the evidence needed to answer it.
- Use open questions, mystery, tension, contrast, and emotional pacing without
  manufacturing facts.
- Place context before conclusions that depend on it.
- Resolve major curiosity loops or clearly explain why the historical record cannot.
- Remove repetition and scenes that do not advance the central story.

Retention techniques must arise from real stakes and unanswered evidence, not
unsupported clickbait.

### 4.4 Script Writer

Every documentary script should contain:

- a strong, truthful hook;
- a clear central question;
- curiosity loops grounded in the evidence;
- natural transitions;
- escalating stakes or understanding;
- source-aware narration;
- a strong ending that resolves the thesis or defines the remaining uncertainty.

Write for natural speech. Avoid robotic phrasing, repeated sentence patterns,
unexplained jargon, invented quotations, fabricated scenes, and exaggerated certainty.
When quoting, preserve the wording and citation and use only the portion needed.

### 4.5 Scene Director

Break the approved script into production scenes. Each scene plan must identify:

- scene number and narrative purpose;
- corresponding narration;
- visual description;
- camera framing or movement idea;
- historical or factual reference;
- intended emotion or pacing;
- evidence or asset requirement;
- transition intent when transitions are in scope.

Do not depict a reconstruction as authentic archival footage. Label reenactments,
illustrations, simulations, and AI-generated imagery when viewers could misunderstand
their status.

### 4.6 Image Prompt Designer

Create professional image-generation prompts that specify, when relevant:

- subject and action;
- time period and location;
- historically supported clothing, objects, architecture, and environment;
- composition and camera angle;
- lens or depth-of-field intent;
- lighting and color palette;
- atmosphere and emotion;
- aspect ratio and placement needs;
- continuity details shared across scenes;
- exclusions such as text, logos, watermark, anachronisms, or modern objects.

Maintain character, wardrobe, setting, color, and visual-style consistency. Do not ask
an image model to invent evidence or create a deceptive imitation of a real document.

### 4.7 Video Prompt Designer

Create prompts compatible with the configured video provider, including Pollo AI when
that provider is available. Each prompt should specify:

- camera movement;
- subject movement;
- environmental movement;
- lighting behavior;
- mood;
- visual style;
- duration or pacing when supported;
- continuity constraints;
- prohibited artifacts or unsupported historical details.

Keep provider-specific syntax inside provider adapters or provider prompt templates.
Do not couple the production pipeline directly to Pollo AI or another vendor.

### 4.8 Thumbnail Designer

Produce multiple evidence-consistent thumbnail concepts. Each concept should define:

- one clear focal subject;
- the curiosity gap;
- composition and contrast;
- optional short text;
- mobile-size readability;
- factual basis.

Never imply an event, person, discovery, or quotation unsupported by the documentary.
Do not use deceptive before-and-after imagery or fabricated evidence.

### 4.9 Quality Assurance Agent

Before declaring work complete, verify:

- historical and factual accuracy;
- claim-to-source traceability;
- distinction between fact, inference, and speculation;
- internal consistency across research, script, scenes, prompts, metadata, and media;
- source quality and independence;
- grammar, pronunciation risks, and natural narrative flow;
- hook strength, pacing, curiosity-loop resolution, and ending quality;
- missing context or missing counterevidence;
- weak evidence, hallucinations, anachronisms, and visual continuity defects;
- output paths, file integrity, media properties, tests, and reproducibility;
- commercial-use, copyright, privacy, safety, and platform-policy concerns.

If quality is insufficient, improve the work before presenting it. If improvement
requires new authority, paid services, or unavailable evidence, report the exact gap.

## 5. Research and Evidence Standard

### 5.1 Source Priority

Use sources in this order when applicable:

1. Primary evidence and original records.
2. Government archives, court records, legislation, FOIA documents, and official
   reports.
3. Peer-reviewed academic papers and university collections.
4. Books from reputable academic or specialist publishers.
5. Historical newspapers and contemporaneous reporting.
6. Named expert interviews and professional institutions.
7. High-quality secondary reporting.

Blogs, social posts, anonymous summaries, SEO pages, and unsourced videos may suggest
research leads but must not be the sole evidence for a material claim.

### 5.2 Verification Procedure

Perform two passes:

1. Evidence verification: confirm names, dates, numbers, quotations, source identity,
   source date, and direct support for the claim.
2. Production verification: confirm the claim is represented accurately in the story,
   visuals, title, thumbnail, description, and metadata without exaggeration.

For sensitive, disputed, medical, legal, political, financial, or reputational claims,
use additional authoritative corroboration and clearly state limitations.

### 5.3 Quotations and Citations

- Quote only from a source actually inspected.
- Preserve the speaker, document, date, and surrounding meaning.
- Never reconstruct a quote from memory.
- Keep quotations within copyright and source-use limits.
- Attach citations as close as practical to the supported claim.
- Preserve stable links, archive identifiers, page numbers, or timestamps.

### 5.4 Uncertainty

Use precise language:

- `Confirmed by ...`
- `The available record shows ...`
- `This is an inference based on ...`
- `Accounts conflict on ...`
- `No reliable public evidence was found for ...`
- `This remains unconfirmed.`

Do not fill evidence gaps with plausible-sounding detail.

## 6. Documentary Production Workflow

Use the smallest applicable subset of this workflow, while preserving handoff artifacts:

1. Idea brief and central question.
2. Research plan and source collection.
3. Evidence ledger and fact check.
4. Timeline or event map.
5. Story outline.
6. Script.
7. Scene plan.
8. Image prompts and video prompts.
9. Asset generation or collection.
10. Narration and audio plan.
11. Edit and captions.
12. Thumbnail concepts and final thumbnail.
13. YouTube title, description, chapters, tags, and disclosures.
14. Technical and editorial QA.
15. Private upload.
16. Human publication approval.
17. Analytics collection and documented lessons for the next production.

Do not skip factual review merely because an automated stage succeeds.

## 7. Required Production Artifacts

When a full documentary project is requested, work toward these artifacts:

- `brief`: topic, thesis, audience, format, duration, and constraints;
- `research`: source notes and citation inventory;
- `evidence-ledger`: claims classified as FACT, EVIDENCE, INFERENCE, or SPECULATION;
- `timeline`: dated events and unresolved conflicts;
- `outline`: acts, beats, curiosity loops, and ending;
- `script`: narration with source references;
- `scene-plan`: purpose, narration, visuals, camera, reference, and emotion;
- `image-prompts` and `video-prompts`;
- `asset-manifest`: provenance, license, generated status, and file path;
- `thumbnail-concepts` and selected thumbnail;
- `metadata`: title, description, chapters, keywords, tags, and disclosures;
- `qa-checklist`;
- final media and publication record.

Use the existing job-directory conventions under `storage/<channel>/jobs/<job-id>/`.
Generated media and secrets must remain excluded from Git unless the repository's policy
explicitly changes.

## 8. Repository Architecture Rules

Preserve these established boundaries:

- External services belong behind interfaces in `src/ai_youtube/providers/`.
- `VisualProvider` remains vendor-neutral.
- `PlaceholderImageProvider` remains available for free tests and fallback.
- Provider selection uses the provider factory.
- `OpenAIImageProvider` remains replaceable.
- `VideoComposer` remains dedicated to deterministic image-to-video composition.
- `MultiSceneImagePipeline` orchestrates ordered Scene images and composition.
- `ScriptEngine` owns the current structured Shorts script generation.
- Shared settings belong in `config/app.yaml` or environment variables.
- Channel-specific settings belong in `config/channels/*.yaml`.
- API keys and OAuth credentials belong only in `.env` or ignored secret files.

Do not duplicate implemented features. Inspect existing code and project status before
adding a module. Prefer a small extension over a parallel implementation.

## 9. Development Procedure

For implementation work, follow this order:

1. Inspect repository status and existing implementation.
2. Define the current production objective and explicit out-of-scope items.
3. Compare only materially different implementation options.
4. Select the smallest maintainable change.
5. Implement with configuration separated from secrets and code.
6. Add lightweight tests without paid or destructive external calls.
7. Run targeted tests.
8. Run the full test suite and Ruff.
9. Run relevant media validation with FFmpeg or ffprobe.
10. Fix failures and repeat verification.
11. Update `README.md` and `docs/PROJECT_STATUS.md` when behavior or status changes.
12. Check Git diff, ignored secrets, and generated artifacts.
13. Commit one coherent completed milestone.
14. Push only when authentication is available, and report the real result.

Never claim a test, render, upload, commit, or push succeeded unless its output was
observed.

## 10. Testing and Completion Standard

Use these standard commands unless the project changes them:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python -m ai_youtube doctor
```

For video outputs, verify at minimum:

- file exists and is nonempty;
- container and codec;
- width and height;
- frame rate;
- duration;
- pixel format when platform compatibility matters;
- full FFmpeg decode without errors.

For image outputs, verify format, dimensions, color mode, file integrity, scene order,
and visual consistency. For structured outputs, validate the schema and required item
counts.

## 11. Cost, External Actions, and Human Approval

Prefer free local validation, mocks, Placeholder providers, and low-cost models before
real calls. Explain official pricing and the intended number of calls before a new paid
test. Do not report an exact charge unless verified billing data is available.

Require user authorization before:

- adopting a new paid service;
- materially increasing recurring cost;
- making a major or difficult-to-reverse architectural change;
- publishing or making content public on YouTube or another external platform;
- changing credential storage or security policy;
- performing an external action outside the approved production scope.

Private previews and local files are not publication approval.

## 12. Security and Privacy

- Never print, log, commit, or include API keys, OAuth tokens, passwords, or complete
  sensitive environment variables in reports.
- Keep `.env`, `secrets/`, generated media, logs, and job data ignored as configured.
- Verify ignore rules before every commit involving credentials or generated output.
- Do not place private personal data into model prompts unless explicitly authorized and
  necessary.
- Redact sensitive values from errors and screenshots.
- Use least-privilege OAuth scopes and default uploads to private.

## 13. Copyright, Licensing, and Disclosure

- Record the origin and license of archival media, music, sound effects, fonts, and
  third-party footage.
- Do not assume online availability grants commercial-use rights.
- Prefer public-domain, properly licensed, original, or generated assets.
- Do not imitate living artists or misrepresent generated media as authentic evidence.
- Include AI-generated media disclosures where required by platform policy, law, or the
  risk of viewer confusion.
- Flag fair-use questions for human review; do not present legal conclusions as settled
  without authoritative support.

## 14. Metadata and Publication Standard

Titles, descriptions, thumbnails, chapters, and keywords must accurately reflect the
documentary. They may create curiosity but must not introduce claims absent from the
evidence or script. Before publication verify:

- title and thumbnail promise match the video;
- description includes necessary sources and disclosures;
- names, dates, spellings, and chapters are correct;
- captions and audio are synchronized;
- the private upload was reviewed;
- explicit human approval for publication was received.

## 15. Communication and Reporting

Lead with the outcome. Keep status updates concise and make blockers explicit. Separate:

- verified facts;
- implementation decisions;
- limitations;
- next recommended production step.

At completion report:

1. Completed work.
2. Changed files or created production artifacts.
3. Verification results.
4. API usage and official-price calculation when applicable.
5. Git commit and actual push status when applicable.
6. Human-review requirements.
7. Remaining limitations and next logical step.

Do not overstate quality, factual certainty, cost accuracy, platform compliance, or
publication readiness.

## 16. Definition of Professional Completion

A task is professionally complete only when:

- the requested artifact or code works;
- evidence is traceable and uncertainty is labeled;
- the narrative does not distort the evidence;
- production outputs pass relevant technical validation;
- tests and lint checks pass for code changes;
- secrets and generated artifacts are protected;
- documentation reflects the current state;
- remaining human gates and limitations are explicit;
- the next production step is identified without silently expanding scope.


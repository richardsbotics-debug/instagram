# AI Reels Pipeline - Build Automated Instagram Reels with Claude Code

A complete, open-source pipeline for producing professional Instagram Reels using AI avatars, AI-generated B-roll, and automated video rendering - all orchestrated through Claude Code.

**What it does:** You write a script, the pipeline generates an AI avatar speaking it, finds/creates B-roll footage, plans a visual storyboard using Claude, assembles everything into a JSON config, and renders a polished split-screen reel via Remotion - with quality gates at every step.

**Stack:** Python + TypeScript/React (Remotion) + Claude API + HeyGen API + Google Veo API + FFmpeg + Whisper

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Project Setup](#project-setup)
4. [Directory Structure](#directory-structure)
5. [Pipeline Flow](#pipeline-flow)
6. [Stage 0: Pre-Pipeline (Script + Avatar + Transcribe)](#stage-0-pre-pipeline)
7. [Stage 1: Asset Curator](#stage-1-asset-curator)
8. [Stage 2: Storyboard Agent](#stage-2-storyboard-agent)
9. [Stage 2.5: Image Resolver](#stage-25-image-resolver)
10. [Stage 3: Veo Agent (AI Video Generation)](#stage-3-veo-agent)
11. [Stage 4: Assembly](#stage-4-assembly)
12. [Stage 5: Review](#stage-5-review)
13. [Remotion Rendering System](#remotion-rendering-system)
14. [JSON Config Schema (ReelConfig)](#json-config-schema)
15. [Claude Code Integration](#claude-code-integration)
16. [Design Principles](#design-principles)
17. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
1080x1920 (9:16 portrait, 25fps)
+--------------------------+
|                          |
|    TOP HALF (960px)      |  B-roll: video clips, screenshots, AI-generated
|    JSON-driven segments  |  Ken Burns zoom, crossfade transitions
|                          |
+--[purple pill caption]---+  Word-by-word caption at the seam
|                          |
|   BOTTOM HALF (960px)    |  AI avatar video (HeyGen)
|   Cropped + centered     |  Audio source for the entire reel
|                          |
+--------------------------+
```

### Pipeline Flow

```
Script -> HeyGen Avatar -> Speed Up (1.1x) -> Whisper Transcribe ->
  Asset Curator [GATE] -> Storyboard [GATE] -> Image Resolver -> Veo (on-demand) ->
  Assembly -> Render -> Review [GATE]
       ^                                                              |
       +------ fix loop (max 3 iterations) --------------------------+
```

Every reel is driven by a single JSON config file. No new React code per reel - just data.

---

## Prerequisites

### Required Software

```bash
# Node.js (for Remotion)
node --version  # v18+ required

# Python 3.10+
python3 --version

# FFmpeg (for video processing + quality analysis)
brew install ffmpeg  # macOS
# or: sudo apt install ffmpeg  # Linux

# Whisper (for transcription) - choose one:
pip install mlx-whisper  # Apple Silicon (recommended, fast)
# or:
pip install openai-whisper  # Cross-platform (requires PyTorch)
```

### API Keys

You'll need accounts and API keys for:

| Service | Purpose | Env Variable | Pricing |
|---------|---------|-------------|---------|
| [HeyGen](https://heygen.com) | AI avatar video generation | `HEYGEN_API_KEY` | ~$24/mo Creator plan |
| [Anthropic](https://console.anthropic.com) | Claude API for storyboard planning | `ANTHROPIC_API_KEY` | Pay per token |
| [Google AI Studio](https://aistudio.google.com) | Veo 3.1 AI video generation | `GOOGLE_API_KEY` | ~$0.60-1.60/clip |

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

---

## Project Setup

```bash
# 1. Install Node.js dependencies (Remotion)
npm install

# 2. Create Python virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Directory Structure

```
ai-reels-pipeline/
├── .env                           # API keys (gitignored)
├── package.json                   # Remotion + dependencies
├── tsconfig.json
│
├── src/                           # Remotion compositions (TypeScript/React)
│   ├── index.ts                   # Remotion entry point (registerRoot)
│   ├── Root.tsx                   # Composition registry
│   ├── DynamicReel.tsx            # PRIMARY: JSON-driven reel composition
│   ├── components/
│   │   ├── DynamicBRoll.tsx       # B-roll renderer (video + images)
│   │   ├── DynamicCaptionOverlay.tsx  # Word-by-word purple pill captions
│   │   └── DynamicSceneRenderer.tsx   # Scene template router (optional overlays)
│   ├── scenes/templates/          # 8 parameterized scene types
│   │   ├── HookTemplate.tsx
│   │   ├── BulletsTemplate.tsx
│   │   ├── FeatureGridTemplate.tsx
│   │   ├── BigNumberTemplate.tsx
│   │   ├── ContrastTemplate.tsx
│   │   ├── StrikethroughTemplate.tsx
│   │   ├── LogoGridTemplate.tsx
│   │   └── ClosingTemplate.tsx
│   └── lib/
│       ├── constants.ts           # FPS, dimensions, colors, typography
│       └── dynamic-config.ts      # TypeScript interfaces for JSON config
│
├── public/                        # Static assets (served by Remotion)
│   ├── config/                    # JSON reel configs
│   │   └── reel-config-*.json
│   ├── avatars/                   # HeyGen avatar videos (sped up 1.1x)
│   ├── broll/
│   │   ├── clips/                 # Video clips (Veo AI + screen recordings)
│   │   └── topics/                # Per-topic image assets
│   ├── logos/                     # Brand logos for overlays
│   └── sfx/                       # Sound effects (optional)
│
├── heygen/                        # Avatar generation
│   ├── heygen_client.py           # HeyGen API wrapper
│   ├── generate.py                # CLI: generate avatar video
│   ├── transcribe.py              # Whisper transcription
│   ├── heygen_config.json         # Avatar/voice profiles
│   └── output/                    # Generated avatars + transcripts
│
├── ai-video-exploration/          # Veo AI video generation
│   ├── generate_broll.py          # Shot list -> Veo API -> MP4 clips
│   ├── config.json                # Gemini API key
│   ├── shot-lists/                # Per-reel shot list JSONs
│   └── outputs/                   # Generated clips
│
├── pipeline/                      # Python automation pipeline
│   ├── agents/
│   │   ├── pipeline_state.py      # State tracking across stages
│   │   ├── asset_curator.py       # Stage 1: collect + grade footage
│   │   ├── storyboard.py          # Stage 2: Claude plans visual timeline
│   │   ├── image_resolver.py      # Stage 2.5: Wikipedia image downloader
│   │   ├── veo_agent.py           # Stage 3: Veo AI clip generation
│   │   ├── assembly.py            # Stage 4: build ReelConfig JSON
│   │   ├── reviewer.py            # Stage 5: post-render QA
│   │   ├── __init__.py
│   │   └── output/                # Per-reel state directories
│   └── __init__.py
│
├── out/                           # Rendered output videos
└── raw-footage/                   # Source footage for B-roll
```

---

## Pipeline Flow

### Quick Start (End-to-End)

```bash
# 1. Write your script (max ~100 words for 45s reel)
SCRIPT="Claude Code just changed everything. It lives inside your terminal and understands your entire codebase. Edit files. Run tests. Create pull requests. Developers are shipping 10x faster. This isn't a copilot, it's an autonomous coding agent."

# 2. Generate HeyGen avatar
cd heygen
python3 generate.py --profile my-avatar --script "$SCRIPT"
# Output: output/<task-id>.mp4

# 3. Speed up 1.1x (more energetic feel)
ffmpeg -i output/<task-id>.mp4 \
  -filter_complex "[0:v]setpts=PTS/1.1[v];[0:a]atempo=1.1[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset fast -crf 18 -c:a aac -b:a 192k \
  ../public/avatars/avatar-my-reel.mp4

# 4. Transcribe the sped-up version (timestamps will be correct)
python3 transcribe.py ../public/avatars/avatar-my-reel.mp4
# Output: ../public/avatars/avatar-my-reel_transcript.json

# 5. Initialize pipeline
cd ../pipeline
python3 -m agents.pipeline_state my-reel-v1 --init \
  --tool "My Product" \
  --transcript "../public/avatars/avatar-my-reel_transcript.json" \
  --avatar "avatars/avatar-my-reel.mp4" \
  --script "$SCRIPT"

# 6. Run each stage (see detailed sections below)
python3 -m agents.asset_curator --reel-id my-reel-v1 --tool "My Product"
python3 -m agents.storyboard --reel-id my-reel-v1
python3 -m agents.image_resolver --reel-id my-reel-v1
python3 -m agents.veo_agent --reel-id my-reel-v1
python3 -m agents.assembly --reel-id my-reel-v1 --render
python3 -m agents.reviewer --reel-id my-reel-v1
```

---

## Stage 0: Pre-Pipeline

Before the automated pipeline begins, you need three things:
1. A script (max ~100 words for a 45s reel)
2. An AI avatar video of someone speaking the script
3. A word-level transcript with timestamps

### HeyGen Config

`heygen/heygen_config.json` holds your avatar/voice IDs and named profiles - see that file for the shape, and fill in your real `api_key`, `avatar_id`, and `voice_id` (get these from the HeyGen dashboard or `heygen_client.list_avatars()` / `list_voices()`).

---

## Stage 1: Asset Curator

Scans your asset library, grades each file on visual quality (brightness, resolution, motion), and outputs an approved/rejected manifest.

**Quality scoring:**
- Brightness (0-255): FFmpeg signalstats YAVG. Reject < 30, warn < 50
- Resolution: Reject below 720p minimum dimension
- Duration (video): Reject below 3 seconds
- Motion score (video): FFmpeg scene detection, 0-100
- Overall quality score: Composite 0-100. Reject < 40

**CLI:**
```bash
python3 -m pipeline.agents.asset_curator \
  --reel-id my-reel-v1 \
  --tool "My Product" \
  [--extra-dir /path/to/screen-recordings] \
  [--scan-all]
```

**Output:** `pipeline/agents/output/<reel-id>/asset-manifest.json`

**Gate:** Review which assets were approved/rejected before proceeding.

---

## Stage 2: Storyboard Agent

Uses the Claude API to intelligently plan which visual appears at every moment of the reel, matching B-roll to speech content.

**Key rules:**
- 10-15 segments for a 30-45s reel
- 60%+ video clips (motion > static)
- Max 1-2 screenshots, never consecutive
- 2-3 Veo AI clips for visual variety
- Every B-roll must semantically match the speech
- Scene overlays disabled (they look cheap)

**CLI:**
```bash
python3 -m pipeline.agents.storyboard \
  --reel-id my-reel-v1 \
  [--model claude-sonnet-4-20250514]
```

**Output:** `pipeline/agents/output/<reel-id>/storyboard.json`

---

## Stage 2.5: Image Resolver

Automatically downloads images for `image_needed` segments (rapid image lists like "Snoop Dogg, Tom Brady, Paris Hilton") using the Wikipedia REST API.

**CLI:**
```bash
python3 -m pipeline.agents.image_resolver --reel-id my-reel-v1
```

No interactive gate - runs automatically between Storyboard and Veo.

---

## Stage 3: Veo Agent

Generates AI video clips using Google's Veo 3.1 for storyboard gaps marked as `veo_needed`.

**Models & pricing:**

| Model | Cost/clip | Quality |
|-------|-----------|---------|
| `veo-3.1-fast` | $0.60 | Good (primary choice) |
| `veo-3.1` | $1.60 | Better (hero shots) |
| `veo-3.0-fast` | $0.60 | Decent (budget) |

**CLI:**
```bash
python3 -m pipeline.agents.veo_agent \
  --reel-id my-reel-v1 \
  [--model veo-3.1-fast] \
  [--dry-run]
```

Builds a shot list from every `veo_needed` storyboard segment, hands it to `ai-video-exploration/generate_broll.py`, then copies the resulting clips into `public/broll/clips/` and rewrites those segments as resolved `video` segments.

---

## Stage 4: Assembly

Converts the storyboard into a final ReelConfig JSON for Remotion, validates everything, and optionally renders.

**Validation checks (blocks on errors):**
1. No PLACEHOLDERs / unresolved `image_needed` or `veo_needed` segments
2. No gaps > 0.1s between segments
3. No duplicate consecutive caption text
4. No dark/low-quality assets (cross-referenced against the asset manifest)
5. All referenced files exist on disk
6. Caption chunks present

**CLI:**
```bash
python3 -m pipeline.agents.assembly \
  --reel-id my-reel-v1 \
  [--render] \
  [--crossfade 5] \
  [--avatar-margin -280]
```

---

## Stage 5: Review

Post-render quality verification. Extracts key frames at each segment boundary, analyzes brightness, detects black frames, and checks semantic relevance.

**Checks:**
1. Duration match (rendered vs config)
2. Audio presence
3. Per-segment frame extraction and brightness analysis
4. Variance-aware black frame detection (distinguishes dark UI content from truly black frames)
5. B-roll semantic relevance (best-effort, via Claude vision on extracted frames)
6. Face-only section check

**CLI:**
```bash
python3 -m pipeline.agents.reviewer \
  --reel-id my-reel-v1 \
  [--rendered out/my-reel-v1.mp4]
```

**Verdicts:** pass / warn / fail. On fail, loop back to storyboard or assembly (max 3 iterations).

---

## Remotion Rendering System

The rendering layer is built with [Remotion](https://remotion.dev) - a React framework for programmatic video. See `src/` for the full implementation:

- `src/DynamicReel.tsx` - the primary composition: top-half B-roll, purple-pill captions at the seam, bottom-half cropped avatar.
- `src/components/DynamicBRoll.tsx` - crossfades between segments, applies Ken Burns zoom.
- `src/components/DynamicCaptionOverlay.tsx` - word-by-word purple pill captions.
- `src/components/DynamicSceneRenderer.tsx` + `src/scenes/templates/` - optional scene overlays (disabled by default; the `scenes` array in every generated config stays empty per the design principles below).
- `src/lib/constants.ts` / `src/lib/dynamic-config.ts` - shared constants and the `ReelConfig` TypeScript contract.

### Rendering Commands

```bash
# Create props file (wraps config as {"config": ...})
python3 -c "
import json
config = json.load(open('public/config/reel-config-my-reel.json'))
json.dump({'config': config}, open('/tmp/reel-props.json', 'w'))
"

# Render
npx remotion render DynamicReel out/my-reel.mp4 --codec=h264 --props=/tmp/reel-props.json

# Verify
ffprobe out/my-reel.mp4  # Check duration matches config
```

---

## JSON Config Schema

Every reel is defined by a single JSON file. This is the contract between the pipeline and the renderer.

```json
{
  "id": "my-reel-v1",
  "duration": 853,
  "avatarSrc": "avatars/avatar-my-reel.mp4",
  "avatarMarginTop": -280,
  "crossfadeFrames": 5,
  "brollSegments": [
    {
      "image": "topics/my-product/hero-screenshot.png",
      "startSec": 0,
      "endSec": 2.4,
      "objectPosition": "center 25%",
      "scaleFrom": 1.0,
      "scaleTo": 1.05,
      "_speech": "What the avatar says here (annotation only)"
    },
    {
      "video": "product-demo-clip.mp4",
      "startSec": 2.4,
      "endSec": 5.0,
      "objectPosition": "center 65%",
      "scaleFrom": 1.25,
      "scaleTo": 1.3,
      "videoStartSec": 2,
      "_speech": "See how easy it is to..."
    }
  ],
  "captionChunks": [
    { "text": "This product", "startSec": 0.0, "endSec": 0.8 },
    { "text": "just changed", "startSec": 0.8, "endSec": 1.5 },
    { "text": "everything.", "startSec": 1.5, "endSec": 2.4 }
  ],
  "scenes": []
}
```

**Key fields:**
- `duration`: Total frames at 25fps (e.g., 853 frames = 34.12 seconds)
- `avatarMarginTop`: Negative values shift the avatar video up (showing more head/torso)
- `crossfadeFrames`: 3=snappy, 5=smooth (recommended), 8=cinematic
- `_speech`: Annotation only, not rendered - helps with semantic matching during editing

---

## Claude Code Integration

To orchestrate this pipeline through Claude Code, use the `/reels` slash command defined in `.claude/commands/reels.md`. It parses natural-language requests like `new`, `curate`, `storyboard`, `veo`, `assemble`, `review`, `status`, and `full` into the corresponding `pipeline.agents.*` CLI invocations, and always runs them from the project root.

---

## Design Principles

1. **Max 45 seconds** - Short attention spans. Write tighter scripts.
2. **Whisper on sped-up video** - Timestamps are inherently correct. Never double-scale.
3. **Duration from ffprobe** - Use actual video duration, not transcript word timestamps.
4. **Fast cuts, high energy** - 10-15 segments, most 1.5-2.5s. Video > static.
5. **Semantic B-roll** - Every visual must relate to what's being said at that moment.
6. **Quality gates** - Human approval between stages prevents bad reels from rendering.
7. **Fix loops** - On review failure, loop back (max 3 iterations) rather than starting over.
8. **JSON-driven** - No new React code per reel. Everything is data.

---

## Troubleshooting

### Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Black frames in render | Missing B-roll asset file | Check paths in reel-config.json match actual files |
| Audio/video desync | Double-scaled timestamps | Only scale if transcript is from original (non-sped) video |
| Dark frames flagged | Terminal/code screenshots | Reviewer uses variance-aware detection - dark content with text is OK |
| Assembly validation fails | Unresolved PLACEHOLDERs | Run image resolver and veo agent first |
| Render crashes | Missing Remotion deps | Run `npm install` in project root |
| Veo rate limited | Too many requests | 60s delay between clips (tier 1 limit) |

### FFmpeg Quick Reference

```bash
# Speed up video 1.1x with pitch preservation
ffmpeg -i input.mp4 \
  -filter_complex "[0:v]setpts=PTS/1.1[v];[0:a]atempo=1.1[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset fast -crf 18 -c:a aac -b:a 192k \
  output.mp4

# Extract frame at specific timestamp
ffmpeg -ss 5 -i video.mp4 -frames:v 1 -q:v 2 frame-5s.jpg

# Get video duration
ffprobe -v quiet -show_entries format=duration -of csv=p=0 video.mp4

# Get brightness
ffmpeg -i image.png -vf signalstats -f null - 2>&1 | grep YAVG

# Trim a clip
ffmpeg -ss 5 -t 3 -i raw.mp4 -an -c:v libx264 -crf 18 trimmed.mp4
```

---

## License

This pipeline is shared as a free resource. Use it however you want. No attribution required.

Built with Claude Code, Remotion, HeyGen, Google Veo, and Whisper.

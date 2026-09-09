"""Storyboard Agent: Claude plans the visual timeline for a reel.

Reads the word-level transcript and the approved asset manifest, then asks
Claude to lay out a sequence of B-roll segments that covers the full avatar
duration and semantically matches what's being said at every moment.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

import anthropic

DEFAULT_MODEL = "claude-sonnet-4-20250514"
MIN_SEGMENTS = 10
MAX_SEGMENTS = 15
MIN_VIDEO_RATIO = 0.6
MAX_SCREENSHOTS = 2
MIN_VEO_CLIPS = 2
MAX_VEO_CLIPS = 3

SYSTEM_PROMPT = """You are a video storyboard planner for short-form vertical Instagram Reels.

You are given:
- A word-level transcript of an AI avatar speaking a script (with timestamps in seconds).
- A manifest of approved B-roll assets (existing videos and screenshots) available for reuse.

Your job: plan the visual timeline that plays above the avatar for the ENTIRE duration of
the transcript. Output a JSON object with a "segments" array. Each segment must have:
  - "type": one of "video", "screenshot", "image_needed", "veo_needed"
  - "startSec": float, "endSec": float (segments must be contiguous, no gaps or overlaps,
    starting at 0.0 and ending at the transcript's final timestamp)
  - "label": short human-readable description of what's shown
  - "_speech": the exact words being spoken during this segment (for semantic-match review)
  - "asset_id": for type "video" or "screenshot", the id of the approved asset being reused
    (must exactly match an id from the asset manifest)
  - "image_query": for type "image_needed", a search term (e.g. a person's name) to look up
    on Wikipedia
  - "veo_prompt": for type "veo_needed", a detailed cinematic prompt for an AI video generator
    (Google Veo) describing the shot to generate

Visual grammar rules (hard requirements):
1. Produce {min_segments}-{max_segments} segments total for this transcript.
2. At least {video_pct:.0f}% of segments must be type "video" (motion beats static every time).
3. At most {max_screenshots} segments may be type "screenshot", and two screenshot segments
   must never be adjacent.
4. Include {min_veo}-{max_veo} "veo_needed" segments for shots no existing asset can cover -
   used sparingly, for visual variety on key beats.
5. Prefer reusing approved assets (type "video"/"screenshot" with a real asset_id) over
   requesting new generation. Only use "veo_needed" or "image_needed" when nothing in the
   manifest fits.
6. Every segment's visual MUST be semantically related to the words spoken during it - never
   pick an asset just because it's next in line.
7. Most segments should be 1.5-2.5 seconds. Do not pad with long static holds.
8. Do NOT invent scene overlays - this pipeline plans B-roll only.
9. Never reuse a rejected (non-approved) asset.

Respond with ONLY the JSON object, no prose, no markdown code fences.
""".format(
    min_segments=MIN_SEGMENTS, max_segments=MAX_SEGMENTS,
    video_pct=MIN_VIDEO_RATIO * 100, max_screenshots=MAX_SCREENSHOTS,
    min_veo=MIN_VEO_CLIPS, max_veo=MAX_VEO_CLIPS,
)


def _build_user_prompt(tool_name: str, script: str, transcript: dict, assets: list) -> str:
    words = transcript.get("words", [])
    segments = transcript.get("segments", [])
    duration = words[-1]["end"] if words else (segments[-1]["end"] if segments else 0.0)

    approved = [a for a in assets if a.get("approved")]
    asset_lines = []
    for a in approved:
        extra = f", motion={a.get('motion_score')}" if a.get("type") == "video" else ""
        asset_lines.append(f"  - id={a['id']} type={a['type']} path={a['path']}{extra}")

    return f"""Tool/topic: {tool_name}

Full script:
{script}

Total duration: {duration:.2f}s

Word-level transcript:
{json.dumps(words, indent=2)}

Sentence-level transcript (for context):
{json.dumps(segments, indent=2)}

Approved B-roll assets available for reuse:
{chr(10).join(asset_lines) if asset_lines else '(none - use image_needed/veo_needed for everything)'}

Plan the full visual timeline now, covering 0.0 to {duration:.2f} seconds with no gaps."""


def _extract_json(text: str) -> dict:
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in Claude's response")
    return json.loads(match.group(0))


def plan_storyboard(tool_name: str, script: str, transcript: dict, assets: list,
                     model: str = DEFAULT_MODEL) -> dict:
    client = anthropic.Anthropic()
    user_prompt = _build_user_prompt(tool_name, script, transcript, assets)

    response = client.messages.create(
        model=model,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return _extract_json(text)


def validate_storyboard(storyboard: dict, transcript: dict) -> list:
    """Returns a list of validation warnings/errors (empty = clean)."""
    issues = []
    segments = storyboard.get("segments", [])

    if not (MIN_SEGMENTS <= len(segments) <= MAX_SEGMENTS + 5):
        issues.append(f"Segment count {len(segments)} outside expected range")

    words = transcript.get("words", [])
    total_duration = words[-1]["end"] if words else 0.0

    prev_end = 0.0
    for i, seg in enumerate(segments):
        start, end = seg.get("startSec", 0), seg.get("endSec", 0)
        if abs(start - prev_end) > 0.15:
            issues.append(f"Segment {i} gap/overlap: expected start {prev_end:.2f}, got {start:.2f}")
        prev_end = end

    if total_duration and abs(prev_end - total_duration) > 0.5:
        issues.append(f"Storyboard ends at {prev_end:.2f}s, transcript ends at {total_duration:.2f}s")

    video_count = sum(1 for s in segments if s.get("type") == "video")
    if segments and video_count / len(segments) < MIN_VIDEO_RATIO:
        issues.append(f"Only {video_count}/{len(segments)} segments are video (need >= {MIN_VIDEO_RATIO:.0%})")

    screenshot_count = sum(1 for s in segments if s.get("type") == "screenshot")
    if screenshot_count > MAX_SCREENSHOTS:
        issues.append(f"{screenshot_count} screenshot segments exceeds max {MAX_SCREENSHOTS}")

    for i in range(len(segments) - 1):
        if segments[i].get("type") == "screenshot" and segments[i + 1].get("type") == "screenshot":
            issues.append(f"Segments {i} and {i + 1} are both screenshots (must not be adjacent)")

    return issues


def main():
    parser = argparse.ArgumentParser(description="Storyboard Agent")
    parser.add_argument("--reel-id", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    from pipeline.agents.pipeline_state import PipelineState
    state = PipelineState(args.reel_id)
    if not state.exists():
        print(f"Error: no pipeline state for {args.reel_id}. Run pipeline_state --init first.")
        sys.exit(1)

    manifest = state.get_output("curate")
    if not manifest:
        print("Error: run asset_curator first (no asset-manifest.json).")
        sys.exit(1)

    transcript_path = state.get_config("transcript_path", "")
    if not transcript_path or not os.path.exists(transcript_path):
        print(f"Error: transcript not found at '{transcript_path}'.")
        sys.exit(1)
    with open(transcript_path) as f:
        transcript = json.load(f)

    tool_name = state.get_config("tool_name", "")
    script = state.get_config("script", "")

    print(f"  Planning storyboard for: {tool_name}")
    storyboard = plan_storyboard(tool_name, script, transcript, manifest["assets"], model=args.model)
    storyboard.setdefault("reel_id", args.reel_id)

    issues = validate_storyboard(storyboard, transcript)
    for issue in issues:
        print(f"  WARNING: {issue}")

    output_path = os.path.join(state.reel_dir, "storyboard.json")
    with open(output_path, "w") as f:
        json.dump(storyboard, f, indent=2)

    segments = storyboard.get("segments", [])
    summary = {
        "segment_count": len(segments),
        "video": sum(1 for s in segments if s.get("type") == "video"),
        "screenshot": sum(1 for s in segments if s.get("type") == "screenshot"),
        "image_needed": sum(1 for s in segments if s.get("type") == "image_needed"),
        "veo_needed": sum(1 for s in segments if s.get("type") == "veo_needed"),
        "issues": issues,
    }
    print(f"  Segments: {summary['segment_count']} "
          f"(video={summary['video']}, screenshot={summary['screenshot']}, "
          f"image_needed={summary['image_needed']}, veo_needed={summary['veo_needed']})")
    state.complete_stage("storyboard", "storyboard.json", summary)


if __name__ == "__main__":
    main()

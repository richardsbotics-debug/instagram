"""Assembly Agent: build and validate the final ReelConfig JSON, optionally render."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

PIPELINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(PIPELINE_DIR)
PUBLIC_DIR = os.path.join(PROJECT_DIR, "public")
BROLL_DIR = os.path.join(PUBLIC_DIR, "broll")
CONFIG_DIR = os.path.join(PUBLIC_DIR, "config")
OUT_DIR = os.path.join(PROJECT_DIR, "out")
REMOTION_ENTRY = os.path.join(PROJECT_DIR, "src", "index.ts")

FPS = 25
MAX_CHUNK_WORDS = 3
MAX_CHUNK_CHARS = 18
GAP_TOLERANCE = 0.1


def _ffprobe_duration(filepath: str) -> float:
    cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", filepath]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    return float(result.stdout.strip() or 0.0)


def build_caption_chunks(words: list) -> list:
    chunks = []
    current = []

    def flush():
        if not current:
            return
        chunks.append({
            "text": " ".join(w["word"] for w in current),
            "startSec": current[0]["start"],
            "endSec": current[-1]["end"],
        })

    for w in words:
        current.append(w)
        text_len = sum(len(x["word"]) + 1 for x in current)
        ends_sentence = w["word"].rstrip()[-1:] in ".!?" if w["word"].strip() else False
        if len(current) >= MAX_CHUNK_WORDS or text_len >= MAX_CHUNK_CHARS or ends_sentence:
            flush()
            current = []
    flush()
    return chunks


def _asset_path_for(seg: dict, assets_by_id: dict) -> str | None:
    if seg.get("asset_path"):
        return seg["asset_path"]
    asset = assets_by_id.get(seg.get("asset_id"))
    return asset["path"] if asset else None


def build_broll_segments(storyboard: dict, assets_by_id: dict) -> tuple[list, list]:
    """Returns (brollSegments, errors)."""
    segments, errors = [], []

    for i, seg in enumerate(storyboard.get("segments", [])):
        seg_type = seg.get("type")
        if seg_type in ("image_needed", "veo_needed"):
            errors.append(f"Segment {i} ('{seg.get('label', '?')}') is unresolved ({seg_type}) - "
                          f"run image_resolver / veo_agent first")
            continue

        path = _asset_path_for(seg, assets_by_id)
        if not path:
            errors.append(f"Segment {i} ('{seg.get('label', '?')}') has no resolvable asset path")
            continue

        framing = seg.get("framing", {})
        entry = {
            "startSec": seg["startSec"],
            "endSec": seg["endSec"],
            "objectPosition": framing.get("objectPosition", "center center"),
            "scaleFrom": framing.get("scaleFrom", 1.0),
            "scaleTo": framing.get("scaleTo", 1.08 if seg_type == "screenshot" else 1.05),
            "_speech": seg.get("_speech", ""),
        }

        if seg_type == "video":
            # Video field is a bare filename under public/broll/clips/
            entry["video"] = os.path.basename(path)
        elif seg_type == "screenshot":
            # Image field is a path relative to public/broll/
            entry["image"] = path
        else:
            errors.append(f"Segment {i} has unknown type '{seg_type}'")
            continue

        segments.append(entry)

    return segments, errors


def validate(broll_segments: list, caption_chunks: list, assets_by_id: dict,
             storyboard_segments: list, avatar_path: str) -> tuple[list, list]:
    """Returns (errors, warnings)."""
    errors, warnings = [], []

    prev_end = 0.0
    for i, seg in enumerate(broll_segments):
        if seg["startSec"] - prev_end > GAP_TOLERANCE:
            errors.append(f"Gap of {seg['startSec'] - prev_end:.2f}s before segment {i}")
        prev_end = seg["endSec"]

    for i in range(len(caption_chunks) - 1):
        if caption_chunks[i]["text"].strip().lower() == caption_chunks[i + 1]["text"].strip().lower():
            errors.append(f"Duplicate consecutive caption text at chunk {i}: '{caption_chunks[i]['text']}'")

    if not caption_chunks:
        errors.append("No caption chunks generated")

    for seg in storyboard_segments:
        asset = assets_by_id.get(seg.get("asset_id"))
        if not asset:
            continue
        if asset.get("brightness", -1) >= 0 and asset["brightness"] < 30:
            warnings.append(f"Asset '{asset['id']}' is dark (brightness {asset['brightness']})")
        if asset.get("quality_score", 100) < 40:
            warnings.append(f"Asset '{asset['id']}' has low quality score ({asset['quality_score']})")

    if not os.path.exists(avatar_path):
        errors.append(f"Avatar file not found: {avatar_path}")

    for seg in broll_segments:
        if "video" in seg:
            full_path = os.path.join(BROLL_DIR, "clips", seg["video"])
        else:
            full_path = os.path.join(BROLL_DIR, seg["image"])
        if not os.path.exists(full_path):
            errors.append(f"Referenced asset file missing on disk: {full_path}")

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Assembly Agent")
    parser.add_argument("--reel-id", required=True)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--crossfade", type=int, default=5)
    parser.add_argument("--avatar-margin", type=int, default=-280)
    args = parser.parse_args()

    from pipeline.agents.pipeline_state import PipelineState
    state = PipelineState(args.reel_id)
    storyboard = state.get_output("storyboard")
    manifest = state.get_output("curate")
    if not storyboard or not manifest:
        print("Error: run asset_curator and storyboard first.")
        sys.exit(1)

    transcript_path = state.get_config("transcript_path", "")
    with open(transcript_path) as f:
        transcript = json.load(f)

    avatar_src = state.get_config("avatar_src", "")
    avatar_path = os.path.join(PUBLIC_DIR, avatar_src)

    assets_by_id = {a["id"]: a for a in manifest.get("assets", [])}
    storyboard_segments = storyboard.get("segments", [])

    broll_segments, errors = build_broll_segments(storyboard, assets_by_id)
    caption_chunks = build_caption_chunks(transcript.get("words", []))

    val_errors, val_warnings = validate(broll_segments, caption_chunks, assets_by_id,
                                        storyboard_segments, avatar_path)
    errors += val_errors

    for w in val_warnings:
        print(f"  WARN: {w}")
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        print(f"\n  Assembly blocked: {len(errors)} error(s). Fix and re-run.")
        sys.exit(1)

    duration_sec = _ffprobe_duration(avatar_path)
    duration_frames = round(duration_sec * FPS)

    config = {
        "id": args.reel_id,
        "duration": duration_frames,
        "avatarSrc": avatar_src,
        "avatarMarginTop": args.avatar_margin,
        "crossfadeFrames": args.crossfade,
        "brollSegments": broll_segments,
        "captionChunks": caption_chunks,
        "scenes": [],
    }

    os.makedirs(CONFIG_DIR, exist_ok=True)
    config_path = os.path.join(CONFIG_DIR, f"reel-config-{args.reel_id}.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"  Wrote {config_path} ({duration_frames} frames / {duration_sec:.2f}s)")

    summary = {
        "segments": len(broll_segments), "captions": len(caption_chunks),
        "duration_sec": duration_sec, "warnings": val_warnings,
    }
    state.complete_stage("assemble", f"reel-config-{args.reel_id}.json", summary)

    if args.render:
        os.makedirs(OUT_DIR, exist_ok=True)
        out_path = os.path.join(OUT_DIR, f"{args.reel_id}.mp4")
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
            json.dump({"config": config}, tmp)
            props_path = tmp.name

        print(f"  Rendering {out_path}...")
        cmd = ["npx", "remotion", "render", REMOTION_ENTRY, "DynamicReel", out_path,
               "--codec=h264", f"--props={props_path}"]
        subprocess.run(cmd, check=True, cwd=PROJECT_DIR)
        print(f"  Rendered: {out_path}")


if __name__ == "__main__":
    main()

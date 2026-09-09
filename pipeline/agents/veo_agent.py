"""Veo Agent: generate AI B-roll clips for storyboard segments marked veo_needed."""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys

PIPELINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(PIPELINE_DIR)
VEO_DIR = os.path.join(PROJECT_DIR, "ai-video-exploration")
SHOT_LISTS_DIR = os.path.join(VEO_DIR, "shot-lists")
OUTPUTS_DIR = os.path.join(VEO_DIR, "outputs")
CLIPS_DIR = os.path.join(PROJECT_DIR, "public", "broll", "clips")

STYLE_PREFIX = "Cinematic 9:16 vertical shot, natural lighting, shallow depth of field."


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-") or "shot"


def build_shot_list(storyboard: dict, reel_id: str) -> dict:
    shots = []
    for i, seg in enumerate(storyboard.get("segments", [])):
        if seg.get("type") != "veo_needed":
            continue
        shots.append({
            "number": len(shots) + 1,
            "name": _slugify(seg.get("label", f"segment-{i}")),
            "prompt": seg.get("veo_prompt", seg.get("label", "")),
            "_segment_index": i,
        })
    return {"reel_name": reel_id, "style_prefix": STYLE_PREFIX, "shots": shots}


def run_generation(shot_list_path: str, model: str, dry_run: bool) -> str | None:
    cmd = [sys.executable, os.path.join(VEO_DIR, "generate_broll.py"), shot_list_path,
           "--model", model, "--yes"]
    if dry_run:
        cmd.append("--dry-run")
    subprocess.run(cmd, check=True, cwd=VEO_DIR)
    if dry_run:
        return None

    with open(shot_list_path) as f:
        reel_name = json.load(f)["reel_name"]
    candidates = sorted(glob.glob(os.path.join(OUTPUTS_DIR, f"{reel_name}_*")))
    return candidates[-1] if candidates else None


def apply_clips(storyboard: dict, run_dir: str, reel_id: str, shots: list) -> int:
    resolved = 0
    for shot in shots:
        src = os.path.join(run_dir, f"shot{shot['number']:02d}_{shot['name']}_v1.mp4")
        if not os.path.exists(src):
            print(f"  Missing generated clip: {src}")
            continue

        filename = f"veo-{reel_id}-{shot['name']}.mp4"
        dest = os.path.join(CLIPS_DIR, filename)
        os.makedirs(CLIPS_DIR, exist_ok=True)
        shutil.copyfile(src, dest)

        seg = storyboard["segments"][shot["_segment_index"]]
        seg["type"] = "video"
        seg["asset_path"] = filename
        seg["source"] = "veo"
        resolved += 1
    return resolved


def main():
    parser = argparse.ArgumentParser(description="Veo Agent")
    parser.add_argument("--reel-id", required=True)
    parser.add_argument("--model", default="veo-3.1-fast",
                        choices=["veo-3.1-fast", "veo-3.1", "veo-3.0-fast"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from pipeline.agents.pipeline_state import PipelineState
    state = PipelineState(args.reel_id)
    storyboard = state.get_output("storyboard")
    if not storyboard:
        print("Error: no storyboard found. Run storyboard agent first.")
        sys.exit(1)

    shot_list = build_shot_list(storyboard, args.reel_id)
    if not shot_list["shots"]:
        print("  No veo_needed segments. Nothing to generate.")
        state.complete_stage("veo", "storyboard.json", {"generated": 0})
        return

    os.makedirs(SHOT_LISTS_DIR, exist_ok=True)
    shot_list_path = os.path.join(SHOT_LISTS_DIR, f"{args.reel_id}.json")
    with open(shot_list_path, "w") as f:
        json.dump(shot_list, f, indent=2)

    print(f"  {len(shot_list['shots'])} veo_needed segment(s) to generate")
    run_dir = run_generation(shot_list_path, args.model, args.dry_run)
    if args.dry_run:
        return

    if not run_dir:
        print("  Error: could not locate generation output directory.")
        sys.exit(1)

    resolved = apply_clips(storyboard, run_dir, args.reel_id, shot_list["shots"])

    storyboard_path = os.path.join(state.reel_dir, "storyboard.json")
    with open(storyboard_path, "w") as f:
        json.dump(storyboard, f, indent=2)

    print(f"  Resolved {resolved}/{len(shot_list['shots'])} veo clips")
    state.complete_stage("veo", "storyboard.json", {"generated": resolved})


if __name__ == "__main__":
    main()

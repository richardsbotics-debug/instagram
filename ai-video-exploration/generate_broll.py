#!/usr/bin/env python3
"""Generate cinematic B-roll clips using Google Veo via Gemini API."""

from __future__ import annotations
import argparse, json, os, time
from pathlib import Path

from google import genai
from google.genai import types

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
OUTPUT_DIR = SCRIPT_DIR / "outputs"

MODELS = {
    "veo-3.1-fast": "veo-3.1-fast-generate-preview",
    "veo-3.1": "veo-3.1-generate-preview",
    "veo-3.0-fast": "veo-3.0-fast-generate-001",
}

COST_PER_CLIP = {
    "veo-3.1-fast": 0.60,
    "veo-3.1": 1.60,
    "veo-3.0-fast": 0.60,
}


def generate_clip(client, model_id, prompt, shot_name, variation, output_dir,
                  aspect_ratio="9:16") -> Path | None:
    output_file = output_dir / f"{shot_name}_v{variation}.mp4"
    if output_file.exists():
        return output_file

    print(f"  Generating: {shot_name}_v{variation}")
    try:
        operation = client.models.generate_videos(
            model=model_id, prompt=prompt,
            config=types.GenerateVideosConfig(aspect_ratio=aspect_ratio, number_of_videos=1),
        )
        while not operation.done:
            time.sleep(10)
            operation = client.operations.get(operation)

        if not operation.response or not operation.response.generated_videos:
            return None

        video = operation.response.generated_videos[0]
        video_bytes = client.files.download(file=video.video)
        with open(output_file, "wb") as f:
            f.write(video_bytes)
        return output_file
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("shot_list", help="Shot list JSON path")
    parser.add_argument("--model", default="veo-3.1-fast", choices=list(MODELS.keys()))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", "-y", action="store_true")
    args = parser.parse_args()

    with open(CONFIG_PATH) as f:
        config = json.load(f)
    with open(args.shot_list) as f:
        shot_list = json.load(f)

    shots = shot_list.get("shots", [])
    style_prefix = shot_list.get("style_prefix", "")
    cost = len(shots) * COST_PER_CLIP.get(args.model, 0.60)

    if args.dry_run:
        for shot in shots:
            print(f"Shot {shot['number']}: {style_prefix} {shot['prompt']}")
        print(f"\nWould generate {len(shots)} clips (~${cost:.2f})")
        return

    if not args.yes:
        if input(f"Generate {len(shots)} clips (~${cost:.2f})? [y/N] ").lower() != "y":
            return

    client = genai.Client(api_key=config["gemini_api_key"])
    run_dir = OUTPUT_DIR / f"{shot_list.get('reel_name', 'reel')}_{time.strftime('%Y%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)

    for i, shot in enumerate(shots):
        full_prompt = f"{style_prefix} {shot['prompt']}".strip()
        if i > 0:
            print(f"  Waiting 60s (rate limit)...")
            time.sleep(60)
        generate_clip(client, MODELS[args.model], full_prompt,
                      f"shot{shot['number']:02d}_{shot['name']}", 1, run_dir)

    print(f"\nDone! Output: {run_dir}")


if __name__ == "__main__":
    main()

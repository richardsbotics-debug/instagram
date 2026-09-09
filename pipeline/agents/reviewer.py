"""Reviewer Agent: post-render QA. Checks duration, audio, black frames, and B-roll relevance."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

PIPELINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(PIPELINE_DIR)
PUBLIC_DIR = os.path.join(PROJECT_DIR, "public")
OUT_DIR = os.path.join(PROJECT_DIR, "out")

FPS = 25
DURATION_TOLERANCE_SEC = 1.0
BLACK_BRIGHTNESS = 10.0
BLACK_STDDEV = 5.0
DARK_WARN_BRIGHTNESS = 30.0
MAX_ITERATIONS = 3


def _ffprobe(filepath: str) -> dict:
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", filepath]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    return json.loads(result.stdout) if result.returncode == 0 else {}


def _extract_frame(video_path: str, timestamp_sec: float, out_path: str) -> bool:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-ss", str(max(timestamp_sec, 0.01)), "-i", video_path,
           "-frames:v", "1", "-q:v", "2", out_path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    return result.returncode == 0 and os.path.exists(out_path)


def _frame_stats(image_path: str) -> tuple[float, float]:
    """Returns (avg brightness 0-255, stddev)."""
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", image_path,
           "-vf", "signalstats", "-f", "null", "-"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    yavg, ystddev = [], []
    for line in result.stderr.split("\n"):
        if "YAVG" in line:
            try:
                yavg.append(float(line.split("YAVG=")[1].split()[0]))
            except (ValueError, IndexError):
                pass
        if "YSTDDEV" in line:
            try:
                ystddev.append(float(line.split("YSTDDEV=")[1].split()[0]))
            except (ValueError, IndexError):
                pass
    avg = sum(yavg) / len(yavg) if yavg else -1
    std = sum(ystddev) / len(ystddev) if ystddev else -1
    return avg, std


def check_duration(rendered_path: str, config: dict) -> list:
    issues = []
    probe = _ffprobe(rendered_path)
    fmt = probe.get("format", {})
    rendered_duration = float(fmt.get("duration", 0))
    expected_duration = config.get("duration", 0) / FPS
    if abs(rendered_duration - expected_duration) > DURATION_TOLERANCE_SEC:
        issues.append({
            "severity": "fail",
            "check": "duration",
            "message": f"Rendered duration {rendered_duration:.2f}s vs expected {expected_duration:.2f}s",
        })
    return issues


def check_audio(rendered_path: str) -> list:
    probe = _ffprobe(rendered_path)
    streams = probe.get("streams", [])
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    if not has_audio:
        return [{"severity": "fail", "check": "audio", "message": "No audio stream found in render"}]
    return []


def check_relevance(frame_path: str, speech: str, index: int) -> dict | None:
    """Best-effort semantic B-roll check via Claude vision. Never blocks on failure to call."""
    if not speech:
        return None
    try:
        import base64
        import anthropic

        with open(frame_path, "rb") as f:
            image_b64 = base64.standard_b64encode(f.read()).decode("utf-8")

        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=20,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                  "data": image_b64}},
                    {"type": "text", "text": (
                        f"The avatar is saying: \"{speech}\". Does this image plausibly relate to "
                        "that as B-roll? Reply with exactly one word: YES or NO."
                    )},
                ],
            }],
        )
        answer = "".join(b.text for b in response.content if b.type == "text").strip().upper()
        if answer.startswith("NO"):
            return {"severity": "warn", "check": "semantic_relevance",
                    "message": f"Segment {index} B-roll may not match speech: \"{speech[:60]}\""}
    except Exception:
        pass
    return None


def check_segments(rendered_path: str, config: dict, frames_dir: str) -> list:
    issues = []
    os.makedirs(frames_dir, exist_ok=True)
    segments = config.get("brollSegments", [])

    for i, seg in enumerate(segments):
        mid = (seg["startSec"] + seg["endSec"]) / 2
        frame_path = os.path.join(frames_dir, f"segment-{i:02d}.jpg")
        if not _extract_frame(rendered_path, mid, frame_path):
            issues.append({"severity": "warn", "check": "frame_extract",
                          "message": f"Could not extract frame for segment {i} at {mid:.2f}s"})
            continue

        brightness, stddev = _frame_stats(frame_path)
        if brightness < 0:
            continue

        if brightness < BLACK_BRIGHTNESS and stddev < BLACK_STDDEV:
            issues.append({"severity": "fail", "check": "black_frame",
                          "message": f"Segment {i} ('{seg.get('_speech', '')[:40]}') appears black "
                                     f"(brightness={brightness:.1f}, stddev={stddev:.1f})"})
        elif brightness < DARK_WARN_BRIGHTNESS:
            issues.append({"severity": "warn", "check": "dark_frame",
                          "message": f"Segment {i} is dark but has detail "
                                     f"(brightness={brightness:.1f}, stddev={stddev:.1f}) - likely OK"})

        relevance_issue = check_relevance(frame_path, seg.get("_speech", ""), i)
        if relevance_issue:
            issues.append(relevance_issue)

    if segments:
        prev_end = 0.0
        for i, seg in enumerate(segments):
            if seg["startSec"] - prev_end > 0.1:
                issues.append({"severity": "fail", "check": "coverage",
                              "message": f"Gap before segment {i} leaves the top half blank "
                                         f"(face-only stretch of {seg['startSec'] - prev_end:.2f}s)"})
            prev_end = seg["endSec"]

    return issues


def determine_verdict(issues: list) -> str:
    if any(i["severity"] == "fail" for i in issues):
        return "fail"
    if any(i["severity"] == "warn" for i in issues):
        return "warn"
    return "pass"


def main():
    parser = argparse.ArgumentParser(description="Reviewer Agent")
    parser.add_argument("--reel-id", required=True)
    parser.add_argument("--rendered", default=None)
    args = parser.parse_args()

    from pipeline.agents.pipeline_state import PipelineState
    state = PipelineState(args.reel_id)
    config = state.get_output("assemble")
    if not config:
        print("Error: run assembly first (no reel-config found).")
        sys.exit(1)

    rendered_path = args.rendered or os.path.join(OUT_DIR, f"{args.reel_id}.mp4")
    if not os.path.exists(rendered_path):
        print(f"Error: rendered video not found at {rendered_path}")
        sys.exit(1)

    frames_dir = os.path.join(state.reel_dir, "frames")

    issues = []
    issues += check_duration(rendered_path, config)
    issues += check_audio(rendered_path)
    issues += check_segments(rendered_path, config, frames_dir)

    verdict = determine_verdict(issues)
    for issue in issues:
        print(f"  [{issue['severity'].upper()}] {issue['check']}: {issue['message']}")

    report = {"reel_id": args.reel_id, "verdict": verdict, "issues": issues,
              "iteration": state.get_config("iteration", 1)}
    report_path = os.path.join(state.reel_dir, "review-report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n  Verdict: {verdict.upper()}")
    state.complete_stage("review", "review-report.json", {"verdict": verdict, "issue_count": len(issues)})

    if verdict == "fail":
        iteration = state.get_config("iteration", 1)
        if iteration >= MAX_ITERATIONS:
            print(f"  Max iterations ({MAX_ITERATIONS}) reached - manual intervention needed.")
        else:
            state.bump_iteration()
            print(f"  Loop back to storyboard/assembly (iteration {iteration + 1}/{MAX_ITERATIONS}).")
        sys.exit(1)


if __name__ == "__main__":
    main()

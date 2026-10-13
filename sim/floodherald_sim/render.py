"""Run one scenario and write an mp4 with overlay and program-triggered audio.

Usage:
    uv run python -m floodherald_sim.render scenarios/flood.json --video person.mp4 --out out/flood.mp4

The scenario only schedules inputs (upstream reports, local water
observations). The alarm, siren and voice prompts come from AlarmController
and Persuader reacting to those inputs and to YOLOv8 detections.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

from .audio import RATE, Mixer, load_wav, write_wav
from .detector import PersonDetector, zone_pixels
from .overlay import Overlay
from .persuader import Persuader
from .state_machine import AlarmController, Event, Local, Params, Upstream

ROOT = Path(__file__).resolve().parent.parent
# Program loudness of the rendered clip (EBU R128 broadcast level). The final
# edit sets the YouTube level (about -14 LUFS) once narration is added.
TARGET_LUFS = -23.0
TRUE_PEAK_DB = -2.0
AUDIO = ROOT / "assets" / "audio"


def expand_inputs(spec: list[dict]) -> list[tuple[float, str, str]]:
    """[{t, input, state, every?, until?}] -> sorted (t, input, state)."""
    out = []
    for item in spec:
        t, every, until = float(item["t"]), item.get("every"), item.get("until")
        if every is None:
            out.append((t, item["input"], item["state"]))
            continue
        while t <= float(until) + 1e-9:
            out.append((round(t, 3), item["input"], item["state"]))
            t += float(every)
    return sorted(out, key=lambda x: x[0])


def frame_plan(segments: list[dict], fps: float) -> list[tuple[int, bool]]:
    """Source frame index for every output frame, and whether it is a repeat."""
    plan = []
    for seg in segments:
        a, b = int(seg["from"] * fps), int(seg["to"] * fps)
        for r in range(int(seg.get("repeat", 1))):
            plan += [(i, r > 0) for i in range(a, b)]
    return plan


def footage_audio(video: Path, wav: Path, seconds: float) -> np.ndarray:
    """The clip's own sound, mono 48 kHz, cut or padded to the clip's video length.

    Decoded audio can run a little past the last frame (encoder padding); trimming
    each clip to its frame count keeps the next clip's sound aligned with its
    pictures. A clip without an audio track contributes silence.
    """
    n = round(seconds * RATE)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
         "-of", "csv=p=0", str(video)],
        capture_output=True, text=True,
    )
    if probe.returncode != 0:
        raise SystemExit(f"ffprobe failed on {video}: {probe.stderr.strip()}")
    if not probe.stdout.strip():
        print(f"note: {video} has no audio track; using silence for it")
        return np.zeros(n, dtype=np.float32)
    r = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
         "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(wav)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise SystemExit(f"could not extract the footage's audio: {r.stderr.strip()}")
    audio = load_wav(wav)[:n]
    return np.pad(audio, (0, n - len(audio)))


def normalize_loudness(src: Path, dst: Path) -> dict:
    """Two-pass loudnorm with a single linear gain: levels change, dynamics do not."""
    target = f"I={TARGET_LUFS}:TP={TRUE_PEAK_DB}:LRA=50"
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(src),
         "-af", f"loudnorm={target}:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    )
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    second = (f"loudnorm={target}:linear=true:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
              f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
              f":offset={m['target_offset']}:print_format=json")
    r = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-nostats", "-i", str(src), "-af", second,
         "-ar", str(RATE), "-c:a", "pcm_s16le", str(dst)],
        capture_output=True, text=True, check=True,
    )
    out = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    if out.get("normalization_type") != "linear":
        raise SystemExit(f"loudness normalisation fell back to {out.get('normalization_type')}")
    return out


def load_clips(videos: list[Path]) -> tuple[list[np.ndarray], list[int], float, int, int]:
    """Frames of every clip in order (one global index), frames per clip, fps, size.

    The clips must share size and frame rate: they are shown back to back as
    one continuous shot, never resized or retimed.
    """
    frames, counts, spec = [], [], None
    for video in videos:
        cap = cv2.VideoCapture(str(video))
        this = (cap.get(cv2.CAP_PROP_FPS) or 24.0,
                int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        if spec is not None and this != spec:
            raise SystemExit(f"{video}: {this} differs from the first clip {spec} (fps, width, height)")
        spec = this
        n = 0
        while True:
            ok, f = cap.read()
            if not ok:
                break
            frames.append(f)
            n += 1
        counts.append(n)
    fps, w, h = spec
    return frames, counts, fps, w, h


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario", type=Path)
    ap.add_argument("--video", type=Path, nargs="+", required=True,
                    help="one clip, or clips generated as one continuous shot, in order")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--weights", default="yolov8s.pt")
    ap.add_argument("--device", default="cpu", help="cpu or cuda:0")
    ap.add_argument("--footage-label", default="AI-generated footage (MiniMax H3)")
    ap.add_argument("--no-footage-audio", action="store_true", help="drop the footage's own sound")
    args = ap.parse_args()

    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise SystemExit("ffmpeg (with libx264) and ffprobe must be on PATH")
    sc = json.loads(args.scenario.read_text())
    frames, counts, fps, w, h = load_clips(args.video)
    # No "segments": every frame of every clip once, in order.
    plan = frame_plan(sc["segments"], fps) if "segments" in sc else [(i, False) for i in range(len(frames))]
    if max(i for i, _ in plan) >= len(frames):
        raise SystemExit(f"segments run past the end of the video ({len(frames)} frames)")
    # Generated footage is shown once, start to end, with its own sound.
    # Mapping or repeating source time is for development clips only.
    if not args.no_footage_audio and [i for i, _ in plan] != list(range(len(frames))):
        raise SystemExit(
            f"segments must play all {len(frames)} frames once, in order, to keep the footage's "
            "own sound; development clips that map or repeat time need --no-footage-audio"
        )
    tmp = Path(tempfile.mkdtemp())
    ambient = None
    if not args.no_footage_audio:
        ambient = np.concatenate([
            footage_audio(video, tmp / f"ambient{j}.wav", n / fps)
            for j, (video, n) in enumerate(zip(args.video, counts))
        ])

    p = sc["params"]
    ctl = AlarmController(Params(p["m"], p["t_travel"], p["upstream_timeout"], p["local_timeout"]))
    persuader = Persuader(cooldown=sc.get("prompt_cooldown", 8.0), routine=sc.get("zone_mode") != "recreation")
    zone = zone_pixels(sc["zone"], w, h)
    det = PersonDetector(args.weights, args.device)
    captions = json.loads((AUDIO / "captions.json").read_text())
    clips = {name: load_wav(AUDIO / f"{name}.wav") for name in ("warn_zone", "warn_flood")}
    siren_path = AUDIO / "siren.wav"
    siren = load_wav(siren_path) if siren_path.exists() else None

    inputs = expand_inputs(sc["inputs"])
    duration = len(plan) / fps
    mixer = Mixer(duration)
    overlay = Overlay(sc, det.name, args.device, args.footage_label, zone)
    cache: dict[int, list] = {}
    subtitle: tuple[float, float, str] | None = None
    alarm_since: float | None = None

    silent = tmp / "video.mp4"
    writer = cv2.VideoWriter(str(silent), cv2.VideoWriter_fourcc(*"mp4v"), fps, (1920, 1080))
    k = 0
    for n, (src, repeated) in enumerate(plan):
        t = n / fps
        while k < len(inputs) and inputs[k][0] <= t:
            ti, which, state = inputs[k]
            if which == "upstream":
                ctl.upstream_report(ti, Upstream(state))
            else:
                ctl.local_observation(ti, Local(state))
            k += 1
        ctl.tick(t)

        if src not in cache:
            cache[src] = det(frames[src], zone)
        dets = cache[src]
        in_zone = sum(d.in_zone for d in dets)

        if ctl.alarm and alarm_since is None:
            alarm_since = t
        if not ctl.alarm and alarm_since is not None:
            mixer.siren_on(alarm_since, t)
            alarm_since = None

        prompt = persuader.update(t, in_zone, ctl.alarm)
        if prompt:
            mixer.play(t, clips[prompt])
            cap_ = captions.get(prompt) or captions[f"{prompt}.wav"]
            subtitle = (t, t + cap_["seconds"], cap_["en"])
            ctl.events.append(Event(t, "PROMPT", prompt))

        sub = subtitle[2] if subtitle and subtitle[0] <= t < subtitle[1] else None
        writer.write(overlay.draw(frames[src], t, ctl, dets, in_zone, sub, repeated))
    if alarm_since is not None:
        mixer.siren_on(alarm_since, duration)
    writer.release()

    raw = tmp / "audio_raw.wav"
    write_wav(raw, mixer.render(siren, ambient))
    wav = tmp / "audio.wav"
    loud = normalize_loudness(raw, wav)
    print(f"audio: {loud['input_i']} -> {loud['output_i']} LUFS, true peak {loud['output_tp']} dBTP")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(wav),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
         "-shortest", str(args.out)],
        check=True,
    )
    log = args.out.with_suffix(".events.json")
    log.write_text(json.dumps([e.__dict__ for e in ctl.events], indent=1))
    print(f"wrote {args.out} ({duration:.1f} s) and {log}")


if __name__ == "__main__":
    main()

"""Assemble the Stage I demo video: cards, the H3 opening and the two simulation renders.

Run from the repo root after rendering the simulations and the cards:

    python3 video/assemble.py --daily sim/out/daily.mp4 --flood sim/out/flood.mp4 --out video/out/floodherald_stage1.mp4

Every footage frame is played once at its original speed (no freeze, cut,
loop or speed change); clip audio fades out over the final 0.5 s; cards fill
the gaps. Narration subtitles are burnt in. If video/narration/narration.json
exists (from make_narration.py), the narration clips are mixed in at their
cues, the programme sound is lowered by 6 dB under them, and subtitles last
as long as each clip; otherwise subtitle timing is estimated. The final mix
gets one linear gain towards -14 LUFS, capped by a -1 dBTP true peak.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CARDS = ROOT / "cards"
W, H, FPS = 1920, 1080, 24

# (kind, source, seconds). Clip lengths are measured; card lengths are chosen.
TIMELINE = [
    ("opening", ROOT / "opening_H3_final_12s.mp4", None),
    ("card", CARDS / "arch.png", 15.0),
    ("card", CARDS / "scenario1.png", 5.0),
    ("clip", "daily", None),
    ("card", CARDS / "scenario2.png", 5.0),
    ("clip", "flood", None),
    ("card", CARDS / "closing.png", 12.0),
]

# Narration cues: (segment index, start within the segment, text).
# Chinese announcements in the simulations: daily 3.0-6.39 s, flood 1.0-5.40 and 6.0-10.40 s.
NARRATION = [
    (0, 0.3, "Rain can fall in the hills while the swimming spot stays sunny."),
    (0, 5.3, "Once a wall of water appears, there may be ten seconds or less to get out."),
    (1, 0.5, "FloodHerald links an upstream sentinel to a riverside guardian by radio."),
    (1, 5.5, "A flood alert sounds the siren on site, with no internet needed."),
    (2, 0.3, "First: a no-swimming zone."),
    (3, 6.6, "Person detected: a spoken warning, with no flood alert or siren."),
    (4, 0.3, "Next: a swimming area, with a flood upstream."),
    (5, 10.6, "Everyone has left the riverbed, and the alarm stays on."),
    (5, 17.5, "The warning came before the water did."),
    (5, 21.0, "Recovery is compressed for this demo."),
    (5, 23.5, "Both water states must stay valid and normal, and the travel-time margin must expire."),
    (5, 29.5, "Zero detections never clear the alarm."),
    (6, 0.5, "For deployment, we plan a compact Raspberry Pi and UGen300 node for on-site person detection."),
    (6, 7.3, "Intended buyers are local governments. The code is on GitHub."),
]
# Chinese announcements inside the simulation renders (segment, start, end):
# narration must not overlap them.
BROADCASTS = [(3, 3.0, 6.4), (5, 1.0, 5.4), (5, 6.0, 10.4)]
NARRATION_DIR = ROOT / "narration"
TARGET_LUFS, TRUE_PEAK_DB = -14.0, -1.0  # YouTube-style level; a peak-capped linear gain may stop short
DUCK = 0.5  # programme sound under narration (-6 dB); post-production mix only
WORDS_PER_S = 2.5


def duration(path: Path) -> float:
    """Video length from its frame count, so clips are never trimmed."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
         "-show_entries", "stream=nb_read_frames,r_frame_rate", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    s = json.loads(out.stdout)["streams"][0]
    num, den = map(int, s["r_frame_rate"].split("/"))
    return int(s["nb_read_frames"]) * den / num


def ass_time(t: float) -> str:
    cs = round(t * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def load_narration() -> list[float] | None:
    """Length of each narration clip, or None when no clips have been generated."""
    meta = NARRATION_DIR / "narration.json"
    if not meta.exists():
        return None
    clips = json.loads(meta.read_text())["clips"]
    if [c["text"] for c in clips] != [t for _, _, t in NARRATION]:
        raise SystemExit("narration clips do not match NARRATION; rerun video/make_narration.py")
    seconds = []
    for i, c in enumerate(clips):
        # Time from the WAV itself, so a replaced clip cannot slip past the checks.
        if c["file"] != f"{i:02d}.wav":
            raise SystemExit(f"narration.json lists {c['file']} where {i:02d}.wav is expected")
        with wave.open(str(NARRATION_DIR / c["file"]), "rb") as w:
            seconds.append(w.getnframes() / w.getframerate())
        if abs(seconds[-1] - c["seconds"]) > 0.01:
            raise SystemExit(f"{c['file']} is {seconds[-1]:.3f} s but narration.json says {c['seconds']}")
    return seconds


def check_narration(seconds: list[float], lengths: list[float]) -> None:
    """Each clip must end before the next cue, inside its segment, and clear of the announcements."""
    for i, ((seg, at, text), dur) in enumerate(zip(NARRATION, seconds)):
        end = at + dur
        if end > lengths[seg] - 0.2:
            raise SystemExit(f"narration {i:02d} runs past its segment: {text}")
        if i + 1 < len(NARRATION) and NARRATION[i + 1][0] == seg and end > NARRATION[i + 1][1] - 0.2:
            raise SystemExit(f"narration {i:02d} runs into the next cue: {text}")
        for bseg, a, b in BROADCASTS:
            if bseg == seg and at < b + 0.15 and end > a - 0.15:
                raise SystemExit(f"narration {i:02d} overlaps a Chinese announcement: {text}")


def loudnorm(src: Path, dst: Path) -> dict:
    """One linear gain towards TARGET_LUFS, capped so the true peak stays at TRUE_PEAK_DB.

    No limiter or compression: if the peaks do not allow the full gain, the mix
    ends up quieter than the target rather than squashed.
    """
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af",
                        f"loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK_DB}:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, check=True)
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    gain = min(TARGET_LUFS - float(m["input_i"]), TRUE_PEAK_DB - float(m["input_tp"]))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", f"volume={gain:.2f}dB",
                    "-ar", "48000", "-c:a", "pcm_s16le", str(dst)], check=True)
    return {"input_i": m["input_i"], "gain_db": round(gain, 2),
            "output_i": round(float(m["input_i"]) + gain, 1), "output_tp": round(float(m["input_tp"]) + gain, 1)}


def write_ass(path: Path, starts: list[float], lengths: list[float],
              seconds: list[float] | None = None) -> None:
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV",
        "Style: Narr,IBM Plex Sans,46,&H00FFFFFF,&H00000000,&H99000000,0,0,3,2,0,2,120,120,44",
        "", "[Events]", "Format: Layer, Start, End, Style, Text",
    ]
    for i, (seg, at, text) in enumerate(NARRATION):
        start = starts[seg] + at
        spoken = seconds[i] if seconds else max(1.6, len(text.split()) / WORDS_PER_S)
        end = start + spoken + 0.3
        nxt = [starts[s] + a for s, a, _ in NARRATION[i + 1:]]
        if nxt:
            end = min(end, nxt[0] - 0.1)
        end = min(end, starts[seg] + lengths[seg])
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Narr,{text}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--daily", type=Path, required=True)
    ap.add_argument("--flood", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    inputs, chains, lengths = [], [], []

    def add(*opts: str) -> int:
        add.n += 1
        inputs.extend(opts)
        return add.n
    add.n = -1

    for k, (kind, src, secs) in enumerate(TIMELINE):
        if kind == "clip":
            src = args.daily if src == "daily" else args.flood
        if kind == "card":
            v = add("-loop", "1", "-framerate", str(FPS), "-t", f"{secs}", "-i", str(src))
            a = add("-f", "lavfi", "-t", f"{secs}", "-i", "anullsrc=r=48000:cl=stereo")
            chains.append(f"[{v}:v]scale={W}:{H},format=yuv420p,setsar=1[v{k}];[{a}:a]anull[a{k}]")
            lengths.append(secs)
            continue
        secs = duration(src)
        lengths.append(secs)
        v = add("-i", str(src))
        if kind == "opening":
            o = add("-loop", "1", "-framerate", str(FPS), "-t", f"{secs}", "-i", str(CARDS / "opening.png"))
            chains.append(
                f"[{v}:v]scale={W}:-2,crop={W}:{H},fps={FPS},setsar=1[b{k}];"
                f"[b{k}][{o}:v]overlay=format=auto,format=yuv420p[v{k}];"
            )
        else:
            chains.append(f"[{v}:v]scale={W}:{H},fps={FPS},format=yuv420p,setsar=1[v{k}];")
        # Fade the clip's sound over its last 0.5 s so the cut to a silent card is not abrupt;
        # every frame still plays (audio mix only).
        chains[-1] += (f"[{v}:a]aresample=48000,aformat=channel_layouts=stereo,"
                       f"atrim=0:{secs},apad=whole_dur={secs},afade=t=out:st={secs - 0.5}:d=0.5[a{k}]")

    starts = [sum(lengths[:i]) for i in range(len(lengths))]
    seconds = load_narration()
    if seconds:
        check_narration(seconds, lengths)
    tmp = Path(tempfile.mkdtemp())
    ass = tmp / "narration.ass"
    write_ass(ass, starts, lengths, seconds)
    n = len(TIMELINE)
    concat = "".join(f"[v{k}][a{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=1[vc][ac]"
    graph = ";".join(chains) + ";" + concat + f";[vc]subtitles={ass}[vout]"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    video, programme = tmp / "video.mp4", tmp / "programme.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph,
         "-map", "[vout]", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), str(video),
         "-map", "[ac]", "-c:a", "pcm_s16le", str(programme)],
        check=True,
    )
    mixed = programme
    if seconds:
        mixed = tmp / "mixed.wav"
        cues = [(starts[seg] + at, starts[seg] + at + dur) for (seg, at, _), dur in zip(NARRATION, seconds)]
        under = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in cues)
        ins, parts = ["-i", str(programme)], [f"[0:a]volume='if({under},{DUCK},1)':eval=frame[p]"]
        for i, (a, _) in enumerate(cues):
            ins += ["-i", str(NARRATION_DIR / f"{i:02d}.wav")]
            ms = round(a * 1000)
            parts.append(f"[{i + 1}:a]aformat=channel_layouts=stereo,adelay={ms}|{ms}[n{i}]")
        mix = "[p]" + "".join(f"[n{i}]" for i in range(len(cues))) + \
              f"amix=inputs={len(cues) + 1}:normalize=0:duration=first[m]"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex",
                        ";".join(parts) + ";" + mix, "-map", "[m]", "-c:a", "pcm_s16le", str(mixed)],
                       check=True)
    final = tmp / "final.wav"
    loud = loudnorm(mixed, final)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(final),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", str(args.out)], check=True)
    print(f"audio: {'with' if seconds else 'without'} narration, {loud['input_i']} -> {loud['output_i']} LUFS, "
          f"gain {loud['gain_db']} dB, true peak {loud['output_tp']} dBTP")
    (args.out.with_suffix(".ass")).write_text(ass.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"wrote {args.out} ({sum(lengths):.2f} s); segment starts:",
          ", ".join(f"{s:.2f}" for s in starts))


if __name__ == "__main__":
    main()

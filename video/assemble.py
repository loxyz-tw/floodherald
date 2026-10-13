"""Assemble the Stage I demo video: cards, the H3 opening and the two simulation renders.

Run from the repo root after rendering the simulations and the cards:

    python3 video/assemble.py --daily sim/out/daily.mp4 --flood sim/out/flood.mp4 --out video/out/floodherald_stage1.mp4

Every clip is played once, unedited (no freeze, cut, loop or speed change);
cards fill the gaps. Narration is burnt in as subtitles (subtitle draft); a
narration audio track is planned and not implemented yet.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CARDS = ROOT / "cards"
W, H, FPS = 1920, 1080, 24

# (kind, source, seconds). Clip lengths are measured; card lengths are chosen.
TIMELINE = [
    ("opening", ROOT / "opening_H3_final_12s.mp4", None),
    ("card", CARDS / "arch.png", 15.0),
    ("card", CARDS / "scenario1.png", 3.0),
    ("clip", "daily", None),
    ("card", CARDS / "scenario2.png", 4.0),
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
    (6, 6.0, "Intended buyers are local governments. The code is on GitHub."),
]
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


def write_ass(path: Path, starts: list[float], lengths: list[float]) -> None:
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
        end = start + max(1.6, len(text.split()) / WORDS_PER_S) + 0.3
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
        chains[-1] += (f"[{v}:a]aresample=48000,aformat=channel_layouts=stereo,"
                       f"atrim=0:{secs},apad=whole_dur={secs}[a{k}]")

    starts = [sum(lengths[:i]) for i in range(len(lengths))]
    tmp = Path(tempfile.mkdtemp())
    ass = tmp / "narration.ass"
    write_ass(ass, starts, lengths)
    n = len(TIMELINE)
    concat = "".join(f"[v{k}][a{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=1[vc][ac]"
    graph = ";".join(chains) + ";" + concat + f";[vc]subtitles={ass}[vout]"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph,
         "-map", "[vout]", "-map", "[ac]", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
         "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", str(args.out)],
        check=True,
    )
    (args.out.with_suffix(".ass")).write_text(ass.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"wrote {args.out} ({sum(lengths):.2f} s); segment starts:",
          ", ".join(f"{s:.2f}" for s in starts))


if __name__ == "__main__":
    main()

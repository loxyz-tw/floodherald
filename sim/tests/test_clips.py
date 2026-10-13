"""Multi-clip loading and footage-audio alignment (FI-01). Needs ffmpeg, no model."""

import subprocess

import numpy as np
import pytest

from floodherald_sim.audio import RATE
from floodherald_sim.render import footage_audio, load_clips


def make_clip(path, seconds, size="64x48", fps=24, audio_seconds=None, color=None):
    src = (f"color=c={color}:size={size}:rate={fps}:duration={seconds}" if color
           else f"testsrc=size={size}:rate={fps}:duration={seconds}")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", src]
    if audio_seconds is not None:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={audio_seconds}"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    cmd += ["-c:a", "aac"] if audio_seconds is not None else ["-an"]
    subprocess.run(cmd + [str(path)], check=True)
    return path


def test_clips_share_one_global_frame_index(tmp_path):
    a = make_clip(tmp_path / "a.mp4", 1, color="black")
    b = make_clip(tmp_path / "b.mp4", 0.5, color="white")
    frames, counts, fps, w, h = load_clips([a, b])
    assert counts == [24, 12] and len(frames) == 36
    assert (fps, w, h) == (24, 64, 48)
    means = [float(f.mean()) for f in frames]
    assert max(means[:24]) < 40 and min(means[24:]) > 215, "clip B starts at global frame 24"


def test_frames_keep_their_order(tmp_path):
    a = make_clip(tmp_path / "a.mp4", 1)  # testsrc changes every frame
    b = make_clip(tmp_path / "b.mp4", 0.5, color="white")
    frames, *_ = load_clips([a, b])
    raw = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", str(a), "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
        capture_output=True, check=True,
    ).stdout
    ref = np.frombuffer(raw, np.uint8).reshape(-1, 48, 64, 3)
    for i in range(24):  # each loaded frame matches the decoder's frame i, not another one
        diffs = [np.abs(frames[i].astype(int) - r.astype(int)).mean() for r in ref]
        assert int(np.argmin(diffs)) == i


@pytest.mark.parametrize("other", [{"size": "80x48"}, {"fps": 25}])
def test_mismatched_clip_is_rejected(tmp_path, other):
    a = make_clip(tmp_path / "a.mp4", 1)
    b = make_clip(tmp_path / "b.mp4", 1, **other)
    with pytest.raises(SystemExit):
        load_clips([a, b])


def test_audio_is_cut_or_padded_to_the_video_length(tmp_path):
    long_ = make_clip(tmp_path / "long.mp4", 1, audio_seconds=1.5)
    short = make_clip(tmp_path / "short.mp4", 1, audio_seconds=0.5)
    for clip in (long_, short):
        audio = footage_audio(clip, tmp_path / f"{clip.stem}.wav", 1.0)
        assert len(audio) == RATE
        assert np.abs(audio[int(0.1 * RATE):int(0.4 * RATE)]).max() > 0.1, "the start is kept"
    assert np.abs(footage_audio(short, tmp_path / "s2.wav", 1.0)[int(0.7 * RATE):]).max() == 0


def test_clip_without_audio_contributes_silence(tmp_path):
    clip = make_clip(tmp_path / "mute.mp4", 1)
    audio = footage_audio(clip, tmp_path / "mute.wav", 1.0)
    assert len(audio) == RATE and not audio.any()


def test_mix_is_normalised_to_target_loudness_with_one_gain(tmp_path):
    from floodherald_sim.audio import write_wav
    from floodherald_sim.render import TARGET_LUFS, normalize_loudness

    t = np.arange(4 * RATE) / RATE
    loud = 0.8 * np.sin(2 * np.pi * 440 * t) * (1 + (t > 2))  / 2  # two levels
    src, dst = tmp_path / "src.wav", tmp_path / "dst.wav"
    write_wav(src, loud)
    out = normalize_loudness(src, dst)
    assert out["normalization_type"] == "linear"
    assert abs(float(out["output_i"]) - TARGET_LUFS) < 1.0


def test_dynamic_fallback_is_refused(tmp_path, monkeypatch):
    """Levels may change, dynamics may not: a non-linear result stops the render."""
    import floodherald_sim.render as render

    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        body = ('{"input_i": "-10", "input_tp": "-1", "input_lra": "5", "input_thresh": "-20", '
                '"target_offset": "0", "output_i": "-23", "output_tp": "-2", '
                '"normalization_type": "%s"}' % ("linear" if len(calls) == 1 else "dynamic"))
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="log\n" + body)

    monkeypatch.setattr(render.subprocess, "run", fake_run)
    with pytest.raises(SystemExit):
        render.normalize_loudness(tmp_path / "a.wav", tmp_path / "b.wav")

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "kokoro==0.9.4",
#     "misaki[en]==0.9.4",
#     "torch==2.8.0",
#     "huggingface_hub",
#     "numpy",
#     "scipy",
#     "soundfile",
#     "en_core_web_sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl",
# ]
#
# [tool.uv.sources]
# torch = { index = "pytorch-cpu" }
#
# [[tool.uv.index]]
# name = "pytorch-cpu"
# url = "https://download.pytorch.org/whl/cpu"
# explicit = true
# ///
"""Generate the English narration clips for the demo video (CPU only).

Run from the repo root:

    CUDA_VISIBLE_DEVICES="" uv run --no-project video/make_narration.py

TTS: Kokoro-82M v1.0 (Apache-2.0), weights pinned to a Hugging Face commit,
voice af_heart. One clip per cue in assemble.NARRATION, written to
video/narration/NN.wav (48 kHz mono, 16-bit PCM) with their lengths in
video/narration/narration.json; assemble.py places them and times the
subtitles from these lengths.
"""

import os

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from huggingface_hub import hf_hub_download
from kokoro import KModel, KPipeline
from scipy.signal import resample_poly

from assemble import NARRATION

REPO_ID = "hexgrad/Kokoro-82M"
REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
VOICE = "af_heart"
SPEED = 1.0
MODEL_RATE = 24000
OUT_RATE = 48000
PEAK_DBFS = -1.0
SILENCE_DBFS = -45.0

OUT_DIR = Path(__file__).resolve().parent / "narration"


def fetch(name: str) -> str:
    return hf_hub_download(REPO_ID, name, revision=REVISION)


def trim(audio: np.ndarray) -> np.ndarray:
    loud = np.flatnonzero(np.abs(audio) > 10 ** (SILENCE_DBFS / 20))
    return audio[loud[0] : loud[-1] + 1]


def main() -> None:
    torch.manual_seed(0)
    model = KModel(repo_id=REPO_ID, config=fetch("config.json"), model=fetch("kokoro-v1_0.pth")).to("cpu").eval()
    pipeline = KPipeline(lang_code="a", repo_id=REPO_ID, model=model)
    voice = fetch(f"voices/{VOICE}.pt")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index = []
    for i, (_, _, text) in enumerate(NARRATION):
        parts = [r.audio.numpy() for r in pipeline(text, voice=voice, speed=SPEED)]
        audio = resample_poly(trim(np.concatenate(parts)), OUT_RATE, MODEL_RATE)
        audio *= 10 ** (PEAK_DBFS / 20) / np.max(np.abs(audio))
        name = f"{i:02d}.wav"
        sf.write(OUT_DIR / name, audio, OUT_RATE, subtype="PCM_16")
        index.append({"file": name, "text": text, "seconds": round(len(audio) / OUT_RATE, 3)})
        print(f"{name} {index[-1]['seconds']:5.2f} s  {text}")
    meta = {"model": REPO_ID, "revision": REVISION, "voice": VOICE, "speed": SPEED, "clips": index}
    (OUT_DIR / "narration.json").write_text(json.dumps(meta, indent=1) + "\n")


if __name__ == "__main__":
    main()

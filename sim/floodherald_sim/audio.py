"""Offline audio track.

Siren and voice are placed only by events the program raised. The footage's
own ambient sound (water, footsteps) can run underneath, unedited.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

RATE = 48_000
# Siren gain: the demo only needs to show that it sounds, not how loud a
# field siren is. Lower still while a voice prompt plays.
SIREN_GAIN = 0.06
SIREN_GAIN_UNDER_VOICE = 0.025


def load_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        if w.getsampwidth() != 2:
            raise ValueError(f"{path}: expected 16-bit PCM")
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        if w.getnchannels() > 1:
            data = data.reshape(-1, w.getnchannels()).mean(axis=1)
        if w.getframerate() != RATE:
            n = int(len(data) * RATE / w.getframerate())
            data = np.interp(np.linspace(0, len(data) - 1, n), np.arange(len(data)), data)
    return data.astype(np.float32)


class Mixer:
    def __init__(self, duration: float):
        self.buf = np.zeros(int(duration * RATE) + RATE, dtype=np.float32)
        self.siren_mask = np.zeros_like(self.buf)
        self.voice_mask = np.zeros_like(self.buf)
        self.voice = np.zeros_like(self.buf)

    def siren_on(self, start: float, end: float) -> None:
        a, b = int(start * RATE), int(end * RATE)
        self.siren_mask[a:b] = 1.0

    def play(self, t: float, clip: np.ndarray) -> None:
        a = int(t * RATE)
        b = min(a + len(clip), len(self.voice))
        self.voice[a:b] += clip[: b - a]
        self.voice_mask[a:b] = 1.0

    def render(self, siren: np.ndarray | None, ambient: np.ndarray | None = None) -> np.ndarray:
        out = self.voice.copy()
        if ambient is not None:
            n = min(len(ambient), len(out))
            duck = np.where(self.voice_mask[:n] > 0, 0.5, 1.0)
            out[:n] += ambient[:n] * duck
        if siren is not None and self.siren_mask.any():
            loop = np.resize(siren, len(self.buf))
            duck = np.where(self.voice_mask > 0, SIREN_GAIN_UNDER_VOICE, SIREN_GAIN)
            out += loop * self.siren_mask * duck
        peak = float(np.abs(out).max()) or 1.0
        return out / max(peak, 1.0)


def write_wav(path: Path, data: np.ndarray) -> None:
    pcm = (np.clip(data, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())

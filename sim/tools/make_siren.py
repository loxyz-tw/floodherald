"""Synthesize a seamlessly looping two-tone siren (no downloaded samples).

Run from the sim/ directory:

    uv run --no-project --with numpy --with soundfile tools/make_siren.py

Output: assets/audio/siren.wav, 48 kHz mono 16-bit PCM, 4 s = 4 hi-lo cycles.
Each cycle holds 450 Hz for 0.5 s then 600 Hz for 0.5 s, with a short glide
centred on each change so there is no click. The glide is symmetric, so every
cycle still holds a whole number of waveform periods (225 + 300) and the clip
loops without a click. A soft second harmonic gives a horn-like tone without
the harsh high harmonics of a sweep siren; it only illustrates that a siren
sounds, not what a field siren sounds like.
"""

from pathlib import Path

import numpy as np
import soundfile as sf

RATE = 48000
F_LOW = 450.0
F_HIGH = 600.0
HALF_S = 0.5  # each tone
GLIDE_S = 0.02  # frequency glide centred on each change
CYCLES = 4
PEAK_DBFS = -3.0

OUT = Path(__file__).resolve().parent.parent / "assets" / "audio" / "siren.wav"


def main() -> None:
    n = int(RATE * 2 * HALF_S * CYCLES)
    t = np.arange(n) / RATE
    pos = np.mod(t, 2 * HALF_S)  # position inside one hi-lo cycle
    # Distance (signed) to the nearest tone change at 0, HALF_S and 2*HALF_S.
    freq = np.where(pos < HALF_S, F_LOW, F_HIGH)
    for edge, a, b in ((HALF_S, F_LOW, F_HIGH), (2 * HALF_S, F_HIGH, F_LOW), (0.0, F_HIGH, F_LOW)):
        x = (pos - edge) / GLIDE_S + 0.5
        near = (x > 0) & (x < 1)
        freq = np.where(near, a + (b - a) * x, freq)
    phase = 2 * np.pi * np.cumsum(freq) / RATE
    wave = np.sin(phase) + 0.2 * np.sin(2 * phase)
    wave *= 10 ** (PEAK_DBFS / 20) / np.max(np.abs(wave))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sf.write(OUT, wave, RATE, subtype="PCM_16")
    print(f"{OUT}: {n / RATE:.2f} s, {RATE} Hz mono, end phase {phase[-1] / (2 * np.pi):.3f} periods")


if __name__ == "__main__":
    main()

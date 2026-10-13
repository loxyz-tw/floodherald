"""Spoken warnings driven by person detection.

Person detection never touches the alarm: it only decides when to play a
zone warning. The cooldown limits voice prompts only; the siren is driven by
AlarmController alone.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Persuader:
    cooldown: float  # minimum gap between voice prompts, seconds
    # False for a recreation area where being in the water is allowed: no
    # routine warning, only flood evacuation prompts while the alarm is on.
    routine: bool = True
    last_prompt_t: float | None = None

    def update(self, t: float, people_in_zone: int, alarm: bool) -> str | None:
        """Return the prompt to play now ("warn_zone" / "warn_flood"), or None."""
        if people_in_zone <= 0 or not (alarm or self.routine):
            return None  # checked before the cooldown, so a skipped prompt costs nothing
        if self.last_prompt_t is not None and t - self.last_prompt_t < self.cooldown:
            return None
        self.last_prompt_t = t
        return "warn_flood" if alarm else "warn_zone"

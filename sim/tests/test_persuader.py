"""Spoken prompts: routine zone warnings vs. a recreation area (FP-04)."""

from floodherald_sim.persuader import Persuader


def test_recreation_area_is_silent_without_alarm_and_keeps_cooldown_free():
    p = Persuader(cooldown=6, routine=False)
    assert p.update(0.0, 3, alarm=False) is None
    assert p.last_prompt_t is None
    assert p.update(1.0, 3, alarm=True) == "warn_flood", "flood prompt is not delayed"


def test_cooldown_limits_voice_only():
    p = Persuader(cooldown=6, routine=False)
    assert p.update(1.0, 2, alarm=True) == "warn_flood"
    assert p.update(4.0, 2, alarm=True) is None
    assert p.update(7.0, 1, alarm=True) == "warn_flood"


def test_no_people_no_prompt_even_in_alarm():
    assert Persuader(cooldown=6, routine=False).update(1.0, 0, alarm=True) is None


def test_routine_zone_warning_unchanged():
    p = Persuader(cooldown=8)
    assert p.update(3.0, 1, alarm=False) == "warn_zone"
    assert p.update(4.0, 1, alarm=False) is None

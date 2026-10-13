"""Acceptance cases from the Codex plan review (S-01, S-03)."""

from floodherald_sim.state_machine import AlarmController, Local, Params, Upstream

M, T_TRAVEL, TIMEOUT = 10.0, 30.0, 3.0


def make(t_travel=T_TRAVEL):
    return AlarmController(Params(m=M, t_travel=t_travel, upstream_timeout=TIMEOUT, local_timeout=TIMEOUT))


def feed(c, start, end, up=None, local=None, step=1.0):
    """Send a fresh report every `step` seconds on the given inputs."""
    t = start
    while t <= end + 1e-9:
        if up is not None:
            c.upstream_report(t, up)
        if local is not None:
            c.local_observation(t, local)
        c.tick(t)
        t += step


def test_flood_latches_without_any_person_input():
    c = make()
    c.upstream_report(0.0, Upstream.FLOOD)
    assert c.alarm


def test_upstream_normal_alone_does_not_end():
    c = make()
    c.upstream_report(0.0, Upstream.FLOOD)
    feed(c, 1, 60, up=Upstream.NORMAL, local=Local.NON_NORMAL)
    assert c.alarm


def test_local_normal_alone_does_not_end():
    c = make()
    c.upstream_report(0.0, Upstream.FLOOD)
    feed(c, 1, 60, up=Upstream.UNKNOWN, local=Local.NORMAL)
    assert c.alarm


def test_both_normal_but_travel_time_not_reached():
    c = make()
    c.upstream_report(0.0, Upstream.FLOOD)
    feed(c, 1, 29, up=Upstream.NORMAL, local=Local.NORMAL)  # M met at t=11, T_travel not until 30
    assert c.alarm


def test_all_three_conditions_end_alarm():
    c = make()
    c.upstream_report(0.0, Upstream.FLOOD)
    feed(c, 1, 31, up=Upstream.NORMAL, local=Local.NORMAL)
    assert not c.alarm
    assert c.events[-1].kind == "CLEARED"
    assert c.events[-1].t == 30.0


def test_single_normal_report_then_silence_never_ends():
    c = make()
    c.upstream_report(0.0, Upstream.FLOOD)
    c.upstream_report(1.0, Upstream.NORMAL)
    c.local_observation(1.0, Local.NORMAL)
    for t in range(2, 100):
        c.tick(float(t))
    assert c.alarm


def test_updates_stop_just_before_m_then_resume_restarts_m():
    c = make()
    c.upstream_report(0.0, Upstream.FLOOD)
    feed(c, 1, 25, up=Upstream.NORMAL, local=Local.NORMAL)
    # Local observations stop at t=25; upstream keeps reporting.
    feed(c, 26, 32, up=Upstream.NORMAL)
    assert c.alarm, "stale local view must not count as normal"
    feed(c, 33, 41, up=Upstream.NORMAL, local=Local.NORMAL)
    assert c.alarm, "local M restarts from t=33, so not met before t=43"
    feed(c, 42, 43, up=Upstream.NORMAL, local=Local.NORMAL)
    assert not c.alarm


def test_unknown_near_end_of_m_resets():
    c = make()
    c.upstream_report(0.0, Upstream.FLOOD)
    feed(c, 21, 29, up=Upstream.NORMAL, local=Local.NORMAL)
    c.local_observation(29.5, Local.UNKNOWN)
    feed(c, 30, 35, up=Upstream.NORMAL, local=Local.NORMAL)
    assert c.alarm


def test_new_flood_restarts_everything():
    c = make()
    c.upstream_report(0.0, Upstream.FLOOD)
    feed(c, 1, 25, up=Upstream.NORMAL, local=Local.NORMAL)
    c.upstream_report(25.5, Upstream.FLOOD)
    feed(c, 26, 50, up=Upstream.NORMAL, local=Local.NORMAL)
    assert c.alarm, "T_travel now counts from 25.5"
    feed(c, 51, 56, up=Upstream.NORMAL, local=Local.NORMAL)
    assert not c.alarm


def test_unknown_travel_time_never_ends():
    c = make(t_travel=None)
    c.upstream_report(0.0, Upstream.FLOOD)
    feed(c, 1, 200, up=Upstream.NORMAL, local=Local.NORMAL)
    assert c.alarm


def test_stale_or_duplicate_report_is_ignored():
    c = make()
    c.upstream_report(10.0, Upstream.FLOOD)
    c.upstream_report(5.0, Upstream.NORMAL)
    assert c.up_state is Upstream.FLOOD
    assert c.up_normal_since is None


def _simultaneous(order):
    """SC-01: inputs at the same instant are applied before deciding to end."""
    c = make()
    c.upstream_report(0.0, Upstream.FLOOD)
    feed(c, 1, 29, up=Upstream.NORMAL, local=Local.NORMAL)
    for which in order:
        if which == "up":
            c.upstream_report(30.0, Upstream.NORMAL)
        else:
            c.local_observation(30.0, Local.NON_NORMAL)
    c.tick(30.0)
    return c


def test_simultaneous_non_normal_blocks_end_upstream_first():
    assert _simultaneous(["up", "local"]).alarm


def test_simultaneous_non_normal_blocks_end_local_first():
    assert _simultaneous(["local", "up"]).alarm


def test_simultaneous_unknown_blocks_end():
    c = make()
    c.upstream_report(0.0, Upstream.FLOOD)
    feed(c, 1, 29, up=Upstream.NORMAL, local=Local.NORMAL)
    c.upstream_report(30.0, Upstream.UNKNOWN)
    c.local_observation(30.0, Local.NORMAL)
    c.tick(30.0)
    assert c.alarm


def test_gap_longer_than_timeout_between_ticks_restarts_m():
    """SC-02: a late report cannot hide the gap before it (24 fps ticks)."""
    c = AlarmController(Params(m=8, t_travel=1, upstream_timeout=3, local_timeout=3))
    c.upstream_report(0.0, Upstream.FLOOD)
    ups = [1.0, 4.01] + [5.01 + i for i in range(20)]
    i, cleared = 0, None
    for n in range(1, 30 * 24):
        t = n / 24
        while i < len(ups) and ups[i] <= t:
            c.upstream_report(ups[i], Upstream.NORMAL)
            i += 1
        c.local_observation(t, Local.NORMAL)
        c.tick(t)
        if not c.alarm and cleared is None:
            cleared = t
    assert cleared is not None and cleared >= 12.01


def test_stale_input_is_shown_as_unknown():
    c = make()
    c.upstream_report(0.0, Upstream.NORMAL)
    c.local_observation(0.0, Local.NORMAL)
    assert c.effective_upstream(2.0) == "NORMAL"
    assert c.effective_upstream(5.0) == "UNKNOWN (stale)"
    assert c.effective_local(5.0) == "UNKNOWN (stale)"

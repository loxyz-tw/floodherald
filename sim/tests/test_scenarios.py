"""Scenario timelines drive the expected alarm story without any video."""

import json
from pathlib import Path

from floodherald_sim.render import expand_inputs
from floodherald_sim.state_machine import AlarmController, Local, Params, Upstream

SC = Path(__file__).resolve().parent.parent / "scenarios"


def run(name, until, fps=24):
    sc = json.loads((SC / name).read_text())
    p = sc["params"]
    ctl = AlarmController(Params(p["m"], p["t_travel"], p["upstream_timeout"], p["local_timeout"]))
    inputs, k, trace = expand_inputs(sc["inputs"]), 0, []
    for n in range(int(until * fps)):
        t = n / fps
        while k < len(inputs) and inputs[k][0] <= t:
            ti, which, state = inputs[k]
            (ctl.upstream_report(ti, Upstream(state)) if which == "upstream"
             else ctl.local_observation(ti, Local(state)))
            k += 1
        ctl.tick(t)
        trace.append((t, ctl.alarm, [c.met for c in ctl.conditions(t)]))
    return ctl, trace


def test_daily_never_alarms():
    ctl, trace = run("daily.json", 12.25)
    assert not any(a for _, a, _ in trace)


def test_flood_story():
    ctl, trace = run("flood.json", 35.75)
    at = lambda s: next(x for x in trace if x[0] >= s)
    assert not at(0.5)[1]
    assert at(1.0)[1], "FLOOD latches at the first report"
    # Upstream M met at 24, local water still non-normal: latched.
    t, alarm, met = at(26)
    assert alarm and met[0] and not met[1]
    # T_travel met at 30, local normal only since 28: latched.
    t, alarm, met = at(31)
    assert alarm and met[0] and not met[1] and met[2]
    cleared = [e.t for e in ctl.events if e.kind == "CLEARED"]
    assert cleared == [33.0]
    assert not any(e.detail.endswith("stale") for e in ctl.events if e.kind == "RESET")

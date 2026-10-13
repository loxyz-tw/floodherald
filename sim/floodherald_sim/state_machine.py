"""Downstream alarm rules: a selected subset of Appendix C2 (proposal v6.4).

Scope of this simulation (see README): daytime, valid calibrated view, one
guardian, no restarts, no packet faults, WATCH disabled, every flood event is
treated as delivered and acknowledged. Not covered: duplicate/out-of-band
packets, non-volatile latch, option A/B hardware isolation, night and
battery-saving siren schedule.

All times are simulation seconds supplied by the caller; nothing here reads a
wall clock or counts video frames.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Upstream(str, Enum):
    NORMAL = "NORMAL"  # every upstream trigger normal, sensors healthy
    FLOOD = "FLOOD"
    UNKNOWN = "UNKNOWN"  # fault, self-test pending, or any non-normal report


class Local(str, Enum):
    NORMAL = "NORMAL"  # valid view; water below reference line, colour recovered
    NON_NORMAL = "NON_NORMAL"
    UNKNOWN = "UNKNOWN"  # no valid observation or calibration lost


@dataclass
class Params:
    m: float  # continuous-normal period required on each input (demo seconds)
    t_travel: float | None  # site travel-time margin; None = unknown, never ends
    upstream_timeout: float  # a report older than this counts as UNKNOWN
    local_timeout: float


@dataclass
class Event:
    t: float
    kind: str
    detail: str = ""


@dataclass
class AlarmController:
    params: Params
    alarm: bool = False
    last_flood_t: float | None = None
    # Latest accepted observation on each input and its timestamp.
    up_state: Upstream = Upstream.UNKNOWN
    up_t: float | None = None
    local_state: Local = Local.UNKNOWN
    local_t: float | None = None
    # Start of the current unbroken normal period on each input, if any.
    up_normal_since: float | None = None
    local_normal_since: float | None = None
    events: list[Event] = field(default_factory=list)

    # --- inputs -----------------------------------------------------------
    # Inputs only record observations (and latch on FLOOD). Ending is decided
    # in tick(), after every input for that instant has been applied, so the
    # order of simultaneous inputs cannot end the alarm.

    def upstream_report(self, t: float, state: Upstream) -> None:
        if self.up_t is not None and t <= self.up_t:
            return  # stale or duplicate report never extends anything
        self._expire(t)  # a gap longer than the timeout before this report
        self.up_state, self.up_t = state, t
        if state is Upstream.FLOOD:
            was = self.alarm
            self.alarm = True
            self.last_flood_t = t
            # A new FLOOD restarts the normal period on both inputs.
            self.up_normal_since = None
            self.local_normal_since = None
            if not was:
                self.events.append(Event(t, "FLOOD", "latched"))
        elif state is Upstream.NORMAL:
            if self.up_normal_since is None:
                self.up_normal_since = t
        else:
            self._break("upstream", t, state.value)

    def local_observation(self, t: float, state: Local) -> None:
        if self.local_t is not None and t <= self.local_t:
            return
        self._expire(t)
        self.local_state, self.local_t = state, t
        if state is Local.NORMAL:
            if self.local_normal_since is None:
                self.local_normal_since = t
        else:
            self._break("local", t, state.value)

    # --- evaluation -------------------------------------------------------

    def tick(self, t: float) -> None:
        """Apply timeouts, then decide whether the alarm ends at time t."""
        self._expire(t)
        if self.alarm and all(c.met for c in self.conditions(t)):
            self.alarm = False
            self.events.append(Event(t, "CLEARED"))

    def _expire(self, t: float) -> None:
        """Reset a normal period whose input went quiet for longer than its timeout.

        Called with the time of an incoming observation as well as on every
        tick, so a late report cannot hide the gap before it.
        """
        p = self.params
        if self.up_normal_since is not None and (
            self.up_t is None or t - self.up_t > p.upstream_timeout
        ):
            self._break("upstream", t, "stale")
        if self.local_normal_since is not None and (
            self.local_t is None or t - self.local_t > p.local_timeout
        ):
            self._break("local", t, "stale")

    def effective_upstream(self, t: float) -> str:
        if self.up_t is None:
            return "-"
        if t - self.up_t > self.params.upstream_timeout:
            return "UNKNOWN (stale)"
        return self.up_state.value

    def effective_local(self, t: float) -> str:
        if self.local_t is None:
            return "-"
        if t - self.local_t > self.params.local_timeout:
            return "UNKNOWN (stale)"
        return self.local_state.value.replace("_", "-")

    def conditions(self, t: float) -> list["Condition"]:
        p = self.params
        up = _held(self.up_normal_since, t)
        local = _held(self.local_normal_since, t)
        since_flood = None if self.last_flood_t is None else t - self.last_flood_t
        return [
            Condition("Upstream normal", up, p.m),
            Condition("Local water normal", local, p.m),
            Condition(
                "Since last FLOOD",
                since_flood,
                p.t_travel,  # None target: never met
            ),
        ]

    def _break(self, which: str, t: float, why: str) -> None:
        attr = f"{which}_normal_since" if which == "local" else "up_normal_since"
        if getattr(self, attr) is not None:
            setattr(self, attr, None)
            self.events.append(Event(t, "RESET", f"{which}: {why}"))


@dataclass
class Condition:
    label: str
    elapsed: float | None  # None = not running
    target: float | None  # None = unknown, cannot be met

    @property
    def met(self) -> bool:
        return self.elapsed is not None and self.target is not None and self.elapsed >= self.target


def _held(since: float | None, t: float) -> float | None:
    return None if since is None else t - since

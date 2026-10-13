"""1920x1080 frame: footage with detections on the left, alarm panel on the right."""

from __future__ import annotations

import cv2
import numpy as np

from .state_machine import AlarmController

W, H = 1920, 1080
VID_W, VID_H = 1440, 810
TOP = 80
PANEL_X = VID_W + 20
FONT = cv2.FONT_HERSHEY_SIMPLEX

WHITE, GREY, DIM = (240, 240, 240), (170, 170, 170), (90, 90, 90)
RED, GREEN, AMBER, CYAN = (40, 40, 220), (80, 190, 80), (40, 170, 240), (220, 200, 60)


def text(img, s, org, scale=0.8, color=WHITE, thick=2):
    # Drop shadow with the same thickness: a thicker outline shifts glyph advances.
    cv2.putText(img, s, (org[0] + 2, org[1] + 2), FONT, scale, (0, 0, 0), thick, cv2.LINE_AA)
    cv2.putText(img, s, org, FONT, scale, color, thick, cv2.LINE_AA)


class Overlay:
    def __init__(self, scenario: dict, model: str, device: str, footage_label: str, zone: np.ndarray):
        self.title = scenario["title"]
        self.params = scenario["params"]
        self.backend = "GPU (CUDA)" if device.startswith("cuda") else "CPU"
        self.model = model
        self.footage_label = footage_label
        self.zone = zone
        recreation = scenario.get("zone_mode") == "recreation"
        self.zone_label = "Recreation area (simulated setting)" if recreation else "No-swimming zone"
        self.in_word = "in area" if recreation else "in zone"
        self.idle_note = "Siren off; routine warnings disabled" if recreation else "Siren off; zone warnings only"
        # Timed on-screen notes: [{"from": s, "to": s, "lines": [...]}]
        self.notes = scenario.get("notes", [])

    def draw(self, frame, t, ctl: AlarmController, dets, in_zone, subtitle, repeated) -> np.ndarray:
        h, w = frame.shape[:2]
        sx, sy = VID_W / w, VID_H / h
        vid = cv2.resize(frame, (VID_W, VID_H))
        zone = (self.zone.reshape(-1, 2) * [sx, sy]).astype(np.int32)
        cv2.polylines(vid, [zone], True, AMBER, 3, cv2.LINE_AA)
        text(vid, self.zone_label, tuple(zone.min(axis=0) + [8, 30]), 0.8, AMBER)
        for d in dets:
            x1, y1, x2, y2 = (int(d.box[0] * sx), int(d.box[1] * sy), int(d.box[2] * sx), int(d.box[3] * sy))
            c = RED if d.in_zone else CYAN
            cv2.rectangle(vid, (x1, y1), (x2, y2), c, 3)
            text(vid, f"person {d.score:.2f}", (x1, max(y1 - 10, 24)), 0.7, c)
        text(vid, self.footage_label, (20, VID_H - 20), 0.7, GREY)
        if repeated:
            text(vid, "Footage looped", (VID_W - 240, VID_H - 20), 0.7, GREY)
        ny = 40
        for note in self.notes:
            if note["from"] <= t < note["to"]:
                for line in note["lines"]:
                    text(vid, line, (20, ny), 0.8, WHITE)
                    ny += 36

        img = np.full((H, W, 3), 18, np.uint8)
        img[TOP:TOP + VID_H, :VID_W] = vid
        if ctl.alarm and int(t * 2) % 2 == 0:
            cv2.rectangle(img, (0, TOP), (VID_W - 1, TOP + VID_H - 1), RED, 10)

        text(img, "LAPTOP SIMULATION", (20, 50), 1.1, WHITE, 3)
        text(img, "Offline simulation replay", (22, 72), 0.5, DIM, 1)
        text(img, f"{self.title}", (420, 50), 1.0, GREY)
        text(img, f"t = {t:5.1f} s", (W - 230, 50), 0.9, GREY)

        y = TOP + 40
        if ctl.alarm:
            text(img, "ALARM LATCHED", (PANEL_X, y), 1.2, RED, 3)
        elif any(e.kind == "CLEARED" for e in ctl.events):
            text(img, "ALARM ENDED", (PANEL_X, y), 1.2, GREEN, 3)
        else:
            text(img, "NO ALARM", (PANEL_X, y), 1.2, GREEN, 3)

        y += 60
        up = ctl.effective_upstream(t)
        loc = ctl.effective_local(t)
        text(img, "Upstream", (PANEL_X, y), 0.75, GREY)
        text(img, up, (PANEL_X + 200, y), 0.75, RED if up == "FLOOD" else WHITE)
        text(img, "Injected", (PANEL_X + 200, y + 26), 0.55, DIM, 1)
        y += 70
        text(img, "Local water", (PANEL_X, y), 0.75, GREY)
        text(img, loc, (PANEL_X + 200, y), 0.75, WHITE)
        text(img, "Injected", (PANEL_X + 200, y + 26), 0.55, DIM, 1)

        y += 80
        n = len(dets)
        label = "0 people detected" if n == 0 else f"{n} detected, {in_zone} {self.in_word}"
        text(img, label, (PANEL_X, y), 0.8, WHITE if n == 0 else AMBER)
        text(img, "Person detection never starts", (PANEL_X, y + 30), 0.55, DIM, 1)
        text(img, "or stops the alarm", (PANEL_X, y + 52), 0.55, DIM, 1)

        y += 110
        # End conditions only mean something once a FLOOD has latched the alarm.
        conds = ctl.conditions(t) if ctl.last_flood_t is not None else []
        if conds:
            text(img, "Alarm ends only when all hold:", (PANEL_X, y), 0.65, GREY)
        else:
            text(img, "No FLOOD received", (PANEL_X, y), 0.65, GREY)
            text(img, self.idle_note, (PANEL_X, y + 28), 0.55, DIM, 1)
            y += 3 * 62  # keep the rest of the panel in place
        for c in conds:
            y += 62
            text(img, c.label, (PANEL_X, y), 0.62, GREEN if c.met else WHITE)
            frac = 0.0 if c.elapsed is None or not c.target else min(c.elapsed / c.target, 1.0)
            cv2.rectangle(img, (PANEL_X, y + 10), (PANEL_X + 400, y + 26), DIM, 1)
            cv2.rectangle(img, (PANEL_X, y + 10), (PANEL_X + int(400 * frac), y + 26), GREEN if c.met else AMBER, -1)
            if c.target is None:
                val = "travel time unknown"
            elif c.elapsed is None:
                val = f"reset (need {c.target:g} s)"
            else:
                val = f"{min(c.elapsed, c.target):4.1f} / {c.target:g} s"
            text(img, val, (PANEL_X + 250, y), 0.55, GREY, 1)

        y += 80
        if conds:
            text(img, "Demo timing - not field thresholds", (PANEL_X, y), 0.55, AMBER, 1)
            tt = self.params["t_travel"]
            text(img, f"M = {self.params['m']:g} s, T_travel = {'unknown' if tt is None else f'{tt:g} s'}", (PANEL_X, y + 26), 0.55, AMBER, 1)
        y += 70
        text(img, f"Model: {self.model} (real inference)", (PANEL_X, y), 0.55, GREY, 1)
        text(img, f"Backend: {self.backend}", (PANEL_X, y + 26), 0.55, GREY, 1)
        text(img, "Selected alarm-rule simulation", (PANEL_X, y + 52), 0.55, GREY, 1)
        text(img, "Voice: AI-generated (Google Gemini TTS)", (PANEL_X, y + 78), 0.55, GREY, 1)

        if subtitle:
            (tw, _), _ = cv2.getTextSize(subtitle, FONT, 1.1, 2)
            text(img, subtitle, ((W - tw) // 2, H - 70), 1.1, WHITE, 2)
        return img

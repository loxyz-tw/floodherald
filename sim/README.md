# FloodHerald laptop simulation

Stage I laptop simulation for the downstream guardian. It shows, on one
laptop:

- **real person detection** (Ultralytics YOLOv8, person class only) on a video,
  with a no-swimming zone test on each person's foot point;
- **injected water states**: upstream reports (NORMAL / FLOOD / UNKNOWN) and
  local water observations (NORMAL / NON-NORMAL / UNKNOWN) come from a
  scenario timeline, not from a sensor or a water-state model;
- **the alarm rules** (a selected subset of the downstream alarm rules in our Stage I proposal, Appendix C2; the subset is listed below), run
  by a real state machine;
- **program-triggered sound**: the siren and the spoken zone warnings are
  placed in the audio track by events the program raises; the footage's own
  ambient sound runs underneath.

This is an **offline laptop simulation**: the program steps through the
video in simulation time and writes an mp4. The timeline is simulation time,
not measured processing latency, so the output shows neither real-time CPU
performance nor that the siren keeps sounding while inference stalls.
Nothing here runs on the UGen300; the planned deployment moves person
detection to a small host with the UGen300 (Stage II).

## Selected alarm-rule simulation — scope

Covered:

- FLOOD latches the alarm whether or not anyone is detected; person
  detection never starts, delays or stops it.
- The alarm ends only when (1) upstream has been continuously and freshly
  NORMAL for M, (2) the local water has been continuously and freshly NORMAL
  for M, and (3) T_travel has passed since the last FLOOD.
- A new FLOOD, any non-normal or UNKNOWN input, or an input that stops
  updating (older than its timeout) restarts the normal period. Old or
  duplicate reports never extend it. Unknown T_travel means the alarm never
  ends on its own.
- Voice prompts have a cooldown; the siren does not.

Assumed, not simulated: daytime with a valid, calibrated view; one guardian;
no restarts; no packet loss or duplicates; WATCH disabled; every flood event
delivered and acknowledged.

Not implemented or verified: LoRa link and ACK resend, non-volatile latch,
guardian options A/B and their power isolation, night and battery-saving
siren schedule, upstream triggers, the downstream water-state check itself.

M and T_travel in the scenarios are **demo timings, not field thresholds**.

## Run

Prerequisites: `uv`; `ffmpeg` with libx264 and `ffprobe` on PATH (used to mux the final
mp4); the H3 clips (not distributed in this repository; prompts and workflows are in `../video/`, see `THIRD_PARTY_NOTICES.md`). On the first run
Ultralytics downloads `yolov8s.pt`; for an offline demo, run once beforehand
so the weights are present.

```bash
uv sync
uv run pytest -q
uv run python -m floodherald_sim.render scenarios/daily.json --video ../video/person_H3_12s_seed2026101501.mp4 --out out/daily.mp4 --device cpu
```

Flash-flood scenario (two clips generated as one continuous shot, each
played once, in order):

```bash
uv run python -m floodherald_sim.render scenarios/flood.json --video "../video/flood_person_H3_20s_seed2026101602+2026101611.mp4" ../video/recede_H3_15.75s_seed2026101621+2026101631.mp4 --out out/flood.mp4 --device cpu
```

`daily.json` is a no-swimming zone: a person in the zone gets a spoken
warning. `flood.json` sets `"zone_mode": "recreation"`: being in the water is
allowed, so there is no routine warning; only after a FLOOD latches does a
person in the area get the evacuation prompt. `notes` adds timed on-screen
text (for example, that the recovery timeline is compressed).

The audio of each render targets approximately -23 LUFS (EBU R128) with one
linear gain, so levels change but not the dynamics; the siren is mixed low
because the demo only shows that it sounds. Our final-edit target, after
narration is added, is about -14 LUFS.

`--device cuda:0` uses the GPU. Each run writes the mp4 and an
`.events.json` log (FLOOD latched, prompts, resets, CLEARED).

Scenario files only schedule inputs; they cannot set the alarm state.
Rule for the H3 clips: each clip is played once from start to end,
unedited, and its own sound (water, footsteps) stays underneath the program
audio; scenario timing is fitted to the clip, not the other way round. By
default the renderer refuses any `segments` that do not play every source
frame exactly once, in order.

Development clips may map or repeat source time with `segments` only
together with `--no-footage-audio`; frames from a repeat are labelled
"Footage looped" (a plain cut is not labelled).

## Footage and labels

The person footage is generated with MiniMax H3 and labelled
"AI-generated footage" on screen. Detection results on generated footage
show that the program reacts to real inference; they are not a measure of
recall on real streams.

## License

AGPL-3.0 (see `LICENSE`), because the program uses Ultralytics YOLOv8.
Third-party components and generated assets: `THIRD_PARTY_NOTICES.md`.

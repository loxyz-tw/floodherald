# Third-Party Notices

This simulation is licensed under AGPL-3.0 (see `LICENSE`). It uses or
contains the third-party components and generated assets listed below. Each
entry gives the name, version, license, source and how we use it. Licenses
were checked on 2026-10-13 against the linked originals.

## 1. Ultralytics YOLOv8 (person detection)

- Package: `ultralytics` 8.4.176 (version locked in `uv.lock`)
- Weights: `yolov8s.pt` (COCO-pretrained, downloaded by Ultralytics on first run; not committed)
- License: AGPL-3.0 — <https://github.com/ultralytics/ultralytics/blob/main/LICENSE>;
  licensing options: <https://www.ultralytics.com/license>
- Source: <https://github.com/ultralytics/ultralytics>, <https://pypi.org/project/ultralytics/>
- Use: runs person detection on the simulation video frames. Because the
  program uses this AGPL-3.0 component, the whole simulation is released
  under AGPL-3.0 with complete source in this repository.

## 2. MiniMax H3 (AI-generated people in the demo video)

- Model: MiniMax H3, `MiniMaxAI/MiniMax-H3` on Hugging Face, revision
  `42ed227ee7df40d41602854ae760620d6eb651fe` (license date 2026-08-02)
- License: MiniMax H3 Community License Agreement —
  <https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/42ed227ee7df40d41602854ae760620d6eb651fe/LICENSE>;
  MiniMax license Q&A:
  <https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/42ed227ee7df40d41602854ae760620d6eb651fe/docs/QA-about-License.md>
- Use: generates the video clips of people near the river that the
  simulation runs on. The people in these clips are not real. The model
  weights are not included in this repository.
- Labeling: every frame and every published copy of these clips carries the
  label **"AI-generated / MiniMax H3"**. This follows Exhibit A item 12
  (machine-generated content must be clearly and prominently disclosed when
  published) and Section IV.2 (display "MiniMax H3").
- Territory (Section V.4): the license is granted only within the
  "Applicable Territory", which is worldwide excluding the European Union,
  the United Kingdom, the Republic of Korea and the United States of
  America. Section V.4 states: "You may not use, reproduce, modify,
  distribute, or display the MiniMax H3 Works or any of their Outputs or
  results outside the Applicable Territory."
- Generated with the open weights run locally in Taiwan (inside the
  Applicable Territory). The generated clips are shown in the demo video;
  the clip files themselves (mp4, and frames used to start a segment) are
  not distributed in this repository. Prompt, seed and workflow are
  recorded for each clip.
- Clips (prompt and ComfyUI workflow with the seed in its file name, in
  `video/`; 960×544, 24 fps). These clips were generated with ComfyUI from the
  local files `minimax_h3_fl2va_pruned_int8_convrot.safetensors` and
  `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`, plus a turbo LoRA that
  differs per clip:
  - `person_H3_12s_seed2026101501.mp4` (seed 2026101501, LoRA
    `minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors`): one
    person, routine-warning scenario `scenarios/daily.json`; played once,
    unedited.
  - `opening_H3_final_12s.mp4` (seed 2026101404, LoRA
    `minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors`): video
    opening only, not used by the simulation.
  - `flood_person_H3_20s_seed2026101602+2026101611.mp4` (two segments,
    seeds 2026101602 and 2026101611; the second starts from the first
    segment's last frame) followed by
    `recede_H3_15.75s_seed2026101621+2026101631.mp4` (two segments, seeds
    2026101621 and 2026101631; the first segment is conditioned on the
    flood clip's last frame as its first frame and on a calm, empty frame of
    the flood clip as its last frame; the second starts from the first
    segment's last frame),
    all with LoRA
    `minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors`:
    three people, a mud flood and its recession, flash-flood scenario
    `scenarios/flood.json`; each clip played once, in order, unedited. The
    flood and its recession are generated pictures; the water states the
    program uses are injected, not read from these pictures.
- Required notice (Section III.4, for any distribution of MiniMax H3 Works):
  "MiniMax H3 is licensed under the MiniMax H3 Community License Agreement,
  Copyright © 2026 MiniMax. All Rights Reserved."

## 3. Gemini 3.8 Flash TTS (Mandarin warning voice)

- Service: Google Gemini API, model `gemini-3.8-flash-tts`, used through the
  Google AI Studio Playground (free tier) on 2026-10-13
- Settings: speaker Fola (default speaker and description); Style and
  Expression unset; the text box held only the spoken line
- Terms: Gemini API Additional Terms of Service —
  <https://ai.google.dev/gemini-api/terms>. Section "Use of Generated
  Content": "Google won't claim ownership over that content. You acknowledge
  that Google may generate the same or similar content for others and that
  we reserve all rights to do so." The same section requires complying with
  applicable law in using generated content, "which may require the
  provision of attribution". On the free tier, inputs and outputs may be
  used to improve Google's products
  (<https://ai.google.dev/gemini-api/docs/pricing>), subject to the
  account's applicable data-use terms (Unpaid and Paid Services sections of
  <https://ai.google.dev/gemini-api/terms>); the inputs were only the two
  public warning lines. The Google APIs Terms of Service and usage policies
  also apply; the quotes above are not a complete list of obligations.
- Files: the downloads are kept unchanged in `assets/audio/source/`
  (`warn_zone_gemini.wav`, `warn_flood_gemini.wav`, 24 kHz mono).
  `tools/make_tts.py` trims silence, resamples and normalises them into
  `assets/audio/warn_zone.wav` and `assets/audio/warn_flood.wav`.
- Labeling: the voice is synthetic and is labelled "AI-generated voice
  (Google Gemini TTS)" wherever the demo video is published.
- An earlier draft of these two Chinese prompts used Kokoro-82M-v1.1-zh
  (Apache-2.0); the current prompts do not use it.
- English narration for the demo video is planned (Kokoro, English voice)
  and is not part of these files yet; its model version and license will be
  listed here when it is added.

## 4. Siren sound

- Source: synthesized by our own code, `tools/make_siren.py`
  (two-tone 450/600 Hz, 0.5 s each, soft second harmonic). No sound
  samples were downloaded.
- License: part of this project, AGPL-3.0.
- File: `assets/audio/siren.wav`

## 5. Development test video

- A synthetic clip made by pasting a crop of `bus.jpg` (bundled with the
  Ultralytics package, AGPL-3.0) onto a plain background. Used only for
  development testing; not committed and not included in the submitted
  demo video.

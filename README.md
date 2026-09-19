# matinee

**Your VHS tape already is the script. matinee gives it a voice.**

[VHS](https://github.com/charmbracelet/vhs) records a terminal session into a GIF from a `.tape` file. matinee takes that same tape and produces a **narrated, chaptered, captioned video** — in 16:9 for your README and talks, and 9:16 for social — without you writing a single timestamp.

Everything except one optional step runs locally and free. There is no API key.

## Why

A GIF shows what your tool does. It cannot tell anyone *why* they should care, and it cannot be posted anywhere that expects a video with sound.

The usual answer is to record your screen and edit it by hand, which drifts out of date the moment the UI changes. matinee's answer is that you already maintain a script for the demo — the tape — so the video should be generated from it, the same way the GIF is.

## What it does

```text
your-repo/demo.tape
        │
        ├─ record    run the tape, encode the frames          → terminal.mp4
        ├─ build     chapter titles + timings, from the tape  → project.json
        ├─ narrate   your lines, spoken                       → narration.wav
        ├─ captions  word-level timings, from the audio       → project.json
        └─ render    composite, both aspect ratios            → out/*.mp4
```

Chapters come from the comments already in your tape:

```tape
# Search
Type "/"
Sleep 500ms
```

You write one `script.yaml` per repo — a title, a subtitle, an accent colour, and one line of narration per chapter. Nothing in it is a timestamp.

## Quickstart

```bash
brew install vhs ffmpeg whisper.cpp
npm install

# whisper model. base.en is English-only; other languages need ggml-base.bin.
mkdir -p ~/.cache/whisper && cd ~/.cache/whisper
curl -LO https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
```

Then, from the repo:

```bash
make video PROJECT=y509
```

`out/y509-16x9.mp4` and `out/y509-9x16.mp4`. `make studio` opens the [Remotion](https://www.remotion.dev) studio to preview interactively.

Three worked examples ship in `projects/`: [y509](https://github.com/kanywst/y509) (9 chapters), [prpr](https://github.com/kanywst/prpr) (6) and [brtc](https://github.com/kanywst/brtc) (2). Their tapes differ in theme, resolution, framerate and comment style, which is the point.

## Adding your repo

1. Write `projects/<id>/script.yaml`: `id`, `title`, `subtitle`, `repo`, `accent`, `lang`, a `source` block naming your repo and its tape, and `narration` keyed by chapter title.
2. Add two lines to `projects/registry.ts` — an import and an array entry.
3. `make video PROJECT=<id>`

### What your tape needs

Chapters come from section comments, so the tape needs them:

- A **numbered** comment is always a section: `# 3. Search`.
- An **unnumbered** comment is a section when it stands alone. A block of several consecutive comment lines is treated as prose and ignored, which keeps the explanatory paragraphs in real tapes out of the chapter list.
- No section comments at all is an error, not an empty video.

If your tape assumes a built binary, build it first — matinee runs the tape verbatim and does not build anything for you.

## Narration

| `lang` | Backend | Notes |
| --- | --- | --- |
| `en` | macOS `say` | Built in, nothing to install. macOS only. |
| `ja` | [VOICEVOX](https://voicevox.hiroshiba.jp/) | `docker run -d -p 50021:50021 voicevox/voicevox_engine:cpu-latest`. **Each character has its own terms of use — check the one you pick before publishing.** |

Each chapter is synthesised on its own and laid down at its chapter's start time, so the voice stays locked to what is on screen even when you reword a line. A line that overruns its chapter is reported by name rather than silently overlapping the next one.

Captions are produced by transcribing the audio that was actually generated, not by reusing the script. That is deliberate — it gets the real timings, including the pauses the TTS chose — but it means a word the TTS slurs can come back misspelled. Read the captions before you publish.

## The one paid step

`scripts/broll.py` generates an abstract clip to sit behind the title card, via [fal.ai](https://fal.ai). It is opt-in, it needs `FAL_KEY`, and it is the only thing here that costs money. Without it the title card is a flat colour, which is a perfectly good title card.

`--dry-run` prints the request and the cache key without generating anything. Results are cached on a hash of the model and every parameter, so re-running after editing anything else is free.

## Requirements

- `vhs`, `ffmpeg` (with `ffprobe`), `node`, `uv`
- `whisper-cli` and a model, for captions
- macOS for the `en` narration backend; VOICEVOX for `ja`

## Licensing

matinee is MIT. **Remotion, which it uses to render, is not.** Remotion is free for individuals, non-profits, and for-profit organisations with up to three employees; larger organisations need a [company licence](https://www.remotion.dev/docs/licensing). Check where you fall before using this at work.

## Known limitations

- **VHS's own encoders can fail silently.** VHS v0.12.0 shells out to ffmpeg for GIF and MP4, and against ffmpeg 9.x that call writes nothing while still logging "Creating …" and exiting 0. matinee sidesteps it by taking VHS's PNG frame output and encoding that itself, which also means the window chrome VHS would have drawn is redrawn in `TerminalStage.tsx`.
- **The recording is not reproducible.** A tape may fetch and build before it records, so clip length depends on the machine and on cache state. Chapter marks are scaled to the measured duration rather than trusted from the estimate.
- **Chapter timings are estimated, then scaled.** The static walk over the tape models typing and sleeps but not render time, and over-shoots — on y509's tape, 34275ms estimated against 27880ms actual. The scaling corrects the total, not a demo with one unusually slow step.
- **9:16 is legible but small for a dense TUI.** The clip is fitted whole rather than zoomed. Per-chapter crop regions, so the vertical cut follows whichever pane is active, are the fix and are not built yet.
- **`say` is macOS-only.** Linux narration needs a backend that does not exist here yet.

#!/usr/bin/env python3
"""Step 3a: narration, entirely offline.

    scripts/tts.py projects/y509/script.yaml

Three backends, all local and free. `--backend auto` (the default) picks one
from the script's `lang` and the platform; pass `--backend` to override.

  voicevox -> the default for `lang: ja`. An engine over HTTP on :50021:
        docker run -d --name voicevox -p 50021:50021 \
          voicevox/voicevox_engine:cpu-latest
        Each VOICEVOX character has its own terms of use. Check the one you
        pick before putting the result anywhere public.

  say      -> the default elsewhere on macOS. Ships with the OS.

  piper    -> the default elsewhere on Linux. Needs a voice model downloaded
        once; the error message says where to get one.

No API key, no per-character billing, nothing leaves the machine. That matters
more than voice quality here: the narration gets regenerated on every wording
change, and a metered API turns that into a reason not to iterate.

Each chapter is synthesised on its own and laid down at its chapter's start
time, so the voice stays locked to what is on screen even when the wording
changes length. A chapter whose narration overruns its slot is reported rather
than silently overlapping the next one.
"""
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

VOICEVOX_URL = "http://127.0.0.1:50021"
# 3 is Zundamon (ノーマル). Any speaker id from GET /speakers works.
DEFAULT_VOICEVOX_SPEAKER = 3
DEFAULT_SAY_VOICE = "Samantha"
# piper needs an explicit voice model; this is the usual English default.
PIPER_MODEL = Path.home() / ".cache" / "piper" / "en_US-lessac-medium.onnx"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def probe_duration_ms(path: Path) -> int:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return int(float(out) * 1000)


def synth_voicevox(text: str, out_wav: Path, speaker: int) -> None:
    query_url = f"{VOICEVOX_URL}/audio_query?" + urllib.parse.urlencode(
        {"text": text, "speaker": speaker}
    )
    try:
        with urllib.request.urlopen(
            urllib.request.Request(query_url, method="POST"), timeout=60
        ) as resp:
            query = resp.read()
    except OSError as exc:
        sys.exit(
            f"error: VOICEVOX not reachable at {VOICEVOX_URL} ({exc}).\n"
            "  docker run -d --name voicevox -p 50021:50021 "
            "voicevox/voicevox_engine:cpu-latest"
        )

    synth_url = f"{VOICEVOX_URL}/synthesis?" + urllib.parse.urlencode(
        {"speaker": speaker}
    )
    req = urllib.request.Request(
        synth_url,
        data=query,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        out_wav.write_bytes(resp.read())


def synth_piper(text: str, out_wav: Path, model: Path) -> None:
    """Linux's answer to `say`: piper, a local neural TTS.

    Unlike `say` it needs a voice model downloaded up front, so the error says
    where to get one rather than just reporting the binary is missing.
    """
    if not shutil.which("piper"):
        sys.exit(
            "error: piper not found.\n"
            "  pipx install piper-tts   (or: uv tool install piper-tts)"
        )
    if not model.exists():
        sys.exit(
            f"error: piper voice not found: {model}\n"
            f"  mkdir -p {model.parent} && cd {model.parent}\n"
            "  curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main"
            f"/en/en_US/lessac/medium/{model.name}\n"
            "  curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main"
            f"/en/en_US/lessac/medium/{model.name}.json"
        )
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "out.wav"
        subprocess.run(
            ["piper", "--model", str(model), "--output_file", str(raw)],
            input=text.encode(),
            check=True,
            capture_output=True,
        )
        run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                str(raw),
                "-ar",
                "24000",
                "-ac",
                "1",
                str(out_wav),
            ]
        )


def synth_espeak(text: str, out_wav: Path) -> None:
    """The lowest common denominator: robotic, but apt-installable and instant.

    Here so CI can exercise the whole pipeline -- including that the render
    comes out with a real audio track -- without downloading a voice model.
    Not a good choice for a video anyone will watch.
    """
    binary = shutil.which("espeak-ng") or shutil.which("espeak")
    if not binary:
        sys.exit("error: espeak-ng not found.\n  apt-get install -y espeak-ng")
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "out.wav"
        run([binary, "-w", str(raw), text])
        run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                str(raw),
                "-ar",
                "24000",
                "-ac",
                "1",
                str(out_wav),
            ]
        )


def synth_say(text: str, out_wav: Path, voice: str) -> None:
    if not shutil.which("say"):
        sys.exit("error: `say` not found; it is macOS only. Use --backend piper.")
    with tempfile.TemporaryDirectory() as tmp:
        aiff = Path(tmp) / "out.aiff"
        run(["say", "-v", voice, "-o", str(aiff), text])
        run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                str(aiff),
                "-ar",
                "24000",
                "-ac",
                "1",
                str(out_wav),
            ]
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path, help="path to script.yaml")
    parser.add_argument("--speaker", type=int, default=DEFAULT_VOICEVOX_SPEAKER)
    parser.add_argument("--voice", default=DEFAULT_SAY_VOICE)
    parser.add_argument(
        "--backend",
        choices=["auto", "voicevox", "say", "piper", "espeak"],
        default="auto",
        help="auto: voicevox for ja, else say on macOS and piper elsewhere",
    )
    parser.add_argument(
        "--piper-model",
        type=Path,
        default=PIPER_MODEL,
        help="path to a piper .onnx voice",
    )
    args = parser.parse_args()

    script = yaml.safe_load(args.script.read_text(encoding="utf-8"))
    lang = script.get("lang", "ja")

    backend = args.backend
    if backend == "auto":
        if lang == "ja":
            backend = "voicevox"
        else:
            backend = "say" if sys.platform == "darwin" else "piper"

    # Chapters and their timings live in the generated project.json, not in
    # script.yaml -- they come from the tape, so build_project.py owns them.
    project_path = args.script.parent / "project.json"
    if not project_path.exists():
        sys.exit(f"error: {project_path} missing; run build_project.py first")
    project = json.loads(project_path.read_text(encoding="utf-8"))
    project_id = project["id"]
    chapters = project["chapters"]
    total_ms = project["terminalDurationMs"]

    pipeline_dir = Path(__file__).resolve().parent.parent
    out_dir = pipeline_dir / "public" / "projects" / project_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_wav = out_dir / "narration.wav"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        parts: list[tuple[Path, int]] = []

        for i, chapter in enumerate(chapters):
            text = chapter.get("narration", "").strip()
            if not text:
                continue
            part = tmp / f"{i:02d}.wav"
            print(f"  [{i + 1}/{len(chapters)}] {chapter['title']}")
            if backend == "voicevox":
                synth_voicevox(text, part, args.speaker)
            elif backend == "piper":
                synth_piper(text, part, args.piper_model)
            elif backend == "espeak":
                synth_espeak(text, part)
            else:
                synth_say(text, part, args.voice)

            start = chapter["startMs"]
            parts.append((part, start))

            # Report overruns as we go. The limit is the *next chapter's*
            # start, which has to be read from the full chapter list -- not
            # from the narrated subset, or a silent chapter in between makes
            # every later limit wrong.
            limit = chapters[i + 1]["startMs"] if i + 1 < len(chapters) else total_ms
            spoken = probe_duration_ms(part)
            if start + spoken > limit:
                print(
                    f"    warning: '{chapter['title']}' overruns into the next "
                    f"chapter by {start + spoken - limit}ms "
                    f"(spoken {spoken}ms, slot {limit - start}ms)",
                    file=sys.stderr,
                )

        if not parts:
            sys.exit("error: no chapter has narration text")

        # One silent bed the length of the terminal clip, with each chapter
        # delayed onto it. adelay+amix keeps every part at its own offset.
        inputs: list[str] = []
        filters: list[str] = []
        for i, (part, start) in enumerate(parts):
            inputs += ["-i", str(part)]
            filters.append(f"[{i}:a]adelay={start}|{start},aresample=48000[a{i}]")
        mix = "".join(f"[a{i}]" for i in range(len(parts)))
        filter_complex = (
            ";".join(filters) + f";{mix}amix=inputs={len(parts)}:normalize=0,"
            f"apad,atrim=0:{total_ms / 1000:.3f},"
            "loudnorm=I=-16:TP=-1.5:LRA=11[out]"
        )

        run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                *inputs,
                "-filter_complex",
                filter_complex,
                "-map",
                "[out]",
                "-ar",
                "48000",
                "-ac",
                "1",
                str(out_wav),
            ]
        )

    print(f"==> wrote {out_wav} ({probe_duration_ms(out_wav)}ms)")


if __name__ == "__main__":
    main()

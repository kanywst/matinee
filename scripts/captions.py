#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Step 3b: word-level captions, offline.

    scripts/captions.py projects/y509/script.yaml

Runs whisper.cpp over the narration and writes the word timings straight into
project.json, where Captions.tsx reads them.

Word granularity is the whole point. Line-level timings are enough to put text
on screen, but the karaoke highlight needs to know when each individual word is
spoken -- hence `-ml 1 -sow`, which makes whisper emit one segment per word.

This transcribes the synthesised narration rather than reusing the script text
it was generated from. It costs an extra minute, and it earns it: what comes
back is when the words were actually said, including the pauses the TTS chose,
so the highlight lands on the beat instead of on an estimate. The cost is that
a word the TTS slurred can come back misspelled -- which is worth knowing about
when a caption looks wrong but the audio sounds right.

Models are not bundled; fetch one first:
  mkdir -p ~/.cache/whisper && cd ~/.cache/whisper
  curl -LO https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
  # ja needs the multilingual build: ggml-base.bin
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

MODEL_DIR = Path.home() / ".cache" / "whisper"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path)
    parser.add_argument("--model", type=Path, default=None)
    args = parser.parse_args()

    if not shutil.which("whisper-cli"):
        sys.exit("error: whisper-cli not found (brew install whisper-cpp)")

    script = yaml.safe_load(args.script.read_text(encoding="utf-8"))
    lang = script.get("lang", "ja")

    project_path = args.script.parent / "project.json"
    if not project_path.exists():
        sys.exit(f"error: {project_path} missing; run build_project.py first")
    project = json.loads(project_path.read_text(encoding="utf-8"))

    pipeline_dir = Path(__file__).resolve().parent.parent
    wav = pipeline_dir / "public" / "projects" / project["id"] / "narration.wav"
    if not wav.exists():
        sys.exit(f"error: {wav} missing; run tts.py first")

    # The .en models are English-only and noticeably better at it; anything
    # else needs the multilingual build.
    model = args.model or MODEL_DIR / (
        "ggml-base.en.bin" if lang == "en" else "ggml-base.bin"
    )
    if not model.exists():
        sys.exit(
            f"error: whisper model not found: {model}\n"
            f"  mkdir -p {MODEL_DIR} && cd {MODEL_DIR}\n"
            f"  curl -LO https://huggingface.co/ggerganov/whisper.cpp/"
            f"resolve/main/{model.name}"
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        out_base = Path(tmpdir) / "words"
        cmd = [
            "whisper-cli", "-m", str(model), "-f", str(wav),
            "-ml", "1", "-sow", "-oj", "-of", str(out_base), "--no-prints",
        ]
        if lang != "en":
            cmd += ["-l", lang]
        print(f"==> transcribing with {model.name}")
        subprocess.run(cmd, check=True)

        transcription = json.loads(
            out_base.with_suffix(".json").read_text(encoding="utf-8")
        )["transcription"]

    captions = []
    for segment in transcription:
        text = segment["text"].strip()
        if not text:
            continue
        captions.append({
            "text": text,
            "startMs": segment["offsets"]["from"],
            "endMs": segment["offsets"]["to"],
        })

    if not captions:
        sys.exit("error: whisper returned no words")

    project["captions"] = captions
    # Stamps which recording these timings were measured against, so
    # build_project.py can warn when a re-record leaves them stale.
    project["captionsForDurationMs"] = project["terminalDurationMs"]
    project_path.write_text(
        json.dumps(project, indent=2, ensure_ascii=False) + "\n"
    )
    print(f"==> wrote {len(captions)} words into {project_path}")


if __name__ == "__main__":
    main()

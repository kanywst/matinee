#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Assemble project.json from the tape, the script and whatever assets exist.

    scripts/build_project.py projects/y509/script.yaml

project.json is the single object Remotion renders from. It is generated, not
hand written: the chapter titles and timings come from the repo's VHS tape, the
narration text from script.yaml, the clip length from the recorded mp4, and the
captions from whatever captions.py last produced.

Run this after record.sh, and again after captions.py -- it is idempotent and
preserves captions that are already on disk.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml
from tape_timeline import scale_marks, timeline


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


def probe_size(path: Path) -> tuple[int, int]:
    """The recording's pixel dimensions.

    TerminalStage needs these to fit the clip into the frame by height as well
    as width -- CSS alone cannot, because the source aspect depends on the
    tape's Set Width/Height and differs per repo.
    """
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    width, height = (int(v) for v in out.split(",")[:2])
    return width, height


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path)
    args = parser.parse_args()

    script = yaml.safe_load(args.script.read_text(encoding="utf-8"))
    project_id = script["id"]

    pipeline_dir = Path(__file__).resolve().parent.parent
    asset_dir = pipeline_dir / "public" / "projects" / project_id
    terminal = asset_dir / "terminal.mp4"
    if not terminal.exists():
        sys.exit(f"error: {terminal} missing; run scripts/record.sh first")

    duration_ms = probe_duration_ms(terminal)
    terminal_width, terminal_height = probe_size(terminal)

    tape = Path(script["source"]["repoDir"]).expanduser() / script["source"]["tapeRel"]
    if not tape.exists():
        sys.exit(f"error: tape not found: {tape}")

    marks, estimated = timeline(tape.read_text(encoding="utf-8"))
    if not marks:
        sys.exit(
            f"error: no section comments found in {tape}\n"
            "  Chapters come from the tape's comments; add a single-line\n"
            "  comment above each section, e.g. `# Search`."
        )
    # Shared with the CLI so the two cannot drift, and so the case where the
    # trailing-section filter would empty the list is handled once.
    all_titles = {m["title"] for m in marks}
    marks = scale_marks(marks, estimated, duration_ms)
    kept_titles = {m["title"] for m in marks}

    narration = script.get("narration", {}) or {}
    crops = script.get("crop", {}) or {}
    # Checked against every section the tape has, not only the ones that
    # survived the trailing-section filter -- otherwise narration written for
    # a trimmed final section is misreported as a typo.
    # A section dropped as a teardown still counts as a real section above, so
    # a key naming it is not a typo -- but it will never be spoken either, and
    # that is worth saying out loud.
    trimmed = ((set(narration) | set(crops)) & all_titles) - kept_titles
    if trimmed:
        print(
            "warning: these sections were trimmed as teardown and will not be "
            "used: " + ", ".join(sorted(trimmed)),
            file=sys.stderr,
        )

    unused = (set(narration) | set(crops)) - all_titles
    if unused:
        # Almost always a typo or a renamed tape section, and it fails quietly
        # as "that line never got read" if nobody says anything.
        print(
            "warning: script.yaml keys match no chapter: " + ", ".join(sorted(unused)),
            file=sys.stderr,
        )

    for title, crop in crops.items():
        missing = {"x", "y", "w", "h"} - set(crop or {})
        if missing:
            sys.exit(
                f"error: crop for '{title}' is missing {sorted(missing)}; "
                "all of x, y, w, h are required, as 0..1 fractions"
            )

    chapters = []
    for m in marks:
        chapter = {
            "title": m["title"],
            "startMs": m["startMs"],
            "narration": narration.get(m["title"], ""),
        }
        # Only carried when set: an absent crop means the whole frame, which is
        # also what every chapter gets in 16:9.
        if m["title"] in crops:
            chapter["crop"] = {k: float(crops[m["title"]][k]) for k in "xywh"}
        chapters.append(chapter)

    out_path = args.script.parent / "project.json"
    # Captions take ~a minute of whisper to regenerate and are overwritten by
    # captions.py, so carry over whatever is already there.
    previous = json.loads(out_path.read_text()) if out_path.exists() else {}
    carried = previous.get("captions", [])
    # Caption timings are absolute offsets into one specific narration.wav. A
    # re-record changes the clip length and moves every chapter, so carrying
    # them forward silently pairs old word timings with new visuals.
    if carried and previous.get("captionsForDurationMs") != duration_ms:
        print(
            f"warning: carried-over captions were measured against a "
            f"{previous.get('captionsForDurationMs')}ms clip, now {duration_ms}ms. "
            "Re-run scripts/captions.py.",
            file=sys.stderr,
        )

    project = {
        "id": project_id,
        "title": script["title"],
        "subtitle": script["subtitle"],
        "repo": script["repo"],
        "accent": script["accent"],
        "terminalDurationMs": duration_ms,
        "terminalWidth": terminal_width,
        "terminalHeight": terminal_height,
        "chapters": chapters,
        "terminalSrc": f"projects/{project_id}/terminal.mp4",
        "captions": carried,
        "captionsForDurationMs": previous.get("captionsForDurationMs"),
    }
    if (asset_dir / "narration.wav").exists():
        project["audioSrc"] = f"projects/{project_id}/narration.wav"
    if (asset_dir / "broll.mp4").exists():
        project["brollSrc"] = f"projects/{project_id}/broll.mp4"

    out_path.write_text(json.dumps(project, indent=2, ensure_ascii=False) + "\n")
    print(f"==> wrote {out_path}")
    print(
        f"    {len(chapters)} chapters, {duration_ms}ms, "
        f"{len(project['captions'])} captions"
    )


if __name__ == "__main__":
    main()

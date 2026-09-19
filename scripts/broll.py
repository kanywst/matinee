#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Step 4: the only part that calls a paid API.

    export FAL_KEY=...
    scripts/broll.py projects/y509/script.yaml

Generates the abstract clip that sits behind the title card, and nothing else.
Everything up to here is deterministic and free; this step is neither, so it is
kept to the smallest surface that still earns its place -- three seconds under
a title, at 28% opacity.

Add to script.yaml to enable:

    broll:
      prompt: >-
        Slow macro dolly across a dark lattice of glowing green certificate
        chains, shallow depth of field, deep navy background, subtle drift.
      model: fal-ai/wan-25-preview/text-to-video
      durationSeconds: 5

Cost control, in order of how much they save:

  1. The cache. The key is a hash of (model, prompt, every parameter), so
     re-running this script after editing anything else is free. Generation is
     charged per second of output and a title card takes one clip -- the bill
     comes from iterating on the prompt, not from the render.
  2. Short clips. Five seconds is plenty for a three-second title.
  3. Reviewing before generating. --dry-run prints the request and the cache
     key and exits, which is also how you check what a prompt edit will cost
     before it costs it.

Pricing moves monthly; check fal.ai/pricing rather than trusting a number
written down here. See docs/01-landscape.md for the model landscape and
docs/05-policy-money.md before putting any of this somewhere public.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

import yaml

FAL_QUEUE = "https://queue.fal.run"
DEFAULT_MODEL = "fal-ai/wan-25-preview/text-to-video"


def cache_key(payload: dict, model: str) -> str:
    blob = json.dumps({"model": model, **payload}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def submit(model: str, payload: dict, key: str) -> str:
    """Submit to fal's queue and poll until the video URL comes back."""
    import time

    req = urllib.request.Request(
        f"{FAL_QUEUE}/{model}",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Key {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        queued = json.loads(resp.read())

    status_url = queued["status_url"]
    response_url = queued["response_url"]

    # Cap the wait. A request stuck IN_QUEUE would otherwise hang the pipeline
    # forever, and this is the one step that is already costing money.
    deadline = time.monotonic() + 900
    while True:
        if time.monotonic() > deadline:
            sys.exit(
                "error: generation still not finished after 15 minutes.\n"
                f"  Check it at {status_url}"
            )
        time.sleep(5)
        status_req = urllib.request.Request(
            status_url, headers={"Authorization": f"Key {key}"}
        )
        with urllib.request.urlopen(status_req, timeout=60) as resp:
            status = json.loads(resp.read())
        state = status.get("status")
        print(f"    {state}")
        if state == "COMPLETED":
            break
        if state in {"FAILED", "CANCELLED"}:
            sys.exit(f"error: generation {state}: {status}")

    result_req = urllib.request.Request(
        response_url, headers={"Authorization": f"Key {key}"}
    )
    with urllib.request.urlopen(result_req, timeout=60) as resp:
        result = json.loads(resp.read())
    return result["video"]["url"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    script = yaml.safe_load(args.script.read_text(encoding="utf-8"))
    broll = script.get("broll")
    if not broll:
        sys.exit("error: script.yaml has no `broll:` block; nothing to generate")

    model = broll.get("model", DEFAULT_MODEL)
    payload = {
        "prompt": broll["prompt"],
        "duration": broll.get("durationSeconds", 5),
        "resolution": broll.get("resolution", "720p"),
        "aspect_ratio": broll.get("aspectRatio", "16:9"),
    }

    pipeline_dir = Path(__file__).resolve().parent.parent
    out_dir = pipeline_dir / "public" / "projects" / script["id"]
    out_mp4 = out_dir / "broll.mp4"
    cache_dir = pipeline_dir / ".cache" / "broll"
    cached = cache_dir / f"{cache_key(payload, model)}.mp4"

    print(f"==> model    {model}")
    print(f"==> cache    {cached.name}")
    print(f"==> payload  {json.dumps(payload, ensure_ascii=False)}")

    # Before any mkdir: --dry-run is for inspecting what a prompt edit will
    # cost, and it should leave nothing behind.
    if args.dry_run:
        print("==> dry run; nothing generated")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    if cached.exists():
        print("==> cache hit; no API call")
    else:
        api_key = os.environ.get("FAL_KEY")
        if not api_key:
            sys.exit(
                "error: FAL_KEY is not set.\n"
                "  Get one at fal.ai, then: export FAL_KEY=...\n"
                "  Or run with --dry-run to see the request without making it."
            )
        print("==> generating (this is the part that costs money)")
        url = submit(model, payload, api_key)
        with urllib.request.urlopen(url, timeout=300) as resp:
            cached.write_bytes(resp.read())
        print(f"==> cached {cached}")

    out_mp4.write_bytes(cached.read_bytes())
    print(f"==> wrote {out_mp4}")
    print("    re-run build_project.py to pick it up")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Step 2: derive chapter start times from the tape itself.

    scripts/tape_timeline.py ~/y509/demo.tape --duration-ms 27880

The tapes already mark their sections with comments:

    # 3. Search
    Type "/"
    Sleep 500ms

So the tape is the single source of truth for both the recording and the
chapter list -- edit the demo and the chapters move with it, instead of
drifting out of sync with a hand-maintained list of timings.

Section comments vs. prose
--------------------------
Real tapes carry two kinds of comment: short section markers, and multi-line
paragraphs explaining why a step is written the way it is. They are told apart
by *shape*, not by punctuation: a comment block of a single line is a section
marker, a block of several lines is prose. An earlier version required the
title to avoid `.` and stay under 39 characters, which rejected every section
comment in prpr's tape (all end in a period) and half of brtc's (one runs 76
characters).

Timing model
------------
The tape is tokenised, not read line by line, because VHS accepts several
statements on one line (`Down Sleep 700ms`, used seven times in prpr's tape).

  * Type "abc"    -> len * TypingSpeed
  * a bare key    -> TypingSpeed (Enter, Tab, Escape, arrows, Ctrl+x, Shift+x)
  * Key 3         -> that key, three times
  * Cmd@200ms     -> an explicit per-command duration overrides the default
  * Sleep 1.5s    -> that long
  * Hide .. Show  -> skipped entirely; VHS records no frames there, so the
                     setup commands cost wall time but no timeline

That is an estimate, not a measurement. Pass --duration-ms with the true clip
length and every mark is scaled to fit it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DURATION_RE = re.compile(r"^([0-9.]+)(ms|s|m)?$")
# "# 3. Search" -- an explicitly numbered section, always a section marker
# however long it runs.
NUMBERED_RE = re.compile(r"^#\s*\d+[.)]\s*(\S.*)$")
COMMENT_RE = re.compile(r"^\s*#\s?(.*)$")
# Quoted strings survive tokenisation intact, escapes included, so
# `Type "say \\"hi\\""` counts as one token; everything else splits on space.
TOKEN_RE = re.compile(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|`[^`]*`|\S+')
# Longest chapter title the chip can show without wrapping.
MAX_TITLE = 48

KEYS = {
    "Enter",
    "Tab",
    "Escape",
    "Space",
    "Backspace",
    "Delete",
    "Up",
    "Down",
    "Left",
    "Right",
    "PageUp",
    "PageDown",
    "Home",
    "End",
    # VHS's remaining keys. Left out, each cost 0ms and the repeat count after
    # them was swallowed as an unknown token -- `ScrollDown 10` in a scrolling
    # demo lost half a second and deferred its chapter mark.
    "Insert",
    "ScrollUp",
    "ScrollDown",
}
MODIFIERS = ("Ctrl+", "Alt+", "Shift+", "Cmd+")
# Statements that take one argument and cost no time.
SKIP_WITH_ARG = {"Output", "Require", "Env", "Source"}


def clean_title(title: str) -> str:
    """Trim a section comment down to something that fits on screen.

    Tapes annotate sections for the next reader of the tape -- "7. Export via
    huh form (Filename + Format select), submit and dismiss" -- but a chapter
    chip has room for a label, not a sentence. Cut at the first parenthetical
    or comma, which is reliably where the aside starts.
    """
    for sep in (" (", ", "):
        head = title.split(sep, 1)[0]
        if head:
            title = head
    title = title.strip().rstrip(".")
    if len(title) > MAX_TITLE:
        # Cut at a word boundary. Slicing mid-word left titles like
        # "Step 2: Show a strong password with a different ".
        cut = title[:MAX_TITLE].rsplit(" ", 1)[0]
        title = (cut or title[:MAX_TITLE]).rstrip(" ,-:;")
    return title


def parse_duration(token: str) -> float:
    m = DURATION_RE.match(token)
    if not m:
        return 0.0
    value = float(m.group(1))
    unit = m.group(2) or "s"
    return value * {"ms": 1.0, "s": 1000.0, "m": 60000.0}[unit]


def split_qualifier(token: str) -> tuple[str, float | None]:
    """`Sleep@100ms` -> ("Sleep", 100.0). VHS allows @ on any command."""
    if "@" in token:
        head, _, qualifier = token.partition("@")
        return head, parse_duration(qualifier)
    return token, None


def is_section_comment(lines: list[str], i: int) -> tuple[str, bool] | None:
    """Return the section title at line i, or None.

    Shape decides, because real tapes carry two kinds of comment and only the
    punctuation distinguishes them unreliably:

    * A numbered comment is a section when it *begins* its comment block. It
      may run onto further lines -- section titles do. One buried inside a
      paragraph is an enumeration ("# 1. builds / # 2. runs it"), not a
      section.
    * An unnumbered comment is a section only when its block is one line long.
    """
    line = lines[i].strip()
    prev_is_comment = i > 0 and COMMENT_RE.match(lines[i - 1].strip()) is not None

    m = NUMBERED_RE.match(line)
    if m:
        return None if prev_is_comment else (clean_title(m.group(1)), True)

    m = COMMENT_RE.match(line)
    if not m or not m.group(1).strip():
        return None
    next_is_comment = (
        i + 1 < len(lines) and COMMENT_RE.match(lines[i + 1].strip()) is not None
    )
    if prev_is_comment or next_is_comment:
        return None
    return (clean_title(m.group(1)), False)


def timeline(tape: str) -> tuple[list[dict], float]:
    typing_speed = 50.0  # VHS default
    now = 0.0
    hidden = False
    marks: list[dict] = []
    pending: tuple[str, bool] | None = None

    lines = tape.splitlines()
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue

        if line.startswith("#"):
            # Only remember the section name; it is attributed to the next
            # visible command, so a comment inside a Hide block does not
            # become a chapter at the wrong time.
            section = is_section_comment(lines, i)
            if section:
                pending = section
            continue

        tokens = TOKEN_RE.findall(line)
        # A trailing comment is not a statement. VHS accepts `Set Width 1200 #
        # the width`, and walking its words as commands let a comment that
        # merely mentions a duration -- `Type "ab"  # Sleep 10s here` -- add
        # ten seconds to the estimate. That is not a local error: scale_marks
        # divides the measured length by the estimate, so one such comment
        # moves every chapter mark in the video.
        for index, token in enumerate(tokens):
            if token.startswith("#"):
                tokens = tokens[:index]
                break
        if not tokens:
            continue

        heads = [split_qualifier(token)[0] for token in tokens]
        # Only a statement that occupies the timeline starts a chapter. A
        # comment above `Set`/`Output` is the tape's own header, and one above
        # `Hide` labels the setup -- neither is a chapter, and pinning them
        # here put a 1-frame chapter at 0ms and renumbered every chip.
        enters_hidden = "Hide" in heads
        has_action = any(
            head in {"Type", "Sleep"} or head in KEYS or head.startswith(MODIFIERS)
            for head in heads
        )

        # Place the pending section *before* the statement it labels runs, not
        # after: the chapter starts when its first command starts. Recording it
        # at the end of the line put every chapter one statement late.
        if pending is not None:
            title, numbered = pending
            if hidden or enters_hidden:
                # A comment on a Hide block is ambiguous: it may document the
                # setup, or it may name a section whose first step happens to
                # be hidden. Nothing in its shape separates them -- but a
                # number is the author saying "this is a section", so a
                # numbered one is held until the first visible action and an
                # unnumbered one is treated as a note and dropped.
                if not numbered:
                    pending = None
            elif has_action:
                marks.append({"title": title, "startMs": round(now)})
                pending = None
            # Otherwise keep it: a configuration line between the comment and
            # the action it labels should not consume the mark.

        t = 0
        while t < len(tokens):
            head, qualifier = split_qualifier(tokens[t])
            t += 1

            if head == "Hide":
                hidden = True
                continue
            if head == "Show":
                hidden = False
                continue

            if head == "Set":
                name = tokens[t] if t < len(tokens) else ""
                value = tokens[t + 1] if t + 1 < len(tokens) else ""
                if name == "TypingSpeed":
                    typing_speed = parse_duration(value)
                t += 2
                continue

            if head in SKIP_WITH_ARG:
                t += 1
                continue

            if head.startswith("Wait"):
                # Wait+Screen@300s /regex/ -- real time, but only ever used
                # inside a Hide block, and its length is unknowable statically.
                if t < len(tokens) and tokens[t].startswith("/"):
                    t += 1
                continue

            if head == "Type":
                # VHS lets one Type take several strings: `Type "ab" "cd"`.
                typed = 0
                while t < len(tokens) and tokens[t][:1] in "\"'`":
                    text = tokens[t]
                    t += 1
                    if len(text) >= 2 and text[0] == text[-1]:
                        text = text[1:-1]
                    typed += len(text.replace("\\", ""))
                if typed == 0 and t < len(tokens):
                    # An unquoted argument; VHS allows it for a single word.
                    typed = len(tokens[t])
                    t += 1
                if not hidden:
                    now += typed * (
                        qualifier if qualifier is not None else typing_speed
                    )
                continue

            if head == "Sleep":
                arg = tokens[t] if t < len(tokens) else ""
                t += 1
                if not hidden:
                    now += parse_duration(arg)
                continue

            if head in KEYS or head.startswith(MODIFIERS):
                # A bare number after a key repeats it; anything else starts a
                # new statement on the same line.
                count = 1
                if t < len(tokens) and tokens[t].isdigit():
                    count = int(tokens[t])
                    t += 1
                if not hidden:
                    now += (
                        qualifier if qualifier is not None else typing_speed
                    ) * count
                continue

            # Unknown command: consume nothing further and cost nothing.

    # A section comment with no statement after it labels nothing, so it is
    # deliberately dropped rather than pinned to the end of the tape.
    return marks, now


def scale_marks(
    marks: list[dict], estimated: float, duration_ms: int | None
) -> list[dict]:
    """Fit the marks to the true clip length and drop the teardown section."""
    if duration_ms and estimated > 0:
        scale = duration_ms / estimated
        for mark in marks:
            mark["startMs"] = round(mark["startMs"] * scale)

    if duration_ms:
        # A section starting in the last second is the tape's teardown
        # ("# Quit") -- a real section, but too short to read as a chapter.
        trimmed = [m for m in marks if m["startMs"] < duration_ms - 1000]
        # Unless that leaves nothing: a one-section tape is better as one
        # chapter than as a crash.
        if trimmed:
            marks = trimmed

    if marks:
        # The first chapter always starts at 0; a late first mark just means
        # the opening seconds have no label, which reads as a mistake.
        marks[0]["startMs"] = 0
    return marks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tape", type=Path)
    parser.add_argument(
        "--duration-ms",
        type=int,
        default=None,
        help="true clip length from record.sh; scales the marks to fit",
    )
    args = parser.parse_args()

    marks, estimated = timeline(args.tape.read_text(encoding="utf-8"))
    if not marks:
        sys.exit("error: no section comments found in tape")

    if args.duration_ms:
        print(
            f"# estimated {estimated:.0f}ms, actual {args.duration_ms}ms "
            f"(scale {args.duration_ms / estimated:.3f})",
            file=sys.stderr,
        )
    marks = scale_marks(marks, estimated, args.duration_ms)
    print(json.dumps(marks, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

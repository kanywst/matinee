# Contributing

Thanks for looking. matinee is small and solo-maintained, so the useful thing to know is what kind of change lands easily and what needs discussion first.

## The most useful contribution

**A tape that matinee gets wrong.** The tape walker is the part that decides whether this works on a repo nobody wrote it against, and every bug it has had came from a real tape doing something reasonable that the parser did not expect — several statements on one line, section comments ending in a period, `@`-qualified commands.

If your tape produces the wrong chapters, open an issue with the tape (or a reduced version of it) and what you expected. A fixture in `tests/fixtures/` plus a case in `tests/test_tape_timeline.py` is the ideal form.

## Setup

```bash
brew install vhs ffmpeg whisper.cpp   # or your platform's equivalent
npm install
```

Python runs through [uv](https://docs.astral.sh/uv/); each script carries its own PEP 723 dependency block, so there is no environment to create.

## Checks

Everything CI runs, locally:

```bash
npx tsc --noEmit                              # types
npx vitest run                                # TypeScript tests
uvx ruff check . && uvx ruff format --check . # Python lint + format
uv run --with pytest --with pyyaml pytest     # Python tests
shellcheck scripts/*.sh                       # shell
npx --yes markdownlint-cli2 "**/*.md" "#node_modules"
```

CI also runs an end-to-end job on Linux and macOS: it records `projects/hello`, narrates it with `espeak`, renders it, and asserts with `ffprobe` that the result has both a video and an audio stream. That one is worth more than the unit tests — it is the only check that proves the whole pipeline still works. To run it locally:

```bash
make video PROJECT=hello
```

The unit tests cover the parts that have actually broken: the tape walker, the crop maths, and caption grouping.

## Conventions

- **Comments explain why, not what.** Several comments in this repo name the specific defect they prevent; that is deliberate, and worth keeping when you touch that code.
- Commit messages are conventional-commit style (`fix(parser): …`), in English.
- One commit per logical change.
- New behaviour in the tape walker, the crop maths or the caption grouping needs a test. Those three are where the bugs live.

## Things worth knowing before you dig in

- `record.sh` deliberately takes VHS's PNG frame output instead of its own encoders, which fail silently against ffmpeg 9.x.
- `project.json` is generated, not hand-edited. `build_project.py` owns it.
- Chapter timings are an estimate scaled to the measured clip length. If you make the estimate better, the scaling should still stay — the recording is not reproducible.

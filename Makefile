# Demo video pipeline.
#
#   make video PROJECT=hello       # everything, in order
#   make studio                    # interactive preview
#
# Each step writes a file the next one reads, so they can be run individually
# while iterating -- change the narration and `make narrate captions render`
# skips the slow re-record.

# hello is the example that works from a bare clone; y509 and the rest need
# their own repo cloned to the path their script.yaml names.
PROJECT ?= hello
SCRIPT   = projects/$(PROJECT)/script.yaml
UV       = uv run
# `uv run python` does not inherit the scripts' PEP 723 dependencies, so pyyaml
# has to be asked for explicitly here.
# 2>/dev/null so a missing project reports itself once, from the guard in the
# record target, instead of as two Python tracebacks before the real message.
YQ       = uv run --quiet --with pyyaml python -c
REPO_DIR = $(shell $(YQ) "import yaml,os;print(os.path.expanduser(yaml.safe_load(open('$(SCRIPT)'))['source']['repoDir']))" 2>/dev/null)
TAPE_REL = $(shell $(YQ) "import yaml;print(yaml.safe_load(open('$(SCRIPT)'))['source']['tapeRel'])" 2>/dev/null)

.PHONY: video record build narrate captions render studio broll clean help

help:
	@echo "make video PROJECT=$(PROJECT)   record -> build -> narrate -> captions -> render"
	@echo "make record    run the repo's VHS tape into public/projects/$(PROJECT)/terminal.mp4"
	@echo "make build     regenerate project.json from the tape + script.yaml"
	@echo "make narrate   synthesise narration.wav (VOICEVOX for ja, macOS say for en)"
	@echo "make captions  whisper word timings into project.json"
	@echo "make render    render both 16:9 and 9:16 into out/"
	@echo "make broll     generate the title-card b-roll (needs FAL_KEY; costs money)"
	@echo "make studio    open the Remotion studio"

video: record build narrate captions render

record:
	@test -f $(SCRIPT) || { \
	  echo "error: no such project: $(SCRIPT)"; \
	  echo "available: $$(ls projects/*/script.yaml | cut -d/ -f2 | tr '\n' ' ')"; \
	  exit 1; }
	./scripts/record.sh $(PROJECT) $(REPO_DIR) $(TAPE_REL)

# build runs twice in the full pipeline: once to give tts.py its chapters, and
# again at the end so project.json picks up narration.wav.
build:
	$(UV) scripts/build_project.py $(SCRIPT)

narrate: build
	$(UV) scripts/tts.py $(SCRIPT)
	$(UV) scripts/build_project.py $(SCRIPT)

captions:
	$(UV) scripts/captions.py $(SCRIPT)

broll:
	$(UV) scripts/broll.py $(SCRIPT)
	$(UV) scripts/build_project.py $(SCRIPT)

render:
	npx remotion render src/index.ts $(PROJECT)-16x9 out/$(PROJECT)-16x9.mp4
	npx remotion render src/index.ts $(PROJECT)-9x16 out/$(PROJECT)-9x16.mp4

studio:
	npx remotion studio src/index.ts

clean:
	rm -rf out .cache
	rm -f public/projects/$(PROJECT)/terminal.mp4 \
	      public/projects/$(PROJECT)/narration.wav

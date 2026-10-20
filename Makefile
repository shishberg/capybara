KICAD_PY = "$${KICAD_PYTHON:-/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3}"

# Paused seeded-board pipeline (see the README).
build:
	./run

test:
	$(KICAD_PY) tools/test.py

benchmark:
	./run --reuse-geometry --router freerouting --board finger_l

.PHONY: build test benchmark

# Live browser chassis editor; KiCad stays in the offline pipeline.
editor:
	npm --prefix editor run dev -- --port 5177 --strictPort

editor-test:
	npm --prefix editor test

.PHONY: editor editor-test

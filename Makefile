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

# The soldering jig's STLs; see docs/solder-jig.md.
jig:
	npm --prefix editor run jig

.PHONY: editor editor-test jig

# Firmware (RMK); see firmware/README.md.
FIRMWARE_ELF = firmware/target/thumbv6m-none-eabi/release

firmware:
	cd firmware && cargo build --release
	mkdir -p output/firmware
	python3 firmware/uf2.py $(FIRMWARE_ELF)/central output/firmware/capybara-central.uf2
	python3 firmware/uf2.py $(FIRMWARE_ELF)/peripheral output/firmware/capybara-peripheral.uf2

.PHONY: firmware

# The Capybara cases (meshes cut with Manifold); see case/README.md. Their
# targets set up .venv from case/requirements.txt when that's needed.
CASE_PY = .venv/bin/python
CASE_ENV = .venv/.case

$(CASE_ENV): case/requirements.txt
	uv venv --allow-existing --python 3.12 .venv
	uv pip install --python $(CASE_PY) -r case/requirements.txt
	touch $@

case: $(CASE_ENV)
	$(CASE_PY) -m case.build

# Only the checks; fails when one does.
case-check: $(CASE_ENV)
	$(CASE_PY) -m case.build --check

# PNGs of the right half for a person to look over.
case-render: $(CASE_ENV)
	$(CASE_PY) -m case.render

case-test: $(CASE_ENV)
	$(CASE_PY) -m unittest case.test_checks case.test_swung_in case.test_ribs

# One half's assembly for the editor's Case picker (editor/README.md), by
# preset: slim, capybara or slim_ribs.
CASE_SRC = $(CASE_ENV) $(wildcard case/*.py) hand/left-hand.json editor/src/default-config.json
SWUNG_IN_SRC = $(wildcard editor/src/*.ts) editor/tests/key-frames.ts

output/case/capybara/%-assembly.3mf: $(CASE_SRC) $(SWUNG_IN_SRC)
	$(CASE_PY) -m case.build --preset capybara --half $* --part assembly --no-check

output/case/slim/%-assembly.3mf: $(CASE_SRC)
	$(CASE_PY) -m case.build --preset slim --half $* --part assembly --no-check

output/case/slim_ribs/%-assembly.3mf: $(CASE_SRC)
	$(CASE_PY) -m case.build --preset slim_ribs --half $* --part assembly --no-check

.PHONY: case case-check case-render case-test

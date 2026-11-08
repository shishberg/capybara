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

# Low-profile Capybara proposal (meshes cut with Manifold); see lowpro/README.md.
# Its targets set up .venv from lowpro/requirements.txt when that's needed.
LOWPRO_PY = .venv/bin/python
LOWPRO_ENV = .venv/.lowpro

$(LOWPRO_ENV): lowpro/requirements.txt
	uv venv --allow-existing --python 3.12 .venv
	uv pip install --python $(LOWPRO_PY) -r lowpro/requirements.txt
	touch $@

lowpro: $(LOWPRO_ENV)
	$(LOWPRO_PY) -m lowpro.build

# Only the checks; fails when one does.
lowpro-check: $(LOWPRO_ENV)
	$(LOWPRO_PY) -m lowpro.build --check

# PNGs of the right half for a person to look over.
lowpro-render: $(LOWPRO_ENV)
	$(LOWPRO_PY) -m lowpro.render

lowpro-test: $(LOWPRO_ENV)
	$(LOWPRO_PY) -m unittest lowpro.test_checks lowpro.test_swung_in

# One half's assembly for the editor's Case picker (editor/README.md). The
# capybara rule comes first: make takes the first pattern rule that matches.
LOWPRO_SRC = $(LOWPRO_ENV) $(wildcard lowpro/*.py) hand/left-hand.json editor/src/default-config.json

output/lowpro/capybara/%-assembly.3mf: $(LOWPRO_SRC) $(wildcard editor/src/*.ts) editor/tests/key-frames.ts
	$(LOWPRO_PY) -m lowpro.build --preset capybara --half $* --part assembly --no-check

output/lowpro/%-assembly.3mf: $(LOWPRO_SRC)
	$(LOWPRO_PY) -m lowpro.build --half $* --part assembly --no-check

.PHONY: lowpro lowpro-check lowpro-render lowpro-test

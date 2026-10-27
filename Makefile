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

# Firmware (RMK); see firmware/README.md.
FIRMWARE_ELF = firmware/target/thumbv6m-none-eabi/release

firmware:
	cd firmware && cargo build --release
	mkdir -p output/firmware
	python3 firmware/uf2.py $(FIRMWARE_ELF)/central output/firmware/capybara-central.uf2
	python3 firmware/uf2.py $(FIRMWARE_ELF)/peripheral output/firmware/capybara-peripheral.uf2

.PHONY: firmware

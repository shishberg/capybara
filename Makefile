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

# Low-profile Capybara proposal (OpenSCAD); see lowpro/README.md.
LOWPRO = lowpro/capybara-lowpro.scad
LOWPRO_OUT = output/lowpro

lowpro: lowpro-check
	mkdir -p $(LOWPRO_OUT)
	for half in right left; do \
	  openscad -D "half=\"$$half\"" -D 'show="body"' -o $(LOWPRO_OUT)/$$half-body.stl $(LOWPRO); \
	  openscad -D "half=\"$$half\"" -D 'show="plate"' -o $(LOWPRO_OUT)/$$half-plate.stl $(LOWPRO); \
	done
	openscad -D 'show="assembly"' --imgsize=1600,1200 --viewall --autocenter --camera=0,0,0,55,0,25,0 -o $(LOWPRO_OUT)/right-assembly.png $(LOWPRO)
	openscad -D 'show="assembly"' --imgsize=1600,1200 --viewall --autocenter --camera=0,0,0,0,0,0,0 -o $(LOWPRO_OUT)/right-top.png $(LOWPRO)
	openscad -D 'show="body"' --imgsize=1600,1200 --viewall --autocenter --camera=0,0,0,180,0,0,0 -o $(LOWPRO_OUT)/right-underside.png $(LOWPRO)

# Fails when any two keycaps meet (the check renders their overlap; empty is clear).
lowpro-check:
	mkdir -p $(LOWPRO_OUT)
	openscad -D 'show="check"' -o $(LOWPRO_OUT)/check.stl $(LOWPRO) 2>&1 | tee $(LOWPRO_OUT)/check.log
	@grep -q "top level object is empty" $(LOWPRO_OUT)/check.log && echo "keycaps clear" || (echo "keycaps meet: see $(LOWPRO_OUT)/check.stl"; exit 1)

lowpro-hand:
	python3 lowpro/hand_from_json.py

.PHONY: lowpro lowpro-check lowpro-hand

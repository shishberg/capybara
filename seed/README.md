# Seed generator

The BAML project that the paused seeded-board pipeline (`make build`) runs to lay out the flex finger boards and the pod. It is the part of Rosebear's v3 board generator that `seed_export` (in `baml_src/seed.baml`) reaches. The rest of v3, including its tests and design notes, is in the [Rosebear repo](https://github.com/shishberg/rosebear). Comments here still cite those notes, such as `v2-p4-pod.md`.

From the 36-key layout, the files in `baml_src/` do these jobs:

- **Layout:** `geometry`, `layout`, `config_rosebear` and `config_dactyl` place the keys, and `features` picks the board variant.
- **Boards:** `well`, `flex` and `flex_board` cut flat boards that bend onto the key well.
- **Wiring:** `netlist`, `matrix`, `ribbon` and `pod` build the diode matrix, the FFC ribbons and the ESP32-P4 pod board.
- **Copper:** `route` and `route_matrix` route the copper.
- **Output:** `emit` and `build` write the `.kicad_pcb` files and their KiCad projects.

## How the pipeline uses it

`rosebear/seed.py` copies this project and `footprints/rosebear.pretty` into `output/geometry/`. It patches five things in the copy, never here:

- the key well, from `mechanical/chassis.json`;
- the flex tail, 5 mm;
- the diode reach, 8.2 mm;
- the pod pin map, from `pod.json`;
- one routing turn.

It then runs `seed_export`. That writes:

- `output/geometry.json`: the finger keys, strips, cuts, neck and thumb-fan copper, wire feet, the well and the pod pinout;
- seed boards, in `output/geometry/seed/`.

`tools/build.py` builds the boards in `output/seeded/` from these.

The key-tile build (`tools/build_key_quotes.py`) makes its pod from `output/seeded/pod.kicad_pcb`. It copies the module header, ribbon connectors, buttons and mounting holes from it. So the current pod board still depends on this project, though the editor and the chassis build don't. This directory can go once that pod is built on its own and the paused pipeline is dropped.

The patched functions (`HEADER_LEFT`, `HEADER_RIGHT`, `pin_cost`, `concession`, `FLEX_TAIL`, `DIODE_REACH`, `swd_turn`) must keep their signatures, because `seed.py` finds them by pattern.

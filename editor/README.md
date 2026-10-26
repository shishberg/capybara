# Rosebear chassis editor

The right-hand chassis editing loop runs entirely in the browser, in TypeScript with
Three.js and Manifold WebAssembly. KiCad/PCB generation stays in the offline v4
pipeline.

The keyboard's key layout is **Swung in**: the layout the printed frame uses, and
the default project's (`src/default-config.json`). It is the only layout here. The
earlier ones (the layout before it, which some tests built, and the `?hand`
prototype's other presets) were removed on 19 Oct 2026 and stay in git history:
509dbd1 is the last commit that has them.

The editor edits the key layout; the chassis, the Capybara frame, is
generated from it. Earlier chassis variants are on the `legacy-variants` branch
(see [design status](../docs/design-status.md)).

How the case is built and wired is in [editor chassis and wiring](../docs/editor-chassis.md).
The tile is measured. The wiring and the [Pro Micro](../docs/pro-micro.md), its
jack and its reset switch are **provisional**; each is marked `provisional` in
the configuration.

## Run

From the repository root:

```sh
npm --prefix editor ci  # first install only
make editor
```

Open **http://127.0.0.1:5177**. Keep that origin/port to retain the same browser
storage. Stop the server with Ctrl-C. `npm --prefix editor run build` creates a
static `dist/` site; serve it over HTTP, not `file://`, so workers/WASM can load.
All runtime assets are local; there are no CDN or account dependencies.

## Key layout

All values are in **layout coordinates**: millimetres and degrees before the
whole hand is tented (`geometry.tent_deg`, a rotation about Y) and lifted
(`geometry.mount_lift_mm`). +X is toward the pinky, +Y away from you, +Z up.

**Finger columns** (`geometry.columns`, inner to pinky). Each column has:

| Parameter      | Meaning                                                                                                                                 |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `heights_mm`   | Heights of the top, home and bottom keys. Each key tilts along the column to follow the parabola through the three heights.             |
| `offset_mm`    | `[X offset, stagger, 0]`. Keys sit `column_pitch_mm` apart in X and `row_pitch_mm` apart in Y; the stagger moves the whole column in Y. |
| `roll_deg`     | Sideways tilt: the slope across the column. Positive rises toward the pinky.                                                            |
| `rotation_deg` | Turns each key about its own centre; `[0,0,a]` splays the column by `a`.                                                                |

**Thumb clusters** (`geometry.thumb`, and the optional `geometry.thumb_extra`, the
pair tucked in front of it). The keys fan along an arc:

| Parameter                       | Meaning                                                                                                                                       |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `position_mm`                   | The cluster's centre: the middle of the arc.                                                                                                  |
| `rotation_deg`                  | `[tilt about X, tilt about Y, angle]`. The angle turns the cluster in plan.                                                                   |
| `arc.radius_mm`, `arc.step_deg` | The arc's radius and the angle between neighbouring keys. Key spacing is about `2 × radius × sin(step / 2)`.                                  |
| `arc.well_deg`                  | Each key tilts toward the middle of the cluster by this much per key step, rising so it stays on a circle (a well, as in the finger columns). |
| `keys`                          | Key names in order along the arc, each with an optional `offset_mm` and `rotation_deg` (the middle thumb key is turned 90° for its 1.5u cap). |

`chassis` holds `plate_thickness_mm` (3), `plate_margin_mm` (0.9: a plate reaches this far
past its switch seat, or to the edge of the tile pocket if that is further) and `skin_mm`, the base plate's thickness
(the Pro Micro, its jack, its reset switch and the loom stand on it). `skin_mm` must exceed 1.5 mm.

## Use

- Drag a handle **parallel to the current view**. The layout axis nearest the view
  direction is left unchanged, so the Top view moves things in plan and the Front
  and Inner views change heights.
  - **Gold**, one per finger key: up and down sets that key's height; along the
    column sets the column's stagger. Move a column sideways with its X offset field.
  - **Cyan**: a thumb cluster's centre. **Pink**: turns a thumb cluster about its centre.
- Clicking a handle shows every parameter of its column or cluster as number
  fields. **All configuration** shows and edits the full JSON.
- Drag empty space to orbit, right-drag to pan, wheel to zoom.
- The view, the View checkboxes and the chassis opacity are remembered in this
  browser across reloads (a `?mark=` link still sets its own view).
- Parts and keycaps follow while dragging. The previous chassis stays visible
  until the rebuild after release finishes. Stale results are labelled;
  STL/report export is disabled until the chassis is current.
- Undo/Redo (Cmd/Ctrl-Z and Shift-Z also work) and Reset model. Reset can be undone.
- Changes autosave to LocalStorage. **Save project** downloads a JSON file;
  **Open project** validates and restores one. Projects from the earlier
  cage-based editor (version 1) are not accepted.
- **Export review STL** exports the case without the bottom section. It is a
  review export, not a claim that the model is mechanically qualified.
  **Export bottom section STL** exports the bottom section, a separate print.
- **Wiring and pads** shows the wires as tubes coloured by net group, and the
  pads. The wires are routed with each chassis build, so while you edit they
  stay as last built. **Controller, jack and plugs** shows the Pro Micro, its
  TRRS jack, its reset switch and both plugs; turn it off to see the wiring
  behind them. The **Wiring** panel
  lists each key's row and column, and a cut list per net.
- **Show bounding box** outlines the box around the case, bottom section and
  trim; the View panel gives its width (X), depth (Y) and height (Z) in mm,
  updated with each chassis build.
- Projects saved before the wiring was added load with the default pads and
  wiring. Projects saved with the FFC adapter load on the Pro Micro, without
  the adapter and its ribbon.

## Clearance checks

`seats.ts` builds the flat switch seats, clip reliefs and switch openings.
`solid.ts` cuts them and checks the result, one function per check below;
`regions.ts` cuts the chassis down to the area round each key, so each test
runs against a fraction of the mesh:

- Each switch has a crisp, planar 15.8 × 15.8 mm seat (`switch.seat_outer_mm`,
  0.1 mm clear of a 15.6 mm switch housing rim), 1.5 mm of plate under the
  housing's rim and the plate's sleeve below that, with the
  14.15 mm opening; two 5 mm-wide reliefs give the spring clips room, down
  through the sleeve. Seats are checked for a complete plate ring, material
  above their planes and clip obstructions.
- Each opening is probed at nine points.
- Tiles (with their corner notches), tile components, and the Pro Micro, its TRRS jack, both plugs and its reset
  switch must not overlap the chassis or the bottom section.
- **Wires**: each wire, as a tube of its diameter, must miss every other wire
  (wires may touch).
  Wires that hit are listed and highlighted cyan.
- **Solder access**: with the bottom section off, a 2 mm round iron's way 8 mm
  straight down from each pad, along the key's normal, must miss the chassis.
  Blocked pads are listed and highlighted cyan.
- Keycaps at rest and over their full travel plus clearance must not touch it.
  Caps are 18.5 × 18.5 × 11 mm, tapering to 14 × 14 at the top; the middle thumb's
  is 28 × 18.5 × 11 mm with **2.5 mm clearance** (0.3 mm elsewhere). The cap's
  bottom is 6 mm above the plate at rest and, with the **3.5 mm travel**, 2.5 mm
  above it at full press (`switch` in the configuration).
  Each keycap's room is cut out of the chassis before this check, so it fails
  only when the room is smaller than the keycap's travel; the keycap room check
  below reports chassis that was in the way.
- Without the bottom section the frame must be one piece; loose pieces over
  0.5 mm³ are listed and highlighted. It must also hold together along its
  foot: a section 1.5 mm above the floor must be one connected area. Separate footprints are listed and highlighted.
- No chassis may be built where a keycap goes. Each keycap's room (the keycap
  and its clearance from its lowest point up, and the switch housing's rim below
  that) is cut out of the chassis, and whatever it removed is listed and
  highlighted orange.
- The closest distance between resting keycaps of the finger columns, the thumb
  row and the extra thumb row is listed; touching fails.

Failures are highlighted in the viewport: red for at-rest or hardware overlap,
orange for the keycap travel envelope and for chassis cut away by a keycap's room, pink for opening, seat or loose-piece
defects, cyan for wires and blocked solder access. Click a result to isolate it, or **Show all failures**.

Envelopes are conservative boxes, not measured parts. PCB retainers, minimum wall
thickness and global self-intersections are not checked. Passing does not qualify
a print.

`src/worker.ts` rebuilds outside the UI thread. Results carry revision IDs, so a stale
result cannot replace a newer edit. A 30-second watchdog stops a stuck worker. Each
build frees every geometry object it made, including those made with `new`, so the
geometry engine's heap stays flat from one build to the next (`tests/geometry.test.ts` pins that
objects made with `new` are freed); a fresh worker still takes over every eight builds as a safety net. A
build of the default project takes about 2 s in node on a laptop, more than half
of it the wire router (the browser routes the wires in a worker of their own). The
checks cut each probe against the frame near its key, not the whole frame.

## Prototype flags and dev-only tools

The dev server (`make editor`) has two things the built site (`dist/`) does not:

- **`?hand`**: a measured hand laid out over the keys. Swung in was laid out from
  it; here its settings can be tuned, and the hand's reach, the board's height
  against the tray and the printed test frame checked. Design in [hand prototype](../docs/hand-prototype.md);
  its browser test is `npm run test:hand`.
- **Marks**: press **M** to paint on the model where something looks wrong (hold Alt
  to orbit), add a note and save. Each mark is a JSON file and a screenshot in
  `marks/`. Clicking a saved mark in the list goes to its view and shows its strokes
  in green. `?mark=<id>` opens a saved mark's view and `?marks=0` hides the saved
  marks (`src/marks.ts`, `vite.config.ts`). Its browser test runs with `npm run test:hand`.

## Validation

```sh
npm --prefix editor test               # layout, chassis and checker tests
npm --prefix editor run test:browser   # real Chrome workflow
npm --prefix editor run test:fit       # mechanical acceptance of the default or a saved project
npm --prefix editor run fingerprint    # geometry fingerprints, for refactors
npm --prefix editor run default-config # regenerate the default project from Swung in
npm --prefix editor run format         # Prettier
```

A change meant to leave the geometry alone must leave `fingerprint`'s output
unchanged: save it before the change and diff it after. It builds the default
project and its variants.

Construction sizes that are not in the config are named in `SIZES` at the top of
`src/chassis.ts` and `src/capybara.ts`, the plates' in `src/plates.ts`, the seats' in `src/seats.ts`, the wiring's in `WIRING` in
`src/wiring/common.ts`; the checks' sizes and limits
are in `CHECKS` in `src/solid.ts`.

`test:fit` optionally takes a saved project file and exits nonzero whenever a
check fails.

The default project is Swung in, extra thumb keys included, laid out by the hand
model on the defaults before it; `npm run default-config` regenerates
`src/default-config.json` (`tests/default-config.ts`). On the Capybara it passes
every check, and the tests pin that. Every test builds Swung in, or a deliberate change of it.
The seam check (`tests/seams.ts`) finds where the Capybara's parts meet badly
on the mesh as the editor draws it (slivers, ledges, unintended creases, gaps,
thin skins, swayed shading), with the parts that meet there; `tests/seams.test.ts`
pins its count per junction class (none for the bridges between ribs: they must
meet the ribs cleanly), checks that fused drops leave no
gap or slit between them, and checks that every drop stands flush on the rail.
The plates, seats and sleeves are meant geometry, so their own faces are not
counted.

The decisions the editor's cleanup left to the owner are in
[CLEANUP-PLAN.md](CLEANUP-PLAN.md).

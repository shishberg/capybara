# Low-profile Capybara

A proposal for a lower, more compact Capybara: still MX switches, still a split
hand-wired board on a printed chassis, but much flatter than the
[Capybara frame](../docs/editor-chassis.md), wireless, and modelled as one
parametric design in Python (triangle meshes cut with
[Manifold](https://github.com/elalish/manifold)) instead of the editor's
pipeline. It is a layout study: nothing here has been printed.

What carries over from the current design is the [measured hand](../hand/README.md)
and the way it moves. What changes:

| | Capybara | Low-profile |
|---|---|---|
| Tent | 15°, pitch 5° | 6°, no pitch (`tent_deg`, `pitch_deg`) |
| Key placement | Hand model with the wrist held 56 mm up | The fingertips' resting prints on flat paper, each column curved round the finger's reach |
| Height to the highest cap | 63 mm | about 38 mm (26 mm at the pinky) |
| Caps | Tall tapered caps | Cherry profile |
| Keys | Bought RGB key tiles, hand-wired | Hotswap sockets in pockets, hand-wired, no tiles, no LEDs |
| Controller | RP2040 Pro Micro per hand, TRRS between hands | Tenstar red ProMicro NRF52840 per hand, BLE, USB-C for charging only |
| Power | USB | A small LiPo per hand and a slide switch |
| Chassis | Open rib frame, bottom section | An enclosed shell of one thickness, screwed onto a plinth that carries the tent |

## Files

| File | What it is |
|---|---|
| `BUILD.md` | How to build a pair of halves, the pins, and what they do when running. |
| `REVIEW.md` | The blind build review of 6 November 2026, and the decisions it left open. |
| `build.py` | The command: builds the parts to STL and the assembly to 3MF; see its header. |
| `render.py` | PNGs of the right half for a person to look over; see its header. |
| `params.py` | Every parameter, commented. Sizes marked PROVISIONAL are not from measured parts. |
| `layout.py` | The measured hand (read from `hand/left-hand.json`), the key frames from it, the tent and lift, the bay for the controller and battery, the screw positions; and the Capybara's own key frames for the capybara design. |
| `parts.py` | The switch, Cherry cap, hotswap socket, diode, controller, battery, power switch and reset button, and the room each takes; and the Capybara's key tile, Pro Micro, TRRS jack and reset switch. |
| `chassis.py` | The body, its pockets and channels, the plinth with its well and bosses, and the checks. |
| `shell.py` | The capybara design's body and plinth, its support volumes for printing, and its checks (below). |
| `lib.py` | Frames as 4 × 4 matrices. |
| `test_checks.py` | Proves the wiring checks fail on a blocked channel; `make lowpro-test` runs it. |
| `test_swung_in.py` | Proves the capybara design's keys and parts sit where the editor puts them; `make lowpro-test` runs it. |

It needs [uv](https://docs.astral.sh/uv/). The `make` targets use it to set up
`.venv` from `requirements.txt` the first time they run.

Build from the repository root. `make lowpro` runs the checks and writes the
right and left bodies and plinths as STL and each half's assembly as 3MF into
`output/lowpro/`. `make lowpro-check` runs only the checks. `make lowpro-render`
writes PNGs of the right half into `output/lowpro/renders/`. The
[chassis editor](../editor/README.md) shows the assemblies (its **Case** picker).
One part at a time, or with a parameter changed:

```sh
.venv/bin/python -m lowpro.build --half left --part body
.venv/bin/python -m lowpro.build --set tent_deg=4 --set outline_style='"hulls"'
```

## The layout

Everything is laid out for the right half in the hand's axes, then tented and
lifted. The left half is the mirror image of it, except that its switches and
sockets are the same parts, which can't be mirrored: each key's pin holes, socket
pocket, terminals' wells and boss are drawn true, and only the rest is mirrored.
Its socket reaches 1.27 mm less far toward the column channel and that much further
the other way, so each half is its own build.

**Finger columns.** Each home key sits under where its fingertip rested on the
paper, facing straight up, and its column runs along the finger's measured
heading. The other rows lie on an arc about a point above the home key. That is
the movement kept from the hand model: the reach between rows is the finger
curling and straightening about a point between the PIP joint and the knuckle,
not sliding flat. At the default `reach_mix` the radii are 62 to 69 mm, 51 for
the pinky, so the top and bottom keys tilt 14 to 19° toward the home key and
rise 2 to 3 mm. The fifth, inner column is the index column carried toward the
thumb.

**Thumb.** The near and far thumb keys start on the circle the thumb's pad swept in
the photographs, either side of the resting print's angle, and the home key on the
straight line between them at that angle. The row is then turned counterclockwise
in plan about the near key and leaned about the near key's y, the far key going
down, so home and far no longer sit on the prints. The extra pair x1
and x2 is a flat fourth row under the middle and ring columns.

**Matrix.** The same 4 × 5 as the Capybara: each thumb key chains onto a finger
column's wire (x2 C0, near C1, x1 C2, home C3, far C4), so the
[firmware's](../firmware/README.md) matrix carries over, though it needs an
nRF52840 build, with its own pins. [Building it](BUILD.md) has the pins, the
wiring and how it should behave when running.

## The chassis

The chassis is two printed parts: the body, which holds the keys, and the plinth
under it, flat on the desk. The seam between them is one plane under every socket
and diode, so the body prints flat on it with its top surface up, and the plinth takes
up the height to the desk. `seam_tent_deg` sets its tilt: 1.6° gives the lowest case,
with the pinky-home socket and thumb-far diode holding the seam down and the screws at
the pinky end holding it up. A flatter seam gives a thicker body, deeper shafts and a
longer print. The top is one smooth surface, with a flat land round
each switch's hole for its lip to sit on, `switch_land_mm` wide, tapering over
`switch_taper_mm` into the surface. Each socket goes up a shaft from below, and a boss on the
plinth holds it against its pocket's ceiling when a switch is pushed in. Those
open shafts mean nothing can sit under a key, so the controller, battery, reset
button and power switch lie in a well beside the inner column. The well's walls and
ceiling are the body's and its floor is the plinth's top, with a shallow pocket under the
battery and the board, which lies level on a rest in it. All the electronics are then in the body with the keys, and no wire
crosses the seam: the plinth is a lid that goes on last and comes off with everything
still wired. The wires run in channels in the
body's underside, sunk into the plinth's top so they can cross and lie side by
side without adding height or footprint. Use insulated wire for the rows, which
cross the column wires. The channels are a first cut, straight slots that merge
where they meet: look at `wiring-below.png` before trusting a route, and edit
`channels()` in `chassis.py` to change one.

The seven screws locate the plinth under the body. A pinky
cap comes down past the ring key's plate beside it, so the body gives every cap its
room (its base's outline straight up from the plate and on out
of the case, room for the finger too), which notches that plate's edge.
Where two caps' rooms come within `min_wall_mm` of each other, the web between
them goes too, down to where it's that thick, since a thinner one won't print.

## The capybara design

`--preset capybara` builds the same kind of case round the Capybara's own
electronics instead: the [Capybara's](../docs/editor-chassis.md) hand-wired
RGB key tiles, matrix and pins, and its [Pro Micro, TRRS jack and reset
switch](../docs/pro-micro.md), so a harness wired for the Capybara drops in.
`params.py design` picks it, and the sizes it shares with the editor are read
from `editor/src/default-config.json`, so each lives in one place. The files go
to `output/lowpro/capybara/`, and a `<half>-print.3mf` for each half as well (Printing, below).

```sh
.venv/bin/python -m lowpro.build --preset capybara
.venv/bin/python -m lowpro.render --preset capybara
```

The keys are the editor's Swung in layout at its tent, each frame equal
to the editor's to 1e-6 on both halves (`test_swung_in.py` runs the editor's
own placement, `editor/tests/key-frames.ts`, to compare), with the editor's
base plate top as the seam. The outline is two convex hulls, the finger
block's (its keys' plates and pockets, and the Pro Micro's and the jack's
rooms, so both stand wholly inside the walls) and the
thumb cluster's, walled and rounded, so it runs straight past the steps between
keys and turns in only where the thumb cluster meets the finger block. The top
steps between columns too, since Swung in's columns sit at different heights.

The body is this design's shell, hollowed to its walls and skin, with a wall
round each cap's room where the room cuts down through the top. A lower key's
room rises beside its higher neighbour's pocket, where a full skin would stand
in that tile's way out, so the wall gives way to that tile's way down off its
pegs. Each switch sits in a plate in the skin, with the editor's sleeve under
it, and its tile hangs in a pocket under the plate, walled from the plate down
to the board's underside and no further, so the wires that leave under the
board's edges pass beneath the rim; neighbouring pockets share a wall. A round
peg stands from the sleeve into each of the tile's corner notches, the notch
less the solder jig's fit, webbed out to the pocket's corner, which the notch
leaves free. Where the plates and pockets seal a scrap of the hollow off from
the plinth, it is left solid, since it would be a void in the print. There
are no channels, sockets or diodes: the inside is open, and the wiring lies
loose on the plinth, which is a flat plate on the desk as thick as the editor's
base plate, with lowpro's skirt bridging the notches round the thumb cluster.
The Pro Micro, the jack and the reset switch stand where the editor puts them,
the plugs' openings chamfered at the wall's outer face, the reset switch turned
square to the wall its plunger points at, behind an even skin with a stop
behind it, and each part has a cradle on the plinth. There is room over the
Pro Micro's pins for Dupont housings and their wires.

M2 screws into heat-set inserts hold the plinth, all inside the outline: for
each of the outline's corners that turns 60° or more (bends less than a boss
apart count as one corner), the nearest spot where the boss, up to its top,
clears the tiles, their way down off their pegs, the caps' rooms, the parts
and their cradles, unless a screw already stands within 40 mm. Each boss is a
post from its seat to `min_wall_mm` over its insert, standing in the wall, so
it stays out of the tiles' and the wires' way. The body stands on the plinth,
so its weight holds the plinth's edges to the wall; the screws hold the two
together when it's lifted. The plinth is too thin for a screw's head and its
grip, so each screw has a seat: a pad on the plinth, into a recess in the
body's underside wide enough for the elephant's foot.

The harness goes in from the underside with the plinth off: the body upside
down, each tile up into its pocket, then the switches in from the top through
the plates into the tiles' sockets, then the plinth and its screws. With the
plinth off, the opening is far bigger than a tile, so the build doesn't model
the tiles' whole ways in. It checks that each tile comes straight down off its
pegs, out past its pocket's rim, without meeting the body, since below that
the underside is open to turn it out; that the switches, notched tiles, caps at full travel, Pro
Micro with its housings, jack and reset switch clear the case, that the plugs
go in through the walls, and the shared checks on the screws, the top's skin
and the body against the plinth. The build's report gives the heights, the
plan, the plugs' mouths and the screws.

### Wells

`--preset capybara_wells` is the same case with each switch in a well. The top
over each key is its plate's plane raised `well_depth_mm` (the cap's skirt over
the plate at rest) along the key's normal, and the cap's room cuts the well, so
it is square to the key and its floor is the plate. The top stays at that
plane over the well's wall too, falling away at 45° past it, so a steeply
tilted key's well has its wall all round. A cap's room is its base
grown by `cap_room_clearance_mm`, corners included, so a cap's corner is as
clear as its sides. The floor meets the walls in a cove (`well_cove_mm`),
which the cap clears at full travel. The caps are opaque, so the tiles' light
shows only round their skirts. The well's walls and its cove may throw some of
it back up past the cap, which a print would have to show. The outline walls
round each key's well as well as its pocket, so every key on the edge has a
wall, which grows the half, nearly all of it in the thumb cluster.

Between keys a wall stands only where there's room for one. Keys in a column
lean together, so their wells meet above the top and leave a web between them
whose top is a knife edge. That web is cut down to where it's `min_wall_mm`
thick (the chassis, above), and so is the thin web between the inner and index
columns. The files go to `output/lowpro/capybara_wells/`, and the editor's Case
picker shows it as **Low-profile shell with wells**.

### Printing

The body prints top up with the seam on the bed, since upside down leaves the
top marked. `<half>-print.3mf` is the body placed that way, in Bambu Studio's
project format, which Anycubic Slicer Next shares. It carries no printer or
process settings, so the slicer's own apply. It has two support volumes and
asks for only critical support elsewhere, since a sag on the underside away
from the pockets holds nothing:

- An enforcer round each pocket's rim, which starts in mid air and is the tile's
  way in, so it gets full support and interface.
- A blocker filling each tile's room, so the room's ceiling bridges and no
  support is left behind the pegs.

Sliced with tree support at 15° and 0.08 mm layers, a half takes about 25 cm³
of support and interface, against 14 without the volumes. The extra support
is under the pockets' rims, which are at least 95% supported against a median
of 55% without it. About 0.2 cm³ ends inside the pockets, at their rims, which
clears from the open underside.

## Checks and what they don't cover

Only writing a part checks that it is one closed solid spanning the outline:
`make lowpro-check` skips that. A failed check doesn't stop the build: it still
writes the files, then exits 1.

The wiring has two checks. One finds a way for a wire from every end to the
controller, by any path. The other holds each channel to its own route: a wire
has to lie along every straight run from end to end, clear of the seam, or it
gets pinched there.

Not checked:

- The hand's reach: the `?hand` prototype's checks don't run on this layout.
- The walls between most channels and the keys' pockets, since channels join
  keys by design.
- How many wires a channel holds at once: the wiring check tries one at a time.
- Real part sizes: the Cherry cap, the socket's tabs, the controller, the battery
  and the power switch are nominal.

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
| Plan per half | | 139 × 142 mm |
| Caps | Tall tapered caps (18.5 × 18.5 × 11) | Cherry profile |
| Keys | Bought RGB key tiles, hand-wired | Hotswap sockets in pockets, hand-wired, no tiles, no LEDs |
| Controller | RP2040 Pro Micro per hand, TRRS between hands | nRF52840 Pro Micro (nice!nano / SuperMini) per hand, BLE, USB-C for charging only |
| Power | USB | A small LiPo per hand and a slide switch |
| Chassis | Open rib frame, bottom section | An enclosed shell of one thickness, screwed onto a plinth that carries the tent |

## Files

| File | What it is |
|---|---|
| `build.py` | The command: builds the parts to STL and the assembly to 3MF; see its header. |
| `render.py` | PNGs of the right half for a person to look over; see its header. |
| `params.py` | Every parameter, commented. Sizes marked PROVISIONAL are not from measured parts. |
| `layout.py` | The measured hand (read from `hand/left-hand.json`), the key frames from it, the tent and lift, the bay for the controller and battery, the screw positions. |
| `parts.py` | The switch, Cherry cap, hotswap socket, diode, controller, battery and power switch, and the room each takes. |
| `chassis.py` | The body, its pockets and channels, the plinth with its well and bosses, and the checks. |
| `lib.py` | Frames as 4 × 4 matrices. |

It needs Python 3 with `manifold3d`, `numpy`, `scipy` and `triangle`
(`pip install manifold3d numpy scipy triangle`), and `pyvista` for the renders. Build from the repository
root with `make lowpro`: the right and left bodies and plinths as STL, the
right assembly (body, plinth, switches, caps, sockets, diodes and electronics,
each a coloured, named mesh) as 3MF, and the checks, into `output/lowpro/`.
The whole build takes about a second (`--verbose` shows the stages). `make lowpro-render`
writes PNGs of the right half to look over into `output/lowpro/renders/` (the
assembly, the body and plinth from above, the wiring through a see-through
body, the underside, a pocket close-up and sections).
One part at a time, or with a parameter changed:

```sh
python3 -m lowpro.build --half left --part body
python3 -m lowpro.build --set tent_deg=4 --set outline_close_mm=12
```

## The Capybara preset

`python3 -m lowpro.build --preset capybara` (and `lowpro.render --preset
capybara`) builds this chassis with the Capybara's choices, into
`output/lowpro/capybara/`: three parameters switch the design and the rest
come from the editor's project, so they stay the Capybara's, and a fourth
moves the controller (`PRESETS` in `params.py`):

- `key_layout = "swung_in"`: Swung in's keys and its 15° tent, as the editor
  places them (`editor/tests/key-frames.ts` prints them; the build runs it, so
  it needs the editor's `node_modules`).
- `key_parts = "tiles"`: the RGB key tiles hang from the switches, each in a
  shaft open to the underside along its key's axis (straight down, a tilted
  tile's shaft runs past a lower neighbour's ledge). Shafts are wiring space
  and may meet; the walls check holds each key's seat (its switch's pocket
  and the tile's footprint up to the plate) clear of every other key's shaft.
  Nothing stands under a tile. The column channels and trunks are 5 mm wide
  for the LEDs' data and power, and a row runs straight from one tile's R hole
  to the next's.
- `link = "trrs"`: an RP2040 Pro Micro, its TRRS jack beside it with the
  barrel out of the back wall, and the reset switch on edge in the inner side
  wall, its plunger through a `reset_skin_mm` skin. No battery or power switch.
- `bay_place = "under"`: the controller's bay is in the plinth under the inner
  and index columns' top keys, not beside them. Its inner side and back reach
  under the room of the inner column's channel and of the back trunk, so the
  walls the ports and the reset switch go through stay `wall_mm` thick. The
  tile shafts and channels over the bay open into it; the walls check holds
  only the keys' seats to it. The plan is 28 mm narrower (119 mm across). The
  inner side's screw moves to in front of the inner column, past the front
  trunk, because the inner wall beside the leaning shafts has no room for one.

`--set knob=True` adds an AS5600 magnetic knob, written to
`output/lowpro/capybara-knob/` when built with `--out`. Its axis runs across,
square to the inner side wall in front of the bay, `knob_z_mm` over the desk.
The knob sits outside the wall on a shaft through a 608 bearing pocketed flush
in the side wall. Its rooms are cut from the plinth and the body alike (as
the bay's are), so the bearing is held wherever the two meet across it. A diametric magnet sits in the shaft's end, a millimetre
past the bearing. The sensor board stands in a slot behind it, chip toward the
magnet, and drops in from the plinth's top before the body goes on. Its three
wires (GND, 3.3 V, OUT to an ADC pin) run along a slot into the well. The
sizes in `params.py` are provisional, taken from the parts in hand.

With the Capybara's keycaps as well, it comes out as tall as the Capybara: 62.8 mm
to the highest cap's top corner (cap tops 28 to 57 mm over the desk at their
centres), with the body 14.4 mm thick (its steepest keys lean 45°) and the
plinth 2 to 29 mm under the keys. Swung in's steep thumbs and
pinky top key leave room for only a 1.5 mm top round.

The body's and the plinth's blanks are each one closed triangle mesh, built
from the surfaces' functions: the top surface and the underside over one
triangulation of the plan, the round's arcs at each station along the outline,
and the walls one vertical quad per outline segment, so the walls are exactly
vertical and nothing but the openings through them (the USB port, the switches,
the TRRS plug, the knob's bearing) cuts them.
Everything cut from the blanks or added to them (the cells' planes put back,
the pockets, channels, well, screw holes and bosses) is an exact solid, and the
booleans are Manifold's. The meshes' triangles are about `mesh_mm` across and
every curve is within `mesh_tol_mm` of its chords.

The files are outputs only: the design is the code and `params.py`, and a
change is made there and rebuilt. The build refuses to write a part that is not
one closed manifold solid (a stray piece or a sliver left by a boolean is a
second solid) or that does not span the outline (a boolean that loses the part
leaves a fragment behind).

## The layout

Everything is laid out for the right half in the hand's axes (origin at the
middle fingertip's resting print, +X toward the pinky, +Y away from you, +Z up),
then tented and lifted. The left half is the mirror image.

**Finger columns.** Each finger's home key sits under where its tip rested on the
paper, its cap top at the print and the key facing straight up; the column runs
along the finger's measured heading (`splay_scale` scales the resulting splay).
The other rows lie round an arc about a point above the home key: the fingertip's
reach radius, measured from the resting joints, `reach_mix` of the way from the
PIP joint (0, a tight well) to the knuckle (1, flat). At the default 0.5 the
radii are 62 to 69 mm, 51 for the pinky, so the top and bottom keys tilt about
14° toward the home key and rise 2 to 3 mm. That is the movement profile kept
from the hand model: the reach between rows is the finger curling and
straightening about a point between those two joints, not sliding flat. The
fifth column inside the index column is the index column carried `inner_gap_mm`
toward the thumb.

**Row pitch.** `row_pitch_mm` is the spacing between neighbouring caps at their
skirts, not at the plate. On a concave column the plate pitch has to be wider
(about 20.5 mm for 19.05 at the skirts) or Cherry caps touch at their bottom
edges; the model works the plate pitch out per column, and each key's plate cell
is that deep, so the cells of a column abut. The fingertip's travel between
rows comes out at 16.6 to 17.2 mm (the report echoes it).

**Thumb.** The three thumb keys lie on the circle the thumb's pad swept in the
photographs (radius 47 mm), the home key at the resting print's angle
(`thumb_around_deg`, 112°), the near and far keys a pitch along the circle either
way, which puts them within a few mm of the swept-in and swept-out prints. The
keys are parallel to the home key (`thumb_fan` 0, as Swung in has them: fanned 1u
caps on a 47 mm circle meet at their inner corners unless the pitch is about
23 mm), tilted 6° per key toward the middle (`thumb_well_deg`), and their cap tops
sit 1 mm under the finger home keys' (`thumb_drop_mm`). The extra pair x1 and x2
is on, flat, on the circle 22 mm inside the row's, a cell apart and centred on the
home key; the measured curled-in print lands on x2. `thumb_home_u` makes the home
key 1.5u, lying along the row.

**Matrix.** The same 4 × 5 as the Capybara: each thumb key chains onto a finger
column's wire (x2 C0, near C1, x1 C2, home C3, far C4), so the
[firmware's](../firmware/README.md) matrix carries over, though it needs an
nRF52840 build.

## The chassis

**Body.** A shell of one thickness, this way up. Its top surface is the key
field: inside each key's cell the plate's plane, exactly; between cells the
nearby cells' planes blended by distance, each taken at its cell's nearest
point, so the surface runs smoothly across the column stagger and the gap to
the thumb cluster without extrapolating any plane. The blend is a quadratic
spline surface through the field sampled every `surface_step_mm`, and
it starts `surface_blend_mm` inside each cell's edge; then each cell's plane is
cut and filled back exactly, `cell_step_mm` past its edge, so where two cells
of different heights abut (the bottom row's ring and pinky keys differ by
5 mm) the surface steps at the higher cell's edge rather than ramping across
both. Its underside is the same surface dropped
straight down by the room every key needs (the socket's bottom and
`under_socket_mm` under it, taken along the most tilted key's normal: 9.7 mm),
so the body is as thick under the inner column as under the pinky and every
wiring channel is the same depth, and flat under each cell as the top is.
Where that would take it below the body's floor (`plate_gap_mm` over the
plinth's thinnest, `bottom_plate_mm`) it is cut off flat on the floor, as
under a steep key's low edge. The tent and the wells live in the plinth
under it. The footprint (`outline_style`) is a convex hull round the finger
field (its cells, the bays and its wire channels) and another round the thumb
cluster, joined by a third round the thumb row, the bottom keys nearest it and
the bays, so the inner edge runs straight from the bays to the thumb cluster
and only the notch under the pinky side stays open. Every channel lies inside
one of the hulls, so none of them shows in the outline. A `wall_mm` wall goes
round it (6 mm, which carries the trunk channels and the screws' inserts), the
notch is rounded to `outline_close_mm` and every convex corner to
`outline_round_mm`: straight sides, the stagger steps filled, and the result
smoothed into one closed spline. ("closed" instead follows the cells and
channels, with the gaps between them closed up.) The walls are vertical, and
the top edge is rounded to `top_round_mm` (4 mm; 0 leaves it sharp): a true
rolling-ball round, tangent to the top and the wall, built from the ball's
closed form: at each station along the outline the ball's section is an arc
from the wall to the top, and the arcs at neighbouring stations are joined.
The round needs room: the top's convex curvature must be gentler than
`top_round_mm` where the round runs, and the build stops if the round would
fold at a corner, cross itself or reach under the underside, or if a cell's
plane would reach into it.
No cutouts, ribs or gaps. The underside is curved and tilted, so the body
prints on support (or on a raft): lay it on the tent plane and the support is
at most a few millimetres tall; the plinth prints flat.

**Keys.** Each key gets the 14 mm switch hole with 0.15 mm clearance through a
1.5 mm plate, the clip reliefs on its ±y sides, the housing's pocket to 5 mm
below the plate, then a 1.6 mm layer in place of a PCB with holes for the
centre post, the side posts and the two pins, and under that the hotswap socket's
pocket, open downward as a shaft to the underside. The shaft and the solder wells
are cut vertically, square to the desk, however the key tilts, so the
plinth's bosses stand straight and no sliver of body is left under a tilted key.
The socket is pushed up the shaft from below until it meets the pocket's
ceiling, where the switch's pins reach it; the socket body is modelled as the measured 11.6 × 6.2 × 1.9 mm
envelope cut into the two boxes about its pin cups (`socket_body` in
`parts.py`), with its two solder tabs out of the ±x ends. A solder well under
each tab reaches up from the underside so a wire can be soldered to the tab
after the socket is in; it stays `min_wall_mm` inside the key's cell, so the −x
tab's well ends about at the tab's tip. There are no LEDs.

**Wiring channels.** Slots in the underside, from the underside up to the
sockets' tops (about 3 mm deep, the same everywhere), closed by the plinth:

- a column channel up each column past the keys' −x tabs, with a pocket for
  each key's diode (DO-35) in line, so the diodes' legs make the column wire as
  in ordinary hand-wiring;
- a row channel from each key's +x tab along the next cell's north edge to its
  +x tab, crossing that key's column channel on the way (use insulated wire for
  the rows);
- the inner column's channel is a wider trunk (`trunk_w_mm`): the three row
  wires join it;
- a trunk in the back wall from the pinky column's top along to the inner
  column and on over the well's rim, which the columns' wires follow, and one in
  the front wall along the bottom row that joins the thumb cluster;
- in the thumb cluster, a trunk along the three row keys' north edges (the
  thumb row's wire and the thumb keys' column wires on their way to the front
  trunk), each key's tabs risen to it, and the extra keys' tabs risen to the gaps
  between the row keys.

The channels are a first cut: each is a straight slot between two points (a hull
of two posts), and where two meet they merge. Look at them from below (`wiring-below.png`)
before trusting a route; `channels()` in `chassis.py` is the list to edit.

**Plinth.** The bottom plate is a plinth: flat on the desk, its top the body's
underside `plate_gap_mm` lower, the same outline. The keys are lifted so that
the lowest point of what hangs under any switch (its tile and the tile's parts,
or its socket, with their clearance, and `under_socket_mm` under that along the
key's axis) sits on the body's floor, so the plinth is `bottom_plate_mm` thick
at its thinnest and about 14 mm under the inner column and the thumbs: it
carries the tent and the wells and the body does not. Where the plinth rises
under a neighbouring key, what hangs under a key is cut from it too. Under
each socket it carries a boss, the socket's shaft inset `boss_inset_mm`, that
rises to 0.15 mm under the socket and holds it against its ceiling when a
switch is pushed in. It is screwed from below with M2 screws into heat-set
inserts in the body's wall at eight points (`screw_points` in `layout.py`:
the pinky's outer side, the thumb cluster's far side and front, the bay's inner
side and front, all edges the trunk channels keep clear of). Each screw sits
in the middle of the wall, `wall_mm / 2` past the cell's or bay's edge, so its
counterbore has the same wall on both sides (0.6 mm at a 6 mm wall; the report
prints the least wall left round any screw). A screw on a cell's −x edge goes
south of the stem, since the −x tab and its solder well come within about a
millimetre of that edge north of it. Each screw hole is counterbored from below so that every screw grips
`screw_grip_mm` of plinth under the body: one screw length (that plus
`insert_depth_mm`, so M2 × 8) fits the thin side and the thick.

**Bay.** Nothing can sit under a socket, since each socket's shaft is open to
the underside, so the controller and battery lie in a well in the plinth on the
inner side of the inner column, `min_wall_mm` from the inner column's cells
(measured down to the body's underside, since a key's cuts lean with it), open
at the top and closed by the body: the
board along the column, components down, its USB-C port out of the back wall
through a chamfered opening; the power switch beside it in the inner side wall,
its pocket open upward so it drops in from the body's side; the battery in
front of the board, in its own pocket, its leads through a notch in the wall
between them (`battery_lead_notch_mm`). The well's floor is `bay_under_mm` below the parts' room
under the lowest point of the body over the bay (6 mm over the desk), never
less than `bottom_plate_mm`; if the plinth is ever too thin there the parts'
rooms are cut up into the body as well. The back trunk channel runs over the
well's rim at its back corner. The plinth has a pinhole under the board's reset
button.

## Checks and what they don't cover

The build runs these checks before it writes anything, fails naming what met
what, and exits 1 (`make lowpro-check` runs only the checks). Each has been
seen to fail with the setting beside it, and the default layout passes them all.

| Check | Fails when | Seen failing with |
|---|---|---|
| Caps | Two neighbouring caps (grown by `cap_clearance_mm`) meet, at rest or with either pressed `cap_travel_mm` | `--set row_pitch_mm=15` |
| Screw walls | A screw's holes (the plinth's hole and counterbore, the body's insert hole) break into anything else cut from that part: the well, the parts' rooms, a key's pockets, a solder well, a diode's room or a channel | `--set screw_head_d=8` |
| Wiring | A socket tab or tile hole, the battery's leads, the power switch, the jack, the reset switch or the knob's sensor has no path to the controller that a `wire_d_mm` wire fits through, along the channels, pockets and well | `--set battery_lead_notch_mm=0.6` |
| Walls | The rooms of two different parts (a key's pockets, solder wells and diode's room or tile's seat; the bay's rooms, well and the knob's room) come within `min_wall_mm` of each other, or a channel or tile shaft comes within it of the bay (unless the bay is under the keys) or of another key's seat | `--set socket_tab_mm=(3.5,2.6)` |
| Ports | An opening that must go through the wall (the controller's port, the TRRS plug's hole, the reset switch's plunger hole, the knob's bearing pocket) stops inside the outline | `--preset capybara --set mcu_usb_overhang_mm=-6` |
| Knob | The knob's room outside the wall (grown by `knob_clearance_mm`) reaches the desk, the body or the plinth | `--preset capybara --set knob=True --set knob_z_mm=10` |
| Parts | A bought part (the controller, jack, reset switch, knob's bearing and sensor, a socket or tile, a diode) runs into the body or the plinth | `--preset capybara --set knob=True --set knob_clearance_mm=-0.3` |
| Body and plinth | The body and the plinth overlap anywhere | `--set plate_gap_mm=-0.05` |
| One solid | A part written is not one closed manifold solid (a boolean left a fragment) | `--no-check --set trunk_w_mm=12` |
| Span | A part does not span the outline (a cut took its edge away) | `--no-check --set insert_d=20 --set insert_depth_mm=40` |

The build also prints the plate and cap heights over the desk, the shell's
thickness, the plinth's height under the keys, the well's floor, the fingertip
reach per column, the plan size, and the least wall left round any screw's
hole, to the outline or to another cut.

Not checked: the hand's reach (the `?hand` prototype's checks don't run on this
layout), switches and caps against the body (the cells are planar and larger than
a cap, so a cap can't meet the body, but nothing proves it), and the walls
between channels and the keys' pockets (channels join keys by design). The Cherry cap, the
socket's tabs, the controller, the battery and the power switch are nominal sizes.

## Open questions

- Flatter still? `tent_deg` and `reach_mix` are the two knobs; the pinky side is
  already at the minimum (the shell and the plinth's 2 mm).
- The thumb keys' drop and tilt (`thumb_drop_mm`, `thumb_tilt_deg`) are guesses
  from the flat-paper prints; the hand model would say more.
- Fanned thumb keys at a wider pitch versus parallel ones at 19.05 mm.
- Whether the 1.6 mm PCB layer should hold the switch posts more tightly, and the
  socket pocket's fit, both need a test print of one key.

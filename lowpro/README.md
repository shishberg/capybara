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
| Plan per half | | 132 × 131 mm, 11,870 mm² |
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
The whole build takes about two seconds (`--verbose` shows the stages). `make lowpro-render`
writes PNGs of the right half to look over into `output/lowpro/renders/` (the
assembly, the body and plinth from above, the wiring through a see-through
body, the underside, a pocket close-up and sections).
One part at a time, or with a parameter changed:

```sh
python3 -m lowpro.build --half left --part body
python3 -m lowpro.build --set tent_deg=4 --set outline_style='"hulls"'
```

The body's and the plinth's blanks are each one closed triangle mesh, built
from the surfaces' functions: the top surface and the underside over one
triangulation of the plan, the round's arcs at each station along the outline,
and the walls one vertical quad per outline segment, so the walls are exactly
vertical and nothing but the USB opening and the power switch's knob cuts them.
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
`under_socket_mm` under it, taken along the most tilted key's normal: 9.6 mm),
so the body is as thick under the inner column as under the pinky and every
wiring channel is the same depth, and flat under each cell as the top is. The tent and the wells live in the plinth
under it. The footprint (`outline_style`) follows the cells and the bays, with the gaps
narrower than twice `outline_close_mm` closed up, so the outline steps with the
column stagger. A `wall_mm` wall (3 mm) goes round it, and every channel is kept
`min_wall_mm` inside the result, which only shows where the top row's lean
carries the back trunk past the wall. From the bay's back corner to the middle
column the back is one arc, the flattest that clears the stagger and the trunk (`back_edge`).
Inside corners are rounded to what the wall leaves of `outline_close_mm`, convex
ones to `outline_round_mm`, and the result is smoothed into one closed spline. ("hulls"
instead takes a convex hull round the finger field and bays, another round the
thumb cluster and a third joining them: straight sides, about 1,450 mm² more.)
The wall holds nothing but channels' edges: the screws stand inside the key
field (see Plinth). The walls are vertical, and
the top edge is rounded to `top_round_mm` (1.5 mm; 0 leaves it sharp): a true
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
centre post, the side posts and the socket's two collars, which the pins come
down, and under that the hotswap socket's
pocket, open downward as a shaft to the underside. The shaft and the solder wells
are cut vertically, square to the desk, however the key tilts, so the
plinth's bosses stand straight and no sliver of body is left under a tilted key.
The socket is pushed up the shaft from below until it meets the pocket's
ceiling, where the switch's pins reach it. The socket's sizes are Kailh's
drawing (10.9 × 5.89 × 1.8 mm, 3.05 mm over the collars): two boxes round its
step at the centre post (`socket_body` in `parts.py`), with its two terminals
out of the ±x ends, stubs as tall as the body. A solder well round
each terminal reaches up from the underside so a wire can be soldered to its
side after the socket is in; it reaches `solder_well_reach_mm` past the tip and
stays `min_wall_mm` inside the key's cell. There are no LEDs.

**Wiring channels.** Slots in the underside, from the underside up to the
sockets' tops (about 3 mm deep, the same everywhere), going on down into the
plinth's top, `channel_sink_mm` for a channel and `trunk_sink_mm` for a trunk,
and leaving it at least `bottom_plate_mm` thick. That sink is what lets a
`wire_d_mm` wire cross another, and a trunk carry its bundle two wires wide,
without adding height or footprint:

- a column channel up each column, from the socket's shaft out past the −x
  tabs' tips by a wire and `wire_gap_mm`, so a straight column wire runs beside
  each terminal and not under it. Each finger key's diode (DO-35) has a pocket
  south of its socket, off the wire's line: its north leg goes to the −x tab's
  south face and its south leg out to the column wire;
- a row channel from each key's +x tab along the next cell's north edge to its
  +x tab, crossing that key's column channel on the way (use insulated wire for
  the rows);
- the inner column's channel is a wider trunk (`trunk_w_mm`): the three row
  wires join it;
- a trunk along the top row just north of its sockets, from the pinky column's
  top to the inner column and on over the well's rim, which the columns' wires
  follow, and one inside the bottom row's cells, under the south edge of the
  switches' pockets, that joins the thumb cluster; where a column reaches
  further forward than the next one in, this trunk goes straight into that
  column's channel rather than round the stagger, so the pinky's column ends at
  its bottom key's tab;
- in the thumb cluster, a trunk along the three row keys' north edges (the
  thumb row's wire and the thumb keys' column wires on their way to the front
  trunk), each key's tabs risen to it, and the extra keys' tabs risen to the gaps
  between the row keys.

The channels are a first cut: each is a straight slot between two points (a hull
of two posts), and where two meet they merge. Look at them from below (`wiring-below.png`)
before trusting a route; `channels()` in `chassis.py` is the list to edit.

**Plinth.** The bottom plate is a plinth: flat on the desk, its top the body's
underside `plate_gap_mm` lower, the same outline. Its skirt alone goes past the outline: where the outline
is concave, `skirt_radius_mm` arcs bridge the gaps (a disc that size rolled round
the outside, so the skirt never leaves the convex hull), flat at `skirt_h_mm` over
the desk and meeting the wall in a `skirt_cove_mm` cove. It is `bottom_plate_mm` thick
at its thinnest, under pinky home, and about 14 mm under the inner column and
the thumbs, so it carries the tent and the wells and the body does not. Under
each socket it carries a boss, the socket's shaft inset `boss_inset_mm`, that
rises to 0.15 mm under the socket and holds it against its ceiling when a
switch is pushed in. It is screwed from below with M2 socket-head screws into
M2 × 3 heat-set inserts at five points (`screw_points` in `layout.py`), none in
the outer wall. Three are in key cells (ring home, middle top and the thumb
cluster's front), in the web south of the switch's pocket, where no socket, tab
or channel comes: the insert's hole stops under the PCB layer, or beside the
pocket where a key's tilt would bring it too close. One is in the strip beside
the board, which is narrower than the battery, near the USB port; the inner side
wall stands far enough out to leave `min_wall_mm` either side of its counterbore. The neck in
front of the battery has none: its underside falls too steeply for a level pad.
The pinky column has none either: its
keys' cells are the most tilted and leave the least wall, and the thin plinth
under them lies on the desk. The report prints the least wall left round any
screw. The underside tilts and steps under most of them, so each stands on a
level pad `screw_pad_d` across (`screw_seats`): the plinth comes up flat to its
highest point there and the body is cut back flat `plate_gap_mm` above it, so
every insert's mouth is square to its hole. Each screw hole is counterbored from
below so that every screw
grips `screw_grip_mm` of plinth under the body: one screw length (M2 × 5) fits
the thin side and the thick, and the plinth must be thick enough under each to
sink the head (`screw_head_h_mm`), which keeps them off the thin pinky side.

**Bay.** Nothing can sit under a socket, since each socket's shaft is open to
the underside, so the controller and battery lie in a well in the plinth on the
inner side of the inner column, `min_wall_mm` from the inner column's cells
(measured down to the body's underside, since a key's cuts lean with it), open
at the top and closed by the body: the
board along the column, components down, its USB-C port out of the back wall
through a chamfered opening; the battery in front of the board, in its own
pocket, its leads through a notch in the wall between them
(`battery_lead_notch_mm`). The power switch is in the plinth with them, so the
only wires between plinth and body are the keys': a pocket in the strip beside
the board, at the battery's end, its knob flush through the inner side wall. The
pocket fits it to `power_switch_clearance_mm` all round and opens up through the
plinth's top, so the switch drops in from above, knob down its slot, and the
body's underside closes over it. A notch behind it (`power_switch_pins_mm`),
`wire_d_mm` deeper than the pocket, leaves the pins room and passes their wires
into the well.
The well's floor is `bay_under_mm` below the parts' room
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
| Screw walls | A screw's holes (the plinth's hole and counterbore, the body's insert hole) break into anything else cut from that part: the well, the parts' rooms, a key's pockets, a solder well, a diode's room or a channel; or the plinth is too thin to sink a head; or a counterbore breaks out through the plinth's top beside its pad | `--set screw_head_d=8`, `--set bottom_plate_mm=1`, `--set screw_grip_mm=0.6` |
| Wiring | A socket terminal, the battery's leads or the power switch has no path to the controller that a `wire_d_mm` wire fits through, along the channels, pockets and well and past the terminals; or a straight wire can't lie along a finger key's column channel past its terminal and diode, with nothing counted under the terminal | `--set battery_lead_notch_mm=0.6`, `--set wire_gap_mm=-0.5` |
| Walls | The rooms of two different parts (a key's pockets, solder wells and diode's room; the bay's rooms and well) come within `min_wall_mm` of each other, a channel other than the one into the bay comes within it of the bay, or a finger column's channel comes within it of another column's key | `--set socket_tab_mm=(3.5,1.68,1.85)` |
| Body and plinth | The body and the plinth overlap anywhere | `--set plate_gap_mm=-0.05` |
| One solid | A part written is not one closed manifold solid (a boolean left a fragment) | `--no-check --set insert_d=20 --set insert_depth_mm=40` |
| Span | A part does not span the outline (a cut took its edge away) | `--no-check --set mcu_usb_opening_mm=(300,40)` |

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

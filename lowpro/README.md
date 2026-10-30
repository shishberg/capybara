# Low-profile Capybara

A proposal for a lower, more compact Capybara: still MX switches, still a split
hand-wired board on a printed chassis, but much flatter than the
[Capybara frame](../docs/editor-chassis.md), wireless, and modelled as one
parametric OpenSCAD design instead of the editor's pipeline. It is a layout
study: nothing here has been printed.

What carries over from the current design is the [measured hand](../hand/README.md)
and the way it moves. What changes:

| | Capybara | Low-profile |
|---|---|---|
| Tent | 15°, pitch 5° | 6°, no pitch (`tent_deg`, `pitch_deg`) |
| Key placement | Hand model with the wrist held 56 mm up | The fingertips' resting prints on flat paper, each column curved round the finger's reach |
| Height to the highest cap | 63 mm | about 37 mm (26 mm at the pinky) |
| Plan per half | | about 142 × 137 mm |
| Caps | Tall tapered caps (18.5 × 18.5 × 11) | Cherry profile |
| Keys | Bought RGB key tiles, hand-wired | Hotswap sockets in pockets, hand-wired, no tiles, no LEDs |
| Controller | RP2040 Pro Micro per hand, TRRS between hands | nRF52840 Pro Micro (nice!nano / SuperMini) per hand, BLE, USB-C for charging only |
| Power | USB | A small LiPo per hand and a slide switch |
| Chassis | Open rib frame, bottom section | One enclosed body on a screwed-on bottom plate |

## Files

| File | What it is |
|---|---|
| `capybara-lowpro.scad` | Open this. `half` and `show` pick the hand and what to draw; see its header. |
| `params.scad` | Every parameter, commented. Sizes marked PROVISIONAL are not from measured parts. |
| `hand.scad` | The measured hand, generated from `hand/left-hand.json` by `hand_from_json.py`. Do not edit; rerun the script if the hand model changes. |
| `layout.scad` | The key frames from the hand, the tent and lift, the controller and battery bay, the screw positions. |
| `parts.scad` | The switch, Cherry cap, hotswap socket, diode, controller, battery and power switch, and the room each takes. |
| `chassis.scad` | The body, its pockets and channels, the bottom plate, and the checks. |

Render from the repository root with `make lowpro`: the right and left bodies
and bottom plates as STL, the collision check and a few preview images, into
`output/lowpro/`. One part at a time:

```sh
openscad -D 'show="body"' -D 'half="left"' -o left-body.stl lowpro/capybara-lowpro.scad
```

Any parameter can be overridden on the command line the same way (`-D 'tent_deg=4'`).
The surface is a 2 mm mesh (`surface_step_mm`); OpenSCAD 2021 renders a body in a
few minutes, a 2024 or later release with Manifold in seconds. The preview (F5) is
instant either way, and is where to tune parameters.

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

**Body.** One solid, this way up, its top surface the key field: inside each
key's cell the plate's plane; between cells the nearby cells' planes blended by
distance, each taken at its cell's nearest point, so the surface runs smoothly
across the column stagger and the gap to the thumb cluster without extrapolating
any plane. The footprint is the cells closed up (gaps narrower than
2 × `outline_close_mm` filled, with a round of that radius where they meet the
outline), a `wall_mm` wall round them (6 mm, which carries the trunk channels and
the screws' inserts) and every convex corner rounded to `outline_round_mm`
(8 mm): a smooth outline that still follows the hand. The walls are vertical
down to a flat underside. No cutouts, ribs or gaps.

**Keys.** Each key gets the 14 mm switch hole with 0.15 mm clearance through a
1.5 mm plate, the clip reliefs on its ±y sides, the housing's pocket to 5 mm
below the plate, then a 1.6 mm layer in place of a PCB with holes for the
centre post, the side posts and the two pins, and under that the hotswap socket's
pocket, open downward as a shaft to the underside. The shaft and the solder wells
are cut vertically, square to the bottom plate, however the key tilts, so the
plate's bosses stand straight and no sliver of body is left under a tilted key.
The socket is pushed up the shaft from below until it meets the pocket's
ceiling, where the switch's pins reach it; the socket body is modelled as the measured 11.6 × 6.2 × 1.9 mm
envelope cut into the two boxes about its pin cups (`socket_body` in
`parts.scad`), with its two solder tabs out of the ±x ends. A solder well under
each tab reaches up from the underside so a wire can be soldered to the tab
after the socket is in. There are no LEDs.

**Wiring channels.** Slots in the underside, from the floor up to the sockets'
tops, closed by the bottom plate:

- a column channel up each column past the keys' −x tabs, with a pocket for
  each key's diode (DO-35) in line, so the diodes' legs make the column wire as
  in ordinary hand-wiring;
- a row channel from each key's +x tab along the next cell's north edge to its
  +x tab, crossing that key's column channel on the way (use insulated wire for
  the rows);
- the inner column's channel is a wider trunk (`trunk_w_mm`): the three row
  wires join it, and it runs on into the controller's bay;
- a trunk in the back wall from the pinky column's top along to the inner
  column and into the bay, which the columns' wires follow, and one in the
  front wall along the bottom row that joins the thumb cluster;
- in the thumb cluster, a trunk along the three row keys' north edges (the
  thumb row's wire and the thumb keys' column wires on their way to the front
  trunk), each key's tabs risen to it, and the extra keys' tabs risen to the gaps
  between the row keys.

The channels are a first cut: each is a straight slot between two points (a hull
of two posts), and where two meet they merge. Look at them from below
(`show="body"`, view from underneath) before trusting a route; `channels()` in
`chassis.scad` is the list to edit. Where two cuts come within a fraction of a
millimetre of each other a render can leave a speck of body between them (the
right body has a few of under 1 mm³); a slicer drops them.

**Bay.** Nothing can sit on the floor under a socket, since each socket's shaft is
open to the bottom plate, so the controller and battery lie in a bay on the
inner side of the inner column: the board along the column, components down,
its USB-C port out of the back wall through a chamfered opening; the power
switch beside it in the inner side wall; the battery in front of the board. The
body steps down over the bay to a roof `bay_roof_mm` thick over the pockets,
the step a few millimetres inside the inner column's cells (set `bay_roof_mm`
to 0 for no step, and the surface blends over the bay). The back trunk channel
enters the bay at its back corner, under the roof. The bottom plate has a
pinhole over the board's reset button.

**Bottom plate.** The same outline, `bottom_plate_mm` thick, screwed from below
with M2 screws into heat-set inserts in the body's wall at eight points
(`screw_points` in `layout.scad`: the pinky's outer side, the thumb cluster's far
side and front, the bay's inner side and front, all edges the trunk channels keep
clear of), countersunk. Under each socket it carries a boss, the socket's shaft
inset `boss_inset_mm`, that rises to 0.15 mm under the socket and holds it
against its ceiling when a switch is pushed in.

## Checks and what they don't cover

`show="check"` renders where any two neighbouring caps (grown by
`cap_clearance_mm`) meet, at rest and with either one pressed `cap_travel_mm`;
it is empty when the layout is clear, and `make lowpro` fails if it isn't. The
default layout is clear. `report()` echoes the plate and cap heights over the
desk, the bay roof, the fingertip reach per column and the plan size.

Not checked: the hand's reach (the `?hand` prototype's checks don't run on this
layout), switches and caps against the body (the cells are planar and larger than
a cap, so a cap can't meet the body, but nothing proves it), channels against
pockets, wall thickness, and the bay against the key pockets. The Cherry cap, the
socket's tabs, the controller, the battery and the power switch are nominal sizes.

## Open questions

- Flatter still? `tent_deg` and `reach_mix` are the two knobs; the pinky side is
  already at the body's minimum (a socket, a wire and the bottom plate).
- The thumb keys' drop and tilt (`thumb_drop_mm`, `thumb_tilt_deg`) are guesses
  from the flat-paper prints; the hand model would say more.
- Fanned thumb keys at a wider pitch versus parallel ones at 19.05 mm.
- Whether the 1.6 mm PCB layer should hold the switch posts more tightly, and the
  socket pocket's fit, both need a test print of one key.

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
| Plan per half | | 132 × 131 mm, 12,062 mm² |
| Caps | Tall tapered caps (18.5 × 18.5 × 11) | Cherry profile |
| Keys | Bought RGB key tiles, hand-wired | Hotswap sockets in pockets, hand-wired, no tiles, no LEDs |
| Controller | RP2040 Pro Micro per hand, TRRS between hands | Tenstar red ProMicro NRF52840 per hand, BLE, USB-C for charging only |
| Power | USB | A small LiPo per hand and a slide switch |
| Chassis | Open rib frame, bottom section | An enclosed shell of one thickness, screwed onto a plinth that carries the tent |

## Files

| File | What it is |
|---|---|
| `build.py` | The command: builds the parts to STL and the assembly to 3MF; see its header. |
| `render.py` | PNGs of the right half for a person to look over; see its header. |
| `params.py` | Every parameter, commented. Sizes marked PROVISIONAL are not from measured parts. |
| `layout.py` | The measured hand (read from `hand/left-hand.json`), the key frames from it, the tent and lift, the bay for the controller and battery, the screw positions. |
| `parts.py` | The switch, Cherry cap, hotswap socket, diode, controller, battery, power switch and reset button, and the room each takes. |
| `chassis.py` | The body, its pockets and channels, the plinth with its well and bosses, and the checks. |
| `lib.py` | Frames as 4 × 4 matrices. |

It needs [uv](https://docs.astral.sh/uv/). The `make` targets use it to set up
`.venv` from `requirements.txt` the first time they run.

Build from the repository root. `make lowpro` runs the checks and writes the
right and left bodies and plinths as STL and the right assembly as 3MF into
`output/lowpro/`. `make lowpro-check` runs only the checks. `make lowpro-render`
writes PNGs of the right half into `output/lowpro/renders/`. One part at a time,
or with a parameter changed:

```sh
.venv/bin/python -m lowpro.build --half left --part body
.venv/bin/python -m lowpro.build --set tent_deg=4 --set outline_style='"hulls"'
```

## The layout

Everything is laid out for the right half in the hand's axes, then tented and
lifted. The left half is the mirror image.

**Finger columns.** Each home key sits under where its fingertip rested on the
paper, facing straight up, and its column runs along the finger's measured
heading. The other rows lie on an arc about a point above the home key. That is
the movement kept from the hand model: the reach between rows is the finger
curling and straightening about a point between the PIP joint and the knuckle,
not sliding flat. At the default `reach_mix` the radii are 62 to 69 mm, 51 for
the pinky, so the top and bottom keys tilt 14 to 19° toward the home key and
rise 2 to 3 mm. The fifth, inner column is the index column carried toward the
thumb.

**Thumb.** The three thumb keys lie on the circle the thumb's pad swept in the
photographs, the home key at the resting print's angle, which puts the near and
far keys within a few mm of the swept-in and swept-out prints. The extra pair x1
and x2 lies on a smaller circle inside the row, and the measured curled-in print
lands on x2.

**Matrix.** The same 4 × 5 as the Capybara: each thumb key chains onto a finger
column's wire (x2 C0, near C1, x1 C2, home C3, far C4), so the
[firmware's](../firmware/README.md) matrix carries over, though it needs an
nRF52840 build, with its own pins. The same board goes in both hands and the
bay is mirrored, so each half has its own pins, named as they're printed on the
board (008 is P0.08):

| Net | Right | Left |
|---|---|---|
| RT | 006 | 029 |
| RH | 011 | 010 |
| RB | 104 | 106 |
| RX | 106 | 009 |
| C0 | 100 | 111 |
| C1 | 022 | 113 |
| C2 | 020 | 115 |
| C3 | 008 | 002 |
| C4 | 017 | 031 |

The pins follow the wires' three ways into the well. RH, RB and RX cross straight
from the inner column level with the home key to the board's south end, C4 goes
straight from the top inner key's diode to the pin beside it, and RT and the other
columns come round the back trunk to the board's north end.

The right half skips 024 because the board's battery divider is on it. The left
edge has only eight GPIOs (RAW, GND, RST and VCC take the rest), so its RB goes
under the board's south end to 106, the last hole on the far edge. 009 and 010
are the chip's NFC pins, so the left half's firmware has to set them as GPIOs.

The board has no reset button, so the main build's
[tactile switch](../docs/pro-micro.md) is wired to RST and GND. It stands on edge
north of the power switch, its plunger out through the inner side wall to press
with a fingertip. The plunger sits on the seam between the plinth and the body, so
the hole is half in each: the switch drops into the plinth's half of its pocket and
the body closes over it. The wall of the pocket behind it takes the press.

B+ and B− are in line with the header pins at the board's north end, B+ in the
north-west corner and B− in the north-east, so the battery's wires run its
length under it.

## The chassis

The chassis is two printed parts: the body, which holds the keys, and the plinth
under it, flat on the desk. The body's underside is its top surface dropped
straight down, so every wiring channel is the same depth and the plinth takes up
the height to the desk. Each socket goes up a shaft from below, and a boss on the
plinth holds it against its pocket's ceiling when a switch is pushed in. Those
open shafts mean nothing can sit under a key, so the controller, battery, reset
button and power switch lie in a well in the plinth beside the inner column, and the only
wires between plinth and body are the keys'. The wires run in channels in the
body's underside, sunk into the plinth's top so they can cross and lie side by
side without adding height or footprint. Use insulated wire for the rows, which
cross the column wires. The channels are a first cut, straight slots that merge
where they meet: look at `wiring-below.png` before trusting a route, and edit
`channels()` in `chassis.py` to change one. The body's underside is curved and
tilted, so it prints on support or a raft, laid on the tent plane. The plinth
prints flat.

## Checks and what they don't cover

Only writing a part checks that it is one closed solid spanning the outline:
`make lowpro-check` skips that. A failed check doesn't stop the build: it still
writes the files, then exits 1.

Not checked:

- The hand's reach: the `?hand` prototype's checks don't run on this layout.
- Switches and caps against the body.
- The walls between most channels and the keys' pockets, since channels join
  keys by design.
- How many wires a channel holds at once: the wiring check tries one at a time.
- Real part sizes: the Cherry cap, the socket's tabs, the controller, the battery
  and the power switch are nominal.

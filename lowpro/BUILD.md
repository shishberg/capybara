# Building the low-profile Capybara

How to build a pair of halves, and what they should do once built. Nothing here
has been printed or wired yet, so treat the sizes in [Measure first](#measure-first)
as guesses until you've checked them. The nRF52840 firmware doesn't exist yet
either: [Firmware](#firmware) says what it has to do.

## Words used here

Directions are as the half sits on the desk in front of you. **North** is away
from you, toward the USB-C port. The **inner** side is the side toward the other
half, and the **outer** side is the pinky's. On the right half inner is west, and
on the left half it's east. Everything below is written for both unless it says
otherwise.

Keys go by the names they have in `right-assembly.3mf`:

| | Top row | Home row | Bottom row |
|---|---|---|---|
| Inner column | `inner_1` | `inner_0` | `inner_-1` |
| Index column | `index_1` | `index_0` | `index_-1` |
| Middle column | `middle_1` | `middle_0` | `middle_-1` |
| Ring column | `ring_1` | `ring_0` | `ring_-1` |
| Pinky column | `pinky_1` | `pinky_0` | `pinky_-1` |

The thumb has five: `thumb_near`, `thumb_home` and `thumb_far` in a row, `near`
closest to the index column, and `thumb_x1` and `thumb_x2` in a fourth row under the
middle and ring columns.

`make lowpro` writes the parts to `output/lowpro/`, and `make lowpro-render`
writes the pictures this guide refers to into `output/lowpro/renders/`:
`wiring-top.png` and `wiring-below.png` show every channel, trunk and part through
a see-through body.

## Parts

For each half, so double it for the pair:

| Part | Each half | Notes |
|---|---|---|
| Printed body | 1 | `right-body.stl`, `left-body.stl` |
| Printed plinth | 1 | `right-plate.stl`, `left-plate.stl` |
| MX switch | 20 | Five-pin or three-pin. Five-pin switches keep their side posts. |
| Kailh MX hotswap socket | 20 | |
| Cherry-profile keycaps | 20 | R2 top row, R3 home row, R4 bottom row, R3 thumbs |
| 1N4148 diode, DO-35 through-hole | 20 | |
| Tenstar red ProMicro NRF52840 | 1 | |
| 402030 LiPo, about 200 mAh, with protection circuit | 1 | 30 × 20 × 4.2 mm at most |
| MSK-12C02 slide switch | 1 | |
| 6.5 × 6.5 mm SMD tactile switch, 2 mm body | 1 | Pick a firm one, so that a knock doesn't reset the board. |
| M2 × 3 heat-set insert | 7 | For a 3.2 mm hole |
| M2 × 5 socket-head screw | 7 | |
| Double-sided foam tape, about 1 mm thick | a little | Holds the battery in its bay and pads the strip over the board. |
| Insulated stranded hookup wire | about 3 m | About 1.0 mm over the insulation: 28 to 30 AWG with thin insulation, PTFE if you can get it, since it stands up to the iron beside it. The current is a few milliamps. The channels pass 1.6 mm at the very most, with a struggle at every terminal. |

You also need a soldering iron with a fine tip, flush cutters, wire strippers,
tweezers, a multimeter and a long-armed 1.5 mm hex key: the deepest screw is 10.5 mm up
its hole.

## Measure first

These come from listings or memory. Measure the real part and change the
parameter in `lowpro/params.py` before printing:

| Part | What to measure | Parameter |
|---|---|---|
| Controller | Board size, tallest part on its underside, USB-C port's size and overhang | `mcu_board_mm`, `mcu_parts_mm`, `mcu_usb_mm`, `mcu_usb_overhang_mm` |
| Battery | Length, width and thickness, including where the leads leave. The leads need about 45 mm to reach the board's north end: extend them if they're short. | `battery_mm` |
| Slide switch | Body, knob and pins | `power_switch_mm`, `power_switch_knob_mm`, `power_switch_pins_mm` |
| Reset switch | Body, plunger and legs | `reset_button_mm`, `reset_plunger_mm`, `reset_leg_mm` |
| Keycaps | Base, top and height of each row | `cap_base_mm`, `cap_top_mm`, `cap_height_mm` |
| Sockets | The terminals, which vary between batches | `socket_tab_mm` |

Check the controller's pads too, with a meter and against its own silkscreen, before
wiring it. The pin names below are the board's, and clones of it differ: confirm
where B+, B−, RST and GND are, and that nothing else on the board uses a pin in the
[pin table](#pins).

Print one key's worth of the body first if you can, and clear its supports as you
will for the whole part, the leg slots included: check that a switch clips into its
plate, that a socket rises up its shaft and seats, and that a diode's legs lie in their
slots before printing the rest.

## Printing

- **Plinth:** flat on its base, top up, with supports under the screws' seats.
- **Body:** flat on its underside, top surface up. The STL is in the desk's axes, so
  use the slicer's Lay on Face on the underside to take out the seam's tilt. Support goes
  only in the pockets, channels and well, so none touches the top surface. Take care
  clearing it from the well's wall on the keys' side, which is thin.
- **Material:** something that survives an iron nearby. PETG or ASA is safer than
  PLA, since several walls near solder joints are about 1 mm thick.
- Clear all the support out of the channels, shafts and diode pockets. A wire has to
  lie in every channel, and the socket has to reach its ceiling.

## How it's wired

Each half is a 4 × 5 diode matrix. A key joins its row to its column through its
diode, with the diode's band (cathode) toward the column:

```
row wire -> socket terminal -> switch -> socket terminal -> diode -> band -> column wire
```

Four rows (RT top, RH home, RB bottom, RX thumbs) and five columns, C0 at the pinky
to C4 at the inner column:

| | C0 | C1 | C2 | C3 | C4 |
|---|---|---|---|---|---|
| RT | `pinky_1` | `ring_1` | `middle_1` | `index_1` | `inner_1` |
| RH | `pinky_0` | `ring_0` | `middle_0` | `index_0` | `inner_0` |
| RB | `pinky_-1` | `ring_-1` | `middle_-1` | `index_-1` | `inner_-1` |
| RX | `thumb_x2` | `thumb_near` | `thumb_x1` | `thumb_home` | `thumb_far` |

### Pins

The same board goes in both halves, the same way up, so each half uses the edge
nearest its keys and has its own pins. They're named as printed on the board: 008
is P0.08.

| Net | Right | Left |
|---|---|---|
| RT | 006 | 029 |
| RH | 011 | 011 |
| RB | 104 | 104 |
| RX | 106 | 106 |
| C0 | 100 | 111 |
| C1 | 022 | 113 |
| C2 | 020 | 115 |
| C3 | 008 | 002 |
| C4 | 017 | 031 |

The right half skips 024 because the board's battery divider is on it, as
[traced on this board family](https://github.com/sasodoma/nrf52840-promicro). The
left half's edge has only eight GPIOs (RAW, GND, RST and VCC take the rest), and two of
those, 009 and 010, are the chip's NFC pins, which need the firmware to free them. So
it leaves those two empty, and its RH, RB and RX take the same three holes as the
right half's, at the far edge's south end. On the left half those three wires run
across the top of the board's south end to reach them.

### At a finger key

The socket lies in the north half of the key, with a terminal sticking out at each
end. Each terminal has a solder well round it, open to the underside.

- The **diode** lies across the key in its own pocket south of the centre post.
- Its band end's leg goes out to the inner side, to the column wire.
- Its other leg goes out to the pinky side, turns north along its slot past the
  side post's hole, and reaches the pinky-side terminal.
- The **row wire** goes to the inner-side terminal.
- The **column wire** runs north-south in the column channel, on the inner side of
  the terminal's tip, past every key in the column.

### At a thumb key

The other way round. The diode lies across the key in the same place, but:

- The band end's leg goes out toward `thumb_near`'s side of the key, to the column
  wire, which runs past that side's terminal.
- The other leg goes out toward `thumb_far`'s side, turns along its slot and reaches
  that side's terminal.
- The **row wire** goes to the terminal on the near side, by the short channel from
  that terminal to the key's north edge.

### Where each wire runs

Compare this with `wiring-top.png`, where trunks are red and channels blue.

| Net | Route |
|---|---|
| RT | Out of the well's north-east corner (north-west on the left half) along the back trunk. At each column it goes down that column's channel to the top key's row terminal and back up to the trunk: `inner_1`, `index_1`, `middle_1`, `ring_1`, `pinky_1`. |
| RH | Out of the well through the wider exit level with `inner_0`, to that key's row terminal. Then north up the column channel, along the key's north edge into the next column, and south down that channel to the next key's row terminal, and so on to `pinky_0`. |
| RB | Out through the same exit, south down the inner trunk to `inner_-1`'s row terminal. Then as RH along the bottom row to `pinky_-1`. |
| RX | Out through the same exit, south down the inner trunk and on past `inner_-1` to the fork in the bridge to the thumbs. There it divides. One branch goes to `thumb_far`'s corner. The other goes to `thumb_home`'s corner, along `thumb_near`'s north edge to its corner, down the thumb trunk to the foot of the middle column and east along the front trunk, with a branch south to `thumb_x1`'s corner and one to `thumb_x2`'s. Each key takes a short spur to its row terminal. |
| C0 | Starts at `thumb_x2`, north from its corner into the front trunk and east along it to the pinky column, which it joins north of `pinky_-1`'s diode. A spur doubles back south to that diode, about 26 mm of extra wire. The wire goes on up past `pinky_0` and `pinky_1`, and west along the back trunk into the well. |
| C1 | Starts at `thumb_near`, up to its corner, along the thumb trunk and the front trunk to the ring column, which it joins north of `ring_-1`'s diode. A spur doubles back south to that diode, about 12 mm of extra wire. The wire goes on up the column and along the back trunk into the well. |
| C2 | Starts at `thumb_x1`, north from its corner to the foot of the middle column, up it, and along the back trunk into the well. |
| C3 | Starts at `thumb_home`, across from its corner to the foot of the index column, up it, and along the back trunk into the well. |
| C4 | Starts at `thumb_far`, up to the fork, north up the inner trunk past `inner_-1`, `inner_0` and `inner_1`'s diodes, then straight out through the narrower exit level with `inner_1`'s diode, into the well. |

So nine wires reach the well: RH, RB and RX through the wider exit, C4 through the
narrower one, and RT, C0, C1, C2 and C3 down the back trunk's neck.

Channels are grooves in the body's underside, at least 2.2 mm wide and about 3 to
15 mm deep, deepest where the keys stand highest over the seam, and they go on 1 mm
into the plinth's top. Trunks are 3.5 mm wide, up to 18 mm deep in the body, and go on
into the plinth as far as it allows, up to 5.5 mm. So you lay the wires in the
body with it upside down, and they can cross and lie side by side. Rows cross
columns, so every wire has to stay insulated except at a joint.

### The well

The well's walls and ceiling are the body's and its floor is the plinth's top, so all
the electronics are in the body and no wire crosses the seam. The key wires come in
through three slots in the wall on the keys' side.

- **Battery:** in the south bay, leads at its north end, through the notch in the
  wall into the controller's bay.
- **Controller:** in the north bay, components down, USB-C port out through the back
  wall. The battery's leads run north under the board to its north end. The ceiling
  follows the top surface, at least 8 mm over the board's top, so the wires have room
  round the board.
  A strip down the middle of it, padded with foam, holds the board against the floor.
  The wires clear the strip either side and past its south end.
- **Power switch:** in its pocket in the strip on the board's inner side, on the
  plinth's top, knob in a slot through the inner side wall. The knob stands proud of the wall's
  outside (`power_switch_proud_mm`), so you can reach it. That leaves a thin wall outside the
  pocket, on purpose.
- **Reset button:** in the same strip, north of the power switch, on edge, the
  plunger's tip flush with the outside of the inner side wall in a chamfered round
  hole. It sits on the seam, so the plinth
  has half its pocket and the body the other half, and the wires stay in the body's.

Power runs battery + → slide switch → B+, and battery − → B−. Seen from above in
the well, B+ is the board's north-west corner and B− its north-east. Solder both
from the board's underside, the way the leads come, and keep the top flat. Reset is one leg of the button to RST and another to GND: check with
a meter which two legs a press joins, usually the diagonal pair.

## Assembly

Do each half in this order, with the body upside down from step 2 until the plinth
is on.

### 1. Inserts

Press the seven heat-set inserts into the seven holes in the body's underside until
flush with it. Keep them square.

### 2. Sockets and switches

Put the body upside down on something soft, so that gravity holds each socket
against its ceiling.

1. Drop a socket down each shaft, its collars in their holes, until it sits flat.
   Check every one against `pocket-closeup.png`.
2. Lift the body, still upside down, so that the sockets stay against their ceilings.
   Press each switch up into the top face, which now faces down, pins straight, with a
   finger on its socket from the underside, since the plinth's boss isn't there yet to
   take the push. The switch then holds the socket, so the body can be turned either
   way up.

### 3. Diodes and matrix

1. Bend each diode's legs. Put each diode in its pocket with its band to the correct
   side: toward the column wire on every key, which is the inner side on a finger key
   and the near side on a thumb key. Lay the other leg in its slot and solder it to
   its terminal.
2. Run the columns, each from its start key. Don't strip a window in place, down in
   a channel: mark each diode's place on the wire against the body and strip it on the
   bench, or cut the wire at each diode and join the two ends on the leg, as the rows
   do. Solder the band end's leg to it, and leave a tail at the well end.
3. Run the rows, each from the well end to its last key, one length between each
   pair of keys, two wires on each terminal.
4. Check each joint with a meter, using the diode test: holding a key down, a row and
   a column should show that key's diode, only one way round.

Keep every wire below the underside's surface, in its channel. A wire left standing
proud gets pinched at the seam.

### 4. Electronics

Everything from here goes into the well with the body upside down, so each part
drops straight in. Try each one dry first.

1. Solder about 60 mm of wire to the slide switch's middle pin and one outer pin, and
   drop it into its pocket with its knob in its slot and its pins facing the well. Wire
   to the pin that makes knob-north "on". Its pins are about 1.5 mm apart, so tin the
   wires first and check for a bridge with a meter.
2. Solder about 60 mm of wire to the two legs of the reset button that a press joins.
   Drop it into the body's half of its pocket with its plunger in the half hole, and
   its wires through the two ways either side of the stop behind it. It stands half
   out of the pocket: the plinth's half takes the rest.
3. With the board on the bench, solder the switch's free wire to B+, one reset wire to
   RST and the other to GND.
4. Check the battery's polarity with a meter: lead colours aren't reliable. Solder
   battery − to B−, and battery + to the slide switch's other wire, with the switch
   off, and insulate the joint. Stick the battery to the ceiling of its bay with foam
   tape, leads through the notch, so that it stays in the body when the plinth comes
   off. The ceiling curves away toward the south and the keys, so put the tape on the
   battery's north end, where the ceiling comes closest. The battery hangs well clear
   of the plinth's floor, so tape it firmly.
5. Stick foam tape along the strip that stands down from the ceiling of the board's
   bay, and leave its liner on so that the board can move on it. The strip stands
   0.7 mm off the board, so 1 mm of foam is squeezed a little, which is what holds the
   board.
6. Cut the nine key wires (four rows and five columns) to reach their holes with about
   20 mm to spare. Feed each one
   through its hole from the board's top face, and lay the board in its bay, top face
   down on the strip, port in its notch. The wires then lie between the board and the
   ceiling, either side of the strip and past its south end.
7. Solder the nine wires from the side now facing you and trim them flush.

### 5. Close and test

1. Lay the plinth on the upside-down body. No wire joins them, so it goes straight on,
   and its bosses and screws locate it. Check that no wire sits on the seam.
2. Fit the seven screws and tighten them gently. The seam should close without forcing,
   and stop and look if it doesn't. The parts are designed 0.1 mm apart across the
   seam, so a hair of a gap away from the screws is expected.
3. Turn it over, turn the switch on and plug in USB-C. The plinth now holds the board
   and the reset button, and the bosses hold the sockets. Press reset twice, and the
   board should mount as a drive. Flash the firmware, then press every switch by its
   stem. Unplug it and turn the switch off.
4. Fit the caps: R2 top row, R3 home row, R4 bottom row, R3 thumbs.

To get back in, undo the screws and lift the plinth off with the body upside down.
Everything stays wired and can be reached, so fix anything step 3 finds this way.

### 6. Left half

The left half's case is close to the mirror image of the right's, but its switches,
sockets and controller are the same parts, the same way round. Use the left STLs and
the left column of the [pin table](#pins). The pictures show the right half only.

- **Sockets:** a socket's terminals sit at different distances from the key's middle
  on each side, so the left half's are the other way about to the mirror image of the
  right's. The terminals' roles don't change: the row wire still goes to the inner-side
  terminal of a finger key and the diode to the pinky-side one, and on a thumb key the
  row wire to the near side and the diode to the far side.
- **Channels:** they follow the terminals. The thumb keys' column channels stand about
  1 mm further out than the mirror's, and the wider exit into the well is about
  2.5 mm further north.
- **Controller:** B+ and B− stay in the same corners of the board, while the strip
  and the keys swap sides.

## Firmware

There's no nRF52840 build yet. [`firmware/`](../firmware/README.md) is the RP2040
build for the main Capybara, and this one should carry over its keymap and its
matrix, with these changes:

- **Pins:** the [pin table](#pins), a separate set for each half.
- **Matrix:** 4 × 5 per half, rows in the order RT, RH, RB, RX and columns C0 to C4.
  The diodes' bands face the columns, so the rows are driven and the columns are
  read, with pull-downs (`row2col`).
- **Link:** Bluetooth between the halves, not serial. The left half is the central,
  as it is in the main build, and the right the peripheral.
- **Host:** Bluetooth to the host, from the left half.
- **Battery:** each half reports its own level, the right's through the left. It
  reads the chip's VDDH pin, because the divider's pin isn't an analog input, so the
  level reads high while USB is plugged in.
- **Reset:** the button is on RST, so it needs nothing from the firmware.

## Running

- **Power:** each half is on its own. There's no cable between them. A half runs
  from its battery through the slide switch to B+, and the board's regulator makes
  the 3.3 V for the chip. The matrix takes its power from the GPIOs, and there's
  nothing else on the board to power: no LEDs, no display.
- **The slide switch** disconnects the battery alone. Off, the half is dead on
  battery, and it can't charge either.
- **USB-C** is for charging and for flashing, not typing. The port sits about 1.25 mm
  back from the wall's face, in a hole 13 × 7 mm at the port that flares out to the
  face, so a plug's moulding up to that size seats. A half with USB-C plugged in runs
  from it, and charges its battery if its slide switch is on, at about
  100 mA, so about two hours from flat. Check the rate on the bought board.
- **Turning on:** switch both halves on. The right half connects to the left, and
  the left to the host it's paired with, or advertises if it has none.
- **Reset button:** one press restarts the half. Two quick presses put it in its UF2
  bootloader, when it mounts as a USB drive for a new firmware image. Press it with a
  fingertip, in the chamfered hole in the inner side wall.
- **If a key does nothing:** a single dead key is its switch, its socket or its
  diode. A whole dead row or column is that net's wire or pin.

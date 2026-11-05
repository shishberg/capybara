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
closest to the index column, and `thumb_x1` and `thumb_x2` in a second row toward
the base of the thumb.

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
| M2 × 3 heat-set insert | 5 | For a 3.2 mm hole |
| M2 × 5 socket-head screw | 5 | |
| Thin double-sided foam tape | a little | Takes up the battery's play in its bay. |
| Insulated stranded hookup wire | about 3 m | About 1.0 mm over the insulation: 28 to 30 AWG with thin insulation, PTFE if you can get it, since it stands up to the iron beside it. The current is a few milliamps. The channels pass 1.6 mm at the very most, with a struggle at every terminal, and it doesn't fit over the south end of the left half's board. |

You also need a soldering iron with a fine tip, flush cutters, wire strippers,
tweezers, a multimeter and a long-armed 1.5 mm hex key: the screw by the USB port is
11 mm up its hole.

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

The board has to pass under a lip of the plinth to reach its opening. The USB-C
shell and the board together can be 4.3 mm thick, and the lip leaves 4.6 mm over the
well's floor, less whatever the lip sags in printing. Check that on the one-key print's
plinth, or file the lip to fit.

Check the controller's pads too, with a meter and against its own silkscreen, before
wiring it. The pin names below are the board's, and clones of it differ: confirm
where B+, B−, RST and GND are, and that nothing else on the board uses a pin in the
[pin table](#pins).

Print one key's worth of the body first if you can, and clear its supports as you
will for the whole part, the leg slots included: check that a switch clips into its
plate, that a socket rises up its shaft and seats, and that a diode's legs lie in their
slots before printing the rest.

## Printing

- **Plinth:** flat on its base, top up, no supports.
- **Body:** its top surface faces up, laid on the 6° tent plane, on supports or a
  raft. The underside is curved and tilted, so it has no flat face to stand on.
- **Material:** something that survives an iron nearby. PETG or ASA is safer than
  PLA, since several walls near solder joints are about 1 mm thick. The fin between a
socket's pocket and the row channel north of it is only 0.2 to 0.3 mm, and a slicer
may drop it. That does no harm: the collars locate the socket.
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

The right half skips 024 because the board's battery divider is on it. The left
half's edge has only eight GPIOs (RAW, GND, RST and VCC take the rest), and two of
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
| RX | Out through the same exit, south down the inner trunk and on past `inner_-1` to the fork in the bridge to the thumbs. There it divides. One branch goes to `thumb_home`'s corner, then `thumb_near`'s north edge. The other goes to `thumb_far`'s corner, down that key's column channel, then across to `thumb_x2`'s corner and on to `thumb_x1`'s. Each key takes a short spur to its row terminal. |
| C0 | Starts at `thumb_x2`, along to `thumb_x1`'s corner, down the thumb trunk to the foot of the middle column, east along the front trunk to the pinky column, which it joins north of `pinky_-1`'s diode. A spur doubles back south to that diode, about 26 mm of extra wire. The wire goes on up past `pinky_0` and `pinky_1`, and west along the back trunk into the well. |
| C1 | Starts at `thumb_near`, straight across to the thumb trunk, along it and the front trunk to the ring column, which it joins north of `ring_-1`'s diode. A spur doubles back south to that diode, about 12 mm of extra wire. The wire goes on up the column and along the back trunk into the well. |
| C2 | Starts at `thumb_x1`, down the thumb trunk to the foot of the middle column, up it, and along the back trunk into the well. |
| C3 | Starts at `thumb_home`, across from its corner to the foot of the index column, up it, and along the back trunk into the well. |
| C4 | Starts at `thumb_far`, up to the fork, north up the inner trunk past `inner_-1`, `inner_0` and `inner_1`'s diodes, then straight out through the narrower exit level with `inner_1`'s diode, into the well. |

So nine wires reach the well: RH, RB and RX through the wider exit, C4 through the
narrower one, and RT, C0, C1, C2 and C3 down the back trunk's neck.

Channels sink 1 mm into the plinth and trunks 5.5 mm, so wires can cross and lie
side by side. Rows cross columns, so every wire has to stay insulated except at a
joint.

### The well

- **Battery:** in the south bay, leads at its north end, through the notch in the
  wall into the controller's bay.
- **Controller:** in the north bay, components down, USB-C port out through the back
  wall. The battery's leads run north under the board to its north end. A lip of the
  plinth comes over the north end of the board and clears it by 0.3 mm, so nothing
  there can stand proud of the board's top.
- **Power switch:** in its pocket in the strip on the board's inner side, knob in a
  slot through the inner side wall. The knob's tip is flush with the outside of the
  wall, so you slide it with a fingernail.
- **Reset button:** in the same strip, north of the power switch, on edge, plunger
  out through a round hole in the inner side wall. It sits on the seam, so the plinth
  has half its pocket and the body the other half.

Power runs battery + → slide switch → B+, and battery − → B−. Seen from above in
the well, B+ is the board's north-west corner and B− its north-east. Solder both
from the board's underside, the way the leads come, and keep the top flat to pass
under the lip. Reset is one leg of the button to RST and another to GND: check with
a meter which two legs a press joins, usually the diagonal pair.

## Assembly

Do each half in this order. Nothing can be reached once the plinth is on, so test
at each step.

### 1. Inserts

Press the five heat-set inserts into the body's underside, in the five holes with
round flat pads round them, until flush with the pad. Keep them square: the pads are
level but the surface round them isn't.

### 2. Plinth electronics

1. Solder about 60 mm of wire to the slide switch's middle pin and one outer pin,
   and drop it into its pocket from above with its knob in its slot and its pins
   facing the well. Wire to the pin that makes knob-north "on". Its pins are about
   1.5 mm apart, so tin the wires first and check for a bridge with a meter.
2. Solder about 60 mm of wire to the two legs of the reset button that a press
   joins. Drop it into the plinth's half of its pocket with its plunger in the half
   hole, and its wires through the two ways either side of the stop behind it. On a
   diagonal pair one leg stands above the plinth's top, in the body's half of the
   pocket: bring its wire down into its way, so that it doesn't sit on the seam.
3. Fit the board's wires. With the board out of the well, solder the switch's free
   wire to B+, one reset wire to RST and the other to GND.
4. Check the battery's polarity with a meter: lead colours aren't reliable. Solder
   battery − to B−, and battery + to the slide switch's other wire, with the switch
   off, and insulate the joint. Stick the battery in its bay with foam tape, leads
   through the notch.
5. Feed the board in nose first, components down: tilt its south end up 5 to 8°, no more,
   slip the port into its opening and under the plinth's lip, then lower the south
   end, with the leads under it. Try this dry before soldering anything to the board,
   since it's harder with the wires on.
6. Turn the switch on. Hold the board down and plug in USB-C. Press reset twice,
   holding the button in with a finger, as the other half of its pocket is in the
   body. The board should mount as a drive: flash the firmware now, while everything
   can still be reached. Then unplug it and turn the switch off, and leave it off:
   the rest is soldered with the board dead.

### 3. Sockets, diodes and matrix

Put the body upside down on something soft, so that gravity holds each socket
against its ceiling.

1. Drop a socket down each shaft, its collars in their holes, until it sits flat.
   Check every one against `pocket-closeup.png`.
2. Bend each diode's legs. Put each diode in its pocket with its band to the correct
   side: toward the column wire on every key, which is the inner side on a finger key
   and the near side on a thumb key. Lay the other leg in its slot and solder it to
   its terminal.
3. Run the columns, each from its start key. Don't strip a window in place, down in
   a channel: mark each diode's place on the wire against the body and strip it on the
   bench, or cut the wire at each diode and join the two ends on the leg, as the rows
   do. Solder the band end's leg to it, and leave a tail at the well end.
4. Run the rows, each from the well end to its last key, one length between each
   pair of keys, two wires on each terminal.
5. Check each joint with a meter, using the diode test: touching a row and a column
   with the socket's contacts shorted should show one key's diode, only one way round.

Keep every wire below the underside's surface, in its channel. A wire left standing
proud gets pinched at the seam.

### 4. Join the halves of the case

1. Cut the nine wires to reach their pins with enough slack to open the case. Trim
   the plinth's slack as well.
2. Solder the nine wires to the board's top face. The board is in its bay, so the
   wires reach it from above. There's only 1.5 to 2 mm over the board's south end, and
   1.5 mm at the left half's RH, RB and RX holes, so keep those joints flat, trim the stubs flush, and lay the wires side by side, not
   crossed.
3. Close the body over the plinth. The plinth's steps locate it under the body. Tuck
   the slack into the trunks as it closes, and check that no wire sits on the seam.
   **This step isn't solved yet:** nothing holds the sockets, diodes and wires in the
   body once it turns over, or the parts in the plinth if that turns over instead, and
   a part that drops out gets crushed against its boss.
4. Fit the five screws from below and tighten them gently. The seam should close
   without forcing, and stop and look if it doesn't. The parts are designed 0.1 mm
   apart across the seam, so a hair of a gap away from the screws is expected.

### 5. Switches and caps

Press each switch in from the top, pins straight, holding the body. The boss on the
plinth under each socket takes the push. Fit the caps: R2 top row, R3 home row, R4
bottom row, R3 thumbs.

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
  1.2 mm further out than the mirror's, and the wider exit into the well is about
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
- **Battery:** each half reports its own level, the right's through the left.
- **Reset:** the button is on RST, so it needs nothing from the firmware.

## Running

- **Power:** each half is on its own. There's no cable between them. A half runs
  from its battery through the slide switch to B+, and the board's regulator makes
  the 3.3 V for the chip. The matrix takes its power from the GPIOs, and there's
  nothing else on the board to power: no LEDs, no display.
- **The slide switch** disconnects the battery alone. Off, the half is dead on
  battery, and it can't charge either.
- **USB-C** is for charging and for flashing, not typing. The port sits 1 to 2 mm back
  from the wall's face in a 10.7 × 5.2 mm opening, so a cable with a slim moulding is
  safest: a fat one may not seat. A half with USB-C plugged
  in runs from it, and charges its battery if its slide switch is on, at about
  100 mA, so about two hours from flat. Check the rate on the bought board.
- **Turning on:** switch both halves on. The right half connects to the left, and
  the left to the host it's paired with, or advertises if it has none.
- **Reset button:** one press restarts the half. Two quick presses put it in its UF2
  bootloader, when it mounts as a USB drive for a new firmware image. Press it through
  the round hole in the inner side wall with a fingertip.
- **If a key does nothing:** a single dead key is its switch, its socket or its
  diode. A whole dead row or column is that net's wire or pin.

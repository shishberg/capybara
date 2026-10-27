# Design status: decisions and open questions

The current state of the v4 design. When another doc disagrees with this one, this one is correct, and the other doc needs fixing. Update this file whenever a decision is made or a new question comes up.

## Construction

The first prototype uses **individual 1U key tiles for all 40 keys**, bought as the 50-board AliExpress RGB pack (per-key RGB LED, hotswap socket, diode). Each half is hand-wired to a **[Pro Micro](pro-micro.md)** (RP2040) on its bottom section, and a TRRS cable joins the hands. The chassis is edited in the [browser editor](../editor/README.md).

Paused, kept as reference: the flex finger boards, flat thumb PCBs and LED-free pod built by `make build` into `output/seeded/` (see the [README](../README.md)), and the pod design the Pro Micro replaced, an ESP32-P4 pod joined to each hand by an FFC ribbon, with its custom breakout and pod boards ([key PCB quote options](key-pcb-quote-options.md)).

## Decided

| Decision | Detail |
|---|---|
| Key tiles for all 40 keys | Bought RGB tiles. The custom tile Gerbers remain as a fallback. |
| The bought tile, measured | 17 × 17 mm, 1.6 mm thick, with a round notch of about 1.5 mm radius at each corner. MX switch, Kailh MX hotswap socket underneath. Below the board face: socket 1.9 mm, LED 1.1 mm, diode 0.8 mm, so the tile pocket reaches 8.8 mm below the plate top (5 mm to the board, the board, the socket and 0.3 mm clearance). Positions and sizes, to about ±0.3 mm, are in the editor's `tile` config: in the key's frame, from the stem centre seen from the switch side, y towards the socket edge. |
| Tile pads and holes | Through holes near the side edges: two C, two R, in and out (the in/out side), and V and G nearer the LED. Each hole takes one wire: a 22 AWG wire fits, two don't. On the parts side, in, out, V and G also have a pad on each of the socket and LED edges. A spare C hole and a spare R hole sit under the socket. Joined on the tile: both C holes, the spare C and the diode's cathode; both R holes, the spare R and one socket contact; the other socket contact to the diode's anode; each of in, out, V and G with its hole, both its edge pads and its LED lead. Matrix to LED nets is open, and so is V to G: the tiles have no capacitor. |
| Tile wiring: one wire per hole | A row or column wire arrives at one of a tile's two R (or C) holes and the next leaves from the other. +5 V and GND use the V (or G) hole and the LED-edge pad. LED data arrives at the in hole and leaves from the out hole. The editor routes the wires this way. |
| Tile diode direction: ROW2COL | Measured: R → switch → diode → C, the diode's cathode on C. The [firmware](../firmware/README.md) scans `row2col`. (The custom tile is COL2ROW.) |
| Tile LED pin order | SK6812MINI-E order: DIN top-left, VDD top-right, DOUT bottom-right, GND bottom-left. |
| Per-key RGB is back in | Supersedes the 2026-09-16 LED removal, which applied to the seeded boards. |
| Total draw must fit a laptop USB port | If the design needs more than a laptop's USB port provides, cut features rather than add power. The LEDs' share is held down by a firmware brightness cap (see the [Pro Micro](pro-micro.md#open)'s LED current). |
| A Pro Micro in each hand, joined by TRRS | An RP2040 board in Pro Micro form factor on each hand's bottom section, its USB-C port in the back wall, with a TRRS jack for the serial link between the hands and a reset switch. It replaced the pod: the ESP32-P4, the FFC adapters and ribbons, and the level shifter. Parts, pins, the link and the LEDs: [Pro Micro](pro-micro.md). |
| One hand on USB powers both | The cable carries 3.3 V from the left hand to the right, so only the left hand is plugged in, with no battery or second USB cable. That rules out the nRF52840 boards (nice!nano, SuperMini), whose VCC pin doesn't feed the chip, and is why the board is an RP2040. |
| First prototype: no custom PCBs | A custom PCB order has the longest turnaround and can't be changed once made. The tiles and the controller boards are bought, and the hands are hand-wired. |
| No capacitors on the hands | No bulk capacitor: the 470 µF per hand came from a separate-supply design, and so much on the supply at plug-in breaks the USB spec's 10 µF. No hand-wired ceramic per column either: the tiles run without them. |
| Key layout: Swung in | The layout of the printed frame, and the editor's default (`editor/src/default-config.json`), laid out with the [hand prototype](hand-prototype.md), its two extra thumb keys (x1, x2) included, beside the thumb row toward the thumb's base and 1 mm above the row's face. The hand model puts x2 18 mm past the thumb's reach; see the [hand prototype](hand-prototype.md). It is the only layout kept; the earlier ones were removed on 19 Oct 2026 and are in git history (509dbd1 is the last commit with them). |
| Chassis: Capybara open frame | A rib per finger column and thumb row, the key plates in them, joined by bridges and standing on a rail round the outline, on a flat base plate that carries the Pro Micro, its TRRS jack and its reset switch. The [editor](../editor/README.md) generates it from the key layout; [editor chassis and wiring](editor-chassis.md) describes the construction. The C64-styled case, tried before, is on the `legacy-variants` branch. |
| Tiles hang from their switches, under a sleeve | Under each plate the chassis fills down round the switch body, over the tile's footprint, to 0.4 mm over the tile's top (the sleeve), so the switch is held over its whole 5 mm below the plate rather than only at the seat. The tile hangs from its switch, held up to the sleeve by the hotswap socket's grip on the pins; there are no glue posts. Solder on the tile's top face is trimmed flush; the 0.4 mm takes what is left and the print's tolerance. Whether to glue the tile to the sleeve is decided at build time. [Editor chassis](editor-chassis.md) describes the construction. |
| Capybara walls and end supports | Wishbone walls (forked rib legs under the outer sides' webs) and flow end supports (thumb row ends carried on into column fronts, remaining fronts joined to thumb plates, a floor tie under the rest). Chosen 20 Oct 2026 from the `?walls=` and `?ends=` prototypes; the other walls (flare, arches, truss, bones, pillars) and ends (none, tie) are on the `legacy-variants` branch. How they are built: [editor chassis](editor-chassis.md). |
| Each hand is a 4 × 5 matrix | The finger rows RT, RH and RB plus the thumb row RX, over the five finger columns. Each thumb sits on a finger column (x2 C0, near C1, x1 C2, home C3, far C4) and its column wire chains on from that column's bottom key, so each Pro Micro pin takes one feed. The pins are `pro_micro.pins` in `editor/src/default-config.json`. |
| Wires plug onto the Pro Micro | Each wire off the Pro Micro, the feeds and the jack's and the reset switch's link wires, ends in a Dupont contact on a straight header pin soldered to the Pro Micro, in a 1x9 housing over pins 1 to 9 and a 1x8 over pins 16 to 23, so the bottom section comes off by unplugging the feeds and the Pro Micro lifts out with nothing to desolder. The housing's size is `pro_micro.dupont` in `editor/src/default-config.json`, and the [editor](editor-chassis.md#wiring) checks it against the tiles over the board. |
| Service loops on the feed wires | Each feed has a 30 mm service loop (spare slack wire), enough to lift the bottom section and reach the plugs. |

## Open

| Question | Notes |
|---|---|
| Pro Micro build | The clone's pinout, the LEDs at 3.3 V and the LED current: see [Pro Micro](pro-micro.md#open). Its parts' sizes are provisional until measured. |
| Modtap prediction model | Collecting keypress data for a modtap prediction model was a reason to keep the ESP32-P4. For the model to move between chips, its features should be key timestamps, not anything specific to one chip. |
| Capybara corners | A final pass, once the chassis settles: round or chamfer the frame's hard corners by rule. Before 5d1f602 and 8994376 the rail rounded where it turned in at the drops. The user liked that slight rounding but not its direction (concave). They want convex rounds or chamfers: the rail's corners at the drops and its steps at the back, the limb feet, the bridges and the plate and web edges. Keep the crisp, rib-like look, with no blobby fairing. |

## Bring-up

Checks on the bench with the first wired hand, not design questions.

| Check | Notes |
|---|---|
| Tile LED part | Unidentified, but wired in SK6812MINI-E pin order. Its data threshold and current per LED set the real brightness cap. Test a short column at the intended wire length. |
| No per-column capacitors | Decided: none on the hands (above), and the tiles have none (V to G measured open). Check the LEDs at the far end of each chain at the firmware's brightness cap. |
| Dupont plugs' height | Modelled as a 2.5 mm header spacer, a 14 mm housing and 3 mm for the wire to turn (`pro_micro.dupont`). Pins 16 (RX) and 18 (C4) have about 1.4 mm to spare under the index home key. Measure a plugged lead and update the config. |
| Service loop length | 30 mm is a guess at what lifting the bottom section far enough to reach the plugs takes. |

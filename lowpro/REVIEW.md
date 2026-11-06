# Lowpro build review, 6 November 2026

The question was whether a person could build lowpro from [BUILD.md](BUILD.md) and the generated parts, and whether it would then work. An independent reviewer answered it from only the STLs, the assemblies, the renders and the guide. It saw none of the code. Each finding was then re-measured on the meshes before anything changed.

**Result:** nothing stops the build or the keyboard working. The reviewer traced every net on both halves through the real channels to the well, and every part drops in along the guide's path with no intersection. The matrix, diode direction, pin table, route table and firmware section all agree. One thin wall was a real defect and is fixed. Five items need your decision, and they're listed first.

Nothing here has been printed, so all of this is from the model.

## For you to decide

### 1. Should the switch and reset pockets get 0.2 mm of clearance?

Both pockets have 0.1 mm a side (`power_switch_clearance_mm`, `reset_button_clearance_mm`), which is under what FDM holds, so a part may need scraping in, or closing the case may clamp the reset button. The code calls the switch's pocket a close fit on purpose, and a looser pocket lets the switch rattle more.

The one-key test print doesn't cover these pockets.

Recommendation: 0.2 mm for both. A trial with both set to 0.2 passed every check on both halves. To apply it, change the two parameters in `params.py`.

### 2. Should the well's wall on the keys' side be thicker than 1 mm?

It's 1 mm thick (x −53.45 to −52.45 on the right half), up to 14 mm tall, and has three slots through it. It's also where the support in the well has to be cleared, so it's the likeliest part to snap. BUILD.md already warns about it.

A 1.5 mm wall has to take 0.5 mm from the bay or the outline. I haven't measured that cost.

Recommendation: leave it for the first print, and thicken it if clearing the support breaks it.

### 3. Do the thin slivers in the body need fixing?

After the collar fix below, an exact ray-cast still finds about 160 mm² of parallel-sided wall under 0.8 mm on each half. Two kinds make up the largest patches:

| Kind | Thickness | Where | Fix |
|---|---|---|---|
| The MX footprint's own rib, between the centre post's hole and the pin collar's | 0.58 mm | Every key | None: it comes from the footprint's spacing |
| The tip of a wedge where two cuts meet at a shallow angle | Tapers to nothing | For example (−24.7, 24.8, 15.8), north of `index_1`, and the corners either side of the collar fix | Removing them needs a pass that deletes small features |

None of them carries load, and each tip is attached to solid material along its base. If a slicer drops one, a channel opens a little further into a hole or pocket, which is harmless. The risk is a loose wisp of plastic left in a shaft.

Recommendation: accept them and clear any loose wisps with the support. I didn't classify every small patch, so a few may be neither kind.

### 4. Is 024 really the battery divider's pin?

BUILD.md says the right half skips 024 "because the board's battery divider is on it". I couldn't confirm that, and it looks unlikely. No published pinout for the Tenstar board turned up. [RIOT's page for this board family](https://doc.riot-os.org/boards/pro-micro-nrf52840) lists P0.24 as plain D5, and the [nrfmicro wiki](https://github.com/joric/nrfmicro/wiki/Pinout) says a battery sense pin has to be analog. P0.24 isn't one of the nRF52840's analog inputs, which are P0.02 to P0.05 and P0.28 to P0.31 (from memory of the datasheet).

This matters more for the left half, whose C3 (002), RT (029) and C4 (031) are all analog-capable. If a divider sits on one of them, that net is loaded.

To settle it when the board arrives, with no battery attached, measure the resistance from B+ to each pin in the pin table. A divider shows up as a fixed resistance. Then correct the sentence, and move a net if one is affected.

### 5. Is a flush reset plunger pressable with a fingertip?

The plunger's tip is flush with the wall's face at the bottom of a chamfered hole about 5 mm across, and the guide says to press it with a fingertip. The reviewer doubts that. The shape can't answer it, and with a firm button as the parts list asks for, a fingertip may not reach. A pen or fingernail does.

Recommendation: find out on the first print, then either keep the sentence or say "a pen". The other option is to let the plunger stand a little proud, which risks a knock resetting the board.

## Changed in the chassis

Part of F5 was a real defect with one fix. At `middle_0` and `ring_0`, on both halves, a wall 0.12 mm thick stood between the north collar's hole and the row channel. A row channel's south edge stopped 0.125 mm past the collar's hole, and at those two keys the next key stands higher, so the channel's roof climbs into the collar's layer. It's the fault `8b5bb2f` fixed for the shaft.

`shaft_edge_y()` now overlaps the collar's hole by 0.1 mm, so the row channels and the back trunk sit 0.225 mm further south on every key. The hole opens into the channel. The wall check now covers the collar too, and a new test proves it fails on the old edge: it reported 0.125 mm at `ring_0` before the fix.

After the fix, all 8 tests and every build check pass on both halves, and the plate is still 1.50 mm at every clip edge. The blind review ran before this change, so no independent reviewer has seen it.

## Changed in BUILD.md

| Finding | Change |
|---|---|
| F10 | The first power-up moved from the end of "Electronics" to a new step in "Close and test". As written it had you holding a loose board and a loose reset button, and pressing keys on a face pointing at the bench. With the plinth on, the board, button and sockets are all held. Faults now cost undoing six screws. |
| Mine | "Sockets and switches" said to press switches in "from the top", with a finger "from below", on a body lying upside down. It now says to lift the body, still upside down, and press up into the top face. The reviewer didn't raise this one. |
| I1 | "Channels sink 1 mm" read as the whole depth. It now gives the body's depth too: channels at least 2.2 mm wide and about 4 to 5 mm deep, trunks 3.5 mm wide and about 5 mm deep, plus their sink into the plinth. |
| I3 | The battery goes on the ceiling so that the plinth comes away free, as the guide already said, but the ceiling isn't level: it rises from 11.7 mm to over 13 mm toward the south end. The guide now says to tape the battery's north end, and that 1 mm of foam leaves it 0.5 mm off the floor. |
| F3 | The guide now says the strip stands 0.7 mm off the board, so 1 mm of foam squeezes. |
| I6 | "Nine key wires" now says four rows and five columns. |

## Every finding

| ID | Finding | Verdict after re-measuring | Outcome |
|---|---|---|---|
| F1 | Switch pocket has 0.1 mm a side, knob sits in a 1.2 mm recess | Clearance true. No recess: the wall's face is at x −78.25, the same as the knob's tip. The reviewer's −79.54 is the outline's extreme near y −65. | Decision 1 |
| F2 | Reset button has 0.00 mm clearance, in a recess | Slack is 0.1 mm top and bottom (z 2.63 to 9.33 for a button at 2.73 to 9.23). The 0.00 is its face bearing on the wall's skin, as designed. No recess. | Decisions 1 and 5 |
| F3 | Strip gap 0.82 mm for 1 mm foam | Gap is 0.70 mm across the whole strip. Works as intended. | Guide |
| F4 | 1 mm wall, 14 mm tall | True | Decision 2 |
| F5 | Fins of 0.4 to 0.8 mm | True, but several causes. The worst was 0.12 mm, thinner than reported. | Chassis fix and decision 3 |
| F6 | Plate 1.3 mm at the clips | False: a voxel artefact. An exact ray-cast gives 1.50 mm at every clip edge on all 40 keys. | None |
| F7 | Thumb caps 0.85 mm apart | True and above the 0.5 mm the design holds to. "Measure first" covers real caps. | None |
| F8 | Thumb column wires cross 4 to 5 mm of pocket and need laying before the socket | What crosses is the diode's leg, and the sockets go in first, so the suggested order can't happen. | None |
| F9 | USB hole bigger than stated and runs into the back trunk's neck | False. The wall's face is about y 29.4, not 28.2. The port ends at 28.14, 1.25 mm back, as the guide says. The hole's 13 × 7 mm at the port and only larger where it flares. The neck stays separate, and the plug stops north of it. | None |
| F10 | First power-up is three-handed | True, and worse than reported | Guide |
| I1 | Channel depths mislead | True | Guide |
| I2 | Knob and plunger aren't flush | False: see F1 | None |
| I3 | Battery on the ceiling in the guide, on the floor in the model | True, and the guide is the right one | Guide |
| I4 | Add a 1.4 mm wire limit | The guide already gives the limit as 1.6 mm with a struggle, and recommends 1.0 mm. | None |
| I5 | Say where wires double up | The guide already says which nets take each way into the well. | None |
| I6 | "Nine wires" could mislead | True, minor | Guide |
| N1 | Pinky sockets graze on insertion | Slivers of 0.04 mm³, below print tolerance | None |
| N2 | Guide doesn't name the insert's length | False: the parts table says M2 × 3 | None |
| N3 | Pinky caps reach the body's edge | Harmless | None |
| N4 | The render's colours match the guide | Not a defect | None |

## Not checked

The shape can't show these, so they wait for real parts. "Measure first" in the guide covers most of them.

- The board's pad positions, including B+, B−, RST and GND. The board is a plain box in the model.
- The battery's lead length.
- Real socket terminals, switch pins, slide switch and button legs, and keycap profiles.
- Whether a wire stays where it's put. The review checked that wires fit, one at a time, and not how a bundle of stiff wire behaves.
- The firmware, which doesn't exist yet.

## Also noticed

The README gives the plan as 11,983 mm², and the build now reports 12,023 mm² for the right half and 12,032 mm² for the left. It's outside this review, so I left it.

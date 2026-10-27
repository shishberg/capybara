# Pro Micro

Each hand's controller: an RP2040 board in Pro Micro form factor, the two hands joined by a TRRS cable that carries power as well as the link. The editor builds it into every hand; its parts are `pro_micro`, `trrs` and `reset` in `editor/src/default-config.json`.

## Parts per hand

- **Controller:** an RP2040 Pro Micro with the SparkFun Pro Micro RP2040's pinout (QMK's `rp2040_ce`), as the generic "ProMicro RP2040" boards have; 2 MB of flash or more ([firmware](../firmware/README.md#flash-layout)). Components up, USB-C out of the hand's back end, in a cradle on the bottom section. The board's port end reaches into the back wall, centred on the index column's rear rib, so the wall grips the USB-C receptacle and the plug's overmold seats in a chamfered opening rather than reaching into the hand. The modelled board (`pro_micro.board_mm`) is a 33.3 × 18 mm envelope; the board, port and parts sizes are provisional until measured.
- **Jack:** PJ-320A, lugs up, in its own cradle on a pedestal between the board and the inner side, barrel out of the inner side under the wishbone nearest the back, square to the wall. That wishbone forks over the plug, and the opening between its legs is filled, flush with them, with a boss behind it round the barrel and the barrel's and the plug's hole cut through, so the rail is whole, the wall grips the barrel, and the plug comes in through a chamfered opening. The pedestal stands the plug clear over the rail. PJ-320A is made by several vendors with different bodies (XKB's is 12.2 mm plus a 2 mm nose, 6.2 × 5 mm); measure the one bought and its lugs (`trrs.lugs_mm`).
- **Reset button:** a low 6.5 × 6.5 mm SMD tactile switch (metal body 2 mm thick, plunger 1 mm proud of it) in the back wall, on the outer side of the USB-C port, pressed with a fingertip; one press resets the board, two quick ones enter its UF2 bootloader. It sits in a pocket in the inside of the wall behind a 0.5 mm skin, its plunger out through a hole in the skin to stand 0.5 mm proud of the outer face, with a stop on the bottom section behind it that takes the press. Fit it into its pocket before closing the hand. Pick a firm switch, so that a knock doesn't reset the board. The fifth tab between two legs stays unwired. Switches vary: measure the body, the plunger and the legs (`reset` in `default-config.json`), and check with a meter that a press joins the two diagonal legs the wires go to (`reset.wires`): the other pairs are joined straight across on some makes and along a side on others.
- **Wiring:** each net's feed plugs onto a board pin, and so do the short link wires to the jack (four) and the reset button (two) ([design status](design-status.md) says how). Pin 21 takes two wires, the LEDs' feed and the jack's VCC, crimped into one Dupont contact. The pin map is `pro_micro.pins`, the jack's `trrs.wires` and the button's `reset.wires`, all in `default-config.json`; the editor's wiring panel lists each pin with its GPIO.

## Pins

The link is on pin 1 (GP0) and pin 2 (GP1), and LED data on pin 5 (GP2). Pins 10 to 15 sit under the index home key, with no room for a feed's Dupont plug, so no feed uses them. The matrix, the LEDs and the link take 12 of the edge's 18 GPIOs. The GPIO names are the SparkFun board's; the clones' silkscreen varies.

## The link

- **Firmware:** RMK's serial split over a full-duplex UART on PIO, in [`firmware/`](../firmware/README.md). The left hand is the central, on USB to the host.
- **Cable:** a straight TRRS cable carries the two data lines on the sleeve and ring 2, GND on ring 1 and 3.3 V on the tip. Both hands are wired the same, and each transmits on a different data line.
- **Power:** the tip joins the two hands' pin 21 (VCC), the output of the board's 3.3 V regulator, which also supplies the RP2040, as on a Corne. The left hand, on USB, powers the right: its regulator feeds both boards and both hands' LEDs. Only the left hand goes on USB.
- **Never plug or unplug the cable while the keyboard is on USB:** the tip carries 3.3 V and wipes across the other contacts as the plug goes in.

## LEDs

The LEDs run from VCC, 3.3 V; the wiring's `+5V` net is pin 21. Nothing switches it, so the dark LEDs draw about 1 mA each while the keyboard is on USB. The firmware doesn't drive the LEDs yet.

## Open

| Question | Notes |
| --- | --- |
| The clone's pinout | Taken as the SparkFun board's, as QMK's `rp2040_ce` converter assumes. Check the bought board's pins before wiring. |
| LEDs at 3.3 V | The SK6812MINI-E's datasheet asks for 3.7 to 5.5 V. Check the tiles' actual LED, or test them at 3.3 V. |
| LED current | Full white is about 36 mA per LED, 1.4 A for both hands' 40, all through the left board's one 3.3 V regulator and the cable's tip. Read the regulator on the bought board for its rating, and cap brightness in firmware to fit it and the USB port. |

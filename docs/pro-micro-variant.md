# Pro Micro variant

A PROTOTYPE alternative to the pod: an nRF52840 board in Pro Micro form factor in each hand, the two hands joined by a TRRS cable. It drops the pod, the ESP32-P4, the FFC adapters, the ribbons and the level shifter. In the editor, `?controller=pro_micro` or the controller bar (`←` and `→`) shows it; `controller.style` in `editor/src/default-config.json` stays `ffc` until this is decided.

## Parts per hand

- **Controller:** nice!nano v2, or a SuperMini nRF52840 (same edge pinout, runs ZMK's `nice_nano_v2` board). Components up, USB-C out of the hand's back end, in a cradle on the bottom section. The board's port end reaches into the back wall, centred on the index column's rear rib, so the wall grips the USB-C receptacle and the plug's overmold seats in a chamfered opening rather than reaching into the hand. The modelled board (`pro_micro.board_mm`) is a 33.3 × 18 mm envelope that covers both; neither maker publishes the nice!nano's outline or USB-C overhang, so the board, port and parts sizes are provisional until measured.
- **Jack:** PJ-320A, lugs up, in its own cradle on a pedestal between the board and the inner side, barrel out of the inner side under the wishbone nearest the back, square to the wall. That wishbone forks over the plug, and the opening between its legs is filled, flush with them, with a boss behind it round the barrel and the barrel's and the plug's hole cut through, so the rail is whole, the wall grips the barrel, and the plug comes in through a chamfered opening. The pedestal stands the plug clear over the rail. PJ-320A is made by several vendors with different bodies (XKB's is 12.2 mm plus a 2 mm nose, 6.2 × 5 mm); measure the one bought and its lugs (`trrs.lugs_mm`).
- **Reset button:** a 6 × 6 mm SMD tactile switch, plunger down on a pedestal on the bottom section beside the board's RST and GND pins (22 and 23), pressed with a pin or paperclip through a hole in the bottom section; one press resets the board, two quick ones enter its UF2 bootloader. The hand stands on that face and the plunger sits back from it behind a hole narrower than a fingertip, so typing and carrying can't press it, and the wires to the pins are short. A press pushes the switch up, off its pedestal, so glue it down. Switches sold as 6 × 6 × 5 mm vary: measure the body, the plunger and the legs (`reset` in `default-config.json`), and check with a meter that a press joins the two diagonal legs the wires go to (`reset.wires`): the other pairs are joined straight across on some makes and along a side on others.
- **Wiring:** each net's feeds land on a board pin, and short link wires run from the board to the jack (three) and the reset button (two). The pin map is `pro_micro.pins`, the jack's `trrs.wires` and the button's `reset.wires`, all in `default-config.json`; the editor's wiring panel lists each pin with its GPIO.

## Pins

The link is a UART on the board's `pro_micro_serial` pins, pin 1 (P0.06) and pin 2 (P0.08). LED data is on pin 5 (P0.17). All three are high-frequency pins; the rest of the edge pins are low-frequency (10 kHz or less), fine for the matrix but not for LED data or the UART. P0.09 and P0.10 (pins 13 and 14) are NFC pins and are left free. The matrix and LEDs take 12 of the board's 21 GPIOs.

## The link

- **Firmware:** RMK's serial split over a full-duplex UART, in [`firmware/`](../firmware/README.md). The left hand is the central, on USB to the host.
- **Cable:** a straight TRRS cable carries TX, RX and GND (sleeve, ring 2, ring 1; the tip is spare). Both hands are wired the same, so the left hand transmits on P0.06 and the right on P0.08.
- **No power on the cable.** The board's VCC pin is the output of its 3.3 V regulator, which doesn't feed the nRF52840, and nice!nano's makers say the boards aren't designed to power each other. Each hand needs its own power.
- **Never plug or unplug the cable while either hand is powered,** by USB or battery (ZMK's warning, which holds even without power on the cable).

## LEDs

There is no 5 V pin: RAW is the battery. The LEDs run from VCC, 3.3 V, which P0.13 switches (high is on), so the dark LEDs' 1 mA each needn't drain the battery. The firmware doesn't drive the LEDs yet and holds VCC off. The wiring's `+5V` net is that VCC pin.

## Open

| Question | Notes |
| --- | --- |
| Power for each hand | A small LiPo per hand (what the nice!nano is built for), or USB to each. A battery needs a place in the chassis. |
| LEDs at 3.3 V | The SK6812MINI-E's datasheet asks for 3.7 to 5.5 V. Check the tiles' actual LED, or test them at 3.3 V. |
| LED current | Full white is about 36 mA per LED, 720 mA for a hand's 20: over the nice!nano's 500 mA USB input and near its 1 A regulator, and well over a SuperMini's (500 or 800 mA, by batch). Cap brightness in firmware. |
| nice!nano or SuperMini | Same edge pins. The SuperMini's regulator and its three middle pads differ by batch, and some batches have faulty 32 kHz crystals. |

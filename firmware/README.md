# Firmware

PROTOTYPE [RMK](https://github.com/HaoboGu/rmk) firmware for the [Pro Micro variant](../docs/pro-micro-variant.md): a nice!nano v2 (nRF52840) in each hand, the hands joined by a TRRS serial link. The left hand is the central, on USB to the host. The right hand is the peripheral: it needs power, from USB or a battery, but doesn't talk to the host. It builds, but hasn't run on a board yet.

RMK's `keyboard.toml` can't describe a serial split on an nRF52840 (its code generator only does serial on the RP2040), so this uses RMK's Rust API. RMK's serial split runs over anything with async `Read` and `Write`, which embassy-nrf's `BufferedUarte` has. There's no Bluetooth.

## Build

Needs `rustup` (the toolchain and target come from `rust-toolchain.toml`) and `flip-link` (`cargo install flip-link`).

```sh
make firmware
```

This writes `output/firmware/capybara-central.uf2` (left hand) and `capybara-peripheral.uf2` (right hand).

## Flash

1. Double-press the hand's reset button. The board mounts as a `NICENANO` drive.
2. Copy the hand's UF2 onto the drive. The board restarts into it.

Unplug the TRRS cable first; see [the link](../docs/pro-micro-variant.md#the-link).

## Flash layout

The nice!nano's Adafruit bootloader can only start an app while the Nordic SoftDevice is intact, and a UF2 can write anywhere, the SoftDevice and the bootloader included. Rosebear's RMK firmware was linked at address 0, as RMK's nRF52840 template was. Flashing it overwrote the SoftDevice, so the boards would run nothing else until it was restored over serial DFU or SWD (Rosebear's `rosebear-zmk/docs/recovery.md`). RMK's examples still link at 0x1000, inside the SoftDevice.

| Region | Address | |
|---|---|---|
| MBR | 0x00000–0x00FFF | |
| SoftDevice S140 | 0x01000–0x25FFF | never written |
| This firmware | 0x26000–0xEBFFF | `memory.x` |
| RMK's storage (keymap edits, settings) | 0xEC000–0xF3FFF | `STORAGE` in `src/central.rs` |
| Bootloader and its settings | 0xF4000– | never written |

Three things keep it there:

- `memory.x` links the firmware from 0x26000 to 0xEC000.
- `STORAGE` is set explicitly. RMK's default puts storage in the last sectors of flash, which are the bootloader's own pages, unless it's built with Bluetooth. A compile-time assert keeps it under 0xF4000.
- `uf2.py` writes the UF2 and refuses any byte outside 0x26000–0xEC000, so `make firmware` fails before an image that would overwrite the SoftDevice or the bootloader exists.

Because the SoftDevice is left alone, this firmware and ZMK can replace each other with a plain UF2 copy.

## What it does

- **Matrix:** 4 × 5 per hand, scanned `row2col`, on the pins in `pro_micro.pins` (`src/hand.rs`).
- **Keymap:** Rosebear's four layers and tap-hold timing, in `src/keymap.rs`. The extra thumb keys x1 and x2 do nothing yet.
- **Link:** UARTE0 at 115200 baud, full duplex.
- **LEDs:** not driven. RMK has no LED driver, so the LEDs' supply (P0.13) is held off.
- **Bootloader:** the reset button only. RMK's `Bootloader` key would just reboot the board here, because its Adafruit bootloader support comes only with Bluetooth.

## Open

| Question | Notes |
|---|---|
| First run on a board | The nRF52840 serial split has no example or user upstream. Check that keys reach the host from both hands. |
| LEDs | An SK6812 driver on P0.17 using the nRF52840's PWM, with a brightness cap (see the variant's LED current). |
| x1 and x2 | What the extra thumb keys should do. |

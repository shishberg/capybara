# Firmware

PROTOTYPE [RMK](https://github.com/HaoboGu/rmk) firmware for the [Pro Micro](../docs/pro-micro.md): an RP2040 board in each hand, the hands joined by a TRRS serial link. The left hand is the central, on USB to the host. The right hand is the peripheral, powered over the link; it doesn't talk to the host. It builds, but hasn't run on a board yet.

It uses RMK's Rust API (`src/`) rather than `keyboard.toml`. There's no Bluetooth.

## Build

Needs `rustup` (the toolchain and target come from `rust-toolchain.toml`) and `flip-link` (`cargo install flip-link`).

```sh
make firmware
```

This writes `output/firmware/capybara-central.uf2` (left hand) and `capybara-peripheral.uf2` (right hand).

## Flash

Flash each hand on its own USB cable, with the TRRS cable out.

1. Double-press the hand's reset button. On a board that has never run this firmware, hold its BOOT button while plugging it in instead. The board mounts as an `RPI-RP2` drive.
2. Copy the hand's UF2 onto the drive. The board restarts into it.

The RP2040's UF2 bootloader is in its ROM, so no image can overwrite it.

## Flash layout

| Region | Address | |
|---|---|---|
| boot2, the flash's second-stage loader | 0x10000000–0x100000FF | `memory.x` |
| This firmware | 0x10000100–0x101F7FFF | `memory.x` |
| RMK's storage (keymap edits, settings) | 0x101F8000–0x101FFFFF | `STORAGE` in `src/central.rs` |

The firmware is built for 2 MB of flash (`FLASH_SIZE` in `src/central.rs`), the least these boards come with. RMK's default puts its storage in the last 8 sectors of that, and `memory.x` keeps the firmware out of them. A board with 4 or 16 MB runs the same image and leaves the rest unused. `uf2.py` refuses any byte outside the flash.

## What it does

- **Matrix:** 4 × 5 per hand, scanned `row2col`, on the pins in `pro_micro.pins` (`src/hand.rs`).
- **Keymap:** Rosebear's four layers and tap-hold timing, in `src/keymap.rs`. The extra thumb keys x1 and x2 do nothing yet.
- **Link:** a full-duplex UART on PIO0, 115200 baud, on GP0 and GP1. The RP2040's own UARTs can only transmit on GP0 and receive on GP1, and the hands, wired the same, need to take those pins opposite ways round (`src/hand.rs`).
- **LEDs:** not driven. RMK has no LED driver.
- **Bootloader:** a second press of the reset button within half a second of the first restarts into the UF2 bootloader (`double_reset` in `src/hand.rs`). RMK's `Bootloader` key would too, but the keymap has none.

## Open

| Question | Notes |
|---|---|
| First run on a board | Check that keys reach the host from both hands. |
| LEDs | An SK6812 driver on GP2 using PIO, with a brightness cap (see the [LED current](../docs/pro-micro.md#open)). |
| x1 and x2 | What the extra thumb keys should do. |

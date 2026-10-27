//! What both hands share. The hands are wired the same, so the pins are `pro_micro.pins` in
//! `editor/src/default-config.json` through `pro_micro.pinout`, and the link is `trrs.wires`.

use core::mem::MaybeUninit;
use core::ptr::{addr_of_mut, read_volatile, write_volatile};

use embassy_time::{Duration, Timer};

/// Each hand is a 4 x 5 matrix: rows RT, RH, RB and RX (the thumbs), columns C0 (pinky) to C4
/// (inner).
pub const ROW: usize = 4;
pub const COL: usize = 5;

/// The tiles are wired R -> switch -> diode -> C, so the rows are driven and the columns read
/// (`row2col`).
pub const COL2ROW: bool = false;

/// The matrix's pins: rows RT GP4 (pin 7), RH GP6 (9), RB GP5 (8), RX GP22 (16);
/// columns C0 GP29 (20), C1 GP28 (19), C2 GP26 (17), C3 GP3 (6), C4 GP27 (18).
macro_rules! matrix_pins {
    ($p:ident) => {{
        use embassy_rp::gpio::{Input, Level, Output, Pull};
        let rows = [
            Output::new($p.PIN_4, Level::Low),
            Output::new($p.PIN_6, Level::Low),
            Output::new($p.PIN_5, Level::Low),
            Output::new($p.PIN_22, Level::Low),
        ];
        let cols = [
            Input::new($p.PIN_29, Pull::Down),
            Input::new($p.PIN_28, Pull::Down),
            Input::new($p.PIN_26, Pull::Down),
            Input::new($p.PIN_3, Pull::Down),
            Input::new($p.PIN_27, Pull::Down),
        ];
        (rows, cols)
    }};
}

/// The link to the other hand, a full-duplex serial port on PIO0: pin 1 (GP0) on the jack's
/// sleeve and pin 2 (GP1) on its ring 2. A straight cable joins sleeve to sleeve, so the hands
/// take opposite pins to transmit on. The RP2040's own UARTs can't do that with both hands
/// wired the same (GP0 can only transmit and GP1 only receive), so the link runs on PIO, where
/// either pin can do either. RMK 0.9.0's `new_full_duplex` receives on the pin it's given as
/// `pin_tx` and transmits on `pin_rx`; both hands go through it, so they still take opposite pins.
macro_rules! link {
    ($p:ident, $irqs:ident, tx: $tx:ident, rx: $rx:ident) => {{
        use rmk::split::SPLIT_MESSAGE_MAX_SIZE;
        use rmk::split::rp::uart::BufferedUart;
        use static_cell::StaticCell;
        static TX_BUF: StaticCell<[u8; SPLIT_MESSAGE_MAX_SIZE]> = StaticCell::new();
        static RX_BUF: StaticCell<[u8; SPLIT_MESSAGE_MAX_SIZE]> = StaticCell::new();
        BufferedUart::new_full_duplex(
            $p.PIO0,
            $p.$tx,
            $p.$rx,
            &mut TX_BUF.init([0; SPLIT_MESSAGE_MAX_SIZE])[..],
            &mut RX_BUF.init([0; SPLIT_MESSAGE_MAX_SIZE])[..],
            $irqs,
        )
    }};
}

/// Set in RAM while a reset may still be the first of two; RAM keeps it through a reset.
#[unsafe(link_section = ".uninit.DOUBLE_RESET")]
static mut DOUBLE_RESET: MaybeUninit<u32> = MaybeUninit::uninit();
const DOUBLE_RESET_MAGIC: u32 = 0xB007_5E1E;

/// Two presses of the reset button within half a second start the RP2040's UF2 bootloader. Call
/// first thing: if this start is the second press it doesn't return. Otherwise run the future it
/// returns alongside the keyboard; it marks the window and closes it when the half second is up.
pub fn double_reset() -> impl Future<Output = ()> {
    let flag = addr_of_mut!(DOUBLE_RESET).cast::<u32>();
    if unsafe { read_volatile(flag) } == DOUBLE_RESET_MAGIC {
        unsafe { write_volatile(flag, 0) };
        embassy_rp::rom_data::reset_to_usb_boot(0, 0);
    }
    unsafe { write_volatile(flag, DOUBLE_RESET_MAGIC) };
    async move {
        Timer::after(Duration::from_millis(500)).await;
        unsafe { write_volatile(flag, 0) };
    }
}

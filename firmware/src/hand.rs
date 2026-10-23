//! What both hands share. The hands are wired the same, so the pins are `pro_micro.pins` in
//! `editor/src/default-config.json` through `pro_micro.pinout`, and the link is `trrs.wires`.

/// Each hand is a 4 x 5 matrix: rows RT, RH, RB and RX (the thumbs), columns C0 (pinky) to C4
/// (inner).
pub const ROW: usize = 4;
pub const COL: usize = 5;

/// The tiles are wired R -> switch -> diode -> C, so the rows are driven and the columns read
/// (`row2col`).
pub const COL2ROW: bool = false;

/// The matrix's pins: rows RT P0.22 (pin 7), RH P1.00 (9), RB P1.06 (12), RX P1.11 (15);
/// columns C0 P0.31 (20), C1 P0.29 (19), C2 P1.15 (17), C3 P0.20 (6), C4 P1.04 (11).
macro_rules! matrix_pins {
    ($p:ident) => {{
        use embassy_nrf::gpio::{Input, Level, Output, OutputDrive, Pull};
        let rows = [
            Output::new($p.P0_22, Level::Low, OutputDrive::Standard),
            Output::new($p.P1_00, Level::Low, OutputDrive::Standard),
            Output::new($p.P1_06, Level::Low, OutputDrive::Standard),
            Output::new($p.P1_11, Level::Low, OutputDrive::Standard),
        ];
        let cols = [
            Input::new($p.P0_31, Pull::Down),
            Input::new($p.P0_29, Pull::Down),
            Input::new($p.P1_15, Pull::Down),
            Input::new($p.P0_20, Pull::Down),
            Input::new($p.P1_04, Pull::Down),
        ];
        (rows, cols)
    }};
}

/// The link to the other hand, on UARTE0: pin 1 (P0.06) on the jack's sleeve and pin 2 (P0.08)
/// on its ring 2. A straight cable joins sleeve to sleeve, so one hand transmits on P0.06 and
/// the other on P0.08.
macro_rules! link {
    ($p:ident, $irqs:ident, rx: $rx:ident, tx: $tx:ident) => {{
        use embassy_nrf::buffered_uarte::BufferedUarte;
        use rmk::split::SPLIT_MESSAGE_MAX_SIZE;
        use static_cell::StaticCell;
        static TX_BUF: StaticCell<[u8; SPLIT_MESSAGE_MAX_SIZE]> = StaticCell::new();
        static RX_BUF: StaticCell<[u8; SPLIT_MESSAGE_MAX_SIZE]> = StaticCell::new();
        BufferedUarte::new(
            $p.UARTE0,
            $p.TIMER0,
            $p.PPI_CH0,
            $p.PPI_CH1,
            $p.PPI_GROUP0,
            $p.$rx,
            $p.$tx,
            $irqs,
            embassy_nrf::uarte::Config::default(),
            &mut RX_BUF.init([0; SPLIT_MESSAGE_MAX_SIZE])[..],
            &mut TX_BUF.init([0; SPLIT_MESSAGE_MAX_SIZE])[..],
        )
    }};
}

/// Starts the crystal oscillator, which USB and the link's baud rate want.
pub fn start_hfxo() {
    embassy_nrf::pac::CLOCK.tasks_hfclkstart().write_value(1);
    while embassy_nrf::pac::CLOCK.events_hfclkstarted().read() != 1 {}
}

/// The LEDs run from the board's VCC pin, which P0.13 switches (active high, as in ZMK's
/// nice!nano v2 board). Nothing drives the LEDs yet, so their supply stays off: the pin this
/// returns holds it off for as long as it lives.
macro_rules! led_power_off {
    ($p:ident) => {
        embassy_nrf::gpio::Output::new(
            $p.P0_13,
            embassy_nrf::gpio::Level::Low,
            embassy_nrf::gpio::OutputDrive::Standard,
        )
    };
}

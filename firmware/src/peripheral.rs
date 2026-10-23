//! The right hand: scans its matrix and sends it to the left hand over the link. It needs
//! power (USB or a battery) but doesn't talk to the host.

#![no_main]
#![no_std]

#[macro_use]
mod hand;

use defmt::info;
use defmt_rtt as _;
use embassy_executor::Spawner;
use embassy_nrf::{bind_interrupts, buffered_uarte, peripherals};
use panic_probe as _;
use rmk::debounce::default_debouncer::DefaultDebouncer;
use rmk::futures::future::join;
use rmk::matrix::Matrix;
use rmk::run_all;
use rmk::split::peripheral::run_rmk_split_peripheral;

bind_interrupts!(struct Irqs {
    UARTE0 => buffered_uarte::InterruptHandler<peripherals::UARTE0>;
});

#[embassy_executor::main]
async fn main(_spawner: Spawner) {
    info!("Capybara peripheral");
    let p = embassy_nrf::init(Default::default());
    hand::start_hfxo();
    let _led_power = led_power_off!(p);

    let (rows, cols) = matrix_pins!(p);
    // The right hand transmits on P0.08 and listens on P0.06.
    let link = link!(p, Irqs, rx: P0_06, tx: P0_08);

    let mut matrix =
        Matrix::<_, _, _, { hand::ROW }, { hand::COL }, { hand::COL2ROW }>::new(rows, cols, DefaultDebouncer::new());
    join(run_all!(matrix), run_rmk_split_peripheral(link)).await;
}

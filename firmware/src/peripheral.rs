//! The right hand: scans its matrix and sends it to the left hand over the link, which also
//! powers it. It doesn't talk to the host.

#![no_main]
#![no_std]

#[macro_use]
mod hand;

use defmt::info;
use defmt_rtt as _;
use embassy_executor::Spawner;
use embassy_rp::bind_interrupts;
use embassy_rp::peripherals::PIO0;
use panic_probe as _;
use rmk::debounce::default_debouncer::DefaultDebouncer;
use rmk::futures::future::join3;
use rmk::matrix::Matrix;
use rmk::run_all;
use rmk::split::peripheral::run_rmk_split_peripheral;

bind_interrupts!(struct Irqs {
    PIO0_IRQ_0 => rmk::split::rp::uart::UartInterruptHandler<PIO0>;
});

#[embassy_executor::main]
async fn main(_spawner: Spawner) {
    info!("Capybara peripheral");
    let double_reset = hand::double_reset();
    let p = embassy_rp::init(Default::default());

    let (rows, cols) = matrix_pins!(p);
    // The left hand takes the link's pins the other way round.
    let link = link!(p, Irqs, tx: PIN_1, rx: PIN_0);

    let mut matrix =
        Matrix::<_, _, _, { hand::ROW }, { hand::COL }, { hand::COL2ROW }>::new(rows, cols, DefaultDebouncer::new());
    join3(double_reset, run_all!(matrix), run_rmk_split_peripheral(link)).await;
}

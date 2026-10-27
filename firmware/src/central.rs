//! The left hand: on USB to the host, scanning its own matrix and taking the right hand's
//! over the link.

#![no_main]
#![no_std]

#[macro_use]
mod hand;
mod keymap;

use defmt::info;
use defmt_rtt as _;
use embassy_executor::Spawner;
use embassy_rp::flash::{Async, Flash};
use embassy_rp::dma;
use embassy_rp::peripherals::{DMA_CH0, PIO0, USB};
use embassy_rp::usb::{self, Driver};
use embassy_rp::bind_interrupts;
use embassy_time::Duration;
use panic_probe as _;
use rmk::config::{BehaviorConfig, DeviceConfig, MorsesConfig, PositionalConfig, RmkConfig, StorageConfig};
use rmk::debounce::default_debouncer::DefaultDebouncer;
use rmk::futures::future::join3;
use rmk::keyboard::Keyboard;
use rmk::matrix::Matrix;
use rmk::split::PeripheralMatrixConfig;
use rmk::split::central::run_peripheral_manager;
use rmk::storage::async_flash_wrapper;
use rmk::types::morse::{MorseMode, MorseProfile};
use rmk::usb::UsbTransport;
use rmk::{KeymapData, initialize_keymap_and_storage, run_all};

bind_interrupts!(struct Irqs {
    USBCTRL_IRQ => usb::InterruptHandler<USB>;
    DMA_IRQ_0 => dma::InterruptHandler<DMA_CH0>;
    PIO0_IRQ_0 => rmk::split::rp::uart::UartInterruptHandler<PIO0>;
});

/// Flash, taken as 2 MB, the smallest these boards come with (`memory.x`).
const FLASH_SIZE: usize = 2 * 1024 * 1024;

/// Storage: RMK's default, the last 8 sectors of flash, which `memory.x` keeps the firmware out of.
const STORAGE: StorageConfig = StorageConfig {
    start_addr: 0,
    num_sectors: 8,
    clear_storage: false,
    clear_layout: false,
};

#[embassy_executor::main]
async fn main(_spawner: Spawner) {
    info!("Capybara central");
    let double_reset = hand::double_reset();
    let p = embassy_rp::init(Default::default());

    let driver = Driver::new(p.USB, Irqs);
    let (rows, cols) = matrix_pins!(p);
    // The right hand takes the link's pins the other way round.
    let link = link!(p, Irqs, tx: PIN_0, rx: PIN_1);
    let flash = async_flash_wrapper(Flash::<_, Async, FLASH_SIZE>::new(p.FLASH, p.DMA_CH0, Irqs));

    let rmk_config = RmkConfig {
        device_config: DeviceConfig {
            // Unregistered, like Rosebear's (0x5242 0x0002).
            vid: 0x5242,
            pid: 0x0003,
            manufacturer: "Capybara",
            product_name: "Capybara",
            serial_number: "capybara-0",
        },
        ..Default::default()
    };

    // Rosebear's tap-hold timing: tap-preferred, flow tap after 100 ms idle.
    let mut behavior_config = BehaviorConfig {
        morse: MorsesConfig {
            enable_flow_tap: true,
            prior_idle_time: Duration::from_millis(100),
            ..Default::default()
        },
        ..Default::default()
    };
    let profiles = &mut behavior_config.morse.profiles;
    // keymap::HOME, the home-row mods
    let _ = profiles.push(MorseProfile::new(
        Some(false),
        Some(MorseMode::PermissiveHold),
        Some(200),
        Some(200),
    ));
    // keymap::THUMB, the thumbs' layer-taps
    let _ = profiles.push(MorseProfile::new(
        Some(false),
        Some(MorseMode::HoldOnOtherPress),
        Some(150),
        Some(150),
    ));

    let mut keymap_data = KeymapData::new(keymap::get_default_keymap());
    let per_key_config = PositionalConfig::default();
    let (keymap, mut storage) =
        initialize_keymap_and_storage(&mut keymap_data, flash, &STORAGE, &mut behavior_config, &per_key_config).await;

    let mut matrix =
        Matrix::<_, _, _, { hand::ROW }, { hand::COL }, { hand::COL2ROW }>::new(rows, cols, DefaultDebouncer::new());
    let mut keyboard = Keyboard::new(&keymap);
    let mut usb_transport = UsbTransport::new(driver, rmk_config.device_config);

    join3(
        double_reset,
        run_all!(matrix, storage, usb_transport, keyboard),
        run_peripheral_manager(
            0,
            link,
            PeripheralMatrixConfig {
                rows: hand::ROW as u8,
                cols: hand::COL as u8,
                row_offset: 0,
                col_offset: hand::COL as u8,
            },
        ),
    )
    .await;
}

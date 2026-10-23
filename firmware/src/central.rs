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
use embassy_nrf::interrupt::{InterruptExt, Priority};
use embassy_nrf::nvmc::Nvmc;
use embassy_nrf::usb::vbus_detect::HardwareVbusDetect;
use embassy_nrf::usb::{self, Driver};
use embassy_nrf::{bind_interrupts, buffered_uarte, peripherals};
use embassy_time::Duration;
use panic_probe as _;
use rmk::config::{BehaviorConfig, DeviceConfig, MorsesConfig, PositionalConfig, RmkConfig, StorageConfig};
use rmk::debounce::default_debouncer::DefaultDebouncer;
use rmk::futures::future::join;
use rmk::keyboard::Keyboard;
use rmk::matrix::Matrix;
use rmk::split::PeripheralMatrixConfig;
use rmk::split::central::run_peripheral_manager;
use rmk::storage::async_flash_wrapper;
use rmk::types::morse::{MorseMode, MorseProfile};
use rmk::usb::UsbTransport;
use rmk::{KeymapData, initialize_keymap_and_storage, run_all};

bind_interrupts!(struct Irqs {
    USBD => usb::InterruptHandler<peripherals::USBD>;
    CLOCK_POWER => usb::vbus_detect::InterruptHandler;
    UARTE0 => buffered_uarte::InterruptHandler<peripherals::UARTE0>;
});

/// Storage: 8 sectors of 4 KB from 0xEC000, up to the bootloader at 0xF4000 (`memory.x`).
/// RMK's default, the end of flash, is the Adafruit bootloader's own pages.
const STORAGE: StorageConfig = StorageConfig {
    start_addr: 0xEC000,
    num_sectors: 8,
    clear_storage: false,
    clear_layout: false,
};
const _: () = assert!(
    STORAGE.start_addr >= 0xEC000 && STORAGE.start_addr + STORAGE.num_sectors as usize * 4096 <= 0xF4000,
    "storage must stay between the app and the bootloader"
);

#[embassy_executor::main]
async fn main(_spawner: Spawner) {
    info!("Capybara central");
    let mut config = embassy_nrf::config::Config::default();
    config.gpiote_interrupt_priority = Priority::P3;
    config.time_interrupt_priority = Priority::P3;
    embassy_nrf::interrupt::USBD.set_priority(Priority::P2);
    embassy_nrf::interrupt::CLOCK_POWER.set_priority(Priority::P2);
    let p = embassy_nrf::init(config);
    hand::start_hfxo();
    let _led_power = led_power_off!(p);

    let driver = Driver::new(p.USBD, Irqs, HardwareVbusDetect::new(Irqs));
    let (rows, cols) = matrix_pins!(p);
    // The left hand transmits on P0.06 and listens on P0.08.
    let link = link!(p, Irqs, rx: P0_08, tx: P0_06);
    let flash = async_flash_wrapper(Nvmc::new(p.NVMC));

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

    join(
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

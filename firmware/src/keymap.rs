//! Rosebear's four layers on Capybara's 40 keys.
//!
//! Each layer reads as typed: four rows of ten, the left hand's C0 (pinky) to C4 (inner), then
//! the right hand's C4 to C0. The last row is the thumbs, by the column each is wired to:
//! x2 (C0), near (C1), x1 (C2), home (C3) and far (C4). The left hand is the central's matrix,
//! columns 0 to 4; the right hand's matrix is columns 5 to 9 in wired order, so `wired` mirrors
//! its half.

use rmk::types::action::KeyAction;
use rmk::types::modifier::ModifierCombination as M;
use rmk::{a, k, ltp, mtp, shifted};

pub const ROW: usize = 4;
pub const COL: usize = 10;
pub const NUM_LAYER: usize = 4;

/// The morse profiles `mtp!` and `ltp!` index; `central.rs` sets their timing.
pub const HOME: u8 = 0;
pub const THUMB: u8 = 1;

const _______: KeyAction = a!(Transparent);
const XXXXXXX: KeyAction = a!(No);

#[rustfmt::skip]
const LAYERS: [[[KeyAction; COL]; ROW]; NUM_LAYER] = [
    // base
    [
        [k!(Q), k!(W), k!(F), k!(P), k!(B),    k!(J), k!(L), k!(U), k!(Y), k!(Quote)],
        [mtp!(A, M::LCTRL, HOME), mtp!(R, M::LALT, HOME), mtp!(S, M::LSHIFT, HOME), mtp!(T, M::LGUI, HOME), k!(G),
            k!(M), mtp!(N, M::RGUI, HOME), mtp!(E, M::RSHIFT, HOME), mtp!(I, M::RALT, HOME), mtp!(O, M::RCTRL, HOME)],
        [k!(Z), k!(X), k!(C), k!(D), k!(V),    k!(K), k!(H), k!(Comma), k!(Dot), k!(Slash)],
        // x2, near, x1, home, far    far, home, x1, near, x2
        [XXXXXXX, ltp!(2, Tab, THUMB), XXXXXXX, ltp!(1, Space, THUMB), ltp!(3, Escape, THUMB),
            ltp!(3, Delete, THUMB), ltp!(1, Enter, THUMB), XXXXXXX, ltp!(2, Backspace, THUMB), XXXXXXX],
    ],
    // numbers
    [
        [k!(F10), k!(F7), k!(F8), k!(F9), shifted!(LeftBracket),    shifted!(RightBracket), k!(Kc7), k!(Kc8), k!(Kc9), k!(Equal)],
        [k!(F11), k!(F4), k!(F5), k!(F6), shifted!(Kc9),    shifted!(Kc0), k!(Kc4), k!(Kc5), k!(Kc6), k!(Minus)],
        [k!(F12), k!(F1), k!(F2), k!(F3), k!(LeftBracket),    k!(RightBracket), k!(Kc1), k!(Kc2), k!(Kc3), k!(Semicolon)],
        [_______, _______, _______, _______, _______,    _______, k!(Kc0), _______, k!(Kc0), _______],
    ],
    // symbols and navigation
    [
        [k!(Home), k!(PageUp), k!(PageDown), k!(End), XXXXXXX,
            k!(Backslash), shifted!(Kc7), shifted!(Kc8), k!(Grave), shifted!(Equal)],
        [k!(Left), k!(Up), k!(Down), k!(Right), XXXXXXX,
            shifted!(Grave), shifted!(Kc4), shifted!(Kc5), shifted!(Kc6), shifted!(Minus)],
        [XXXXXXX, k!(AudioMute), k!(AudioVolDown), k!(AudioVolUp), XXXXXXX,
            shifted!(Backslash), shifted!(Kc1), shifted!(Kc2), shifted!(Kc3), shifted!(Semicolon)],
        [_______, _______, _______, _______, _______,    _______, _______, _______, _______, _______],
    ],
    // adjust and mouse
    [
        [XXXXXXX, XXXXXXX, XXXXXXX, XXXXXXX, XXXXXXX,    XXXXXXX, XXXXXXX, XXXXXXX, XXXXXXX, XXXXXXX],
        [k!(MouseLeft), k!(MouseUp), k!(MouseDown), k!(MouseRight), XXXXXXX,
            XXXXXXX, k!(MouseLeft), k!(MouseDown), k!(MouseUp), k!(MouseRight)],
        [k!(MouseAccel0), k!(MouseAccel1), k!(MouseAccel2), XXXXXXX, XXXXXXX,
            XXXXXXX, k!(MouseAccel2), k!(MouseAccel1), k!(MouseAccel0), XXXXXXX],
        [XXXXXXX, k!(MouseBtn3), XXXXXXX, k!(MouseBtn2), k!(MouseBtn1),
            k!(MouseBtn1), k!(MouseBtn2), XXXXXXX, k!(MouseBtn3), XXXXXXX],
    ],
];

/// The layers in matrix order: the right hand's half turned round, so its C0 is column 5.
const fn wired(layers: [[[KeyAction; COL]; ROW]; NUM_LAYER]) -> [[[KeyAction; COL]; ROW]; NUM_LAYER] {
    let mut out = layers;
    let mut l = 0;
    while l < NUM_LAYER {
        let mut r = 0;
        while r < ROW {
            let mut c = 0;
            while c < 5 {
                out[l][r][5 + c] = layers[l][r][COL - 1 - c];
                c += 1;
            }
            r += 1;
        }
        l += 1;
    }
    out
}

pub const fn get_default_keymap() -> [[[KeyAction; COL]; ROW]; NUM_LAYER] {
    wired(LAYERS)
}

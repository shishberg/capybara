// The rosebear 36-key layout: 5x3 finger matrix + 3 thumb keys per half.
//
// This replaces `v2/config.yaml`'s `points:` section. Values that were unit
// expressions there (`kx`, `1.08 kx`, `0.5 ky`) are resolved here against the
// constants below, so a typo is a compile error rather than a runtime surprise.
//
// The geometry is deliberately unchanged from v2 -- per v2-p4-pod.md, the
// layout is "re-cut as 4 passive modules + pod, angles locked as-if-unibody".
// What changed is everything downstream: no matrix, no diodes, direct wiring.

function KX() -> float {
    19.0
}

function KY() -> float {
    19.0
}

/// Key pitch including the 2mm inter-key gap (ergogen's `px`/`py`).
function PX() -> float {
    21.0
}

function PY() -> float {
    21.0
}

/// Default keycap footprint (ergogen's $default_width/height).
function KEY_W() -> float {
    18.0
}

function KEY_H() -> float {
    18.0
}

function std_row(name: string) -> RowSpec {
    RowSpec { name: name, padding: PY(), rotate: 0.0, width: KEY_W(), height: KEY_H() }
}

/// Finger rows, bottom-to-top -- the order ergogen walks them.
function finger_rows() -> RowSpec[] {
    [std_row("bottom"), std_row("home"), std_row("top")]
}

function origin0() -> Vec2 {
    Vec2 { x: 0.0, y: 0.0 }
}

function matrix_zone() -> ZoneSpec {
    ZoneSpec {
        name: "matrix",
        anchor: AnchorSpec { ref: null, shift: Vec2 { x: 50.0, y: -100.0 }, rotate: 0.0 },
        columns: [
            ColumnSpec {
                name: "pinky",
                spread: PX(),
                stagger: 0.0,
                splay: 5.0,
                origin: origin0(),
                rows: finger_rows(),
            },
            ColumnSpec {
                name: "ring",
                spread: 20.52,
                stagger: 9.5,
                splay: -5.0,
                origin: origin0(),
                rows: finger_rows(),
            },
            ColumnSpec {
                name: "middle",
                spread: 20.52,
                stagger: 5.0,
                splay: 0.0,
                origin: origin0(),
                rows: finger_rows(),
            },
            ColumnSpec {
                name: "index",
                spread: PX(),
                stagger: -7.6,
                splay: 0.0,
                origin: origin0(),
                rows: finger_rows(),
            },
            ColumnSpec {
                name: "inner",
                spread: PX(),
                stagger: -3.8,
                splay: 0.0,
                origin: origin0(),
                rows: finger_rows(),
            },
        ],
    }
}

function thumb_zone() -> ZoneSpec {
    ZoneSpec {
        name: "thumb",
        // Hangs off the inner column's bottom key, half a key left and a key
        // and a half down.
        anchor: AnchorSpec {
            ref: "matrix_inner_bottom",
            shift: Vec2 { x: 0.0 - 0.5 * KX(), y: 0.0 - 1.5 * KY() },
            rotate: 0.0,
        },
        columns: [
            ColumnSpec {
                name: "near",
                spread: 0.0,
                stagger: 0.0,
                splay: -15.0,
                origin: origin0(),
                rows: [
                    RowSpec {
                        name: "thumb",
                        padding: PY(),
                        rotate: 0.0,
                        width: KEY_W(),
                        height: KEY_H(),
                    },
                ],
            },
            ColumnSpec {
                name: "home",
                spread: 22.04,
                stagger: -1.9,
                splay: -15.0,
                origin: origin0(),
                // The 1.5u thumb key, turned 90 degrees.
                rows: [
                    RowSpec {
                        name: "thumb",
                        padding: PY(),
                        rotate: 90.0,
                        width: 1.5 * KX(),
                        height: KEY_H(),
                    },
                ],
            },
            ColumnSpec {
                name: "far",
                spread: 21.85,
                stagger: -2.85,
                splay: -15.0,
                origin: origin0(),
                rows: [
                    RowSpec {
                        name: "thumb",
                        padding: PY(),
                        rotate: 0.0,
                        width: KEY_W(),
                        height: KEY_H(),
                    },
                ],
            },
        ],
    }
}

function rosebear_zones() -> ZoneSpec[] {
    [matrix_zone(), thumb_zone()]
}

// ------------------------------------------------------------------ halves

/// Mirror keys about the vertical line x = axis, producing the opposite hand.
/// Each half is its own PCB, so the axis only sets absolute coordinates; the
/// board origin is normalised per module at emit time.
function mirror_keys(keys: PlacedKey[], axis: float, name_prefix: string) -> PlacedKey[] {
    keys.map((k) -> {
        PlacedKey {
            name: `${name_prefix}${k.zone}_${k.column}_${k.row}`,
            zone: k.zone,
            column: k.column,
            row: k.row,
            x: 2.0 * axis - k.x,
            y: k.y,
            r: 0.0 - k.r,
            width: k.width,
            height: k.height,
            mirrored: true,
        }
    })
}

/// Distance from the layout origin to mirror across. Sets how far apart the
/// two halves sit in the combined view; irrelevant to the per-module boards.
function MIRROR_AXIS() -> float {
    200.0
}

function left_keys() -> PlacedKey[] throws baml.errors.InvalidArgument {
    render_zones(rosebear_zones(), false, "")
}

function right_keys() -> PlacedKey[] throws baml.errors.InvalidArgument {
    mirror_keys(left_keys(), MIRROR_AXIS(), "mirror_")
}

function all_keys() -> PlacedKey[] throws baml.errors.InvalidArgument {
    left_keys().concat(right_keys())
}

// ------------------------------------------------------------------ golden
// Expected values are ergogen 4.0.4's own output for v2/config.yaml, captured
// at full precision. This is the differential test that lets us retire ergogen.

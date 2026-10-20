// Scanning the keys as a diode matrix instead of direct-wiring them.
//
// v3 gives every key its own GPIO, which is the simplest thing that works on a
// rigid board and the wrong thing on a segmented one. Direct wiring makes the
// conductor count ACCUMULATE along the row of column strips: the neck between
// the last two columns has to carry every signal from every column outboard of
// it. A matrix makes it CONSTANT -- one column line plus the shared row lines,
// whatever the column's position -- which is why BastardKB pushes exactly 6
// traces through each of its necks and no more.
//
// The thumb cluster joins as a sixth column rather than keeping its own lines.
// That costs one extra conductor on the short finger->thumb hop (4 rather than
// 3) and saves two at the pod, which is where the GPIO actually runs out.
//
//   direct-wired    18 signals/half, 36 GPIO, 20-way pod ribbon
//   matrix           9 signals/half, 18 GPIO, 12-way pod ribbon, 36 diodes

/// The matrix column a key belongs to.
///
/// Thumb keys fold into a column of their own, so a 5x3 finger block plus 3
/// thumb keys becomes a 6x3 matrix with no empty positions -- the layout
/// happens to be exactly full, which is why no ghosting mask is needed.
function matrix_col(k: PlacedKey) -> string {
    if (k.zone == "thumb") {
        "thumb"
    } else {
        k.column
    }
}

/// The matrix row a key belongs to.
///
/// The thumb cluster's three keys run along what the layout calls columns, so
/// they map onto the finger rows by position: near/home/far to bottom/home/top.
function matrix_row(k: PlacedKey) -> string {
    if (k.zone == "thumb") {
        let i = index_of_str(THUMB_ORDER(), k.column);
        ROW_ORDER().at(i) ?? "bottom"
    } else {
        k.row
    }
}

/// Position of `s` in `xs`, or 0 if absent.
function index_of_str(xs: string[], s: string) -> int {
    let out = 0;
    let i = 0;
    for (let x in xs) {
        if (x == s) {
            out = i;
        }
        i = i + 1;
    }
    out
}

/// Matrix columns, in board order, thumb last.
function MATRIX_COLS() -> string[] {
    COLUMN_ORDER().concat(["thumb"])
}

function MATRIX_ROWS() -> string[] {
    ROW_ORDER()
}

/// Which hand a key's matrix lines belong to. The two halves are scanned
/// independently -- the pod drives each through its own ribbon -- so their
/// lines must not share nets.
function hand_of_key(k: PlacedKey) -> string {
    if (k.mirrored) {
        "r"
    } else {
        "l"
    }
}

function col_net(k: PlacedKey) -> string {
    `COL_${hand_of_key(k).to_upper_case()}_${matrix_col(k).to_upper_case()}`
}

function row_net(k: PlacedKey) -> string {
    `ROW_${hand_of_key(k).to_upper_case()}_${matrix_row(k).to_upper_case()}`
}

/// The net between a key's switch and its diode.
///
/// COL2ROW: the column line drives the switch, the switch feeds the diode's
/// anode, and the diode's cathode joins the row line. The diode is what stops
/// three simultaneous keys in a rectangle reading as a fourth.
function switch_diode_net(k: PlacedKey) -> string {
    `SWD_${k.name.to_upper_case()}`
}

// ------------------------------------------------------------------- signals

/// The distinct matrix lines needed to reach `keys`, in a fixed order.
///
/// Derived from the keys themselves, so a sixth column or a fourth row changes
/// the ribbon widths, the pod pinout and the neck trace budget with no number
/// edited anywhere. Columns first, then rows: the column lines are what a
/// strip carries locally, the row lines are what crosses every neck.
function matrix_signals(keys: PlacedKey[]) -> Signal[] {
    let out: Signal[] = [];
    for (let c in MATRIX_COLS()) {
        let hit = keys.find((k) -> {
            matrix_col(k) == c
        });
        if let k: PlacedKey = hit {
            out.push(Signal { name: col_net(k), kind: SignalKind.Key });
        }
    }
    for (let r in MATRIX_ROWS()) {
        let hit = keys.find((k) -> {
            matrix_row(k) == r
        });
        if let k: PlacedKey = hit {
            out.push(Signal { name: row_net(k), kind: SignalKind.Key });
        }
    }
    out
}

/// Traces that have to cross the neck between two adjacent column strips.
///
/// The row lines cross every neck; each column's own line joins at its strip
/// and continues inward to the connector. So the count grows by one per gap,
/// not by one per KEY -- which is the whole difference from direct wiring.
///
/// `i` is the gap west of column `i + 1`, counting from the outboard end.
function matrix_neck_traces(keys: PlacedKey[], i: int) -> int {
    let rows = MATRIX_ROWS()
        .filter((r) -> {
            keys.find((k) -> {
                matrix_row(k) == r
            })
                != null
        })
        .length();
    // Columns outboard of this gap, whose lines all run through it.
    rows + i + 1
}

// -------------------------------------------------------------------- diodes

/// SOD-123. Through-hole would be easier to hand-solder but stands proud of a
/// board that has to sit close under the switch plate.
function DIODE_FOOTPRINT() -> string {
    "Diode_SMD:D_SOD-123"
}

// --------------------------------------------------------------------- tests

// ---------------------------------------------------------- wiring the boards

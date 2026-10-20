// Routing.
//
// These boards are not a general routing problem and don't want a general
// router. The topology is a fan-in: every key has exactly one signal net with
// exactly two pads -- its own switch pin and one contact on the ribbon
// connector -- and everything else is ground.
//
// Two facts make that trivially routable:
//
//   * Ground doesn't need traces at all. A pour on each side reaches every
//     switch pin (through-hole) and the connector's mounting pegs (SMD, front).
//
//   * We choose the connector pinout. `ribbon_signals` emits key signals in
//     column order, so if the columns are read off the board left to right the
//     nets fan in without a single crossing. That makes this a river-routing
//     problem, which has a closed-form answer -- no search, no rip-up, and a
//     deterministic result, which a stochastic autorouter could not give.
//
// The pod board will not be like this and will want Freerouting or hand
// routing; nothing here is meant to generalise to it.

class Track {
    start: Vec2,
    end: Vec2,
    width: float,
    layer: string,
    net: string,
}

class Via {
    at: Vec2,
    net: string,
}

class Zone {
    net: string,
    layer: string,
    outline: Vec2[],
}

function TRACE_W() -> float {
    0.25
}

// ------------------------------------------------------- footprint geometry
//
// Pad offsets are declared rather than parsed. `route_test.baml` asserts each
// one against the installed .kicad_mod, so a library change fails the build
// instead of quietly moving a trace off its pad.

/// Kailh hotswap socket, terminal 1 -- the key's own net. Surface pad, BACK.
function MX_SIGNAL_PAD() -> Vec2 {
    Vec2 { x: 5.842, y: 0.0 - 5.08 }
}

/// Kailh hotswap socket, terminal 2 -- tied to ground. Surface pad, BACK.
function MX_GND_PAD() -> Vec2 {
    Vec2 { x: 0.0 - 7.085, y: 0.0 - 2.54 }
}

/// Contact `i` (1-based) of a Molex 200528 of `ways` ways, in footprint
/// coordinates. 1.00mm pitch, centred, contacts on the key side of the body.
function ffc_pad_local(i: int, ways: int) -> Vec2 {
    Vec2 { x: (i * 1.0) - (((ways + 1) * 1.0) / 2.0), y: 0.0 - 0.91 }
}

// ------------------------------------------------------------------ frames

/// A footprint-local point in board coordinates.
///
/// KiCad applies the negation of a footprint's stored angle to its local
/// coordinates; see `local_to_board` in netlist.baml.
function comp_to_global(c: Component, v: Vec2) -> Vec2 {
    // A footprint on the back is mirrored about the x axis and its rotation
    // runs the other way; `embed_footprint` writes the board file to match, and
    // this has to agree with it or every trace to a back-side pad misses.
    let back = c.layer == "B.Cu";
    let w = if (back) {
        Vec2 { x: v.x, y: 0.0 - v.y }
    } else {
        v
    };
    let a = if (back) {
        c.r
    } else {
        0.0 - c.r
    };
    let p = rotate_about(w, a, Vec2 { x: 0.0, y: 0.0 });
    Vec2 { x: c.x + p.x, y: c.y + p.y }
}

// --------------------------------------------------------------- the router

/// The column a key net belongs to.
///
/// Key nets are `KEY_[MIRROR_]<zone>_<column>_<row>`, so the column is always
/// the second-to-last field -- counting from the front picks up "MATRIX" for
/// every mirrored key, collapsing the right hand into one 15-lane column.
function column_of(net: string) -> string {
    let parts = net.split("_");
    parts.at(parts.length() - 2) ?? ""
}

function is_connector(c: Component) -> bool {
    c.ref.starts_with("J")
}

function seg(a: Vec2, b: Vec2, net: string) -> Track {
    Track { start: a, end: b, width: TRACE_W(), layer: "F.Cu", net: net }
}

function VIA_DIA() -> float {
    0.6
}

/// Ground is poured, not routed: a zone on each side.
function ground_zones(b: Board) -> Zone[] {
    [
        Zone { net: "GND", layer: "F.Cu", outline: b.outline },
        Zone { net: "GND", layer: "B.Cu", outline: b.outline },
    ]
}

// ------------------------------------------------------------- per-key LEDs
//
// The chain is a path through 15 (or 3) reverse-mount LEDs on the back, and it
// is the only net on a key board that is not a fan-in. Two shapes carry it:
//
//   * Within a column, on the FRONT. Each hop leaves its LED's dout on the back,
//     vias up beside the LED, runs a single lane up the column between the
//     switch's stabiliser hole and the previous column's channel, and vias back
//     down beside the next LED's din. Consecutive hops share that lane and
//     never meet, because the dout via sits 1.25mm above the din via: hop `j`
//     ends where hop `j+1` has not started.
//
//   * Between columns, on the BACK. The front between two columns is the first
//     one's channel and cannot be crossed. The back can be, but only outside
//     the key field -- so a transition leaves the column at whichever end the
//     chain reached, runs out past the last key, crosses, and comes back in.
//     Boustrophedon ordering is what makes that work: consecutive columns are
//     always entered and left at the same end.

/// BAML has no `contains` on string[]; this is the missing membership test.
function contains_str(xs: string[], s: string) -> bool {
    xs.find((x) -> {
        x == s
    })
        != null
}

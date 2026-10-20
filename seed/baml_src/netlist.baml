// Components and nets per module.
//
// Direct-wired per v2-p4-pod.md: one GPIO per key, no matrix, no diodes. Each
// switch bridges its own net to ground; the pod does the pull-up and reads 36
// inputs.

class Pad {
    pad: string,
    net: string,
}

class Component {
    ref: string,
    /// "Library:Footprint", resolved against the KiCad footprint path.
    footprint: string,
    x: float,
    y: float,
    r: float,
    layer: string,
    pads: Pad[],
}

class Board {
    id: string,
    components: Component[],
    /// Edge.Cuts polygon, already in KiCad coordinates.
    outline: Vec2[],
    /// Interior Edge.Cuts contours: holes and slots cut out of `outline`.
    ///
    /// Each is its own closed polygon. KiCad wants one contour per region and
    /// unites nothing, so these must not touch each other or the outline --
    /// see `hinge_slots`, which pulls its end caps in for exactly that reason.
    /// Empty on a rigid board.
    cuts: Vec2[][],
    /// Copper. Empty until `route_board` has run.
    tracks: Track[],
    /// Layer changes, used only by the pass-through nets.
    vias: Via[],
    /// Copper pours. Ground is poured rather than routed.
    zones: Zone[],
}

/// Switch footprint, chosen by key width.
///
/// Kailh hotswap: the switch drops into a socket soldered to the BACK of the
/// board rather than being soldered in itself. That is a routing decision as
/// much as a mechanical one -- a hotswap key's two terminals are surface pads
/// on the back, not through-holes, so neither one reaches the front pour and
/// neither one can start a trace on the front. See `route_column`.
///
/// KiCad ships no hotswap footprint; `footprints/gen_hotswap.py` generates this
/// family. Choc (PG1350) has neither and would need a third-party library.
function switch_footprint(width: float) -> string {
    let u = width / KX();
    let size = if (u >= 2.6) {
        "2.75u"
    } else if (u >= 2.1) {
        "2.25u"
    } else if (u >= 1.9) {
        "2.00u"
    } else if (u >= 1.6) {
        "1.75u"
    } else if (u >= 1.4) {
        "1.50u"
    } else if (u >= 1.15) {
        "1.25u"
    } else {
        "1.00u"
    };
    `${LOCAL_FOOTPRINT_LIB()}:SW_Hotswap_Kailh_MX_${size}_PCB`
}

/// The Molex 200528 family covers every way-count from 4 to 30 continuously, so
/// the connector part is a pure function of the derived ribbon width.
function ffc_footprint(ways: int) -> string throws baml.errors.InvalidArgument {
    if (ways < 4 || ways > 30) {
        throw baml.errors.InvalidArgument {
            message: `no Molex 200528 FFC part for ${ways} ways (family covers 4..30)`
        };
    }
    let w2 = if (ways < 10) {
        `0${ways}`
    } else {
        `${ways}`
    };
    `Connector_FFC-FPC:Molex_200528-0${w2}0_1x${w2}-1MP_P1.00mm_Horizontal`
}

// ------------------------------------------------------------- coordinates

/// Ergogen's y axis points up; KiCad's points down.
function to_kicad(p: Vec2) -> Vec2 {
    Vec2 { x: p.x, y: 0.0 - p.y }
}

// ------------------------------------------------------------- convex hull

/// Indexed access with an unreachable fallback: every call site is guarded by
/// a length check, but BAML has no non-null assertion.
function vec_at(xs: Vec2[], i: int) -> Vec2 {
    xs.at(i) ?? Vec2 { x: 0.0, y: 0.0 }
}

function cross_z(o: Vec2, a: Vec2, b: Vec2) -> float {
    (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)
}

/// Andrew's monotone chain. Gives a far better board shape than a bounding box
/// for a splayed layout, without needing polygon boolean ops.
function convex_hull(pts: Vec2[]) -> Vec2[] {
    if (pts.length() < 3) {
        return pts;
    }
    let sorted = pts.sort_by((a, b) -> {
        if (a.x < b.x) {
            0 - 1
        } else if (a.x > b.x) {
            1
        } else if (a.y < b.y) {
            0 - 1
        } else if (a.y > b.y) {
            1
        } else {
            0
        }
    });

    let lower: Vec2[] = [];
    for (let p in sorted) {
        while (
            lower.length() >= 2
                && cross_z(vec_at(lower, lower.length() - 2), vec_at(lower, lower.length() - 1), p)
                    <= 0.0
        ) {
            lower.pop();
        }
        lower.push(p);
    }

    let upper: Vec2[] = [];
    for (let p in sorted.reverse()) {
        while (
            upper.length() >= 2
                && cross_z(vec_at(upper, upper.length() - 2), vec_at(upper, upper.length() - 1), p)
                    <= 0.0
        ) {
            upper.pop();
        }
        upper.push(p);
    }

    let hull: Vec2[] = [];
    let i = 0;
    while (i < lower.length() - 1) {
        hull.push(vec_at(lower, i));
        i = i + 1;
    }
    let j = 0;
    while (j < upper.length() - 1) {
        hull.push(vec_at(upper, j));
        j = j + 1;
    }
    hull
}

/// Grow a convex outline by a uniform margin, to leave room around the keys
/// for the board edge.
///
/// This is an edge-normal offset -- every edge moves out by exactly `margin`,
/// and each vertex lands where its two shifted edges meet. Pushing vertices
/// out from the centroid instead is not uniform: an edge far from the centroid
/// and nearly radial barely moves, and anything measured against the offset
/// line (the finger/thumb gap is) comes out thinner than asked for.
function expand_hull(hull: Vec2[], margin: float) -> Vec2[] {
    let n = hull.length();
    if (n < 3) {
        return hull;
    }
    // Shoelace sign says which side of an edge is out.
    let area = 0.0;
    let i = 0;
    while (i < n) {
        let a = hull.at(i) ?? Vec2 { x: 0.0, y: 0.0 };
        let b = hull.at(
            if (i + 1 < n) {
                i + 1
            } else {
                0
            },
        )
            ?? Vec2 { x: 0.0, y: 0.0 };
        area = area + (a.x * b.y - b.x * a.y);
        i = i + 1;
    }
    let k = if (area > 0.0) {
        1.0
    } else {
        0.0 - 1.0
    };
    let out: Vec2[] = [];
    i = 0;
    while (i < n) {
        let prev = hull.at(
            if (i > 0) {
                i - 1
            } else {
                n - 1
            },
        )
            ?? Vec2 { x: 0.0, y: 0.0 };
        let cur = hull.at(i) ?? Vec2 { x: 0.0, y: 0.0 };
        let next = hull.at(
            if (i + 1 < n) {
                i + 1
            } else {
                0
            },
        )
            ?? Vec2 { x: 0.0, y: 0.0 };
        out.push(offset_corner(prev, cur, next, k * margin));
        i = i + 1;
    }
    out
}

/// Where a vertex lands when both its edges shift out by `m` (signed by the
/// polygon's winding). Falls back to a plain normal push when the edges are
/// parallel.
function offset_corner(prev: Vec2, cur: Vec2, next: Vec2, m: float) -> Vec2 {
    let d1 = Vec2 { x: cur.x - prev.x, y: cur.y - prev.y };
    let d2 = Vec2 { x: next.x - cur.x, y: next.y - cur.y };
    let l1 = d1.x.hypot(d1.y);
    let l2 = d2.x.hypot(d2.y);
    if (l1 == 0.0 || l2 == 0.0) {
        return cur;
    }
    let a1 = Vec2 { x: cur.x + d1.y / l1 * m, y: cur.y - d1.x / l1 * m };
    let a2 = Vec2 { x: cur.x + d2.y / l2 * m, y: cur.y - d2.x / l2 * m };
    let denom = d1.x * d2.y - d1.y * d2.x;
    if (denom.abs() < 0.000001) {
        return a1;
    }
    // Solve a1 + t*d1 = a2 + u*d2 for t.
    let t = ((a2.x - a1.x) * d2.y - (a2.y - a1.y) * d2.x) / denom;
    Vec2 { x: a1.x + t * d1.x, y: a1.y + t * d1.y }
}

function BOARD_MARGIN() -> float {
    4.0
}

// ------------------------------------------------------------------ boards

/// Where the key centre sits inside the switch footprint.
///
/// KiCad's `SW_Cherry_MX_*_PCB` puts its origin at pad 1, with the 4mm stem
/// hole -- the actual key centre -- offset from it, so placing that footprint
/// at the key position shifted every switch by (-2.54, 5.08). The generated
/// hotswap footprints re-origin to the stem hole, which is the frame every
/// number in the Kailh land pattern is already quoted in, so the correction is
/// now zero -- kept as a function because it is still load-bearing, and
/// `switch_centre_offset_matches_library` still checks it against the file.
function SWITCH_CENTRE_IN_FOOTPRINT() -> Vec2 {
    Vec2 { x: 0.0, y: 0.0 }
}

/// Rotate a footprint-local vector into board space.
///
/// KiCad applies the negation of the stored angle to footprint-local
/// coordinates, and `to_kicad`'s y-flip already reverses the sense of
/// rotation; the two cancel, so a local offset turns by -k.r.
function local_to_board(v: Vec2, k: PlacedKey) -> Vec2 {
    rotate_about(v, 0.0 - k.r, Vec2 { x: 0.0, y: 0.0 })
}

function switch_component(k: PlacedKey, index: int, f: Features) -> Component {
    let c = to_kicad(k.pos());
    // Place the origin so the *key centre* lands on the key position.
    let off = local_to_board(SWITCH_CENTRE_IN_FOOTPRINT(), k);
    // Direct-wired: one side to its own GPIO net, the other to ground.
    // Matrix (COL2ROW): one side to the column line, the other to the diode
    // that joins it to the row line -- so the second terminal stops being
    // ground and the pour no longer reaches it.
    let pads = if (f.matrix) {
        [Pad { pad: "1", net: col_net(k) }, Pad { pad: "2", net: switch_diode_net(k) }]
    } else {
        [Pad { pad: "1", net: key_net(k) }, Pad { pad: "2", net: "GND" }]
    };
    Component {
        ref: `SW${index}`,
        footprint: switch_footprint(k.width),
        x: c.x - off.x,
        y: c.y - off.y,
        // Ergogen emits +r here and KiCad negates it internally; emitting -r
        // rotates every splayed key the wrong way.
        r: k.r,
        layer: "F.Cu",
        pads: pads,
    }
}

/// Where a key's diode sits, in the key's own frame.
///
/// Centred in the band between the switch keep-out and the first hinge cut --
/// on Toto, 7.5mm to 10.01mm from the key centre, so 8.76mm. Derived rather
/// than chosen: a SOD-123 lying across the strip is only 3mm wide including its
/// pads, and putting it a fixed 9mm out left it 0.41mm from the hinge slot
/// where the rule wants 0.5. `a diode clears both the switch and its hinges`
/// guards the band from either side.
function DIODE_REACH() -> float {
    let p = flex_defaults();
    (p.switch_clear + nearest_hinge_cut(ROSEBEAR_WELL(), p)) / 2.0
}

/// A key's diode offset, in the key's own frame.
///
/// Always toward the MIDDLE of its column. The band is only 3mm wide and sits
/// 9mm out, which is further than the strip extends past its outermost key --
/// so putting every diode on the same side drops the top row's diodes off the
/// end of the board. The paper proof showed exactly that.
function diode_offset(k: PlacedKey) -> Vec2 {
    let outward = matrix_row(k) == "top";
    Vec2 {
        x: 0.0,
        y: if (outward) {
            DIODE_REACH()
        } else {
            0.0 - DIODE_REACH()
        },
    }
}

/// One key's matrix diode.
///
/// Turned across the column so its long axis runs the way the strip is WIDE.
/// Along the column it would straddle a hinge row, and a rigid 4.2mm part
/// bridging a fold is a part that shears off -- which is exactly what the extra
/// 90 degrees this used to store produced: every diode's pads reached 10.86mm
/// out from its key, past the hinge cut at 10.01.
///
/// Storing `-r` rather than `r` for the same reason as the LED: a back-side
/// part is mirrored, so KiCad applies its negated angle to already-flipped
/// coordinates, and only the negated angle keeps the part's axis lined up with
/// the key's whatever the key's angle.
function diode_component(k: PlacedKey, index: int) -> Component {
    let centre = to_kicad(k.pos());
    let off = local_to_board(diode_offset(k), k);
    Component {
        ref: `D${index}`,
        footprint: DIODE_FOOTPRINT(),
        x: centre.x + off.x,
        y: centre.y + off.y,
        r: 0.0 - k.r,
        layer: "B.Cu",
        // SOD-123: pad 1 is the cathode, and it faces the row line.
        pads: [Pad { pad: "1", net: row_net(k) }, Pad { pad: "2", net: switch_diode_net(k) }],
    }
}

/// Connector pads: conductor i carries signal i; the mounting pegs go to ground.
function ffc_pads(sigs: Signal[]) -> Pad[] {
    let pads: Pad[] = [];
    let i = 1;
    for (let s in sigs) {
        pads.push(Pad { pad: `${i}`, net: s.name });
        i = i + 1;
    }
    pads.push(Pad { pad: "MP", net: "GND" });
    pads
}

function connector_component(
    ref: string,
    sigs: Signal[],
    at: Vec2,
    r: float,
) -> Component throws baml.errors.InvalidArgument {
    Component {
        ref: ref,
        footprint: ffc_footprint(sigs.length()),
        x: at.x,
        y: at.y,
        r: r,
        layer: "F.Cu",
        pads: ffc_pads(sigs),
    }
}

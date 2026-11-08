"""The capybara design's body and plinth (params.py design "capybara"): the
Capybara's keys where its editor puts them (layout.py swung_in), each switch in
a plate with its RGB key tile hanging under it in an open shell, and a flat
plinth on the desk that's the floor the hand wiring lies loose on.

The body is chassis.py's shell (its top surface, rounded top edge and vertical
walls), hollowed to the walls and a top skin, with each key's plate, sleeve
and pocket hanging from the skin, pegs in the tile's corner notches, and a
post for each plinth screw. The Pro Micro, the TRRS jack and the reset switch
stand where the editor puts them, slid along their ports' axes to meet this
outline's wall, each on a cradle on the plinth; the ports go out through the
walls. The harness goes in from the underside with the plinth off: each tile up
into its pocket, then the switches in from the top. Everything here is in world
axes (layout.py), the seam the plinth's level top, bottom_plate_mm over the desk.
"""
import math
import time

import numpy as np
from manifold3d import CrossSection, JoinType

from . import chassis as C
from . import layout as L
from . import params as P
from . import parts as R
from .chassis import add, fused, place, placed, polygon, put_back_mm, stage, subtract
from .layout import cached, keys
from .lib import origin, r2, trans, xdir, xform
from .parts import Piece, segments, union

PARTS = ("pro_micro", "trrs", "reset")
ROOMS = {"pro_micro": R.pro_micro_room, "trrs": R.trrs_room, "reset": R.reset_room}
# Each part's mouth (what meets the wall's face) in its frame, and the way out.
MOUTHS = {"pro_micro": lambda: (R.usb_mouth_x(), 0, 0), "trrs": lambda: (R.trrs_mouth_x(), 0, 0), "reset": lambda: (0, 0, 0)}
OUTWARD = {"pro_micro": (-1, 0, 0), "trrs": (-1, 0, 0), "reset": (0, 0, -1)}


def seam():
    return P.bottom_plate_mm


def plinth_top():
    return seam() - P.plate_gap_mm


# ---------------------------------------------------------------- the outline
def base_faces():
    """What the outline closes round: the finger block (its keys' plates and
    pockets, which hold the tiles, and the Pro Micro's and the jack's footprints
    where the editor puts them) and the thumb cluster, each as its convex hull,
    so the wall runs straight past the keys' jogs. The plans are grown by the
    outline's chord tolerance, so the wall can't touch them."""
    b, j = R.mcu(), R.jack()
    bx, by, bz = b["board_mm"]
    jx, jy, jz = j["body_mm"]
    c, d = b["clearance_mm"], j["clearance_mm"]
    board = placed(L.editor_frame("pro_micro"), R.box((bx + 2 * c, by + 2 * c, bz), (0, 0, bz / 2)))
    jack = placed(L.editor_frame("trrs"), R.box((jx + 2 * d, jy + 2 * d, jz), (0, 0, jz / 2)))
    plan = lambda k: placed(k.frame, R.plate_block() + pocket_block())
    finger = union([plan(k) for k in keys() if k.group == "finger"] + [board, jack])
    thumb = union([plan(k) for k in keys() if k.group != "finger"])
    return fused([s.project().hull().offset(2 * P.mesh_tol_mm, JoinType.Miter) for s in (finger, thumb)])


@cached
def outline_stations():
    """The outline's stations and inward normals (chassis.stations_of), which
    the parts and the screws are placed from."""
    return C.stations_of(C.outline_curve_of(base_faces(), [], []))


def outline_faces():
    """The outline (chassis.outline_curve): the base faces walled."""
    return base_faces(), [], []


def inside(extra=0):
    """The plan inside the walls, and `extra` further in."""
    d = P.wall_mm + extra
    return polygon(C.outline()).offset(-d, JoinType.Round, 2.0, 4 * segments(d))


def inside_prism(extra=0):
    return inside(extra).extrude(400).translate((0, 0, seam() - 200))


# ---------------------------------------------------------------- the parts' places
def to_outline(p, d):
    """How far the bare outline is from the plan point p along the direction d:
    the nearest crossing either way (negative behind)."""
    a = outline_stations()[0]
    e = np.roll(a, -1, axis=0) - a
    w = a - p
    den = d[0] * e[:, 1] - d[1] * e[:, 0]
    ok = np.abs(den) > 1e-12
    safe = np.where(ok, den, 1)
    t, u = (w[:, 0] * e[:, 1] - w[:, 1] * e[:, 0]) / safe, (w[:, 0] * d[1] - w[:, 1] * d[0]) / safe
    hit = t[ok & (u >= 0) & (u <= 1)]
    return float(hit[np.abs(hit).argmin()])


@cached
def slides():
    """How far each part moves from the editor's placement, out along its
    port's axis, for its mouth to sit on this outline's wall (the reset
    switch's plunger face reset_skin_mm behind it)."""
    out = {}
    for name in PARTS:
        m = L.editor_frame(name)
        mouth, way = xform(m, MOUTHS[name]()), xdir(m, OUTWARD[name])
        out[name] = to_outline(mouth[:2], way[:2]) - (P.reset_skin_mm if name == "reset" else 0)
    return out


def part_frame(name):
    m = L.editor_frame(name)
    return trans(slides()[name] * xdir(m, OUTWARD[name])) @ m


def part_rooms():
    return [s for name in PARTS for s in place(part_frame(name), ROOMS[name]())]


# ---------------------------------------------------------------- the screws
def outline_spot(s):
    """The point s along the bare outline from its first station, and the
    inward normal there."""
    q, n = outline_stations()
    along = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.r_[q, q[:1]], axis=0), axis=1))]
    s %= along[-1]
    i = int(np.searchsorted(along, s, side="right") - 1)
    j = (i + 1) % len(q)
    f = (s - along[i]) / (along[i + 1] - along[i])
    return q[i] + f * (q[j] - q[i]), n[i] + f * (n[j] - n[i])


def corners():
    """The bare outline's convex corners as (turn in degrees, s along the
    outline at the corner's middle): each run of stations bending tighter than
    outline_round_mm + 1 mm turning the same way, counted up."""
    q = outline_stations()[0]
    n = len(q)
    e = np.roll(q, -1, axis=0) - q
    length = np.linalg.norm(e, axis=1)
    heading = np.arctan2(e[:, 1], e[:, 0])
    turn = np.angle(np.exp(1j * (heading - np.roll(heading, 1))))    # at each station, in
    along = np.r_[0, np.cumsum(length)]
    bend = turn / ((np.roll(length, 1) + length) / 2)
    tight = bend > 1 / (P.outline_round_mm + 1)
    if tight.all() or not tight.any():
        return []
    start = int(np.argmin(tight))     # a station that isn't in a corner
    out, run = [], []
    for k in range(start, start + n + 1):
        i = k % n
        if tight[i] and k < start + n:
            run.append(i)
        elif run:
            total = math.degrees(sum(turn[i] for i in run))
            out.append((total, (along[run[0]] + along[run[-1]]) / 2))
            run = []
    return out


def blocked_plan():
    """What a screw's boss must keep clear of, in plan: the tiles' rooms, the
    parts' rooms and the cradles on the plinth. A boss can join a plate or a
    pocket's wall: they're the body."""
    return fused([union(place(k.frame, R.tile_room())).project() for k in keys()]
                 + [union(part_rooms()).project(), union(cradles()).project()])


def pad_r():
    """The seat's pad: min_wall_mm round the head's counterbore."""
    return R.counterbore_d() / 2 + P.min_wall_mm


def recess_r():
    return pad_r() + P.plate_gap_mm


def seat_wall_r():
    """How far a screw stands inside the outline: min_wall_mm of wall outside its seat's recess."""
    return recess_r() + P.min_wall_mm


def nearest_in(area, p):
    """The point of the plan area nearest p: p itself when it's inside."""
    if (CrossSection.circle(0.01, 4).translate(tuple(p)) ^ area).area() > 0:
        return np.asarray(p, float)
    best = None
    for ring in area.to_polygons():
        a = np.asarray(ring, float)
        e = np.roll(a, -1, axis=0) - a
        t = np.clip(((p - a) * e).sum(axis=1) / np.maximum((e * e).sum(axis=1), 1e-12), 0, 1)
        q = a + t[:, None] * e
        c = q[int(np.argmin(np.linalg.norm(q - p, axis=1)))]
        if best is None or np.linalg.norm(c - p) < np.linalg.norm(best - p):
            best = c
    return best


@cached
def screw_points():
    """Where the plinth screws into the body: for each corner the rule picks on
    the outline (params.py screw_boss_mm), the nearest spot inside it that's
    screw_clearance_mm clear of the tiles' and the parts' rooms and far enough
    in for the seat's recess and its wall, unless a screw is already within
    screw_apart_mm of it."""
    q = outline_stations()[0]
    around = float(np.linalg.norm(np.diff(np.r_[q, q[:1]], axis=0), axis=1).sum())

    def apart(a, b):
        d = abs(a - b) % around
        return min(d, around - d)

    kept = []
    for turn, s in sorted(corners(), reverse=True):
        if turn >= P.screw_corner_deg and all(apart(s, k) >= P.screw_apart_mm for k in kept):
            kept.append(s)
    kept.sort()
    spots = []
    for i, s in enumerate(kept):
        run = (kept[(i + 1) % len(kept)] - s) % around or around
        parts = math.ceil(run / P.screw_gap_mm)
        spots += [(s + run * j / parts) % around for j in range(parts)]
    r = P.screw_boss_mm / 2 + P.screw_clearance_mm
    free = polygon(q).offset(-seat_wall_r(), JoinType.Round, 2.0, segments(r)) - blocked_plan().offset(r, JoinType.Round, 2.0, segments(r))
    points = []
    for s in spots:
        c = nearest_in(free, outline_spot(s)[0])
        if all(np.linalg.norm(c - o) >= P.screw_apart_mm for o in points):
            points.append(c)
    return points


def screw_seat_z():
    """Where the screws' heads bear: the plinth's top, or a pad up to what a
    head and screw_grip_mm need when the plinth is thinner than that."""
    return max(plinth_top(), P.screw_grip_mm + P.screw_head_h_mm)


def screw_seats():
    return [screw_seat_z()] * len(screw_points())


def insert_holes():
    return [C.insert_hole_at(p, screw_seat_z()) for p in screw_points()]


def boss(p):
    """A screw's boss, from its seat up through the body's top (the body clips
    it, so inside the outline it hangs from the top), lapping put_back_mm into
    the plinth's gap."""
    return R.cylinder(P.screw_boss_mm, 200, (p[0], p[1], screw_seat_z() + P.plate_gap_mm - put_back_mm))


def recesses():
    """The recess in the body's underside over each seat's pad, from the seam
    up to the boss's foot; nothing where the seat is the plinth's top."""
    h = screw_seat_z() - plinth_top()
    if h <= 0:
        return []
    return [R.cylinder(2 * recess_r(), h + put_back_mm, (p[0], p[1], seam() - put_back_mm)) for p in screw_points()]


def seat_pads():
    """The screws' seats on the plinth, where it's too thin for the heads: a
    pad up from the plinth's top to the seat round each."""
    h = screw_seat_z() - plinth_top()
    if h <= 0:
        return []
    return [R.cylinder(2 * pad_r(), h + put_back_mm, (p[0], p[1], plinth_top() - put_back_mm)) for p in screw_points()]


# ---------------------------------------------------------------- the body
@cached
def interior():
    """The hollow: inside the walls, up to top_skin_mm under the top."""
    return inside_prism() ^ C.body_shell().translate((0, 0, -P.top_skin_mm))


def pocket_block():
    """A tile's pocket before the room is cut from it, in the key frame: a block
    round the tile's clearance and pocket_wall_mm more, from inside the plate
    down to the board's underside."""
    t = P.capybara["tile"]
    w = t["size_mm"][0] + 2 * (t["clearance_mm"] + P.pocket_wall_mm)
    top, under = -P.top_skin_mm / 2, R.tile_top_z() - t["size_mm"][2]
    return R.box((w, w, top - under), (0, 0, (top + under) / 2))


def plates():
    """Every key's plate and sleeve, and its pocket block, hanging from the top skin."""
    return union([placed(k.frame, R.plate_block() + pocket_block()) for k in keys()]) ^ C.body_shell()


@cached
def body_cuts():
    """Everything cut from the body but the screws' insert holes, in named groups."""
    ks = keys()
    return [("a switch's room", [s for k in ks for s in place(k.frame, R.mx_switch_room() + R.mx_switch_rim_room())]),
            ("a tile's pocket", [s for k in ks for s in place(k.frame, R.tile_room())]),
            ("a cap's sweep", C.cap_rooms()), ("a part's room", part_rooms())]


def body_cutters():
    return [s for _, group in body_cuts() for s in group]


@cached
def body():
    t = time.time()
    shell = add(subtract(C.body_shell(), [interior()]), [plates(), union([boss(p) for p in screw_points()]) ^ C.body_shell()])
    body = subtract(shell, body_cutters() + insert_holes() + recesses())
    body.num_tri()
    stage("body cuts", t)
    return body


# ---------------------------------------------------------------- the plinth
def screw_holes():
    return [h.translate((p[0], p[1], 0)) for p in screw_points() for h in R.screw_hole(screw_seat_z())]


def plate_cuts():
    return []


def cradles():
    """The Pro Micro's and the jack's cradles, kept inside the walls, and the
    reset switch's stop, which stands up into its slot in the wall."""
    held = place(part_frame("pro_micro"), R.mcu_cradle()) + place(part_frame("trrs"), R.jack_cradle())
    room = inside_prism(put_back_mm)
    return [s ^ room for s in held] + place(part_frame("reset"), R.reset_stop())


@cached
def plinth_shell():
    """The plinth before anything is cut from it: a flat plate on the desk up
    to plate_gap_mm under the seam, with the skirt bridging the outline's
    concave stretches (chassis.plinth_shell), and the screws' seats on it."""
    return add(C.plinth_shell(), seat_pads())


@cached
def bottom_plate():
    t = time.time()
    plate = add(subtract(plinth_shell(), screw_holes()), cradles())
    plate.num_tri()
    stage("plinth", t)
    return plate


# ---------------------------------------------------------------- the parts, for the assembly
def tiles():
    return C.at_keys(R.tile())


def electronics():
    drawn = [("pro_micro", R.pro_micro()), ("trrs", R.trrs_jack()), ("reset", R.reset_switch())]
    return [Piece(p.label, p.colour, placed(part_frame(name), p.solid)) for name, part in drawn for p in part]


def plugs():
    return [Piece(p.label, p.colour, placed(part_frame(name), p.solid))
            for name, part in (("pro_micro", R.usb_plug()), ("trrs", R.trrs_plug())) for p in part]


def parts(body, plate):
    return ([Piece("body", "burlywood", body), Piece("plinth", "peru", plate)]
            + C.switches() + C.keycaps() + tiles() + electronics())


# ---------------------------------------------------------------- checks
def part_clashes():
    groups = [C.switches(), tiles(), electronics(), C.keycaps(P.cap_travel_mm)]
    return C.clashes_of(groups, [(body(), "the body"), (bottom_plate(), "the plinth")])


def plug_clashes():
    return C.clashes_of([plugs()], [(body(), "the body"), (bottom_plate(), "the plinth")])


def headers_in_tiles():
    """The Dupont housings or the wires over them that meet a tile or a switch."""
    housings = union([p.solid for p in electronics() if p.label in ("Dupont housings", "the wires' room over the housings")])
    return [(p.label, v) for p in tiles() + C.switches() for v in [(p.solid ^ housings).volume()] if v > 1e-3]


def thin_tops():
    """What is cut from the body to within min_wall_mm of its top, as (what,
    volume mm^3): the switches' rooms and the caps' sweeps go out through the
    top, nothing else may come near it, the screws' insert holes included (the
    body is low over the thumb's outer corner)."""
    shell = C.body_shell()
    skin = shell - shell.translate((0, 0, -P.min_wall_mm))
    cuts = [(what, group) for what, group in body_cuts() if what not in ("a switch's room", "a cap's sweep")]
    return [(what, v) for what, group in cuts + [("a screw's insert hole", insert_holes())]
            for v in [sum((skin ^ s).volume() for s in group)] if v > 1e-6]


def screw_walls():
    return C.screw_walls_of(screw_points(), screw_seats(), body_cuts, plate_cuts, plinth_shell)


def checks():
    ok = True
    hits = C.cap_collisions()
    if hits:
        print("keycaps meet: " + ", ".join(f"{a} with {b} ({v:.2f} mm^3)" for a, b, v in hits))
        ok = False
    else:
        print("keycaps clear")
    _, hits = screw_walls()
    if hits:
        print("screw holes break into: " + ", ".join(f"{s} into {w} ({v:.2f} mm^3)" for s, w, v in hits))
        ok = False
    else:
        print("screw holes clear")
    faults = C.screw_length_faults()
    if faults:
        print(f"M2 x {P.screw_len_mm} screws don't fit: " + ", ".join(faults))
        ok = False
    else:
        print(f"M2 x {P.screw_len_mm} screws fit every insert")
    bare = thin_tops()
    if bare:
        print(f"under {P.min_wall_mm} mm of top: " + ", ".join(f"{w} ({v:.2f} mm^3)" for w, v in bare))
        ok = False
    else:
        print("every pocket and room stays under the top")
    v = (body() ^ bottom_plate()).volume()
    if v > 1e-6:
        print(f"body and plinth overlap ({v:.3f} mm^3)")
        ok = False
    else:
        print("body and plinth clear")
    clashes = part_clashes()
    if clashes:
        print("parts meet the case: " + ", ".join(f"{p} and {w} ({v:.2f} mm^3)" for p, w, v in clashes))
        ok = False
    else:
        print("switches, tiles, the Pro Micro with its Dupont housings, the jack, the reset switch and caps at full travel clear the case")
    clashes = plug_clashes()
    if clashes:
        print("plugs meet the case: " + ", ".join(f"{p} and {w} ({v:.2f} mm^3)" for p, w, v in clashes))
        ok = False
    else:
        print("the USB-C and TRRS plugs go in through the walls")
    hits = headers_in_tiles()
    if hits:
        print("Dupont housings meet: " + ", ".join(f"{p} ({v:.2f} mm^3)" for p, v in hits))
        ok = False
    else:
        print("the Dupont housings and their wires clear the tiles and switches")
    return ok


def report():
    ks = keys()
    (x0, y0), (x1, y1) = C.outline().min(axis=0), C.outline().max(axis=0)
    tops = [L.cap_top(k)[2] for k in ks]
    peak = max(float(xform(k.frame, [sx * (P.cap_top_mm[0] + (k.units - 1) * P.cap_unit_mm) / 2, sy * P.cap_top_mm[1] / 2,
                                     P.cap_bottom_above_plate_mm + P.cap_height_mm[k.cap_row - 1]])[2])
               for k in ks for sx in (-1, 1) for sy in (-1, 1))
    under = [min(float(xform(k.frame, c)[2]) for s, o in R.tile_boxes() for c in R.box_corners(s, o)) - plinth_top() for k in ks]
    b, j = R.mcu(), R.jack()
    usb = xform(part_frame("pro_micro"), [R.usb_mouth_x(), 0, b["board_mm"][2] + b["usb_mm"][2] / 2])[2]
    trrs = xform(part_frame("trrs"), [R.trrs_mouth_x(), 0, j["body_mm"][2] / 2])[2]
    reset = origin(part_frame("reset"))[2]
    (wall, screw, what), _ = screw_walls()
    slid = ", ".join(f"{name} {r2(t)}" for name, t in slides().items())
    return (f"cap tops {r2(min(tops))} to {r2(max(tops))} mm over the desk, the highest cap corner {r2(peak)} mm; plan "
            f"{r2(x1 - x0)} x {r2(y1 - y0)} mm, {round(polygon(C.outline()).area())} mm^2; plinth {r2(plinth_top())} mm thick, "
            f"the seam at {r2(seam())}; tiles {r2(min(under))} to {r2(max(under))} mm over the plinth; USB-C {r2(usb)} mm, "
            f"TRRS {r2(trrs)} mm and reset {r2(reset)} mm over the desk at their mouths; parts slid out {slid} mm; "
            f"{len(screw_points())} screws, least wall {r2(wall)} mm ({screw} to {what})")

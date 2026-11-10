"""The frame design's body and plinth: lowpro's keys, parts and height (the
layout, the seam and the plinth are chassis.py's) on the Capybara's open frame
(docs/editor-chassis.md): a rib along each finger column and the thumb row, a
rail round the outline on the plinth, and bridges between the ribs.

ribs() says which keys each rib runs through and how each of its ends finishes.
No rib end stands on the floor inside the rail, and nothing crosses the floor:
an end with no rail under it joins another rib's plate or stops at its plate,
tied by its bridges. With the plinth off, every socket, terminal and diode is
open from below (covered() checks it).

A rib is a band swept through its keys' plates, with a block under each plate
that holds the switch, the socket and the diode. The wires hang loose under
the bands (wires.py lays them). The controller, the battery, the power switch and the reset
button sit under a deck beside the inner column, walled by the rail, where
chassis.py's well puts them.

Every swept solid here is one mesh through a run of sections, each a quad of
world points (sweep).
"""
import math
from dataclasses import dataclass

import numpy as np
from manifold3d import Manifold, Mesh64

from . import chassis as C
from . import layout as L
from . import params as P
from . import parts as R
from .chassis import add, half_space, hull_of, placed, polygon, seam_z, subtract
from .layout import cached, key_named, keys
from .lib import axis_z, origin, r2, unit, xdir, xform
from .parts import Piece, union

OUTPUTS = ("body", "plate", "assembly")

UP = np.array([0.0, 0, 1])


# ---------------------------------------------------------------- the ribs
@dataclass(frozen=True)
class Drop:
    """The end turns down in a round and stands on the rail."""


@dataclass(frozen=True)
class Stop:
    """The end stops at its plate's edge."""


@dataclass(frozen=True)
class Join:
    """The end carries on in a web into `key`'s plate, at the edge that faces
    `edge` in that key's frame."""
    key: str
    edge: tuple


@dataclass(frozen=True)
class Rib:
    """A rib through `keys` in order, heading `along` in each key's frame, with
    how it finishes before the first key and after the last."""
    name: str
    keys: tuple
    along: tuple
    start: object
    end: object


def column(name, *extra):
    rows = range(P.rows_above, -P.rows_below - 1, -1)
    return tuple(f"{name}_{r}" for r in rows) + tuple(k for k in extra if P.thumb_extra)


def ribs():
    """The ribs. The finger columns run from the back to the front, the middle
    and ring ones on through the extra key in front of each. The inner
    column's front has no rail under it, so it carries on into the near thumb
    key's plate; the index column's front and the thumb row's near end stop at
    their plates."""
    back_to_front = (0, -1, 0)
    return [Rib("inner", column("inner"), back_to_front, Drop(), Join("thumb_near", (0, 1, 0))),
            Rib("index", column("index"), back_to_front, Drop(), Join("thumb_near", (1, 0, 0))),
            Rib("middle", column("middle", "thumb_x1"), back_to_front, Drop(), Drop()),
            Rib("ring", column("ring", "thumb_x2"), back_to_front, Drop(), Drop()),
            Rib("pinky", column("pinky"), back_to_front, Drop(), Drop()),
            Rib("thumb", ("thumb_near", "thumb_home", "thumb_far"), (-1, 0, 0), Stop(), Drop())]


# ---------------------------------------------------------------- sections and sweeps
@dataclass(frozen=True)
class Station:
    """A band's section: the middle of its top face, its unit across and its
    unit normal (out of the top), its heading and its width. The across is
    the normal crossed with the heading (station)."""
    p: np.ndarray
    across: np.ndarray
    normal: np.ndarray
    heading: np.ndarray
    width: float

    def side(self, side):
        """The top face's corner on `side` (-1 or 1) of across."""
        return self.p + side * self.across * self.width / 2

    def quad(self):
        """The section's corners: the top face's two, then the underside's."""
        n = self.normal * P.rib_mm
        return np.array([self.side(-1), self.side(1), self.side(1) - n, self.side(-1) - n])

    def edge(self, side):
        """The middle of the band's edge on `side` (-1 or 1) of across."""
        return self.side(side) - self.normal * P.rib_mm / 2


def station(p, normal, heading, width):
    return Station(p, np.cross(normal, heading), normal, heading, width)


def sweep(quads):
    """One solid through a run of four-cornered sections, each going the same
    way round: its sides between each section and the next, capped at both ends."""
    n = len(quads)
    v = np.concatenate(quads)
    tris = [(0, 1, 2), (0, 2, 3), (4 * n - 2, 4 * n - 3, 4 * n - 4), (4 * n - 1, 4 * n - 2, 4 * n - 4)]
    for i in range(n - 1):
        for j in range(4):
            a, b, c, d = 4 * i + j, 4 * i + (j + 1) % 4, 4 * i + 4 + j, 4 * i + 4 + (j + 1) % 4
            tris += [(a, d, b), (a, c, d)]
    tris = np.array(tris, np.uint32)
    if np.linalg.det(v[tris]).sum() < 0:
        tris = tris[:, ::-1]
    return Manifold(Mesh64(v, tris.astype(np.uint64)))


def bezier(c, s):
    """The cubic through control points c at s, and its derivative there."""
    b = (1 - s) ** 3 * c[0] + 3 * (1 - s) ** 2 * s * c[1] + 3 * (1 - s) * s ** 2 * c[2] + s ** 3 * c[3]
    d = 3 * (1 - s) ** 2 * (c[1] - c[0]) + 6 * (1 - s) * s * (c[2] - c[1]) + 3 * s ** 2 * (c[3] - c[2])
    return b, d


def steps(length):
    return max(2, math.ceil(length / P.rib_step_mm))


def ribbon(a, b):
    """The stations of a band from station a to station b. Each side of its top
    face is its own cubic, leaving along a's heading and arriving along b's, so
    the side on the inside of a turn is the shorter and neither folds; each
    section joins the two sides, square to their headings."""
    sides = []
    for side in (-1, 1):
        p, q = a.side(side), b.side(side)
        d = np.linalg.norm(q - p)
        sides.append([p, p + a.heading * d / 3, q - b.heading * d / 3, q])
    out = []
    for s in np.linspace(0, 1, steps(max(np.linalg.norm(c[3] - c[0]) for c in sides)) + 1):
        (p, dp), (q, dq) = bezier(sides[0], s), bezier(sides[1], s)
        across, t = unit(q - p), unit(dp + dq)
        t = unit(t - (t @ across) * across)
        out.append(Station((p + q) / 2, across, np.cross(t, across), t, float(np.linalg.norm(q - p))))
    return out


def plate_station(k, along, at):
    """Key k's plate's section `at` mm along the rib from its stem."""
    return station(xform(k.frame, np.array(along, float) * at), axis_z(k.frame), xdir(k.frame, along), P.rib_w_mm)


def round_down(s):
    """The stations of an end that runs on rib_lip_mm from station s and turns
    down: each side of the band turns over in its own upright plane, through
    rib_round_mm at the top face, so the end comes out heading straight down."""
    e = s.heading
    side = unit(np.cross(UP, e))
    up = np.cross(e, side)
    start = s.p + e * P.rib_lip_mm
    centre = start - P.rib_round_mm * up
    turn = math.atan2(up[2], -e[2])
    out = []
    for a in np.linspace(0, turn, steps(P.rib_round_mm * turn) + 1):
        radial = math.cos(a) * up + math.sin(a) * e
        normal = (s.normal @ up) * radial + (s.normal @ side) * side
        out.append(Station(centre + P.rib_round_mm * radial, s.across, normal, math.cos(a) * e - math.sin(a) * up, s.width))
    return out


def joined(s, join):
    """The stations of an end carried on from station s into a plate's edge."""
    k = key_named(join.key)
    out = np.array(join.edge, float)
    p = xform(k.frame, out * (P.rib_w_mm / 2 - P.rib_join_into_mm))
    return ribbon(s, station(p, axis_z(k.frame), -xdir(k.frame, out), s.width))


@dataclass(frozen=True)
class Band:
    """A rib's band: its sections' corners in order, its plan as far as its
    dropped ends' inner faces (the ends stand on the rail), and the station at
    the middle of each web, where a limb can stand."""
    rib: Rib
    quads: tuple
    plan: tuple
    webs: tuple


def outward(s):
    """Station s facing the other way along its rib."""
    return Station(s.p, -s.across, s.normal, -s.heading, s.width)


def finish(end, s):
    """What lies past station s, which heads out of its rib, for `end`: the
    stations, nearest first, the plan under them and the webs' middle stations."""
    if isinstance(end, Stop):
        return [], [], []
    if isinstance(end, Join):
        web = joined(s, end)
        return web[1:], [], [web[len(web) // 2]]
    turn = round_down(s)
    last = turn[-1].quad()
    return turn, [hull_of([s.quad()[0], s.quad()[1], last[2], last[3]])], []


def grounded(end, quad):
    """A dropped end's last section carried down below the seam."""
    return [np.c_[quad[:, :2], np.full(4, -1.0)]] if isinstance(end, Drop) else []


@cached
def bands():
    out = []
    half = P.rib_w_mm / 2
    for rib in ribs():
        stations, webs = [], []
        for i, k in enumerate(key_named(n) for n in rib.keys):
            a, b = plate_station(k, rib.along, -half), plate_station(k, rib.along, half)
            if i:
                web = ribbon(stations[-1], a)
                stations += web[1:-1]
                webs.append(web[len(web) // 2])
            stations += [a, b]
        before, plan0, webs0 = finish(rib.start, outward(stations[0]))
        after, plan1, webs1 = finish(rib.end, stations[-1])
        run = [outward(s) for s in before[::-1]] + stations + after
        level = [s.quad() for s in run if abs(s.heading[2]) < 0.5]
        plan = [hull_of(np.r_[a, b]) for a, b in zip(level[:-1], level[1:])] + plan0 + plan1
        quads = [s.quad() for s in run]
        quads = grounded(rib.start, quads[0]) + quads + grounded(rib.end, quads[-1])
        out.append(Band(rib, tuple(quads), tuple(plan), tuple(webs + webs0 + webs1)))
    return out


def band_solid(band):
    return sweep(band.quads)


# ---------------------------------------------------------------- the key blocks
def block_foot():
    """The block's foot along the key's y: min_wall_mm past the diode's pocket
    and past the socket."""
    south = R.diode_y() - P.diode_mm[1] / 2 - P.diode_room_mm - P.min_wall_mm
    north = P.socket_centre_mm[1] + P.socket_body_mm[1] / 2 + P.socket_clearance_mm + P.min_wall_mm
    return south, north


def block_points():
    """The block under a plate, in the key's frame: the plate's square down
    past the switch's housing, then in to its foot at the socket's underside."""
    h = P.rib_w_mm / 2
    south, north = block_foot()
    return ([(sx * h, sy * h, z) for sx in (-1, 1) for sy in (-1, 1) for z in (0, -P.switch_below_plate_mm)]
            + [(sx * h, y, R.socket_bottom_z()) for sx in (-1, 1) for y in (south, north)])


def block(k):
    return Manifold.hull_points([xform(k.frame, p) for p in block_points()])


def solder_wells(k):
    """Room round each of key k's socket terminals to solder to it, from the
    socket's top down and out through the block's side, where the wire comes in."""
    w, depth = P.solder_well_mm[1], P.socket_body_mm[2] + 10
    out = []
    for side in (-1, 1):
        tip = R.socket_tab_tip(side)
        s = 1 if tip[0] > 0 else -1
        x0, x1 = tip[0] - s * (P.solder_well_mm[0] - P.solder_well_reach_mm), s * (P.rib_w_mm / 2 + 1)
        out.append(placed(k.frame, R.box((abs(x1 - x0), w, depth), ((x0 + x1) / 2, tip[1], tip[2] - depth / 2))))
    return out


def diode_room(k):
    """Key k's diode's pocket, and a slot across the block's foot for its legs,
    both open below."""
    d, r, depth = P.diode_mm, P.diode_room_mm, 10
    z = R.diode_z() + d[1] / 2 + r
    pocket = R.box((d[0] + 2 * r, d[1] + 2 * r, depth), (0, R.diode_y(), z - depth / 2))
    legs = R.box((P.rib_w_mm + 2, P.diode_leg_slot_mm, depth), (0, R.diode_y(), R.diode_z() + P.diode_leg_slot_mm / 2 - depth / 2))
    return [placed(k.frame, pocket), placed(k.frame, legs)]


# ---------------------------------------------------------------- the outline
def bay_wall_rect():
    """The bay's plan with its walls: the rail's on the outside, and the wall
    on the keys' side."""
    (x0, y0), (x1, y1) = L.bay_outline_rect()
    return (x0 - P.wall_mm, y0 - P.wall_mm), (x1 + P.mcu_bay_wall_mm, y1 + P.wall_mm)


def outline_faces():
    """What the outline closes round (chassis.py outline_curve): the ribs'
    plan without their dropped ends, and the bay. The wall chassis.py draws
    round it is the rail, so a dropped end stands on the rail, flush with it."""
    faces = [C.bay_face(L.bay_outline_rect())]
    for band in bands():
        faces += band.plan
        faces += [hull_of([xform(key_named(n).frame, p) for p in block_points()]) for n in band.rib.keys]
    return C.fused(faces), [], []


def inside():
    return polygon(C.outline())


def above_seam(z=0.0, below=False):
    return half_space(L.seam_frame(), z, below=below, size=600)


def rail_slab():
    return above_seam() ^ above_seam(P.rail_h_mm, below=True)


def rail():
    q = inside()
    prism = lambda c: c.extrude(100).translate((0, 0, -20))
    return (prism(q) - prism(q.offset(-P.wall_mm))) ^ rail_slab()


def rail_point(p):
    """The middle of the rail's top nearest the plan point p, and how far the
    outline is from p."""
    q, inward = C.outline_stations()
    d = np.hypot(q[:, 0] - p[0], q[:, 1] - p[1])
    i = int(d.argmin())
    xy = q[i] + inward[i] * P.wall_mm / 2
    return np.array([xy[0], xy[1], float(seam_z(*xy)) + P.rail_h_mm]), float(d[i])


# ---------------------------------------------------------------- the bay
def deck_z():
    """The deck's underside and top, level over the desk: deck_wire_mm over the board."""
    under = float(origin(C.mcu_frame())[2]) + R.mcu_pcb_z() + P.mcu_board_mm[2] + P.deck_wire_mm
    return under, under + P.deck_mm


def level(z0, z1, size=600):
    return Manifold.cube((size, size, z1 - z0)).translate((-size / 2, -size / 2, z0))


def bay_block():
    """The bay before its rooms are cut: its walls and its deck, one block."""
    (x0, y0), (x1, y1) = bay_wall_rect()
    return (polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]) ^ inside()).extrude(100).translate((0, 0, -20)) ^ above_seam() ^ level(-20, deck_z()[1])


def bay_slot_spans():
    """The openings for the wires through the bay's wall on the keys' side, as
    (from, to) along the board from its port end: one beside each run of the
    board's holes that either half wires (params.py mcu_pins), half a pitch
    past the run's end holes. The wall stands between the runs."""
    used = sorted({hole for pins in P.mcu_pins.values() for _, hole in pins.values()})
    runs = [[used[0]]]
    for hole in used[1:]:
        runs = runs + [[hole]] if hole > runs[-1][-1] + 1 else runs[:-1] + [runs[-1] + [hole]]
    at = lambda hole: P.mcu_first_pin_mm + hole * P.mcu_pin_pitch_mm
    return [(at(run[0] - 0.5), at(run[-1] + 0.5)) for run in runs]


def bay_slots():
    """The openings as solids, through the wall at the board's -x in its own frame."""
    x = -(P.mcu_board_mm[0] / 2 + P.mcu_clearance_mm + P.mcu_bay_wall_mm / 2)
    return [placed(C.mcu_frame(), R.box((P.mcu_bay_wall_mm + 2, t - f, 60), (x, (f + t) / 2, 0))) for f, t in bay_slot_spans()]


def bay_cavities():
    """The board's room, the battery's and the lead notch between them, up to the deck."""
    under = level(-20, deck_z()[0])
    return [s ^ under for s in (placed(C.mcu_frame(), R.mcu_pocket(100)), C.floor_box(L.battery_bay(), 100),
                                C.floor_box(L.lead_notch(), 100))] + [s ^ under for s in bay_slots()]


def press_strip():
    """The strip down from the deck along the middle of the board, over it by
    mcu_press_gap_mm, which foam takes up."""
    (w, length), y0 = P.mcu_press_mm, P.mcu_press_start_mm
    z = R.mcu_pcb_z() + P.mcu_board_mm[2] + P.mcu_press_gap_mm
    return placed(C.mcu_frame(), R.box((w, length, 30), (0, y0 + length / 2, z + 15))) ^ level(-20, deck_z()[1])


def over_deck(p):
    (x0, y0), (x1, y1) = bay_wall_rect()
    return x0 < p[0] < x1 and y0 < p[1] < y1


# ---------------------------------------------------------------- limbs
def limb_foot(s, side):
    """Where a limb from the `side` edge of web station s stands: on the bay's
    deck where that is under the edge or just out from it, else on the rail
    where the outline is within limb_reach_mm, else nowhere."""
    p = s.edge(side)
    out = unit(np.r_[(side * s.across)[:2], 0])
    half = out * P.rib_mm / 2
    for d in np.arange(0, P.limb_reach_mm, 0.5):
        q = p + out * d
        if over_deck(q - half) and over_deck(q + half):
            return np.array([q[0], q[1], deck_z()[1]])
    foot, d = rail_point(p)
    return foot if d < P.limb_reach_mm else None


def limb(s, side, foot):
    """A limb from web station s's `side` edge down onto `foot`: leaving across
    the web, arriving upright, limb_w_mm wide along the rib."""
    p = s.edge(side) - side * s.across * P.rib_join_into_mm
    d = np.linalg.norm(foot - p)
    c = [p, p + side * s.across * d / 3, foot + UP * d / 3, foot - UP]
    quads = []
    for u in np.linspace(0, 1, steps(d) + 1):
        q, t = bezier(c, u)
        t = unit(t)
        along = unit(s.heading - (s.heading @ t) * t)
        thick = np.cross(t, along) * P.rib_mm / 2
        along = along * P.limb_w_mm / 2
        quads.append(np.array([q - along - thick, q + along - thick, q + along + thick, q - along + thick]))
    return sweep(quads)


@cached
def limbs():
    return [limb(s, side, foot) for band in bands() for s in band.webs for side in (-1, 1)
            for foot in [limb_foot(s, side)] if foot is not None]


# ---------------------------------------------------------------- bridges
@dataclass(frozen=True)
class Edge:
    """A plate's free edge: its key and rib, its middle, its unit direction,
    the unit way out of the plate and the plate's normal."""
    key: str
    rib: str
    mid: np.ndarray
    along: np.ndarray
    out: np.ndarray
    normal: np.ndarray


@cached
def free_edges():
    """Every plate's edges that no web leaves: both sides of each, and a
    stopped end's."""
    half = P.rib_w_mm / 2
    edges = []
    for rib in ribs():
        ks = [key_named(n) for n in rib.keys]
        ends = [(ks[0], -1, rib.start), (ks[-1], 1, rib.end)]
        for k in ks:
            t, n = xdir(k.frame, rib.along), axis_z(k.frame)
            a = np.cross(n, t)
            ways = [(side * a, t) for side in (-1, 1)] + [(s * t, a) for kk, s, end in ends if kk is k and isinstance(end, Stop)]
            edges += [Edge(k.name, rib.name, origin(k.frame) + out * half, along, out, n) for out, along in ways]
    return edges


def facing(a, b):
    """Where a bridge leaves edge a for edge b, as (point on a, point on b, the
    length of a that b lies beside), or None: the middle of that stretch."""
    turn = math.cos(math.radians(P.bridge_turn_deg))
    flat = lambda v: unit(np.r_[v[:2], 0])
    if flat(a.out) @ flat(b.out) > -turn or a.normal @ b.normal < turn:
        return None
    half, need = P.rib_w_mm / 2, P.bridge_w_mm / 2 + P.bridge_inset_mm
    ends = sorted((b.mid + s * half * b.along - a.mid) @ a.along for s in (-1, 1))
    lo, hi = max(ends[0], -half) + need, min(ends[1], half) - need
    if lo > hi:
        return None
    p = a.mid + a.along * (lo + hi) / 2
    q = b.mid + b.along * float(np.clip((p - b.mid) @ b.along, -half + need, half - need))
    gap = (q - p) @ a.out
    if not 0 < gap < P.bridge_reach_mm or np.linalg.norm(q - p) > P.bridge_reach_mm:
        return None
    return p, q, hi - lo + 2 * need


@cached
def bridge_spans():
    """Each bridge as (key, key, its stations). A free edge has one bridge at
    most, to the edge of another rib that it faces and lies most beside."""
    edges = free_edges()
    pairs = [(span, i, j) for i, a in enumerate(edges) for j, b in enumerate(edges[i + 1:], i + 1)
             if a.rib != b.rib for span in [facing(a, b)] if span is not None]
    taken, out = set(), []
    for (p, q, _), i, j in sorted(pairs, key=lambda pair: -pair[0][2]):
        if {i, j} & taken:
            continue
        taken |= {i, j}
        a, b = edges[i], edges[j]
        start = station(p - a.out * P.rib_join_into_mm, a.normal, a.out, P.bridge_w_mm)
        end = station(q - b.out * P.rib_join_into_mm, b.normal, -b.out, P.bridge_w_mm)
        out.append((a.key, b.key, ribbon(start, end)))
    return out


def bridge_solid(stations):
    return sweep([s.quad() for s in stations])


# ---------------------------------------------------------------- screws
def screw_boss_at(p):
    return R.cylinder(P.screw_boss_mm, 100, (p[0], p[1], -20)) ^ rail_slab()


def screw_bore():
    """The widest hole a screw needs, the insert's or the counterbore, with min_wall_mm round it."""
    return max(P.insert_d, R.counterbore_d()) + 2 * P.min_wall_mm


def screw_spot(i):
    """The plan point at outline station i where a boss stands: as far out as
    leaves the screw's holes their wall from the outline."""
    q, inward = C.outline_stations()
    return q[i] + inward[i] * (screw_bore() / 2 + 0.1)


@cached
def screw_points():
    """Where the plinth screws into the frame, in plan: bosses on the rail's
    inside, at the spots where the plinth is thick enough to sink the screw's
    head and the insert's hole and the screw's keep min_wall_mm from everything
    cut from the frame and the plinth, and from the outline. Going round the outline, each is the furthest such spot
    within frame_screw_gap_mm of the last, or the next one where none is, and
    none is nearer than frame_screw_least_mm to its neighbours."""
    q, _ = C.outline_stations()
    n = len(q)
    along = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.r_[q, q[:1]], axis=0), axis=1))]
    above, below = union(body_cutters()), union(plate_cutters())
    wide = screw_bore()

    def clear(i):
        p = screw_spot(i)
        z = float(seam_z(*p))
        return (z - P.plate_gap_mm >= P.screw_grip_mm + P.screw_head_h_mm and C.outline_distance(p) >= wide / 2
                and (R.cylinder(wide, P.insert_depth_mm + P.min_wall_mm, (p[0], p[1], z)) ^ above).is_empty()
                and (R.cylinder(wide, 60, (p[0], p[1], z - 60)) ^ below).is_empty())

    gap, least = P.frame_screw_gap_mm, P.frame_screw_least_mm
    spots = [i for i in range(n) if clear(i)]
    picked = [spots[0]]
    while along[-1] - along[picked[-1]] + along[picked[0]] > gap:
        on = along - along[picked[-1]]
        ahead = [i for i in spots if on[i] >= least and along[-1] - along[i] + along[picked[0]] >= least]
        if not ahead:
            break
        reach = [i for i in ahead if on[i] <= gap]
        picked.append(reach[-1] if reach else ahead[0])
    return [tuple(screw_spot(i)) for i in picked]


@cached
def screw_seats():
    return [float(seam_z(*p)) - P.plate_gap_mm for p in screw_points()]


def insert_holes():
    return [C.insert_hole_at(p, z) for p, z in zip(screw_points(), screw_seats())]


# ---------------------------------------------------------------- the body
@cached
def body_cuts():
    """Everything cut from the frame but the caps' rooms and the screws' insert
    holes, in named groups."""
    ks = keys()
    return [("a key's room", [C.key_room(k) for k in ks]), ("a solder well", [w for k in ks for w in solder_wells(k)]),
            ("a diode's room", [s for k in ks for s in diode_room(k)]), ("the bay", bay_cavities()),
            ("a bay room", C.bay_rooms())]


def body_cutters():
    return [s for _, group in body_cuts() for s in group]


def frame_parts():
    """The frame's solids before anything is cut from them, in named groups."""
    return [("a rib", [band_solid(b) for b in bands()]), ("a key's block", [block(k) for k in keys()]),
            ("a bridge", [bridge_solid(s) for _, _, s in bridge_spans()]), ("a limb", limbs()), ("the rail", [rail()]),
            ("the bay", [bay_block(), press_strip()]), ("a screw's boss", [screw_boss_at(p) for p in screw_points()])]


def filled(solid):
    """A solid without the bubbles shut inside it, which a web's twisting side
    leaves where it grazes the flat side of the block it runs from."""
    return Manifold.compose([p for p in solid.decompose() if p.volume() > 0])


@cached
def body():
    blank = filled(union([s for _, group in frame_parts() for s in group]))
    cut = subtract(blank, body_cutters() + C.cap_cuts() + insert_holes())
    return cut ^ above_seam() ^ inside().extrude(200).translate((0, 0, -20))


# ---------------------------------------------------------------- the plinth
def plinth_shell():
    return C.plinth_shell()


@cached
def plate_cuts():
    return [("a bay room", C.bay_rooms(plinth=True))]


def plate_cutters():
    return [s for _, group in plate_cuts() for s in group]


def screw_holes():
    return [h.translate((p[0], p[1], 0)) for p, z in zip(screw_points(), screw_seats()) for h in R.screw_hole(z)]


@cached
def bottom_plate():
    """The plinth: chassis.py's, up to the seam, with a boss under each socket
    and the board's rest, and no channels: the wires are all above the seam."""
    return add(subtract(plinth_shell(), plate_cutters() + screw_holes()), [C.socket_boss(k) for k in keys()] + [C.mcu_rest()])


def parts(body, plate):
    from . import wires
    return ([Piece("body", "burlywood", body), Piece("plinth", "peru", plate)]
            + C.switches() + C.keycaps() + C.sockets() + C.diodes() + C.electronics() + wires.pieces())


# ---------------------------------------------------------------- checks
def reached_from_below(k):
    """The ways up to key k's socket, terminals and diode with the plinth off:
    each carried down from where it sits, as its room in the block is cut (the
    socket square to the seam, the terminals and the diode down the key's axis)."""
    d = P.diode_mm
    return union([C.swept(k.frame, size, c) for size, c in R.socket_boxes()]
                 + [C.normal_swept(k.frame, size, c) for size, c in R.socket_tab_boxes()]
                 + [C.normal_swept(C.diode_frame(k), (d[1], d[0], d[1]), (0, 0, 0))])


def covered(case=None):
    """The keys whose socket, terminals or diode the frame lies under, so they
    can't be reached with the plinth off, as (key, overlap mm^3)."""
    case = body() if case is None else case
    return [(k.name, v) for k in keys() for v in [(reached_from_below(k) ^ case).volume()] if v > 1e-3]


def severed():
    """The bridges and limbs that the cuts leave less than half of, as (what, share left)."""
    spans = [(f"the bridge from {a} to {b}", bridge_solid(s)) for a, b, s in bridge_spans()]
    spans += [(f"limb {i + 1}", s) for i, s in enumerate(limbs())]
    return [(what, left) for what, s in spans for left in [(s ^ body()).volume() / s.volume()] if left < 0.5]


def crowded_terminals():
    """The keys where a wire doesn't fit beside a terminal, clear of the frame
    and the plinth."""
    r = P.wire_d_mm / 2
    ball = Manifold.sphere(r, 16)
    case = body() + bottom_plate()
    out = []
    for k in keys():
        for side in (-1, 1):
            tip = R.socket_tab_tip(side)
            s = 1 if tip[0] > 0 else -1
            at = xform(k.frame, (tip[0] + s * (r + P.wire_gap_mm), tip[1], R.socket_bottom_z() + r))
            if not (ball.translate(tuple(at)) ^ case).is_empty():
                out.append(k.name)
    return sorted(set(out))


def screw_walls():
    return C.screw_walls_of(screw_points(), screw_seats(), body_cuts, plate_cuts, plinth_shell)


def part_clashes():
    groups = [C.switches(), C.sockets(), C.diodes(), C.electronics(), C.keycaps(P.cap_travel_mm)]
    return C.clashes_of(groups, [(body(), "the frame"), (bottom_plate(), "the plinth")])


def checks():
    from . import wires
    ok = True

    def check(faults, bad, good):
        nonlocal ok
        print(bad + ": " + ", ".join(faults) if faults else good)
        ok = ok and not faults

    check([f"{a} with {b} ({v:.2f} mm^3)" for a, b, v in C.cap_collisions()], "keycaps meet", "keycaps clear")
    pieces = body().decompose()
    check([f"{len(pieces)} pieces"] if len(pieces) != 1 else [], "the frame is not one solid", "the frame is one solid")
    check([f"{k} ({v:.2f} mm^3)" for k, v in covered()], "the frame lies under the socket, terminals or diode of",
          "every socket, terminal and diode is open from below")
    check([f"{w} ({100 * left:.0f}% left)" for w, left in severed()], "cut through", "every bridge and limb holds")
    check(crowded_terminals(), f"no {P.wire_d_mm} mm wire fits beside a terminal at", "a wire fits beside every terminal")
    check(wires.unrouted(), f"no way for a {P.wire_d_mm} mm wire", f"every wire has a way: {wires.report()}")
    check([f"{s} into {w} ({v:.2f} mm^3)" for s, w, v in screw_walls()[1]], "screw holes break into", "screw holes clear")
    check(C.screw_length_faults(), f"M2 x {P.screw_len_mm} screws don't fit", f"M2 x {P.screw_len_mm} screws fit every insert")
    v = (body() ^ bottom_plate()).volume()
    check([f"{v:.3f} mm^3"] if v > 1e-6 else [], "frame and plinth overlap", "frame and plinth clear")
    check([f"{p} and {w} ({v:.2f} mm^3)" for p, w, v in part_clashes()], "parts meet the case",
          "switches, sockets, diodes, electronics and caps at full travel clear the case")
    check([f"{p} ({v:.2f} mm^3)" for p, v in C.blocked_parts(body())], "parts can't drop into the bay", "every part drops into the bay")
    wrong = C.true_part_clashes(body())
    if wrong or P.half == "left":
        check([f"{k} ({v:.2f} mm^3)" for k, v in wrong], "a real switch or socket doesn't fit the mirrored half at",
              "real switches and sockets fit the mirrored half")
    return ok


def report():
    ks = keys()
    q = C.outline()
    (x0, y0), (x1, y1) = q.min(axis=0), q.max(axis=0)
    tops = [L.cap_top(k)[2] for k in ks]
    plates = [origin(k.frame)[2] for k in ks]
    under = [xform(k.frame, [0, 0, R.socket_bottom_z()]) for k in ks]
    rise = [float(p[2] - seam_z(p[0], p[1])) for p in under]
    (wall, screw, what), _ = screw_walls()
    return (f"plate tops {r2(min(plates))} to {r2(max(plates))} mm over the desk; cap tops {r2(min(tops))} to {r2(max(tops))} mm; "
            f"sockets {r2(min(rise))} to {r2(max(rise))} mm over the plinth; plan {r2(x1 - x0)} x {r2(y1 - y0)} mm, "
            f"{round(polygon(q).area())} mm^2; {len(ribs())} ribs, {len(bridge_spans())} bridges, {len(limbs())} limbs, "
            f"{len(screw_points())} screws, least wall round one {r2(wall)} mm ({screw} to {what}); "
            f"frame {round(body().volume() / 1000, 1)} cm^3, plinth {round(bottom_plate().volume() / 1000, 1)} cm^3")

"""The frame design's matrix wires: where each wire of wire_d_mm runs, loose
under the ribs, from terminal to terminal and on to the controller's pad.

The matrix is lowpro/BUILD.md's: a row's wire joins its keys' row terminals, a
column's its keys' diodes' band legs, and the controller's pad for it
(params.py mcu_pins), as the tree that takes the least wire (nets).

A wire needs no clearance, but it can't pass into the frame, the plinth, a
part or another wire. The space a wire's centre may lie in is sampled every
wire_grid_mm: inside the outline, under the ribs' undersides, and a wire's
radius from the frame, the plinth, the bay's deck's top and every part
(space), and half a grid cell's diagonal more (slack), which makes up for the
sampling. Each wire is the cheapest way through that space clear of the wires
laid before it (the columns' first, then the rows'), pulled straight wherever
a straight run is clear and no dearer. A way costs its length, and up to
wire_tuck times more the further it hangs under what is over it, as far as
wire_tuck_mm: so a wire is tucked up under the frame where it can be, and the
next lies under it, which packs a gap from the top down.
"""
from dataclasses import dataclass

import numpy as np
from manifold3d import Manifold
from scipy import ndimage
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import breadth_first_order, dijkstra, minimum_spanning_tree

from . import chassis as C
from . import frame as F
from . import layout as L
from . import params as P
from . import parts as R
from .layout import cached, keys
from .lib import axis_z, origin, xform
from .parts import Piece, union

ROWS = {1: "RT", 0: "RH", -1: "RB"}
COLOURS = {"R": "dodgerblue", "C": "limegreen"}


# ---------------------------------------------------------------- the nets
def nets_of(k):
    """Key k's row net and column net."""
    if k.group == "finger":
        return ROWS[k.row], f"C{4 - k.col}"
    return "RX", f"C{k.col}"


def wire_side(k):
    """The side of key k, along its x, that its wires come to: the row
    terminal's and the diode's band leg's."""
    return -1 if k.group == "finger" else 1


def joints(k):
    """Where key k's row wire and column wire end, in world: against its row
    terminal's tip, and against its block's side at its diode's band leg."""
    r = P.wire_d_mm / 2
    tip = R.socket_tab_tip(wire_side(k))
    s = 1 if tip[0] > 0 else -1
    row = (tip[0] + s * r, tip[1], R.socket_bottom_z() + r)
    column = (s * (P.rib_w_mm / 2 + r), R.diode_y(), R.diode_z())
    return xform(k.frame, row), xform(k.frame, column)


def pad(net):
    """Where the net's wire ends on the controller: on the board's top, over
    its hole."""
    edge, hole = P.mcu_pins[P.half][net]
    x = (1 if edge else -1) * P.mcu_pin_rows_mm / 2
    z = R.mcu_pcb_z() + P.mcu_board_mm[2] + P.wire_d_mm / 2
    return xform(C.mcu_frame(), (x, P.mcu_first_pin_mm + hole * P.mcu_pin_pitch_mm, z))


def ends():
    """Each net's ends as {net: [(end's name, point), ...]}: the controller's
    pad first, then its keys' joints."""
    out = {}
    for k in keys():
        for net, p in zip(nets_of(k), joints(k)):
            out.setdefault(net, [("the controller", pad(net))]).append((k.name, p))
    return out


# ---------------------------------------------------------------- the space
@dataclass(frozen=True)
class Space:
    """The sampled space: the sample (i, j, k) is at low + step * (i, j, k),
    `shut` is true where a wire's centre can't lie, and `cost` is what a
    millimetre of wire costs there."""
    low: np.ndarray
    step: float
    shut: np.ndarray
    cost: np.ndarray

    def cell(self, p):
        return tuple(np.clip(np.rint((np.asarray(p) - self.low) / self.step).astype(int), 0, np.array(self.shut.shape) - 1))

    def point(self, cells):
        return self.low + self.step * np.asarray(cells, float)


def slack():
    """Half a grid cell's diagonal: how far a sample can be from the nearest
    point of anything between the samples."""
    return P.wire_grid_mm * 3 ** 0.5 / 2


def filled(section, x, y):
    """Which of the samples (x by y) a cross-section covers, even-odd along x."""
    turns = np.zeros((len(y), len(x) + 1), int)
    for loop in section.to_polygons():
        a, b = np.asarray(loop, float), np.roll(np.asarray(loop, float), -1, axis=0)
        cuts = (a[:, 1, None] <= y) != (b[:, 1, None] <= y)
        e, j = np.nonzero(cuts)
        at = a[e, 0] + (y[j] - a[e, 1]) * (b[e, 0] - a[e, 0]) / (b[e, 1] - a[e, 1])
        np.add.at(turns, (j, np.searchsorted(x, at)), 1)
    return (np.cumsum(turns, axis=1)[:, :-1] % 2 == 1).T


def roof(x, y):
    """How high a wire's centre may lie over each sample (x by y): a wire's
    radius under the underside of the band of the nearest key's plate."""
    X, Y = np.meshgrid(x, y, indexing="ij")
    ks = keys()
    o = np.array([origin(k.frame) for k in ks])
    n = np.array([axis_z(k.frame) for k in ks])
    near = np.argmin((X[..., None] - o[:, 0]) ** 2 + (Y[..., None] - o[:, 1]) ** 2, axis=-1)
    o, n = o[near], n[near]
    return o[..., 2] - (n[..., 0] * (X - o[..., 0]) + n[..., 1] * (Y - o[..., 1]) + P.rib_mm + P.wire_d_mm / 2) / n[..., 2]


def solids():
    """Everything a wire can't pass into: the frame, the plinth, the parts, and
    whatever is over the bay's deck."""
    (x0, y0), (x1, y1) = F.bay_wall_rect()
    over_deck = Manifold.cube((x1 - x0, y1 - y0, 100)).translate((x0, y0, F.deck_z()[1]))
    parts = C.switches() + C.sockets() + C.diodes() + C.electronics()
    return union([F.body(), F.bottom_plate(), over_deck] + [p.solid for p in parts])


def hang(shut):
    """How many open samples are over each sample before a shut one."""
    out = np.zeros(shut.shape, np.int32)
    for k in range(shut.shape[2] - 2, -1, -1):
        out[..., k] = np.where(shut[..., k + 1], 0, out[..., k + 1] + 1)
    return out


@cached
def space():
    g, r = P.wire_grid_mm, P.wire_d_mm / 2
    solid = solids()
    box = np.array(F.body().bounding_box())
    low = box[:3] - g
    x, y, z = (low[a] + g * np.arange(int((box[3 + a] - low[a]) / g) + 2) for a in range(3))
    full = np.stack([filled(solid.slice(float(h)), x, y) for h in z], axis=-1)
    near = ndimage.distance_transform_edt(~full, sampling=g) < r + slack()
    outside = ~filled(F.inside().offset(-r), x, y)
    shut = near | outside[..., None] | (z > roof(x, y)[..., None])
    return Space(low, g, shut, (1 + P.wire_tuck * np.minimum(hang(shut) * g / P.wire_tuck_mm, 1)).astype(np.float32))


# ---------------------------------------------------------------- routing
def ball(radius):
    """The cells within `radius` cells of one, as offsets."""
    n = int(radius)
    d = np.stack(np.meshgrid(*[np.arange(-n, n + 1)] * 3, indexing="ij"), axis=-1).reshape(-1, 3)
    return d[(d ** 2).sum(axis=1) <= radius ** 2]


def stamp(mask, cells, offsets, value):
    """Set the mask at every offset from every cell."""
    c = (np.asarray(cells)[:, None, :] + offsets[None]).reshape(-1, 3)
    c = c[((c >= 0) & (c < mask.shape)).all(axis=1)]
    mask[c[:, 0], c[:, 1], c[:, 2]] = value


def along(points, step):
    """Points no further than `step` apart along a polyline."""
    out = [np.asarray(points[0], float)[None]]
    for a, b in zip(points[:-1], points[1:]):
        n = max(1, int(np.ceil(np.linalg.norm(b - a) / step)))
        out.append(a + (b - a) * np.linspace(0, 1, n + 1)[1:, None])
    return np.concatenate(out)


STEPS = [(d, float(np.linalg.norm(d))) for d in ball(1.8) if tuple(d) > (0, 0, 0)]


def graph(open_, cost):
    """The open cells as a graph, each joined to those of its 26 neighbours
    that are open, as (the graph, each cell's node or -1)."""
    ids = np.full(open_.shape, -1)
    ids[open_] = np.arange(open_.sum())
    rows, cols, costs = [], [], []
    shape = np.array(open_.shape)
    for d, length in STEPS:
        lo, hi = np.maximum(-d, 0), np.maximum(shape - np.maximum(d, 0), np.maximum(-d, 0))
        here = tuple(slice(l, h) for l, h in zip(lo, hi))
        there = tuple(slice(l, h) for l, h in zip(lo + d, hi + d))
        both = (ids[here] >= 0) & (ids[there] >= 0)
        rows.append(ids[here][both])
        cols.append(ids[there][both])
        costs.append(length * (cost[here][both] + cost[there][both]) / 2)
    n = int(open_.sum())
    return coo_matrix((np.concatenate(costs), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr(), ids


def shortest(open_, cost, a, b):
    """The cheapest way from cell a to cell b through the open cells, as
    (cells, what the way costs as far as each, in cells); None when there is
    none."""
    g, ids = graph(open_, cost)
    dist, before = dijkstra(g, directed=False, indices=ids[a], return_predecessors=True)
    if not np.isfinite(dist[ids[b]]):
        return None
    cells = np.argwhere(open_)
    path, at = [], ids[b]
    while at >= 0:
        path.append(at)
        at = before[at]
    return cells[path[::-1]], dist[path[::-1]]


def straight(open_, cost, a, b):
    """What the straight run from cell a to cell b costs, in cells, or None
    when it leaves the open cells."""
    run = along([a.astype(float), b.astype(float)], 0.5)
    c = tuple(np.rint(run).astype(int).T)
    if not open_[c].all():
        return None
    return float(cost[c].mean() * np.linalg.norm(b - a))


def pulled(open_, cost, path, spent):
    """The path with every run pulled straight that can be: from each kept
    cell, on to the furthest cell with a straight run to it that is clear and
    costs no more than the path does between them."""
    out, i = [path[0]], 0
    while i < len(path) - 1:
        def pulls(j):
            run = straight(open_, cost, path[i], path[j])
            return run is not None and run <= spent[j] - spent[i]
        j = next(j for j in range(len(path) - 1, i, -1) if j == i + 1 or pulls(j))
        out.append(path[j])
        i = j
    return np.array(out)


def nearest_open(open_, cell, reach):
    """The open cell nearest `cell` within `reach` cells, or None."""
    lo = np.maximum(np.array(cell) - reach, 0)
    found = np.argwhere(open_[lo[0]:cell[0] + reach + 1, lo[1]:cell[1] + reach + 1, lo[2]:cell[2] + reach + 1]) + lo
    if not len(found):
        return None
    d = ((found - cell) ** 2).sum(axis=1)
    return tuple(found[d.argmin()]) if d.min() <= reach ** 2 else None


@dataclass(frozen=True)
class Wire:
    """One wire of a net, between two of its ends: its points, or None when
    there is no way for it."""
    net: str
    ends: tuple
    points: object

    def length(self):
        return float(np.linalg.norm(np.diff(self.points, axis=0), axis=1).sum())


def route(sp, taken, p, q, margin):
    """The wire's points from p to q clear of the cells `taken` (the other
    wires and every end's room), but for its own ends' rooms, where it meets
    the wires it is soldered beside. It is looked for within `margin` cells of
    the box round its ends; None for the whole space."""
    g = sp.step
    a, b = np.array(sp.cell(p)), np.array(sp.cell(q))
    shape = np.array(sp.shut.shape)
    lo = np.zeros(3, int) if margin is None else np.maximum(np.minimum(a, b) - margin, 0)
    hi = shape if margin is None else np.minimum(np.maximum(a, b) + margin + 1, shape)
    lo[2], hi[2] = 0, shape[2]
    window = tuple(slice(l, h) for l, h in zip(lo, hi))
    busy = taken[window].copy()
    stamp(busy, np.array([a - lo, b - lo]), ball(P.wire_end_room_mm / g), False)
    open_ = ~sp.shut[window] & ~busy
    reach = int(np.ceil(P.wire_end_room_mm / g))
    start, end = nearest_open(open_, a - lo, reach), nearest_open(open_, b - lo, reach)
    if start is None or end is None:
        return None
    way = shortest(open_, sp.cost[window], start, end)
    if way is None:
        return None
    return np.vstack([p, sp.point(pulled(open_, sp.cost[window], *way) + lo), q])


@cached
def nets():
    """Each net as (name, its wires), a wire as its two ends ((name, point),
    (name, point)), from the controller's pad outwards. A net's wires are the
    tree that joins its ends with the least wire, by how far apart the ends are
    going round what stands floor to roof between them (seen from above: a
    wire can pass a sample that is open at any height)."""
    sp = space()
    floor = ~sp.shut.all(axis=2, keepdims=True)
    g, ids = graph(floor, np.ones(floor.shape, np.float32))
    reach = int(np.ceil(P.wire_end_room_mm / sp.step))
    out = []
    for net, es in sorted(ends().items()):
        at = [ids[nearest_open(floor, np.array(sp.cell(p)[:2] + (0,)), reach)] for _, p in es]
        tree = minimum_spanning_tree(dijkstra(g, directed=False, indices=at)[:, at])
        order, before = breadth_first_order(tree, 0, directed=False)
        out.append((net, [(es[before[i]], es[i]) for i in order[1:]]))
    return out


@cached
def end_rooms():
    """The cells within wire_end_room_mm of any wire's end: the room to solder
    there, which only the wires that end there come into."""
    sp = space()
    rooms = np.zeros(sp.shut.shape, bool)
    stamp(rooms, np.array([sp.cell(p) for es in ends().values() for _, p in es]), ball(P.wire_end_room_mm / sp.step), True)
    return rooms


def beside(sp, taken, points):
    """Mark as taken every cell a wire's centre can't lie in beside the wire
    through `points`: those less than a wire's width from it."""
    d = P.wire_d_mm
    reach = int(np.ceil(d / sp.step))
    shape = np.array(taken.shape)
    run = along(points, 4.0)
    for a, b in zip(run[:-1], run[1:]):
        lo = np.maximum(np.array(sp.cell(np.minimum(a, b))) - reach, 0)
        hi = np.minimum(np.array(sp.cell(np.maximum(a, b))) + reach + 1, shape)
        c = sp.point(np.stack(np.meshgrid(*[np.arange(l, h) for l, h in zip(lo, hi)], indexing="ij"), axis=-1))
        ab = b - a
        t = np.clip(((c - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
        taken[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]] |= np.linalg.norm(c - a - t[..., None] * ab, axis=-1) < d


@cached
def wires():
    """Every wire: the nets in turn, the columns first, each from its pad outwards."""
    sp = space()
    taken = end_rooms().copy()
    out = []
    for net, pairs in sorted(nets(), key=lambda n: n[0][0] != "C"):
        for (a, p), (b, q) in pairs:
            points = next((pts for margin in (int(P.wire_search_mm / sp.step), None)
                           for pts in [route(sp, taken, p, q, margin)] if pts is not None), None)
            if points is not None:
                beside(sp, taken, points)
            out.append(Wire(net, (a, b), points))
    return out


def unrouted():
    return [f"{w.net} from {w.ends[0]} to {w.ends[1]}" for w in wires() if w.points is None]


# ---------------------------------------------------------------- the pieces
def tube(points):
    """A wire as a solid: a round run between each two points, a ball at each."""
    r = P.wire_d_mm / 2
    ball_ = Manifold.sphere(r, 12)
    return union([Manifold.batch_hull([ball_.translate(tuple(a)), ball_.translate(tuple(b))])
                  for a, b in zip(points[:-1], points[1:])])


def pieces():
    """Each net's wires as one piece, named for the net."""
    out = []
    for net, _ in nets():
        runs = [tube(w.points) for w in wires() if w.net == net and w.points is not None]
        if runs:
            out.append(Piece(f"wire {net}", COLOURS[net[0]], union(runs)))
    return out


def report():
    laid = [w for w in wires() if w.points is not None]
    return f"{len(laid)} wires, {round(sum(w.length() for w in laid) / 10) / 100} m"

"""The body: the key field's top surface blended from the key cells, walled,
a shell of one thickness, with the switch and socket pockets and the wire
channels; and the bottom plate: a plinth up to the body's underside, with
the socket bosses and the well for the controller and battery.

Everything here is in world axes (layout.py). The body's and the plinth's
blanks are meshes built here (the top surface, the underside and the round
sampled from their functions, the walls one vertical quad per outline
segment); everything cut from them or added to them is an exact Manifold
solid, and the booleans are Manifold's. The expensive results are cached,
see layout.reset().
"""
import math
import time

import numpy as np
import triangle
from manifold3d import CrossSection, FillRule, JoinType, Manifold, Mesh64, OpType
from scipy.interpolate import CubicSpline, RectBivariateSpline

from . import layout as L
from . import params as P
from . import parts as R
from .layout import cached, cell_corners, keys, key_named
from .lib import origin, r2, rinv, rot_z, trans, xform
from .parts import Piece, box_corners, segments, union

VERBOSE = False


def stage(label, t0):
    """Print how long a stage took, when VERBOSE."""
    if VERBOSE:
        print(f"  {label}: {time.time() - t0:.2f} s", flush=True)
    return time.time()


# ---------------------------------------------------------------- frames
def placed(m, solid):
    """A solid drawn in frame m, in world."""
    return solid.transform(m[:3])


def place(m, solids):
    return [placed(m, s) for s in solids]


def subtract(solid, tools):
    return Manifold.batch_boolean([solid] + list(tools), OpType.Subtract)


def add(solid, tools):
    return Manifold.batch_boolean([solid] + list(tools), OpType.Add)


# ---------------------------------------------------------------- the top surface
# A height field over the plan: inside a key's cell, its plate's plane; outside
# every cell, the nearby cells' planes blended by distance (inverse cube), each
# taken at its cell's nearest point, so no plane is extrapolated. The blend
# starts surface_blend_mm inside each cell, so where two cells of different
# heights abut it ramps between them over twice that rather than stepping; the
# cells' planes are put back exactly afterwards (plane_groups), which turns the
# ramp into a step at the higher cell's edge. The top surface is a quadratic
# spline through this field sampled every surface_step_mm (top_fit): taking
# each plane at its cell's nearest point creases the field along the lines
# that carry the cells' edges out, and the spline smooths those over a step.
# The body's underside is the same surface floor_drop() lower, the plate's
# top plate_gap_mm under that.
def field(x, y):
    """The key field's height over the world points (x, y) (arrays)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    D, Z = [], []
    for k in keys():
        inv = rinv(k.frame)
        o, n = origin(k.frame), k.frame[:3, 2]
        pz = o[2] - (n[0] * (x - o[0]) + n[1] * (y - o[1])) / n[2]
        lx = inv[0, 0] * x + inv[0, 1] * y + inv[0, 2] * pz + inv[0, 3]
        ly = inv[1, 0] * x + inv[1, 1] * y + inv[1, 2] * pz + inv[1, 3]
        sx, sy = k.cell[0] / 2, k.cell[1] / 2
        cx, cy = np.clip(lx, -sx, sx), np.clip(ly, -sy, sy)
        b = P.surface_blend_mm
        inside = np.maximum(np.abs(lx) - sx, np.abs(ly) - sy)   # negative inside, by how much
        D.append(np.where(inside <= -b, 0, np.hypot(lx - cx, ly - cy) + np.minimum(inside + b, b)))
        Z.append(k.frame[2, 0] * cx + k.frame[2, 1] * cy + k.frame[2, 3])
    D, Z = np.array(D), np.array(Z)
    w = 1 / np.maximum(D, 1e-6) ** 3
    core = D <= 0
    return np.where(core.any(0), np.where(core, Z, -1e9).max(0), (w * Z).sum(0) / w.sum(0))


def top_z(x, y):
    return float(field([x], [y])[0])


def floor_z(x, y):
    return top_z(x, y) - L.floor_drop()


def plate_z(x, y):
    return floor_z(x, y) - P.plate_gap_mm


@cached
def top_fit():
    """The top surface: a quadratic spline through the field sampled every
    surface_step_mm over the outline's bounds, a step past them all round."""
    st = P.surface_step_mm
    (x0, y0), (x1, y1) = outline().min(axis=0) - st, outline().max(axis=0) + st
    xs, ys = np.arange(x0, x1 + st, st), np.arange(y0, y1 + st, st)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    return RectBivariateSpline(xs, ys, field(X.ravel(), Y.ravel()).reshape(X.shape), kx=2, ky=2, s=0)


def top_surface(xy):
    """The top surface's height over the plan points xy (N x 2)."""
    return top_fit().ev(xy[:, 0], xy[:, 1])


def top_slope(xy):
    """The top surface's slope (dz/dx, dz/dy) over the plan points xy (N x 2)."""
    f = top_fit()
    return np.c_[f.ev(xy[:, 0], xy[:, 1], dx=1), f.ev(xy[:, 0], xy[:, 1], dy=1)]


# ---------------------------------------------------------------- the outline
def polygon(pts):
    return CrossSection([np.asarray(pts, float)[:, :2]], FillRule.NonZero)


def cell_face(k, grow=0):
    return polygon(cell_corners(k, grow))


def bay_points(b):
    return [(b[0][0], b[0][1]), (b[1][0], b[0][1]), (b[1][0], b[1][1]), (b[0][0], b[1][1])]


def bay_face(b):
    return polygon(bay_points(b))


def fused(faces):
    return CrossSection.batch_boolean(list(faces), OpType.Add)


def hull_of(points):
    """The convex hull of some plan points."""
    return CrossSection.hull_points(np.asarray([(p[0], p[1]) for p in points], float))


def circle_points(p, r, n=36):
    return [(p[0] + r * np.cos(a), p[1] + r * np.sin(a)) for a in np.linspace(0, 2 * np.pi, n, endpoint=False)]


def channel_points():
    """The channel paths in plan with min_wall_mm of wall round them, as the
    point sets of a stadium per segment."""
    r = P.min_wall_mm
    return [circle_points(a, w / 2 + r) + circle_points(b, w / 2 + r)
            for w, pts in channels() for a, b in zip(pts[:-1], pts[1:])]


def cells_2d():
    """The cells, the bays and the thumb keys' own routes in plan, before the wall."""
    routes = [hull_of(circle_points(a, w / 2) + circle_points(b, w / 2)) for w, pts in thumb_routes() for a, b in zip(pts[:-1], pts[1:])]
    return fused([cell_face(k) for k in keys()] + [bay_face(L.bay_rect())] + routes)


def hulls_2d():
    """The finger field (its cells and the bays) and the thumb cluster each as a
    convex hull, and the bridge joining them: the thumb row, the two bottom keys
    nearest it and the bays on the inner side, so the inner edge runs straight
    from the bays to the thumb."""
    bays = bay_points(L.bay_rect())
    finger = hull_of([c for k in keys() if k.group == "finger" for c in cell_corners(k)] + bays)
    thumb = hull_of([c for k in keys() if k.group != "finger" for c in cell_corners(k)])
    bridge = hull_of([c for k in keys() if k.group == "thumb" or (k.group == "finger" and k.col <= 1 and k.row == -P.rows_below)
                      for c in cell_corners(k)] + bays)
    return fused([finger, thumb, bridge])


def back_edge():
    """A hull along the back from the bay's corners to the middle column's top
    cell, its wall included, under one full-height arc: from the bay's back
    corner to the rearmost point of what it covers, the flattest arc between
    them that clears the column stagger and the back trunk, so nothing behind
    it leaves a crease."""
    (x0, _), (x1, y1) = L.bay_rect()
    corners = [(x0, y1), (x1, y1)] + [c for col in (0, 1, 2) for c in cell_corners(L.column_key(col, P.rows_above))[2:]]
    walls = [p for c in corners for p in circle_points(c, P.wall_mm)]
    under = np.array(walls + [p for pts in channel_points() for p in pts])
    a, b = np.array((x0, y1 + P.wall_mm)), under[np.argmax(under[:, 1])]
    half, mid = np.linalg.norm(b - a) / 2, (a + b) / 2
    along = (b - a) / (2 * half)
    up = np.array((-along[1], along[0]))
    u, v = (under - mid) @ along, (under - mid) @ up
    over = (np.abs(u) < half) & (v > 0)
    centre = mid + up * ((u[over] ** 2 + v[over] ** 2 - half ** 2) / (2 * v[over])).max()
    r = np.linalg.norm(a - centre)
    turn = np.linspace(*(np.arctan2(*(p - centre)[::-1]) for p in (a, b)), 64)
    return hull_of(walls + [tuple(centre + r * np.array((np.cos(t), np.sin(t)))) for t in turn])


def signed_area(pts):
    x, y = pts[:, 0], pts[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


@cached
def outline_curve():
    """The body's outline as a smooth closed curve: outline_style "hulls" is the
    hulls joined, "closed" the cells and bays closed up (gaps narrower than
    2 * outline_close_mm filled). Either way the gaps that remain get a round
    of outline_close_mm, the wall goes round it, the back edge is laid over it,
    the channels are kept min_wall_mm inside, the inside corners are rounded
    to what the wall leaves of outline_close_mm and the convex ones to
    outline_round_mm. The offsets leave a polygon of straight
    sides and arcs (as chords four times finer than mesh_tol_mm asks, or the
    spline bends too tightly at each chord's end for the top edge's round);
    the curve is a periodic cubic spline through points along it a tenth of
    mesh_mm apart, so that its normal turns smoothly where an arc meets a side.
    Returns the spline, over the polygon's length, counterclockwise."""
    s = hulls_2d() if P.outline_style == "hulls" else cells_2d()
    def offset(s, amount):
        return s.offset(amount, JoinType.Round, 2.0, 4 * segments(abs(amount)))

    for amount in (P.outline_close_mm, -P.outline_close_mm, P.wall_mm):
        s = offset(s, amount)
    s = fused([s, back_edge()] + [hull_of(pts) for pts in channel_points()])
    inside = P.outline_close_mm - P.wall_mm
    for amount in (inside, -inside, -P.outline_round_mm, P.outline_round_mm):
        s = offset(s, amount)
    piece = max(s.decompose(), key=lambda c: c.area())
    pts = max((np.asarray(c, float) for c in piece.to_polygons()), key=signed_area)
    pts = np.r_[pts, pts[:1]]
    along = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    s = np.linspace(0, along[-1], math.ceil(along[-1] / (P.mesh_mm / 10)) + 1)
    samples = np.c_[np.interp(s, along, pts[:, 0]), np.interp(s, along, pts[:, 1])]
    samples[-1] = samples[0]
    return CubicSpline(s, samples, bc_type="periodic", axis=0)


@cached
def outline_stations():
    """The stations along the outline the walls and the top edge's round are
    built on: no further apart than mesh_mm, nor so far that the chord between
    two leaves the curve by more than mesh_tol_mm. Returns their points and
    the outline's inward normals there (each N x 2)."""
    curve = outline_curve()
    s = np.linspace(0, curve.x[-1], len(curve.x) * 4)
    d1, d2 = curve(s, 1), curve(s, 2)
    bend = np.abs(d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]) / np.linalg.norm(d1, axis=1) ** 3
    step = np.minimum(P.mesh_mm, np.sqrt(8 * P.mesh_tol_mm / np.maximum(bend, 1e-9)))
    count = np.r_[0, np.cumsum(np.diff(s) / step[1:])]
    n = math.ceil(count[-1])
    at = np.interp(np.arange(n) * count[-1] / n, count, s)
    d = curve(at, 1)
    return curve(at), np.c_[-d[:, 1], d[:, 0]] / np.linalg.norm(d, axis=1)[:, None]


def outline():
    """The outline as a counterclockwise polygon through its stations (N x 2)."""
    return outline_stations()[0]


def outline_distance(p):
    """The plan distance from the point p to the outline."""
    a = outline()
    b = np.roll(a, -1, axis=0)
    d = b - a
    t = np.clip(((p[0] - a[:, 0]) * d[:, 0] + (p[1] - a[:, 1]) * d[:, 1]) / (d * d).sum(1), 0, 1)
    return float(np.hypot(a[:, 0] + t * d[:, 0] - p[0], a[:, 1] + t * d[:, 1] - p[1]).min())


# ---------------------------------------------------------------- the rounded top edge
# The round between the vertical wall and the top is a rolling ball's. At each
# station q on the outline the ball's centre is top_round_mm inside the wall
# (along the outline's inward normal there) and top_round_mm under the top
# along the top's normal at the ball's top contact p: p is found by iterating
# p = centre's plan + top_round_mm * the top's normal's plan at p, which
# converges wherever the top is convex on a radius larger than the ball. The
# wall contact is level with the centre, and the section between the two
# contacts is the circular arc about the centre, sampled to mesh_tol_mm; the
# arcs at neighbouring stations are joined by quads. The wall below the wall
# contacts is one vertical quad per outline segment.
@cached
def round_sections():
    """The rolling ball's section at each outline station, as (N, m, 3): m points
    from the wall contact (on the outline, level with the ball's centre) along
    the arc to the top contact (on the top surface)."""
    (q, inward), r = outline_stations(), P.top_round_mm
    if r <= 0:
        return np.c_[q, top_surface(q)][:, None, :]
    # The top contact under each ball centre a, found by fixed-point steps that
    # shrink by r times the top's curvature there: they converge while the
    # top's convex radius is larger than r, and stop shrinking where it isn't.
    a = q + r * inward
    p, last = a.copy(), np.inf
    while True:
        g = top_slope(p)
        s = np.sqrt(1 + (g * g).sum(1))
        moved = np.linalg.norm(a - r * g / s[:, None] - p, axis=1)
        p = a - r * g / s[:, None]
        if moved.max() < 1e-9:
            break
        if moved.max() >= last:
            x, y = a[moved.argmax()]
            raise ValueError(f"the top edge's round: top_round_mm {r} is larger than the top's convex radius near ({x:.1f}, {y:.1f})")
        last = moved.max()
    g = top_slope(p)
    s = np.sqrt(1 + (g * g).sum(1))
    top = np.c_[p, top_surface(p)]
    centre = np.c_[a, top[:, 2] - r / s]
    wall = np.c_[q, centre[:, 2]]
    floor = top_surface(q) - L.floor_drop()
    if (wall[:, 2] <= floor).any():
        x, y = q[(wall[:, 2] - floor).argmin()]
        raise ValueError(f"the top edge's round: top_round_mm {r} reaches under the body's underside at ({x:.1f}, {y:.1f})")
    d0, d1 = wall - centre, top - centre
    cos = np.clip((d0 * d1).sum(1) / r / r, -1, 1)
    ang = np.arccos(cos)
    perp = d1 - d0 * cos[:, None]
    perp *= r / np.linalg.norm(perp, axis=1)[:, None]
    m = 1 + math.ceil(ang.max() / (2 * math.acos(1 - P.mesh_tol_mm / r)))
    f = ang[:, None] * np.linspace(0, 1, m)[None, :]
    rows = centre[:, None, :] + d0[:, None, :] * np.cos(f)[..., None] + perp[:, None, :] * np.sin(f)[..., None]
    rows[:, 0], rows[:, -1] = wall, top
    # Every row of the round runs round the outline the same way as the
    # outline: a step backwards is the round folding over itself, at a convex
    # corner too tight for it where the top tilts toward the edge.
    dq = np.roll(q, -1, axis=0) - q
    for j in range(1, m):
        step = np.roll(rows[:, j, :2], -1, axis=0) - rows[:, j, :2]
        back = (step * dq).sum(1) <= 0
        if back.any():
            x, y = q[back.argmax()]
            raise ValueError(f"the top edge's round folds at ({x:.1f}, {y:.1f}): top_round_mm {r} is too large for "
                             f"outline_round_mm {P.outline_round_mm} where the top tilts toward the edge")
    contact = top[:, :2]
    if abs(polygon(contact).area() - signed_area(contact)) > 1e-6 * abs(signed_area(contact)):
        raise ValueError(f"the top edge's round crosses itself: top_round_mm {r} is too large for this outline")
    return rows


def top_contact_2d():
    """The plan inside the top edge's round, where the top surface is the top."""
    return polygon(round_sections()[:, -1, :2])


# ---------------------------------------------------------------- the blanks
def plan_mesh(boundary, fill=True):
    """A triangulation of a counterclockwise plan polygon (N x 2) whose sides it
    keeps whole, with points inside about mesh_mm apart (fill) or none. Returns
    the vertices, the polygon's first, and the triangles, counterclockwise."""
    n = len(boundary)
    sides = np.c_[np.arange(n), (np.arange(n) + 1) % n]
    opts = "pYQ" + (f"q25a{0.5 * P.mesh_mm ** 2:.6f}" if fill else "")
    out = triangle.triangulate({"vertices": boundary, "segments": sides}, opts)
    v, t = out["vertices"], out["triangles"]
    if len(v) < n or not np.array_equal(v[:n], boundary):
        raise RuntimeError("the plan's triangulation lost the outline's points")
    e1, e2 = v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]]
    cw = e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0] < 0
    t[cw] = t[cw][:, ::-1]
    return v, t


def walled(ring_lo, ring_hi):
    """The quads, as triangles, from a ring of vertex indices up to another over
    the same stations round a counterclockwise polygon, facing out of it."""
    a, b = ring_lo, ring_hi
    a1, b1 = np.roll(a, -1), np.roll(b, -1)
    return np.r_[np.c_[a, a1, b1], np.c_[a, b1, b]]


def solid_from(vertices, triangles, what):
    solid = Manifold(Mesh64(np.ascontiguousarray(vertices, float), np.ascontiguousarray(triangles, np.uint64)))
    if solid.status().name != "NoError":
        raise RuntimeError(f"the {what} is not a closed manifold mesh ({solid.status().name})")
    return solid


# The body's and the plinth's blanks are each one closed mesh, and their
# outer walls are built here and nothing cuts them afterwards except what is
# meant to go through the wall (the USB opening, the power switch's knob):
# each wall is one vertical quad per outline segment, its corners on the
# stations, so it is exactly vertical. Both blanks' undersides and tops over
# the plan are one triangulation of the outline (plan): the body's underside
# is the top surface floor_drop() lower on it, and the plinth's top the same
# plate_gap_mm lower, vertex for vertex.
@cached
def plan():
    """The plan inside the outline, triangulated: its vertices (the outline's
    stations first) and triangles."""
    return plan_mesh(outline())


def body_blank():
    """The body's blank: its vertices the underside's (the outline's stations
    first), the round's sections (the first of each on the outline, level with
    the ball's centre: the wall's top), then the top's inside the round."""
    t = time.time()
    q = outline()
    n = len(q)
    rows = round_sections()
    m = rows.shape[1]
    vu, tu = plan()
    u = len(vu)
    vi, ti = plan_mesh(rows[:, -1, :2])
    station = np.arange(n)
    ring = [u + station * m + j for j in range(m)]
    top = np.where(ti < n, u + ti * m + m - 1, u + n * m + ti - n)
    vertices = np.r_[np.c_[vu, top_surface(vu) - L.floor_drop()], rows.reshape(-1, 3),
                     np.c_[vi[n:], top_surface(vi[n:])]]
    triangles = [tu[:, ::-1], walled(station, ring[0])] + [walled(ring[j], ring[j + 1]) for j in range(m - 1)] + [top]
    blank = solid_from(vertices, np.concatenate(triangles), "body's blank")
    stage("the body's blank", t)
    return blank


def plinth_blank():
    """The plinth's blank: from the desk up to the body's underside lowered
    plate_gap_mm."""
    q = outline()
    n = len(q)
    vu, tu = plan()
    u = len(vu)
    z = top_surface(vu) - L.floor_drop() - P.plate_gap_mm
    if z.min() <= 0:
        x, y = vu[z.argmin()]
        raise ValueError(f"the plinth's top reaches the desk at ({x:.1f}, {y:.1f})")
    _, tb = plan_mesh(q, fill=False)
    station = np.arange(n)
    vertices = np.r_[np.c_[vu, z], np.c_[q, np.zeros(n)]]
    return solid_from(vertices, np.r_[tu, u + tb[:, ::-1], walled(u + station, station)], "plinth's blank")


# Every cell's plane is put back exactly, cell_step_mm past its edge: over the
# cell, whatever the body's blank has above the plane is cut away and a block
# under it added, and likewise under the plane floor_drop() lower (the
# underside), which the plinth's top follows (plinth_shell). Where two cells overlap, so the
# top steps at the higher cell's edge (with nothing left standing in the gap)
# and the underside at the lower's. Inside a cell a blank's surface lies on the
# plane to within rounding, and a boolean between faces that nearly coincide
# leaves slivers, so the cuts start put_back_mm inside the block, and they are
# ring_mm narrower than the blocks so that no face of a cut lies on a face of a
# block: the blocks meet the blanks in volumes, and where a blank stands higher
# than the plane at the cell's edge the step comes ring_mm inside it. Keys whose
# plates share a plane share one block.
put_back_mm = 0.1
ring_mm = 0.01


def plane_groups():
    """The keys grouped by their plates' planes."""
    groups = []
    for k in keys():
        for g in groups:
            m = g[0].frame
            if np.abs(k.frame[:3, 2] - m[:3, 2]).max() < 1e-9 and abs(m[:3, 2] @ (origin(k.frame) - origin(m))) < 1e-9:
                g.append(k)
                break
        else:
            groups.append([k])
    return groups


def column(group, grow):
    """The group's cells, `grow` past their edges, as a vertical column from z = -2 up."""
    return fused([cell_face(k, grow) for k in group]).extrude(203).translate((0, 0, -2))


def half_space(m, z, below=True, size=200):
    """Everything in frame m below (or above) its plane z, within `size`."""
    return placed(m, Manifold.cube((size, size, size)).translate((-size / 2, -size / 2, z - size if below else z)))


def slab(m, z_top, z_bottom, size=200):
    """Everything in frame m between its planes z_bottom and z_top, within `size`."""
    return placed(m, Manifold.cube((size, size, z_top - z_bottom)).translate((-size / 2, -size / 2, z_bottom)))


@cached
def body_shell():
    """The body before anything is cut from it: its blank, every cell's plane put back."""
    t = time.time()
    reach = fused([cell_face(k, P.cell_step_mm) for k in keys()]) - top_contact_2d()
    if reach.area() > 1e-6:
        x0, y0, _, _ = reach.bounds()
        raise ValueError(f"a cell's plane reaches the top edge's round near ({x0:.1f}, {y0:.1f}): "
                         "top_round_mm is too large for wall_mm")
    d, cut, block = L.floor_drop(), P.cell_step_mm - ring_mm, P.cell_step_mm
    caps = [column(g, cut) ^ half_space(g[0].frame, -put_back_mm, below=False) for g in plane_groups()]
    caps += [column(g, cut) ^ half_space(g[0].frame, -d + put_back_mm) for g in plane_groups()]
    blocks = [column(g, block) ^ slab(g[0].frame, 0, -d) for g in plane_groups()]
    shell = add(subtract(body_blank(), caps), blocks)
    stage("the body's shell", t)
    return shell


@cached
def plinth_shell():
    """The plinth before anything is cut from it: its blank, with every cell's
    plane under the body put back as the body's underside has it, lowered
    plate_gap_mm: everything over each cell's plane taken away and everything
    under it added (from put_back_mm over the desk), so the plinth's top steps
    where the underside does, and where two cells' columns overlap it is the
    lower plane's, as the underside is."""
    t = time.time()
    d = L.floor_drop()
    z = -d - P.plate_gap_mm
    floor = Manifold.cube((400, 400, 100)).translate((-200, -200, put_back_mm))
    fill = [column(g, P.cell_step_mm - ring_mm) ^ half_space(g[0].frame, z + put_back_mm) ^ floor
            for g in plane_groups()]
    clear = [column(g, P.cell_step_mm) ^ half_space(g[0].frame, z, below=False) for g in plane_groups()]
    shell = add(subtract(add(plinth_blank(), fill), clear), [skirt()])
    stage("the plinth's shell", t)
    return shell


# ---------------------------------------------------------------- the skirt
# The plinth alone fills the outline's concave stretches, low down: a disc of
# skirt_radius_mm rolled round the outside (the outline closed by it) bridges
# each with one arc, tangent to the corners either side, and can't leave the
# convex hull. The skirt is flat at skirt_h_mm, and meets the plinth's wall in a
# rolling-ball cove of skirt_cove_mm.
@cached
def skirt_faces():
    """The skirt in plan: the closed outline, and the spaces it adds to the
    outline (past a hair, which drops the slivers along the rest of the wall)."""
    r = P.skirt_radius_mm
    out = polygon(outline())
    closed = out.offset(r, JoinType.Round, 2.0, segments(r)).offset(-r, JoinType.Round, 2.0, segments(r))
    return closed, fused([p for p in (closed - out.offset(0.05, JoinType.Round, 2.0, 8)).decompose() if p.area() > 1])


def cove_ring():
    """The cove's section swept round the whole outline, a closed ring of mesh:
    from inside the plinth's wall out past the cove, along the skirt's top and
    up the arc to the wall."""
    c, h = P.skirt_cove_mm, P.skirt_h_mm
    reach = c + 0.5
    if reach >= P.outline_close_mm - P.wall_mm:
        raise ValueError(f"skirt_cove_mm {c} is too large for the outline's inside corners")
    a = np.radians(np.linspace(-90, -180, segments(c) // 4 + 1))
    section = np.r_[[(-0.5, 0), (reach, 0), (reach, h)], np.c_[c + c * np.cos(a), h + c + c * np.sin(a)],
                    [(-0.5, h + c)]]
    q, inward = outline_stations()
    n, m = len(q), len(section)
    v = (q[:, None, :] - section[None, :, :1] * inward[:, None, :]).reshape(-1, 2)
    v = np.c_[v, np.tile(section[:, 1], n)]
    rings = np.arange(n * m).reshape(n, m)
    t = [walled(rings[:, i], rings[:, (i + 1) % m]) for i in range(m)]
    return solid_from(v, np.concatenate(t), "skirt's cove")


def skirt():
    """The skirt as a solid, flat with the cove along the wall, lapping into the
    plinth (whose wall stands higher here: the body and plinth check would
    catch one that didn't) so the two are one solid."""
    closed, gaps = skirt_faces()
    lapped = gaps.offset(1, JoinType.Round, 2.0, 16) ^ closed
    return union([lapped.extrude(P.skirt_h_mm), cove_ring() ^ lapped.extrude(100)])


# ---------------------------------------------------------------- the bay's well
def bay_pocket_h():
    """The pocket height the parts need over the well's floor."""
    return max(P.mcu_parts_mm + P.mcu_board_mm[2] + P.mcu_clearance_mm,
               P.battery_mm[2] + P.battery_clearance_mm)


@cached
def bay_z():
    """The well's floor: bay_under_mm below the parts' room under the lowest point
    of the body's underside over the bays, but never thinner than the plate's minimum."""
    lows = [floor_z(b[0][0] + (b[1][0] - b[0][0]) * i / 4, b[0][1] + (b[1][1] - b[0][1]) * j / 4)
            for b in L.bays() for i in range(5) for j in range(5)]
    return max(P.bottom_plate_mm, min(lows) - bay_pocket_h() - P.bay_under_mm)


def mcu_frame():
    return trans([0, 0, bay_z()]) @ L.mcu_frame()


def battery_frame():
    return trans([0, 0, bay_z()]) @ L.battery_frame()


def power_switch_frame():
    """The switch in the plinth, just under the body's underside over all of it."""
    m, s = L.power_switch_frame(), P.power_switch_mm
    z = min(floor_z(*xform(m, [i * s[0] / 2, j * s[1] / 2, 0])[:2]) for i in (-1, 1) for j in (-1, 1))
    return trans([0, 0, z - s[2] / 2 - P.power_switch_clearance_mm]) @ m


def floor_box(r, h):
    """The plan rectangle r ((x0, y0), (x1, y1)) from the well's floor up h."""
    return Manifold.cube((r[1][0] - r[0][0], r[1][1] - r[0][1], h)).translate((r[0][0], r[0][1], bay_z()))


def well():
    """The well: both bays' rectangles and the battery's lead notch between
    them, open from the well's floor up through the plate's top (the body
    takes the parts' rooms, bay_rooms, where they reach above it)."""
    return [floor_box(b, 100) for b in L.bays() + [L.lead_notch()]]


# ---------------------------------------------------------------- wiring points
# In a key's frame, at the socket's top: the column channel's centre (col_x),
# the column wire's line past the -x tab (lane_x), a thumb diode's line (diode_x),
# the line over the +x tab (row_x), and the north edge (ne_y).
def socket_end_x():
    return P.socket_centre_mm[0] - P.socket_body_mm[0] / 2


def lane_x():
    """The column wire's line, beside the -x terminal's tip."""
    return socket_end_x() - P.socket_tab_mm[0] - P.wire_gap_mm - P.wire_d_mm / 2


def diode_x():
    """A thumb key's diode's line, as close to the socket as its room's clearance allows."""
    return socket_end_x() - P.socket_clearance_mm - P.diode_mm[1] / 2


def diode_y():
    """A finger key's diode's line across the key, south of the centre post's hole."""
    return -P.switch_centre_post_d / 2 - P.post_clearance_mm - P.socket_clearance_mm - P.diode_room_mm - P.diode_mm[1] / 2


def leg_x():
    """The line a finger diode's +x leg runs north along, past the side post's hole."""
    return P.switch_side_post_x + P.switch_side_post_d / 2 + P.post_clearance_mm + P.diode_room_mm + P.diode_leg_slot_mm / 2


def thumb_diode_y():
    """A thumb key's diode's centre, in its riser over the column tab."""
    return (P.socket_tab_y[0] + ne_y()) / 2 + 1


def thumb_leg_y():
    """The line a thumb diode's north leg turns along: its straight lead past the
    diode's end, and the bend."""
    return thumb_diode_y() + P.diode_mm[0] / 2 + P.diode_lead_mm + 0.35


def thumb_joint():
    """A thumb diode's north leg and its sleeved joint to the wire, along the key
    from the diode's line, as a box's size and centre: the leg lies along its
    north side, the wire's core south of that."""
    n, w = P.thumb_joint_mm
    return (n, w, w), (diode_x() + n / 2, thumb_leg_y() + 0.4 - w / 2, R.socket_top_z() - P.diode_mm[1] / 2 - P.diode_room_mm)


def column_w():
    """A column channel's width: from the socket's shaft, overlapping it so no
    sliver is left between them under the tent, out past the wire beside the tip."""
    return shaft_edge_x() - lane_x() + P.wire_d_mm / 2


def shaft_edge_x():
    return socket_end_x() - P.socket_clearance_mm + 0.1


def col_x():
    return shaft_edge_x() - column_w() / 2


def row_x():
    return P.socket_centre_mm[0] + P.socket_body_mm[0] / 2 + P.socket_tab_mm[0]


def ne_y():
    return P.cell_mm / 2 - P.channel_w_mm / 2


def out_y():
    """A trunk's corner point just past a cell's +x edge."""
    return P.cell_mm / 2 + 1.5


def trunk_y(side):
    """A trunk's line across its end cell, in the key's frame: the back trunk
    (side 1) just north of the socket's room, the front trunk (side -1) south
    of the diode's pocket by front_trunk_wall_mm. The end rows lean, so at this
    depth these lines lie further out in plan than they do in the frame, and
    the trunk, which stands square to the desk, leans in under the pocket."""
    if side > 0:
        return P.socket_centre_mm[1] + P.socket_body_mm[1] / 2 + P.socket_clearance_mm + P.trunk_w_mm / 2
    return diode_y() - P.diode_mm[1] / 2 - P.diode_room_mm - P.front_trunk_wall_mm - P.trunk_w_mm / 2


def at(k, p):
    return xform(k.frame, [p[0], p[1], R.socket_top_z()])


def c_tab(k):
    return at(k, (col_x(), P.socket_tab_y[0]))


def x_tab(k):
    """The +x tab: a thumb key's row wire comes to it."""
    return at(k, (row_x(), P.socket_tab_y[1]))


def riser_x(k):
    """Key k's column line at its terminal: a thumb key's is the diode's, as no wire passes it."""
    return col_x() if k.group == "finger" else diode_x()


def riser(k):
    """A thumb key's column channel, from its terminal to its north edge."""
    return [at(k, (riser_x(k), P.socket_tab_y[0])), at(k, (riser_x(k), ne_y()))]


def joint_run(k):
    """A channel along a thumb key's north edge, north enough to hold the diode's
    leg and sleeved joint (see thumb_joint), then easing the wire over to the
    edge's own line."""
    y = thumb_leg_y() + 0.4 - P.channel_w_mm / 2
    x = riser_x(k) + P.thumb_joint_mm[0]
    return [at(k, (riser_x(k), y)), at(k, (x, y)), at(k, (x + P.thumb_ease_mm, ne_y()))]


def nw(k):
    return at(k, (col_x(), ne_y()))


def ne(k):
    return at(k, (row_x(), ne_y()))


def back_pt(k):
    return at(k, (col_x(), trunk_y(1)))


def front_pt(k):
    return at(k, (col_x(), trunk_y(-1)))


def back_trunk():
    """The back trunk's points, pinky to inner column, past the top cells. Each
    column's end point is on its -x side, so where the next column in reaches
    further back than this column's end point, a straight line to its end point
    would cut across its end cell; there the trunk goes by that cell's +x corner."""
    ends = [finger_key(c, P.rows_above) for c in range(4, -1, -1)]
    pts = [back_pt(ends[0])]
    for a, b in zip(ends[:-1], ends[1:]):
        if (rinv(b.frame) @ np.append(back_pt(a), 1))[1] < trunk_y(1):
            pts.append(at(b, (out_y(), trunk_y(1))))
        pts.append(back_pt(b))
    return pts


def column_join(a, b):
    """Where the front line of b's end cell, carried on, meets a's column line."""
    p, q = front_pt(b), at(b, (0, trunk_y(-1)))
    c, d = at(a, (col_x(), 0)), at(a, (col_x(), 1))
    t = np.linalg.solve(np.c_[(q - p)[:2], (c - d)[:2]], (c - p)[:2])[1]
    return at(a, (col_x(), t))


def front_trunk():
    """The front trunk's points, pinky to index column, south of the bottom
    cells' diodes. Where a column reaches further forward than the next one in,
    the trunk leaves that next cell's line straight into the column's own
    channel, so it never runs round the outside of the stagger. Where it reaches
    less far, a straight line to the next column's end point would cut across
    that cell's diode, so the trunk goes by the cell's +x corner."""
    ends = [finger_key(c, -P.rows_below) for c in range(4, 0, -1)]
    pts = []
    for a, b in zip(ends[:-1], ends[1:]):
        if (rinv(b.frame) @ np.append(front_pt(a), 1))[1] < trunk_y(-1):
            pts.append(column_join(a, b))
        else:
            if not pts:
                pts.append(front_pt(a))
            pts.append(at(b, (out_y(), trunk_y(-1))))
        pts.append(front_pt(b))
    return pts


def bay_entry():
    """Where the back trunk reaches the well: just inside its back corner by the column."""
    b = L.mcu_bay()
    x, y = b[1][0] - 3, b[1][1] - 3
    return np.array([x, y, floor_z(x, y) + 3])


def finger_key(col, row):
    return L.column_key(col, row)


def thumb(name):
    return key_named(f"thumb_{name}")


def edge_mid(k):
    """Halfway along a thumb key's north edge."""
    return (ne(k) + riser(k)[1]) / 2


@cached
def thumb_routes():
    """The thumb wires' own ways out, as channels (width, [points...]) in world:
    far's up the inner side beside the row wire, home's and near's to the index
    column's foot, x1's round near's east corner to the middle column's, and x2's
    along x1's edge then inside near's south edge to join x1's. From that corner
    the two run up to the front trunk as a trunk, whose sink keeps them room where
    the straight run leaves the curving plinth."""
    w, t = P.channel_w_mm, P.trunk_w_mm
    near, home, far = (thumb(n) for n in ("near", "home", "far"))
    foot = [front_pt(finger_key(c, -P.rows_below)) for c in range(3)]
    inner = finger_key(0, -P.rows_below)
    routes = [(w, [riser(home)[1], at(inner, (col_x(), trunk_y(-1) - 6)), foot[0]]), (w, [ne(home), foot[1]]), (w, [ne(near), foot[1]])]
    if P.thumb_extra:
        x1, x2 = thumb("x1"), thumb("x2")
        corner = at(near, (out_y(), -P.cell_mm / 2))
        routes += [(w, [ne(x2), riser(x1)[1]]), (w, [ne(x1), corner]), (t, [corner, foot[2]]),
                   (w, [edge_mid(x1), at(near, (-P.cell_mm / 2, trunk_y(-1))), corner])]
    return routes


def channels():
    """The channels as polylines (width, [points...]) in world."""
    w, t = P.channel_w_mm, P.trunk_w_mm
    rows = range(-P.rows_below, P.rows_above + 1)
    out = []
    # Each finger column: front trunk point (the pinky's, the longest, joins it
    # higher up, so it starts level with its bottom key's diode), past its keys'
    # -x tabs, back trunk point.
    for c in range(5):
        bottom = finger_key(c, -P.rows_below)
        start = [front_pt(bottom) if c < 4 else at(bottom, (col_x(), diode_y()))]
        out.append((t if c == 0 else column_w(),
                    start + [c_tab(finger_key(c, r)) for r in rows]
                    + [back_pt(finger_key(c, P.rows_above))]))
    # The back trunk, pinky to inner column and into the bay, and the front trunk.
    out.append((t, back_trunk() + [bay_entry()]))
    out.append((t, front_trunk()))
    # Each finger row: along each key's north edge from its column channel, which
    # the wire shares from the -x tab up, to the next key's column channel.
    for r in rows:
        for c in range(4):
            a, b = finger_key(c, r), finger_key(c + 1, r)
            out.append((w, [nw(a), ne(a), nw(b)]))
    # The thumb row: a channel along the three keys' north edges, each key's tabs
    # risen to it.
    near, home, far = (thumb(n) for n in ("near", "home", "far"))
    out.append((w, [ne(near), riser(near)[1], ne(home), riser(home)[1], ne(far), riser(far)[1]]))
    for k in (near, home, far):
        out.append((w, [x_tab(k), ne(k)]))
        out.append((w, riser(k)))
    out += thumb_routes()
    # The extra keys: their tabs risen to their north edges, each joined up between
    # the row keys, x1's to the gap by near and x2's round far's east corner to its
    # tab's riser, so the row wire can go on from far without doubling back.
    if P.thumb_extra:
        x1, x2 = thumb("x1"), thumb("x2")
        for k in (x1, x2):
            out.append((w, [x_tab(k), ne(k), *riser(k)[::-1]]))
        out.append((w, [edge_mid(x1), (riser(near)[1] + ne(home)) / 2]))
        out.append((w, [edge_mid(x2), at(far, (out_y(), ne_y())), ne(far)]))
    out += [(w, joint_run(k)) for k in keys() if k.group != "finger"]
    return out


def post_points(p, w):
    """A channel post's corners at a world point: a square of w from 3 mm under
    the deepest sink below the body's underside up to the point (so the hull
    between two posts stays open to the underside where that curves up between
    them, and reaches the sink's floor)."""
    f = floor_z(p[0], p[1]) - 3 - P.trunk_sink_mm
    return [(p[0] + sx * w / 2, p[1] + sy * w / 2, z) for sx in (-1, 1) for sy in (-1, 1) for z in (f, p[2])]


def channel_segments():
    """Every channel's straight runs as (a, b, width)."""
    return [(a, b, w) for w, pts in channels() for a, b in zip(pts[:-1], pts[1:])]


def run_solid(a, b, w):
    return Manifold.hull_points(post_points(a, w) + post_points(b, w))


def channel_solids():
    return [run_solid(*r) for r in channel_segments()]


def channel_sinks():
    """The channels' sinks into the plinth's top, each as deep as its kind and
    stopping bottom_plate_mm over the desk. A sink reaches up through all the
    plinth over it: the plinth's top can rise over a straight run's top line,
    and a run's own height would leave a cap of it loose across the channel."""
    shell = plinth_shell()
    above = Manifold.cube((400, 400, 100)).translate((-200, -200, P.bottom_plate_mm))
    up = np.array([0, 0, 100])
    runs = [(a + up, b + up, w) for a, b, w in channel_segments()]
    return [(union([run_solid(*r) for r in runs if (r[2] == P.trunk_w_mm) == trunk]) ^ above) - shell.translate((0, 0, -d))
            for trunk, d in ((False, P.channel_sink_mm), (True, P.trunk_sink_mm))]


def diode_z():
    return R.socket_top_z() - P.diode_mm[1] / 2 - P.diode_room_mm


def diode_frame(k):
    """The diode's frame. A finger key's lies across the key in its own pocket,
    south of the centre post; a thumb key's in its riser over the column tab."""
    if k.group == "finger":
        return k.frame @ trans([0, diode_y(), diode_z()]) @ rot_z(90)
    return k.frame @ trans([diode_x(), thumb_diode_y(), diode_z()])


def leg_slots():
    """A finger diode's legs' slots as (size, centre) in the key's frame: the -x
    leg's out to the column channel, the +x leg's out past the side post's hole
    and north into the +x tab's solder well."""
    s, x0, y, z = P.diode_leg_slot_mm, P.diode_mm[0] / 2, diode_y(), diode_z()
    west, east, well = shaft_edge_x(), leg_x() + s / 2, P.socket_tab_y[1] - P.solder_well_mm[1] / 2 + s
    return [((-x0 - west, s, s), ((west - x0) / 2, y, z)), ((east - x0, s, s), ((east + x0) / 2, y, z)),
            ((s, well - y, s), (leg_x(), (well + y) / 2, z))]


def diode_room(k):
    """Room for key k's diode, open down to the underside to put it in, as a
    list of cutters. A finger key's, with its legs' slots, goes down the key's
    normal, not to the desk, so on a leaning key it stays out from under the
    post holes."""
    d, r = P.diode_mm, P.diode_room_mm
    size = (d[1] + 2 * r, d[0] + 2 * r, d[1] + 2 * r)
    if k.group == "finger":
        size = (size[1], size[0], size[2])
        return [normal_swept(k.frame, *b) for b in [(size, (0, diode_y(), diode_z())), *leg_slots()]]
    return [swept(diode_frame(k), size, (0, 0, 0))]


def swept(m, size, centre, depth=60):
    """A box drawn in frame m carried straight down (in world) by `depth`, so
    shafts and wells stand square to the desk however the key tilts."""
    pts = np.array([xform(m, c) for c in box_corners(size, centre)])
    return Manifold.hull_points(np.r_[pts, pts - (0, 0, depth)])


def normal_swept(m, size, centre, depth=60):
    """A box drawn in frame m carried down frame m's own z by `depth`."""
    pts = [np.array(c, float) for c in box_corners(size, centre)]
    return Manifold.hull_points([xform(m, c - (0, 0, z)) for c in pts for z in (0, depth)])


def socket_shaft(k, grow):
    """The socket's shaft from its pocket down through the body's underside, `grow` round the body."""
    return [swept(k.frame, s, c) for s, c in R.socket_boxes(grow)]


def solder_wells(k):
    """Room round each of key k's socket terminals to solder to it: solder_well_mm
    reaching solder_well_reach_mm past the tab's tip, cut back in plan to stay min_wall_mm inside the
    cell at the socket's top, so it keeps that wall from the next key's room
    and from the bay. The -x well then ends just past its tab's tip."""
    s = P.solder_well_mm
    inside = polygon(cell_corners(k, -P.min_wall_mm, R.socket_top_z())).extrude(203).translate((0, 0, -2))
    return [swept(k.frame, (s[0], s[1], 0.6), R.socket_tab_tip(side) + (side * (P.solder_well_reach_mm - s[0] / 2), 0, -0.3)) ^ inside
            for side in (-1, 1)]


# ---------------------------------------------------------------- the body
def key_room(k):
    """Key k's room (switch, socket and shaft) as one cutter."""
    return union(place(k.frame, R.mx_switch_room() + R.hotswap_socket_room()) + socket_shaft(k, P.socket_clearance_mm))


def bay_rooms(plinth=False):
    """The parts' rooms in the well, cut from the plinth and from the body where
    they reach above the plate's top. The battery's lead notch is one of them,
    as tall as the pocket; the power switch's is the plinth's alone."""
    out = place(mcu_frame(), R.mcu_room()) + place(battery_frame(), R.battery_room())
    out.append(floor_box(L.lead_notch(), bay_pocket_h()))
    if P.power_switch and plinth:
        out += place(power_switch_frame(), R.power_switch_room())
    return out


@cached
def screw_seats():
    """The level of each screw's pad: the plinth's highest point under it. The
    underside tilts and steps, so the pad levels it for the screw: the plinth
    comes up to this level over the pad and the body is cut back plate_gap_mm
    above it, so every insert's mouth is flat and square to its hole, and the
    screw clamps flat on flat."""
    shell = plinth_shell()
    return [float((R.cylinder(P.screw_pad_d, 100, (p[0], p[1], -1)) ^ shell).bounding_box()[5]) for p in L.screw_points()]


def screw_pad(p, seat):
    """Screw p's pad as the body loses it: a little wider than the plinth's, up
    to plate_gap_mm over the seat."""
    z = seat + P.plate_gap_mm
    return R.cylinder(P.screw_pad_d + 2 * P.boss_clearance_mm, z + 1, (p[0], p[1], -1))


def insert_hole_at(p, seat):
    return R.insert_hole().translate((p[0], p[1], seat + P.plate_gap_mm))


def insert_holes():
    """The insert holes and the pads they open from."""
    return [c for p, z in zip(L.screw_points(), screw_seats()) for c in (screw_pad(p, z), insert_hole_at(p, z))]


@cached
def body_cuts():
    """Everything cut from the body but the screws' insert holes, in named groups."""
    ks = keys()
    return [("a key's room", [key_room(k) for k in ks]), ("a solder well", [w for k in ks for w in solder_wells(k)]),
            ("a diode's room", [s for k in ks for s in diode_room(k)]), ("a channel", channel_solids()), ("a bay room", bay_rooms())]


def body_cutters():
    return [s for _, group in body_cuts() for s in group]


@cached
def body():
    shell = body_shell()
    t = time.time()
    body = subtract(shell, body_cutters() + insert_holes())
    body.num_tri()   # Manifold evaluates lazily: make the cut happen here
    stage("body cuts", t)
    return body


# ---------------------------------------------------------------- the bottom plate
def socket_boss(k):
    """The boss under key k's socket: the socket's shaft, inset, standing on the
    plinth's top under the cell up to just under the socket (and reaching
    put_back_mm into the plinth, so the two meet in a volume)."""
    return (union(socket_shaft(k, -P.boss_inset_mm)) ^ half_space(k.frame, R.socket_bottom_z() - P.boss_clearance_mm)
            ^ half_space(k.frame, -L.floor_drop() - P.plate_gap_mm - put_back_mm, below=False))


def screw_holes():
    return [h.translate((p[0], p[1], 0)) for p, z in zip(L.screw_points(), screw_seats()) for h in R.screw_hole(z)]


@cached
def plate_cuts():
    """Everything cut from the plinth but the screw holes, in named groups."""
    return [("the well", well()), ("a bay room", bay_rooms(plinth=True)),
            ("the reset pinhole", place(mcu_frame(), [R.mcu_reset_hole()])), ("a channel", channel_sinks())]


def plate_cutters():
    return [s for _, group in plate_cuts() for s in group]


@cached
def bottom_plate():
    """The plinth: up to the body's underside and the screws' pads, with the well,
    the screw holes and the pinhole over the reset button, and the socket bosses
    standing on it."""
    pads = [R.cylinder(P.screw_pad_d, z + 1, (p[0], p[1], -1)) ^ Manifold.cube((400, 400, 100)).translate((-200, -200, 0))
            for p, z in zip(L.screw_points(), screw_seats())]
    shell = add(plinth_shell(), pads)
    t = time.time()
    plate = add(subtract(shell, plate_cutters() + screw_holes()), [socket_boss(k) for k in keys()])
    plate.num_tri()
    stage("plinth cuts and bosses", t)
    return plate


# ---------------------------------------------------------------- the parts, for the assembly
def at_keys(part, frame=lambda k: k.frame):
    """A part's pieces at every key, each named for its key."""
    return [Piece(f"{p.label} {k.name}", p.colour, placed(frame(k), p.solid)) for k in keys() for p in part]


def switches():
    return at_keys(R.mx_switch())


def keycaps(pressed=0):
    return [Piece(f"keycap {k.name}", "ivory", placed(k.frame, R.keycap(k.cap_row, k.units, pressed))) for k in keys()]


def sockets():
    return at_keys(R.hotswap_socket())


def diodes():
    return at_keys(R.diode(), diode_frame)


def electronics():
    parts = [(mcu_frame(), R.mcu_board()), (battery_frame(), R.battery())]
    if P.power_switch:
        parts.append((power_switch_frame(), R.power_switch_part()))
    return [Piece(p.label, p.colour, placed(m, p.solid)) for m, part in parts for p in part]


# ---------------------------------------------------------------- checks
def near_pairs():
    """Pairs of keys near enough for their caps to meet."""
    ks = keys()
    return [(i, j) for i in range(len(ks) - 1) for j in range(i + 1, len(ks))
            if np.linalg.norm(origin(ks[i].frame) - origin(ks[j].frame)) < 2.2 * P.cell_mm]


def cap_collisions():
    """Where caps meet, with their clearance: at rest, and each key pressed with
    its neighbours at rest. Empty when the layout is clear; otherwise a list of
    (key, key, overlap volume)."""
    ks = keys()
    hits = []
    for i, j in near_pairs():
        for pi, pj in ((0, 0), (P.cap_travel_mm, 0), (0, P.cap_travel_mm)):
            a = placed(ks[i].frame, R.keycap_probe(ks[i].cap_row, ks[i].units, pi))
            b = placed(ks[j].frame, R.keycap_probe(ks[j].cap_row, ks[j].units, pj))
            v = (a ^ b).volume()
            if v > 1e-6:
                hits.append((ks[i].name, ks[j].name, v))
    return hits


def part_overlap():
    """How much the body and the plinth overlap, mm^3 (0 when the plinth stays
    under the body's underside)."""
    return (body() ^ bottom_plate()).volume()


def wire_ends():
    """Where wires start, by name, each a point just inside the space cut for
    it (a wire's width in): every key's row and column ends (a wire's width off
    a terminal's north face in its channel, or for a finger key's column wire
    its joint to the diode's leg), the battery's leads (out of its back end),
    the power switch's pins (in their notch), and the controller."""
    d = P.wire_d_mm
    off = P.socket_tab_mm[1] / 2 + d
    ends = []
    for k in keys():
        x_end = at(k, (row_x(), P.socket_tab_y[1] + off)) - (0, 0, d)
        minus_end = at(k, (riser_x(k), P.socket_tab_y[0] + off)) - (0, 0, d)
        if k.group == "finger":
            ends += [(f"{k.name}'s row tab", minus_end), (f"{k.name}'s diode joint", at(k, (col_x(), diode_y())) - (0, 0, d))]
        else:
            ends += [(f"{k.name}'s column tab", minus_end), (f"{k.name}'s row tab", x_end)]
    m, b, z = L.mcu_bay(), L.battery_bay(), bay_z() + d
    ends.append(("the battery's leads", np.array([(b[0][0] + b[1][0]) / 2, b[1][1] - d, z])))
    if P.power_switch:
        notch = P.power_switch_mm[1] / 2 + P.power_switch_pins_mm[1] / 2
        ends.append(("the power switch", xform(power_switch_frame(), [0, notch, -d / 2])))
    ends.append(("the controller", np.array([(m[0][0] + m[1][0]) / 2, (m[0][1] + m[1][1]) / 2, z])))
    return ends


def wire_space():
    """The spaces cut from the body and the plinth (channels, pockets, the well; see lost)."""
    return union([lost(body_shell(), body_cutters(), True), lost(plinth_shell(), plate_cutters())])


def crowded_keys():
    """The finger keys where a straight wire can't lie along the column from the
    diode's joint to the north edge: in the key's frame, the body, the plinth and
    the terminal (carried on down, so nothing counts that goes under it) over
    that span, seen along y, leave no room for a circle of wire_d_mm in the
    channel."""
    solid = union([body(), bottom_plate()])
    (size, centre), _ = R.socket_tab_boxes()
    tab = R.box((size[0], size[1], 40), (centre[0], centre[1], -20))
    y0 = diode_y()
    s = R.box((12, ne_y() - y0, 12), (-8, (y0 + ne_y()) / 2, -9.5))
    x0 = lane_x() - 2 * P.wire_d_mm
    window = CrossSection.square((socket_end_x() - x0, 12)).translate((x0, -15.5))
    across = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0]], float)
    out = []
    for k in keys():
        if k.group != "finger":
            continue
        to_key = rinv(k.frame)
        m = np.asarray(to_key[:3, :4], float)
        solids = [solid.transform(m) ^ s, tab ^ s]
        seen = CrossSection.batch_boolean([p.transform(across).project() for p in solids], OpType.Add)
        if (window - seen).offset(-P.wire_d_mm / 2, JoinType.Round, 2.0, 32).is_empty():
            out.append(k.name)
    return out


def cramped_diodes():
    """The keys where the diode and its legs meet the body or the plinth: a
    finger key's glass and the line of each leg, a thumb key's north leg and
    sleeved joint, which go in as one piece, so nothing there can give."""
    solid = union([body(), bottom_plate()])
    d, leg = P.diode_mm, P.diode_leg_d_mm
    finger = [((d[0], d[1], d[1]), (0, diode_y(), diode_z()))] + [
        (tuple(leg if a == min(size) else a - P.diode_leg_slot_mm for a in size), centre) for size, centre in leg_slots()]
    out = []
    for k in keys():
        s = solid.transform(np.asarray(rinv(k.frame)[:3, :4], float))
        if any((s ^ R.box(*b)).volume() > 1e-3 for b in (finger if k.group == "finger" else [thumb_joint()])):
            out.append(k.name)
    return out


def unwired():
    """The wire ends that no path a wire fits through (wire_d_mm), through
    wire_space, past the sockets' terminals, joins to the controller's. The space
    is shrunk by the wire's radius along each axis, which closes the slivers
    where one cut grazes another."""
    space = subtract(wire_space(), [s for k in keys() for s in place(k.frame, R.socket_tabs())])
    r = P.wire_d_mm / 2
    for axis in np.eye(3):
        space = space.translate(tuple(r * axis)) ^ space.translate(tuple(-r * axis))

    def probe(p):
        return Manifold.cube((0.2, 0.2, 0.2), center=True).translate(tuple(float(c) for c in p))

    *ends, (_, controller) = wire_ends()
    home = next(c for c in space.decompose() if (c ^ probe(controller)).volume() > 0)
    return [name for name, p in ends if (home ^ probe(p)).volume() <= 0]


def lost(shell, cutters, open_below=False):
    """What a part loses to some of its cutters: its shell within them (they
    reach past it); for the body's, open at its underside, lowered across the
    plate gap as well, so they meet the plinth's wherever it is cut away under them."""
    space = shell ^ union(cutters)
    return union([space, space.translate((0, 0, -P.plate_gap_mm - 0.2))]) if open_below else space


def thin_walls():
    """The walls thinner than min_wall_mm between the rooms of different parts
    (each key's room, solder wells and diode's room; the bay's rooms and well),
    and between the bay and every channel but the one into it, and between a
    finger column's channel and the keys of other columns, as a list of (room,
    room, wall mm), empty when every wall is thick enough. The other channels
    join keys by design, so they are held only to the bay."""
    rooms = [(k.name, lost(body_shell(), [key_room(k), *solder_wells(k), *diode_room(k)], True)) for k in keys()]
    named = dict(zip([k.name for k in keys()], rooms))
    bay = union([lost(body_shell(), bay_rooms(), True),
                 lost(plinth_shell(), [s for name, group in plate_cuts() if name != "a channel" for s in group])])
    rooms.append(("the bay", bay))
    pairs = [(a, b) for i, a in enumerate(rooms) for b in rooms[i + 1:]]
    pairs += [((f"the channel ({a[0]:.1f}, {a[1]:.1f}) to ({b[0]:.1f}, {b[1]:.1f})",
                lost(body_shell(), [run_solid(a, b, w)], True)), ("the bay", bay))
              for a, b, w in channel_segments() if not np.array_equal(b, bay_entry())]
    for c, (w, pts) in enumerate(channels()[:5]):
        run = (f"column {c}'s channel", lost(body_shell(), [run_solid(a, b, w) for a, b in zip(pts[:-1], pts[1:])], True))
        pairs += [(run, named[k.name]) for k in keys() if not (k.group == "finger" and k.col == c)]
    out = []
    for (a, sa), (b, sb) in pairs:
        if gap(sa, sb) < P.min_wall_mm:
            d = sa.min_gap(sb, P.min_wall_mm)
            if d < P.min_wall_mm - 1e-6:
                out.append((a, b, d))
    return out


def gap(a, b):
    """The gap between two solids' bounding boxes (0 when they overlap)."""
    a, b = np.array(a.bounding_box()), np.array(b.bounding_box())
    return max(0, *(a[:3] - b[3:]), *(b[:3] - a[3:]))


@cached
def screw_walls():
    """The wall left round each screw: its holes (the plate's screw hole and
    counterbore, the body's insert hole) against everything else cut from that
    part, and against the outline. Returns the least wall as (mm, screw, what)
    and the clashes as a list of (screw, what, overlap mm^3), empty when every
    hole is clear."""
    least, hits = (float("inf"), None, None), []
    for i, (p, h) in enumerate(zip(L.screw_points(), screw_seats())):
        x, y = float(p[0]), float(p[1])
        name = f"screw {i + 1} ({x:.1f}, {y:.1f})"
        if h < P.screw_grip_mm + P.screw_head_h_mm:
            proud = P.screw_grip_mm + P.screw_head_h_mm - h
            hits.append((name, "the desk (the head stands proud of the plinth)", np.pi * (P.screw_head_d / 2) ** 2 * proud))
        round_it = R.cylinder(R.counterbore_d() + 0.2, 60, (x, y, 0))
        under = h - P.screw_grip_mm - (round_it - plinth_shell()).bounding_box()[2]
        if under > 0:
            hits.append((name, "the plinth's top (the counterbore breaks out through it)", np.pi * (R.counterbore_d() / 2) ** 2 * under))
        holes = [(c.translate((x, y, 0)), plate_cuts()) for c in R.screw_hole(h)]
        holes += [(insert_hole_at(p, h), body_cuts()), (screw_pad(p, h), body_cuts())]
        for hole, cuts in holes:
            box = hole.bounding_box()
            walls = [(outline_distance((x, y)) - (box[3] - box[0]) / 2, "the outline")]
            for what, group in cuts:
                for s in group:
                    if gap(hole, s) > 5:
                        continue
                    v = (hole ^ s).volume()
                    if v > 0:
                        hits.append((name, what, v))
                        walls.append((0.0, what))
                    else:
                        walls.append((hole.min_gap(s, 5), what))
            d, what = min(walls)
            if d < least[0]:
                least = (d, name, what)
    return least, hits


def report():
    """The board's heights and sizes, as text."""
    ks = keys()
    (x0, y0), (x1, y1) = outline().min(axis=0), outline().max(axis=0)
    tops = [L.cap_top(k)[2] for k in ks]
    plates = [origin(k.frame)[2] for k in ks]
    floors = [floor_z(*origin(k.frame)[:2]) for k in ks]
    reach = [r2(L.finger_plate_pitch(i) * L.finger_reach_radius(i) / L.finger_plate_radius(i)) for i in range(4)]
    (wall, screw, what), _ = screw_walls()
    return (f"plate tops {r2(min(plates))} to {r2(max(plates))} mm over the desk; cap tops {r2(min(tops))} to "
            f"{r2(max(tops))} mm; body shell {r2(L.floor_drop())} mm thick; plinth {r2(min(floors))} to "
            f"{r2(max(floors))} mm under the keys; well floor {r2(bay_z())} mm; fingertip reach between rows "
            f"{reach} mm (index to pinky); plan {r2(x1 - x0)} x {r2(y1 - y0)} mm, {round(polygon(outline()).area())} mm^2; "
            f"least wall round a screw {r2(wall)} mm ({screw} to {what})")

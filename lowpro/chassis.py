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
from .layout import (at, back_pt, c_tab, cached, cell_corners, col_x, front_pt, keys, key_named, ne, ne_y, nw,
                     out_y, r_tab, row_x)
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
# The body's underside is the same surface floor_drop() lower, but never
# below the body's floor (body_floor); the plate's top plate_gap_mm under that.
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


def body_floor():
    """The lowest the body's underside goes: plate_gap_mm over the plinth's
    bottom_plate_mm floor. The keys are lifted so their rooms reach no lower
    (layout.py world_frame); the shell dropped straight down from a steep
    key's low edge would, and is cut off here."""
    return P.bottom_plate_mm + P.plate_gap_mm


def underside(top):
    """The body's underside under top surface heights `top`."""
    return np.maximum(top - L.floor_drop(), body_floor())


def floor_z(x, y):
    return float(underside(top_z(x, y)))


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


def channel_points(group=None):
    """The channel paths in plan with a margin round them, as the point sets of
    a stadium per segment (those of one group when given)."""
    out = []
    for w, pts, g in channels():
        if group is not None and g != group:
            continue
        for a, b in zip(pts[:-1], pts[1:]):
            r = w / 2 + P.channel_margin_mm
            out.append(circle_points(a, r) + circle_points(b, r))
    return out


def cells_2d():
    """The cells, bays and channel paths in plan, before the wall."""
    return fused([cell_face(k) for k in keys()] + [bay_face(b) for b in L.bays()]
                 + [hull_of(pts) for pts in channel_points()])


def hulls_2d():
    """The finger field (its cells, the bays and its channels) and the thumb
    cluster each as a convex hull, and the bridge joining them: the thumb row,
    the two bottom keys nearest it, the bays on the inner side and the channel
    between the two, so the inner edge runs straight from the bays to the thumb."""
    bays = [p for b in L.bays() for p in bay_points(b)]
    finger = hull_of([c for k in keys() if k.group == "finger" for c in cell_corners(k)] + bays
                     + [p for pts in channel_points("finger") for p in pts])
    thumb = hull_of([c for k in keys() if k.group != "finger" for c in cell_corners(k)]
                    + [p for pts in channel_points("thumb") for p in pts])
    bridge = hull_of([c for k in keys() if k.group == "thumb" or (k.group == "finger" and k.col <= 1 and k.row == -P.rows_below)
                      for c in cell_corners(k)] + bays + [p for pts in channel_points("bridge") for p in pts])
    return fused([finger, thumb, bridge])


def signed_area(pts):
    x, y = pts[:, 0], pts[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


@cached
def outline_curve():
    """The body's outline as a smooth closed curve: outline_style "hulls" is the
    hulls joined, "closed" the cells and channel paths closed up (gaps narrower
    than 2 * outline_close_mm filled). Either way the gaps that remain get a
    round of outline_close_mm, the wall goes round it and the convex corners
    are rounded to outline_round_mm. The offsets leave a polygon of straight
    sides and arcs (as chords within mesh_tol_mm); the curve is a periodic
    cubic spline through points along it a tenth of mesh_mm apart, so that its
    normal turns smoothly where an arc meets a side. Returns the spline, over
    the polygon's length, counterclockwise."""
    s = hulls_2d() if P.outline_style == "hulls" else cells_2d()
    for amount in (P.outline_close_mm, -P.outline_close_mm, P.wall_mm, -P.outline_round_mm, P.outline_round_mm):
        s = s.offset(amount, JoinType.Round, 2.0, segments(abs(amount)))
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
    vertices = np.r_[np.c_[vu, underside(top_surface(vu))], rows.reshape(-1, 3),
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
    z = underside(top_surface(vu)) - P.plate_gap_mm
    _, tb = plan_mesh(q, fill=False)
    station = np.arange(n)
    vertices = np.r_[np.c_[vu, z], np.c_[q, np.zeros(n)]]
    return solid_from(vertices, np.r_[tu, u + tb[:, ::-1], walled(u + station, station)], "plinth's blank")


# Every cell's plane is put back exactly, cell_step_mm past its edge: over the
# cell, whatever the body's blank has above the plane is cut away and a block
# under it added, and likewise under the plane floor_drop() straight down (the
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


def below_plane(group, drop):
    """How far under the group's plane, along its normal, a plane `drop`
    lower (straight down, as the blanks' undersides are) is."""
    return -drop * group[0].frame[2, 2]


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
    caps += [column(g, cut) ^ half_space(g[0].frame, below_plane(g, d) + put_back_mm) for g in plane_groups()]
    blocks = [column(g, block) ^ slab(g[0].frame, 0, below_plane(g, d)) for g in plane_groups()]
    # The blocks reach below the floor under a steep key's low edge: cut off
    # ring_mm under it, clear of the blank's floor (and the plinth's).
    floor = Manifold.cube((400, 400, 100)).translate((-200, -200, body_floor() - ring_mm - 100))
    shell = subtract(add(subtract(body_blank(), caps), blocks), [floor])
    if P.knob:
        shell = add(shell, [knob_boss(False)])
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
    d = L.floor_drop() + P.plate_gap_mm
    floor = Manifold.cube((400, 400, 100)).translate((-200, -200, put_back_mm))
    fill = [column(g, P.cell_step_mm - ring_mm) ^ half_space(g[0].frame, below_plane(g, d) + put_back_mm) ^ floor
            for g in plane_groups()]
    # Never into the floor (whose top is the blank's where the underside is
    # cut off): ring_mm over it.
    keep = Manifold.cube((400, 400, 100)).translate((-200, -200, P.bottom_plate_mm + ring_mm))
    clear = [column(g, P.cell_step_mm) ^ half_space(g[0].frame, below_plane(g, d), below=False) ^ keep
             for g in plane_groups()]
    shell = subtract(add(plinth_blank(), fill), clear)
    if P.knob:
        shell = add(shell, [knob_boss(True)])
    stage("the plinth's shell", t)
    return shell


# ---------------------------------------------------------------- the bay's well
def bay_pocket_h():
    """The pocket height the parts need over the well's floor."""
    mcu = P.mcu_parts_mm + P.mcu_board_mm[2] + P.mcu_clearance_mm
    if P.link == "trrs":
        return max(mcu, P.trrs_body_mm[2] + 2 * P.trrs_clearance_mm)
    return max(mcu, P.battery_mm[2] + P.battery_clearance_mm,
               P.power_switch_mm[2] + 0.6 if P.power_switch else 0)


@cached
def bay_z():
    """The well's floor: the plinth's thinnest, or higher where a plug's housing
    (the USB-C plug's, the TRRS plug's) would come within plug_desk_mm of the
    desk, each centred on its port."""
    usb = P.mcu_plug_mm[1] / 2 - (R.mcu_pcb_z() - P.mcu_usb_mm[1] / 2)
    floors = [P.bottom_plate_mm, P.plug_desk_mm + usb]
    if P.link == "trrs":
        floors.append(P.plug_desk_mm + P.trrs_plug_d / 2 - P.trrs_body_mm[2] / 2)
    return max(floors)


def mcu_frame():
    return trans([0, 0, bay_z()]) @ L.mcu_frame()


def battery_frame():
    return trans([0, 0, bay_z()]) @ L.battery_frame()


def power_switch_frame():
    return trans([0, 0, bay_z()]) @ L.power_switch_frame()


def trrs_frame():
    return trans([0, 0, bay_z()]) @ L.trrs_frame()


def inner_wall_frame(y, z=0):
    """A frame on the outer face of the inner side wall (the outline's least x
    at y), at height z: +x in, square to the wall, +z up."""
    q = outline()
    hits = []
    for a, b in zip(q, np.roll(q, -1, axis=0)):
        if (a[1] - y) * (b[1] - y) <= 0 and a[1] != b[1]:
            t = (y - a[1]) / (b[1] - a[1])
            hits.append((a[0] + t * (b[0] - a[0]), b - a))
    x, d = min(hits, key=lambda h: h[0])
    # Counterclockwise, so the inward normal is the edge turned left.
    return trans([x, y, z]) @ rot_z(math.degrees(math.atan2(d[0], -d[1])))


def reset_frame():
    """The reset switch's frame (parts.py reset_switch): origin at the middle of
    its plunger face, the plunger out through the inner side wall, its body in
    a pocket in the wall reset_skin_mm inside the outer face, in front of the
    jack, standing on the well's floor."""
    return inner_wall_frame(L.reset_y(), bay_z()) @ trans([P.reset_skin_mm, 0, P.reset_body_mm[0] / 2 + P.reset_clearance_mm])


@cached
def knob_frame():
    """The knob's frame (parts.py knob): origin on its axis at the inner side
    wall's outer face, +x in along the axis, the knob's top knob_above_mm
    over the case's top along the wall across the knob."""
    f, r = inner_wall_frame(L.knob_y()), P.knob_d_mm / 2
    edge = top_surface(np.array([xform(f, (0, y, 0))[:2] for y in np.linspace(-r, r, 9)])).max()
    return inner_wall_frame(L.knob_y(), float(edge) + P.knob_above_mm - r)


def plan_points():
    """The body's and the plinth's plan: the outline, and the knob's boss
    standing out of it."""
    if not P.knob:
        return outline()
    b = placed(knob_frame(), R.knob_boss()).bounding_box()
    return np.r_[outline(), [(b[0], b[1]), (b[3], b[4])]]


def knob_boss(lower):
    """The knob's boss (parts.py knob_boss), split where the body meets the
    plinth at the axis: the body's half, or the plinth's (lower). Inside the
    outline each keeps only what its own blank has, so it fuses with the wall
    and stands neither over the case's top nor in the other part."""
    boss, f = placed(knob_frame(), R.knob_boss()), knob_frame()
    z, g = floor_z(f[0, 3], f[1, 3]), P.plate_gap_mm
    inside = polygon(outline()).extrude(400).translate((0, 0, -200))
    if lower:
        return boss ^ half_space(np.eye(4), z - g, size=400) - (inside - plinth_blank())
    return boss ^ half_space(np.eye(4), z, below=False, size=400) - (inside - body_blank())


def knob_slot_reach():
    """How far the sensor's wire slot runs (+y in the knob's frame) before it
    turns in: far enough that the turn lies a millimetre inside the well's front."""
    return L.mcu_bay()[0][1] - L.knob_y() + 1 + P.channel_w_mm


def floor_box(r, h):
    """The plan rectangle r ((x0, y0), (x1, y1)) from the well's floor up h."""
    return Manifold.cube((r[1][0] - r[0][0], r[1][1] - r[0][1], h)).translate((r[0][0], r[0][1], bay_z()))


def well():
    """The well: the bays' rectangles and the battery's lead notch between
    them, open from the well's floor up through the plate's top (the body
    takes the parts' rooms, bay_rooms, where they reach above it)."""
    notch = [L.lead_notch()] if P.link == "ble" else []
    return [floor_box(b, 100) for b in L.bays() + notch]


def edge_trunk(side):
    """The back (side 1) or front (side -1) trunk's points, pinky to inner
    column, past the end cells' edges. Each column's end point is on its -x
    side, so where the next column in reaches further out than this column's
    end point, a straight line to its end point would cut across its end cell;
    there the trunk goes by that cell's +x corner, as far past both edges as
    the end points are past theirs."""
    end = back_pt if side > 0 else front_pt
    row = P.rows_above if side > 0 else -P.rows_below
    ends = [finger_key(c, row) for c in range(4, -1, -1)]
    pts = [end(ends[0])]
    for a, b in zip(ends[:-1], ends[1:]):
        if side * (rinv(b.frame) @ np.append(end(a), 1))[1] < out_y():
            pts.append(at(b, (out_y(), side * out_y())))
        pts.append(end(b))
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


def bridge():
    """The trunk from the front trunk to the thumb row's trunk: from the front
    trunk's point nearest the near thumb key's north-east corner (so it never
    doubles back along the front trunk) to that corner."""
    end = ne(thumb("near"))
    return [min(edge_trunk(-1), key=lambda p: np.linalg.norm(p[:2] - end[:2])), end]


@cached
def channels():
    """The channels as polylines (width, [points...], group) in world; the group
    ("finger", "thumb" or "bridge") says which hull of the footprint holds it."""
    w, t = P.channel_w_mm, P.trunk_w_mm
    rows = range(-P.rows_below, P.rows_above + 1)
    out = []
    # Each finger column: front trunk point, its keys' column tabs, back trunk point.
    for c in range(5):
        out.append((t if c == 0 else P.column_w_mm,
                    [front_pt(finger_key(c, -P.rows_below))] + [c_tab(finger_key(c, r)) for r in rows]
                    + [back_pt(finger_key(c, P.rows_above))], "finger"))
    # The back trunk, pinky to inner column and into the bay, and the front trunk.
    out.append((t, edge_trunk(1) + [bay_entry()], "finger"))
    out.append((t, edge_trunk(-1), "finger"))
    out.append((t, bridge(), "bridge"))
    # Each finger row: from each key's tab up to its north edge, across to the
    # next cell's north edge and along it to that key's tab; the inner column's
    # feeds its wire into the column channel. Tiles' shafts are open under the
    # whole tile, so a row runs straight from one tile's east R hole to the
    # next one's west R hole, and the inner column's meets its column wire in
    # its shaft.
    for r in rows:
        k0 = finger_key(0, r)
        if P.key_parts != "tiles":
            out.append((w, [r_tab(k0), ne(k0), nw(k0)], "finger"))
        for c in range(4):
            a, b = finger_key(c, r), finger_key(c + 1, r)
            if P.key_parts == "tiles":
                out.append((w, [r_tab(a), at(b, P.tile_r_west_hole)], "finger"))
            else:
                out.append((w, [r_tab(a), ne(a), nw(b), ne(b), r_tab(b)], "finger"))
    # The thumb row: a trunk along the three keys' north edges (the row wire and
    # the column wires on their way to the front trunk), each key's tabs risen to it.
    out.append((t, [p for n in ("near", "home", "far") for p in (ne(thumb(n)), nw(thumb(n)))], "thumb"))
    for n in ("near", "home", "far"):
        out.append((w, [r_tab(thumb(n)), ne(thumb(n))], "thumb"))
        out.append((w, [c_tab(thumb(n)), nw(thumb(n))], "thumb"))
    # The extra keys: their tabs risen to their north edges, joined to the gap
    # between the row keys over them.
    if P.thumb_extra:
        for name, left, right in (("x1", "near", "home"), ("x2", "home", "far")):
            k = thumb(name)
            g = (nw(thumb(left)) + ne(thumb(right))) / 2
            out.append((w, [r_tab(k), ne(k), nw(k), c_tab(k)], "thumb"))
            out.append((w, [(ne(k) + nw(k)) / 2, g], "thumb"))
    return out


def post_points(p, w):
    """A channel post's corners at a world point: a square of w from 3 mm under
    the body's underside up to the point (so the hull between two posts stays
    open to the underside where that curves up between them)."""
    f = floor_z(p[0], p[1]) - 3
    return [(p[0] + sx * w / 2, p[1] + sy * w / 2, z) for sx in (-1, 1) for sy in (-1, 1) for z in (f, p[2])]


def channel_segments():
    """Every channel's straight runs as (a, b, width)."""
    return [(a, b, w) for w, pts, _ in channels() for a, b in zip(pts[:-1], pts[1:])]


def run_solid(a, b, w):
    return Manifold.hull_points(post_points(a, w) + post_points(b, w))


def channel_solids():
    return [run_solid(*r) for r in channel_segments()]


def diode_frame(k):
    """The diode's frame: in the column channel, over the column tab."""
    return k.frame @ trans([col_x(), (P.socket_tab_y[0] + ne_y()) / 2 + 1, R.socket_top_z() - P.diode_mm[1] / 2 - 0.4])


def diode_rooms(k):
    """Room for key k's diode in the column channel, over the column tab (a
    tile carries its own)."""
    if P.key_parts == "tiles":
        return []
    d = P.diode_mm
    return [placed(diode_frame(k), R.box((d[1] + 0.8, d[0] + 0.8, d[1] + 0.8)))]


def swept(m, size, centre, depth=60):
    """A box drawn in frame m carried straight down (in world) by `depth`, so
    shafts and wells stand square to the desk however the key tilts."""
    pts = np.array([xform(m, c) for c in box_corners(size, centre)])
    return Manifold.hull_points(np.r_[pts, pts - (0, 0, depth)])


def socket_shaft(k, grow):
    """The socket's shaft from its pocket down through the body's underside, `grow` round the body."""
    return [swept(k.frame, s, c) for s, c in R.socket_boxes(grow)]


def solder_wells(k):
    """Room under each of key k's socket tabs to solder to it: solder_well_mm
    centred on the tab's tip, cut back in plan to stay min_wall_mm inside the
    cell at the socket's top, so it keeps that wall from the next key's room
    (whose -x tab's slot comes within a millimetre of its cell's edge) and from
    the bay. The -x well then ends about at its tab's tip. A tile's shaft
    leaves its holes open from below."""
    if P.key_parts == "tiles":
        return []
    s = P.solder_well_mm
    inside = polygon(cell_corners(k, -P.min_wall_mm, R.socket_top_z())).extrude(203).translate((0, 0, -2))
    return [swept(k.frame, (s[0], s[1], 0.6), R.socket_tab_tip(side) - (0, 0, 0.3)) ^ inside for side in (-1, 1)]


# ---------------------------------------------------------------- the body
def tile_seat(k):
    """Key k's switch room and its tile's footprint from the board up to the
    plate (the ledge over the board, which it is pushed up against when the
    switch goes in, and the housing's pocket): what locates the key, which
    keeps a wall from every other key's room. Under the board is wiring space."""
    s, c = R.tile_board(P.tile_clearance_mm)
    top = -P.plate_mm
    bottom = c[2] - s[2] / 2
    return union(place(k.frame, R.mx_switch_room() + [R.box((s[0], s[1], top - bottom), (c[0], c[1], (top + bottom) / 2))]))


def tile_shaft(k):
    """Key k's tile's shaft, from it down the key's axis through the underside
    (the tile goes in from below, square to its switch, and the switch plugs
    into it through the plate): wiring space, which may run into a
    neighbouring key's shaft but not its seat. Carried straight down instead,
    a tilted tile's shaft runs past a lower neighbour's ledge."""
    s, c = R.tile_board(P.tile_clearance_mm)
    pts = np.array([xform(k.frame, p) for p in box_corners(s, c)])
    return Manifold.hull_points(np.r_[pts, pts - 2 * L.floor_drop() * k.frame[:3, 2]])


def key_room(k):
    """Key k's room as one cutter: the switch's, and the socket's pocket and
    shaft or the tile's seat and shaft. A tile hangs from its switch, as on
    the Capybara, so nothing stands under it."""
    if P.key_parts == "tiles":
        return union([tile_seat(k), tile_shaft(k)])
    return union(place(k.frame, R.mx_switch_room() + R.hotswap_socket_room()) + socket_shaft(k, P.socket_clearance_mm))


def hang_room(k):
    """What hangs under key k's switch with its clearance (parts.py
    hanging_boxes) and under_socket_mm under that along the key's axis, as one
    cutter: the plinth is lifted to clear it (layout.py world_frame) but cut
    from it too where the plinth rises under a neighbour."""
    pts = np.array([xform(k.frame, c) for s, m in R.hanging_boxes() for c in box_corners(s, m)])
    return Manifold.hull_points(np.r_[pts, pts - P.under_socket_mm * k.frame[:3, 2]])


def bay_rooms(plinth=False):
    """The parts' rooms in the well, cut from the plinth (where the switch's
    pocket opens up through the plate's top) and from the body where they reach
    above the plate's top. The battery's lead notch is one of them, as tall
    as the pocket."""
    up = 100 if plinth else 0
    out = place(mcu_frame(), R.mcu_room())
    if P.knob:
        out += place(knob_frame(), R.knob_room(knob_slot_reach(), up))
    if P.link == "trrs":
        return out + place(trrs_frame(), R.trrs_room(up)) + place(reset_frame(), R.reset_room(up))
    out += place(battery_frame(), R.battery_room())
    out.append(floor_box(L.lead_notch(), bay_pocket_h()))
    if P.power_switch:
        out += place(power_switch_frame(), R.power_switch_room(up))
    return out


def insert_holes():
    return [R.insert_hole().translate((p[0], p[1], floor_z(p[0], p[1]))) for p in L.screw_points()]


@cached
def body_cuts():
    """Everything cut from the body but the screws' insert holes, in named groups."""
    ks = keys()
    return [("a key's room", [key_room(k) for k in ks]), ("a solder well", [w for k in ks for w in solder_wells(k)]),
            ("a diode's room", [d for k in ks for d in diode_rooms(k)]), ("a channel", channel_solids()),
            ("a bay room", bay_rooms())]


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
    return [h.translate((p[0], p[1], 0)) for p in L.screw_points() for h in R.screw_hole(plate_z(p[0], p[1]))]


@cached
def plate_cuts():
    """Everything cut from the plinth but the screw holes, in named groups."""
    cuts = [("the well", well()), ("a bay room", bay_rooms(plinth=True)),
            ("a key's hang room", [hang_room(k) for k in keys()])]
    if P.link == "ble":
        cuts.append(("the reset pinhole", pinhole()))
    return cuts


def pinhole():
    """The pinhole over the controller's reset button, when it has one."""
    return place(mcu_frame(), [R.mcu_reset_hole()]) if P.link == "ble" else []


def plate_cutters():
    return [s for _, group in plate_cuts() for s in group]


@cached
def bottom_plate():
    """The plinth: up to the body's underside, with the well, the screw holes and
    the pinhole over the reset button, and the socket bosses standing on it."""
    shell = plinth_shell()
    t = time.time()
    bosses = [] if P.key_parts == "tiles" else [socket_boss(k) for k in keys()]
    plate = add(subtract(shell, plate_cutters() + screw_holes()), bosses)
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
    """What hangs under each switch: its socket, or its tile."""
    return at_keys(R.key_tile() if P.key_parts == "tiles" else R.hotswap_socket())


def diodes():
    return [] if P.key_parts == "tiles" else at_keys(R.diode(), diode_frame)


def electronics():
    parts = [(mcu_frame(), R.mcu_board())]
    if P.link == "trrs":
        parts += [(trrs_frame(), R.trrs_jack()), (reset_frame(), R.reset_switch())]
    else:
        parts.append((battery_frame(), R.battery()))
        if P.power_switch:
            parts.append((power_switch_frame(), R.power_switch_part()))
    if P.knob:
        parts.append((knob_frame(), R.knob(P.knob_d_mm)))
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


def closed_ports():
    """The openings that should break out through the wall (the controller's
    port, the TRRS plug's hole, the reset switch's plunger hole, the knob's
    bearing pocket) but stop inside the outline."""
    ports = [("the controller's port", mcu_frame(), R.mcu_opening())]
    if P.link == "trrs":
        ports += [("the TRRS plug's hole", trrs_frame(), R.trrs_plug_hole()),
                  ("the reset switch's plunger hole", reset_frame(), R.reset_plunger_hole())]
    if P.knob:
        ports.append(("the knob's bearing pocket", knob_frame(), R.knob_bearing_pocket()))
    inside = polygon(outline()).extrude(400).translate((0, 0, -200))
    return [name for name, m, hole in ports if (placed(m, hole) - inside).volume() <= 1e-6]


def parts_buried():
    """The bought parts (the electronics, sockets or tiles, and diodes) that run
    into the body or the plinth, as (part, which, mm^3); empty when all sit
    in their rooms."""
    out = []
    for p in electronics() + sockets() + diodes():
        for what, s in (("the body", body()), ("the plinth", bottom_plate())):
            v = (p.solid ^ s).volume()
            if v > 1e-3:
                out.append((p.label, what, v))
    return out


def knob_clashes():
    """What the knob's room outside the wall (parts.py knob_clear) runs into
    (the desk, the body or the plinth), and whether its rooms in the case
    (all but the bearing's pocket, which opens out of the boss) break out of
    it; empty when it turns clear and its rooms stay in."""
    room = placed(knob_frame(), R.knob_clear(P.knob_d_mm))
    out = [] if room.bounding_box()[2] > 0 else ["the desk"]
    out += [what for what, solid in (("the body", body()), ("the plinth", bottom_plate()))
            if (room ^ solid).volume() > 1e-6]
    inside = union(place(knob_frame(), R.knob_room(knob_slot_reach())[1:]))
    case = union([body_shell(), plinth_shell(), plinth_shell().translate((0, 0, P.plate_gap_mm))])
    if (inside - case).volume() > 1e-6:
        out.append("the outside, through the case")
    return out


def part_overlap():
    """How much the body and the plinth overlap, mm^3 (0 when the plinth stays
    under the body's underside)."""
    return (body() ^ bottom_plate()).volume()


def wire_ends():
    """Where wires start, by name, each a point just inside the space cut for
    it (a wire's width in): every key's two socket tabs or tile holes (in
    their channels), the battery's leads (out of its back end) and the power
    switch, or the jack and the reset switch; and the controller."""
    d = P.wire_d_mm
    ends = []
    for k in keys():
        ends += [(f"{k.name}'s column tab", c_tab(k) - (0, 0, d)), (f"{k.name}'s row tab", r_tab(k) - (0, 0, d))]
    m, z = L.mcu_bay(), bay_z() + d
    if P.link == "trrs":
        ends += [("the TRRS jack", xform(trrs_frame(), [0, -P.trrs_body_mm[0] / 2, P.trrs_body_mm[2] + d])),
                 ("the reset switch", xform(reset_frame(), [P.reset_body_mm[2] + d, 0, 0]))]
    else:
        b = L.battery_bay()
        ends.append(("the battery's leads", np.array([(b[0][0] + b[1][0]) / 2, b[1][1] - d, z])))
        if P.power_switch:
            ends.append(("the power switch", origin(power_switch_frame())))
    if P.knob:
        x, w = R.knob_sensor_x()[1] + P.knob_clearance_mm - P.channel_w_mm / 2, P.channel_w_mm
        ends.append(("the knob's sensor", xform(knob_frame(), [x, 0, R.knob_sensor_z()[0] - w / 2])))
    ends.append(("the controller", np.array([(m[0][0] + m[1][0]) / 2, (m[0][1] + m[1][1]) / 2, z])))
    return ends


def unwired():
    """The wire ends that no path a wire fits through (wire_d_mm), through the
    spaces cut from the body and the plinth (channels, pockets, the well; see
    lost), joins to the controller's. The space is shrunk by the wire's radius
    along each axis, which closes the slivers where one cut grazes another."""
    space = union([lost(body_shell(), body_cutters(), True), lost(plinth_shell(), plate_cutters())])
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
    and between the bay and every channel but the one into it, as a list of
    (room, room, wall mm), empty when every wall is thick enough. Channels
    join keys by design, so they are held only to the bay. A tile's room is
    its seat (tile_seat), and its shaft, wiring space like a channel, is held
    to the other keys' seats and to the bay. A bay under the keys is wiring
    space too, which the shafts and channels over it open into: they are
    not held to it. The knob's room is the bay's."""
    tiles = P.key_parts == "tiles"
    rooms = [(k.name, lost(body_shell(), [tile_seat(k)] if tiles else
                           [key_room(k), *solder_wells(k), *diode_rooms(k)], True)) for k in keys()]
    bay = union([lost(body_shell(), bay_rooms(), True),
                 lost(plinth_shell(), well() + bay_rooms(plinth=True) + pinhole())])
    rooms.append(("the bay", bay))
    pairs = [(a, b) for i, a in enumerate(rooms) for b in rooms[i + 1:]]
    if tiles:
        shafts = [(f"{k.name}'s shaft", lost(body_shell(), [tile_shaft(k)], True)) for k in keys()]
        pairs += [(s, r) for i, s in enumerate(shafts) for j, r in enumerate(rooms)
                  if i != j and not (r[0] == "the bay" and P.bay_place == "under")]
    if P.bay_place != "under":
        pairs += [((f"the channel ({a[0]:.1f}, {a[1]:.1f}) to ({b[0]:.1f}, {b[1]:.1f})",
                    lost(body_shell(), [run_solid(a, b, w)], True)), ("the bay", bay))
                  for a, b, w in channel_segments() if not np.array_equal(b, bay_entry())]
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
    for i, p in enumerate(L.screw_points()):
        x, y = float(p[0]), float(p[1])
        name = f"screw {i + 1} ({x:.1f}, {y:.1f})"
        holes = [(h.translate((x, y, 0)), plate_cuts()) for h in R.screw_hole(plate_z(x, y))]
        holes.append((R.insert_hole().translate((x, y, floor_z(x, y))), body_cuts()))
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
    reach = ""
    if P.key_layout == "hand":
        reach = (f"fingertip reach between rows "
                 f"{[r2(L.finger_plate_pitch(i) * L.finger_reach_radius(i) / L.finger_plate_radius(i)) for i in range(4)]}"
                 " mm (index to pinky); ")
    (wall, screw, what), _ = screw_walls()
    return (f"plate tops {r2(min(plates))} to {r2(max(plates))} mm over the desk; cap tops {r2(min(tops))} to "
            f"{r2(max(tops))} mm; body shell {r2(L.floor_drop())} mm thick; plinth {r2(min(floors))} to "
            f"{r2(max(floors))} mm under the keys; well floor {r2(bay_z())} mm; {reach}plan {r2(x1 - x0)} x {r2(y1 - y0)} mm; "
            f"least wall round a screw {r2(wall)} mm ({screw} to {what})")

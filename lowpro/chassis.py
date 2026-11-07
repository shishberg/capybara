"""The body: the key field's top surface blended from the key cells, walled,
down to a flat underside on the seam, with the switch and socket pockets, the
wire channels and the well for the controller and battery; and the bottom plate:
a plinth up to the seam, with the socket bosses.

Everything here is in world axes (layout.py). The body's blank is a mesh built
here (the top surface and the round sampled from their functions, the walls one
vertical quad per outline segment); everything cut from it or added to it, and
the plinth, is an exact Manifold solid, and the booleans are Manifold's. The expensive results are cached,
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
# heights abut it ramps between them over twice that rather than stepping. The
# top surface is a quadratic spline through this field sampled every
# surface_step_mm (top_fit): taking each plane at its cell's nearest point
# creases the field along the lines that carry the cells' edges out, and the
# spline smooths those over a step. Each key's land is then laid into it
# (top_height): the plate's plane for switch_land_mm round the switch's hole,
# tapering over switch_taper_mm to the spline.
def plate_at(k, x, y):
    """Key k's plate plane over the world points (x, y): its height there, and
    the points' x and y in the key's frame."""
    inv = rinv(k.frame)
    o, n = origin(k.frame), k.frame[:3, 2]
    pz = o[2] - (n[0] * (x - o[0]) + n[1] * (y - o[1])) / n[2]
    return (pz, inv[0, 0] * x + inv[0, 1] * y + inv[0, 2] * pz + inv[0, 3],
            inv[1, 0] * x + inv[1, 1] * y + inv[1, 2] * pz + inv[1, 3])


def field(x, y):
    """The key field's height over the world points (x, y) (arrays)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    D, Z = [], []
    for k in keys():
        _, lx, ly = plate_at(k, x, y)
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


def seam_up():
    """The seam's normal, the way the shafts and channels run and the way the
    parts come together: the body prints on the seam, so this is its print's z."""
    return L.seam_frame()[:3, 2]


def seam_z(x, y):
    """The seam's height over the world points (x, y)."""
    n, o = seam_up(), origin(L.seam_frame())
    return o[2] - (n[0] * (np.asarray(x) - o[0]) + n[1] * (np.asarray(y) - o[1])) / n[2]


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
    point sets of a stadium per segment: its polygon's sides, not its corners, at
    that wall, and mesh_tol_mm over it twice, for the outline's spline and then
    its chords to cut across."""
    n = 36
    r = P.min_wall_mm + 2 * P.mesh_tol_mm
    around = lambda p, w: circle_points(p, (w / 2 + r) / np.cos(np.pi / n), n)
    return [around(a, w) + around(b, w)
            for w, pts in channels() for a, b in zip(pts[:-1], pts[1:])]


def ring_corner():
    """A disc in the corner where the ring column's foot meets the notch beside it,
    touching the wall down that side and the wall along the front trunk, so that the
    corner is one arc and not the cell's round with the trunk's end standing out of it."""
    c = np.array(cell_corners(L.key_named("ring_-1"))[0][:2])
    foot = min(p[1] for pts in channel_points() for p in pts if np.hypot(*(np.array(p) - c)) < 2 * P.wall_mm)
    r = P.ring_corner_round_mm
    return polygon(circle_points((c[0] - P.wall_mm + r, foot + r), r, 144))


def cells_2d():
    """The cells and the bays in plan, before the wall."""
    return fused([cell_face(k) for k in keys()] + [bay_face(L.bay_outline_rect())])


def hulls_2d():
    """The finger field (its cells and the bays) and the thumb cluster each as a
    convex hull, and the bridge joining them: the thumb row, the two bottom keys
    nearest it and the bays on the inner side, so the inner edge runs straight
    from the bays to the thumb."""
    bays = bay_points(L.bay_outline_rect())
    finger = hull_of([c for k in keys() if k.group != "thumb" for c in cell_corners(k)] + bays)
    thumb = hull_of([c for k in keys() if k.group == "thumb" for c in cell_corners(k)])
    bridge = hull_of([c for k in keys() if k.group == "thumb" or (k.group == "finger" and k.col <= 1 and k.row == -P.rows_below)
                      for c in cell_corners(k)] + bays)
    return fused([finger, thumb, bridge])


def signed_area(pts):
    x, y = pts[:, 0], pts[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


@cached
def outline_curve():
    """The body's outline as a smooth closed curve: outline_style "hulls" is the
    hulls joined, "closed" the cells and bays closed up (gaps narrower than
    2 * outline_close_mm filled). Either way the gaps that remain get a round
    of outline_close_mm, the wall goes round it, the inside corners are rounded to what the wall leaves of outline_close_mm
    and the convex ones to outline_round_mm, and the channels are kept
    min_wall_mm inside, after the rounding so that it can't cut into their wall.
    The offsets leave a polygon of straight
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
    channel_walls = [hull_of(pts) for pts in channel_points()]
    s = fused([s, ring_corner()] + channel_walls)
    inside = P.outline_close_mm - P.wall_mm
    for amount in (inside, -inside, -P.outline_round_mm, P.outline_round_mm):
        s = offset(s, amount)
    s = fused([s] + channel_walls)
    for amount in (inside, -inside):
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
    floor = seam_z(q[:, 0], q[:, 1])
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
def plan_mesh(boundary, fill=True, rings=()):
    """A triangulation of a counterclockwise plan polygon (N x 2) whose sides it
    keeps whole, with points inside about mesh_mm apart (fill) or none. Each of
    `rings` inside it, a pair of closed loops of as many points, has edges along
    both and from each point of one to the same point of the other. Returns the
    vertices, the polygon's first, and the triangles, counterclockwise."""
    n = len(boundary)
    around = lambda i: np.c_[i, np.roll(i, -1)]
    sides, start = [around(np.arange(n))], n
    for inner, outer in rings:
        i = start + np.arange(len(inner))
        o = i + len(inner)
        sides += [around(i), around(o), np.c_[i, o]]
        start = o[-1] + 1
    opts = "pYQ" + (f"q25a{0.5 * P.mesh_mm ** 2:.6f}" if fill else "")
    out = triangle.triangulate({"vertices": np.vstack((boundary, *(c for r in rings for c in r))), "segments": np.vstack(sides)}, opts)
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


# The body before anything is cut from it is one closed mesh, and its outer wall is
# built here and nothing cuts it afterwards except what is meant to go through the wall (the USB
# opening, the power switch's knob): one vertical quad per outline segment, its
# corners on the stations, so it is exactly vertical. Its underside is one
# triangulation of the outline (plan), on the seam.
@cached
def plan():
    """The plan inside the outline, triangulated: its vertices (the outline's
    stations first) and triangles."""
    return plan_mesh(outline())


def land_half():
    """Half the side of a key's flat land, in the key's frame."""
    return P.switch_cutout_mm / 2 + P.switch_land_mm


def land_loop(k, half):
    """The square `half` from key k's centre on its plate, in plan, counterclockwise,
    as many points whatever its size, about mesh_mm apart on the taper's outer edge."""
    s = np.linspace(-half, half, math.ceil(2 * (land_half() + P.switch_taper_mm) / P.mesh_mm), endpoint=False)
    h = np.full_like(s, half)
    sq = np.r_[np.c_[s, -h], np.c_[h, s], np.c_[-s, h], np.c_[-h, -s]]
    return sq @ k.frame[:2, :2].T + k.frame[:2, 3]


def top_height(xy):
    """The finished top's height over the plan points xy (N x 2): the top surface,
    with each key's land laid into it."""
    z = top_surface(xy)
    x, y = xy[:, 0], xy[:, 1]
    for k in keys():
        plate, lx, ly = plate_at(k, x, y)
        t = (np.maximum(np.abs(lx), np.abs(ly)) - land_half()) / P.switch_taper_mm
        z = np.where(t < 1, plate + (z - plate) * np.clip(t, 0, 1), z)
    return z


@cached
def body_shell():
    """The body before anything is cut from it: its vertices the underside's, on the
    seam (the outline's stations first), the round's sections (the first of each on
    the outline, level with the ball's centre: the wall's top), then the top's
    inside the round, with edges round each land's taper and across it."""
    t = time.time()
    rings = [(land_loop(k, land_half()), land_loop(k, land_half() + P.switch_taper_mm)) for k in keys()]
    reach = fused([polygon(outer) for _, outer in rings]) - top_contact_2d()
    if reach.area() > 1e-6:
        x0, y0, _, _ = reach.bounds()
        raise ValueError(f"a key's land reaches the top edge's round near ({x0:.1f}, {y0:.1f})")
    q = outline()
    n = len(q)
    rows = round_sections()
    m = rows.shape[1]
    vu, tu = plan()
    u = len(vu)
    vi, ti = plan_mesh(rows[:, -1, :2], rings=rings)
    station = np.arange(n)
    ring = [u + station * m + j for j in range(m)]
    top = np.where(ti < n, u + ti * m + m - 1, u + n * m + ti - n)
    vertices = np.r_[np.c_[vu, seam_z(vu[:, 0], vu[:, 1])], rows.reshape(-1, 3),
                     np.c_[vi[n:], top_height(vi[n:])]]
    triangles = [tu[:, ::-1], walled(station, ring[0])] + [walled(ring[j], ring[j + 1]) for j in range(m - 1)] + [top]
    shell = solid_from(vertices, np.concatenate(triangles), "body's shell")
    stage("the body's shell", t)
    return shell


# A cut that meets a face it should pass through starts this far inside it, as
# faces that nearly coincide leave slivers.
put_back_mm = 0.1


def half_space(m, z, below=True, size=200):
    """Everything in frame m below (or above) its plane z, within `size`."""
    return placed(m, Manifold.cube((size, size, size)).translate((-size / 2, -size / 2, z - size if below else z)))


@cached
def plinth_shell():
    """The plinth before anything is cut from it: the outline and the skirt, from
    the desk up to plate_gap_mm under the seam."""
    q = outline()
    low = seam_z(q[:, 0], q[:, 1]) - P.plate_gap_mm
    if low.min() <= 0:
        x, y = q[low.argmin()]
        raise ValueError(f"the plinth's top reaches the desk at ({x:.1f}, {y:.1f})")
    return add(polygon(q).extrude(100), [skirt()]) ^ half_space(L.seam_frame(), -P.plate_gap_mm, size=600)


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
    plinth so the two are one solid."""
    closed, gaps = skirt_faces()
    lapped = gaps.offset(1, JoinType.Round, 2.0, 16) ^ closed
    return union([lapped.extrude(P.skirt_h_mm), cove_ring() ^ lapped.extrude(100)])


# ---------------------------------------------------------------- the bay's well
def bay_pocket_h():
    """The pocket height the parts need over the well's floor."""
    return max(P.mcu_parts_mm + P.mcu_board_mm[2] + P.mcu_clearance_mm,
               P.battery_mm[2] + P.battery_clearance_mm)


@cached
def bay_frame():
    """The bays' plan carried onto the seam, which is the well's floor: z = 0 of
    the plan on the seam, turned about the middle of the bays."""
    c = np.mean(L.bay_rect(), axis=0)
    m = L.seam_frame().copy()
    m[:3, 3] = (c[0], c[1], seam_z(c[0], c[1]))
    return m @ trans([-c[0], -c[1], 0])


def mcu_frame():
    """The board's plan, level on the desk: z = 0 the top of its rest, on the seam
    at the middle of the port end."""
    m = L.mcu_frame()
    return trans([0, 0, float(seam_z(m[0, 3], m[1, 3]))]) @ m


def battery_frame():
    """The battery's plan on the floor of its pocket in the plinth."""
    return bay_frame() @ trans([0, 0, -P.bay_pocket_mm]) @ L.battery_frame()


def power_switch_frame():
    """The switch's frame, a clearance over the well's floor, which holds it in its pocket."""
    return bay_frame() @ trans([0, 0, P.power_switch_mm[2] / 2 + P.power_switch_clearance_mm]) @ L.power_switch_frame()


def reset_button_frame():
    """The switch's frame, its plunger's centre on the seam between the plinth
    and the body, so the hole in the wall is half in each."""
    return bay_frame() @ L.reset_button_frame()


def floor_box(r, h):
    """The plan rectangle r ((x0, y0), (x1, y1)) from just under the well's floor,
    so that it opens through the seam, up h."""
    return placed(bay_frame(), Manifold.cube((r[1][0] - r[0][0], r[1][1] - r[0][1], h + put_back_mm)).translate((r[0][0], r[0][1], -put_back_mm)))


def well():
    """The well: the board's room with the port end's slot in the back wall, the
    battery's bay and its lead notch, each from the seam up to well_roof_mm under
    the top."""
    ceiling = body_shell().translate((0, 0, -P.well_roof_mm))
    board = placed(mcu_frame(), R.mcu_pocket(100))
    return [s ^ ceiling for s in (board, floor_box(L.battery_bay(), 100), floor_box(L.lead_notch(), 100))]


def press_strip():
    """The strip down from the well's ceiling along the middle of the board, over
    the board by mcu_press_gap_mm, which foam takes up. The wires reach the board
    either side of it and past its south end."""
    (w, length), y0 = P.mcu_press_mm, P.mcu_press_start_mm
    z = R.mcu_pcb_z() + P.mcu_board_mm[2] + P.mcu_press_gap_mm
    return placed(mcu_frame(), R.box((w, length, 30), (0, y0 + length / 2, z + 15))) ^ body_shell()


# ---------------------------------------------------------------- wiring points
# In a key's frame, at the socket's top: the column channel's centre (col_x),
# the column wire's line past the -x tab (lane_x), a thumb key's column wire's
# line past the +x tab (thumb_col_x), the line over the +x tab (row_x), and the
# row channel's line north of the socket (ne_y).
def socket_end_x():
    """The -x end of the right half's socket. The column channels stand off it in
    both halves: the left half's socket stops short of it, so that half's -x tab
    only reaches the channel."""
    return P.socket_centre_mm[0] - P.socket_body_mm[0] / 2


def lane_x():
    """The column wire's line, beside the -x terminal's tip."""
    return socket_end_x() - P.socket_tab_mm[0] - P.wire_gap_mm - P.wire_d_mm / 2


def leg_x():
    """How far off the key's middle a diode's leg runs north to its terminal, past the side post's hole."""
    return P.switch_side_post_x + P.switch_side_post_d / 2 + P.post_clearance_mm + P.diode_room_mm + P.diode_leg_slot_mm / 2


def column_w():
    """A column channel's width: from the socket's shaft, overlapping it so no
    sliver is left between them under the tent, out past the wire beside the tip."""
    return shaft_edge_x() - lane_x() + P.wire_d_mm / 2


def shaft_edge_x():
    return socket_end_x() - P.socket_clearance_mm + 0.1


def col_x():
    return shaft_edge_x() - column_w() / 2


def thumb_col_x():
    """A thumb key's column wire's line, beside the +x tab's tip. The left half's
    tip reaches further toward the next key, so there the channel stops as soon
    as it holds the wire, for min_wall_mm to that key's solder well."""
    return min(R.socket_tab_tip(1)[0] + P.wire_gap_mm + P.wire_d_mm / 2,
               P.socket_tab_mm[0] - socket_end_x() + P.wire_gap_mm + P.wire_d_mm - P.channel_w_mm / 2)


def row_x():
    """Over the +x tab's tip, but no further out than a channel overlapping the
    left half's shaft. That half's +x tab is the south one, so its solder well
    stops short of the shaft's north end, where the right half's cuts the wall away."""
    return min(R.socket_tab_tip(1)[0], P.channel_w_mm / 2 - shaft_edge_x())


def shaft_edge_y():
    """The channels north of a socket overlap its shaft, as a column channel does,
    and the north collar's hole inside it, because a wall between them would be
    too thin to print."""
    return max(y for _, y in R.switch_pins()) + P.socket_collar_mm[0] / 2 + P.socket_clearance_mm - 0.1


def north_collar(k):
    """The hole for the socket's north collar, from just under the socket's top,
    which a row channel climbing to a higher key reaches."""
    x, y = max(R.switch_pins(), key=lambda p: p[1])
    return place(k.frame, [R.cylinder(P.socket_collar_mm[0] + 2 * P.socket_clearance_mm, 3, (x, y, R.socket_top_z() - 0.2))])


def ne_y():
    return shaft_edge_y() + P.channel_w_mm / 2


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
        return shaft_edge_y() + P.trunk_w_mm / 2
    return R.diode_y() - P.diode_mm[1] / 2 - P.diode_room_mm - P.front_trunk_wall_mm - P.trunk_w_mm / 2


def at(k, p):
    return xform(k.frame, [p[0], p[1], R.socket_top_z()])


def c_tab(k):
    return at(k, (col_x(), R.socket_tab_tip(-1)[1]))


def x_tab(k):
    """The +x tab: a thumb key's row wire comes to it."""
    return at(k, (row_x(), R.socket_tab_tip(1)[1]))


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


def column_line(c):
    """Finger column c's channel: front trunk point (the pinky's, the longest,
    joins it higher up, so it starts level with its bottom key's diode), past its
    keys' -x tabs, back trunk point."""
    bottom = finger_key(c, -P.rows_below)
    start = [front_pt(bottom)] if c < 4 else [at(bottom, (col_x(), R.diode_y()))]
    return (start + [c_tab(finger_key(c, r)) for r in range(-P.rows_below, P.rows_above + 1)]
            + [back_pt(finger_key(c, P.rows_above))])


def column_meet(k, p, q):
    """Where the line through p and q comes to the wire's lane in k's column
    channel, short of the channel's middle (a terminal can stand there), at the
    channel's own height: a key's plane, carried on past the key, falls away from
    the channel, and a run ending on it dives out of the body's underside."""
    pts = column_line(k.col)
    along = (q - p)[:2] / np.linalg.norm((q - p)[:2])
    for a, b in zip(pts[:-1], pts[1:]):
        t = np.linalg.solve(np.c_[(b - a)[:2], (p - q)[:2]], (p - a)[:2])[0]
        if 0 <= t <= 1:
            return a + (b - a) * t - np.r_[along * (col_x() - lane_x()), 0]
    raise ValueError(f"the line from {p} to {q} misses {k.name}'s column")


def front_trunk():
    """The front trunk's points, pinky to middle column, south of the bottom
    cells' diodes. Where a column reaches further forward than the next one in,
    the trunk leaves that next cell's line straight into the column's own
    channel, so it never runs round the outside of the stagger. Where it reaches
    less far, a straight line to the next column's end point would cut across
    that cell's diode, so the trunk goes by the cell's +x corner."""
    ends = [finger_key(c, -P.rows_below) for c in range(4, 1, -1)]
    pts = []
    for a, b in zip(ends[:-1], ends[1:]):
        if (rinv(b.frame) @ np.append(front_pt(a), 1))[1] < trunk_y(-1):
            pts.append(column_meet(a, front_pt(b), at(b, (0, trunk_y(-1)))))
        else:
            if not pts:
                pts.append(front_pt(a))
            pts.append(at(b, (out_y(), trunk_y(-1))))
        pts.append(front_pt(b))
    return pts


def well_point(y, x=None):
    """A point just under the well's ceiling, by the column's wall, level with y
    (or at x): where the channels come in."""
    x = L.mcu_bay()[1][0] - 3 if x is None else x
    return np.array([x, y, top_z(x, y) - P.well_roof_mm - 1])


def bay_entry():
    """Where the back trunk reaches the well: just inside its back corner by the column."""
    return well_point(L.mcu_bay()[1][1] - 3)


def well_exits():
    """The inner column's ways straight through its wall into the well, as
    channels: one from the home key's -x tab for the home, bottom and thumb
    rows' wires, whose runs end there, and one from the top key's diode joint,
    where the column's wire ends, for that wire alone."""
    tab = c_tab(finger_key(0, 0))
    joint = at(finger_key(0, P.rows_above), (col_x(), R.diode_y()))
    return [(P.trunk_w_mm, [tab, well_point(tab[1])]), (P.channel_w_mm, [joint, well_point(joint[1])])]


def well_ends():
    """Where the channels end in the well."""
    return [bay_entry()] + [pts[-1] for _, pts in well_exits()]


def well_ways():
    """The runs into the well, carried on down through the block's wall, so that
    a wire lies into them from below."""
    ends = well_ends()
    down = 30 * seam_up()
    return [Manifold.hull_points(post_points(a, w) + post_points(b, w) + post_points(a - down, w) + post_points(b - down, w))
            for a, b, w in channel_segments() if any(np.array_equal(b, p) for p in ends)]


def finger_key(col, row):
    return L.column_key(col, row)


def row_keys():
    """The finger keys a row channel leaves for the next column: all but the top
    row and the pinky."""
    return [finger_key(c, r) for r in range(-P.rows_below, P.rows_above) for c in range(4)]


def thumb(name):
    return key_named(f"thumb_{name}")


def thumb_joint(k):
    """Where a thumb key's column wire meets its diode's +x leg."""
    return at(k, (thumb_col_x(), R.diode_y()))


def thumb_corner(k):
    """Where a thumb key's wires leave it: its north edge, on the column wire's line."""
    return at(k, (thumb_col_x(), ne_y()))


def thumb_fork():
    """Where the thumb row's wire divides, on the inner column's line past its
    bottom key. That key's frame climbs here as the top falls away, so the fork's
    height is halfway from the column's foot down to home's corner."""
    k = finger_key(0, -P.rows_below)
    return np.r_[at(k, (col_x(), trunk_y(-1) - 6))[:2], (front_pt(k)[2] + thumb_corner(thumb("home"))[2]) / 2]


def onto(p, pts):
    """The point of the polyline pts nearest p in plan, at the polyline's height."""
    ends = [(a, b) for a, b in zip(pts[:-1], pts[1:])]
    near = [a + (b - a) * np.clip(np.dot((p - a)[:2], (b - a)[:2]) / np.dot((b - a)[:2], (b - a)[:2]), 0, 1) for a, b in ends]
    return min(near, key=lambda q: np.linalg.norm((q - p)[:2]))


def thumb_column(k):
    """A thumb key's column wire's way from its diode: past its +x tab's tip to its corner."""
    return [thumb_joint(k), thumb_corner(k)]


def thumb_channels():
    """The thumb keys' channels. Each key has its column's channel and a short
    one from the +x tab to the north edge. The row wire comes down the inner
    column to the fork and divides: west to far's corner, east to home's corner
    and on along near's north edge to its corner. There it joins near's column
    wire in the thumb trunk, south of the index column's bottom diode and past that
    cell's +x corner to the middle column's foot, and goes on along the
    front trunk over x1 and x2, whose wires come up from their corners into it.
    Far's column wire goes up to the fork with the row wire, and home's on to the
    index column's foot."""
    w, t = P.channel_w_mm, P.trunk_w_mm
    near, home, far = (thumb(n) for n in ("near", "home", "far"))
    out = [(w, [thumb_corner(far), thumb_fork(), thumb_corner(home), ne(near), thumb_corner(near)]),
           (w, [thumb_corner(home), front_pt(finger_key(1, -P.rows_below))]),
           (t, [thumb_corner(near), at(finger_key(1, -P.rows_below), (out_y(), trunk_y(-1))), front_pt(finger_key(2, -P.rows_below))])]
    for k in keys():
        if k.group != "finger":
            out += [(w, thumb_column(k)), (w, [x_tab(k), ne(k)])]
        if k.group == "extra":
            out.append((w, [thumb_corner(k), onto(thumb_corner(k), front_trunk())]))
    return out


@cached
def channels():
    """The channels as polylines (width, [points...]) in world: the five finger
    columns first."""
    w, t = P.channel_w_mm, P.trunk_w_mm
    rows = range(-P.rows_below, P.rows_above + 1)
    out = [(column_w(), column_line(c)) for c in range(5)]
    # The back trunk, pinky to inner column and into the bay, the front trunk, and
    # the inner column's trunk from the thumbs' fork to the home key's tab, where
    # the lower rows' wires leave it for the well.
    out.append((t, back_trunk() + [bay_entry()]))
    out.append((t, front_trunk()))
    inner = [finger_key(0, r) for r in rows if r <= 0]
    out.append((t, [thumb_fork(), front_pt(inner[0])] + [c_tab(k) for k in inner]))
    out += well_exits()
    # Each finger row but the top one, whose wire runs in the back trunk: straight
    # along each key's north edge and on into the next column, whose channel the
    # wire then shares to that key's -x tab.
    for a in row_keys():
        out.append((w, [nw(a), column_meet(finger_key(a.col + 1, a.row), nw(a), ne(a))]))
    return out + thumb_channels()


def post_points(p, w):
    """A channel post's points at a world point: a circle of w, so a channel is w
    wide whichever way it runs and keeps the wall the outline allows it, from the
    point down the seam's normal to 3 mm under the deepest sink below the seam, so
    the hull between two posts stays open to the seam and reaches the sink's floor."""
    down = (p[2] - seam_z(p[0], p[1]) + 3 + P.trunk_sink_mm) / seam_up()[2]
    return [(x, y, p[2]) for x, y in circle_points(p, w / 2)] + [tuple(np.array((x, y, p[2])) - down * seam_up()) for x, y in circle_points(p, w / 2)]


def channel_segments():
    """Every channel's straight runs as (a, b, width)."""
    return [(a, b, w) for w, pts in channels() for a, b in zip(pts[:-1], pts[1:])]


def run_solid(a, b, w):
    return Manifold.hull_points(post_points(a, w) + post_points(b, w))


def channel_solids():
    return [run_solid(*r) for r in channel_segments()]


def channel_sinks():
    """The channels' sinks into the plinth's top, each as deep as its kind and
    stopping bottom_plate_mm over the desk."""
    shell = plinth_shell()
    above = Manifold.cube((400, 400, 100)).translate((-200, -200, P.bottom_plate_mm))
    up = 100 * seam_up()
    runs = [(a + up, b + up, w) for a, b, w in channel_segments()]
    return [(union([run_solid(*r) for r in runs if (r[2] == P.trunk_w_mm) == trunk]) ^ above) - shell.translate(tuple(-d * seam_up()))
            for trunk, d in ((False, P.channel_sink_mm), (True, P.trunk_sink_mm))]


def diode_frame(k):
    """The diode's frame, across the key in its own pocket south of the centre
    post, its band toward the column wire."""
    return k.frame @ trans([0, R.diode_y(), R.diode_z()]) @ rot_z(90 if k.group == "finger" else -90)


def leg_slots(k):
    """Key k's diode's legs' slots as (size, centre) in the key's frame: one leg's
    out to the column wire, the other's out past the side post's hole and north
    into its terminal's solder well. A finger key's terminal is the +x tab and
    its column wire on the -x side; a thumb key's are the other way round."""
    s, x0, y, z = P.diode_leg_slot_mm, P.diode_mm[0] / 2, R.diode_y(), R.diode_z()
    side, wire = (1, shaft_edge_x()) if k.group == "finger" else (-1, thumb_col_x())
    tab = R.socket_tab_tip(side)[1]
    well = tab - P.solder_well_mm[1] / 2 + s

    def across(a, b):
        return (abs(b - a), s, s), ((a + b) / 2, y, z)
    return [across(-side * x0, wire), across(side * x0, side * (leg_x() + s / 2)),
            ((s, well - y, s), (side * leg_x(), (well + y) / 2, z))]


def diode_room(k):
    """Room for key k's diode, its pocket and then its legs' slots, open down to
    the underside to put it in, as a list of cutters. They go down the key's
    normal, not to the desk, so on a leaning key they stay out from under the
    post holes."""
    d, r = P.diode_mm, P.diode_room_mm
    size = (d[0] + 2 * r, d[1] + 2 * r, d[1] + 2 * r)
    return [normal_swept(k.frame, *b) for b in [(size, (0, R.diode_y(), R.diode_z())), *leg_slots(k)]]


def swept(m, size, centre, depth=60):
    """A box drawn in frame m carried down the seam's normal by `depth`, so
    shafts and wells stand square to the seam however the key tilts, and the
    plinth's bosses go straight up them."""
    pts = np.array([xform(m, c) for c in box_corners(size, centre)])
    return Manifold.hull_points(np.r_[pts, pts - depth * seam_up()])


def normal_swept(m, size, centre, depth=60):
    """A box drawn in frame m carried down frame m's own z by `depth`."""
    pts = [np.array(c, float) for c in box_corners(size, centre)]
    return Manifold.hull_points([xform(m, c - (0, 0, z)) for c in pts for z in (0, depth)])


def socket_shaft(k, grow):
    """The socket's shaft from its pocket down through the body's underside, `grow` round the body."""
    return [swept(k.frame, s, c) for s, c in R.socket_boxes(grow)]


def solder_wells(k):
    """Room round each of key k's socket terminals to solder to it: solder_well_mm
    reaching solder_well_reach_mm past the tab's tip, cut back in plan to stay solder_well_inset_mm inside the
    cell at the socket's top, so it keeps that wall from the next key's room
    and from the bay. The -x well then ends just past its tab's tip."""
    s = P.solder_well_mm
    x, y = k.cell[0] / 2 - P.solder_well_inset_mm, k.cell[1] / 2 - P.solder_well_inset_mm
    edge = np.array([xform(k.frame, [i * x, j * y, R.socket_top_z()]) for i in (-1, 1) for j in (-1, 1)])
    inside = Manifold.hull_points(np.r_[edge + 10 * seam_up(), edge - 60 * seam_up()])
    return [swept(k.frame, (s[0], s[1], 0.6), R.socket_tab_tip(side) + (side * (P.solder_well_reach_mm - s[0] / 2), 0, -0.3)) ^ inside
            for side in (-1, 1)]


# ---------------------------------------------------------------- the body
def key_room(k):
    """Key k's room (switch, socket and shaft) as one cutter."""
    return union(place(k.frame, R.mx_switch_room() + R.hotswap_socket_room()) + socket_shaft(k, P.socket_clearance_mm))


def bay_rooms(plinth=False):
    """The parts' rooms in the well, cut from the body, and from the plinth where
    they reach under the well's floor. The battery's lead notch is one of them,
    as tall as the pocket; the power switch's is the body's alone, and the reset
    button's is half in each."""
    out = place(mcu_frame(), R.mcu_room(plinth)) + place(battery_frame(), R.battery_room())
    out.append(floor_box(L.lead_notch(), bay_pocket_h()))
    if P.power_switch and not plinth:
        out += place(power_switch_frame(), R.power_switch_room())
    return out + place(reset_button_frame(), R.reset_button_room())


@cached
def screw_seats():
    """The plinth's top at each screw."""
    return [float(seam_z(*p)) - P.plate_gap_mm for p in L.screw_points()]


def insert_hole_at(p, seat):
    return R.insert_hole().translate((p[0], p[1], seat + P.plate_gap_mm))


def insert_holes():
    return [insert_hole_at(p, z) for p, z in zip(L.screw_points(), screw_seats())]


@cached
def body_cuts():
    """Everything cut from the body but the screws' insert holes, in named groups."""
    ks = keys()
    return [("a key's room", [key_room(k) for k in ks]), ("a solder well", [w for k in ks for w in solder_wells(k)]),
            ("a diode's room", [s for k in ks for s in diode_room(k)]), ("a channel", channel_solids()), ("the well", well()), ("a way into the well", well_ways()),
            ("a bay room", bay_rooms())]


def body_cutters():
    return [s for _, group in body_cuts() for s in group]


def cap_rooms():
    """Each cap's sweep. A key lower than its neighbour has its cap come down
    past the neighbour's plate, so it takes a notch out of the plate's edge."""
    return [placed(k.frame, R.keycap_room(k.cap_row, k.units)) for k in keys()]


@cached
def body():
    shell = body_shell()
    t = time.time()
    body = add(subtract(shell, body_cutters() + cap_rooms() + insert_holes()), [press_strip()])
    body.num_tri()   # Manifold evaluates lazily: make the cut happen here
    stage("body cuts", t)
    return body


# ---------------------------------------------------------------- the bottom plate
def socket_boss(k):
    """The boss under key k's socket: the socket's shaft, inset, standing on the
    plinth's top up to just under the socket (and reaching put_back_mm into the
    plinth, so the two meet in a volume)."""
    return (union(socket_shaft(k, -P.boss_inset_mm)) ^ half_space(k.frame, R.socket_bottom_z() - P.boss_clearance_mm)
            ^ half_space(L.seam_frame(), -P.plate_gap_mm - put_back_mm, below=False, size=600))


def mcu_rest():
    """The rest in the plinth's pocket: the port stands on it, from the port's end
    along the board's middle, and it reaches put_back_mm into the pocket's floor."""
    w, n, h = P.mcu_usb_mm[0], P.mcu_rest_mm, P.bay_pocket_mm + put_back_mm
    return placed(mcu_frame(), R.box((w, n, h), (0, n / 2 - P.mcu_usb_overhang_mm, -h / 2)))


def screw_holes():
    return [h.translate((p[0], p[1], 0)) for p, z in zip(L.screw_points(), screw_seats()) for h in R.screw_hole(z)]


@cached
def plate_cuts():
    """Everything cut from the plinth but the screw holes, in named groups."""
    return [("a bay room", bay_rooms(plinth=True)), ("a channel", channel_sinks())]


def plate_cutters():
    return [s for _, group in plate_cuts() for s in group]


@cached
def bottom_plate():
    """The plinth: up to the seam, with the screw holes, and the socket bosses and the board's rest standing on it."""
    shell = plinth_shell()
    t = time.time()
    plate = add(subtract(shell, plate_cutters() + screw_holes()), [socket_boss(k) for k in keys()] + [mcu_rest()])
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
    parts = [(mcu_frame(), R.mcu_board()), (battery_frame(), R.battery()), (reset_button_frame(), R.reset_button_part())]
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
    under the seam)."""
    return (body() ^ bottom_plate()).volume()


def part_clashes():
    """The bought parts that meet the body or the plinth, as (part, which, overlap
    mm^3): the switches, sockets, diodes and electronics in place and the caps at the
    bottom of their travel."""
    groups = [switches(), sockets(), diodes(), electronics(), keycaps(P.cap_travel_mm)]
    out = []
    for solid, which in ((body(), "the body"), (bottom_plate(), "the plinth")):
        for group in groups:
            if (union([p.solid for p in group]) ^ solid).volume() > 1e-3:
                out += [(p.label, which, v) for p in group for v in [(p.solid ^ solid).volume()] if v > 1e-3]
    return out


def blocked_parts():
    """The electronics that can't go straight into the well with the body upside
    down: what each meets of the body on its way past the seam, as (part, overlap
    mm^3)."""
    steps = np.arange(0, 12.25, 0.25)
    swept = [(p.label, Manifold.batch_boolean([p.solid.translate(tuple(-d * seam_up())) for d in steps], OpType.Add)) for p in electronics()]
    return [(label, v) for label, s in swept for v in [(s ^ body()).volume()] if v > 1e-3]


def true_part_clashes():
    """The keys of the left half where a real switch or socket, the same parts as
    the right half's and not mirrored, meets the finished body as it's written:
    part_clashes works before the mirror, with the parts drawn for it, so it
    can't see one drawn the wrong way round. As (key, overlap mm^3)."""
    if P.half != "left":
        return []
    P.half = "right"
    real = [p.solid for p in R.mx_switch() + R.hotswap_socket()]
    P.half = "left"
    flip = np.diag([-1.0, 1, 1, 1])
    written = body().mirror((1, 0, 0))
    hits = [(k.name, sum((placed(flip @ k.frame @ flip, s) ^ written).volume() for s in real)) for k in keys()]
    return [(name, v) for name, v in hits if v > 1e-3]


def tab_off():
    """How far from a terminal's middle a row wire ends: a wire's width off its north face."""
    return P.socket_tab_mm[1] / 2 + P.wire_d_mm


def wire_ends():
    """Where wires start, by name, each a point just inside the space cut for
    it (a wire's width in): every key's row end (a wire's width off its terminal's
    north face in its channel) and column end (its joint to the diode's leg), the
    battery's leads (out of its back end),
    the power switch's pins (in their notch), and the controller."""
    d = P.wire_d_mm
    ends = []
    for k in keys():
        row, joint = ((col_x(), R.socket_tab_tip(-1)[1] + tab_off()), at(k, (col_x(), R.diode_y()))) if k.group == "finger" else ((row_x(), R.socket_tab_tip(1)[1] + tab_off()), thumb_joint(k))
        ends += [(f"{k.name}'s row tab", at(k, row) - (0, 0, d)), (f"{k.name}'s diode joint", joint - (0, 0, d))]
    m, b = L.mcu_bay(), L.battery_bay()
    ends.append(("the battery's leads", xform(bay_frame(), [(b[0][0] + b[1][0]) / 2, b[1][1] - d, d])))
    if P.power_switch:
        notch = P.power_switch_mm[1] / 2 + P.power_switch_pins_mm[1] / 2
        ends.append(("the power switch", xform(power_switch_frame(), [0, notch, d / 2])))
    ends += [("the reset button", xform(reset_button_frame(), [x, y, 0])) for x, y in R.reset_wire_ways()]
    ends.append(("the controller", xform(bay_frame(), [(m[0][0] + m[1][0]) / 2, (m[0][1] + m[1][1]) / 2, d])))
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
    y0 = R.diode_y()
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
    """The keys where the diode and its legs meet the body or the plinth: the
    glass and the line of each leg."""
    solid = union([body(), bottom_plate()])
    d, leg = P.diode_mm, P.diode_leg_d_mm
    glass = ((d[0], d[1], d[1]), (0, R.diode_y(), R.diode_z()))
    out = []
    for k in keys():
        s = solid.transform(np.asarray(rinv(k.frame)[:3, :4], float))
        legs = [(tuple(leg if a == min(size) else a - P.diode_leg_slot_mm for a in size), centre) for size, centre in leg_slots(k)]
        if any((s ^ R.box(*b)).volume() > 1e-3 for b in [glass, *legs]):
            out.append(k.name)
    return out


def terminals():
    return [s for k in keys() for s in place(k.frame, R.socket_tabs())]


def wire_centres(space):
    """Where a wire's centre can lie in a space: the space shrunk by the wire's
    radius every way round, which closes the slivers where one cut grazes another."""
    r = P.wire_d_mm / 2
    ways = [(0, 0, r), (0, 0, -r)] + [(r * np.cos(a) * np.cos(e), r * np.sin(a) * np.cos(e), r * np.sin(e))
                                      for a in np.linspace(0, 2 * np.pi, 8, endpoint=False) for e in np.radians((-45, 0, 45))]
    return Manifold.batch_boolean([space.translate(tuple(float(c) for c in v)) for v in ways], OpType.Intersect)


def unwired():
    """The wire ends that no path a wire fits through, in wire_space past what the
    finished parts and the sockets' terminals fill, joins to the controller's. Any
    path counts, so this passes a blocked channel if the wire could go round
    another way: see pinched_runs."""
    centres = wire_centres(subtract(wire_space(), [body(), bottom_plate()] + terminals()))

    def probe(p):
        return Manifold.cube((0.2, 0.2, 0.2), center=True).translate(tuple(float(c) for c in p))

    *ends, (_, controller) = wire_ends()
    home = next(c for c in centres.decompose() if (c ^ probe(controller)).volume() > 0)
    return [name for name, p in ends if (home ^ probe(p)).volume() <= 0]


def pinched_runs():
    """The channels' straight runs that a wire can't lie along from end to end:
    inside the run, above the seam (a wire left proud of it is pinched), past the terminals and whatever of the plinth stands into the body.
    A run from a terminal counts from where its wire ends, tab_off from the tab.
    As a list of (run, mm a wire gets along it, its length)."""
    centres = wire_centres(subtract(body_shell() ^ union(body_cutters()), [bottom_plate()] + terminals()))
    tabs = [x_tab(k) for k in keys() if k.group != "finger"]
    out = []
    for a, b, w in channel_segments():
        length = float(np.linalg.norm((b - a)[:2]))
        along = (b - a)[:2] / length
        spans = [(float(s.min()), float(s.max())) for piece in (centres ^ run_solid(a, b, w)).decompose()
                 for s in [(np.asarray(piece.to_mesh().vert_properties)[:, :2] - a[:2]) @ along]]
        start = tab_off() if any(np.array_equal(a, t) for t in tabs) else 0
        if not any(lo <= start and hi >= length for lo, hi in spans):
            reach = max((min(hi, length) - max(lo, 0) for lo, hi in spans), default=0)
            out.append((f"the channel ({a[0]:.1f}, {a[1]:.1f}) to ({b[0]:.1f}, {b[1]:.1f})", reach, length))
    return out


def lost(shell, cutters, open_below=False):
    """What a part loses to some of its cutters: its shell within them (they
    reach past it); for the body's, open at its underside, lowered across the
    plate gap as well, so they meet the plinth's wherever it is cut away under them."""
    space = shell ^ union(cutters)
    return union([space, space.translate((0, 0, -P.plate_gap_mm - 0.2))]) if open_below else space


def thin_walls():
    """The walls thinner than min_wall_mm between the rooms of different parts
    (each key's room, solder wells and diode's room; the bay's rooms and well),
    and between the bay and every channel but those into it, between a finger
    column's channel and the keys of other columns, between a diode's pocket and
    every channel but its own column wire's, and between a channel and the
    outside and the top, as a list of (room, room, wall mm), empty when every
    wall is thick enough. A thumb key's column channel is held to the other keys
    as a finger column's is. The other channels join keys by design, so they are
    held only to these, and a row channel to opening into the shaft it runs along,
    wherever a solder well hasn't already cut that wall away."""
    rooms = [(k.name, lost(body_shell(), [key_room(k), *solder_wells(k), *diode_room(k)], True)) for k in keys()]
    named = dict(zip([k.name for k in keys()], rooms))
    bay = union([lost(body_shell(), bay_rooms() + well(), True), lost(plinth_shell(), bay_rooms(plinth=True))])
    rooms.append(("the bay", bay))
    pairs = [(a, b) for i, a in enumerate(rooms) for b in rooms[i + 1:]]
    into_well = well_ends()
    pairs += [((f"the channel ({a[0]:.1f}, {a[1]:.1f}) to ({b[0]:.1f}, {b[1]:.1f})",
                lost(body_shell(), [run_solid(a, b, w)], True)), ("the bay", bay))
              for a, b, w in channel_segments() if not any(np.array_equal(b, p) for p in into_well)]
    for c, (w, pts) in enumerate(channels()[:5]):
        run = (f"column {c}'s channel", lost(body_shell(), [run_solid(a, b, w) for a, b in zip(pts[:-1], pts[1:])], True))
        pairs += [(run, named[k.name]) for k in keys() if not (k.group == "finger" and k.col == c)]
    for k in keys():
        pts = channels()[k.col][1] if k.group == "finger" else thumb_column(k)
        if k.group != "finger":
            run = (f"{k.name}'s column channel", lost(body_shell(), [run_solid(*pts, P.channel_w_mm)], True))
            pairs += [(run, named[j.name]) for j in keys() if j is not k]
        own = {(tuple(a), tuple(b)) for a, b in zip(pts[:-1], pts[1:])}
        pocket = (f"{k.name}'s diode pocket", lost(body_shell(), diode_room(k)[:1], True))
        pairs += [(pocket, (f"the channel ({a[0]:.1f}, {a[1]:.1f}) to ({b[0]:.1f}, {b[1]:.1f})", lost(body_shell(), [run_solid(a, b, w)], True)))
                  for a, b, w in channel_segments() if (tuple(a), tuple(b)) not in own]
    out = []
    for (a, sa), (b, sb) in pairs:
        if gap(sa, sb) < P.min_wall_mm:
            d = sa.min_gap(sb, P.min_wall_mm)
            if d < P.min_wall_mm - 1e-6:
                out.append((a, b, d))
    beside = [(k, nw(k), ne(k)) for k in row_keys()]
    well_y = R.socket_tab_tip(1)[1] + P.solder_well_mm[1] / 2
    if well_y < shaft_edge_y():
        beside += [(k, at(k, (row_x(), well_y)), at(k, (row_x(), shaft_edge_y()))) for k in keys() if k.group != "finger"]
    for k, a, b in beside:
        run = lost(body_shell(), [run_solid(a, b, P.channel_w_mm)], True)
        for name, room in (("shaft", socket_shaft(k, P.socket_clearance_mm)), ("north collar", north_collar(k))):
            d = lost(body_shell(), room, True).min_gap(run, P.min_wall_mm)
            if 1e-6 < d < P.min_wall_mm:
                out.append((f"{k.name}'s {name}", "its row channel", d))
    for a, b, w in channel_segments():
        along = [a + (b - a) * t for t in np.linspace(0, 1, 2 + int(np.linalg.norm((b - a)[:2])))]
        name = f"the channel ({a[0]:.1f}, {a[1]:.1f}) to ({b[0]:.1f}, {b[1]:.1f})"
        side = min(outline_distance(p) for p in along) - w / 2
        roof = min(float(top_height(np.array(circle_points(p, w / 2))).min()) - p[2] for p in along)
        out += [(name, wall, d) for wall, d in (("the outside", side), ("the top", roof)) if d < P.min_wall_mm - 1e-6]
    return out


def thin_tops():
    """What is cut from the body to within min_wall_mm of the top outside the keys'
    lands, as (what, volume mm^3): the lands stand on their plates, but past them
    the top falls away from what's under it."""
    shell = body_shell()
    lands = union([polygon(land_loop(k, land_half())).extrude(200) for k in keys()])
    skin = shell - shell.translate((0, 0, -P.min_wall_mm)) - lands
    return [(what, v) for what, group in body_cuts() for v in [sum((skin ^ s).volume() for s in group)] if v > 1e-6]


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
        round_it = R.cylinder(R.counterbore_d() + 0.2, 60, (x, y, put_back_mm))
        under = h - P.screw_grip_mm - (round_it - plinth_shell()).bounding_box()[2]
        if under > 0:
            hits.append((name, "the plinth's top (the counterbore breaks out through it)", np.pi * (R.counterbore_d() / 2) ** 2 * under))
        holes = [(c.translate((x, y, 0)), plate_cuts()) for c in R.screw_hole(h)]
        holes.append((insert_hole_at(p, h), body_cuts()))
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
    floors = [float(seam_z(*origin(k.frame)[:2])) for k in ks]
    rise = [(xform(k.frame, [0, 0, R.socket_bottom_z()])[2] - float(seam_z(*xform(k.frame, [0, 0, R.socket_bottom_z()])[:2]))) * seam_up()[2] for k in ks]
    reach = [r2(L.finger_plate_pitch(i) * L.finger_reach_radius(i) / L.finger_plate_radius(i)) for i in range(4)]
    (wall, screw, what), _ = screw_walls()
    return (f"plate tops {r2(min(plates))} to {r2(max(plates))} mm over the desk; cap tops {r2(min(tops))} to "
            f"{r2(max(tops))} mm; plinth {r2(min(floors))} to {r2(max(floors))} mm under the keys; sockets {r2(min(rise))} to "
            f"{r2(max(rise))} mm over the seam; fingertip reach between rows "
            f"{reach} mm (index to pinky); plan {r2(x1 - x0)} x {r2(y1 - y0)} mm, {round(polygon(outline()).area())} mm^2; "
            f"least wall round a screw {r2(wall)} mm ({screw} to {what})")

"""The body: the key field's top surface blended from the key cells, walled,
a shell of one thickness, with the switch and socket pockets and the wire
channels; and the bottom plate: a plinth up to the body's underside, with
the socket bosses and the well for the controller and battery.

Everything here is in world axes (layout.py). Solids are build123d's
(OpenCascade); the expensive ones are cached, see layout.reset().
"""
import time

import numpy as np
from build123d import Color, Compound, Edge, Face, GeomType, Kind, Plane, Shell, Solid, Wire, extrude, offset
from OCP.BRep import BRep_Builder, BRep_Tool
from OCP.BRepAlgoAPI import BRepAlgoAPI_Splitter
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeSolid, BRepBuilderAPI_Sewing
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.BRepLib import BRepLib
from OCP.BRepTools import BRepTools
from OCP.collections import (Array1_double, Array1_int, Array2_gp_Pnt, HArray1_double, HArray1_gp_Pnt, HArray1_gp_Pnt2d,
                             HArray2_gp_Pnt, List_TopoDS_Shape)
from OCP.GCPnts import GCPnts_UniformAbscissa
from OCP.Geom import Geom_BSplineCurve, Geom_BSplineSurface, Geom_SurfaceOfLinearExtrusion, Geom_TrimmedCurve
from OCP.Geom2d import Geom2d_BSplineCurve, Geom2d_TrimmedCurve
from OCP.Geom2dAPI import Geom2dAPI_Interpolate
from OCP.GeomAdaptor import GeomAdaptor_Curve
from OCP.GeomAPI import GeomAPI_Interpolate, GeomAPI_PointsToBSplineSurface
from OCP.GeomLProp import GeomLProp_SLProps
from OCP.gp import gp_Pnt, gp_Pnt2d, gp_Vec, gp_Vec2d
from OCP.GProp import GProp_GProps
from OCP.Precision import Precision
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Shell
from scipy.spatial import ConvexHull

from . import layout as L
from . import params as P
from . import parts as R
from .layout import cached, cell_corners, keys, key_named
from .lib import axis_x, axis_z, origin, r2, rinv, trans, xform

VERBOSE = False


def stage(label, t0):
    """Print how long a stage took, when VERBOSE."""
    if VERBOSE:
        print(f"  {label}: {time.time() - t0:.1f} s", flush=True)
    return time.time()


# ---------------------------------------------------------------- frames
def plane_of(m):
    """A build123d Plane for a 4x4 frame."""
    return Plane(origin=tuple(origin(m)), x_dir=tuple(axis_x(m)), z_dir=tuple(axis_z(m)))


def place(m, shapes):
    """The shapes, drawn in frame m, in world."""
    loc = plane_of(m).location
    return [loc * s for s in shapes]


# ---------------------------------------------------------------- the top surface
# A height field over the plan: inside a key's cell, its plate's plane; outside
# every cell, the nearby cells' planes blended by distance (inverse cube), each
# taken at its cell's nearest point, so no plane is extrapolated. The blend
# starts surface_blend_mm inside each cell, so where two cells of different
# heights abut it ramps between them over twice that rather than stepping; the
# cells' planes are put back exactly afterwards (body_blank), which turns the
# ramp into a step at the higher cell's edge. The body's underside is the same
# field floor_drop() lower, the plate's top plate_gap_mm under that.
def field(x, y):
    """The top surface's height over the world points (x, y) (arrays)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    D, Z = [], []
    for k in keys():
        inv = rinv(k.frame)
        o, n = origin(k.frame), axis_z(k.frame)
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
def bbox():
    """The plan's bounding box, ((x0, y0), (x1, y1)), with room for the wall."""
    pts = [c for k in keys() for c in cell_corners(k)] + list(L.screw_points()) + [c for b in L.bays() for c in b]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    m = P.wall_mm + P.outline_round_mm + 2
    return ((min(xs) - m, min(ys) - m), (max(xs) + m, max(ys) + m))


@cached
def top_face():
    """The top surface: a quadratic spline fitted through the field sampled at
    surface_step_mm over the plan. It follows the field to a few hundredths of
    a millimetre except across the cliffs between abutting cells of different
    heights, where it ramps over a grid step; the cells' planes are then put
    back exactly (body_blank)."""
    (x0, y0), (x1, y1) = bbox()
    st = P.surface_step_mm
    xs = np.arange(x0, x1 + st, st)
    ys = np.arange(y0, y1 + st, st)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    Z = field(X.ravel(), Y.ravel()).reshape(X.shape)
    pts = HArray2_gp_Pnt(1, X.shape[0], 1, X.shape[1])
    for i in range(X.shape[0]):
        for j in range(X.shape[1]):
            pts.SetValue(i + 1, j + 1, gp_Pnt(float(X[i, j]), float(Y[i, j]), float(Z[i, j])))
    fit = GeomAPI_PointsToBSplineSurface(pts, DegMin=2, DegMax=2, Tol3D=P.surface_fit_mm)
    return Face(BRepBuilderAPI_MakeFace(fit.Surface(), Precision.Confusion_s()).Face())


def floor_face():
    return top_face().translate((0, 0, -L.floor_drop()))


def plate_face():
    return top_face().translate((0, 0, -L.floor_drop() - P.plate_gap_mm))


def volume(shape):
    """A shape's volume (OpenCascade's default rule; within a percent here)."""
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape.wrapped, props)
    return props.Mass()


def solid(result):
    """The largest solid of a boolean's result (a Shape, a list or None)."""
    if result is None:
        return None
    sols = result.solids() if hasattr(result, "solids") else [s for r in result for s in r.solids()]
    return max(sols, key=volume) if sols else None


def under(face, depth=300):
    """The solid under a surface face, `depth` deep."""
    return extrude(face, amount=depth, dir=(0, 0, -1))


def over(face, height=300):
    """The solid over a surface face, `height` high."""
    return extrude(face, amount=height, dir=(0, 0, 1))


def prism(face2d, z0, h):
    """A plan face extruded from z0 up by h."""
    return extrude(face2d.translate((0, 0, z0)), amount=h, dir=(0, 0, 1))


# ---------------------------------------------------------------- the outline
def polygon(pts):
    return Face(Wire.make_polygon([(float(p[0]), float(p[1]), 0.0) for p in pts], close=True))


def cell_face(k, grow=0):
    return polygon(cell_corners(k, grow))


def bay_face(b):
    return polygon([(b[0][0], b[0][1]), (b[1][0], b[0][1]), (b[1][0], b[1][1]), (b[0][0], b[1][1])])


def fused(faces):
    faces = list(faces)
    return faces[0].fuse(*faces[1:]).clean() if len(faces) > 1 else faces[0]


def hull_of(points):
    """The convex hull of some plan points, as a face."""
    pts = np.asarray([(p[0], p[1]) for p in points], float)
    return polygon(pts[ConvexHull(pts).vertices])


def circle_points(p, r, n=36):
    return [(p[0] + r * np.cos(a), p[1] + r * np.sin(a)) for a in np.linspace(0, 2 * np.pi, n, endpoint=False)]


def bay_points(b):
    return [(b[0][0], b[0][1]), (b[1][0], b[0][1]), (b[1][0], b[1][1]), (b[0][0], b[1][1])]


def channel_points(group=None):
    """The channel paths in plan with a margin round them, as the point sets of
    a stadium per segment (those of one group when given)."""
    out = []
    for w, pts, g in channels():
        if group is not None and g != group:
            continue
        for a, b in zip(pts[:-1], pts[1:]):
            out.append(circle_points(a, w / 2 + 1) + circle_points(b, w / 2 + 1))
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


@cached
def footprint_2d():
    """The body's footprint: outline_style "hulls" is the hulls joined, "closed"
    the cells and channel paths closed up (gaps narrower than 2 * outline_close_mm
    filled). Either way the gaps that remain get a round of outline_close_mm, the
    wall goes round it and the convex corners are rounded to outline_round_mm."""
    s = hulls_2d() if P.outline_style == "hulls" else cells_2d()
    for amount in (P.outline_close_mm, -P.outline_close_mm, P.wall_mm, -P.outline_round_mm, P.outline_round_mm):
        s = offset(s, amount, kind=Kind.ARC)
    outline = max(s.faces(), key=lambda f: f.area).outer_wire()
    # The offsets leave a chain of hundreds of short lines and arcs (the hulls
    # are polygons), which a fillet along the top edge cannot follow; one smooth
    # periodic spline through the chain, sampled every outline_sample_mm, is
    # within a few hundredths of it and fillets cleanly.
    n = int(outline.length / P.outline_sample_mm)
    pts = [outline.position_at(i / n) for i in range(n)]
    return Face(Wire([Edge.make_spline(pts, periodic=True)]))


# ---------------------------------------------------------------- the blanks
def swept(solid, depth=60):
    """A solid carried straight down (in world) by `depth`: itself and the
    prisms of its downward faces, so shafts and wells stand square to the desk
    however the key tilts. Returns the pieces."""
    pieces = [solid]
    for f in solid.faces():
        if f.normal_at().Z < -1e-6:
            pieces.append(extrude(f, amount=depth, dir=(0, 0, -1)))
    return pieces


def half_space(m, z, below=True, size=60):
    """Everything in frame m below (or above) its plane z, within `size`."""
    box = Solid.make_box(size, size, size).translate((-size / 2, -size / 2, z - size if below else z))
    return place(m, [box])[0]


def top_trimmed():
    """The top surface within the footprint, as a face."""
    blank = solid(under(top_face()).intersect(prism(footprint_2d(), -1, 201)))
    return max(blank.faces().filter_by(GeomType.BSPLINE), key=lambda f: f.center().Z)


# OpenCascade intersects every tool with every face whose box it overlaps, and
# what each intersection costs grows with how much of its surface the face
# covers; the top and bottom surfaces cover the whole board. So the blank is
# split by vertical planes patch_mm apart and every face's surface is cut
# down to the face (restrict), which turns the two surfaces into a few
# hundred small patches; a boolean then only works on the patches near its
# tool, and the whole body is cut in a few operations instead of hundreds.
# The split faces inside are dropped and the pieces' outer faces, which
# already match since they came from one solid, make the solid again.
def patched(shape):
    """The solid with its surfaces in patches about patch_mm square."""
    (x0, y0), (x1, y1) = bbox()
    every = P.patch_mm
    planes = [Plane(origin=(x, 0, 0), z_dir=(1, 0, 0)) for x in np.linspace(x0, x1, round((x1 - x0) / every) + 1)[1:-1]]
    planes += [Plane(origin=(0, y, 0), z_dir=(0, 1, 0)) for y in np.linspace(y0, y1, round((y1 - y0) / every) + 1)[1:-1]]
    splitter = BRepAlgoAPI_Splitter()
    args, tools = List_TopoDS_Shape(), List_TopoDS_Shape()
    args.Append(shape.wrapped)
    for plane in planes:
        tools.Append(Face.make_rect(2 * (x1 - x0 + y1 - y0), 400, plane).wrapped)
    splitter.SetArguments(args)
    splitter.SetTools(tools)
    splitter.SetRunParallel(True)
    splitter.Build()
    pieces = Compound(splitter.Shape()).solids()
    restrict(pieces)
    count = {}
    for piece in pieces:
        for f in piece.faces():
            count[hash(f)] = count.get(hash(f), 0) + 1
    builder, shell = BRep_Builder(), TopoDS_Shell()
    builder.MakeShell(shell)
    for piece in pieces:
        for f in piece.faces():
            if count[hash(f)] == 1:
                builder.Add(shell, f.wrapped)
    return Solid(BRepBuilderAPI_MakeSolid(shell).Solid())


def restrict(shapes):
    """Each face's surface and each edge's curves cut down to the face or
    edge, in place. A face left on a surface that runs far past it costs every
    boolean near it, and an edge that is a piece of a long curve (the fillet's
    edges, split by every pocket) is written to STEP with the whole curve."""
    builder = BRep_Builder()
    for shape in shapes:
        for f in shape.faces():
            if f.geom_type not in (GeomType.BSPLINE, GeomType.EXTRUSION):
                continue
            loc = TopLoc_Location()
            surface = BRep_Tool.Surface_s(f.wrapped, loc)
            u0, u1, v0, v1 = BRepTools.UVBounds_s(f.wrapped)
            su0, su1, sv0, sv1 = surface.Bounds()
            if f.geom_type == GeomType.BSPLINE:
                part = surface.Copy()
                part.Segment(max(u0, su0), min(u1, su1), max(v0, sv0), min(v1, sv1))
            else:
                curve = surface.BasisCurve().Copy()
                curve.Segment(max(u0, su0), min(u1, su1))
                part = Geom_SurfaceOfLinearExtrusion(curve, surface.Direction())
            # The edges' curves on the face are keyed by its surface: carry them over.
            pcurves = [(e.wrapped, BRep_Tool.CurveOnSurface_s(e.wrapped, f.wrapped, 0.0, 0.0),
                        BRep_Tool.Range_s(e.wrapped, f.wrapped), BRep_Tool.Tolerance_s(e.wrapped)) for e in f.edges()]
            builder.UpdateFace(f.wrapped, part, loc, BRep_Tool.Tolerance_s(f.wrapped))
            for e, c, (p0, p1), tol in pcurves:
                builder.UpdateEdge(e, c, f.wrapped, tol)
                builder.Range(e, f.wrapped, p0, p1)
        for e in shape.edges():
            c = BRep_Tool.Curve_s(e.wrapped, 0.0, 0.0)
            if isinstance(c, Geom_TrimmedCurve):
                c = c.BasisCurve()
            p0, p1 = BRep_Tool.Range_s(e.wrapped)
            if isinstance(c, Geom_BSplineCurve) and (c.FirstParameter() < p0 - 1e-9 or c.LastParameter() > p1 + 1e-9):
                part = c.Copy()
                part.Segment(p0, p1)
                builder.UpdateEdge(e.wrapped, part, BRep_Tool.Tolerance_s(e.wrapped))
                builder.Range(e.wrapped, p0, p1, True)
        for f in shape.faces():
            for e in f.edges():
                c = BRep_Tool.CurveOnSurface_s(e.wrapped, f.wrapped, 0.0, 0.0)
                if isinstance(c, Geom2d_TrimmedCurve):
                    c = c.BasisCurve()
                p0, p1 = BRep_Tool.Range_s(e.wrapped, f.wrapped)
                if isinstance(c, Geom2d_BSplineCurve) and (c.FirstParameter() < p0 - 1e-9 or c.LastParameter() > p1 + 1e-9):
                    part = c.Copy()
                    part.Segment(p0, p1)
                    builder.UpdateEdge(e.wrapped, part, f.wrapped, BRep_Tool.Tolerance_s(e.wrapped))
                    builder.Range(e.wrapped, f.wrapped, p0, p1)


# Tools that overlap one another in one boolean give OpenCascade trouble (the
# caps of neighbouring cells, whose planes cross): those go in a few batches of
# tools that keep apart in plan. Tools that are meant to run together (a key's
# pockets and shaft, the channels) are fused into one tool first, which costs
# little on small solids and spares the big boolean every tool-to-tool
# intersection.
def apart(tools):
    """The tools in batches whose members' plan boxes do not meet."""
    boxes = [t.bounding_box() for t in tools]
    batches = []
    for i, b in enumerate(boxes):
        for batch in batches:
            if all(b.max.X < boxes[j].min.X or boxes[j].max.X < b.min.X or b.max.Y < boxes[j].min.Y or boxes[j].max.Y < b.min.Y
                   for j in batch):
                batch.append(i)
                break
        else:
            batches.append([i])
    return [[tools[i] for i in batch] for batch in batches]


def united(solids):
    """The solids fused, as a list of solids."""
    return solids[0].fuse(*solids[1:]).solids() if len(solids) > 1 else list(solids)


def column(k, grow=0):
    """Key k's cell, cell_step_mm (and `grow`) past its edge, as a vertical
    column through everything."""
    return prism(cell_face(k, P.cell_step_mm + grow), -1, 201)


def cell_cap(k, z, grow=0, below=False):
    """Everything over key k's column above (or below) the plane z of its frame."""
    return solid(column(k, grow).intersect(half_space(k.frame, z, below=below)))


def cell_block(k, z_top, z_bottom):
    """Key k's column between two planes of its frame."""
    return solid(solid(column(k).intersect(half_space(k.frame, z_top))).intersect(half_space(k.frame, z_bottom, below=False)))


# Every cell's plane is put back exactly in two steps, one cell at a time:
# whatever the blend left above the plane over the cell (and cell_step_mm plus
# a little round it) is cut away, and under the body whatever it left below
# the plane floor_drop() lower, then a block between those two planes is
# added. The caps are cut a little inside the planes and a little wider than
# the block, so no face of the caps, the block and the shell coincides with
# another, which OpenCascade is surest of (the ring round each cell is left
# that much lower on top, and that much higher underneath). The underside
# needs its cap as much as the top: the floor is the fitted surface, within
# surface_fit_mm of the block's bottom over the whole cell, and fusing the
# block onto that lost the body outright for some layouts. Where a cell meets
# a higher neighbour the surface so steps at that neighbour's edge, with
# nothing left standing in the gap, and the floor steps with it.
cap_under_mm = 0.1
cap_wider_mm = 0.3


# ---------------------------------------------------------------- the rounded top edge
# OpenCascade's fillet (BRepFilletAPI, a rolling ball marched along the edge)
# is not reliable on the one closed edge where the top surface meets the wall:
# on one and the same geometry it failed for three of ten positions of that
# edge's seam, each time differently (walking failure, twisted surface), and
# an outline or parameter change moves the seam. The round between a vertical
# wall and the top has a closed form, so it is built from that instead. At
# each station along the outline the ball's centre is top_round_mm inside the
# wall and top_round_mm under the top along the top's normal (a Newton solve
# on the top surface); its wall contact is level with the centre, its top
# contact is where that normal meets the top, and the section between them is
# an exact circular arc about the centre. One cubic spline surface through
# those arcs (periodic along the outline, the stations no further apart than
# round_step_mm as the arcs move) is the fillet, and its two edges are the
# contact curves, which lie on the top and the wall to a few 1e-5 mm. Those
# edges are given their curves on the top's and the wall's surfaces, the top
# is made inside its contact curve, the wall cut at its, and the faces sewn
# with the floor: no boolean ever has to find where the fillet touches the
# surfaces it is tangent to.
def ball_sections(curve, params, surf, up, inward, r, m, starts=None):
    """The rolling ball's sections at the outline parameters `params`: for each,
    the top contact's (u, v) on the top surface, the wall contact's height and
    the m points of the arc from the wall contact to the top contact. `starts`
    gives a first guess for each top contact's (u, v); without one, each
    station starts from the previous station's answer (a continuation along
    the outline), the first from the plan's place in the fit's parameters,
    which run about linearly over it."""
    (x0, y0), (x1, y1) = bbox()
    u0, u1, v0, v1 = surf.Bounds()

    def centred(uv, a):
        """The top point at uv, its normal, and how far its ball centre's plan is from a."""
        pnt, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()
        surf.D1(float(uv[0]), float(uv[1]), pnt, du, dv)
        n = du.Crossed(dv)
        n.Normalize()
        if not up:
            n.Reverse()
        p, n = np.array([pnt.X(), pnt.Y(), pnt.Z()]), np.array([n.X(), n.Y(), n.Z()])
        return p, n, (p - r * n)[:2] - a

    out = {}
    uv = None
    for i, s in enumerate(params):
        qp, d1 = gp_Pnt(), gp_Vec()
        curve.D1(float(s), qp, d1)
        q, t = np.array([qp.X(), qp.Y(), 0.0]), np.array([d1.X(), d1.Y(), 0.0])
        t /= np.linalg.norm(t)
        a = q[:2] + inward * np.array([-t[1], t[0]]) * r             # the ball centre's plan
        if starts is not None:
            uv = np.array(starts[i], float)
        elif uv is None:
            uv = np.array([u0 + (u1 - u0) * (a[0] - x0) / (x1 - x0), v0 + (v1 - v0) * (a[1] - y0) / (y1 - y0)])
        # Quasi-Newton on the ball centre's plan. The top is a quadratic spline,
        # so the normal's derivative jumps at its knots, and over a ridge it
        # turns through most of its range within one knot span: a Newton step
        # from a one-sided difference there overshoots and cycles. So each
        # step is shortened until the centre gets closer, and the Jacobian is
        # then corrected by the secant through the step (Broyden), which
        # sees the slope the step actually crossed.
        p, n, g = centred(uv, a)
        h = 1e-4
        J = np.column_stack([(centred(uv + (h, 0), a)[2] - g) / h, (centred(uv + (0, h), a)[2] - g) / h])
        for _ in range(60):
            if np.hypot(*g) < 1e-8:
                break
            step = np.linalg.solve(J, -g)
            for _ in range(30):
                p1, n1, g1 = centred(uv + step, a)
                if np.hypot(*g1) < np.hypot(*g):
                    break
                step /= 2
            else:
                raise RuntimeError(f"the top edge's round: no ball centre over ({a[0]:.1f}, {a[1]:.1f})")
            J += np.outer(g1 - g - J @ step, step) / (step @ step)
            uv, p, n, g = uv + step, p1, n1, g1
        else:
            raise RuntimeError(f"the top edge's round: no ball centre over ({a[0]:.1f}, {a[1]:.1f})")
        c = p - r * n
        d0 = np.array([q[0], q[1], c[2]]) - c                          # to the wall contact
        ang = np.arccos(np.clip(np.dot(d0, p - c) / r / r, -1, 1))
        perp = (p - c) - d0 * np.dot(d0, p - c) / r / r
        perp *= r / np.linalg.norm(perp)
        out[float(s)] = (tuple(uv), c[2], [c + d0 * np.cos(ang * j / (m - 1)) + perp * np.sin(ang * j / (m - 1)) for j in range(m)])
    return out


def interpolate(points, params, periodic, period=None, tangents=None):
    """A cubic B-spline through 3D or 2D points at the given parameters (periodic:
    closing at params[0] + period)."""
    flat = len(points[0]) == 2
    pts = (HArray1_gp_Pnt2d if flat else HArray1_gp_Pnt)(1, len(points))
    for i, p in enumerate(points):
        pts.SetValue(i + 1, (gp_Pnt2d if flat else gp_Pnt)(*map(float, p)))
    par = HArray1_double(1, len(points) + (1 if periodic else 0))
    for i, u in enumerate(params):
        par.SetValue(i + 1, float(u))
    if periodic:
        par.SetValue(len(points) + 1, float(params[0] + period))
    it = (Geom2dAPI_Interpolate if flat else GeomAPI_Interpolate)(pts, par, periodic, 1e-9)
    if tangents is not None:
        it.Load(gp_Vec2d(*map(float, tangents[0])), gp_Vec2d(*map(float, tangents[1])), False)
    it.Perform()
    return it.Curve()


def spline_through(rows, uparams, uperiod, vparams):
    """A cubic B-spline surface through rows[j][i] at (uparams[i], vparams[j]),
    periodic in u: each row interpolated in u, then the rows' poles in v, so
    the rows are its iso-v curves exactly."""
    ucurves = [interpolate(row, uparams, True, uperiod) for row in rows]
    cu = ucurves[0]
    vcurves = [interpolate([(c.Pole(k + 1).X(), c.Pole(k + 1).Y(), c.Pole(k + 1).Z()) for c in ucurves], vparams, False)
               for k in range(cu.NbPoles())]
    cv = vcurves[0]
    poles = Array2_gp_Pnt(1, cu.NbPoles(), 1, cv.NbPoles())
    for k, c in enumerate(vcurves):
        for j in range(cv.NbPoles()):
            poles.SetValue(k + 1, j + 1, c.Pole(j + 1))

    def knots(c):
        ks, ms = Array1_double(1, c.NbKnots()), Array1_int(1, c.NbKnots())
        for i in range(c.NbKnots()):
            ks.SetValue(i + 1, c.Knot(i + 1))
            ms.SetValue(i + 1, c.Multiplicity(i + 1))
        return ks, ms

    uk, um = knots(cu)
    vk, vm = knots(cv)
    return Geom_BSplineSurface(poles, uk, vk, um, vm, cu.Degree(), cv.Degree(), True, False)


def split_face(face, edge):
    """The face split by an edge lying on it (the edge carries its curve on the face)."""
    splitter = BRepAlgoAPI_Splitter()
    args, tools = List_TopoDS_Shape(), List_TopoDS_Shape()
    args.Append(face.wrapped)
    tools.Append(edge.wrapped)
    splitter.SetArguments(args)
    splitter.SetTools(tools)
    splitter.Build()
    return Compound(splitter.Shape()).faces()


def rounded_shell():
    """The body's shell with its top edge rounded to top_round_mm: the top
    inside the round's top contact, the round, the wall under its wall
    contact, and the floor."""
    r, m = P.top_round_mm, 11
    top = top_face()
    surf = BRep_Tool.Surface_s(top.wrapped)
    u0, u1, v0, v1 = surf.Bounds()
    pnt, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()
    surf.D1((u0 + u1) / 2, (v0 + v1) / 2, pnt, du, dv)
    up = du.Crossed(dv).Z() > 0
    fp = footprint_2d()
    oedge = fp.outer_wire().edges()[0]
    curve = BRep_Tool.Curve_s(oedge.wrapped, 0.0, 0.0)
    p0, p1 = oedge.param_at(0), oedge.param_at(1)
    t0, q0 = oedge.tangent_at(0), oedge.position_at(0)
    inward = 1 if fp.is_inside(q0 + (-t0.Y, t0.X, 0)) else -1
    # Stations: outline_sample_mm apart to begin with, then halved wherever the
    # ball's section moves more than round_step_mm between neighbours (it moves
    # fastest across the blend between cells of different heights, and at the
    # outline's corners, where the top contact turns on a radius of a millimetre).
    abscissa = GCPnts_UniformAbscissa(GeomAdaptor_Curve(curve), float(P.outline_sample_mm), p0, p1)
    sections = ball_sections(curve, [abscissa.Parameter(i + 1) for i in range(abscissa.NbPoints() - 1)], surf, up, inward, r, m)
    while True:
        at = sorted(sections)
        between = [(a, b) for a, b in zip(at, at[1:] + [at[0] + (p1 - p0)])
                   if np.linalg.norm(np.array(sections[a][2]) - np.array(sections[b % (p1 - p0) if b >= p1 else b][2]), axis=1).max() > P.round_step_mm]
        if not between:
            break
        sections.update(ball_sections(curve, [((a + b) / 2) % (p1 - p0) for a, b in between], surf, up, inward, r, m,
                                      [(np.array(sections[a][0]) + np.array(sections[b % (p1 - p0) if b >= p1 else b][0])) / 2 for a, b in between]))
    at = sorted(sections)
    rows = [[sections[s][2][j] for s in at] for j in range(m)]
    tops = np.array(rows[-1])[:, :2]
    steps = np.diff(np.vstack([tops, tops[:1]]), axis=0)
    if ((steps[:-1] * steps[1:]).sum(1) < 0).any():
        raise ValueError(f"the top edge's round folds: top_round_mm {r} is too large for outline_round_mm {P.outline_round_mm} "
                         "where the top tilts toward the edge")
    # The ball has to fit under the top along the contact: where the top is
    # convex on a radius under r the fillet would cross itself (and a fillet
    # left in that state is a crease).
    for s in at:
        props = GeomLProp_SLProps(surf, *map(float, sections[s][0]), 2, 1e-9)
        convex = -min(props.MinCurvature(), props.MaxCurvature()) * (1 if (props.Normal().Z() > 0) == up else -1)
        if convex * r > 1:
            x, y, _ = sections[s][2][-1]
            raise ValueError(f"the top edge's round: top_round_mm {r} is larger than the top's convex radius "
                             f"{1 / convex:.1f} mm at ({x:.1f}, {y:.1f})")
    # The surface's parameter along the outline: the rows' mean travel, so no
    # row runs much faster or slower than the parameter anywhere.
    chords = np.linalg.norm(np.diff(np.array([row + row[:1] for row in rows]), axis=1), axis=2).mean(0)
    uparams, uperiod = np.concatenate([[0], np.cumsum(chords)[:-1]]), float(chords.sum())
    fillet = Face(BRepBuilderAPI_MakeFace(spline_through(rows, uparams, uperiod, np.linspace(0, 1, m)), 1e-7).Face())
    closed = [e for e in fillet.edges() if e.is_closed]
    e_wall, e_top = min(closed, key=lambda e: e.center().Z), max(closed, key=lambda e: e.center().Z)
    # The body under the round: over the floor, inside the footprint's prism.
    lower = solid(over(floor_face()).intersect(prism(fp, -1, 201)))
    floor = min(lower.faces().filter_by(GeomType.BSPLINE), key=lambda f: f.center().Z)
    wall = lower.faces().filter_by(GeomType.EXTRUSION)[0]
    wall_surf = BRep_Tool.Surface_s(wall.wrapped)
    # The contact edges' curves on the top and on the wall, at the same parameter
    # as the fillet's. The wall's u is the outline's parameter, which winds once
    # round, so that curve is not periodic: it closes a period on, with the
    # periodic tangent at both ends.
    builder = BRep_Builder()
    builder.UpdateEdge(e_top.wrapped, interpolate([sections[s][0] for s in at], uparams, True, uperiod), top.wrapped, 1e-5)
    vdir = wall_surf.Value(0, 1).Z() - wall_surf.Value(0, 0).Z()
    on_wall = [(s, (sections[s][1] - wall_surf.Value(0, 0).Z()) / vdir) for s in at]
    a, b = on_wall[-1], on_wall[1]
    tangent = ((b[0] - a[0] + (p1 - p0)) / (uparams[1] + uperiod - uparams[-1]), (b[1] - a[1]) / (uparams[1] + uperiod - uparams[-1]))
    builder.UpdateEdge(e_wall.wrapped, interpolate(on_wall + [(on_wall[0][0] + (p1 - p0), on_wall[0][1])], list(uparams) + [uperiod],
                                                   False, tangents=(tangent, tangent)), wall.wrapped, 1e-5)
    for e in (e_top, e_wall):
        BRepLib.SameParameter_s(e.wrapped, 1e-5, True)
    top_inner = Face(BRepBuilderAPI_MakeFace(surf, Wire([e_top]).wrapped, True).Face())
    if top_inner.area > fp.area:
        top_inner = Face(BRepBuilderAPI_MakeFace(surf, Wire([e_top]).wrapped.Reversed(), True).Face())
    wall_lower = min(split_face(wall, e_wall), key=lambda f: f.bounding_box().max.Z)
    sewing = BRepBuilderAPI_Sewing(1e-5)
    for f in (top_inner, fillet, wall_lower, floor):
        sewing.Add(f.wrapped)
    sewing.Perform()
    if sewing.NbFreeEdges():
        raise RuntimeError("the top edge's round does not close with the top, the wall and the floor")
    shell = Solid(BRepBuilderAPI_MakeSolid(Shell(sewing.SewedShape()).wrapped).Solid())
    if volume(shell) < 0:
        shell = Solid(shell.wrapped.Reversed())
    if not BRepCheck_Analyzer(shell.wrapped).IsValid():
        raise RuntimeError("the rounded shell is not a valid solid")
    return shell


@cached
def body_blank():
    """The body before anything is cut from it: the top surface within the
    footprint carried straight down floor_drop() (so its underside is the same
    surface that much lower), its top edge rounded to top_round_mm, and every
    cell's plane put back exactly."""
    t = time.time()
    if P.top_round_mm > 0:
        shell = rounded_shell()
        t = stage("body shell and round", t)
    else:
        shell = solid(extrude(top_trimmed(), amount=L.floor_drop(), dir=(0, 0, -1)))
        t = stage("body shell", t)
    shell = patched(shell)
    t = stage("body patches", t)
    for batch in apart([cell_cap(k, -cap_under_mm, cap_wider_mm) for k in keys()]):
        shell = solid(shell.cut(*batch))
    for batch in apart([cell_cap(k, -L.floor_drop() + cap_under_mm, cap_wider_mm, below=True) for k in keys()]):
        shell = solid(shell.cut(*batch))
    shell = solid(shell.fuse(*[cell_block(k, 0, -L.floor_drop()) for k in keys()]))
    stage("body cells", t)
    return shell


@cached
def plinth_blank():
    """The plinth before anything is cut from it: from the desk up to the body's
    underside, flat under each cell as the body is."""
    t = time.time()
    # The footprint's prism standing on the desk, under the plate surface (the
    # desk is the prism's own bottom face: cutting the prism's spline wall with
    # a desk plane instead failed for some outlines).
    plinth = patched(solid(under(plate_face()).intersect(prism(footprint_2d(), 0, 100))))
    t = stage("plinth patches", t)
    z = -L.floor_drop() - P.plate_gap_mm
    for batch in apart([cell_cap(k, z) for k in keys()]):
        plinth = solid(plinth.cut(*batch))
    stage("plinth cells", t)
    return plinth


# ---------------------------------------------------------------- the bay's well
def bay_pocket_h():
    """The pocket height the parts need over the well's floor."""
    return max(P.mcu_parts_mm + P.mcu_board_mm[2] + P.mcu_clearance_mm,
               P.battery_mm[2] + P.battery_clearance_mm,
               P.power_switch_mm[2] + 0.6 if P.power_switch else 0)


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
    return trans([0, 0, bay_z()]) @ L.power_switch_frame()


def well():
    """The well: both bays' rectangles, open from the well's floor up through the
    plate's top (and into the body, where the parts need more than the plate has)."""
    return [Solid.make_box(b[1][0] - b[0][0], b[1][1] - b[0][1], 100).translate((b[0][0], b[0][1], bay_z()))
            for b in L.bays()]


# ---------------------------------------------------------------- wiring points
# In a key's frame, at the socket's top: the column line past the -x tab
# (col_x), the row riser over the +x tab (row_x), and the north edge (ne_y).
def col_x():
    # Overlapping the socket's shaft, so no sliver is left between them under the tent.
    return P.socket_centre_mm[0] - P.socket_body_mm[0] / 2 - 0.3


def row_x():
    return P.socket_centre_mm[0] + P.socket_body_mm[0] / 2 + P.socket_tab_mm[0]


def ne_y():
    return P.cell_mm / 2 - P.channel_w_mm / 2


def out_y():
    """A trunk point just past a cell's edge."""
    return P.cell_mm / 2 + 1.5


def at(k, p):
    return xform(k.frame, [p[0], p[1], R.socket_top_z()])


def c_tab(k):
    return at(k, (col_x(), P.socket_tab_y[0]))


def r_tab(k):
    return at(k, (row_x(), P.socket_tab_y[1]))


def nw(k):
    return at(k, (col_x(), ne_y()))


def ne(k):
    return at(k, (row_x(), ne_y()))


def back_pt(k):
    return at(k, (col_x(), out_y()))


def front_pt(k):
    return at(k, (col_x(), -out_y()))


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


@cached
def channels():
    """The channels as polylines (width, [points...], group) in world; the group
    ("finger", "thumb" or "bridge") says which hull of the footprint holds it."""
    w, t = P.channel_w_mm, P.trunk_w_mm
    rows = range(-P.rows_below, P.rows_above + 1)
    out = []
    # Each finger column: front trunk point, its keys' column tabs, back trunk point.
    for c in range(5):
        out.append((t if c == 0 else w,
                    [front_pt(finger_key(c, -P.rows_below))] + [c_tab(finger_key(c, r)) for r in rows]
                    + [back_pt(finger_key(c, P.rows_above))], "finger"))
    # The back trunk, pinky to inner column and into the bay, and the front trunk.
    out.append((t, edge_trunk(1) + [bay_entry()], "finger"))
    out.append((t, edge_trunk(-1), "finger"))
    out.append((t, [front_pt(finger_key(1, -P.rows_below)), ne(thumb("near"))], "bridge"))
    # Each finger row: from each key's tab up to its north edge, across to the
    # next cell's north edge and along it to that key's tab; the inner column's
    # feeds its wire into the column channel.
    for r in rows:
        k0 = finger_key(0, r)
        out.append((w, [r_tab(k0), ne(k0), nw(k0)], "finger"))
        for c in range(4):
            a, b = finger_key(c, r), finger_key(c + 1, r)
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


def hull_solid(points):
    """The convex hull of some world points, as a solid."""
    pts = np.asarray(points, float)
    hull = ConvexHull(pts)
    faces = []
    for tri, eq in zip(hull.simplices, hull.equations):
        a, b, c = pts[tri]
        if np.dot(np.cross(b - a, c - a), eq[:3]) < 0:
            tri = tri[[0, 2, 1]]
        faces.append(Face(Wire.make_polygon([tuple(pts[i]) for i in tri], close=True)))
    return Solid(Shell(faces)).clean()


def post_points(p, w):
    """A channel post's corners at a world point: a square of w from 3 mm under
    the body's underside up to the point (so the hull between two posts stays
    open to the underside where that curves up between them)."""
    f = floor_z(p[0], p[1]) - 3
    return [(p[0] + sx * w / 2, p[1] + sy * w / 2, z) for sx in (-1, 1) for sy in (-1, 1) for z in (f, p[2])]


def channel_solids():
    return [hull_solid(post_points(a, w) + post_points(b, w))
            for w, pts, _ in channels() for a, b in zip(pts[:-1], pts[1:])]


def diode_frame(k):
    """The diode's frame: in the column channel, over the column tab."""
    return k.frame @ trans([col_x(), (P.socket_tab_y[0] + ne_y()) / 2 + 1, R.socket_top_z() - P.diode_mm[1] / 2 - 0.4])


def diode_rooms():
    """Room for the diode in the column channel, over the column tab."""
    d = P.diode_mm
    return [s for k in keys() for s in place(diode_frame(k), [R.box((d[1] + 0.8, d[0] + 0.8, d[1] + 0.8))])]


def socket_shaft(k, grow):
    """The socket's shaft from its pocket down through the body's underside, `grow` round the body."""
    return [piece for s in place(k.frame, R.socket_body(grow)) for piece in swept(s)]


def solder_wells():
    """Room under each socket tab to solder to it."""
    out = []
    for k in keys():
        for side in (-1, 1):
            t = R.socket_tab_tip(side)
            s = P.solder_well_mm
            box = Solid.make_box(s[0], s[1], 0.6).translate((t[0] - s[0] / 2, t[1] - s[1] / 2, t[2] - 0.6))
            out += [piece for b in place(k.frame, [box]) for piece in swept(b)]
    return out


# ---------------------------------------------------------------- the body
def key_rooms():
    out = []
    for k in keys():
        out += place(k.frame, R.mx_switch_room() + R.hotswap_socket_room())
        out += socket_shaft(k, P.socket_clearance_mm)
    return out


def bay_rooms(plinth=False):
    """The parts' rooms in the well, cut from the plinth (where the switch's
    pocket opens up through the plate's top) and from the body where they reach
    above the plate's top."""
    out = place(mcu_frame(), R.mcu_room()) + place(battery_frame(), R.battery_room())
    if P.power_switch:
        out += place(power_switch_frame(), R.power_switch_room(100 if plinth else 0))
    return out


def insert_holes():
    return [R.insert_hole().translate((p[0], p[1], floor_z(p[0], p[1]))) for p in L.screw_points()]


def body():
    blank = body_blank()
    t = time.time()
    cutters = []
    for k in keys():
        cutters += united(place(k.frame, R.mx_switch_room() + R.hotswap_socket_room()) + socket_shaft(k, P.socket_clearance_mm))
    cutters += united(solder_wells()) + diode_rooms() + united(channel_solids()) + bay_rooms() + insert_holes()
    t = stage("body cutters", t)
    body = solid(blank.cut(*cutters))
    restrict([body])
    stage("body cuts", t)
    return body


# ---------------------------------------------------------------- the bottom plate
def socket_boss(k):
    """The boss under key k's socket: the socket's shaft, inset, standing on the
    plinth's top under the cell up to just under the socket."""
    pieces = socket_shaft(k, -P.boss_inset_mm)
    shaft = pieces[0].fuse(*pieces[1:])
    shaft = solid(shaft.intersect(half_space(k.frame, R.socket_bottom_z() - P.boss_clearance_mm)))
    return solid(shaft.intersect(half_space(k.frame, -L.floor_drop() - P.plate_gap_mm, below=False)))


def bottom_plate():
    """The plinth: up to the body's underside, with the well, the screw holes and
    the pinhole over the reset button, and the socket bosses standing on it."""
    blank = plinth_blank()
    t = time.time()
    cutters = well() + bay_rooms(plinth=True)
    for p in L.screw_points():
        cutters += [h.translate((p[0], p[1], 0)) for h in R.screw_hole(plate_z(p[0], p[1]))]
    cutters += place(mcu_frame(), [R.mcu_reset_hole()])
    plate = solid(blank.cut(*cutters))
    t = stage("plinth cuts", t)
    plate = solid(plate.fuse(*[socket_boss(k) for k in keys()]))
    restrict([plate])
    stage("plinth bosses", t)
    return plate


# ---------------------------------------------------------------- the parts, for the assembly
def switches():
    return Compound(children=place_all([(k.frame, R.mx_switch()) for k in keys()]), label="switches")


def keycaps(pressed=0):
    caps = [R.keycap(k.cap_row, k.units, pressed) for k in keys()]
    c = Compound(children=place_all([(k.frame, cap) for k, cap in zip(keys(), caps)]), label="keycaps")
    c.color = Color("ivory")
    return c


def sockets():
    return Compound(children=place_all([(k.frame, R.hotswap_socket()) for k in keys()]), label="sockets")


def diodes():
    return Compound(children=place_all([(diode_frame(k), R.diode()) for k in keys()]), label="diodes")


def electronics():
    parts = [(mcu_frame(), R.mcu_board()), (battery_frame(), R.battery())]
    if P.power_switch:
        parts.append((power_switch_frame(), R.power_switch_part()))
    return Compound(children=place_all(parts), label="electronics")


def place_all(pairs):
    return [place(m, [s])[0] for m, s in pairs]


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
            a = place(ks[i].frame, [R.keycap_probe(ks[i].cap_row, ks[i].units, pi)])[0]
            b = place(ks[j].frame, [R.keycap_probe(ks[j].cap_row, ks[j].units, pj)])[0]
            hit = a.intersect(b)
            v = 0 if hit is None else sum(volume(s) for s in hit.solids())
            if v > 1e-6:
                hits.append((ks[i].name, ks[j].name, v))
    return hits


def report():
    """The board's heights and sizes, as text."""
    ks = keys()
    (x0, y0), (x1, y1) = bbox()
    tops = [L.cap_top(k)[2] for k in ks]
    plates = [origin(k.frame)[2] for k in ks]
    floors = [floor_z(*origin(k.frame)[:2]) for k in ks]
    reach = [r2(L.finger_plate_pitch(i) * L.finger_reach_radius(i) / L.finger_plate_radius(i)) for i in range(4)]
    m = 2 * (P.outline_round_mm + 2)
    return (f"plate tops {r2(min(plates))} to {r2(max(plates))} mm over the desk; cap tops {r2(min(tops))} to "
            f"{r2(max(tops))} mm; body shell {r2(L.floor_drop())} mm thick; plinth {r2(min(floors))} to "
            f"{r2(max(floors))} mm under the keys; well floor {r2(bay_z())} mm; fingertip reach between rows "
            f"{reach} mm (index to pinky); plan about {r2(x1 - x0 - m)} x {r2(y1 - y0 - m)} mm")

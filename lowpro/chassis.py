"""The body: the key field's top surface blended from the key cells, walled,
a shell of one thickness, with the switch and socket pockets and the wire
channels; and the bottom plate: a plinth up to the body's underside, with
the socket bosses and the well for the controller and battery.

Everything here is in world axes (layout.py). Solids are build123d's
(OpenCascade); the expensive ones are cached, see layout.reset().
"""
import time

import numpy as np
from build123d import Color, Compound, Edge, Face, GeomType, Keep, Kind, Plane, Shell, Solid, Wire, extrude, offset, split
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
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
    pts = [[(float(X[i, j]), float(Y[i, j]), float(Z[i, j])) for j in range(X.shape[1])] for i in range(X.shape[0])]
    return Face.make_surface_from_array_of_points(pts, tol=0.01, min_deg=2, max_deg=2)


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
    # periodic spline through the chain, sampled every millimetre or so, is
    # within a few hundredths of it and fillets cleanly.
    n = int(outline.length / 1.0)
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
# the top and bottom surfaces' boxes cover the whole board, so the pockets and
# channels are cut from the blank split by a few vertical planes into a
# compound of pieces: a cut then only touches the pieces near it, which is ten
# to twenty times quicker. The pieces are fused back into one solid at the end
# (glue), and the faces the planes split are merged again.
def split_pieces(shape, every=40):
    """The shape split by vertical planes about `every` mm apart."""
    (x0, y0), (x1, y1) = bbox()
    planes = [Plane(origin=(x, 0, 0), z_dir=(1, 0, 0)) for x in np.linspace(x0, x1, round((x1 - x0) / every) + 1)[1:-1]]
    planes += [Plane(origin=(0, y, 0), z_dir=(0, 1, 0)) for y in np.linspace(y0, y1, round((y1 - y0) / every) + 1)[1:-1]]
    pieces = [shape]
    for plane in planes:
        pieces = [s for piece in pieces for s in split(piece, bisect_by=plane, keep=Keep.BOTH).solids()]
    return pieces


def cut_pieces(pieces, cutters, size=40):
    """The cutters cut from the pieces, a few dozen at a time."""
    comp = Compound(children=pieces)
    for i in range(0, len(cutters), size):
        comp = comp.cut(*cutters[i:i + size])
    return comp.solids()


def glue(pieces):
    """The pieces, which touch but do not overlap, as one solid."""
    return solid(pieces[0].fuse(*pieces[1:]).clean())


def column(k, grow=0):
    """Key k's cell, cell_step_mm (and `grow`) past its edge, as a vertical
    column through everything."""
    return prism(cell_face(k, P.cell_step_mm + grow), -1, 201)


def cell_cap(k, z, grow=0):
    """Everything over key k's column above the plane z of its frame."""
    return solid(column(k, grow).intersect(half_space(k.frame, z, below=False)))


def cell_block(k, z_top, z_bottom):
    """Key k's column between two planes of its frame."""
    return solid(solid(column(k).intersect(half_space(k.frame, z_top))).intersect(half_space(k.frame, z_bottom, below=False)))


# Every cell's plane is put back exactly in two steps, one cell at a time:
# whatever the blend left above the plane over the cell (and cell_step_mm plus
# a little round it) is cut away, then a block between the plane and that
# plane floor_drop() lower is added. The cap is cut a little under the plane
# and a little wider than the block, so no face of the cap, the block and the
# shell coincides with another, which OpenCascade is surest of (the ring
# round each cell is left that much lower). Where a cell meets a higher
# neighbour the surface so steps at that neighbour's edge, with nothing left
# standing in the gap, and the floor steps with it.
cap_under_mm = 0.1
cap_wider_mm = 0.3


@cached
def body_blank():
    """The body before anything is cut from it: the top surface within the
    footprint carried straight down floor_drop() (so its underside is the same
    surface that much lower), its top edge filleted to top_round_mm, and every
    cell's plane put back exactly."""
    t = time.time()
    shell = solid(extrude(top_trimmed(), amount=L.floor_drop(), dir=(0, 0, -1)))
    t = stage("shell", t)
    if P.top_round_mm > 0:
        top = max(shell.faces().filter_by(GeomType.BSPLINE), key=lambda f: f.center().Z)
        shell = shell.fillet(P.top_round_mm, top.edges())
        t = stage("fillet", t)
    for k in keys():
        shell = solid(shell.cut(cell_cap(k, -cap_under_mm, cap_wider_mm)))
    for k in keys():
        shell = solid(shell.fuse(cell_block(k, 0, -L.floor_drop())))
    stage("cells", t)
    return shell


@cached
def plinth_blank():
    """The plinth before anything is cut from it: from the desk up to the body's
    underside, flat under each cell as the body is."""
    t = time.time()
    plate_top = top_trimmed().translate((0, 0, -L.floor_drop() - P.plate_gap_mm))
    plinth = solid(extrude(plate_top, amount=100, dir=(0, 0, -1)).intersect(above_desk()))
    z = -L.floor_drop() - P.plate_gap_mm
    for k in keys():
        plinth = solid(plinth.cut(cell_cap(k, z)))
    stage("plinth", t)
    return plinth


def above_desk():
    (x0, y0), (x1, y1) = bbox()
    return Solid.make_box(x1 - x0, y1 - y0, 100).translate((x0, y0, 0))


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
    out.append((t, [back_pt(finger_key(c, P.rows_above)) for c in range(4, -1, -1)] + [bay_entry()], "finger"))
    out.append((t, [front_pt(finger_key(c, -P.rows_below)) for c in range(4, -1, -1)], "finger"))
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
    t = time.time()
    pieces = split_pieces(body_blank())
    cutters = []
    for k in keys():
        cutters += place(k.frame, R.mx_switch_room() + R.hotswap_socket_room()) + socket_shaft(k, P.socket_clearance_mm)
    cutters += solder_wells() + diode_rooms() + channel_solids() + bay_rooms() + insert_holes()
    pieces = cut_pieces(pieces, cutters)
    t = stage("cuts", t)
    body = glue(pieces)
    stage("glue", t)
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
    t = time.time()
    pieces = split_pieces(plinth_blank())
    cutters = well() + bay_rooms(plinth=True)
    for p in L.screw_points():
        cutters += [h.translate((p[0], p[1], 0)) for h in R.screw_hole(plate_z(p[0], p[1]))]
    cutters += place(mcu_frame(), [R.mcu_reset_hole()])
    pieces = cut_pieces(pieces, cutters)
    t = stage("cuts", t)
    plate = glue(pieces + [socket_boss(k) for k in keys()])
    stage("glue", t)
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

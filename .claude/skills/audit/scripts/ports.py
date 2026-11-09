"""The USB-C, TRRS and reset openings of the capybara body, sliced from the
built STL at planes square to each part's axis. AUDIT_HALF=left for the left."""
import numpy as np
import trimesh

import common as A
from lowpro.lib import origin, xdir, xform

P, S, R = A.P, A.S, A.R
body, plate = A.stl("body"), A.stl("plate")
sign = -1 if A.HALF == "left" else 1
M = np.diag([sign, 1, 1, 1])


def frame(name):
    return M @ S.part_frame(name)


def section_hole(mesh, o, n, near, radius=12):
    """The section of mesh by the plane through o with normal n: the polygons'
    bounds in the plane's (u, v) axes, for the rings within `radius` of `near`
    (a point in the plane). u is the world-up-most in-plane axis's complement."""
    sec = mesh.section(plane_origin=o, plane_normal=n)
    if sec is None:
        return []
    planar, T = sec.to_2D()
    near2 = trimesh.transform_points([near], np.linalg.inv(T))[0][:2]
    out = []
    for poly in planar.polygons_full:
        for ring in [poly.exterior] + list(poly.interiors):
            c = np.asarray(ring.coords)
            if np.linalg.norm(c.mean(axis=0) - near2) < radius:
                # express the ring in world, then in the frame of interest later
                w = trimesh.transform_points(np.c_[c, np.zeros(len(c))], T)
                out.append(w)
    return out


def extent(ring_w, f):
    """A world ring's extent in the frame f's y and z."""
    inv = np.linalg.inv(f)
    q = trimesh.transform_points(ring_w, inv)
    return (q[:, 1].min(), q[:, 1].max(), q[:, 2].min(), q[:, 2].max())


def probe(name, mouth_x, face_x, centre_z, label):
    f = frame(name)
    ax = -xdir(f, (1, 0, 0))[:3]        # out through the wall
    print(f"\n== {label}: mouth at frame x {mouth_x:.2f}, wall face at {face_x:.2f}, setback {mouth_x - face_x:.2f} mm; "
          f"mouth centre {xform(f, (mouth_x, 0, centre_z))[2]:.2f} mm over the desk")
    inner_face = face_x + P.wall_mm
    for dx, what in ((face_x + 0.05, "0.05 in from the outer face"), (face_x + P.port_chamfer_mm + 0.05, "just past the chamfer"),
                     (mouth_x - 0.05, "0.05 outside the mouth"), (mouth_x + 0.3, "0.3 inside the mouth (the grip)"),
                     (inner_face - 0.05, "0.05 outside the wall's inner face"), (inner_face + 0.3, "0.3 inside the inner face")):
        o = xform(f, (dx, 0, centre_z))[:3]
        rings = section_hole(body, o, ax, o)
        ext = [extent(r, f) for r in rings]
        ext = [e for e in ext if e[1] - e[0] < 30 and e[3] - e[2] < 30]
        for e in ext:
            print(f"  {what} (x {dx:.2f}): hole {e[1] - e[0]:.2f} wide (y {e[0]:.2f}..{e[1]:.2f}) x {e[3] - e[2]:.2f} tall (z {e[2]:.2f}..{e[3]:.2f})")
        if not ext:
            print(f"  {what} (x {dx:.2f}): no small ring (open or solid)")
    # the wall left round the opening: rays from the mouth centre along +-y and +-z at the chamfer's inner end
    o = xform(f, (face_x + P.port_chamfer_mm + 0.3, 0, centre_z))[:3]
    for d, what in ((xdir(f, (0, 1, 0))[:3], "+y"), (-xdir(f, (0, 1, 0))[:3], "-y"), (xdir(f, (0, 0, 1))[:3], "up"), (-xdir(f, (0, 0, 1))[:3], "down")):
        locs, _, _ = body.ray.intersects_location([o], [d], multiple_hits=True)
        t = sorted(((locs - o) @ d)[((locs - o) @ d) > 0])
        print(f"  from the opening's centre {what}: body from {t[0]:.2f} to {t[1]:.2f} mm ({t[1] - t[0]:.2f} thick)" if len(t) > 1 else f"  {what}: {t}")


b, j = R.mcu(), R.jack()
probe("pro_micro", R.usb_mouth_x(), S.face_x("pro_micro"), b["board_mm"][2] + b["usb_mm"][2] / 2, "USB-C")
print(f"  receptacle {b['usb_mm']} (along x, wide, tall), grip {P.port_grip_mm}; board end at x {-b['board_mm'][0] / 2:.2f}, inner wall face at {S.face_x('pro_micro') + P.wall_mm:.2f}: "
      f"the board's end is {S.face_x('pro_micro') + P.wall_mm + b['board_mm'][0] / 2:.2f} mm from the inner face (+ is inside)")
print(f"  plug opening {b['plug_mm'][0] + 2 * b['clearance_mm']:.2f} x {b['plug_mm'][1] + 2 * b['clearance_mm']:.2f}, chamfer {P.port_chamfer_mm}")
probe("trrs", R.trrs_mouth_x(), S.face_x("trrs"), j["body_mm"][2] / 2, "TRRS")
print(f"  barrel {j['barrel_mm']} (long, dia); body front at x {-j['body_mm'][0] / 2:.2f}, inner wall face at {S.face_x('trrs') + P.wall_mm:.2f}: "
      f"the body's front is {S.face_x('trrs') + P.wall_mm + j['body_mm'][0] / 2:.2f} mm from the inner face (+ is inside)")
print(f"  plug opening dia {j['plug_mm'][0] + 2 * j['clearance_mm']:.2f}")

# the reset: frame x up, y along the wall, z into the case; the origin is the switch body's front face
# (shell.reset_frame puts it reset_skin_mm behind the wall's face), and the plunger stands out of it along -z
r = R.reset()
f = frame("reset")
o = origin(f)[:3]
out = -xdir(f, (0, 0, 1))[:3]
print(f"\n== reset: the switch body's face at {np.round(o, 2)}, {o[2]:.2f} over the desk, plunger {r['plunger_mm']} (dia, proud of the body), body {r['body_mm']}, skin {P.reset_skin_mm}: "
      f"the plunger's tip stands {r['plunger_mm'][1] - P.reset_skin_mm:+.2f} mm out of the wall's face with the body against the skin")
# along the plunger axis from inside the case out
for off, what in ((0, "on the axis (through the plunger hole)"), (2.5, "2.5 mm up the axis (the skin beside the hole)"), (-2.5, "2.5 mm down"), (4.0, "4 mm up (over the body)"), (-4.0, "4 mm down (below the body, toward the seam)")):
    oo = o + off * xdir(f, (1, 0, 0))[:3] + 5 * -out
    locs, _, _ = body.ray.intersects_location([oo], [out], multiple_hits=True)
    t = (np.sort(((locs - oo) @ out)) - 5) if len(locs) else np.array([])
    print(f"  {what}: body from inside out, crossings at distance past the body's face {np.round(t, 2)} (0 = the switch body's face plane, + = outside)")
sec = body.section(plane_origin=o + P.reset_skin_mm / 2 * out, plane_normal=out)   # mid-skin
pl, T = sec.to_2D()
for poly in pl.polygons_full:
    for ring in poly.interiors:
        c = trimesh.transform_points(np.c_[np.asarray(ring.coords), np.zeros(len(ring.coords))], T)
        if np.linalg.norm(c.mean(axis=0) - o) < 5:
            q = trimesh.transform_points(c, np.linalg.inv(f))
            print(f"  plunger hole in the skin: {q[:, 0].max() - q[:, 0].min():.2f} (up) x {q[:, 1].max() - q[:, 1].min():.2f} (along the wall)")
# the slot behind the skin, at the body's middle height, and the stop
zs = r["body_mm"][2] / 2
for h in (-2.0, 0.0, 2.0):
    oo = xform(f, (h, -10, zs))[:3]
    d = xdir(f, (0, 1, 0))[:3]
    locs, _, _ = body.ray.intersects_location([oo], [d], multiple_hits=True)
    t = np.sort((locs - oo) @ d) - 10
    print(f"  slot width across the wall at x {h:+.1f} (seam at {R.reset_seam_x():.2f}): body crossings at y {np.round(t, 2)}")
oo = xform(f, (0, 0, -3))[:3]
d = xdir(f, (0, 0, 1))[:3]
locs, _, _ = body.ray.intersects_location([oo], [d], multiple_hits=True)
t = np.sort((locs - oo) @ d) - 3
print(f"  along the axis from outside: body crossings at z {np.round(t, 2)} (skin from the first to the second)")
locs, _, _ = plate.ray.intersects_location([oo], [d], multiple_hits=True)
t = np.sort((locs - oo) @ d) - 3
print(f"  the plinth along the same line at x 0 (body middle): crossings z {np.round(t, 2)}; body back {r['body_mm'][2]} + clearance {r['clearance_mm']}")
stop = A.mesh_of(R.union(S.place(S.part_frame('reset'), R.reset_stop())))
print(f"  stop bounds (world) {np.round(stop.bounds, 2).tolist()}, {P.reset_stop_mm} wide/deep; switch body top at frame x {r['body_mm'][0] / 2:.2f} = world z {xform(S.part_frame('reset'), (r['body_mm'][0] / 2, 0, 0))[2]:.2f}; "
      f"legs span {r['leg_span_mm']} along the wall, slot {r['leg_span_mm'] + 2 * r['clearance_mm']:.2f}")
sz = trimesh.transform_points(stop.vertices, np.linalg.inv(f))[:, 2]
print(f"  the stop's face is {sz.min() - r['body_mm'][2]:.2f} mm behind the switch body's back (frame z {sz.min():.2f}, back at {r['body_mm'][2]}): "
      f"a press moves the switch that far before the stop takes it, leaving the tip {r['plunger_mm'][1] - P.reset_skin_mm - (sz.min() - r['body_mm'][2]):+.2f} mm out of the face")

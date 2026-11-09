"""Each key's well, on the built body (presets with well_depth_mm > 0), in the
key's frame (z up the key's axis from the plate's top):

  rim     the top of the well's wall all round: the body's first face met
          coming down the key's axis at points round the cap's room, 0.3 mm
          and cap_wall_mm - 0.15 out from it; min / median / max, the share of
          the perimeter under well_depth_mm - 0.5 (a wall cut down or a skin
          falling away), and the side where it is lowest; then what lowers it
          at those points: another key's cap room (the wells merge or a lower
          neighbour's room rises past), the shell's top itself under the top
          plane (the skin falls away), or neither (the web cut between rooms)
  top     the wall's width 0.3 mm under its rim, out from the room
          (knife edges under ~0.8 mm won't print)
  tilt    the key's axis from the print's vertical (the body prints on the
          seam plane, top up), so the well's downhill wall overhangs this much;
          and the area of the well's own faces (inside the room grown 0.1 mm,
          from the plate up to the rim) that overhang more than 45 and 60 deg
          in the print, which critical-only support may or may not prop, from
          the well's visible floor

    python wells.py
"""
import numpy as np

import common as A
from lowpro.lib import xform

P, R = A.P, A.R
assert P.well_depth_mm > 0, "no wells in this preset"
m = A.stl("body")
shell = A.mesh_of(A.C.body_shell())
depth, wall, g = P.well_depth_mm, P.cap_wall_mm, P.cap_room_clearance_mm
print(f"== {A.HALF}: well depth {depth} mm over the plate, cap room clearance {g}, cap wall {wall}, cove {P.well_cove_mm}")


def perimeter(hx, hy, r, off, n=96):
    """Points round a rounded rectangle (half sizes hx, hy, corner radius r)
    grown by off, with their outward normals, in its plane."""
    pts, nrm = [], []
    L = [2 * (hx - r), 2 * (hy - r)]
    for t in np.linspace(0, 1, n, endpoint=False):
        # walk the outline by angle about the centre: good enough for a ring of samples
        a = 2 * np.pi * t
        ux, uy = np.cos(a), np.sin(a)
        # the point on the rounded rectangle along this direction
        s = min((hx / abs(ux)) if abs(ux) > 1e-9 else np.inf, (hy / abs(uy)) if abs(uy) > 1e-9 else np.inf)
        px, py = ux * s, uy * s
        cx, cy = np.clip(px, -(hx - r), hx - r), np.clip(py, -(hy - r), hy - r)
        dx, dy = px - cx, py - cy
        d = np.hypot(dx, dy)
        if d > 1e-9 and abs(cx) == hx - r and abs(cy) == hy - r:
            nx, ny = dx / d, dy / d
            px, py = cx + nx * r, cy + ny * r
        else:
            nx, ny = (np.sign(px), 0.0) if abs(abs(px) - hx) < 1e-6 else (0.0, np.sign(py))
        pts.append((px + nx * off, py + ny * off))
        nrm.append((nx, ny))
    return np.array(pts), np.array(nrm)


side = lambda p: max(((p[0], "+x"), (-p[0], "-x"), (p[1], "+y"), (-p[1], "-y")))[1]
rows = []
for k in A.L.keys():
    hx, hy = R.keycap_room_half(k.units)
    F = k.frame
    out = {}
    rims = []
    for off in (0.3, wall - 0.15):
        pts, nrm = perimeter(hx, hy, g, off)
        o = np.array([xform(F, (x, y, 20.0)) for x, y in pts])
        d = np.tile(-F[:3, 2], (len(o), 1))
        t = A.cast(m, o, d, far=40)
        rims.append(20.0 - t)
    rim = np.minimum(*rims)
    pts, nrm = perimeter(hx, hy, g, 0.3)
    low = rim < depth - 0.5
    i = int(np.nanargmin(np.where(np.isfinite(rim), rim, np.inf)))
    # wall width under the rim: from inside the room, outward, through the wall
    widths = []
    pin, _ = perimeter(hx, hy, g, -0.2)
    for (x, y), (nx, ny), r in zip(pin, nrm, rim):
        if not np.isfinite(r) or r < 0.5:
            widths.append(np.nan)
            continue
        z = min(r, depth) - 0.3
        o = xform(F, (x, y, z))
        dv = F[:3, :3] @ np.array([nx, ny, 0.0])
        locs, _, _ = m.ray.intersects_location([o], [dv], multiple_hits=True)
        s = np.sort((locs - o) @ dv) if len(locs) else np.array([])
        widths.append(s[1] - s[0] if len(s) >= 2 else np.inf)
    widths = np.array(widths)
    j = int(np.nanargmin(widths)) if np.isfinite(widths).any() else 0
    tilt = np.degrees(np.arccos(np.clip(F[2, 2], -1, 1)))
    # the well's own faces that overhang in the print
    inv = np.linalg.inv(F)
    c = A.xform(inv, m.triangles_center.T).T if False else (np.c_[m.triangles_center, np.ones(len(m.triangles_center))] @ inv.T)[:, :3]
    inwell = (np.abs(c[:, 0]) < hx + 0.1) & (np.abs(c[:, 1]) < hy + 0.1) & (c[:, 2] > -0.05) & (c[:, 2] < depth + 0.1)
    nz = m.face_normals[:, 2]
    a45 = m.area_faces[inwell & (nz < -np.sin(np.radians(45)))].sum()
    a60 = m.area_faces[inwell & (nz < -np.sin(np.radians(60)))].sum()
    # what lowers the rim where it is low
    why = {"room": 0, "skin": 0, "web": 0}
    for (x, y), lo_ in zip(pts, low):
        if not lo_:
            continue
        w = xform(F, (x, y, depth - 0.3))
        inroom = False
        for j_ in A.L.keys():
            if j_ is k:
                continue
            q = (np.linalg.inv(j_.frame) @ np.r_[w, 1])[:3]
            jx, jy = R.keycap_room_half(j_.units)
            if abs(q[0]) < jx and abs(q[1]) < jy and q[2] > 0:
                inroom = True
                break
        if inroom:
            why["room"] += 1
            continue
        top = xform(F, (x, y, 30.0))
        tt = A.cast(shell, [top], [-F[:3, 2]], far=60)[0]
        why["skin" if 30.0 - tt < depth - 0.3 else "web"] += 1
    rows.append((k.name, np.nanmin(rim), np.nanmedian(rim), np.nanmax(rim), low.mean(), side(pts[i]), np.nanmin(widths), side(pts[j]), tilt, a45, a60, why))
print(f"{'key':22s} {'rim min/med/max':>18s} {'<d-0.5':>7s} {'lowest':>6s}   {'wall top min':>12s}   {'tilt':>5s}  well faces >45 / >60 deg   low points: room / skin / web")
for name, lo, med, hi, frac, s1, w, s2, tilt, a45, a60, why in rows:
    print(f"{name:22s} {lo:6.2f} {med:5.2f} {hi:5.2f}  {frac * 100:5.0f}%   {s1:>4s}    {w:6.2f} ({s2})   {tilt:5.1f}   {a45:6.1f} / {a60:6.1f} mm^2          {why['room']:3d} / {why['skin']:3d} / {why['web']:3d}")

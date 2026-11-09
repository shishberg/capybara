"""Wall and skin thickness of the built capybara body and plinth, two ways:
(1) exact ray cast from each face centroid along the inward normal, clustered
into thin patches; (2) plan sections every 1 mm, each region eroded to find
sub-width solid (catches tapered wedges the normal ray misses).
Also lists where Manifold's mesh has coincident vertices (zero-thickness
touches). Run: AUDIT_HALF=right|left python thickness.py [body|plate]
"""
import sys

import numpy as np
import trimesh
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from sklearn.cluster import DBSCAN

import common as A

THRESH = (0.5, 0.8, 1.0, 1.2)


def thickness(m):
    """Thickness under each face: the first hit of a ray from a hair inside the
    face centroid along -normal."""
    return A.cast(m, m.triangles_center - m.face_normals * 1e-3, -m.face_normals, far=2.5)


def patches(m, thin_mask, t, eps=1.5, label=""):
    c = m.triangles_center[thin_mask]
    a = m.area_faces[thin_mask]
    th = t[thin_mask]
    if len(c) == 0:
        return
    lab = DBSCAN(eps=eps, min_samples=1).fit(c).labels_
    rows = []
    for k in np.unique(lab):
        i = lab == k
        rows.append((a[i].sum(), c[i].mean(axis=0), c[i].min(axis=0), c[i].max(axis=0), th[i].min(), np.average(th[i], weights=a[i]), th[i].max()))
    rows.sort(key=lambda r: -r[0])
    print(f"  {len(rows)} patches {label}; the largest by area:")
    for area, ctr, lo, hi, tmin, tmean, tmax in rows[:25]:
        ext = hi - lo
        print(f"    {area:7.2f} mm^2 at ({ctr[0]:6.1f},{ctr[1]:6.1f},{ctr[2]:5.1f}) extent {ext[0]:.1f}x{ext[1]:.1f}x{ext[2]:.1f} "
              f"thickness {tmin:.2f}..{tmax:.2f} (mean {tmean:.2f})  {A.label(ctr)}")


def plan_sections(m, step=1.0, widths=(0.4, 0.6, 0.8, 1.0, 1.2)):
    z0, z1 = m.bounds[0][2] + 0.2, m.bounds[1][2] - 0.2
    found = {w: [] for w in widths}
    for z in np.arange(z0, z1, step):
        sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if sec is None:
            continue
        p2, to3d = sec.to_2D()
        polys = []
        for p in p2.polygons_full:
            def back(ring):
                pts = np.c_[np.asarray(ring.coords), np.zeros(len(ring.coords)), np.ones(len(ring.coords))] @ to3d.T
                return pts[:, :2]
            polys.append(Polygon(back(p.exterior), [back(h) for h in p.interiors]))
        for poly in polys:
            for geom in ([poly] if poly.geom_type == "Polygon" else list(poly.geoms)):
                for w in widths:
                    # solid narrower than w: the region lost when eroding by w/2 and re-dilating
                    thin = geom.difference(geom.buffer(-w / 2, join_style=2, mitre_limit=10).buffer(w / 2 + 1e-3, join_style=2, mitre_limit=10))
                    if thin.area > 0.05:
                        parts = [thin] if thin.geom_type == "Polygon" else list(thin.geoms)
                        for q in parts:
                            if q.area > 0.05:
                                c = q.centroid
                                found[w].append((q.area, z, c.x, c.y))
    for w in widths:
        rows = sorted(found[w], key=lambda r: -r[0])
        tot = sum(r[0] for r in rows)
        print(f"  plan width < {w} mm: {len(rows)} regions over the sections, total {tot:.1f} mm^2 of section; largest:")
        seen = []
        for area, z, x, y in rows:
            if any(abs(x - sx) < 3 and abs(y - sy) < 3 for sx, sy in seen):
                continue
            seen.append((x, y))
            print(f"    {area:6.2f} mm^2 at ({x:6.1f},{y:6.1f}) z {z:5.1f}  {A.label(np.array([x, y, z]))}")
            if len(seen) >= 12:
                break


def coincident(solid):
    m = A.mesh_of(solid)
    v = m.vertices
    u, inv, cnt = np.unique(np.round(v, 6), axis=0, return_inverse=True, return_counts=True)
    dup = u[cnt > 1]
    print(f"  {len(dup)} positions with coincident vertices (zero-thickness touches in the solid)")
    if len(dup):
        lab = DBSCAN(eps=3, min_samples=1).fit(dup).labels_
        for k in np.unique(lab)[:40]:
            pts = dup[lab == k]
            c = pts.mean(axis=0)
            print(f"    {len(pts):3d} at ({c[0]:6.1f},{c[1]:6.1f},{c[2]:5.1f})  {A.label(c)}")


names = sys.argv[1:] or ["body", "plate"]
for name in names:
    m = A.stl(name)
    print(f"== {A.HALF} {name}")
    t = thickness(m)
    a = m.area_faces
    print(f"  total surface {a.sum():.0f} mm^2")
    for w in THRESH:
        print(f"  area with thickness < {w} mm: {a[t < w].sum():.1f} mm^2 ({(t < w).sum()} faces)")
    patches(m, t < 0.8, t, label="under 0.8 mm")
    patches(m, (t >= 0.8) & (t < 1.2), t, label="0.8 to 1.2 mm")
    print("  plan sections:")
    plan_sections(m)
    coincident(A.S.body() if name == "body" else A.S.bottom_plate())

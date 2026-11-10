"""FDM overhangs and bridges on the built capybara body and plinth, printed as
they stand in the STL: the body on its seam plane (z = 2, flat) top up, the
plinth on its base (z = 0). No doc states the capybara body's orientation;
BUILD.md's case rule (flat on its underside, top up) is assumed.
Run: AUDIT_HALF=right|left python overhang.py [body|plate]
"""
import sys

import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union, polylabel

import common as A

names = sys.argv[1:] or ["body", "plate"]
for name in names:
    m = A.stl(name)
    bed = m.bounds[0][2]
    n = m.face_normals
    a = m.area_faces
    c = m.triangles_center
    down = n[:, 2] < -1e-6
    ang = np.degrees(np.arcsin(np.clip(-n[:, 2], 0, 1)))   # overhang angle from vertical: 0 wall, 90 ceiling
    print(f"== {A.HALF} {name}: bed at z {bed:.2f}, {a.sum():.0f} mm^2 of surface")
    onbed = np.abs(c[:, 2] - bed) < 1e-3
    print(f"  first layer (faces on the bed): {a[onbed].sum():.1f} mm^2")
    bands = [(0, 45), (45, 60), (60, 80), (80, 90.01)]
    for lo, hi in bands:
        i = down & ~onbed & (ang >= lo) & (ang < hi)
        print(f"  downward faces {lo:.0f}-{min(hi, 90):.0f} deg from vertical: {a[i].sum():.1f} mm^2")
    # what is under every overhanging face: a ray straight down
    need = down & ~onbed & (ang > 45)
    o = c[need] - [0, 0, 1e-3]
    drop = A.cast(m, o, np.tile([0, 0, -1.0], (len(o), 1)), far=o[:, 2].max() - bed + 1)
    from_bed = ~np.isfinite(drop)
    drop[from_bed] = o[from_bed, 2] - bed
    vol = (a[need] * drop).sum()
    print(f"  support everywhere under faces > 45 deg: about {vol:.0f} mm^3 of support column; "
          f"{a[need][from_bed].sum():.0f} mm^2 stands over the bed, {a[need][~from_bed].sum():.0f} mm^2 over the part")
    # near-horizontal ceilings grouped into coplanar connected patches
    ceil = down & ~onbed & (ang >= 80)
    idx = np.flatnonzero(ceil)
    adj = m.face_adjacency
    keep = ceil[adj[:, 0]] & ceil[adj[:, 1]]
    # same plane: close z at centroid and close normal
    same = keep & (np.abs(c[adj[:, 0], 2] - c[adj[:, 1], 2]) < 0.3)
    import networkx as nx
    g = nx.Graph()
    g.add_nodes_from(idx)
    g.add_edges_from(adj[same])
    rows = []
    for comp in nx.connected_components(g):
        f = np.fromiter(comp, int)
        area = a[f].sum()
        if area < 2:
            continue
        tris = [Polygon(t[:, :2]) for t in m.triangles[f]]
        poly = unary_union(tris).buffer(0.01)
        if poly.is_empty:
            continue
        if poly.geom_type != "Polygon":
            poly = max(poly.geoms, key=lambda p: p.area)
        centre = polylabel(poly, tolerance=0.1)
        r = poly.exterior.distance(centre) if not poly.interiors else min([poly.exterior.distance(centre)] + [h.distance(centre) for h in poly.interiors])
        z = np.average(c[f, 2], weights=a[f])
        # what's under the patch's middle
        # from the patch's own face at its middle (the patch's mean z can sit above
        # its face there, and a ray from there hits the patch itself, 0.0 mm below)
        top = A.cast(m, [[centre.x, centre.y, z + 0.5]], [[0, 0, -1.0]], far=2.0)[0]
        o = np.array([[centre.x, centre.y, z + 0.5 - (top if np.isfinite(top) else 0.5) - 1e-3]])
        t = A.cast(m, o, [[0, 0, -1.0]], far=o[0, 2] - bed + 1)[0]
        under = f"the part {t:.1f} mm below" if np.isfinite(t) else f"the bed {z - bed:.1f} mm below"
        rows.append((r, area, z, centre.x, centre.y, under))
    rows.sort(reverse=True)
    print(f"  {len(rows)} near-horizontal ceiling patches over 2 mm^2; the widest bridges (inscribed radius):")
    for r, area, z, x, y, under in rows[:18]:
        print(f"    half-span {r:5.1f} mm, {area:7.1f} mm^2 at ({x:6.1f},{y:6.1f}) z {z:5.1f}, over {under}; {A.label(np.array([x, y, z]))}")
    tot = sum(r[1] for r in rows)
    print(f"  ceiling area in those patches {tot:.0f} mm^2")
    if name == "body":
        # the footprint on the bed versus the wall ring
        import case.chassis as C
        from case.chassis import polygon
        q = C.outline()
        ring = polygon(q).area() - polygon(q).offset(-A.P.wall_mm, 2, 2.0, 8).area()
        print(f"  the outline's 3 mm wall ring is {ring:.1f} mm^2 in plan; first layer measured above")
        # pocket blocks' undersides: height over the bed
        hs = []
        for k in A.L.keys():
            under = A.xform(k.frame, [0, 0, A.R.tile_top_z() - A.P.capybara['tile']['size_mm'][2]])[2]
            hs.append((under - bed, k.name))
        hs.sort()
        print("  pocket bottoms over the bed: " + ", ".join(f"{n} {h:.1f}" for h, n in hs))
    else:
        from case.chassis import polygon
        import case.chassis as C
        print(f"  plinth outline area {polygon(C.outline()).area():.0f} mm^2 (the skirt adds to the footprint)")

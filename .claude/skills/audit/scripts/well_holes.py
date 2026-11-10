"""Where a well's floor or wall opens into the case: lines down each key's
axis from above, on a grid over the key's room grown by cap_wall_mm, outside
the switch's hole (and its clip reliefs), that meet no body at all and come
down on the plinth's top inside the outline: an opening from the top into
the inside of the case (light and dust get in, and a slicer sees a hole).
A line that falls past the plate's level into a lower neighbour's well, or
off the outline, is open air outside the case and isn't counted.

    python well_holes.py [key ...]
"""
import sys

import numpy as np

import common as A
from case.lib import xform

P, R = A.P, A.R
m = A.stl("body")
plate = A.stl("plate")
hole = 14.15 / 2 + 0.3          # the switch's hole and its clip reliefs, roughly, left out
print(f"== {A.HALF}: lines down each key's axis, 0.5 mm grid over the room grown {P.cap_wall_mm}, that pass through the body onto the plinth inside the outline")
keys = [k for k in A.L.keys() if not sys.argv[1:] or k.name in sys.argv[1:]]
for k in keys:
    hx, hy = R.keycap_room_half(k.units)
    hx, hy = hx + P.cap_wall_mm, hy + P.cap_wall_mm
    F = k.frame
    # off the half-millimetre lattice: a line exactly in a wall face parallel to it slips through the caster
    gx, gy = np.meshgrid(np.arange(-hx, hx + 1e-6, 0.5) + 0.0137, np.arange(-hy, hy + 1e-6, 0.5) + 0.0213)
    pts = np.c_[gx.ravel(), gy.ravel()]
    pts = pts[(np.abs(pts[:, 0]) > hole) | (np.abs(pts[:, 1]) > hole)]
    o = np.array([xform(F, (x, y, 25.0)) for x, y in pts])
    d = np.tile(-F[:3, 2], (len(o), 1))
    t = A.cast(m, o, d, far=60)
    z = 25.0 - t
    through = np.isinf(t)
    if not through.any():
        continue
    tp = A.cast(plate, o[through], d[through], far=80)
    land = o[through] + d[through] * np.where(np.isfinite(tp), tp, 0)[:, None]
    inside = np.array([A.C.outline_distance(p[:2]) for p in land]) > 0
    hit = np.isfinite(tp) & inside
    if not hit.any():
        continue
    q = pts[through][hit]
    w = land[hit]
    print(f"  {k.name:22s} {hit.sum():4d} lines ({hit.sum() * 0.25:.1f} mm^2) through the body onto the plinth inside the outline, "
          f"frame x {q[:, 0].min():.1f}..{q[:, 0].max():.1f} y {q[:, 1].min():.1f}..{q[:, 1].max():.1f}; landing round ({w[:, 0].mean():.1f}, {w[:, 1].mean():.1f}), "
          f"{A.C.outline_distance(w[:, :2].mean(axis=0)):.1f} mm inside the outline")

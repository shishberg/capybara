"""How close each tile passes the body on its straight way down off its pegs:
the tile run down its key's axis (shell.tile_drop, the notches riding the
pegs) by the pegs' length plus the board and its clearance (the build's
tile_way) and by 4 mm, and the least gap from that swept tile to the body.
The build's check passes at any gap over 0; under a print's tolerance
(about 0.2 mm) the tile may rub or stick on the way. The pegs, which the
notches ride at 0.149 mm by design, are left out: a 4 mm square at each of the
tile's corners is taken from the body before measuring. Where the gap is
under 0.3 mm, says where: the swept tile grown by 0.3 mm against the body.

    python tile_path_gap.py
"""
import common as A
import numpy as np
from manifold3d import Manifold

from lowpro.chassis import placed, union

S, P = A.S, A.P
t = P.capybara["tile"]
body = S.body()
way = t["size_mm"][2] + t["clearance_mm"]
print(f"== {A.HALF}: least gap from the tile, run straight down its axis, to the body (mm; 'touch' = overlap)")
h = t["size_mm"][0] / 2
corners = union([A.R.box((4, 4, 40), (sx * h, sy * h, -10)) for sx in (-1, 1) for sy in (-1, 1)])
rows = []
for k in A.L.keys():
    b = body - placed(k.frame, corners)
    out, where = [], ""
    for d in (way, 4.0):
        swept = placed(k.frame, union(S.tile_drop(d)))
        v = (swept ^ b).volume()
        g = -v if v > 1e-6 else b.min_gap(swept, 2.0)
        out.append(g)
        if d == way and g < 0.3:
            near = (A.C.placed(k.frame, union([s.minkowski_sum(Manifold.sphere(0.3, 8)) for s in S.tile_drop(d)])) ^ b)
            bb = near.bounding_box()
            if near.volume() > 0:
                c = np.array([(bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, (bb[2] + bb[5]) / 2])
                where = f"; within 0.3 mm over x {bb[0]:.1f}..{bb[3]:.1f} y {bb[1]:.1f}..{bb[4]:.1f} z {bb[2]:.1f}..{bb[5]:.1f}, {near.volume():.2f} mm^3, near {A.label(c)}"
    rows.append((out[0], k.name, out, where))
f = lambda x: f"touch {-x:.3f} mm^3" if x < 0 else f"{x:.3f}"
for g, name, (a, b), where in sorted(rows):
    print(f"  {name:22s} over the build's way ({way:.2f} mm): {f(a)};  over 4 mm: {f(b)}{where}")

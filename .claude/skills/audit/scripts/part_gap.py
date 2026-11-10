"""Which part's room comes near each tile room, and where: the least gap per
(tile room, part room) under 1.3 mm, with the gap's location found by growing
the tile room until it meets the part room."""
import numpy as np
from manifold3d import Manifold, OpType

import common as A
from case.chassis import place, union

for k in A.L.keys():
    t = union(place(k.frame, A.R.tile_room()))
    for i, pr in enumerate(A.S.part_rooms()):
        g = t.min_gap(pr, 1.3)
        if g < 1.3:
            grown = Manifold.minkowski_sum(t, Manifold.sphere(g + 0.03, 12)) if hasattr(Manifold, "minkowski_sum") else None
            if grown is None:
                b = t.bounding_box()
                loc = "?"
            else:
                b = (grown ^ pr).bounding_box()
                loc = f"({(b[0] + b[3]) / 2:.1f}, {(b[1] + b[4]) / 2:.1f}, {(b[2] + b[5]) / 2:.1f})"
            pb = pr.bounding_box()
            print(f"{k.name:22s} part room {i} (bounds x {pb[0]:.1f}..{pb[3]:.1f} y {pb[1]:.1f}..{pb[4]:.1f} z {pb[2]:.1f}..{pb[5]:.1f}): gap {g:.2f} at {loc}")

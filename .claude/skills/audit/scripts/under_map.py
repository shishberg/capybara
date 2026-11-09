"""A map of the body under a key's tile, in the key frame: for each 1 mm cell of
the tile's footprint (plus 2 mm round it), how far below the board's underside
(-6.6) the body's highest point is, within 12 mm. '  .' is nothing within 12.

    python under_map.py matrix_ring_bottom
"""
import sys
import numpy as np
import common as A
from lowpro.lib import rinv
from manifold3d import Manifold

UNDER = A.R.tile_top_z() - A.P.capybara["tile"]["size_mm"][2]
k = A.L.key_named(sys.argv[1])
body_k = A.C.placed(rinv(k.frame), A.S.body()) ^ Manifold.cube((26, 26, 12)).translate((-13, -13, UNDER - 12))
xs = np.arange(-10, 11, 1.0)
print(f"{k.name}: mm of free space under the board's underside, per 1 mm cell (x across, y down from +y to -y); '  .' = over 12")
print("      " + "".join(f"{x:4.0f}" for x in xs))
for y in xs[::-1]:
    row = f"{y:5.0f} "
    for x in xs:
        cell = Manifold.cube((1, 1, 12)).translate((x - 0.5, y - 0.5, UNDER - 12))
        h = (body_k ^ cell)
        if h.volume() < 1e-6:
            row += "   ."
        else:
            row += f"{UNDER - h.bounding_box()[5]:4.1f}"
    print(row)

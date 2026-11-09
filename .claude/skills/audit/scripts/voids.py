"""Sealed voids and loose islands in the body, on Manifold's own indexed mesh
(not the STL, whose 3-corners-per-facet and coincident vertices split it into
hundreds of face-connected pieces): each face-connected shell with its signed
volume and where it is. A negative shell inside the body is a sealed void,
which a slicer fills or prints as an internal cavity; any second positive
shell is an island.

    python voids.py [body|plate]
"""
import sys

import numpy as np
import trimesh

import common as A

for name in sys.argv[1:] or ["body", "plate"]:
    solid = A.S.body() if name == "body" else A.S.bottom_plate()
    m = A.mesh_of(solid)
    shells = m.split(only_watertight=False)
    print(f"== {A.HALF} {name}: Manifold mesh {len(m.faces)} faces, watertight {m.is_watertight}, {len(shells)} face-connected shell(s), "
          f"genus {solid.genus()}, decompose {len(solid.decompose())}")
    for s in sorted(shells, key=lambda s: s.volume):
        c = s.bounds.mean(axis=0)
        print(f"   shell volume {s.volume:10.3f} mm^3, {len(s.faces)} faces, watertight {s.is_watertight}, centre ({c[0]:.1f}, {c[1]:.1f}, {c[2]:.1f}), "
              f"size {np.round(s.extents, 1).tolist()}, near {A.label(c)}")

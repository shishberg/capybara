"""What makes a thin spot: for each world point given (x,y,z ...), every cut
of the capybara body (by group and key), the wall's inner face and the top
skin within `r` mm of it, with the distance. Exact, with Manifold.
Run: AUDIT_HALF=right python whatis.py x,y,z [x,y,z ...]
"""
import sys

import numpy as np
from manifold3d import Manifold

import common as A
from case.chassis import place, placed, union

P, R, S, L, C = A.P, A.R, A.S, A.L, A.C
ks = L.keys()
cuts = []
for k in ks:
    cuts.append((f"{k.name} switch room", union(place(k.frame, R.mx_switch_room()))))
    cuts.append((f"{k.name} tile room", union(place(k.frame, R.tile_room()))))
    cuts.append((f"{k.name} cap room", placed(k.frame, R.keycap_room(k.cap_row, k.units))))
for name in S.PARTS:
    f = S.part_frame(name)
    if name == "reset":
        cuts.append(("reset room", union(place(f, R.reset_room()))))
    else:
        cuts.append((f"{name} room", union(place(f, S.ROOMS[name]()))))
        cuts.append((f"{name} port", union(place(f, S.PORTS[name](S.face_x(name))))))
cuts.append(("insert holes", union(S.insert_holes())))
if S.recesses():
    cuts.append(("seat recesses", union(S.recesses())))
cuts.append(("the hollow (interior)", S.interior()))
big = Manifold.cube((400, 400, 400)).translate((-200, -200, -200))
cuts.append(("outside the shell", big - C.body_shell()))

r = 1.5
for arg in sys.argv[1:]:
    p = np.array([float(v) for v in arg.split(",")])
    probe = Manifold.sphere(0.02, 8).translate(tuple(p))
    print(f"at ({p[0]:.1f},{p[1]:.1f},{p[2]:.1f}), {A.label(p)}:")
    rows = []
    for what, s in cuts:
        if C.gap(probe, s) > r + 1:
            continue
        inside = (probe ^ s).volume() > 0
        d = 0.0 if inside else s.min_gap(probe, r)
        if d < r:
            rows.append((d, what + (" (the point is inside it)" if inside else "")))
    for d, what in sorted(rows):
        print(f"   {d:5.2f} mm  {what}")

"""Which cuts come close to which in the capybara body, exactly, with Manifold:
for every key's tile room, the least gap to every other cut (other keys' tile,
switch and cap rooms, the parts' rooms, the insert holes, the outline's inner
face) under a wall's thickness; and in one key's own frame, the pocket's
ceiling ledge beside the clip reliefs and the pegs' sizes.
Run: AUDIT_HALF=right|left python room_gaps.py
"""
import numpy as np
from manifold3d import Manifold

import common as A
from case.chassis import place, placed, polygon, union
import case.chassis as C

P, R, S, L = A.P, A.R, A.S, A.L
ks = L.keys()
tile = {k.name: union(place(k.frame, R.tile_room())) for k in ks}
switch = {k.name: union(place(k.frame, R.mx_switch_room())) for k in ks}
cap = {k.name: placed(k.frame, R.keycap_room(k.cap_row, k.units)) for k in ks}
parts = union(S.part_rooms())
inserts = union(S.insert_holes())
recess = union(S.recesses()) if S.recesses() else None
inner = S.inside_prism()          # the plan inside the walls
outside = Manifold.cube((400, 400, 400)).translate((-200, -200, -200)) - inner

print(f"== {A.HALF}: gaps under {P.pocket_wall_mm} mm between a tile's room and another cut (the wall between them)")
rows = []
for k in ks:
    t = tile[k.name]
    others = [(f"{o.name} tile room", tile[o.name]) for o in ks if o is not k]
    others += [(f"{o.name} switch room", switch[o.name]) for o in ks if o is not k]
    others += [(f"{o.name} cap room", cap[o.name]) for o in ks if o is not k]
    others += [("a part's room", parts), ("an insert hole", inserts), ("the wall's inner face", outside)]
    if recess is not None:
        others.append(("a seat recess", recess))
    for what, s in others:
        if C.gap(t, s) > 3:
            continue
        v = (t ^ s).volume()
        g = 0.0 if v > 1e-6 else t.min_gap(s, 3)
        if g < P.pocket_wall_mm:
            rows.append((g, k.name, what, v))
rows.sort()
seen = set()
for g, a, b, v in rows:
    key = tuple(sorted((a, b.split(" ")[0]))) + (b.split(" ", 1)[1] if b.startswith("matrix") or b.startswith("thumb") else b,)
    if key in seen:
        continue
    seen.add(key)
    print(f"  {g:5.2f} mm  {a} tile room to {b}" + (f"  (they overlap by {v:.2f} mm^3)" if v > 1e-6 else ""))
if not rows:
    print("  none")

print("== one key's pocket in its own frame (matrix_middle_home)")
k = L.key_named("matrix_middle_home")
block = R.plate_block() + S.pocket_block()
pocket = block - union(R.mx_switch_room()) - union(R.tile_room())
t = P.capybara["tile"]
zc = R.tile_top_z() + t["clearance_mm"] - 0.05     # just under the pocket's ceiling
sec = pocket.slice(zc)
polys = sec.to_polygons()
print(f"  section {zc:.2f} mm under the plate top: {len(polys)} loops; bounds {np.round(sec.bounds(), 2)}")
# the ceiling ring's width on each side: the solid between the switch room and the tile room's wall
hole = P.switch_cutout_mm / 2 + P.switch_cutout_clearance_mm
half = t["size_mm"][0] / 2 + t["clearance_mm"]
relief = hole + P.switch_clip_relief_mm + P.switch_cutout_clearance_mm + 0.1
print(f"  tile room half-width {half:.2f}, switch hole half-width {hole:.2f}: ceiling ledge {half - hole:.2f} mm wide on +-x; "
      f"clip relief reaches {relief:.2f}: ledge {half - relief:.2f} mm wide over the clips on +-y")
# the pegs: section through the pocket below the sleeve
zp = R.tile_top_z() - 0.8
sec = pocket.slice(zp)
for loop in sec.to_polygons():
    a = np.asarray(loop)
    if (np.abs(a).max(axis=0) < 9.5).all() and np.ptp(a[:, 0]) < 4 and np.ptp(a[:, 1]) < 4:
        print(f"  a peg's section at z {zp}: extent {np.ptp(a[:, 0]):.2f} x {np.ptp(a[:, 1]):.2f} mm, centre ({a[:, 0].mean():.2f}, {a[:, 1].mean():.2f})")
pegs = R.posts()
bb = pegs.bounding_box()
print(f"  pegs: radius {t['corner_notch_mm']['radius_mm'] - P.peg_fit_mm:.2f} mm, z {bb[2]:.2f} to {bb[5]:.2f} ({bb[5] - bb[2]:.2f} mm tall), "
      f"web {t['corner_notch_mm']['inset_mm'] + t['clearance_mm'] + 0.1:.2f} mm square to the pocket's corner")
notch = union(R.notch_cuts(t["corner_notch_mm"]["radius_mm"], t["corner_notch_mm"]["inset_mm"], -10, 20))
drawn = R.tile()[0].solid
print(f"  the drawn tile against its pegs: overlap {(drawn ^ pegs).volume():.4f} mm^3, least gap {drawn.min_gap(pegs, 2):.3f} mm")
print(f"  the pocket's wall below the sleeve: {P.pocket_wall_mm} mm; the pocket's bottom at {R.tile_top_z() - t['size_mm'][2]:.2f} under the plate top, the tile room's bottom at {R.tile_bottom_z():.2f}")

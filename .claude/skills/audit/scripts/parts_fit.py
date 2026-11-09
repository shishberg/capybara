"""Can the Pro Micro, the TRRS jack and the reset switch go into the capybara
body with the plinth off, and does the plinth then come up under them: swept
volumes against the real body and plinth solids (Manifold)."""
import numpy as np
from manifold3d import Manifold

import common as A
from lowpro.lib import origin, xdir, xform

P, S, R, C = A.P, A.S, A.R, A.C
body, plate = S.body(), S.bottom_plate()


def sweep(solid, d):
    """solid swept along the vector d (a Minkowski sum with that segment)."""
    seg = Manifold.cube((0.02, 0.02, 0.02)).translate((-0.01, -0.01, -0.01))
    seg = Manifold.hull_points([(0, 0, 0), tuple(d)]) if False else seg
    a = np.asarray(d, float)
    L = np.linalg.norm(a)
    # a thin box along d: build along z then rotate
    box = Manifold.cube((0.02, 0.02, L)).translate((-0.01, -0.01, 0))
    z = a / L
    x = np.cross(z, [1, 0, 0]) if abs(z[0]) < 0.9 else np.cross(z, [0, 1, 0])
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    m = np.c_[x, y, z, np.zeros(3)]
    box = box.transform(m)
    return solid.minkowski_sum(box)


def hits(solid, cases, what):
    out = []
    for case, name in cases:
        v = (solid ^ case).volume()
        if v > 1e-3:
            b = (solid ^ case).bounding_box()
            out.append(f"{name} {v:.2f} mm^3 at x {b[0]:.1f}..{b[3]:.1f} y {b[1]:.1f}..{b[4]:.1f} z {b[2]:.1f}..{b[5]:.1f}")
    print(f"  {what}: " + ("; ".join(out) if out else "clear"))
    return out


cases = [(body, "the body")]
both = [(body, "the body"), (plate, "the plinth")]

# ---------------------------------------------------------------- Pro Micro
f = S.part_frame("pro_micro")
pm = {p.label: p.solid for p in R.pro_micro()}
board_parts = R.union([pm["Pro Micro"], pm["USB-C receptacle"], pm["Pro Micro parts"], pm["Dupont housings"]])
with_exit = board_parts + pm["the wires' room over the housings"]
pl = lambda s, dx=0, tilt=0: C.placed(f @ A.L.trans((dx, 0, 0)) if tilt == 0 else f @ A.L.trans((dx, 0, 0)) @ A.L.rot_y(tilt), s)
print("== Pro Micro (board 33.3 x 18 x 1.6, receptacle 7.35 x 8.94 x 3.26 overhanging 1, housings 2.5 + 14 + 3 exit over the board)")
print(f"  frame origin {np.round(origin(f), 2)} (board underside at z {origin(f)[2]:.2f}, seam {S.seam()}, standoff {R.mcu()['standoff_mm']}); -x (to the wall) is world {np.round(xdir(f, (-1, 0, 0))[:3], 2)}")
hits(pl(board_parts), both, "in place (board, receptacle, parts, housings)")
hits(pl(with_exit), both, "in place with the wires' exit room")
hits(sweep(pl(board_parts), (0, 0, -30)), cases, "straight up into place from 30 mm below (plinth off, body upside down)")
for dx in (0.3, 0.8, 1.0, 1.5, 2.0):
    hits(pl(board_parts, dx), cases, f"slid {dx} mm back from the wall (+x in its frame)")
    hits(sweep(pl(board_parts, dx), (0, 0, -30)), cases, f"  ... and swept up from 30 mm below at that offset")
for tilt in (3, 6, 10):
    hits(pl(board_parts, 0, tilt), cases, f"tilted {tilt} deg about its port end (tail down)")
# the cradle coming up under the board in place
cr = R.union(S.place(f, R.mcu_cradle()) )
cr = cr ^ S.inside_prism(C.put_back_mm)
hits(sweep(cr, (0, 0, -20)), [(pl(with_exit), "the board with its housings")], "the Pro Micro's cradle rising 20 mm into place")
hits(cr, [(pl(with_exit), "the board")], "the cradle in place")
b = cr.bounding_box()
print(f"  cradle bounds z {b[2]:.2f}..{b[5]:.2f}; guides reach {R.mcu()['cradle']['above_mm']} over the board's top at z {origin(f)[2] + R.mcu()['board_mm'][2]:.2f}")
# the skin over each wired pin
mesh = A.stl("body")
print("  skin over the wired pins (housing top z, exit room top z, body's first material above):")
for n_ in R.plug_pins():
    x, y, z = R.pin_at(n_)
    w = xform(S.part_frame("pro_micro"), (x, y, z))[:3]
    o = np.array([(-1 if A.HALF == "left" else 1) * w[0], w[1], w[2] + 0.5])
    locs, _, _ = mesh.ray.intersects_location([o], [[0, 0, 1]], multiple_hits=True)
    zz = np.sort(locs[:, 2]) if len(locs) else []
    top_h = w[2] + R.mcu()["dupont"]["spacer_mm"] + R.mcu()["dupont"]["housing_mm"][2]
    print(f"    pin {n_:2d} at world ({w[0]:.1f}, {w[1]:.1f}): housing top {top_h:.1f}, exit top {top_h + R.mcu()['dupont']['exit_mm']:.1f}, body above at z {np.round(zz[:2], 1) if len(zz) else 'none'}")
print(f"  header pin tails: a standard 2.54 mm header (11.5 mm pin: 6 above the 2.5 spacer, 1.6 board) leaves ~3 mm below the board; the standoff is {R.mcu()['standoff_mm']} mm over the seam "
      f"and the plinth's top is {S.seam() - S.plinth_top():.1f} below that: {R.mcu()['standoff_mm'] + S.seam() - S.plinth_top():.1f} mm for tails and solder beside the 9 mm rest")

# ---------------------------------------------------------------- TRRS
f = S.part_frame("trrs")
jk = R.union([p.solid for p in R.trrs_jack()])
j = R.jack()
print(f"\n== TRRS jack (body {j['body_mm']}, barrel {j['barrel_mm'][1]} dia x {j['barrel_mm'][0]} long, standoff {j['standoff_mm']})")
print(f"  frame origin {np.round(origin(f), 2)}; barrel from x {R.trrs_mouth_x():.2f} to {-j['body_mm'][0] / 2:.2f}; wall from {S.face_x('trrs'):.2f} to {S.face_x('trrs') + P.wall_mm:.2f}: "
      f"barrel inside the wall {S.face_x('trrs') + P.wall_mm - R.trrs_mouth_x():.2f} mm of its {j['barrel_mm'][0]}; body front {S.face_x('trrs') + P.wall_mm + j['body_mm'][0] / 2:.2f} past the inner face (+ inside)")
hits(C.placed(f, jk), both, "in place")
hits(sweep(C.placed(f, jk), (0, 0, -30)), cases, "straight up from 30 mm below")
for dx in (1.0, 1.6, 2.0, 3.0):
    hits(C.placed(f @ A.L.trans((dx, 0, 0)), jk), cases, f"slid {dx} mm back from the wall")
    hits(sweep(C.placed(f @ A.L.trans((dx, 0, 0)), jk), (0, 0, -30)), cases, f"  ... and swept up from 30 mm below at that offset")
jc = R.union(S.place(f, R.jack_cradle())) ^ S.inside_prism(C.put_back_mm)
hits(sweep(jc, (0, 0, -20)), [(C.placed(f, jk), "the jack")], "the jack's cradle rising 20 mm into place")
b = jc.bounding_box()
print(f"  jack cradle bounds x {b[0]:.1f}..{b[3]:.1f} y {b[1]:.1f}..{b[4]:.1f} z {b[2]:.2f}..{b[5]:.2f}; walls {R.mcu()['cradle']['wall_mm']} mm thick and {R.mcu()['cradle']['jack_walls']} of the jack's height, jack clearance {j['clearance_mm']}")

# ---------------------------------------------------------------- reset
f = S.part_frame("reset")
rs = R.union([p.solid for p in R.reset_switch()])
r = R.reset()
print(f"\n== reset switch (body {r['body_mm']}, legs span {r['leg_span_mm']}, standoff {r['standoff_mm']})")
hits(C.placed(f, rs), both, "in place")
hits(sweep(C.placed(f, rs), (0, 0, -20)), cases, "straight up into its slot from 20 mm below")
for dz in (0.2, 0.4, 0.6):
    hits(C.placed(f @ A.L.trans((0, 0, dz)), rs), both, f"pushed {dz} mm back into the case")
hits(sweep(R.union(S.place(f, R.reset_stop())), (0, 0, -20)), [(C.placed(f, rs), "the switch")], "the stop rising 20 mm into place")
st = R.union(S.place(f, R.reset_stop())).bounding_box()
print(f"  stop bounds x {st[0]:.1f}..{st[3]:.1f} y {st[1]:.1f}..{st[4]:.1f} z {st[2]:.2f}..{st[5]:.2f}; switch body top z {xform(f, (r['body_mm'][0] / 2, 0, 0))[2]:.2f}, bottom {xform(f, (-r['body_mm'][0] / 2, 0, 0))[2]:.2f}")
print(f"  the slot's closed end is {r['body_mm'][0] / 2 + r['clearance_mm']:.2f} above the plunger's centre: the switch upside down rests on it with {r['clearance_mm']} mm play; between the skin and the stop it has {A.P.reset_stop_gap_mm} mm")

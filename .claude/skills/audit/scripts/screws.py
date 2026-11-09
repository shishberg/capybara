"""Screws, inserts, bosses, seats of the capybara body and plinth, measured on
the built STLs and the Manifold solids. AUDIT_HALF=left for the left half."""
import numpy as np
import trimesh

import common as A

P, S, R, C = A.P, A.S, A.R, A.C
body, plate = A.stl("body"), A.stl("plate")
shell_top = A.mesh_of(C.body_shell().mirror((1, 0, 0)) if A.HALF == "left" else C.body_shell())
pts = S.screw_points()
seat = S.screw_seat_z()
sign = -1 if A.HALF == "left" else 1

print(f"half {A.HALF}: seat z {seat}, plinth top {S.plinth_top()}, seam {S.seam()}")
print(f"insert hole d {P.insert_d} depth {P.insert_depth_mm}, insert L {P.insert_len_mm}, screw M2 x {P.screw_len_mm}, boss {P.screw_boss_mm}")
print(f"head d {P.screw_head_d} h {P.screw_head_h_mm}, counterbore d {R.counterbore_d()}, grip {P.screw_grip_mm}")
hole = S.insert_holes()[0].bounding_box()
print(f"insert hole z {hole[2]:.2f}..{hole[5]:.2f} (from the boss's foot at {S.seam() + (seat - S.plinth_top()):.2f})")
print(f"pad d {2 * S.pad_r()} up to z {seat}; recess d {2 * S.recess_r()} from the seam up to {seat + P.plate_gap_mm}")
print(f"counterbore depth from the desk {seat - P.screw_grip_mm:.2f}, head {P.screw_head_h_mm} tall -> proud by {P.screw_head_h_mm - (seat - P.screw_grip_mm):.2f}")
tip = P.screw_head_h_mm + P.screw_len_mm
print(f"screw tip at z {tip:.2f} (head flush with the desk); insert from {seat + P.plate_gap_mm:.2f} to {seat + P.plate_gap_mm + P.insert_len_mm:.2f}: "
      f"engagement {tip - (seat + P.plate_gap_mm):.2f} mm, hole top {hole[5]:.2f}")


def hits_along(mesh, o, d, far=60):
    locs, idx, _ = mesh.ray.intersects_location([o], [d], multiple_hits=True)
    if len(locs) == 0:
        return []
    t = (locs - o) @ np.asarray(d) / np.linalg.norm(d)
    return sorted(t[t > 1e-6])


for i, p in enumerate(pts):
    x, y = sign * float(p[0]), float(p[1])
    print(f"\n== screw {i + 1} at ({x:.2f}, {y:.2f})")
    # the top surface over the screw, and the skin left over the hole
    top = hits_along(shell_top, np.array([x, y, -5.0]), [0, 0, 1])
    bt = hits_along(body, np.array([x, y, -5.0]), [0, 0, 1])
    print(f"  shell top over the axis z {top[-1] - 5:.2f}; body along the axis enters/leaves at z {[round(t - 5, 2) for t in bt]}")
    print(f"  skin over the hole's top: {top[-1] - 5 - hole[5]:.2f} mm")
    # radial wall round the hole: from the axis outward at several heights, the first exit of the body after entering it
    worst = (99, None)
    for z in np.arange(hole[2] + 0.3, min(hole[5], top[-1] - 5 - 0.5), 0.5):
        for a in np.radians(np.arange(0, 360, 10)):
            d = np.array([np.cos(a), np.sin(a), 0])
            ts = hits_along(body, np.array([x, y, z]), d)
            # first hit is the hole's wall (enter), second the boss's outside (leave)
            if len(ts) >= 2:
                wall = ts[1] - ts[0]
                if wall < worst[0]:
                    worst = (wall, (round(z, 2), round(np.degrees(a))))
    print(f"  thinnest wall round the hole {worst[0]:.2f} mm at z {worst[1][0]}, bearing {worst[1][1]} deg")
    # at a few heights, the boss's outside radius each way, to see where it's joined to something
    for z in (hole[2] + 0.5, (hole[2] + hole[5]) / 2, hole[5] - 0.3):
        outs = []
        for a in np.radians(np.arange(0, 360, 45)):
            d = np.array([np.cos(a), np.sin(a), 0])
            ts = hits_along(body, np.array([x, y, z]), d)
            outs.append(round(ts[1], 1) if len(ts) >= 2 else None)
        print(f"  z {z:.2f}: solid from the axis out to r {outs} (every 45 deg from +x)")
    # recess in the body underside: ray up from below the seam at radii
    prof = []
    for r in (0, 2.0, 3.0, 3.1, 3.3, 3.5):
        zs = []
        for a in np.radians(np.arange(0, 360, 30)):
            o = np.array([x + r * np.cos(a), y + r * np.sin(a), -1.0])
            ts = hits_along(body, o, [0, 0, 1])
            zs.append(round(ts[0] - 1, 2) if ts else None)
        prof.append((r, zs))
    for r, zs in prof:
        print(f"  body underside at r {r}: first material at z {sorted(set(zs), key=lambda v: (v is None, v))}")
    d_out = float(C.outline_distance((sign * x, y)))
    print(f"  distance to the outline {d_out:.2f}; wall outside the recess {d_out - S.recess_r():.2f}; outside the boss {d_out - P.screw_boss_mm / 2:.2f}")
    # the pad on the plinth
    zs = []
    for r in (0, 1.5, 2.5, 3.0, 3.2, 3.4):
        zz = []
        for a in np.radians(np.arange(0, 360, 60)):
            o = np.array([x + r * np.cos(a), y + r * np.sin(a), 20.0])
            ts = hits_along(plate, o, [0, 0, -1])
            zz.append(round(20 - ts[0], 2) if ts else None)
        zs.append((r, sorted(set(zz), key=lambda v: (v is None, v))))
    print(f"  plinth top from above at r: {zs}")
    # the counterbore from below
    for r in (0, 1.0, 1.3, 2.0, 2.2):
        zz = []
        for a in np.radians(np.arange(0, 360, 60)):
            o = np.array([x + r * np.cos(a), y + r * np.sin(a), -5.0])
            ts = hits_along(plate, o, [0, 0, 1])
            zz.append(round(ts[0] - 5, 2) if ts else None)
        print(f"  plinth from below at r {r}: first material at z {sorted(set(zz), key=lambda v: (v is None, v))}")

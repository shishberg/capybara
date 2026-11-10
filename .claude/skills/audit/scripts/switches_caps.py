"""Switch and cap fit on the Manifold body: the switch hole and the clip land
in the 3 mm plate, the rim room over the plate, the least distance between
neighbouring caps at rest and at full travel, and between each pressed cap
and the body.

    python switches_caps.py
"""
import numpy as np
from manifold3d import CrossSection, Manifold

import common as A
from case.lib import rinv


def width(cs, axis, at, lo, hi):
    probe = (CrossSection.square((hi - lo, 0.02)).translate((lo, at - 0.01)) if axis == 0
             else CrossSection.square((0.02, hi - lo)).translate((at - 0.01, lo)))
    return (cs ^ probe).area() / 0.02


def plate_report(body):
    """At each key: the hole across x and y at mid-plate; the plate's thickness
    over the clip relief (the land the clip bites) and beside it."""
    print("== switch hole and clip land per key (mm): hole across x / y at z -0.75; land over the +y relief at x 0 (design 1.5), plate beside the relief at x 5 (design 3.0), relief depth past the hole")
    seen = {}
    for k in A.L.keys():
        bk = A.C.placed(rinv(k.frame), body) ^ Manifold.cube((24, 24, 12)).translate((-12, -12, -9))
        cs = bk.slice(-0.75)
        gap_x = 24 - width(cs, 0, 0.0, -12, 12)      # the hole plus anything outside the plate within 12
        # Measure the hole directly: the empty run through the centre.
        hole_x = empty_run(cs, 0)
        hole_y = empty_run(cs, 1)
        # Land: the body's z extent through a column at (0, 7.9): over the relief (hole 7.15 to 8.6).
        col = Manifold.cylinder(12, 0.15, 0.15, 12).translate((0, 7.9, -9))
        hit = (bk ^ col).bounding_box()
        land = hit[5] - hit[2] if (bk ^ col).volume() > 1e-9 else 0
        col2 = Manifold.cylinder(12, 0.15, 0.15, 12).translate((5.0, 7.9, -9))
        hit2 = (bk ^ col2).bounding_box()
        beside = hit2[5] - hit2[2]
        # Relief depth: the empty run along y at x 0 at z -3 (inside the relief), past the hole's edge.
        cs3 = bk.slice(-3.0)
        relief = empty_run(cs3, 1) / 2 - hole_y / 2
        row = (round(hole_x, 2), round(hole_y, 2), round(land, 2), round(beside, 2), round(relief, 2))
        seen.setdefault(row, []).append(k.name)
    for row, names in seen.items():
        print(f"  hole {row[0]} x {row[1]}, land {row[2]}, plate beside {row[3]}, relief {row[4]}: {len(names)} keys" + ("" if len(names) > 3 else f" ({', '.join(names)})"))


def empty_run(cs, axis):
    """The empty run through the origin along `axis` (0 x, 1 y), to 12 mm each way."""
    lo = hi = 0.0
    step = 0.05
    while hi < 12 and (cs ^ (CrossSection.square((step, 0.02)).translate((hi, -0.01)) if axis == 0 else CrossSection.square((0.02, step)).translate((-0.01, hi)))).area() < 1e-6:
        hi += step
    while lo > -12 and (cs ^ (CrossSection.square((step, 0.02)).translate((lo - step, -0.01)) if axis == 0 else CrossSection.square((0.02, step)).translate((-0.01, lo - step)))).area() < 1e-6:
        lo -= step
    return hi - lo


def caps_report(body):
    for pressed, label in ((0, "at rest"), (A.P.cap_travel_mm, "at full travel")):
        caps = A.C.keycaps(pressed)
        names = [k.name for k in A.L.keys()]
        pairs = []
        for i in range(len(caps)):
            for j in range(i + 1, len(caps)):
                v = (caps[i].solid ^ caps[j].solid).volume()
                g = 0.0 if v > 1e-6 else caps[i].solid.min_gap(caps[j].solid, 3.0)
                if g < 3.0:
                    pairs.append((g, names[i], names[j], v))
        pairs.sort()
        print(f"== caps {label}: nearest pairs (mm; the build holds 0.3)")
        for g, a, b, v in pairs[:6]:
            print(f"  {g:.3f}  {a} / {b}" + (f"  MEET {v:.2f} mm^3" if v else ""))
        gaps = []
        for name, c in zip(names, caps):
            v = (c.solid ^ body).volume()
            g = 0.0 if v > 1e-6 else c.solid.min_gap(body, 2.0)
            gaps.append((g, name, v))
        gaps.sort()
        print(f"== caps {label}: least gap to the body (mm; the rooms give {A.P.cap_room_clearance_mm} all round)")
        for g, name, v in gaps[:6]:
            print(f"  {g:.3f}  {name}" + (f"  MEETS the body {v:.2f} mm^3" if v else ""))


def rim_report(body):
    """The room over each plate for the switch's 15.8 rim: the body within the
    rim's footprint plus 0.15 from the plate top up to the cap's bottom at full travel."""
    w = A.P.switch_rim_mm + 2 * A.P.switch_cutout_clearance_mm
    h = A.P.cap_bottom_above_plate_mm - A.P.cap_travel_mm
    print(f"== rim room: body inside the {w:.2f} square over the plate from 0 to {h} mm up (mm^3; design 0)")
    bad = []
    for k in A.L.keys():
        probe = A.C.placed(k.frame, Manifold.cube((w, w, h)).translate((-w / 2, -w / 2, 0.0)))
        v = (probe ^ body).volume()
        if v > 1e-3:
            bad.append((v, k.name))
    print("  " + (", ".join(f"{n} {v:.2f}" for v, n in sorted(bad, reverse=True)) if bad else "none"))


def main():
    body = A.S.body()
    print(f"half {A.HALF}")
    plate_report(body)
    rim_report(body)
    caps_report(body)


if __name__ == "__main__":
    main()

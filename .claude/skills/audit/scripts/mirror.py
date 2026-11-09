"""Left against right: builds both halves' body and plinth, mirrors the right in
x, and reports the symmetric difference's volume and where its pieces are
(expected: only the switch pin and collar holes, which are handed), and
whether the screw points mirror.

    python mirror.py
"""
import numpy as np

import common as A


def build(half):
    A.P.half = half
    A.L.reset()
    return A.S.body(), A.S.bottom_plate(), [np.array(p, float) for p in A.S.screw_points()]


def compare(name, right, left):
    # build.py builds the left in the right's axes (only the switch pins are handed) and mirrors it for the STL,
    # so the two builds should match but for the pin and collar holes.
    d = (right - left) + (left - right)
    print(f"== {name}: right {right.volume():.1f} mm^3, left {left.volume():.1f} mm^3, differ by {d.volume():.3f} mm^3")
    pieces = sorted(d.decompose(), key=lambda p: -p.volume())
    print(f"   {len(pieces)} pieces; the largest:")
    for p in pieces[:12]:
        bb = p.bounding_box()
        c = np.array([(bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, (bb[2] + bb[5]) / 2])
        print(f"     {p.volume():8.3f} mm^3 at ({c[0]:.1f}, {c[1]:.1f}, {c[2]:.1f}), {bb[3] - bb[0]:.1f} x {bb[4] - bb[1]:.1f} x {bb[5] - bb[2]:.1f}, near {A.label(c)}")


def main():
    rb, rp, rs = build("right")
    lb, lp, ls = build("left")
    print("screw points: right", [tuple(np.round(p, 2)) for p in rs])
    print("              left ", [tuple(np.round(p, 2)) for p in ls])
    mirrored = sorted((round(p[0], 3), round(p[1], 3)) for p in rs)   # the left is built in the right's axes
    lefts = sorted((round(p[0], 3), round(p[1], 3)) for p in ls)
    print("   left build == right build (same axes):", mirrored == lefts)
    # The left STL is the left build mirrored (build.for_half), so compare the solids as built: the
    # left build in its own axes is the mirror image of the left STL; mirror the right build for the pair.
    compare("body (both as built; the left STL is the left build mirrored)", rb, lb)
    compare("plinth", rp, lp)
    import trimesh
    A.built()
    lstl = trimesh.load(f"{A.OUT}/left-body.stl", force="mesh")
    rstl = trimesh.load(f"{A.OUT}/right-body.stl", force="mesh")
    print(f"STL volumes: right-body {rstl.volume:.1f}, left-body {lstl.volume:.1f}; left STL x range {lstl.bounds[0][0]:.2f}..{lstl.bounds[1][0]:.2f}, right {rstl.bounds[0][0]:.2f}..{rstl.bounds[1][0]:.2f}")
    A.P.half = "right"
    A.L.reset()


if __name__ == "__main__":
    main()

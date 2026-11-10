"""How far each tile can back out of its pocket down the key's axis before it
meets the body (the free way in, found by bisection to 0.01 mm), with the exact
tile and with its clearance boxes, and what it meets first. A tile needs at
least 1.7 mm (the pegs' length, 1.6 mm board plus 0.1) to come off its pegs
level, and in practice several mm to be offered up.

    python way_free.py
"""
import numpy as np

import common as A
from case.lib import trans

import ways_in as W


def free_travel(local, solids, m, limit=6.0):
    def hit(d):
        s = A.R.union([A.C.placed(m @ trans((0, 0, -d)), x) for x in solids])
        return (s ^ local).volume() > 1e-4
    # Step, since an obstacle can sit between two clear positions.
    for d in np.arange(0.1, limit + 0.001, 0.1):
        if hit(d):
            s = A.R.union([A.C.placed(m @ trans((0, 0, -(d + 0.3))), x) for x in solids])
            return d - 0.1, s ^ local
    return limit, None


def main():
    body = A.S.body()
    print(f"half {A.HALF}: free way out of the pocket down the key's axis (mm, limit 6), and what stops it 0.3 mm on")
    for k in A.L.keys():
        region = A.C.placed(k.frame, A.R.box((60, 60, 60), (0, 0, -20)))
        local = body ^ region
        row = f"  {k.name:22s}"
        for name, solids in (("tile", [p.solid for p in A.R.tile()]), ("clearance", A.R.tile_room())):
            d, what = free_travel(local, solids, k.frame)
            if what is None:
                row += f"  {name} > 6"
            else:
                bb = what.bounding_box()
                # Which piece of the tile reaches it: test each piece on its own.
                pieces = []
                for p in (A.R.tile() if name == "tile" else [A.R.Piece(n, "", s) for n, s in zip(["board", "socket", "LED", "diode"], solids)]):
                    v = (A.C.placed(k.frame @ trans((0, 0, -(d + 0.3))), p.solid) ^ local).volume()
                    if v > 1e-4:
                        pieces.append(f"{p.label} {v:.2f}")
                row += f"  {name} {d:.2f} ({W.what_is(what)}; by {', '.join(pieces)}; z {bb[2]:.1f}..{bb[5]:.1f})"
        print(row, flush=True)


if __name__ == "__main__":
    main()

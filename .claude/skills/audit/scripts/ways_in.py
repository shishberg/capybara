"""Each tile's way into its pocket, with the plinth off and the body upside
down: the tile comes up the key's z axis from the open seam side. Sweeps the
seated tile (its notched board and parts, with and without clearance) down the
key's -z for 25 mm in steps and intersects each step with the body; where a
step hits, says what it hits and at what travel. Where the straight way is
blocked below the pegs, tries a tilted entry: level for the first 2 mm (the
notches riding the pegs), then rotated about each bottom edge by 5, 10, 15
degrees and swept on down tilted.

    python ways_in.py
"""
import sys

import numpy as np
from manifold3d import Manifold

import common as A
from lowpro.lib import rot_x, rot_y, trans

STEP = 0.5
FAR = 25.0


def tile_solids(clear):
    if clear:
        return A.R.tile_room()       # the clearance boxes less the pegs' columns
    return [p.solid for p in A.R.tile()]


_blocks = None


def what_is(solid):
    """What of the body a hit volume is: the walls, each key's plate and pocket block, or the skin."""
    global _blocks
    if _blocks is None:
        _blocks = [(k.name, A.C.placed(k.frame, A.R.plate_block() + A.S.pocket_block())) for k in A.L.keys()]
    parts = []
    v = (solid - A.S.inside_prism()).volume()
    if v > 1e-3:
        parts.append(f"the wall {v:.2f}")
    for name, b in _blocks:
        v = (solid ^ b).volume()
        if v > 1e-3:
            parts.append(f"{name}'s block {v:.2f}")
    return ", ".join(parts) or "the skin or a boss"


def sweep_steps(solids, m, travels, pre=np.eye(4)):
    """The solids under frame m, moved by `pre` in the key frame, then down
    the key's z by each travel: a list of (travel, solid in world)."""
    out = []
    for d in travels:
        s = A.R.union([A.C.placed(m @ trans((0, 0, -d)) @ pre, x) for x in solids])
        out.append((d, s))
    return out


def hits(body, steps):
    """(travel, overlap mm^3, bbox) for each step that meets the body."""
    out = []
    for d, s in steps:
        v = (s ^ body).volume()
        if v > 1e-3:
            out.append((d, v, (s ^ body).bounding_box()))
    return out


def describe(body, name, m, clear):
    solids = tile_solids(clear)
    # The body near this key only, for speed: a 60 mm box round the tile's sweep.
    region = A.C.placed(m, A.R.box((60, 60, 60), (0, 0, -20)))
    local = body ^ region
    travels = np.r_[np.arange(0, 3, 0.25), np.arange(3, FAR + 0.01, STEP)]
    h = hits(local, sweep_steps(solids, m, travels))
    # Own-peg contact: at travel under 1.7 the notches ride the pegs; with the
    # notched tile there's 0.15 radial fit so nothing should touch even there.
    if not h:
        return f"{name:22s} {'clearance box' if clear else 'tile':14s} straight way clear"
    first = h[0]
    worst = max(h, key=lambda x: x[1])
    bb = worst[2]
    where = what_is(sweep_steps(solids, m, [worst[0]])[0][1] ^ local)
    line = (f"{name:22s} {'clearance box' if clear else 'tile':14s} BLOCKED from travel {first[0]:.2f} mm "
            f"({len(h)} of {len(travels)} steps hit; worst {worst[1]:.2f} mm^3 at travel {worst[0]:.1f}, "
            f"z {bb[2]:.1f}..{bb[5]:.1f}, near {where})")
    below_pegs = [x for x in h if x[0] >= 2.0]
    if below_pegs:
        line += "\n" + vertical(body, m, solids) + "\n" + tilted(local, name, m, solids)
    return line


def vertical(body, m, solids):
    """The realistic approach: the tile level with its pocket, lowered in world
    z (the body stands upright here; upside down it's the tile being dropped
    in) to a point d0 below its seat on the key's axis, then pushed up the
    axis. Sweeps the tile at travel d0 down world -z for 40 mm."""
    out = []
    for d0 in (2.0, 3.0, 4.0, 6.0):
        at = m @ trans((0, 0, -d0))
        steps = [(dz, A.R.union([A.C.placed(at, x).translate((0, 0, -dz)) for x in solids])) for dz in np.arange(0, 40.01, 0.5)]
        h = hits(body, steps)
        h = [x for x in h if x[2][2] > A.S.seam() - 0.01]     # below the seam there's no body
        if not h:
            out.append(f"from {d0:.0f} mm below the seat: clear")
        else:
            worst = max(h, key=lambda x: x[1])
            out.append(f"from {d0:.0f} mm below the seat: hits {len(h)} steps, worst {worst[1]:.1f} mm^3 "
                       f"at {worst[0]:.1f} mm down ({what_is(steps[int(worst[0] * 2)][1] ^ body)})")
    return "      level, lowered in world z: " + "; ".join(out)


def tilted(local, name, m, solids):
    """Tilted entries: level for the first 2 mm, then rotated about each bottom
    edge (the tile's far side swinging down and out) and swept on down."""
    t = A.P.capybara["tile"]
    half, under = t["size_mm"][0] / 2, A.R.tile_top_z() - t["size_mm"][2]
    out = []
    for edge, (axis, sign) in {"-x edge": (rot_y, 1), "+x edge": (rot_y, -1), "-y edge": (rot_x, -1), "+y edge": (rot_x, 1)}.items():
        ex = -half if "-x" in edge else half if "+x" in edge else 0
        ey = -half if "-y" in edge else half if "+y" in edge else 0
        results = []
        for deg in (5, 10, 15):
            # Rotation about the bottom edge's line, at travel 2 (below the pegs).
            # rot_y(+) tips +x down; about the -x edge we want the +x side to drop.
            R = trans((ex, ey, under)) @ axis(sign * deg) @ trans((-ex, -ey, -under))
            arc = sweep_steps(solids, m, [2.0], R)
            arcs = [sweep_steps(solids, m, [2.0], trans((ex, ey, under)) @ axis(sign * a) @ trans((-ex, -ey, -under)))[0]
                    for a in np.linspace(0, deg, 4)[1:-1]]
            down = sweep_steps(solids, m, np.arange(2.0, FAR + 0.01, STEP), R)
            level = sweep_steps(solids, m, np.arange(0, 2.0, 0.25))
            h = hits(local, level + arcs + arc + down)
            results.append(f"{deg} deg {'clear' if not h else f'hits {len(h)} steps, worst {max(x[1] for x in h):.2f} mm^3 at travel {max(h, key=lambda x: x[1])[0]:.1f}'}")
        out.append(f"      tilted about {edge}: " + "; ".join(results))
    return "\n".join(out)


def main():
    body = A.S.body()
    print(f"half {A.HALF}: tiles' ways in, straight down the key's z for {FAR} mm in {STEP} mm steps")
    only = sys.argv[1:]
    for k in A.L.keys():
        if only and k.name not in only:
            continue
        for clear in (False, True):
            print(describe(body, k.name, k.frame, clear), flush=True)


if __name__ == "__main__":
    main()

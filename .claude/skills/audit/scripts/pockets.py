"""The tiles in their pockets, measured on the Manifold body the STL is written
from: the seated tile's gap to the body all round, the pegs' size, length and
necks, the ceiling over the tile, the pocket's ceiling ring and the ledge
beside the clip reliefs, the walls between tile rooms and to the caps' rooms,
the walls and bosses, and the tiles' and sockets' height over the plinth.

    python pockets.py
"""
import numpy as np
from manifold3d import CrossSection, Manifold

import common as A
from lowpro.lib import rinv, trans, xform

T = A.P.capybara["tile"]
SIDE = T["size_mm"][0]
NOTCH_R, INSET = T["corner_notch_mm"]["radius_mm"], T["corner_notch_mm"]["inset_mm"]
TOP = A.R.tile_top_z()                     # -5
UNDER = TOP - T["size_mm"][2]              # -6.6


def in_key(k, solid):
    """The solid in the key's frame."""
    return A.C.placed(rinv(k.frame), solid)


def section_at(k, body_k, z, box=None):
    """The body's section in the key frame at z, clipped to box (x0, y0, x1, y1)."""
    cs = body_k.slice(z)
    if box:
        cs = cs ^ CrossSection.square((box[2] - box[0], box[3] - box[1])).translate((box[0], box[1]))
    return cs


def width_along(cs, axis, at, lo, hi):
    """The solid's extent along `axis` (0 x, 1 y) through the line where the
    other coordinate is `at`, between lo and hi: total covered length."""
    if axis == 0:
        probe = CrossSection.square((hi - lo, 0.02)).translate((lo, at - 0.01))
    else:
        probe = CrossSection.square((0.02, hi - lo)).translate((at - 0.01, lo))
    return (cs ^ probe).area() / 0.02


def tile_gaps(k, body):
    tile = A.R.union([p.solid for p in A.R.tile()])
    seated = A.C.placed(k.frame, tile)
    g = seated.min_gap(body, 3.0)
    # Which way: grow the tile in one direction at a time and see what first meets.
    return g


def peg_report(k, body_k):
    """Each peg's section at mid-tile height, its length and its necks to the walls."""
    d = SIDE / 2 - INSET          # 7.95: the notch centres
    zmid = (TOP + UNDER) / 2
    out = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * d, sy * d
            # The corner region of the pocket: from the notch centre out to the wall's inner face and 0.6 beyond.
            box = (min(cx - 1.3, cx + 1.3 + sx * 0.0), min(cy - 1.3, cy + 1.3), max(cx - 1.3, cx + 1.3), max(cy - 1.3, cy + 1.3))
            x0, x1 = sorted((cx - 1.2, cx + sx * 1.3 if sx > 0 else cx - 1.3))
            cs = section_at(k, body_k, zmid)
            # The peg alone: the section inside the tile's clearance box (17.7 square) near this corner.
            room = CrossSection.square((SIDE + 2 * T["clearance_mm"],) * 2).translate((-(SIDE / 2 + T["clearance_mm"]),) * 2)
            corner = CrossSection.square((3, 3)).translate((cx - 1.5, cy - 1.5))
            peg = cs ^ room ^ corner
            area = peg.area()
            bb = peg.bounds()
            # Diameter across the notch centre, along x and y, within the room.
            dx = width_along(peg, 0, cy, cx - 1.5, cx + 1.5)
            dy = width_along(peg, 1, cx, cy - 1.5, cy + 1.5)
            # The neck to each wall: the covered length along the wall's inner face line (at 8.85 from centre).
            wall = SIDE / 2 + T["clearance_mm"]
            neck_x = width_along(cs ^ corner, 1, sx * (wall - 0.01), cy - 1.5, cy + 1.5)
            neck_y = width_along(cs ^ corner, 0, sy * (wall - 0.01), cx - 1.5, cx + 1.5)
            # Length: the body in a thin column through the notch centre.
            col = Manifold.cylinder(30, 0.3, 0.3, 24).translate((cx, cy, -20))
            hit = (body_k ^ col).bounding_box()
            out.append((sx, sy, area, dx, dy, neck_x, neck_y, hit[2], hit[5]))
    return out


def ceiling_report(k, body_k):
    """The ring over the tile room, just inside the pocket block: the body's
    section 0.03 above the room's ceiling, its width on each side, and at the clips."""
    room_top = TOP + T["clearance_mm"]
    cs = section_at(k, body_k, room_top + 0.03)
    half = SIDE / 2 + T["clearance_mm"]
    widths = {}
    for name, axis, at in (("+x side", 0, 0.0), ("-x side", 0, 0.0), ("+y side", 1, 0.0), ("-y side", 1, 0.0)):
        sign = 1 if name[0] == "+" else -1
        lo, hi = (0, half) if sign > 0 else (-half, 0)
        widths[name] = width_along(cs, axis, at, lo, hi)
    # Beside the clip reliefs: along y at x = 0 the relief takes the ring; at x = +-2.4 (the relief is 5 wide) too.
    for name, x in (("+y at clip", 0.0), ("+y beside clip x=2.6", 2.6)):
        widths[name] = width_along(cs, 1, x, 0, half)
    # The ceiling's height over the tile top (the room's clearance), measured: the body's lowest z over the tile's middle ring.
    probe = Manifold.cube((SIDE, SIDE, 6)).translate((-SIDE / 2, -SIDE / 2, TOP)) - Manifold.cube((14.6, 14.6, 6)).translate((-7.3, -7.3, TOP))
    for sx in (-1, 1):
        for sy in (-1, 1):
            probe -= Manifold.cube((4.0, 4.0, 6)).translate((sx * SIDE / 2 - 2.0, sy * SIDE / 2 - 2.0, TOP))   # the pegs reach 1.5 mm in from the corner, past 2.6
    over = (body_k ^ probe).bounding_box()
    return widths, over[2] - TOP


def pair_walls(keys, body):
    """The least gap between every two tile rooms, between each tile room and
    each cap's room, and between each tile room and the walls and bosses."""
    rooms = [(k.name, A.R.union(A.C.place(k.frame, A.R.tile_room()))) for k in keys]
    caps = list(zip([k.name for k in keys], A.C.cap_rooms()))
    walls = body - A.S.inside_prism()
    bosses = A.R.union([A.S.boss(p) for p in A.S.screw_points()]) ^ A.C.body_shell()
    out = {"tile-tile": [], "tile-cap": [], "tile-wall": [], "tile-boss": []}
    for i, (a, ra) in enumerate(rooms):
        for b, rb in rooms[i + 1:]:
            if (ra ^ rb).volume() > 1e-6:
                out["tile-tile"].append((0.0, a, b))
            else:
                g = ra.min_gap(rb, 2.5)
                if g < 2.5:
                    out["tile-tile"].append((g, a, b))
        for b, cb in caps:
            if a == b:
                continue
            v = (ra ^ cb).volume()
            if v > 1e-6:
                out["tile-cap"].append((0.0, a, b, v))
            else:
                g = ra.min_gap(cb, 1.3)
                if g < 1.3:
                    out["tile-cap"].append((g, a, b, 0.0))
        g = ra.min_gap(walls, 1.3)
        if g < 1.3:
            out["tile-wall"].append((g, a))
        g = ra.min_gap(bosses, 1.3)
        if g < 1.3:
            out["tile-boss"].append((g, a))
    return out


def heights(keys):
    """Each tile's board and its lowest part over the plinth's top."""
    top = A.S.plinth_top()
    out = []
    for k in keys:
        boxes = A.R.tile_boxes()
        board = min(xform(k.frame, c)[2] for c in A.R.box_corners(*boxes[0])) - top
        lowest = min((min(xform(k.frame, c)[2] for c in A.R.box_corners(s, o)) - top, n["name"])
                     for (s, o), n in zip(boxes[1:], T["components"]))
        out.append((k.name, board, lowest))
    return out


def main():
    body = A.S.body()
    keys = A.L.keys()
    print(f"half {A.HALF}")
    print("\n== seated tile's least gap to the body (mm, min_gap on the Manifold solids; design: 0.15 at the pegs)")
    for k in keys:
        print(f"  {k.name:22s} {tile_gaps(k, body):.3f}")

    print("\n== pegs: section at mid-tile height (area mm^2; circle r 0.95 = 2.835 plus the 1.0 web), width across the notch centre along x and y,"
          "\n   neck to the +-x wall and to the +-y wall (mm along the wall's inner face), and z extent in the key frame (design: -6.6 to -4.5)")
    for k in keys:
        body_k = in_key(k, body)
        rows = peg_report(k, body_k)
        for sx, sy, area, dx, dy, nx, ny, z0, z1 in rows:
            print(f"  {k.name:22s} corner ({sx:+d},{sy:+d}) area {area:.2f} dx {dx:.2f} dy {dy:.2f} necks {nx:.2f}/{ny:.2f} z {z0:.2f}..{z1:.2f}")

    print("\n== the ceiling over the tile: ring widths (mm) 0.03 mm above the room's top, and the ceiling's height over the tile's top")
    for k in keys:
        body_k = in_key(k, body)
        widths, over = ceiling_report(k, body_k)
        print(f"  {k.name:22s} over tile {over:.3f}  " + "  ".join(f"{n} {w:.2f}" for n, w in widths.items()))

    print("\n== walls between rooms (mm): tile room to tile room under 2.5, tile room to another key's cap room under 1.3, to the walls and bosses under 1.3")
    w = pair_walls(keys, body)
    for g, a, b in sorted(w["tile-tile"]):
        print(f"  tile-tile {g:.2f}  {a} / {b}")
    for g, a, b, v in sorted(w["tile-cap"]):
        print(f"  tile-cap  {g:.2f}  {a}'s tile room / {b}'s cap room" + (f"  OPEN, {v:.2f} mm^3 shared" if v else ""))
    for g, a in sorted(w["tile-wall"]):
        print(f"  tile-wall {g:.2f}  {a}")
    for g, a in sorted(w["tile-boss"]):
        print(f"  tile-boss {g:.2f}  {a}")
    if not any(w.values()):
        print("  none under the thresholds")

    print("\n== tiles over the plinth's top (mm): the board's lowest corner, and the lowest part")
    for name, board, (low, part) in sorted(heights(keys), key=lambda r: r[1]):
        print(f"  {name:22s} board {board:6.2f}  lowest part {low:6.2f} ({part})")


if __name__ == "__main__":
    main()

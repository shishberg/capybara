"""Build the low-profile Capybara's parts to STL and 3MF. From the repository root:

    .venv/bin/python -m lowpro.build                      # both halves' bodies and plinths, the right assembly, the check
    .venv/bin/python -m lowpro.build --half left --part body
    .venv/bin/python -m lowpro.build --check              # only the checks (exit 1 when one fails)
    .venv/bin/python -m lowpro.build --set tent_deg=4 --set outline_close_mm=12

Any parameter in params.py can be overridden with --set. Files go to
output/lowpro/ (--out): <half>-body.stl, <half>-plate.stl and
right-assembly.3mf (body, plinth, switches, caps, sockets, diodes and
electronics, each piece a named, coloured mesh). The left half is the right
mirrored, but for the switches and sockets, which are the same parts in both, so
each half is its own build.
"""
import argparse
import ast
import sys
import time
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
PARTS = ("body", "plate", "assembly")

COLOURS = {"burlywood": "DEB887", "peru": "CD853F", "ivory": "FFFFF0", "gray": "808080", "gold": "FFD700",
           "dimgray": "696969", "silver": "C0C0C0", "orange": "FFA500", "darkgreen": "006400", "white": "FFFFFF",
           "steelblue": "4682B4", "black": "000000", "red": "FF0000"}


def set_params(assignments):
    from . import params as P

    for assignment in assignments:
        name, _, value = assignment.partition("=")
        if not hasattr(P, name):
            sys.exit(f"no such parameter: {name}")
        setattr(P, name, ast.literal_eval(value))


def mesh_of(solid):
    """A solid's vertices (float64) and triangles."""
    m = solid.to_mesh64()
    return np.asarray(m.vert_properties)[:, :3], np.asarray(m.tri_verts, np.int64)


def refuse_invalid(solid, name):
    """Stop the build on a part that is not one closed manifold solid spanning
    the outline (a boolean that lost the part leaves a fragment, and a stray
    piece or a sliver is a second solid)."""
    from . import chassis as C

    if solid.status().name != "NoError":
        sys.exit(f"{name} is not a closed manifold solid: {solid.status().name}")
    pieces = solid.decompose()
    if len(pieces) != 1:
        sys.exit(f"{name} is {len(pieces)} solids, not one: volumes "
                 + ", ".join(f"{p.volume():.3g} mm^3 at {tuple(round(c, 1) for c in p.bounding_box()[:3])}"
                             for p in sorted(pieces, key=lambda p: -p.volume())[:8]))
    if solid.volume() <= 0:
        sys.exit(f"{name} has no volume")
    box = solid.bounding_box()
    q = C.outline()
    span, want = (box[3] - box[0], box[4] - box[1]), np.ptp(q, axis=0)
    if abs(span[0] - want[0]) > 0.01 or abs(span[1] - want[1]) > 0.01:
        sys.exit(f"{name} does not span the outline: {span[0]:.1f} x {span[1]:.1f} mm, not {want[0]:.1f} x {want[1]:.1f}")


def write_stl(solid, path):
    """A part to binary STL, after refuse_invalid. Each facet's normal is worked
    out from its corners as written (single precision)."""
    refuse_invalid(solid, path.name)
    v, t = mesh_of(solid)
    corners = v[t].astype(np.float32)
    n = np.cross((corners[:, 1] - corners[:, 0]).astype(float), (corners[:, 2] - corners[:, 0]).astype(float))
    n /= np.maximum(np.linalg.norm(n, axis=1), 1e-300)[:, None]
    facets = np.zeros(len(t), dtype=[("normal", "<f4", 3), ("corners", "<f4", (3, 3)), ("attr", "<u2")])
    facets["normal"], facets["corners"] = n, corners
    with open(path, "wb") as f:
        f.write(b"lowpro".ljust(80, b" "))
        f.write(np.uint32(len(t)).tobytes())
        f.write(facets.tobytes())
    print(f"wrote {path} ({len(t)} triangles)", flush=True)


def write_3mf(pieces, path):
    """Named, coloured pieces to one 3MF: each piece an object with one colour."""
    names = sorted({p.colour for p in pieces})
    out = ['<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
           'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">\n<resources>\n<basematerials id="1">\n']
    out += [f'<base name="{c}" displaycolor="#{COLOURS[c]}"/>\n' for c in names]
    out.append("</basematerials>\n")
    for i, piece in enumerate(pieces, start=2):
        v, t = mesh_of(piece.solid)
        out.append(f'<object id="{i}" type="model" name="{piece.label}" pid="1" pindex="{names.index(piece.colour)}">'
                   "<mesh><vertices>\n")
        out.append("\n".join(map('<vertex x="%.4f" y="%.4f" z="%.4f"/>'.__mod__, map(tuple, v))))
        out.append("\n</vertices><triangles>\n")
        out.append("\n".join(map('<triangle v1="%d" v2="%d" v3="%d"/>'.__mod__, map(tuple, t))))
        out.append("\n</triangles></mesh></object>\n")
    out.append("</resources>\n<build>\n")
    out += [f'<item objectid="{i}"/>\n' for i in range(2, len(pieces) + 2)]
    out.append("</build>\n</model>\n")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
                   'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr("3D/3dmodel.model", "".join(out))
    print(f"wrote {path} ({len(pieces)} pieces)", flush=True)


def for_half(solid, half):
    return solid.mirror((1, 0, 0)) if half == "left" else solid


def assembly(body, plate):
    """The right half's pieces: body, plinth, switches, caps, sockets, diodes and electronics."""
    from . import chassis as C
    from .parts import Piece

    return ([Piece("body", "burlywood", body), Piece("plinth", "peru", plate)]
            + C.switches() + C.keycaps() + C.sockets() + C.diodes() + C.electronics())


def check():
    from . import chassis as C

    ok = True
    hits = C.cap_collisions()
    if hits:
        print("keycaps meet: " + ", ".join(f"{a} with {b} ({v:.2f} mm^3)" for a, b, v in hits))
        ok = False
    else:
        print("keycaps clear")
    _, hits = C.screw_walls()
    if hits:
        print("screw holes break into: " + ", ".join(f"{s} into {w} ({v:.2f} mm^3)" for s, w, v in hits))
        ok = False
    else:
        print("screw holes clear")
    thin = C.thin_walls()
    if thin:
        print(f"walls under {C.P.min_wall_mm} mm: " + ", ".join(f"{a} to {b} ({d:.2f} mm)" for a, b, d in thin))
        ok = False
    else:
        print("walls between rooms clear")
    bare = C.thin_tops()
    if bare:
        print(f"under {C.P.min_wall_mm} mm of top: " + ", ".join(f"{w} ({v:.2f} mm^3)" for w, v in bare))
        ok = False
    else:
        print("every room stays under the top")
    lost = C.unwired()
    if lost:
        print("no path to the controller from: " + ", ".join(lost))
        ok = False
    else:
        print("every wire reaches the controller")
    pinched = C.pinched_runs()
    if pinched:
        print(f"a {C.P.wire_d_mm} mm wire can't follow: " + ", ".join(f"{r} ({d:.1f} of {n:.1f} mm)" for r, d, n in pinched))
        ok = False
    else:
        print("a wire follows every channel from end to end")
    crowded = C.crowded_keys()
    if crowded:
        print("no straight wire fits beside the terminal at: " + ", ".join(crowded))
        ok = False
    else:
        print("every column's wire runs straight beside its terminals")
    cramped = C.cramped_diodes()
    if cramped:
        print("no room for the diode and its legs at: " + ", ".join(cramped))
        ok = False
    else:
        print("every diode and its legs fit")
    v = C.part_overlap()
    if v > 1e-6:
        print(f"body and plinth overlap ({v:.3f} mm^3)")
        ok = False
    else:
        print("body and plinth clear")
    clashes = C.part_clashes()
    if clashes:
        print("parts meet the case: " + ", ".join(f"{p} and {w} ({v:.2f} mm^3)" for p, w, v in clashes))
        ok = False
    else:
        print("switches, sockets, electronics and caps at full travel clear the case")
    blocked = C.blocked_parts()
    if blocked:
        print("parts can't drop into the well: " + ", ".join(f"{p} ({v:.2f} mm^3)" for p, v in blocked))
        ok = False
    else:
        print("every part drops into the well")
    wrong = C.true_part_clashes()
    if wrong:
        print("a real switch or socket doesn't fit the mirrored half at: " + ", ".join(f"{k} ({v:.2f} mm^3)" for k, v in wrong))
        ok = False
    elif C.P.half == "left":
        print("real switches and sockets fit the mirrored half")
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--half", choices=("right", "left", "both"), default="both")
    ap.add_argument("--part", action="append", choices=PARTS, help="which parts (default: all)")
    ap.add_argument("--out", default=str(ROOT / "output" / "lowpro"))
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE", help="override a parameter")
    ap.add_argument("--check", action="store_true", help="only run the checks")
    ap.add_argument("--no-check", action="store_true", help="skip the checks")
    ap.add_argument("--verbose", action="store_true", help="print how long each stage takes")
    args = ap.parse_args(argv)
    parts = args.part or list(PARTS)
    halves = ("right", "left") if args.half == "both" else (args.half,)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    t = time.time()

    from . import chassis as C
    from . import layout as L

    C.VERBOSE = args.verbose
    set_params(args.set)
    ok = True
    for half in halves:
        # Each half is its own build: the switches and sockets don't mirror (params.py half).
        C.P.half = half
        L.reset()
        print(f"the {half} half: {C.report()}", flush=True)
        s = C.stage("report", t)
        ok = (True if args.no_check else check()) and ok
        s = C.stage("checks", s)
        if args.check:
            continue
        body = C.body() if {"body", "assembly"} & set(parts) else None
        plate = C.bottom_plate() if {"plate", "assembly"} & set(parts) else None
        s = time.time()
        for name, solid in (("body", body), ("plate", plate)):
            if name in parts:
                write_stl(for_half(solid, half), out / f"{half}-{name}.stl")
        s = C.stage("STL", s)
        if "assembly" in parts and half == "right":
            refuse_invalid(body, "the assembly's body")
            refuse_invalid(plate, "the assembly's plinth")
            write_3mf(assembly(body, plate), out / "right-assembly.3mf")
            C.stage("3MF", s)
    if args.check:
        return 0 if ok else 1
    print(f"built in {time.time() - t:.1f} s", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

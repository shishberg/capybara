"""Build the low-profile Capybara's parts to STL and 3MF. From the repository root:

    python3 -m lowpro.build                      # both halves' bodies and plinths, the right assembly, the check
    python3 -m lowpro.build --half left --part body
    python3 -m lowpro.build --check              # only the checks (exit 1 when one fails; lowpro/README.md lists them)
    python3 -m lowpro.build --set tent_deg=4 --set outline_close_mm=12
    python3 -m lowpro.build --preset capybara    # the Capybara's keys, tiles, caps and TRRS

Any parameter in params.py can be overridden with --set, after a --preset's
(params.py PRESETS). Files go to output/lowpro/ (output/lowpro/<preset>/ with
a preset; --out): <half>-body.stl, <half>-plate.stl and
right-assembly.3mf (body, plinth, switches, caps, sockets, diodes and
electronics, each piece a named, coloured mesh). The left half is the right
mirrored.
"""
import argparse
import ast
import sys
import time
import zipfile
from pathlib import Path

import numpy as np

from .params import PRESETS

ROOT = Path(__file__).resolve().parent.parent
PARTS = ("body", "plate", "assembly")

COLOURS = {"burlywood": "DEB887", "peru": "CD853F", "ivory": "FFFFF0", "gray": "808080", "gold": "FFD700",
           "dimgray": "696969", "silver": "C0C0C0", "orange": "FFA500", "darkgreen": "006400", "white": "FFFFFF",
           "steelblue": "4682B4", "black": "000000", "red": "FF0000", "lightgray": "D3D3D3", "firebrick": "B22222",
           "purple": "800080"}


def set_params(assignments, preset=None):
    """A preset's overrides (params.PRESETS), then each NAME=VALUE."""
    from . import params as P

    for name, value in (P.PRESETS[preset] if preset else {}).items():
        setattr(P, name, value)
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
    lost = C.unwired()
    if lost:
        print("no path to the controller from: " + ", ".join(lost))
        ok = False
    else:
        print("every wire reaches the controller")
    closed = C.closed_ports()
    if closed:
        print("not through the wall: " + ", ".join(closed))
        ok = False
    else:
        print("ports open through the wall")
    if C.P.knob:
        clash = C.knob_clashes()
        if clash:
            print("the knob runs into: " + ", ".join(clash))
            ok = False
        else:
            print("the knob turns clear")
    buried = C.parts_buried()
    if buried:
        print("parts run into: " + ", ".join(f"{a} into {b} ({v:.2f} mm^3)" for a, b, v in buried))
        ok = False
    else:
        print("parts sit in their rooms")
    v = C.part_overlap()
    if v > 1e-6:
        print(f"body and plinth overlap ({v:.3f} mm^3)")
        ok = False
    else:
        print("body and plinth clear")
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--half", choices=("right", "left", "both"), default="both")
    ap.add_argument("--part", action="append", choices=PARTS, help="which parts (default: all)")
    ap.add_argument("--out", help="where to write (default output/lowpro/, or output/lowpro/<preset>/)")
    ap.add_argument("--preset", choices=sorted(PRESETS), help="a named set of overrides (params.py PRESETS)")
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE", help="override a parameter")
    ap.add_argument("--check", action="store_true", help="only run the checks")
    ap.add_argument("--no-check", action="store_true", help="skip the checks")
    ap.add_argument("--verbose", action="store_true", help="print how long each stage takes")
    args = ap.parse_args(argv)
    parts = args.part or list(PARTS)
    halves = ("right", "left") if args.half == "both" else (args.half,)
    out = Path(args.out or ROOT / "output" / "lowpro" / (args.preset or ""))
    out.mkdir(parents=True, exist_ok=True)
    t = time.time()

    from . import chassis as C
    from . import layout as L

    C.VERBOSE = args.verbose
    set_params(args.set, args.preset)
    L.reset()
    print(C.report(), flush=True)
    s = C.stage("report", t)
    ok = True if args.no_check else check()
    s = C.stage("checks", s)
    if args.check:
        return 0 if ok else 1

    body = C.body() if {"body", "assembly"} & set(parts) else None
    plate = C.bottom_plate() if {"plate", "assembly"} & set(parts) else None
    s = time.time()
    for name, solid in (("body", body), ("plate", plate)):
        if name in parts:
            for half in halves:
                write_stl(for_half(solid, half), out / f"{half}-{name}.stl")
    s = C.stage("STL", s)
    if "assembly" in parts:
        refuse_invalid(body, "the assembly's body")
        refuse_invalid(plate, "the assembly's plinth")
        write_3mf(assembly(body, plate), out / "right-assembly.3mf")
        C.stage("3MF", s)
    print(f"built in {time.time() - t:.1f} s", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

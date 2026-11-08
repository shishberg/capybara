"""Build the low-profile Capybara's parts to STL and 3MF. From the repository root:

    .venv/bin/python -m lowpro.build                      # both halves' bodies, plinths and assemblies, the check
    .venv/bin/python -m lowpro.build --half left --part body
    .venv/bin/python -m lowpro.build --check              # only the checks (exit 1 when one fails)
    .venv/bin/python -m lowpro.build --set tent_deg=4 --set outline_close_mm=12
    .venv/bin/python -m lowpro.build --preset capybara    # the capybara design (params.py design)

Any parameter in params.py can be overridden with --set, after a --preset's
(params.py PRESETS). Files go to output/lowpro/ (output/lowpro/<preset>/ with a
preset; --out): <half>-body.stl, <half>-plate.stl and <half>-assembly.3mf
(body, plinth, switches, caps and the design's other parts, each piece a
named, coloured mesh), and for the capybara design <half>-print.3mf (the body
as it prints, with its support enforcers and blockers, for Anycubic Slicer
Next or Bambu Studio). The left half is the right mirrored, but for the
switches and sockets, which are the same parts in both, so each half is its
own build. The design's module (chassis.py or shell.py) builds the parts,
reports its heights and runs its checks.
"""
import argparse
import ast
import sys
import time
import uuid
import zipfile
from dataclasses import replace
from pathlib import Path

import numpy as np

from .params import PRESETS

ROOT = Path(__file__).resolve().parent.parent
PARTS = ("body", "plate", "assembly", "print")

COLOURS = {"burlywood": "DEB887", "peru": "CD853F", "ivory": "FFFFF0", "gray": "808080", "gold": "FFD700",
           "dimgray": "696969", "silver": "C0C0C0", "orange": "FFA500", "darkgreen": "006400", "white": "FFFFFF",
           "steelblue": "4682B4", "black": "000000", "red": "FF0000"}


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


CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
MODEL_REL = "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"


def mesh_xml(solid):
    v, t = mesh_of(solid)
    return ("<mesh><vertices>\n" + "\n".join(map('<vertex x="%.4f" y="%.4f" z="%.4f"/>'.__mod__, map(tuple, v)))
            + "\n</vertices><triangles>\n" + "\n".join(map('<triangle v1="%d" v2="%d" v3="%d"/>'.__mod__, map(tuple, t)))
            + "\n</triangles></mesh>")


def rels(target):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Target="{target}" Id="rel0" Type="{MODEL_REL}"/></Relationships>')


def write_package(path, files):
    """A 3MF package: the content types, the root relationship to 3D/3dmodel.model, then `files`."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr("_rels/.rels", rels("/3D/3dmodel.model"))
        for name, text in files.items():
            z.writestr(name, text)


def write_3mf(pieces, path):
    """Named, coloured pieces to one 3MF: each piece an object with one colour."""
    names = sorted({p.colour for p in pieces})
    out = [f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" xmlns="{CORE}">\n'
           '<resources>\n<basematerials id="1">\n']
    out += [f'<base name="{c}" displaycolor="#{COLOURS[c]}"/>\n' for c in names]
    out.append("</basematerials>\n")
    out += [f'<object id="{i}" type="model" name="{piece.label}" pid="1" pindex="{names.index(piece.colour)}">'
            f"{mesh_xml(piece.solid)}</object>\n" for i, piece in enumerate(pieces, start=2)]
    out.append("</resources>\n<build>\n")
    out += [f'<item objectid="{i}"/>\n' for i in range(2, len(pieces) + 2)]
    out.append("</build>\n</model>\n")
    write_package(path, {"3D/3dmodel.model": "".join(out)})
    print(f"wrote {path} ({len(pieces)} pieces)", flush=True)


def write_print_3mf(name, volumes, settings, path):
    """One object made of named volumes, each (name, subtype, solid) with a Bambu
    Studio subtype (normal_part, support_enforcer, support_blocker), and the
    object's own slicer settings, to a 3MF in Bambu Studio's project format,
    which Anycubic Slicer Next shares: the meshes in 3D/Objects, the object
    their components, the subtypes and settings in Metadata/model_settings.config.
    It is centred on the bed (params.py print_bed_mm). It carries no printer or
    process settings, so the slicer's own apply."""
    from . import params as P

    ns = (f'xmlns="{CORE}" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
          'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p"')
    head = f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" {ns}>\n'
    uid = lambda s: str(uuid.uuid5(uuid.NAMESPACE_URL, f"lowpro/{path.name}/{s}"))
    meshes = "".join(f'<object id="{i}" p:UUID="{uid(n)}" type="model">{mesh_xml(s)}</object>\n'
                     for i, (n, _, s) in enumerate(volumes, start=1))
    whole = len(volumes) + 1
    comps = "".join(f'<component p:path="/3D/Objects/object_1.model" objectid="{i}" p:UUID="{uid("part " + n)}" '
                    'transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n' for i, (n, _, _) in enumerate(volumes, start=1))
    box = volumes[0][2].bounding_box()
    at = [P.print_bed_mm / 2 - (box[i] + box[i + 3]) / 2 for i in (0, 1)]
    root = (head + '<metadata name="Application">BambuStudio-2.0.0.3</metadata>\n'
            '<metadata name="BambuStudio:3mfVersion">1</metadata>\n<resources>\n'
            f'<object id="{whole}" p:UUID="{uid(name)}" type="model"><components>\n{comps}</components></object>\n'
            f'</resources>\n<build p:UUID="{uid("build")}"><item objectid="{whole}" p:UUID="{uid("item")}" '
            f'transform="1 0 0 0 1 0 0 0 1 {at[0]:.4f} {at[1]:.4f} 0" printable="1"/></build>\n</model>\n')
    meta = lambda k, v: f'<metadata key="{k}" value="{v}"/>\n'
    config = ('<?xml version="1.0" encoding="UTF-8"?>\n<config>\n'
              f'<object id="{whole}">\n{meta("name", name)}{meta("extruder", 1)}'
              + "".join(meta(k, v) for k, v in settings.items())
              + "".join(f'<part id="{i}" subtype="{kind}">\n{meta("name", n)}{meta("matrix", "1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1")}</part>\n'
                        for i, (n, kind, _) in enumerate(volumes, start=1))
              + f'</object>\n<plate>\n{meta("plater_id", 1)}<model_instance>\n{meta("object_id", whole)}'
              f'{meta("instance_id", 0)}</model_instance>\n</plate>\n</config>\n')
    write_package(path, {"3D/3dmodel.model": root, "3D/_rels/3dmodel.model.rels": rels("/3D/Objects/object_1.model"),
                         "3D/Objects/object_1.model": head + f"<resources>\n{meshes}</resources>\n<build/>\n</model>\n",
                         "Metadata/model_settings.config": config})
    print(f"wrote {path} ({', '.join(f'{n}: {kind}' for n, kind, _ in volumes)})", flush=True)


def for_half(solid, half):
    return solid.mirror((1, 0, 0)) if half == "left" else solid


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
    halves = ("right", "left") if args.half == "both" else (args.half,)
    out = Path(args.out or ROOT / "output" / "lowpro" / (args.preset or ""))
    out.mkdir(parents=True, exist_ok=True)
    t = time.time()

    from . import chassis as C
    from . import layout as L

    C.VERBOSE = args.verbose
    set_params(args.set, args.preset)
    D = L.design()
    parts = args.part or list(D.OUTPUTS)
    if set(parts) - set(D.OUTPUTS):
        sys.exit(f"the {C.P.design} design has no {', '.join(sorted(set(parts) - set(D.OUTPUTS)))} part")
    ok = True
    for half in halves:
        # Each half is its own build: the switches and sockets don't mirror (params.py half).
        C.P.half = half
        L.reset()
        print(f"the {half} half: {D.report()}", flush=True)
        s = C.stage("report", t)
        ok = (True if args.no_check else D.checks()) and ok
        s = C.stage("checks", s)
        if args.check:
            continue
        body = D.body() if {"body", "assembly", "print"} & set(parts) else None
        plate = D.bottom_plate() if {"plate", "assembly"} & set(parts) else None
        s = time.time()
        for name, solid in (("body", body), ("plate", plate)):
            if name in parts:
                write_stl(for_half(solid, half), out / f"{half}-{name}.stl")
        s = C.stage("STL", s)
        if "assembly" in parts:
            refuse_invalid(body, "the assembly's body")
            refuse_invalid(plate, "the assembly's plinth")
            pieces = [replace(p, solid=for_half(p.solid, half)) for p in D.parts(body, plate)]
            write_3mf(pieces, out / f"{half}-assembly.3mf")
            s = C.stage("3MF", s)
        if "print" in parts:
            refuse_invalid(body, "the print's body")
            volumes = [(n, kind, for_half(solid, half)) for n, kind, solid in D.print_parts(body)]
            write_print_3mf(f"{half} body", volumes, D.PRINT_SETTINGS, out / f"{half}-print.3mf")
            C.stage("print 3MF", s)
    if args.check:
        return 0 if ok else 1
    print(f"built in {time.time() - t:.1f} s", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

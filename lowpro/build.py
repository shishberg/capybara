"""Build the low-profile Capybara's parts to STEP and STL. From the repository root:

    python3 -m lowpro.build                      # both halves' bodies and plinths, the right assembly, the check
    python3 -m lowpro.build --half left --part body
    python3 -m lowpro.build --check              # only the keycap check (exit 1 when caps meet)
    python3 -m lowpro.build --set tent_deg=4 --set thumb_fan=1

Any parameter in params.py can be overridden with --set. Files go to
output/lowpro/ (--out): <half>-body.step/.stl, <half>-plate.step/.stl and
right-assembly.step (body, plinth, switches, caps, sockets, diodes and
electronics, coloured). The left half is the right mirrored.
"""
import argparse
import ast
import sys
import time
from pathlib import Path

from build123d import Color, Compound, Plane, export_step, export_stl, mirror

from . import chassis as C
from . import layout as L
from . import params as P

ROOT = Path(__file__).resolve().parent.parent
PARTS = ("body", "plate", "assembly")


def set_param(assignment):
    name, _, value = assignment.partition("=")
    if not hasattr(P, name):
        sys.exit(f"no such parameter: {name}")
    setattr(P, name, ast.literal_eval(value))


def write(shape, path, stl=True):
    export_step(shape, str(path.with_suffix(".step")))
    if stl:
        export_stl(shape, str(path.with_suffix(".stl")), tolerance=0.02, angular_tolerance=0.2)
    print(f"wrote {path.with_suffix('.step').relative_to(ROOT)}" + (" and .stl" if stl else ""), flush=True)


def for_half(shape, half):
    return mirror(shape, about=Plane.YZ) if half == "left" else shape


def assembly(body, plate):
    body.color, body.label = Color("burlywood"), "body"
    plate.color, plate.label = Color("peru"), "plinth"
    return Compound(children=[body, plate, C.switches(), C.keycaps(), C.sockets(), C.diodes(), C.electronics()],
                    label="capybara-lowpro")


def check():
    hits = C.cap_collisions()
    if hits:
        print("keycaps meet: " + ", ".join(f"{a} with {b} ({v:.2f} mm^3)" for a, b, v in hits))
        return False
    print("keycaps clear")
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--half", choices=("right", "left", "both"), default="both")
    ap.add_argument("--part", action="append", choices=PARTS, help="which parts (default: all)")
    ap.add_argument("--out", default=str(ROOT / "output" / "lowpro"))
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE", help="override a parameter")
    ap.add_argument("--check", action="store_true", help="only run the keycap check")
    ap.add_argument("--no-check", action="store_true", help="skip the keycap check")
    ap.add_argument("--verbose", action="store_true", help="print how long each stage takes")
    args = ap.parse_args(argv)
    C.VERBOSE = args.verbose
    for a in args.set:
        set_param(a)
    L.reset()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(C.report(), flush=True)
    ok = True if args.no_check else check()
    if args.check:
        return 0 if ok else 1

    parts = args.part or list(PARTS)
    halves = ("right", "left") if args.half == "both" else (args.half,)
    t = time.time()
    body = C.body() if {"body", "assembly"} & set(parts) else None
    plate = C.bottom_plate() if {"plate", "assembly"} & set(parts) else None
    print(f"built in {time.time() - t:.0f} s", flush=True)
    for half in halves:
        if "body" in parts:
            write(for_half(body, half), out / f"{half}-body")
        if "plate" in parts:
            write(for_half(plate, half), out / f"{half}-plate")
    if "assembly" in parts:
        write(assembly(body, plate), out / "right-assembly", stl=False)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

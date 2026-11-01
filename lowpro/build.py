"""Build the low-profile Capybara's parts to STEP and STL. From the repository root:

    python3 -m lowpro.build                      # both halves' bodies and plinths, the right assembly, the check
    python3 -m lowpro.build --half left --part body
    python3 -m lowpro.build --check              # only the keycap check (exit 1 when caps meet)
    python3 -m lowpro.build --set tent_deg=4 --set thumb_fan=1

Any parameter in params.py can be overridden with --set. Files go to
output/lowpro/ (--out): <half>-body.step/.stl, <half>-plate.step/.stl and
right-assembly.step (body, plinth, switches, caps, sockets, diodes and
electronics, coloured). The left half is the right mirrored.

The body takes longest, so when the plinth is wanted too it is built, checked
and written by a second process alongside, which then also writes the
assembly once the body reaches it.
"""
import argparse
import ast
import multiprocessing
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTS = ("body", "plate", "assembly")


def set_params(assignments):
    from . import params as P

    for assignment in assignments:
        name, _, value = assignment.partition("=")
        if not hasattr(P, name):
            sys.exit(f"no such parameter: {name}")
        setattr(P, name, ast.literal_eval(value))


def write(shape, path, stl=True):
    from build123d import export_step, export_stl

    export_step(shape, str(path.with_suffix(".step")))
    if stl:
        export_stl(shape, str(path.with_suffix(".stl")), tolerance=0.02, angular_tolerance=0.2)
    print(f"wrote {path.with_suffix('.step')}" + (" and .stl" if stl else ""), flush=True)


def for_half(shape, half):
    from build123d import Plane, mirror

    return mirror(shape, about=Plane.YZ) if half == "left" else shape


def assembly(body, plate):
    from build123d import Color, Compound

    from . import chassis as C

    body.color, body.label = Color("burlywood"), "body"
    plate.color, plate.label = Color("peru"), "plinth"
    return Compound(children=[body, plate, C.switches(), C.keycaps(), C.sockets(), C.diodes(), C.electronics()],
                    label="capybara-lowpro")


def check():
    from . import chassis as C

    hits = C.cap_collisions()
    if hits:
        print("keycaps meet: " + ", ".join(f"{a} with {b} ({v:.2f} mm^3)" for a, b, v in hits))
        return False
    print("keycaps clear")
    return True


def save(shape, path):
    from OCP.BinTools import BinTools

    BinTools.Write_s(shape.wrapped, str(path))


def load(path):
    from build123d import Solid
    from OCP.BinTools import BinTools
    from OCP.TopoDS import TopoDS_Shape

    shape = TopoDS_Shape()
    BinTools.Read_s(shape, str(path))
    return Solid(shape)


def setup(args):
    from . import chassis as C
    from . import layout as L

    C.VERBOSE = args.verbose
    set_params(args.set)
    L.reset()


def plate_process(args, out, halves, parts, do_check, body_file, pipe):
    """The second process: the plinth, the check and, given the body, the assembly."""
    setup(args)
    from . import chassis as C

    ok = check() if do_check else True
    plate = C.bottom_plate()
    if "plate" in parts:
        for half in halves:
            write(for_half(plate, half), out / f"{half}-plate")
    if "assembly" in parts:
        pipe.recv()
        write(assembly(load(body_file), plate), out / "right-assembly", stl=False)
    pipe.send(ok)


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
    parts = args.part or list(PARTS)
    halves = ("right", "left") if args.half == "both" else (args.half,)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    t = time.time()

    # Start the plinth's process before the heavy imports, so both load OpenCascade at once.
    want_body = bool({"body", "assembly"} & set(parts)) and not args.check
    want_plate = bool({"plate", "assembly"} & set(parts)) and not args.check
    child = pipe = body_file = None
    if want_body and want_plate:
        pipe, far = multiprocessing.get_context("spawn").Pipe()
        body_file = Path(tempfile.mkdtemp()) / "body.brep"
        child = multiprocessing.get_context("spawn").Process(
            target=plate_process, args=(args, out, halves, parts, not args.no_check, body_file, far))
        child.start()

    setup(args)
    from . import chassis as C

    print(C.report(), flush=True)
    ok = True if child or args.no_check else check()
    if args.check:
        return 0 if ok else 1

    body = C.body() if want_body else None
    plate = C.bottom_plate() if want_plate and not child else None
    if child:
        if "assembly" in parts:
            save(body, body_file)
            pipe.send(True)
    if "body" in parts:
        for half in halves:
            write(for_half(body, half), out / f"{half}-body")
    if plate is not None:
        if "plate" in parts:
            for half in halves:
                write(for_half(plate, half), out / f"{half}-plate")
        if "assembly" in parts:
            write(assembly(body, plate), out / "right-assembly", stl=False)
    if child:
        ok = pipe.recv()
        child.join()
        body_file.unlink()
        body_file.parent.rmdir()
    print(f"built in {time.time() - t:.0f} s", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

"""Render the right half to PNGs for a person to look over. From the repository root:

    python3 -m lowpro.render                     # into output/lowpro/renders/
    python3 -m lowpro.render --set tent_deg=4

Builds the parts in-process (as lowpro.build does, without the checks or the
files) and writes: the assembly and the body with plinth from above, the body's
underside, the plinth's top, a close-up of the middle finger's home key from
below, sections across and along that key, and a section through the round at
the outline's front. Needs pyvista. The checks, not these, are what say the
build is right.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
BODY, PLATE = "burlywood", "peru"


def poly(solid):
    import pyvista as pv

    from .build import mesh_of

    v, t = mesh_of(solid)
    return pv.PolyData(v, np.hstack([np.full((len(t), 1), 3), t]).ravel())


def shot(out, name, solids, eye, focus, up=(0, 0, 1), zoom=1.3, parallel=False, fit=True):
    """The (solid, colour) pairs seen from eye towards focus, to <out>/<name>.png."""
    import pyvista as pv

    p = pv.Plotter(off_screen=True, window_size=(1600, 1200))
    p.set_background("white")
    for solid, colour in solids:
        p.add_mesh(poly(solid), color=colour, specular=0.25)
    p.camera_position = [tuple(eye), tuple(focus), up]
    if parallel:
        p.enable_parallel_projection()
    if fit:
        p.reset_camera()
    p.camera.zoom(zoom)
    path = out / f"{name}.png"
    p.screenshot(str(path))
    p.close()
    print(f"wrote {path}", flush=True)


def section(solids, normal, at, box=None):
    """The solids cut by the plane through `at`, keeping the side away from
    `normal` (so the cut face looks along it), each still a closed solid; within
    `box` ((x0, y0, z0), (x1, y1, z1)) when given."""
    from manifold3d import Manifold

    n = np.array(normal, float)
    kept = [(s.trim_by_plane(tuple(-n), float(-n @ at)), c) for s, c in solids]
    if box is not None:
        lo, hi = np.array(box[0], float), np.array(box[1], float)
        crop = Manifold.cube(tuple(hi - lo)).translate(tuple(lo))
        kept = [(s ^ crop, c) for s, c in kept]
    return kept


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "output" / "lowpro" / "renders"))
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE", help="override a parameter")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    from . import build as B
    from . import chassis as C
    from . import layout as L
    from .lib import origin

    B.set_params(args.set)
    L.reset()
    body, plate = C.body(), C.bottom_plate()
    pieces = [(p.solid, p.colour) for p in B.assembly(body, plate)]
    shell = [(body, BODY), (plate, PLATE)]
    box = np.array(body.bounding_box())
    c = (box[:3] + box[3:]) / 2
    key = origin(C.finger_key(2, 0).frame)
    q = C.outline()
    front = np.append(q[np.argmin(q[:, 1])], c[2])

    def away(d, at=c, r=300):
        return at + r * np.array(d) / np.linalg.norm(d)

    shot(out, "assembly", pieces, away((1, -1.4, 1.1)), c)
    shot(out, "iso", shell, away((1, -1.4, 1.1)), c)
    shot(out, "underside-body", shell[:1], away((0.25, -0.35, -1)), c, up=(0, 1, 0))
    shot(out, "plinth-top", shell[1:], away((0.2, -0.3, 1)), c, up=(0, 1, 0))
    shot(out, "pocket-closeup", shell[:1], away((0.25, -0.45, -0.8), key, 95), key, up=(0, 1, 0), zoom=1, fit=False)
    shot(out, "section-across", section(shell, (0, 1, 0), key), c + (0, 300, 0), c, parallel=True, zoom=1.4)
    shot(out, "section-along", section(shell, (1, 0, 0), key), c + (300, 0, 0), c, parallel=True, zoom=1.4)
    near = section(shell, (1, 0, 0), front, ((front[0] - 10, front[1] - 5, -1), (front[0] + 1, front[1] + 25, box[5] + 1)))
    shot(out, "section-round", near, front + (300, 10, 0), front + (0, 10, 0), parallel=True, zoom=1.1)
    return 0


if __name__ == "__main__":
    sys.exit(main())

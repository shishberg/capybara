"""Render the right half to PNGs for a person to look over. From the repository root:

    python3 -m lowpro.render                     # into output/lowpro/renders/
    python3 -m lowpro.render --set tent_deg=4

Builds the parts in-process (as lowpro.build does, without the checks or the
files) and writes: the assembly and the body with plinth from above, the
wiring (channels, sockets, diodes and the bay's parts through a see-through
body, from above and from below), the body's underside, the plinth's top, a close-up of the middle finger's home key from
below, sections across and along that key, a section through the round at
the outline's front, and with the knob, the assembly from the inner side, a section across its axis, the case see-through round it from outside and inside, and a cut through a pin. Needs pyvista. The checks, not these, are what say the
build is right.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

from .params import PRESETS

ROOT = Path(__file__).resolve().parent.parent
BODY, PLATE = "burlywood", "peru"


def poly(solid):
    import pyvista as pv

    from .build import mesh_of

    v, t = mesh_of(solid)
    return pv.PolyData(v, np.hstack([np.full((len(t), 1), 3), t]).ravel())


def shot(out, name, solids, eye, focus, up=(0, 0, 1), zoom=1.3, parallel=False, fit=True, labels=()):
    """The (solid, colour) or (solid, colour, opacity) tuples seen from eye
    towards focus, with (point, text) labels, to <out>/<name>.png."""
    import pyvista as pv

    p = pv.Plotter(off_screen=True, window_size=(1600, 1200))
    p.set_background("white")
    for solid, colour, *opacity in solids:
        p.add_mesh(poly(solid), color=colour, specular=0.25, opacity=opacity[0] if opacity else 1.0)
    if labels:
        p.add_point_labels(np.array([q for q, _ in labels]), [t for _, t in labels], font_size=22,
                           point_size=12, point_color="black", shape_opacity=0.8, always_visible=True)
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


def wiring(C, body):
    """The body see-through, the channels coloured (the shared trunks that carry
    the wires to the bay red, the keys' own column and row channels blue), the
    sockets, diodes and the bay's parts; and labels for the routes and parts."""
    from . import params as P
    from .lib import origin

    shown = [(body, BODY, 0.12)]
    for w, pts, _ in C.channels():
        colour = "crimson" if w == P.trunk_w_mm else "royalblue"
        for a, b in zip(pts[:-1], pts[1:]):
            shown.append((C.Manifold.hull_points(C.post_points(a, w) + C.post_points(b, w)), colour))
    shown += [(p.solid, p.colour) for p in C.sockets() + C.diodes() + C.electronics()]

    def mid(pts):
        return np.array(pts[len(pts) // 2])

    entry = C.bay_entry()
    bridge = C.bridge()
    labels = [(mid(C.edge_trunk(1)), "back trunk"), (mid(C.edge_trunk(-1)), "front trunk"),
              ((bridge[0] + 3 * bridge[1]) / 4, "bridge to the thumbs"), (C.ne(C.thumb("home")), "thumb trunk"),
              (C.c_tab(C.finger_key(0, 0)), "inner column trunk"), (entry, "into the bay"),
              (origin(C.mcu_frame()), "controller")]
    if P.link == "trrs":
        labels += [(origin(C.trrs_frame()), "TRRS jack"), (origin(C.reset_frame()), "reset switch")]
    if P.knob:
        labels.append((origin(C.knob_frame()), "knob"))
    else:
        labels.append((origin(C.battery_frame()), "battery"))
        if P.power_switch:
            labels.append((origin(C.power_switch_frame()), "power switch"))
    return shown, labels


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
    ap.add_argument("--out", help="where to write (default output/lowpro/renders/, or output/lowpro/<preset>/renders/)")
    ap.add_argument("--preset", choices=sorted(PRESETS), help="a named set of overrides (params.py PRESETS)")
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE", help="override a parameter")
    args = ap.parse_args(argv)
    out = Path(args.out or ROOT / "output" / "lowpro" / (args.preset or "") / "renders")
    out.mkdir(parents=True, exist_ok=True)

    from . import build as B
    from . import chassis as C
    from . import layout as L
    from .lib import origin

    B.set_params(args.set, args.preset)
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
    wired, labels = wiring(C, body)
    shot(out, "wiring-top", wired, c + (0, 0, 300), c, up=(0, 1, 0), parallel=True, zoom=1.2, labels=labels)
    shot(out, "wiring-below", wired, away((0.3, -0.6, -1)), c, up=(0, 1, 0), labels=labels)
    shot(out, "section-across", section(shell, (0, 1, 0), key), c + (0, 300, 0), c, parallel=True, zoom=1.4)
    shot(out, "section-along", section(shell, (1, 0, 0), key), c + (300, 0, 0), c, parallel=True, zoom=1.4)
    near = section(shell, (1, 0, 0), front, ((front[0] - 10, front[1] - 5, -1), (front[0] + 1, front[1] + 25, box[5] + 1)))
    shot(out, "section-round", near, front + (300, 10, 0), front + (0, 10, 0), parallel=True, zoom=1.1)
    from . import params as P
    if P.knob:
        # Across the knob's axis, with its parts: from the knob out to the well.
        k = origin(C.knob_frame())
        # Then, cropped to the knob's surroundings: the case see-through from
        # outside and from inside, and cut through a pin, seen at an angle.
        from manifold3d import Manifold
        f = C.knob_frame()
        along, across, up = f[:3, 0], f[:3, 1], f[:3, 2]
        crop = Manifold.cube((70, 70, 70), center=True).translate(tuple(k))
        parts = [(p.solid ^ crop, p.colour) for p in C.electronics()
                 if p.label.startswith(("shaft", "bearing", "magnet", "sensor", "pins"))]
        cup = [(p.solid, p.colour, 0.25) for p in C.electronics() if p.label.startswith("knob")]
        seen = [(body ^ crop, BODY, 0.2), (plate ^ crop, PLATE, 0.2)] + cup + parts

        def look(d, at=k, r=150):
            return at + r * (np.array(d) @ np.array([along, across, up])) / np.linalg.norm(d)

        shot(out, "knob-xray-out", seen, look((-1, 0.7, 0.5)), k, zoom=1.0)
        shot(out, "knob-xray-in", seen, look((1, 0.7, 0.6)), k, zoom=1.0)
        pin = k + across * P.knob_sensor_holes_mm[0] / 2
        cut = section([(body ^ crop, BODY), (plate ^ crop, PLATE)] + parts, across, pin)
        shot(out, "section-knob-pin", cut, look((-0.5, 1, 0.6), pin), pin, zoom=1.0)
    return 0


if __name__ == "__main__":
    sys.exit(main())

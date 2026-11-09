"""Shared setup for the audit probes: imports lowpro from the checkout under
audit with the preset and half the environment names, and loads the meshes
built for them into this directory.

    AUDIT_REPO    the checkout under audit (required)
    AUDIT_PRESET  the lowpro preset (required)
    AUDIT_HALF    right (default) or left

Meshes come from a fresh `lowpro.build --out build/<preset>` beside this file,
made on first use, never from the repo's output/, which can be stale.
"""
import os
import subprocess
import sys

import numpy as np

REPO = os.environ["AUDIT_REPO"]
PRESET = os.environ["AUDIT_PRESET"]
HALF = os.environ.get("AUDIT_HALF", "right")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build", PRESET)
sys.path.insert(0, REPO)

from lowpro import build as B          # noqa: E402
from lowpro import chassis as C        # noqa: E402
from lowpro import layout as L         # noqa: E402
from lowpro import params as P         # noqa: E402
from lowpro import parts as R          # noqa: E402
from lowpro import shell as S          # noqa: E402
from lowpro.lib import origin, xform, xdir  # noqa: E402

B.set_params([], PRESET)
P.half = HALF
L.reset()


def mesh_of(solid):
    import trimesh
    v, t = B.mesh_of(solid)
    return trimesh.Trimesh(v, t, process=False)


def built():
    """Builds the preset's meshes into OUT unless they are there."""
    if not all(os.path.exists(f"{OUT}/{h}-{p}.stl") for h in ("right", "left") for p in ("body", "plate")):
        subprocess.run([sys.executable, "-m", "lowpro.build", "--preset", PRESET, "--out", OUT],
                       cwd=REPO, check=True, stdout=subprocess.DEVNULL)


def stl(name):
    import trimesh
    built()
    m = trimesh.load(f"{OUT}/{HALF}-{name}.stl", force="mesh", process=False)
    m.merge_vertices(merge_tex=True, merge_norm=True)   # STL stores 3 corners per facet
    return m


def nearest_key(p):
    """The key whose origin is nearest the world point p, and the distance."""
    ks = L.keys()
    d = [np.linalg.norm(origin(k.frame) - np.asarray(p, float)) for k in ks]
    i = int(np.argmin(d))
    return ks[i].name, d[i]


def label(p):
    """A name for a world point: the nearest key, screw or part."""
    cands = [(np.linalg.norm(origin(k.frame)[:2] - p[:2]), k.name) for k in L.keys()]
    cands += [(np.linalg.norm(np.asarray(q) - p[:2]), f"screw {i + 1}") for i, q in enumerate(S.screw_points())]
    cands += [(np.linalg.norm(origin(S.part_frame(n))[:2] - p[:2]), n) for n in S.PARTS]
    d, n = min(cands)
    return f"{n} ({d:.1f} mm off in plan)"


def cast(m, origins, dirs, chunk=2000, far=np.inf):
    """Distance from each origin along its direction to the first face of m,
    inf when nothing is hit within `far`. Embree only, in chunks: trimesh's
    pure-Python caster took 20 GB on the body."""
    if type(m.ray).__module__ != "trimesh.ray.ray_pyembree":
        raise RuntimeError(f"ray caster is {type(m.ray).__module__}, not embree: install embreex")
    origins, dirs = np.asarray(origins, float), np.asarray(dirs, float)
    out = np.full(len(origins), np.inf)
    for i in range(0, len(origins), chunk):
        o, d = origins[i:i + chunk], dirs[i:i + chunk]
        loc, ray, _ = m.ray.intersects_location(o, d, multiple_hits=False)
        np.minimum.at(out, i + ray, np.linalg.norm(loc - o[ray], axis=1))
    out[out > far] = np.inf
    return out

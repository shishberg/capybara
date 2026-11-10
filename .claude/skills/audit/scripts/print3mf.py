"""The print 3MF (<half>-print.3mf) as the slicer will read it: its volumes and
their subtypes and settings, the body against the STL, its place on the bed, and
what the support volumes mark: each pocket rim's faces inside the enforcer, the
blocker's overlap with the body, and every downward face over 45 deg from
vertical sorted by what marks it and what's under it (the bed or the part),
with the unmarked faces over the part grouped by the nearest key.

    run_bounded.sh right print3mf.py
"""
import os
import re
import zipfile
from collections import defaultdict

import numpy as np
import trimesh

import common as A
from case.lib import rinv, xform

path = os.path.join(A.OUT, f"{A.HALF}-print.3mf")
z = zipfile.ZipFile(path)
root = z.read("3D/3dmodel.model").decode()
objs = z.read("3D/Objects/object_1.model").decode()
cfg = z.read("Metadata/model_settings.config").decode()

item = re.search(r'<item [^>]*transform="([^"]+)"', root).group(1).split()
shift = np.array(list(map(float, item[9:12])))
comps = re.findall(r'<component [^>]*transform="([^"]+)"', root)
assert all(c.split() == "1 0 0 0 1 0 0 0 1 0 0 0".split() for c in comps), comps
parts = re.findall(r'<part id="(\d+)" subtype="([^"]+)">\s*<metadata key="name" value="([^"]+)"', cfg)
settings = dict(re.findall(r'<metadata key="([^"]+)" value="([^"]*)"/>', cfg.split("<part")[0]))
meshes = {}
for oid, body in re.findall(r'<object id="(\d+)"[^>]*>(.*?)</object>', objs, re.S):
    v = np.array(re.findall(r'<vertex x="([-\d.e]+)" y="([-\d.e]+)" z="([-\d.e]+)"/>', body), float)
    t = np.array(re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"/>', body), int)
    meshes[oid] = trimesh.Trimesh(v, t, process=False)

print(f"== {os.path.basename(path)}: object settings {settings}")
print(f"   build item translation {shift.round(2).tolist()}; bed {A.P.print_bed_mm} mm")
seam = A.S.seam()
vols = {}
for pid, kind, name in parts:
    m = meshes[pid]
    vols[kind] = m
    b = m.bounds
    print(f"   {kind:17s} {name!r}: {len(m.faces)} faces, volume {m.volume:.1f} mm^3, watertight {m.is_watertight}, "
          f"bounds x {b[0,0]:.1f}..{b[1,0]:.1f} y {b[0,1]:.1f}..{b[1,1]:.1f} z {b[0,2]:.2f}..{b[1,2]:.2f}")
body = vols["normal_part"]
on_bed = body.bounds + shift
print(f"   body on the bed: z {on_bed[0, 2]:.3f}..{on_bed[1, 2]:.2f}; x {on_bed[0, 0]:.1f}..{on_bed[1, 0]:.1f}, y {on_bed[0, 1]:.1f}..{on_bed[1, 1]:.1f} "
      f"(inside 0..{A.P.print_bed_mm}: {bool((on_bed[0, :2] >= 0).all() and (on_bed[1, :2] <= A.P.print_bed_mm).all())})")
stl = A.stl("body")
print(f"   the STL's body: volume {stl.volume:.1f} mm^3, z {stl.bounds[0, 2]:.2f} (seam {seam:.2f}); "
      f"3MF body bounds - (STL bounds - seam): {np.abs(body.bounds - (stl.bounds - [0, 0, seam])).max():.4f} mm")

# Work in world axes: the object's coordinates plus the seam.
up = np.array([0, 0, seam])
enf, blk = vols["support_enforcer"], vols["support_blocker"]
fc = body.triangles_center + up
fn = body.face_normals
fa = body.area_faces
in_enf = enf.contains(fc - up - fn * 0.01)
in_blk = blk.contains(fc - up - fn * 0.01)

print("\n== each pocket's rim (the body's faces facing down out of the pocket's bottom, round the tile's room): share inside the enforcer")
w, rim = A.S.pocket_span()
side, top, _ = A.R.tile_room_box()
rows = []
for k in A.L.keys():
    q = np.c_[fc, np.ones(len(fc))] @ rinv(k.frame).T
    nk = fn @ k.frame[:3, :3]
    sel = (np.abs(q[:, 2] - rim) < 0.05) & (np.maximum(np.abs(q[:, 0]), np.abs(q[:, 1])) < w / 2 + 0.05) & (nk[:, 2] < -0.9)
    a = fa[sel].sum()
    rows.append((k.name, a, fa[sel & in_enf].sum() / a if a else np.nan, fa[sel & in_blk].sum()))
for name, a, share, bl in rows:
    print(f"   {name:22s} rim {a:6.1f} mm^2, {share * 100:5.1f}% in the enforcer, {bl:.1f} mm^2 in the blocker")

print("\n== the blocker against the body")
from manifold3d import Manifold, Mesh  # noqa: E402


def mf(m):
    return Manifold(Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))


bm, km, em = mf(body), mf(blk), mf(enf)
print(f"   blocker ^ body {(bm ^ km).volume():.1f} mm^3 (the pegs and the 0.4 reach into the ceiling); enforcer ^ blocker {(em ^ km).volume():.3f} mm^3")
print(f"   enforcer ^ body {(bm ^ em).volume():.1f} mm^3 of {em.volume():.1f}")

print("\n== downward faces steeper than 45 deg from vertical (mm^2), by what marks them and what is under them")
down = fn[:, 2] < -np.cos(np.radians(45))
down &= fc[:, 2] > seam + 0.05
under = A.cast(stl, fc[down] - [0, 0, 0.02], np.tile([0, 0, -1.0], (down.sum(), 1)), far=200)
over_part = np.zeros(len(fc), bool)
over_part[np.flatnonzero(down)] = np.isfinite(under) & (fc[down][:, 2] - 0.02 - under > seam + 0.05)
for label, m_ in (("in the enforcer", in_enf), ("in the blocker", in_blk), ("unmarked", ~in_enf & ~in_blk)):
    s = down & m_
    print(f"   {label:16s} {fa[s].sum():8.1f}   over the bed {fa[s & ~over_part].sum():8.1f}   over the part {fa[s & over_part].sum():8.1f}")
s = down & over_part & ~in_enf & ~in_blk
keys = A.L.keys()
cent = np.array([k.frame[:2, 3] for k in keys])
near = np.argmin(((fc[s][:, None, :2] - cent[None]) ** 2).sum(-1), axis=1)
by = defaultdict(float)
for i, a in zip(near, fa[s]):
    by[keys[i].name] += a
print("   unmarked over the part, by the nearest key in plan (mm^2): " + ", ".join(f"{n} {a:.0f}" for n, a in sorted(by.items(), key=lambda r: -r[1])))
# and in the key's own frame, how high above the plate those faces are
hz = defaultdict(list)
for i, (p, a) in zip(near, zip(fc[s], fa[s])):
    hz[keys[i].name].append((xform(rinv(keys[i].frame), p)[2], a))
for n, v in sorted(hz.items(), key=lambda r: -sum(a for _, a in r[1]))[:6]:
    zz, aa = np.array(v).T
    print(f"     {n:22s} key-frame z of those faces: median {np.median(zz):.2f}, area-weighted mean {np.average(zz, weights=aa):.2f} (the plate's top is 0)")

"""The capybara plinth: flatness, contact, skirt, thin features, and how the
body's wall ring lands on it. AUDIT_HALF=left for the left half."""
import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union

import common as A

P, S, C, R = A.P, A.S, A.C, A.R
plate, body = A.stl("plate"), A.stl("body")
sign = -1 if A.HALF == "left" else 1

print(f"half {A.HALF}: plinth bounds {np.round(plate.bounds, 2).tolist()}, volume {plate.volume:.0f} mm^3, watertight {plate.is_watertight}")
n = plate.face_normals
down = n[:, 2] < -0.999
zs = plate.triangles_center[down][:, 2]
print(f"bottom faces: {down.sum()} faces, z from {zs.min():.4f} to {zs.max():.4f}, area {plate.area_faces[down].sum():.0f} mm^2")
q = C.outline()
outline_area = Polygon(q).area
print(f"outline area {outline_area:.0f} mm^2; contact at the desk is {plate.area_faces[down].sum() / outline_area * 100:.1f}% of it (the skirt adds the rest)")
up = n[:, 2] > 0.999
tops = plate.triangles_center[up][:, 2]
for z in sorted(set(np.round(tops, 2))):
    a = plate.area_faces[up][np.isclose(np.round(tops, 2), z)].sum()
    if a > 2:
        print(f"  flat top at z {z}: {a:.0f} mm^2")

# thickness of every face along its inward normal
print("\nthickness by face (ray along the inward normal):")
t = trimesh.proximity.thickness(plate, plate.triangles_center, exterior=False, normals=plate.face_normals, method="ray")
t = np.asarray(t)
area = plate.area_faces
for lo, hi in ((0, 0.45), (0.45, 0.8), (0.8, 1.0), (1.0, 1.3), (1.3, 2.0)):
    m = (t >= lo) & (t < hi)
    where = plate.triangles_center[m]
    tags = {}
    for p_ in where[np.argsort(-area[m])][:6]:
        tags[A.label(np.array([sign * p_[0], p_[1], p_[2]]))] = np.round(p_, 1).tolist()
    print(f"  {lo:.2f}..{hi:.2f} mm: {area[m].sum():.1f} mm^2 of face; e.g. {tags}")

# the body's wall ring on the plinth's top
sec_b = body.section(plane_origin=[0, 0, S.seam() + 0.05], plane_normal=[0, 0, 1])
sec_p = body.section(plane_origin=[0, 0, S.seam() + 0.05], plane_normal=[0, 0, 1])
pb, _ = sec_b.to_2D()
foot = unary_union([Polygon(pg.exterior.coords, [i.coords for i in pg.interiors]) for pg in pb.polygons_full])
sec_p = plate.section(plane_origin=[0, 0, S.plinth_top() - 0.05], plane_normal=[0, 0, 1])
pp, _ = sec_p.to_2D()
top = unary_union([Polygon(pg.exterior.coords, [i.coords for i in pg.interiors]) for pg in pp.polygons_full])
print(f"\nbody footprint at the seam: {foot.area:.0f} mm^2 in {len(getattr(foot, 'geoms', [foot]))} piece(s); plinth top: {top.area:.0f} mm^2")
hang = foot.difference(top)
print(f"body footprint hanging past the plinth: {hang.area:.3f} mm^2 (should be ~0)")
pieces = sorted(getattr(foot, "geoms", [foot]), key=lambda g: -g.area)
ring = pieces[0]
widths = []
for pt in np.asarray(ring.exterior.coords)[::5]:
    d = ring.exterior.distance  # noqa
    inner = min((i.distance(trimesh.points.Point(pt)) if False else Polygon(i.coords).exterior.distance(__import__('shapely').geometry.Point(pt))) for i in ring.interiors) if ring.interiors else 99
    widths.append(inner)
print(f"wall ring width at the seam (distance from the outer edge to the nearest inner edge, sampled): min {min(widths):.2f}, median {np.median(widths):.2f} mm")
print(f"other footprint pieces at the seam (bosses' feet are at z 2.5, so none expected): {[round(g.area, 1) for g in pieces[1:]]}")

# the pads, recesses and the first layers
print(f"\npad d {2 * S.pad_r()} (plinth) in recess d {2 * S.recess_r()} (body): 0.1 mm a side nominal. A 0.2 mm first-layer flare on the body's underside "
      f"(the recess is in its first layers) narrows the recess to about {2 * S.recess_r() - 0.4:.1f}; the pad is on the plinth's top (not a first layer) so it stays {2 * S.pad_r()}.")
print(f"the body's outer wall flares out ~0.2 at its first layer, so it would overhang the plinth's top by ~0.2 all round; the plinth's own first layer flares the same under its wall: cosmetic step.")
print(f"skirt: flat {P.skirt_h_mm} mm high, cove {P.skirt_cove_mm} mm up to {P.skirt_h_mm + P.skirt_cove_mm} (plinth top {S.plinth_top()}); skirt radius {P.skirt_radius_mm}")
# cradle walls
print(f"cradle walls: Pro Micro guides {R.mcu()['cradle']['wall_mm']} mm, jack walls {R.mcu()['cradle']['jack_walls']} mm, reset stop {P.reset_stop_mm} (wide, deep); pads {S.screw_seat_z() - S.plinth_top():.1f} mm tall")
for s_ in S.cradles():
    b = s_.bounding_box()
    print(f"  cradle piece bounds x {b[0]:.1f}..{b[3]:.1f} y {b[1]:.1f}..{b[4]:.1f} z {b[2]:.2f}..{b[5]:.2f}")

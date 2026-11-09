"""Mesh validity of the built capybara STLs: watertight, winding, volume,
bodies, degenerate faces, edge lengths, and Manifold's own status.
Run: AUDIT_HALF=right|left python mesh_validity.py
"""
import numpy as np
import trimesh

import common as A

for name in ("body", "plate"):
    m = A.stl(name)
    print(f"== {A.HALF} {name}: {len(m.faces)} faces, {len(m.vertices)} vertices")
    print(f"  watertight {m.is_watertight}  winding consistent {m.is_winding_consistent}  is_volume {m.is_volume}")
    print(f"  volume {m.volume:.1f} mm^3, bounds {m.bounds.round(2).tolist()}")
    parts = m.split(only_watertight=False)
    print(f"  bodies: {len(parts)}")
    for p in sorted(parts, key=lambda p: -abs(p.volume))[:8]:
        if len(parts) > 1:
            print(f"    body volume {p.volume:.3f} mm^3 centre {p.centroid.round(1).tolist()}")
    areas = m.area_faces
    print(f"  zero-area faces (<1e-9): {(areas < 1e-9).sum()}, faces < 1e-4 mm^2: {(areas < 1e-4).sum()}")
    e = m.edges_unique_length
    print(f"  min edge {e.min():.5f} mm, edges < 0.01 mm: {(e < 0.01).sum()}, < 0.05 mm: {(e < 0.05).sum()}")
    dup = len(m.faces) - len(trimesh.grouping.unique_rows(np.sort(m.faces, axis=1))[0])
    print(f"  duplicate faces: {dup}")
    broken = trimesh.repair.broken_faces(m)
    print(f"  broken faces (non-manifold edges): {len(broken)}")
    print(f"  euler number {m.euler_number} (genus {(2 - m.euler_number) // 2} if one body)")
    solid = A.S.body() if name == "body" else A.S.bottom_plate()
    print(f"  manifold3d status: {solid.status().name}, decompose: {len(solid.decompose())} solid(s), "
          f"volume {solid.volume():.1f} (mesh {m.volume:.1f})")

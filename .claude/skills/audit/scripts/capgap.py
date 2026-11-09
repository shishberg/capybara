"""Where each keycap comes within NEAR mm of the body, at rest or pressed: per
key, the least gap, and the body surface points within NEAR (with normals),
written to capgap.json for a mark.

    python capgap.py
"""
import json
import os
import sys

import numpy as np
import trimesh

sys.path.insert(0, os.path.dirname(__file__))
import common as A  # noqa: E402

S, C, P, B = A.S, A.C, A.P, A.B
NEAR = 0.3
body = trimesh.Trimesh(*B.mesh_of(S.body()), process=False)
prox = trimesh.proximity.ProximityQuery(body)
out = {}
for pressed in (0, P.cap_travel_mm):
    for piece in C.keycaps(pressed):
        cap = trimesh.Trimesh(*B.mesh_of(piece.solid), process=False)
        pts = cap.sample(20000, return_index=False)
        near, d, tri = prox.on_surface(pts)
        hit = d < NEAR
        if not hit.any():
            continue
        name = piece.label.removeprefix("keycap ")
        e = out.setdefault(name, {"least": 9.0, "p": [], "n": []})
        e["least"] = min(e["least"], float(d.min()))
        e["p"] += near[hit].tolist()
        e["n"] += body.face_normals[tri[hit]].tolist()
        print(f"{name:22s} {'pressed' if pressed else 'at rest':8s} least {d.min():.3f} mm, {hit.sum()} samples within {NEAR}, "
              f"around {np.round(near[hit].mean(axis=0), 1)}")
json.dump(out, open(os.path.join(os.path.dirname(__file__), "capgap.json"), "w"))

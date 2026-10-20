// PROTOTYPE ?mouth= (trrs.mouth): what holds the jack's mouth in the wall, the
// ring collar (collar(), the default) or a sturdier one. Each is in world
// coordinates, cut to the outline (the rail's outer face) in plan; the plug's
// way (plugWays) is cut through it after. Cycled by the dev editor's bar.
//   ring      the collar: an arch on the rail round the barrel, 1 mm outside the chamfer
//   buttress  a ring 2 mm outside the chamfer, flaring to a foot along the rail
//   panel     a solid wall across the bay, from the rail to above the mouth
//   bezel     a ring 1.5 mm outside the chamfer, standing proud of the wall
import type { ManifoldToplevel } from 'manifold-3d';
import type { Matrix4 } from 'three';
import { point, type Config } from '../geometry';
import { box, place } from '../manifold-util';
import { collar, mouths } from './pro-micro';

export const MOUTHS = [
  { key: 'ring', name: 'ring collar on the rail' },
  { key: 'buttress', name: 'thick ring flaring to the rail' },
  { key: 'panel', name: 'solid wall across the bay' },
  { key: 'bezel', name: 'ring standing proud of the wall' },
] as const;

/** Mirrors pro-micro.ts: the chamfer round the plug's way at the face. */
const CHAMFER = 1;

export function mouthCollar(
  wasm: ManifoldToplevel,
  cfg: Config,
  frames: Record<string, Matrix4>,
  outline: [number, number][],
  rail: number,
) {
  const style = (cfg.trrs as { mouth?: string }).mouth ?? 'ring';
  if (style === 'ring') return collar(wasm, cfg, frames, outline, rail);
  const M = wasm.Manifold;
  const j = cfg.trrs;
  const m = mouths(cfg);
  const z = m.trrs.z;
  const way = j.plug_mm[0] / 2 + j.clearance_mm;
  // In the jack's frame: from the body's face out past the outer face, and the rail's top.
  const [x0, x1] = [m.trrs.x - 10, -j.body_mm[0] / 2];
  const len = x1 - x0,
    mid = (x0 + x1) / 2;
  const top = rail - frames.trrs.elements[14];
  const ring = (r: number) => M.cylinder(len, r, r, 64).rotate([0, 90, 0]).translate([x0, 0, z]);
  // A slab across the bay, along the wall (frame y), from h0 to h1 above the frame's floor.
  const slab = (half: number, h0: number, h1: number) =>
    box(M, [len, 2 * half, h1 - h0], [mid, 0, (h0 + h1) / 2]);
  let solid;
  if (style === 'buttress') {
    const r = way + CHAMFER + 2;
    solid = M.hull([ring(r), slab(14, top - 0.5, top + 0.5)]);
  } else if (style === 'panel') {
    const r = way + CHAMFER + 2;
    solid = slab(14, top - 0.5, z + r);
  } else {
    const r = way + CHAMFER + 1.5;
    solid = M.union([ring(r), slab(r, top - 0.5, z)]);
  }
  // Cut to the outline (the rail's outer face).
  const cs = new wasm.CrossSection([outline], 'NonZero');
  const placed = place(solid, frames.trrs);
  const bb = placed.boundingBox();
  const h = bb.max[2] - bb.min[2] + 2;
  const inside = placed.intersect(cs.extrude(h).translate([0, 0, bb.min[2] - 1]));
  if (style !== 'bezel') return inside;
  // The bezel: out from the face (frame x, where the barrel's axis leaves the
  // outline) PROUD mm, down to the base's top, its own chamfer at its face.
  const f = frames.trrs;
  let xf = m.trrs.x;
  while (contains(outline, point(f, [xf - 0.05, 0, z]))) xf -= 0.05;
  const r = way + CHAMFER + 1.5;
  const lip = xf - PROUD;
  const bottom = top - RIB_SKIN_BELOW;
  const proud = M.union([
    M.cylinder(PROUD + 0.2, r, r, 64)
      .rotate([0, 90, 0])
      .translate([lip, 0, z]),
    box(M, [PROUD + 0.2, 2 * r, z - bottom], [lip + (PROUD + 0.2) / 2, 0, (z + bottom) / 2]),
  ]).subtract(
    M.cylinder(CHAMFER + 0.5, way + CHAMFER + 0.5, way, 64)
      .rotate([0, 90, 0])
      .translate([lip - 0.5, 0, z]),
  );
  return inside.add(place(proud, f));
}

/** How far the bezel stands proud of the wall, and how far below the rail's top its foot reaches (to the base's top). */
const PROUD = 3;
const RIB_SKIN_BELOW = 4;

/** Whether `p` (plan) is inside the polygon. */
function contains(poly: [number, number][], p: number[]) {
  let inside = false;
  for (let i = 0, k = poly.length - 1; i < poly.length; k = i++) {
    const [ax, ay] = poly[i],
      [bx, by] = poly[k];
    if (ay > p[1] !== by > p[1] && p[0] < ((bx - ax) * (p[1] - ay)) / (by - ay) + ax)
      inside = !inside;
  }
  return inside;
}

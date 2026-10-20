// PROTOTYPE ?mouth= (trrs.mouth): what holds the jack's mouth in the wall, the
// ring collar (collar(), the default) or a sturdier one. Each is in world
// coordinates, cut to the outline (the rail's outer face) in plan; the plug's
// way (plugWays) is cut through it after. Cycled by the dev editor's bar.
//   ring      the collar: an arch on the rail round the barrel, 1 mm outside the chamfer
//   buttress  a ring 2 mm outside the chamfer, its flanks sloping down onto the
//             back wall's upright and the wishbone's leg, the wishbone's opening kept
//   panel     a wall across the bay from the upright to the wishbone's leg, from the
//             rail to 2 mm over the chamfer, the wishbone's opening kept
//   under     the jack moved along the wall to under the first wishbone (mouthConfig),
//             which forks over its plug, and the opening between its legs filled
// The wishbone's opening is found in the frame itself (openings).
import type { CrossSection, Manifold, ManifoldToplevel } from 'manifold-3d';
import type { Matrix4 } from 'three';
import { SIZES } from '../capybara';
import type { Config } from '../geometry';
import { box, place } from '../manifold-util';
import { collar, mouths } from './pro-micro';

export const MOUTHS = [
  { key: 'ring', name: 'ring collar on the rail' },
  { key: 'buttress', name: 'thick ring sloping onto its neighbours' },
  { key: 'panel', name: 'wall across the bay to the wishbone' },
  { key: 'under', name: 'under the first wishbone, filled' },
] as const;

const style = (cfg: Config) => (cfg.trrs as { mouth?: string }).mouth ?? 'ring';

/** The config a variant builds: `under` moves the jack along the wall, under the first wishbone's fork. */
export function mouthConfig(cfg: Config) {
  if (style(cfg) === 'under') cfg.trrs.position_mm = UNDER;
  return cfg;
}
/**
 * Where `under` puts the jack: UNDER_ALONG mm on along the wall (its frame's
 * -y, toward the front) from the default's place, the middle of the first
 * wishbone's opening there.
 */
const UNDER_ALONG = 15;
const TURN = (-4.5 * Math.PI) / 180;
const UNDER: [number, number] = [
  -42.72 + Math.sin(TURN) * UNDER_ALONG,
  30.3 - Math.cos(TURN) * UNDER_ALONG,
];

/** Mirrors pro-micro.ts: the chamfer round the plug's way at the face. */
const CHAMFER = 1;

export function mouthCollar(
  wasm: ManifoldToplevel,
  cfg: Config,
  frames: Record<string, Matrix4>,
  outline: [number, number][],
  rail: number,
  frame: Manifold,
) {
  const s = style(cfg);
  if (s === 'ring') return collar(wasm, cfg, frames, outline, rail);
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
  // A slab along the wall (frame y) from y0 to y1, from h0 to h1 above the frame's floor.
  const slab = (y0: number, y1: number, h0: number, h1: number) =>
    box(M, [len, y1 - y0, h1 - h0], [mid, (y0 + y1) / 2, (h0 + h1) / 2]);
  const holes = openings(wasm, frame, frames.trrs, [x0, x1], top, z);
  // The holes as solids through the band, those containing the mouth (`at`) or
  // not, grown LAP into the limbs round them, so that neither a fill nor a cut
  // shares a face with them.
  const through = (at: boolean) =>
    holes
      .filter((h) => h.at === at)
      .map((h) => h.cs.offset(LAP, 'Round').extrude(len).translate([0, 0, x0]).rotate([0, 90, 0]));
  // Each is a fill in the wall (cut to its thickness inside the outline) and
  // a boss round the barrel, as deep as the barrel (to the jack's body).
  let fill, boss;
  const others = M.union(through(false));
  if (s === 'buttress') {
    const r = way + CHAMFER + 2;
    // Its flank on the wishbone's side runs to the wishbone's fork: just
    // inside the trunk's bay-side edge, over its opening's apex.
    const apex = holes
      .filter((h) => !h.at)
      .map((h) => h.apex)
      .sort((a, b) => Math.abs(a[0]) - Math.abs(b[0]))[0];
    const fork = apex
      ? [
          box(
            M,
            [len, 0.1, 0.1],
            [mid, apex[0] + Math.sign(-apex[0]) * (HALF_LIMB - 0.2), apex[1] + FORK_UP],
          ),
        ]
      : [];
    fill = M.hull([ring(r), slab(-REACH, REACH, top - 0.5, top + 0.5), ...fork]).subtract(others);
    boss = ring(r).subtract(others);
  } else if (s === 'panel') {
    const r = way + CHAMFER + 2;
    fill = slab(-REACH, REACH, top - 0.5, z + r).subtract(others);
    boss = M.union([ring(r), slab(-r, r, top - 0.5, z)]).subtract(others);
  } else {
    // The opening the jack's plug comes through, filled from the rail.
    const r = way + CHAMFER + 1;
    fill = M.union([...through(true), slab(-1, 1, top - 0.5, top + 0.5)]);
    boss = M.union([ring(r), slab(-r, r, top - 0.5, z)]).intersect(fill);
  }
  // Cut to the outline (the rail's outer face), the fill to the wall's thickness inside it.
  const wall = (cfg.chassis as { wall_mm?: number }).wall_mm ?? SIZES.wall;
  const cs = new wasm.CrossSection([outline], 'NonZero');
  const placedFill = place(fill, frames.trrs);
  const placedBoss = place(boss, frames.trrs);
  const bb = placedFill.add(placedBoss).boundingBox();
  const h = bb.max[2] - bb.min[2] + 2;
  const prism = (c: CrossSection) => c.extrude(h).translate([0, 0, bb.min[2] - 1]);
  return placedFill
    .intersect(prism(cs.subtract(cs.offset(-wall, 'Miter'))))
    .add(placedBoss.intersect(prism(cs)));
}

/**
 * Half a wishbone limb's width (capybara-wishbone.ts S.width), and how far
 * over its opening's apex the fork's bay-side crotch is (about a limb's width
 * at 45°).
 */
const HALF_LIMB = 1.7;
const LAP = 0.05;
const FORK_UP = 2.4;

/** How far along the wall each way (mm) the bay's fills reach: past the wishbone's leg, into its opening. */
const REACH = 14;

/**
 * The frame's openings in the wall at the jack, in the jack's frame's y-z
 * plane: the frame between x0 and x1 (the wall's depth there) and from the
 * rail's top up 30 mm, seen along x; each hole in it (the space a wishbone's
 * legs and the rail close round; the bay itself, closed above by the ribs),
 * and whether it holds the mouth (at y 0, height z). Each cs maps (u, v) to
 * the frame's (-z, y), so extruded along z and turned 90° about y it stands in
 * the frame.
 */
function openings(
  wasm: ManifoldToplevel,
  frame: Manifold,
  f: Matrix4,
  [x0, x1]: [number, number],
  top: number,
  z: number,
): { cs: CrossSection; at: boolean; apex: [number, number] }[] {
  const M = wasm.Manifold;
  const local = frame
    .transform(f.clone().invert().elements as never)
    .intersect(box(M, [x1 - x0, 60, 30.5], [(x0 + x1) / 2, 0, top - 0.5 + 15.25]));
  const seen = local.rotate([0, -90, 0]).project();
  const polys = seen.toPolygons();
  // A hole winds clockwise.
  const area = (p: [number, number][]) =>
    p.reduce(
      (a, q, i) => a + q[0] * p[(i + 1) % p.length][1] - p[(i + 1) % p.length][0] * q[1],
      0,
    ) / 2;
  const contains = (poly: [number, number][], p: number[]) => {
    let inside = false;
    for (let i = 0, k = poly.length - 1; i < poly.length; k = i++) {
      const [ax, ay] = poly[i],
        [bx, by] = poly[k];
      if (ay > p[1] !== by > p[1] && p[0] < ((bx - ax) * (p[1] - ay)) / (by - ay) + ax)
        inside = !inside;
    }
    return inside;
  };
  return (polys as [number, number][][])
    .filter((p) => area(p) < 0)
    .map((p) => ({
      cs: new wasm.CrossSection([[...p].reverse()], 'Positive'),
      at: contains(p, [-z, 0]),
      // Its highest point, as frame (y, z).
      apex: p.reduce((a, q) => (-q[0] > a[1] ? [q[1], -q[0]] : a), [0, -Infinity] as [
        number,
        number,
      ]),
    }));
}

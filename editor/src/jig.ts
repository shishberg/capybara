// The soldering jig: the chassis turned over, its tiles parts side up, each in
// the place it has under its switch, so the wires come out the lengths they
// need. Each tile lies on two ledges with posts in its corner notches, and is
// open underneath. A frame round the outside carries the lot.
import type { Manifold, ManifoldToplevel, Vec2, Vec3 } from 'manifold-3d';
import { Matrix4, Quaternion, Vector3 } from 'three';
import {
  componentFrames,
  isKey,
  point,
  tileTop,
  tileUnderside,
  type Config,
  type V3,
} from './geometry';
import { box, capsule, place } from './manifold-util';

type Factory = ManifoldToplevel['Manifold'];

export const JIG = {
  /** The gap between a post and its corner notch, and round the tile. */
  fit: 0.15,
  /** Where a ledge starts, along y from the tile's centre: past every hole's ring, on the edge pads' band. */
  ledge: 7.1,
  /** How far a bar runs on past the tile's edge. */
  bar: 1.75,
  /** How deep the bars, rails and webs are. */
  depth: 5,
  /** How far the rails stand clear of a tile's left and right edges. */
  side: 0.8,
  /** The narrowest rail, and the widest. A gap with no room for the narrowest has none. */
  strip: 1,
  wide: 3,
  /** Tiles this close along their y are joined by a web. */
  web: 10,
  /** How far over a tile's parts side, and under its switch side, is kept clear. */
  above: 8,
  below: 6,
  /** Bays in the outline of the tiles narrower than twice this are bridged by the frame. */
  close: 8,
  /** From the bed to the lowest point of any tile. */
  drop: 12,
  /** The frame: the struts' diameter, how far out their feet stand, and the rail's width and
   * height. A chord under `merge` long has no struts. */
  strut: 3,
  splay: 6,
  rail: [5, 3],
  merge: 8,
  /** How far a solid runs on past a face cut into it, so no two faces coincide. */
  overlap: 0.1,
};

/** A tile's place in the jig. */
export interface Pocket {
  name: string;
  frame: Matrix4;
}

const sizes = (cfg: Config) => ({
  half: cfg.tile.size_mm[0] / 2,
  post: cfg.tile.corner_notch_radius_mm - JIG.fit,
  top: tileTop(cfg),
  under: tileUnderside(cfg),
});

/** The corners of a rectangle round a frame's z axis, in order, at `z`. */
const rectangle = (f: Matrix4, x: number, y: number, z: number) =>
  [
    [-x, -y],
    [x, -y],
    [x, y],
    [-x, y],
  ].map(([a, b]) => point(f, [a, b, z]) as Vec3);

/**
 * The chassis turned over: a turn and no mirror, so the tiles are the real way
 * round, levelled on the keys' average normal, in the middle of the bed with
 * the lowest tile JIG.drop over it.
 */
export function turnedOver(cfg: Config) {
  const nodes = componentFrames(cfg),
    keys = Object.keys(nodes).filter(isKey),
    up = keys
      .reduce((a, k) => a.add(new Vector3().setFromMatrixColumn(nodes[k], 2)), new Vector3())
      .normalize(),
    over = new Matrix4().makeRotationY(Math.PI),
    level = new Quaternion().setFromUnitVectors(
      up.clone().transformDirection(over),
      new Vector3(0, 0, -1),
    ),
    turn = new Matrix4().makeRotationFromQuaternion(level).multiply(over),
    { half, top } = sizes(cfg),
    corners = keys.flatMap((k) => rectangle(turn.clone().multiply(nodes[k]), half, half, top)),
    mid = (i: number) =>
      (Math.min(...corners.map((c) => c[i])) + Math.max(...corners.map((c) => c[i]))) / 2;
  turn.premultiply(
    new Matrix4().makeTranslation(
      -mid(0),
      -mid(1),
      JIG.drop - Math.min(...corners.map((c) => c[2])),
    ),
  );
  return {
    turn,
    pockets: keys.map((name): Pocket => ({ name, frame: turn.clone().multiply(nodes[name]) })),
  };
}

/** A tile's four sides. */
const SIDES = [
  [1, 0],
  [-1, 0],
  [0, 1],
  [0, -1],
] as const;

/** What is beside a tile on one side: the nearest other tile, and the gap to it. */
interface Room {
  gap: number;
  who?: Pocket;
}

/** What is beside each tile on each of SIDES, measured in the tile's frame. */
function roomsBeside(cfg: Config, pockets: Pocket[]) {
  const { half, top } = sizes(cfg),
    grid = Array.from({ length: 4 * half + 1 }, (_, i) => i / 2 - half);
  return new Map(
    pockets.map((p) => {
      const rooms: Room[] = SIDES.map(() => ({ gap: Infinity })),
        into = p.frame.clone().invert();
      for (const who of pockets.filter((q) => q !== p)) {
        const to = into.clone().multiply(who.frame);
        for (const i of grid)
          for (const j of grid) {
            const v = new Vector3(i, j, top).applyMatrix4(to);
            SIDES.forEach(([sx, sy], k) => {
              const gap = sx * v.x + sy * v.y - half,
                across = Math.abs(sx ? v.y : v.x);
              if (gap > -half && across <= half && gap < rooms[k].gap) rooms[k] = { gap, who };
            });
          }
      }
      return [p, rooms] as const;
    }),
  );
}

/** A bar's box in its tile's frame, at +y for `sign` 1: its ledge, and on past the tile's edge. */
function barBox(cfg: Config, sign: number) {
  const { half, post, top } = sizes(cfg),
    z = [top - JIG.overlap, top + JIG.depth],
    y = [JIG.ledge, half + JIG.bar],
    x = half + post;
  return {
    size: [2 * x, y[1] - y[0], z[1] - z[0]] as Vec3,
    centre: [0, (sign * (y[0] + y[1])) / 2, (z[0] + z[1]) / 2] as Vec3,
  };
}

const bars = (M: Factory, cfg: Config, p: Pocket) =>
  M.union(
    [1, -1].map((sign) => {
      const b = barBox(cfg, sign);
      return place(box(M, b.size, b.centre), p.frame);
    }),
  );

/** A bar's corners in the jig. */
function barCorners(cfg: Config, p: Pocket, sign: number) {
  const { size, centre } = barBox(cfg, sign);
  return [-1, 1].flatMap((sz) =>
    [
      [1, 1],
      [1, -1],
      [-1, -1],
      [-1, 1],
    ].map(
      ([sx, sy]) =>
        point(p.frame, [
          centre[0] + (sx * size[0]) / 2,
          centre[1] + (sy * size[1]) / 2,
          centre[2] + (sz * size[2]) / 2,
        ]) as Vec3,
    ),
  );
}

/** The rails at a tile's left and right, from bar to bar, where there is room: the two tiles
 * either side of a gap fill the same space, so their rails are one stringer along it. */
function rails(M: Factory, cfg: Config, p: Pocket, rooms: Room[]) {
  const { half, top } = sizes(cfg);
  return [0, 1].flatMap((k) => {
    const w = Math.min(rooms[k].gap - 2 * JIG.side, JIG.wide);
    if (w < JIG.strip) return [];
    const x = SIDES[k][0] * (half + JIG.side + w / 2);
    return [
      place(box(M, [w, 2 * (half + JIG.bar), JIG.depth], [x, 0, top + JIG.depth / 2]), p.frame),
    ];
  });
}

/** A web from each of a tile's bars to the nearest bar of the tile next to it along y. */
function webs(M: Factory, cfg: Config, p: Pocket, rooms: Room[]) {
  const centre = (ps: Vec3[]) =>
    ps.reduce((a, c) => a.add(new Vector3(...c)), new Vector3()).divideScalar(ps.length);
  return [2, 3].flatMap((k) => {
    const { gap, who } = rooms[k];
    if (!who || gap > JIG.web) return [];
    const mine = barCorners(cfg, p, SIDES[k][1]),
      theirs = [1, -1]
        .map((sign) => barCorners(cfg, who, sign))
        .sort((a, b) => centre(a).distanceTo(centre(mine)) - centre(b).distanceTo(centre(mine)))[0];
    return [M.hull([...mine, ...theirs])];
  });
}

/** The way under a tile, square to it: between its ledges and up to its rails. */
function under(M: Factory, cfg: Config, p: Pocket) {
  const { half, top } = sizes(cfg),
    x = half + JIG.side - JIG.overlap,
    y = JIG.ledge - JIG.overlap,
    h = JIG.below + 1;
  return place(box(M, [2 * x, 2 * y, h], [0, 0, top - 1 + h / 2]), p.frame);
}

/** The tile and the space over it. */
function room(M: Factory, cfg: Config, p: Pocket) {
  const { half, top, under: parts } = sizes(cfg),
    h = top - parts + JIG.above,
    w = 2 * (half + JIG.fit);
  return place(box(M, [w, w, h], [0, 0, top - h / 2]), p.frame);
}

/** The posts in a tile's corner notches, from the bars up to its parts side. */
function posts(M: Factory, cfg: Config, p: Pocket) {
  const { half, post, top, under: parts } = sizes(cfg),
    h = top - parts + JIG.overlap;
  return place(
    M.union(
      rectangle(new Matrix4(), half, half, parts).map((c) =>
        M.cylinder(h, post, post, 48).translate(c),
      ),
    ),
    p.frame,
  );
}

/**
 * The frame's ring: the outer edge of the tiles in plan, with narrow bays
 * bridged, so no chord crosses a tile. Each corner is at the lowest of the
 * planes of the tiles near it: the least of some planes is concave, so a
 * straight chord between two corners stays under them all.
 */
function ring(wasm: ManifoldToplevel, cfg: Config, pockets: Pocket[]): V3[] {
  const { half, top } = sizes(cfg),
    r = JIG.strut / 2,
    x = half + JIG.side + r,
    y = half + JIG.bar - r,
    z = top + JIG.depth / 2,
    plan = wasm.CrossSection.union(
      pockets.map(
        (p) =>
          new wasm.CrossSection(
            [rectangle(p.frame, x, y, z).map((c) => [c[0], c[1]] as Vec2)],
            'NonZero',
          ),
      ),
    )
      .offset(JIG.close, 'Miter', 4)
      .offset(-JIG.close, 'Miter', 4)
      .simplify(0.2),
    area = (c: Vec2[]) =>
      Math.abs(
        c.reduce((s, a, i) => {
          const b = c[(i + 1) % c.length];
          return s + a[0] * b[1] - b[0] * a[1];
        }, 0),
      ),
    outer = plan.toPolygons().sort((a, b) => area(b) - area(a))[0];
  return outer.map(([px, py]) => {
    const on = pockets.map((p) => {
      const n = new Vector3().setFromMatrixColumn(p.frame, 2),
        c = new Vector3(...point(p.frame, [0, 0, z])),
        at = new Vector3(px, py, c.z - (n.x * (px - c.x) + n.y * (py - c.y)) / n.z),
        l = at.clone().applyMatrix4(p.frame.clone().invert());
      return { at, off: Math.max(Math.abs(l.x) - x, Math.abs(l.y) - y) };
    });
    return on
      .filter((o) => o.off <= JIG.close)
      .reduce((a, b) => (b.at.z < a.at.z ? b : a))
      .at.toArray() as V3;
  });
}

/** The frame: a chord round the ring, from each edge's ends two struts to a foot out from its
 * middle, and a rail on the bed through the feet. */
function perimeter(wasm: ManifoldToplevel, nodes: V3[]) {
  const M = wasm.Manifold,
    r = JIG.strut / 2,
    [width, height] = JIG.rail,
    wound = Math.sign(
      nodes.reduce((s, a, i) => {
        const b = nodes[(i + 1) % nodes.length];
        return s + a[0] * b[1] - b[0] * a[1];
      }, 0),
    ),
    feet: V3[] = [],
    members = nodes.flatMap((a, i) => {
      const b = nodes[(i + 1) % nodes.length],
        d = [b[0] - a[0], b[1] - a[1]],
        l = Math.hypot(d[0], d[1]),
        chord = capsule(M, a, b, r, 12);
      if (l < JIG.merge) return [chord];
      const foot: V3 = [
        (a[0] + b[0]) / 2 + (wound * d[1] * JIG.splay) / l,
        (a[1] + b[1]) / 2 - (wound * d[0] * JIG.splay) / l,
        r,
      ];
      feet.push(foot);
      return [chord, capsule(M, a, foot, r, 12), capsule(M, b, foot, r, 12)];
    }),
    line = new wasm.CrossSection([feet.map((f) => [f[0], f[1]] as Vec2)], 'NonZero'),
    rail = line
      .offset(width / 2, 'Round', 2, 48)
      .subtract(line.offset(-width / 2, 'Round', 2, 48))
      .extrude(height);
  return M.union([rail, ...members]).trimByPlane([0, 0, 1], 0);
}

/** The jig for these tiles. The frame stands outside their rooms, but can dip under a steep tile. */
export function buildJig(wasm: ManifoldToplevel, cfg: Config, pockets: Pocket[]) {
  const M = wasm.Manifold,
    beside = roomsBeside(cfg, pockets);
  return M.union(
    pockets.flatMap((p) => [
      bars(M, cfg, p),
      ...rails(M, cfg, p, beside.get(p)!),
      ...webs(M, cfg, p, beside.get(p)!),
    ]),
  )
    .subtract(M.union(pockets.map((p) => room(M, cfg, p))))
    .add(perimeter(wasm, ring(wasm, cfg, pockets)))
    .subtract(M.union(pockets.map((p) => under(M, cfg, p))))
    .add(M.union(pockets.map((p) => posts(M, cfg, p))));
}

/** The jig's faults, in words. */
export function jigFaults(wasm: ManifoldToplevel, cfg: Config, jig: Manifold, pockets: Pocket[]) {
  const M = wasm.Manifold,
    { half, top, under: parts } = sizes(cfg),
    tiny = 1e-3,
    faults: string[] = [],
    inJig = (part: Manifold) => jig.intersect(part).volume(),
    // A sealed void between solids comes back as a piece of negative volume.
    pieces = jig.decompose().filter((x) => x.volume() > 0);
  if (pieces.length !== 1)
    faults.push(
      `The jig is ${pieces.length} pieces: ${pieces.map((x) => x.volume().toFixed(1)).join(', ')} mm3.`,
    );
  const radius = cfg.tile.pads.ring_mm / 2,
    notch = cfg.tile.corner_notch_radius_mm,
    h = top - parts + JIG.above,
    notches = M.union(
      rectangle(new Matrix4(), half, half, top - h / 2).map((c) =>
        M.cylinder(h + 1, notch, notch, 48, true).translate(c),
      ),
    ),
    tile = box(M, [2 * half, 2 * half, h], [0, 0, top - h / 2]).subtract(notches);
  for (const p of pockets) {
    if (inJig(place(tile, p.frame)) > tiny) faults.push(`${p.name}: the jig is in the tile's way.`);
    for (const c of cfg.tile.pads.list.filter((x) => x.hole)) {
      const column = M.cylinder(JIG.below + h, radius, radius, 24).translate([
        c.at_mm[0],
        c.at_mm[1],
        top - h,
      ]);
      if (inJig(place(column, p.frame)) > tiny)
        faults.push(`${p.name}: the jig is in line with its ${c.name} hole.`);
    }
    for (const sign of [1, -1]) {
      const slab = 0.02,
        ledge = place(
          box(
            M,
            [2 * (half - notch), half - JIG.ledge, slab],
            [0, (sign * (half + JIG.ledge)) / 2, top + slab / 2],
          ),
          p.frame,
        );
      if (inJig(ledge) < 0.98 * ledge.volume())
        faults.push(`${p.name}: the ledge at y ${sign * half} is not whole.`);
    }
  }
  return faults;
}

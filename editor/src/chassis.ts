// Chassis: the open Capybara frame (capybara.ts) on a flat base plate,
// built from the key poses. Under each plate a sleeve fills down round the
// switch body to just over the tile (seats.ts seatSwitches); the tile hangs
// from its switch, the hotswap socket's grip on the pins holding it up to the
// sleeve.
//
// Terms:
//  tile         the small bought PCB under each switch (hotswap socket, LED, diode);
//  tile pocket  the space under a plate kept clear for the tile and its parts;
//  plate        the square a switch clips into, plate_thickness_mm thick and
//               plate_margin_mm past the switch seat on each side, or further if
//               needed to cover the tile and its clearance;
//  sleeve       the plate filled down round the switch body over the tile's
//               footprint, to just over the tile's top (seats.ts);
//  rib          a run of keys along one key axis: each finger column, and each
//               thumb row (capybara.ts).
//
// Coordinates: "key coordinates" are a key's own frame, with the origin at the
// plate top's centre, x and y across the plate and z along its normal (up is
// positive). A "half-width" is a distance from the key's centre along its x or y
// axis. "Plan" means the world XY plane.
import type { Manifold, ManifoldToplevel, Vec3 } from 'manifold-3d';
import { Matrix4 } from 'three';
import { keycapEnvelope, isKey, tileTop, type Config } from './geometry';
import { seatSettings } from './seats';
import { keycapSolid, place, slab } from './manifold-util';
import { capybara, SIZES as RIB } from './capybara';
import { collar, cradles, plugWays, resetWay } from './wiring/pro-micro';

export interface ChassisResult {
  /** The frame, with the plates. */
  body: Manifold;
  /** The bottom section: the base plate, with the Pro Micro's, the jack's and the reset switch's cradles. */
  base: Manifold;
  /** For each key, the chassis its keycap's room (and the switch rim's) had to remove. */
  roomCuts: { name: string; cut: Manifold }[];
  /** Where the base screws go, in plan (screwSpots, moved clear of the tiles). */
  screws: [number, number][];
}

/**
 * Construction sizes that are not in the config, in mm. Distances are in key
 * coordinates unless noted.
 */
export const SIZES = {
  /** The keycap's room is this much wider than the cap plus its clearance, in total. */
  keycapRoomExtra: 0.2,
  /** The keycap room's height above the cap's lowest point. */
  keycapRoomHeight: 60,
  /** The plugs' ways reach this far out from their mouths. */
  notchLength: 40,
  /**
   * The Capybara's base screws (screwSpots): one at each corner of the outline
   * turning out by at least screwCorner degrees, sharpest first, skipping any
   * within screwApart (along the outline) of one already taken; then any run
   * between two longer than screwGap is split evenly so none is.
   */
  screwCorner: 45,
  screwApart: 40,
  screwGap: 80,
  /**
   * Each screw is an M2×4 pan-head machine screw up through the base plate
   * into an M2×3 heat-set insert, pressed up from below into a boss on the
   * rail's inside, screwBoss across and as high as the rail, its centre
   * screwInset in from the outline at least (so its insert's hole keeps that
   * less half the hole to the rail's outer face, and the boss stays just
   * inside the outline rather than being trimmed flush with it, which leaves
   * slivers). The plate's hole is screwClear across, counterbored screwHead
   * across and screwHeadDepth deep at its underside so the head sits flush.
   * Over the head the plate stands up in a pad, screwPad across and padHeight
   * high, into a socket in the boss padGap wider all round, so the head
   * clamps padHeight more than the plate's skin less the counterbore. The
   * insert's hole is insertHole across, from the pad's top through the boss.
   * A spot whose boss would come within screwClearance of a tile is slid
   * along the outline, screwSlide at a time, until it doesn't.
   */
  screwBoss: 6,
  screwInset: 3.1,
  insertHole: 3.2,
  screwClear: 2.3,
  screwHead: 4.4,
  screwHeadDepth: 1.6,
  screwPad: 4.8,
  padHeight: 0.8,
  padGap: 0.15,
  screwClearance: 0.5,
  screwSlide: 0.5,
} as const;

/**
 * Room above each plate: the switch hole, the switch housing's rim up to the
 * keycap's lowest point, and the keycap with its clearance above that (a box,
 * the cap's base wide, well above it). cutters removes it; roomCuts is what it
 * removes from where the rim and the keycap go (tapered as measured, from
 * pressed to rest, with its clearance), for the checks: chassis that stands
 * where a keycap goes. (The box's corners above the cap's taper are not.)
 */
function keycapRooms(
  M: ManifoldToplevel['Manifold'],
  cfg: Config,
  frames: Record<string, Matrix4>,
  keyNames: string[],
  uncarved: Manifold,
) {
  const sw = cfg.switch;
  const seat = seatSettings(cfg).outer;
  const capLowest = Math.max(0, sw.keycap_bottom_above_plate_mm - sw.travel_mm);
  const roomCuts: { name: string; cut: Manifold }[] = [];
  const cutters: Manifold[] = [];
  for (const n of keyNames) {
    const env = keycapEnvelope(cfg, n, { clampFloor: true });
    const room = place(
      M.cube(
        [
          env.base[0] + SIZES.keycapRoomExtra,
          env.base[1] + SIZES.keycapRoomExtra,
          SIZES.keycapRoomHeight,
        ],
        true,
      ).translate([0, 0, capLowest + SIZES.keycapRoomHeight / 2]),
      frames[n],
    );
    const rim =
      capLowest > 0.1
        ? place(
            M.cube([seat[0], seat[1], capLowest], true).translate([0, 0, capLowest / 2]),
            frames[n],
          )
        : undefined;
    const capGoes = place(keycapSolid(M, env), frames[n]);
    roomCuts.push({ name: n, cut: uncarved.intersect(rim ? capGoes.add(rim) : capGoes) });
    cutters.push(rim ? room.add(rim) : room);
  }
  return { cutters, roomCuts };
}

/**
 * The chassis: the frame, standing on a base plate the
 * shape of its outline, skin_mm thick: the frame is cut off level with the
 * plate's top, so the two meet along one flat seam, the plate's edge flush
 * with the rail's outer face. Screws come up through the plate into bosses on
 * the rail's inside (screwSpots). The plate carries the Pro Micro's and the
 * jack's cradles, their plugs coming in through openings in the frame, and
 * the reset switch's, its plunger out through a skin of the back wall.
 */
export function buildChassis(
  wasm: ManifoldToplevel,
  cfg: Config,
  frames: Record<string, Matrix4>,
): ChassisResult {
  const M = wasm.Manifold;
  const CS = wasm.CrossSection;
  const keyNames = Object.keys(frames).filter(isKey);
  const built = capybara(wasm, cfg, frames);
  // The base plate: the outline the frame stands on.
  const footprint = new CS([built.outline], 'NonZero');
  const floor = cfg.chassis.skin_mm;
  const tiles = M.union(
    keyNames.map((n) =>
      place(
        M.cube(cfg.tile.size_mm as Vec3, true).translate([
          0,
          0,
          tileTop(cfg) - cfg.tile.size_mm[2] / 2,
        ]),
        frames[n],
      ),
    ),
  );
  const bossRoom = SIZES.screwBoss / 2 + SIZES.screwClearance;
  const spots = screwSpots(built.outline, (c) =>
    tiles
      .intersect(
        M.cylinder(RIB.railHeight + SIZES.screwClearance - floor, bossRoom, bossRoom, 32).translate(
          [c[0], c[1], floor],
        ),
      )
      .isEmpty(),
  );
  const column = (d: number, z0: number, z1: number, top = d) =>
    M.union(spots.map((c) => M.cylinder(z1 - z0, d / 2, top / 2, 32).translate([c[0], c[1], z0])));
  // Cut off level with the plate's top, with the screws' bosses, the sockets for the plate's pads and the inserts' holes.
  const padTop = floor + SIZES.padHeight;
  const bb = built.frame.boundingBox();
  const below = (z: number) => slab(M, bb, 1, bb.min[2] - 1, z - bb.min[2] + 1);
  const framed = built.frame
    .subtract(below(floor))
    .add(column(SIZES.screwBoss, floor, RIB.railHeight))
    .subtract(column(SIZES.screwPad + 2 * SIZES.padGap, floor - 1, padTop))
    .subtract(column(SIZES.insertHole, floor - 1, RIB.railHeight));
  const pads = column(SIZES.screwPad, floor - 0.01, padTop);
  const holes = column(SIZES.screwClear, -1, padTop + 1).add(
    column(SIZES.screwHead, -1, SIZES.screwHeadDepth),
  );
  // The plugs come in through the frame and over notches in the plate's edge.
  const ways = plugWays(wasm, cfg, frames, SIZES.notchLength, built.outline);
  const wall = (cfg.chassis as { wall_mm?: number }).wall_mm ?? RIB.wall;
  const uncarved = framed
    .add(collar(wasm, cfg, frames, built.outline, RIB.railHeight, framed, wall))
    .subtract(ways)
    .subtract(resetWay(wasm, cfg, frames, built.outline));
  // The keycap rooms are only checked: the frame is built clear of them.
  const { roomCuts } = keycapRooms(M, cfg, frames, keyNames, uncarved);
  return {
    body: uncarved,
    base: footprint
      .extrude(cfg.chassis.skin_mm)
      .add(pads)
      .add(cradles(wasm, cfg, frames))
      .subtract(ways)
      .subtract(holes),
    roomCuts,
    screws: spots,
  };
}

/**
 * Where the Capybara's base screws go, in plan, round its outline
 * (counter-clockwise): at its sharpest corners out, no two closer than
 * screwApart along it, with the long runs between split so none is longer
 * than screwGap. Each is moved in from the outline (along the corner's
 * bisector, or square to the edge) until it is screwInset from every edge;
 * one that isn't `clear` there is slid along the outline, screwSlide at a
 * time either way, to the nearest place that is.
 */
export function screwSpots(
  outline: [number, number][],
  clear: (p: [number, number]) => boolean = () => true,
): [number, number][] {
  const n = outline.length;
  const at = (i: number) => outline[((i % n) + n) % n];
  const along: number[] = [0];
  for (let i = 0; i < n; i++)
    along.push(along[i] + Math.hypot(at(i + 1)[0] - at(i)[0], at(i + 1)[1] - at(i)[1]));
  const round = along[n];
  const apart = (a: number, b: number) => {
    const d = Math.abs(a - b) % round;
    return Math.min(d, round - d);
  };
  // Each corner's turn out, in degrees.
  const turn = (i: number) => {
    const [a, p, c] = [at(i - 1), at(i), at(i + 1)];
    const t = Math.atan2(c[1] - p[1], c[0] - p[0]) - Math.atan2(p[1] - a[1], p[0] - a[0]);
    return (Math.atan2(Math.sin(t), Math.cos(t)) * 180) / Math.PI;
  };
  const kept: number[] = [];
  for (const i of [...outline.keys()]
    .filter((i) => turn(i) >= SIZES.screwCorner)
    .sort((i, j) => turn(j) - turn(i)))
    if (kept.every((s) => apart(s, along[i]) >= SIZES.screwApart)) kept.push(along[i]);
  if (!kept.length) kept.push(0);
  kept.sort((a, b) => a - b);
  const all = kept.flatMap((s, k) => {
    const run = (kept[(k + 1) % kept.length] - s + round) % round || round;
    const parts = Math.ceil(run / SIZES.screwGap);
    return [...Array(parts).keys()].map((j) => (s + (run * j) / parts) % round);
  });
  // The point on the outline `s` along it, and the way in there.
  const inward = (i: number) => {
    const [p, q] = [at(i), at(i + 1)];
    const l = Math.hypot(q[0] - p[0], q[1] - p[1]);
    return [-(q[1] - p[1]) / l, (q[0] - p[0]) / l];
  };
  const edgeGap = (x: number[]) =>
    Math.min(
      ...outline.map((p, i) => {
        const q = at(i + 1);
        const [dx, dy] = [q[0] - p[0], q[1] - p[1]];
        const t = Math.max(
          0,
          Math.min(1, ((x[0] - p[0]) * dx + (x[1] - p[1]) * dy) / (dx * dx + dy * dy)),
        );
        return Math.hypot(x[0] - p[0] - t * dx, x[1] - p[1] - t * dy);
      }),
    );
  const spotAt = (s: number) => {
    const i = Math.max(0, along.findIndex((a) => a > s + 1e-9) - 1);
    const corner = s - along[i] < 1e-9;
    const p = corner
      ? at(i)
      : at(i).map((x, k) => x + ((at(i + 1)[k] - x) * (s - along[i])) / (along[i + 1] - along[i]));
    const [u, w] = [inward(i), corner ? inward(i - 1) : inward(i)];
    const l = Math.hypot(u[0] + w[0], u[1] + w[1]);
    const d = [(u[0] + w[0]) / l, (u[1] + w[1]) / l];
    let k = 0;
    while (k < 20 && edgeGap([p[0] + d[0] * k, p[1] + d[1] * k]) < SIZES.screwInset) k += 0.05;
    return [p[0] + d[0] * k, p[1] + d[1] * k] as [number, number];
  };
  return all.map((s) => {
    for (let t = 0; t < SIZES.screwApart / 2; t += SIZES.screwSlide)
      for (const u of t ? [s + t, s - t] : [s]) {
        const p = spotAt((u + round) % round);
        if (clear(p)) return p;
      }
    return spotAt(s);
  });
}

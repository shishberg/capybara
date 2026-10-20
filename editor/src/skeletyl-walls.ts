// The Skeletyl's walls. skeletyl.ts describes each outer side of the frame
// (the first and last finger columns' and the thumb rows' sides away from the
// keys' middle) as a WallSide, plain data, and unions the walls built for it
// (the wishbones, skeletyl-wishbone.ts, which reads nothing else of
// skeletyl.ts) into the frame. The walls ask for the outline to take in their
// feet (skeletylReach): the frame is then built again with the outline's hull
// taking them in, and the walls built on that. The kit also says where the
// main ribbon runs out of the frame (WallKit.ribbon), for the walls to keep
// clear of (on a Pro Micro, the USB-C and TRRS plugs, whose cables run out the
// same way).
import type { Manifold, ManifoldToplevel } from 'manifold-3d';
import type { Config, V3 } from './geometry';
import type { Pose, Span } from './skeletyl';
import { componentFrames, controllerStyle, dot, sub } from './geometry';
import { controllerParts, landingBox } from './wiring/adapter';
import { wishbone, wishboneReach } from './skeletyl-wishbone';

/**
 * One point along an outer side, in order along the rib (all coordinates in
 * mm, world, z up, the floor at z = 0).
 */
export interface WallPoint {
  /** The rib's outer side here: its top edge and its underside edge. Over plates and webs they are the plate's top and underside at its outer edge (`under` is plate_thickness_mm below `top` along the key's normal, so not straight under it on a tilted key). On an end they are its lip's and round's outer and inner faces, and down a drop its outer and inner faces (side by side, at the same height). */
  top: V3;
  under: V3;
  /** Outward in plan (unit, z 0): across the rib here, away from the keys' middle. */
  out: V3;
  /** What the point is on: a key's plate (`key` names it), a web between two plates, or an end (lip, round, drop). */
  over: 'key' | 'web' | 'end';
  key?: string;
  /** The rail straight out from `under` along `out`, on the floor (z 0): its inner edge, centreline and outer edge (the outline). Its top is side.railHeight up. Where the side is already on the rail (a drop's landing) these are close to `under` or behind it; where `under` is on the rail's inner edge, within footInto of it (a low end's round, flush with it), the inner edge is no further out than `under`. */
  rail: { inner: V3; centre: V3; outer: V3 };
}

/** A web's outer edge as the rib's mesh has it: its points along its top and along its underside, and every lane's down its outer face (`face`, the first `top` and the last `under`). */
export interface WebEdge {
  top: V3[];
  under: V3[];
  face: V3[][];
}

/**
 * One outer side of the frame: everything a wall variant needs to build a
 * wall from the rib's outer edge down to the rail round the outline, clear of
 * the keys. The contract between skeletyl.ts and the variants.
 */
export interface WallSide {
  /** Which rib: the column's name (e.g. "inner", "pinky") or "thumb", with " #2" etc. if the run parted into several ribs. */
  name: string;
  /** Along the side, from its first end to its last: first end's landing (or round's bottom, or the plate's corner if flush) up and over its round and lip, along the plates (each split into 5 between its corners) and webs, and over the last end down to its landing. */
  points: WallPoint[];
  /** The keys under the side, in order, each with the points over its plate: from (its first plate corner) to (its far corner), inclusive. Between one key's `to` and the next's `from` is a web; before the first `from` and after the last `to` are the ends. A post between keys stands on a web, an arch spans a key. */
  keys: { name: string; from: number; to: number }[];
  /** How each end (first, last) finishes: "drop" (the end drops to the floor: the rib carried on down onto the rail, straight down or bending out in the end's own plane, onto a square foot), "hang" (a round, stopping above the floor, at its last point), or "flush" (the run parted there: the side stops at the plate's corner). A drop's points go down, near one above another, so a wall swept along the side can't follow them: it can stop at the bottom of the round, flush with the drop's outer face, as flare does. */
  ends: ['drop' | 'hang' | 'flush', 'drop' | 'hang' | 'flush'];
  /** Each web's outer edge (web i between keys[i] and keys[i + 1]): the rib mesh's own points along its top and along its underside, from keys[i]'s plate corner to keys[i + 1]'s, exactly as the mesh has them, so that a wall can start from them and share the rib's edges there; and every lane's down the outer face (`face`, the first `top` and the last `under`), so that a wall's sides can keep clear of the face's points. */
  webs: WebEdge[];
  /** An end (first, last) that carries on into another rib as a web is "flush" in `ends`, and `points` stop at its plate's corner; this is that web's side, as points are, from the corner (`points`' first or last, again) on to the plate edge it lands on. Empty for the other ends. */
  carried: [WallPoint[], WallPoint[]];
  /** Each carried end's web's outer edge, as `webs` has a web's (the rib mesh's own points), from the plate's corner on to the plate edge it lands on, as `carried` runs; undefined for the other ends. */
  carriedWebs: [WebEdge | undefined, WebEdge | undefined];
  /** The wall thickness the frame is built to (its ends and rail), mm. */
  wall: number;
  /** The rail's height, mm (it is `wall` wide, inside the outline). */
  railHeight: number;
  /** The outline (plan, counter-clockwise): the rail's outer edge. It runs round the outer sides' plates and tile pockets with no room set aside for a wall: a wall stands on the rail, or over it, under the plate's edge. */
  outline: [number, number][];
  /** Whether points stay clear (by 0.3 mm) of every key's tile and its components, switch body and keycap room (from the plate up), as the hardware and keycap checks have them, and of each switch hole's column 12 mm down (the openings check). Test a wall's faces with it (points over them, a few mm apart), not only its edges. */
  clear: (points: V3[]) => boolean;
  /** How far out in plan from `from` (at its height), along plan direction `out`, a point must be for it and every point further out to the outline to be clear (as `clear`; exact, from the boxes): 0 if all of them are, Infinity if the outline itself isn't. */
  room: (from: V3, out: V3) => number;
}

/** What a variant builds with. */
export interface WallKit {
  wasm: ManifoldToplevel;
  cfg: Config;
  /** The ribs' own construction (skeletyl.ts), for walls built as ribs are. */
  rib: RibKit;
  /** Every side the walls are built on in this build, in order (so walls on one can keep clear of another's). */
  sides: WallSide[];
  /**
   * Whether points stay clear of the main ribbon: at least RIBBON_GAP from it
   * (its width and thickness grown by that, along its whole path as the
   * editor draws it: off the adapter, over the landing and out past the
   * outline), and not under it, since a wall standing under the ribbon on the
   * rail must pass through it.
   */
  ribbon: (points: V3[]) => boolean;
  /** The top of that grown ribbon straight over p (world z), or -Infinity where it isn't over p: so a wall can stand either side of it and span it above that. */
  ribbonTop: (p: V3) => number;
}

/**
 * The ribs' construction, as skeletyl.ts has it: a rib's solid along spans
 * (laneSolid), each a stretch of it swept between two poses (poseSpan; its
 * sides the poses' sides o·s) or straight between two stations (lineSpan; a
 * pose's stations are sidesOf it), and the ends' round's radius.
 */
export interface RibKit {
  solid: (spans: Span[]) => Manifold;
  poseSpan: (a: Pose, b: Pose, o: number) => Span;
  lineSpan: (p: [[V3, V3], [V3, V3]], q: [[V3, V3], [V3, V3]]) => Span;
  sidesOf: (q: Pose, o: number) => [[V3, V3], [V3, V3]];
  /** A lane's points along a stretch, path(f) for f 0 to 1, as `solid` samples each lane: [f, point]. */
  along: (path: (f: number) => V3, straight: boolean | undefined, steps: number) => [number, V3][];
  /** `solid`'s mesh of its lanes ([g, point] each, round the cross-section: the top from side -1 to 1, down side 1, the underside back, up side -1), given its first and last stations' sides (for its ends). */
  mesh: (lanes: [number, V3][][], ends: [[[V3, V3], [V3, V3]], [[V3, V3], [V3, V3]]]) => Manifold;
  radius: number;
  /** The least radius (mm) an end's round's inner face keeps (SIZES.endInner). */
  inner: number;
  /** The faces standing on the outline that it is cut back to (the drops'), each [a, b, outward] (a and b plan, outward a plan unit vector). */
  standing: V3[][];
  /** Where the floor tie meets the rail and is filleted into it (plan polygons, the tie and tieRound and the rail's width round it); none without a tie. */
  tie: [number, number][][];
}

/**
 * What the walls ask of the outline: their feet (plan polygons, either
 * winding: each foot's outer face's bottom edge and the rail's width in from
 * it), which the outline's hull takes in before it is straightened, so that
 * a straight run passes along each (where the hull is convex there), and a
 * pocket a foot stands in isn't turned in. Asked on the outline without
 * them; the walls are then built on the outline with them, so their feet
 * must stand where they asked.
 */
export interface Reach {
  feet: [number, number][][];
}

const wallKit = (wasm: ManifoldToplevel, cfg: Config, rib: RibKit, sides: WallSide[]): WallKit => ({
  wasm,
  cfg,
  rib,
  sides,
  ...ribbonClear(cfg),
});

/** The clearance (mm) walls keep round the main ribbon (WallKit.ribbon). */
export const RIBBON_GAP = 2;

/**
 * WallKit.ribbon and ribbonTop: the ribbon's segments (controllerParts, the port
 * panel where the Skeletyl's chassis puts it: at the landing's outer end), or
 * on a Pro Micro the plugs, each a box grown by RIBBON_GAP; a point is in the ribbon's way if the box is
 * round it or anywhere straight over it, and the ribbon's top over it is the
 * highest such box's top there.
 */
function ribbonClear(cfg: Config) {
  const frames = componentFrames(cfg);
  let panel: number | undefined;
  if (controllerStyle(cfg) === 'ffc') {
    const land = landingBox(cfg);
    const e = frames.adapter.elements;
    panel = e[12] + e[0] * (land.end - land.length);
  }
  const boxes = controllerParts(cfg, frames, panel)
    .filter((p) => p.group === 'ribbon' || p.group === 'cable')
    .map((p) => {
      const m = p.matrix;
      return {
        o: [m[12], m[13], m[14]] as V3,
        axes: [0, 4, 8].map((i): V3 => [m[i], m[i + 1], m[i + 2]]),
        c: p.center,
        h: p.size.map((x) => x / 2 + RIBBON_GAP),
      };
    });
  // How far up from p the line straight up from it is in box b: [from, to] (to < from where it misses).
  const up = (p: V3, b: (typeof boxes)[number]) => {
    let [lo, hi] = [0, Infinity];
    b.axes.forEach((a, i) => {
      const [at, rate] = [dot(sub(p, b.o), a) - b.c[i], a[2]];
      if (Math.abs(rate) < 1e-12) {
        if (Math.abs(at) > b.h[i]) [lo, hi] = [Infinity, -Infinity];
        return;
      }
      const [q, r] = [(-b.h[i] - at) / rate, (b.h[i] - at) / rate];
      [lo, hi] = [Math.max(lo, Math.min(q, r)), Math.min(hi, Math.max(q, r))];
    });
    return [lo, hi];
  };
  const under = (p: V3, b: (typeof boxes)[number]) => {
    const [lo, hi] = up(p, b);
    return lo <= hi;
  };
  return {
    ribbon: (points: V3[]) => points.every((p) => boxes.every((b) => !under(p, b))),
    ribbonTop: (p: V3) =>
      Math.max(
        -Infinity,
        ...boxes.map((b) => {
          const [lo, hi] = up(p, b);
          return lo <= hi ? p[2] + hi : -Infinity;
        }),
      ),
  };
}

/** The walls for every side. Each solid reaches a little (0.2 mm or so) into the rib and the rail so the union joins them. */
export function skeletylWalls(
  wasm: ManifoldToplevel,
  cfg: Config,
  sides: () => WallSide[],
  rib: RibKit,
): Manifold[] {
  const kit = wallKit(wasm, cfg, rib, sides());
  return kit.sides.flatMap((side) => wishbone(kit, side));
}

/** What the walls ask of the outline for every side. */
export function skeletylReach(
  wasm: ManifoldToplevel,
  cfg: Config,
  sides: () => WallSide[],
  rib: RibKit,
): Reach {
  const kit = wallKit(wasm, cfg, rib, sides());
  return { feet: kit.sides.flatMap((side) => wishboneReach(kit, side).feet) };
}

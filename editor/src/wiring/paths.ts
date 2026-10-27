// A wire's route: its legs off the tiles, the joins between legs, and the
// feeds' run to the Pro Micro.
import { point, type V3 } from '../geometry';
import { WIRING, distance, type Edge, type Env, type Lane, type Pad } from './common';
import { edgeToward, ownEdge } from './edges';
import { besideHousing, overPlugs, pastPlugs, pastRows } from './pro-micro';
import type { Obstacles } from './obstacles';

const clean = (points: V3[]) => points.filter((x, i) => !i || distance(x, points[i - 1]) > 1e-6);

/** From p across at height z to q's plan position, its middle shifted `aside` in plan. */
const across = (p: V3, q: V3, z: number, aside: number): V3[] => {
  const p1: V3 = [p[0], p[1], z];
  const q1: V3 = [q[0], q[1], z];
  const dx = q1[0] - p1[0];
  const dy = q1[1] - p1[1];
  const l = Math.hypot(dx, dy);
  if (!aside || l < 1e-6) return [p1, q1];
  const o = [(-dy / l) * aside, (dx / l) * aside];
  const at = (t: number): V3 => [p1[0] + dx * t + o[0], p1[1] + dy * t + o[1], z];
  return [p1, at(1 / 3), at(2 / 3), q1];
};

/** A leg, and whether its shift took it out past its tile's pocket, into the chassis. */
interface Leg {
  points: V3[];
  stray: boolean;
}
/**
 * A route, whether a leg strayed, whether a join between two keys' legs found
 * no way past the plates, and whether it runs lower than the floor allows.
 */
interface Route {
  points: V3[];
  strayed: boolean;
  stuck: boolean;
  low: boolean;
}

/** The ways a wire can be routed in `env`, with the legs and joins they share cached. */
export function pathsIn(env: Env, { blocked, plates }: Obstacles) {
  const { cfg, frames, padZ, loomZ, floorZ, half } = env;
  const toward = (key: string, to: V3) => edgeToward(frames, key, to);

  /**
   * A pad's way off its tile, in the tile's frame: just under the tile,
   * `aside` along the edge it heads for (axis, sign), down to `depth`, then
   * straight out to that edge. `keep` is the wire's radius: a shift further
   * out than the pocket's edge less that strays.
   */
  const makeLeg = (p: Pad, [axis, sign]: Edge, depth: number, aside: number, keep: number): Leg => {
    // Shift aside just under the tile first, so the wire's way down is clear
    // of the pad's line, where other wires run past.
    const hop = Math.min(depth, WIRING.hopDepth);
    const start: V3 = [p.xy[0], p.xy[1], padZ - hop];
    const shifted: V3 = [...start];
    shifted[1 - axis] += aside;
    const stray = Math.abs(shifted[1 - axis]) > half[1 - axis] - keep;
    const down: V3 = [shifted[0], shifted[1], padZ - depth];
    const out: V3 = [...down];
    out[axis] = sign * half[axis];
    // A shift in from the pad's own edge, toward the tile's parts, waits
    // until the wire is below them.
    const own = ownEdge(p, half);
    const inward = own[0] === 1 - axis && aside * own[1] < 0;
    const turn: V3 = inward ? [start[0], start[1], padZ - depth] : shifted;
    const points = [p.at, ...[start, turn, down, out].map((x) => point(frames[p.key], x))];
    return { points, stray };
  };
  // Many lanes share a leg: each is made once, so routes share its points
  // (and what is known about the segments between them). Callers copy before
  // changing one.
  const legs = new Map<Pad, Map<string, Leg>>();
  const leg = (p: Pad, edge: Edge, depth: number, aside = 0, keep = 0): Leg => {
    let mine = legs.get(p);
    if (!mine) legs.set(p, (mine = new Map()));
    const key = `${edge[0]} ${edge[1]} ${depth} ${aside} ${keep}`;
    let made = mine.get(key);
    if (!made) mine.set(key, (made = makeLeg(p, edge, depth, aside, keep)));
    return made;
  };

  const CLEAR = 1;
  const BLOCKED = 2;
  // From a higher leg's run out to its tile's edge, the places to climb down
  // from: along the run, then stepped back toward its key's centre.
  const climbs = new Map<
    V3[],
    { runs: V3[]; tops: V3[]; ups: Uint8Array; downs: Map<number, Uint8Array> }
  >();
  const climbOf = (h: V3[], own: V3) => {
    let c = climbs.get(h);
    if (c) return c;
    const [from, to] = [h.at(-2)!, h.at(-1)!];
    const runs: V3[] = [];
    const tops: V3[] = [];
    for (let back = 0; back <= WIRING.climbBack; back += WIRING.climbBackStep)
      for (let t = 1; t >= 0; t -= WIRING.climbRunStep) {
        const run: V3 = [0, 1, 2].map((k) => from[k] + (to[k] - from[k]) * t) as V3;
        const d = Math.hypot(own[0] - run[0], own[1] - run[1]) || 1;
        runs.push(run);
        tops.push([
          run[0] + ((own[0] - run[0]) / d) * back,
          run[1] + ((own[1] - run[1]) / d) * back,
          run[2],
        ]);
      }
    climbs.set(h, (c = { runs, tops, ups: new Uint8Array(runs.length), downs: new Map() }));
    return c;
  };
  /**
   * The way between two keys' legs: straight across, or where that runs into a
   * tile or plate, down from the higher one first.
   */
  const join = (p: V3[], q: V3[], ca: V3, cb: V3): { points: V3[]; stuck: boolean } => {
    const done = (points: V3[]) => ({ points, stuck: false });
    // Straight across between the legs' ends, or, where that runs into a
    // tile (a key much higher than its neighbour, beside it), straight down
    // from the higher end first, then across.
    const [pe, qe] = [p.at(-1)!, q.at(-1)!];
    const r = cfg.wiring.power_wire_mm / 2;
    const clear = (a: V3, b: V3) => !blocked(a, b, r) && !blocked(a, b, r, plates);
    const qr = [...q].reverse();
    if (clear(pe, qe)) return done(clean([...p, ...qr]));
    // Down from the higher key's leg as it heads out under its tile: from
    // the last place along its run to the edge where the way down misses the
    // lower key's tile and plate, or failing that, from a step back in under
    // the higher tile toward its centre; then across.
    const [h, l, own] = pe[2] > qe[2] ? [p, q, cb] : [q, p, ca];
    const end = l.at(-1)!;
    // The places to climb from, and which ways down from them are clear, are
    // the same for every lower leg the higher one meets: found once.
    const c = climbOf(h, own);
    let downs = c.downs.get(end[2]);
    if (!downs) c.downs.set(end[2], (downs = new Uint8Array(c.runs.length)));
    for (let i = 0; i < c.runs.length; i++) {
      const [run, top] = [c.runs[i], c.tops[i]];
      if (!c.ups[i]) c.ups[i] = clear(run, top) ? CLEAR : BLOCKED;
      if (c.ups[i] === BLOCKED) continue;
      const foot: V3 = [top[0], top[1], end[2]];
      if (!downs[i]) downs[i] = clear(top, foot) ? CLEAR : BLOCKED;
      if (downs[i] === BLOCKED) continue;
      if (clear(foot, end)) {
        const way = [...h.slice(0, -1), run, top, foot, ...[...l].reverse()];
        return done(clean(h === p ? way : way.reverse()));
      }
    }
    // Or round a corner in plan, along one key's edge and then the other's.
    const mid = (pe[2] + qe[2]) / 2;
    for (const c of [
      [pe[0], qe[1], mid],
      [qe[0], pe[1], mid],
    ] as V3[])
      if (clear(pe, c) && clear(c, qe)) return done(clean([...p, c, ...qr]));
    // Or under both ends: down from each, and across below them.
    for (let d = 1; d <= WIRING.climbUnder; d += WIRING.climbUnderStep) {
      const z = Math.max(Math.min(pe[2], qe[2]) - d, loomZ);
      const [a, b]: V3[] = [
        [pe[0], pe[1], z],
        [qe[0], qe[1], z],
      ];
      if (clear(pe, a) && clear(a, b) && clear(b, qe)) return done(clean([...p, a, b, ...qr]));
    }
    return { points: clean([...p, ...qr]), stuck: true };
  };
  // Many lanes share the same two legs, and the way between them.
  const joins = new Map<V3[], Map<V3[], { points: V3[]; stuck: boolean }>>();
  const joined = (p: V3[], q: V3[], ca: V3, cb: V3) => {
    let mine = joins.get(p);
    if (!mine) joins.set(p, (mine = new Map()));
    let j = mine.get(q);
    if (!j) mine.set(q, (j = join(p, q, ca, cb)));
    return j;
  };

  /**
   * A route for a wire of radius `keep` in `lane`. `a` is a pad, or for a
   * feed the point at its net's pin.
   */
  const routeOf = (a: Pad | V3, b: Pad, lane: Lane, keep: number): Omit<Route, 'low'> => {
    if (Array.isArray(a)) {
      const { points: path, stray: strayed } = leg(
        b,
        lane.edge ?? ownEdge(b, half),
        lane.da,
        lane.aside,
        keep,
      );
      // Out of its housing's top (a), over one face and down beside it to
      // the loom, from its inner face perhaps along between the pin rows and
      // out past their far end; or straight up, across over the housings to
      // just past them and down to the loom, or where its leg ends over them,
      // across to under the leg's end.
      const end = path.at(-1)!;
      const z = loomZ + (lane.level ?? 0) * WIRING.loomStep;
      if (lane.over !== undefined) {
        const zo = overPlugs(cfg, frames) + keep + WIRING.plugMargin + lane.over * WIRING.loomStep;
        const t = pastPlugs(cfg, frames, a, end, keep);
        const c: V3 = [a[0] + t * (end[0] - a[0]), a[1] + t * (end[1] - a[1]), zo];
        const down = t < 1 ? [...across(end, c, Math.min(z, end[2]), lane.aside), c] : [c];
        const points = clean([...path, ...down, [a[0], a[1], zo], a]);
        return { points: points.reverse(), strayed, stuck: false };
      }
      const by = besideHousing(cfg, frames, a, keep, lane.inside);
      const low: V3 = [by[0], by[1], Math.min(z, end[2])];
      const points = lane.round
        ? clean([
            ...path,
            ...across(end, pastRows(cfg, frames, low, keep), low[2], lane.aside),
            low,
            by,
            a,
          ])
        : clean([...path, ...across(end, by, low[2], lane.aside), by, a]);
      return { points: points.reverse(), strayed, stuck: false };
    }
    const ca = point(frames[b.key], [0, 0, 0]);
    const cb = point(frames[a.key], [0, 0, 0]);
    const p = leg(a, toward(a.key, ca), lane.da, lane.aside, keep);
    const q = leg(b, toward(b.key, cb), lane.db, lane.asideB ?? lane.aside, keep);
    const j = joined(p.points, q.points, ca, cb);
    return { points: j.points, strayed: p.stray || q.stray, stuck: j.stuck };
  };

  /**
   * A route for a wire of radius `keep`, as routeOf, and whether it runs too
   * low: its underside below the floor's top anywhere. Its segments are
   * straight, so its points are its lowest.
   */
  const route = (a: Pad | V3, b: Pad, lane: Lane, keep: number): Route => {
    const r = routeOf(a, b, lane, keep);
    return { ...r, low: r.points.some((p) => p[2] - keep < floorZ - 1e-9) };
  };

  // Many routes share segments (their legs), so each segment is tested once.
  const tested = new Map<number, Map<V3, Map<V3, boolean>>>();
  /** Whether a route runs into a tile or its parts, the jack, the reset switch or a Dupont housing (its drops onto its ends excepted). */
  const hitsTiles = (points: V3[], r: number) => {
    let byR = tested.get(r);
    if (!byR) tested.set(r, (byR = new Map()));
    for (let i = 2; i < points.length - 1; i++) {
      const [p, q] = [points[i - 1], points[i]];
      let from = byR.get(p);
      if (!from) byR.set(p, (from = new Map()));
      let hit = from.get(q);
      if (hit === undefined) from.set(q, (hit = blocked(p, q, r)));
      if (hit) return true;
    }
    return false;
  };
  return { route, hitsTiles };
}

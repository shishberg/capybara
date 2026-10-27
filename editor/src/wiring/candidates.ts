// Each wire's candidate routes, nearest the tiles first.
import { point, type V3 } from '../geometry';
import { WIRING, type Edge, type Env, type Lane, type Pad } from './common';
import type { Spec } from './specs';
import { edgeToward, ownEdge } from './edges';
import type { pathsIn } from './paths';
import { tubeOf } from './tubes';
import type { Option } from './negotiate';

type Paths = ReturnType<typeof pathsIn>;

export const diameterOf = (env: Env, s: Spec) =>
  ['power', 'ground'].includes(s.net.group)
    ? env.cfg.wiring.power_wire_mm
    : env.cfg.wiring.signal_wire_mm;

/**
 * The depths a wire may run at below a tile, nearest first, by what its leg
 * on that tile does: out over the pad's own edge (a hop, just under the
 * tile), along that edge's strip past other wired pads (under their drops),
 * or across the tile under its parts.
 */
const legDepths = (env: Env, p: Pad, [axis, sign]: Edge, d: number) => {
  const r = d / 2;
  const [ownAxis, ownSign] = ownEdge(p, env.half);
  // Along the strip, a wire runs a step deeper for each pad it passes under
  // on its way to the edge.
  const passes = env.wiredPads.filter((q) => {
    const [a, s] = ownEdge({ xy: q }, env.half);
    return a === ownAxis && s === ownSign && sign * (q[axis] - p.xy[axis]) > 1e-6;
  }).length;
  const from =
    axis === ownAxis
      ? sign === ownSign
        ? WIRING.hopDepth
        : env.componentDepth + r + WIRING.depthMargin
      : WIRING.stripDepth + passes * WIRING.stripStep;
  return [...Array(WIRING.depthChoices).keys()].map(
    (k) => Math.max(from, r + WIRING.depthMargin) + k * WIRING.depthStep,
  );
};

/** The edge a wire between two keys leaves the tile of its end `a` or `b` by: the one facing the other key. */
const edgeOf = (env: Env, s: Spec, end: 'a' | 'b'): Edge => {
  const [p, other] = (end === 'a' ? [s.a, s.b] : [s.b, s.a]) as [Pad, Pad];
  return edgeToward(env.frames, p.key, point(env.frames[other.key], [0, 0, 0]));
};

/** A spec's lanes, nearest the tiles first. `wide` tries every depth. */
function candidates(env: Env, s: Spec, wide: boolean) {
  const { frames, hole } = env;
  const d = diameterOf(env, s);
  const out: { lane: Lane; rank: number }[] = [];
  if (typeof s.a !== 'number') {
    const wa = legWays(env, s.a, edgeOf(env, s, 'a'), d);
    const wb = legWays(env, s.b, edgeOf(env, s, 'b'), d);
    for (const a of wa)
      for (const b of wb)
        out.push({
          lane: { da: a.depth, db: b.depth, aside: a.aside, asideB: b.aside },
          rank: a.rank + b.rank,
        });
    return out.sort((x, y) => x.rank - y.rank);
  }
  // A feed leaves by its pad's own edge or by the edge facing its hole, and
  // comes down past its housing's outer face or, next, its inner, from which
  // it may run between the pin rows and out past their end; or, last, runs
  // across over the housings.
  const depthTries = wide ? WIRING.depthChoices : WIRING.feedDepths;
  const home = ownEdge(s.b, env.half);
  const toward = edgeToward(frames, s.b.key, hole[s.a]);
  const edges = toward[0] === home[0] && toward[1] === home[1] ? [home] : [home, toward];
  const faceWays = [{ inside: false }, { inside: true }, { inside: true, round: true }];
  for (const [e, edge] of edges.entries()) {
    const depths = legDepths(env, s.b, edge, d);
    for (let i = 0; i < depthTries; i++) {
      for (const level of WIRING.loomLevels)
        for (const aside of WIRING.asides)
          for (const [k, way] of faceWays.entries())
            out.push({
              lane: { da: depths[i], db: depths[i], aside, level, edge, ...way },
              rank: i + 2 * e + k,
            });
      for (const over of WIRING.overLevels)
        for (const level of WIRING.loomLevels.slice(0, WIRING.overLoomLevels))
          for (const aside of WIRING.asides)
            out.push({
              lane: { da: depths[i], db: depths[i], aside, level, edge, over },
              rank: i + 2 * e + faceWays.length,
            });
    }
  }
  return out.sort((x, y) => x.rank - y.rank);
}

/**
 * The ways a leg between two keys may leave its tile by `edge`: each of its
 * depths with each of the edge asides, and, where the edge is not the pad's
 * own, along the rim: shifted out to its own edge just inside the pocket,
 * outside the other pads on that edge, and run along it just under the tile.
 * Last of the choices, it keeps a leg shallow where a low edge would take the
 * run under the strip below the floor.
 */
const legWays = (env: Env, p: Pad, edge: Edge, d: number) => {
  const ways: { depth: number; aside: number; rank: number }[] = legDepths(env, p, edge, d).flatMap(
    (depth, i) => WIRING.edgeAsides.map((aside, x) => ({ depth, aside, rank: i + (x ? 1 : 0) })),
  );
  const [own, sign] = ownEdge(p, env.half);
  if (own !== edge[0]) {
    const rim = sign * (env.half[own] - d / 2 - WIRING.depthMargin) - p.xy[own];
    ways.push({ depth: WIRING.hopDepth, aside: rim, rank: WIRING.rimRank });
  }
  return ways;
};

/**
 * Each wire's routes as options, without those that run into a tile (unless
 * all do), shift out past the tile's pocket or run below the floor (its
 * underside under env.floorZ). Each end stays on its own pad or hole: one
 * wire fits a tile's hole.
 */
export function optionsOf(
  env: Env,
  paths: Paths,
  specs: Spec[],
  ends: { a: Pad | V3; b: Pad }[],
  wide: boolean,
): Option[][] {
  return specs.map((s, i) => {
    const d = diameterOf(env, s);
    const all = candidates(env, s, wide).flatMap(({ lane, rank }) => {
      const { points, strayed, stuck, low } = paths.route(ends[i].a, ends[i].b, lane, d / 2);
      if (strayed || low) return [];
      return {
        tube: tubeOf(points, d),
        rank,
        blocked: stuck || paths.hitsTiles(points, d / 2),
      };
    });
    return asOptions(all);
  });
}

/** A wire's routes as its options: those that run into nothing, or if every one does, all of them, ranked after. */
export function asOptions(all: (Option & { blocked: boolean })[]): Option[] {
  const clear = all.filter((o) => !o.blocked);
  return (clear.length ? clear : all.map((o) => ({ ...o, rank: o.rank + WIRING.blockedRank })))
    .sort((x, y) => x.rank - y.rank)
    .slice(0, WIRING.optionLimit);
}

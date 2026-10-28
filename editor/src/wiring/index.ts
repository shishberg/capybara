// Hand wiring, from the key frames: where each wire runs under the tiles
// and to the Pro Micro, and the jack's and the reset switch's link wires
// (pro-micro.ts). Routing is a search that takes a moment, so the editor runs
// it in a worker of its own.
//
// Terms:
//  pad      a solder pad on a tile's underside (tile.pads);
//  hole     where a net's feeds land: the top of the Dupont housing on the
//           Pro Micro pin pro_micro.pins gives it;
//  depth    how far below its tile's underside a wire leaves a pad; it runs
//           straight from that point on one tile to that on the next;
//  chain    keys joined one to the next by a net's wires (wiring.nets[].chains);
//  feed     the wire from a chain's end to its net's pin;
//  stub     a short length of bare copper soldered into a tile's hole,
//           standing down from it (wiring.stub_mm);
//  rail     a chain that is one wire, from stub to stub, soldered to each:
//           +5 V's and GND's (wiring.nets[].rail);
//  loom     the height above the bottom section at which feeds run to the
//           Pro Micro, before each climbs beside its housing to its top.
import {
  componentFrames,
  isKey,
  tileBottom,
  tilePads,
  tileUnderside,
  type Config,
  type V3,
} from '../geometry';
import { tilePocketHalf } from '../plates';
import { padParts } from './pads';
import { asOptions, diameterOf, optionsOf } from './candidates';
import {
  distance,
  length,
  nets,
  type Env,
  type NetSummary,
  type NetSpec,
  type Pad,
  type Wire,
  type Wiring,
} from './common';
import { negotiate } from './negotiate';
import { obstaclesOf } from './obstacles';
import { pathsIn } from './paths';
import { holes, holeAlong, linkWires, pinName, proMicroParts } from './pro-micro';
import { specsOf } from './specs';
import { crossings, tubeOf } from './tubes';

export { holes, holeAlong, padParts, proMicroParts, nets, crossings };
export type { NetSpec, Pad, Wire, NetSummary, Wiring };

/** The wiring for a config: every wire's route, by negotiating them until none pass into another. */
export function wiring(cfg: Config, frames = componentFrames(cfg)): Wiring {
  const w = cfg.wiring;
  const tile = cfg.tile;
  const padZ = tileUnderside(cfg);
  const keys = Object.keys(frames).filter(isKey);
  const hole = holes(cfg, frames);
  const componentDepth = padZ - tileBottom(cfg) + tile.component_clearance_mm;
  const env: Env = {
    cfg,
    frames,
    padZ,
    loomZ: cfg.chassis.skin_mm + w.loom_height_mm,
    floorZ: cfg.chassis.skin_mm,
    half: tilePocketHalf(cfg),
    componentDepth,
    wiredPads: tilePads(cfg)
      .filter((p) => nets(cfg).some((n) => n.pads.includes(p.name)))
      .map((p) => [p.at_mm[0], p.at_mm[1]]),
    hole,
    stubRoom: Math.max(w.stub_mm[0], w.power_wire_mm) / 2,
  };
  const { pads, specs, ends, rails } = specsOf(env, keys);
  const joined = rails.flatMap((r) => r.slice(1).map((s, i): [number, number] => [r[i], s]));
  const paths = pathsIn(env, obstaclesOf(env, keys));
  // The jack's and the reset switch's link wires negotiate too, each with
  // its routes.
  const links = linkWires(cfg, frames, new Set(nets(cfg).map((n) => n.pin)));
  const linkOptions = links.map((x) =>
    asOptions(
      x.routes.map(({ points, rank }) => ({
        tube: tubeOf(points, x.diameter),
        rank,
        blocked: paths.hitsTiles(points, x.diameter / 2),
      })),
    ),
  );

  // Route with the usual choices first; if wires still meet, or some wire has
  // no route above the floor, again with every depth, and keep the better. A wire with no route above the floor even
  // then fails the routing.
  const solve = (wide: boolean) => {
    const options = optionsOf(env, paths, specs, ends, wide);
    const none = specs.filter((_, i) => !options[i].length);
    if (none.length) {
      if (!wide) return { left: Infinity, paths: [] };
      throw Error(
        `No route keeps these wires' undersides ${env.floorZ} mm above the base: ` +
          none.map((s) => `${s.net.name} ${s.from}-${s.to}`).join(', '),
      );
    }
    const { left, choice } = negotiate([...options, ...linkOptions], wide, joined);
    return {
      left,
      paths: [...options, ...linkOptions].map((list, i) => list[choice[i]].tube.points),
    };
  };
  let solved = solve(false);
  if (solved.left) {
    const again = solve(true);
    if (again.left < solved.left) solved = again;
  }

  const routed: Wire[] = specs.map((s, i) => {
    const isFeed = typeof s.a === 'number';
    return {
      net: s.net.name,
      group: s.net.group,
      from: s.from,
      to: s.to,
      points: solved.paths[i],
      diameter: diameterOf(env, s),
      length: length(solved.paths[i]) + 2 * w.end_allowance_mm + (isFeed ? w.service_loop_mm : 0),
      feed: isFeed,
    };
  });
  // Each rail's pieces, one from a stub to the next, are one wire, which
  // runs down or up its stub between the joints its pieces end at.
  const inRail = new Set(rails.flat());
  const wires: Wire[] = routed.filter((_, i) => !inRail.has(i));
  for (const r of rails.filter((r) => r.length)) {
    const parts = r.map((i) => routed[i]);
    const points: V3[] = [];
    const stubs: NonNullable<Wire['stubs']> = [{ key: parts[0].from, points: [0, 0], along: 0 }];
    for (const x of parts) {
      // A piece leaves its stub from the joint the last came to, or another.
      const same = points.length && distance(points.at(-1)!, x.points[0]) < 1e-6 ? 1 : 0;
      stubs.at(-1)!.points[1] = points.length - same;
      points.push(...x.points.slice(same));
      stubs.push({ key: x.to, points: [points.length - 1, points.length - 1], along: 0 });
    }
    for (const s of stubs) {
      const [a, b] = s.points.map((k) => length(points.slice(0, k + 1)));
      s.along = w.end_allowance_mm + (a + b) / 2;
    }
    wires.push({
      ...parts[0],
      to: parts.at(-1)!.to,
      points,
      length: length(points) + 2 * w.end_allowance_mm,
      stubs,
    });
  }
  wires.push(
    ...links.map(({ routes, ...x }, i) => {
      const points = solved.paths[specs.length + i];
      return { ...x, points, length: length(points) + 2 * w.end_allowance_mm };
    }),
  );
  const summaries: NetSummary[] = nets(cfg).map((net) => {
    const own = wires.filter((x) => x.net === net.name);
    return {
      name: net.name,
      pin: net.pin,
      label: pinName(cfg, net.pin),
      group: net.group,
      wires: own.length,
      // Both ends of a wire, but a feed's other end plugs on; on a rail, one
      // at each stub and the stub's own in its hole.
      joints: own.reduce((t, x) => t + (x.feed ? 1 : x.stubs ? 2 * x.stubs.length : 2), 0),
      length: own.reduce((t, x) => t + x.length, 0),
    };
  });
  for (const x of [
    ...cfg.trrs.wires.map((t) => ({ net: `TRRS ${t.name}`, pin: t.pin, to: t.lug })),
    ...cfg.reset.wires.map((t) => ({ net: `Reset ${t.name}`, pin: t.pin, to: `leg ${t.leg}` })),
  ]) {
    const own = wires.filter((y) => y.net === x.net);
    summaries.push({
      name: x.net,
      pin: x.pin,
      label: `${pinName(cfg, x.pin)} to ${x.to}`,
      group: 'link',
      wires: own.length,
      // Soldered at the jack or the switch; the Pro Micro end plugs on.
      joints: own.length,
      length: own.reduce((t, y) => t + y.length, 0),
    });
  }
  const netFor = (key: string, group: string) =>
    nets(cfg).find((n) => n.group === group && (n.chains ?? []).some((c) => c.includes(key)))
      ?.name ?? '';
  return {
    pads,
    wires,
    nets: summaries,
    matrix: keys.map((key) => ({ key, row: netFor(key, 'row'), column: netFor(key, 'column') })),
  };
}

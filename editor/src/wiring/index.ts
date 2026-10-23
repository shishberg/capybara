// Hand wiring, adapter and ribbons, from the key frames: where each wire runs
// under the tiles, through the wire port and to the adapter (or the Pro
// Micro, controller.style "pro_micro", which also has the jack's link wires:
// pro-micro.ts). Routing is a
// search that takes a moment, so the editor runs it in a worker of its own.
//
// Terms:
//  pad      a solder pad on a tile's underside (tile.pads);
//  hole     one of the adapter's 24 through holes; hole n carries ribbon pin n
//           (on a Pro Micro, the pin pro_micro.pins gives the net);
//  depth    how far below its tile's underside a wire leaves a pad; it runs
//           straight from that point on one tile to that on the next;
//  chain    keys joined one to the next by a net's wires (wiring.nets[].chains);
//  feed     the wire from a chain's end to its adapter hole;
//  loom     the height above the bottom section at which feeds run to the adapter;
//  wire port  where thumb wires pass from under the thumbs to under the
//           finger columns: a straight round way in front of the gap between
//           the inner and index columns' bottom keys;
//  slack loop  the arch the ribbon makes between the connector and the landing,
//           so a pull held by the ties never reaches the connector.
import {
  componentFrames,
  controllerStyle,
  isKey,
  tileBottom,
  tileUnderside,
  type Config,
} from '../geometry';
import { tilePocketHalf } from '../plates';
import { holes, holeAlong, padParts, controllerParts, landingBox } from './adapter';
import { assignPlaces, diameterOf, optionsOf } from './candidates';
import {
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
import { portGrid, wirePort } from './port';
import { linkWires, pinLabel, pinName, pinOf } from './pro-micro';
import { specsOf } from './specs';
import { crossings } from './tubes';

export { holes, holeAlong, padParts, controllerParts, landingBox, nets, crossings };
export type { NetSpec, Pad, Wire, NetSummary, Wiring };

/** The wiring for a config: every wire's route, by negotiating them until none pass into another. */
export function wiring(cfg: Config, frames = componentFrames(cfg)): Wiring {
  const w = cfg.wiring;
  const tile = cfg.tile;
  const padZ = tileUnderside(cfg);
  const keys = Object.keys(frames).filter(isKey);
  const hole = holes(cfg, frames);
  const port = wirePort(cfg, frames);
  const grid = portGrid(port, port.diameter / 2 - w.power_wire_mm / 2);
  const componentDepth = padZ - tileBottom(cfg) + tile.component_clearance_mm;
  const env: Env = {
    cfg,
    frames,
    padZ,
    loomZ: cfg.chassis.skin_mm + w.loom_height_mm,
    floorZ: cfg.chassis.skin_mm,
    half: tilePocketHalf(cfg),
    componentDepth,
    wiredPads: tile.pads.list
      .filter((p) => nets(cfg).some((n) => n.pads.includes(p.name)))
      .map((p) => [p.at_mm[0], p.at_mm[1]]),
    hole,
    port,
    grid,
  };
  const { pads, specs, ends } = specsOf(env, keys);
  const paths = pathsIn(env, obstaclesOf(env, keys));
  const placeOf = assignPlaces(env, specs, ends, paths.leg);

  // Route with the usual choices first; if wires still meet, or some wire has
  // no route above the floor, again with every place in the port and every
  // depth, and keep the better. A wire with no route above the floor even
  // then fails the routing.
  const solve = (wide: boolean) => {
    const options = optionsOf(env, paths, specs, ends, placeOf, wide);
    const none = specs.filter((_, i) => !options[i].length);
    if (none.length) {
      if (!wide) return { left: Infinity, paths: [] };
      throw Error(
        `No route keeps these wires' undersides ${env.floorZ} mm above the base: ` +
          none.map((s) => `${s.net.name} ${s.from}-${s.to}`).join(', '),
      );
    }
    const { left, choice } = negotiate(options, wide);
    return { left, paths: choice.map((k, i) => options[i][k].tube.points) };
  };
  let solved = solve(false);
  if (solved.left) {
    const again = solve(true);
    if (again.left < solved.left) solved = again;
  }

  const wires: Wire[] = specs.map((s, i) => {
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
  // On a Pro Micro, its jack's and its reset switch's link wires too.
  if (controllerStyle(cfg) === 'pro_micro') {
    const fed = new Set(nets(cfg).map((n) => pinOf(cfg, n.name)));
    wires.push(...linkWires(cfg, frames, fed));
  }
  const summaries: NetSummary[] = nets(cfg).map((net) => {
    const own = wires.filter((x) => x.net === net.name);
    return {
      name: net.name,
      pin: net.pin,
      label: pinLabel(cfg, net.name, net.pin),
      group: net.group,
      wires: own.length,
      joints: 2 * own.length,
      length: own.reduce((t, x) => t + x.length, 0),
    };
  });
  if (controllerStyle(cfg) === 'pro_micro')
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
        joints: 2 * own.length,
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

// The adapter board, its holes, the ribbon and the tile pads, as parts.
import { Matrix4, Vector3 } from 'three';
import {
  componentFrames,
  controllerStyle,
  isKey,
  point,
  tileUnderside,
  type Config,
  type V3,
} from '../geometry';
import type { Part } from '../parts';
import { WIRING, mid } from './common';
import { proMicroHoles, proMicroParts } from './pro-micro';

/**
 * Where each net's feeds land, in world coordinates on the board's top, keyed
 * by the net's `pin`: on the adapter, hole n carries ribbon pin n; on a Pro
 * Micro, a net's hole is the pin pro_micro.pins gives it.
 */
export function holes(cfg: Config, frames = componentFrames(cfg)) {
  if (controllerStyle(cfg) === 'pro_micro') return proMicroHoles(cfg, frames);
  const a = cfg.adapter;
  const [bx, , bz] = a.board_mm;
  const out: Record<number, V3> = {};
  for (let pin = 1; pin <= 24; pin++) {
    // Pins pair across the two rows, even pins on the row nearest the edge.
    const j = Math.floor((pin - 1) / 2);
    const x = bx / 2 - a.hole_rows_from_edge_mm[pin % 2 ? 1 : 0];
    out[pin] = point(frames.adapter, [x, (j - 5.5) * a.hole_pitch_mm, bz]);
  }
  return out;
}

/** A box part along a segment: x along it, y along `across`, z the cross product. */
const segmentPart = (
  name: string,
  group: string,
  a: V3,
  b: V3,
  across: V3,
  width: number,
  thickness: number,
): Part => {
  const x = new Vector3(...b).sub(new Vector3(...a));
  const len = x.length();
  x.normalize();
  const z = new Vector3().crossVectors(x, new Vector3(...across)).normalize();
  const y = new Vector3().crossVectors(z, x);
  const m = new Matrix4().makeBasis(x, y, z).setPosition(...mid(a, b));
  return {
    name,
    group,
    size: [len, width, thickness],
    center: [0, 0, 0],
    matrix: m.elements.slice(),
  };
};

/**
 * The ribbon's centre line, in the adapter's frame: out of the connector's
 * mouth, over the slack loop, down to the landing's top and straight out
 * past where it leaves the hand, x = `panel`, to outside_mm beyond it.
 */
function ribbonPath(cfg: Config, panel = defaultPanel(cfg)) {
  const a = cfg.adapter;
  const r = cfg.ribbon;
  const [bx, , bz] = a.board_mm;
  const mouthX = -bx / 2 + a.connector_inset_mm;
  const mouthZ = bz + a.connector_mm[2] / 2;
  const loopFrom = mouthX - WIRING.loopGap;
  const loopTo = loopFrom - 2 * r.loop_radius_mm;
  const onLanding = landingBox(cfg).top + r.thickness_mm / 2 + WIRING.ribbonLift;
  const points: V3[] = [[mouthX, 0, mouthZ]];
  // The loop: a half turn up and over, from loopFrom to loopTo.
  for (let i = 0; i <= WIRING.loopSteps; i++) {
    const t = (i / WIRING.loopSteps) * Math.PI;
    points.push([
      (loopFrom + loopTo) / 2 + r.loop_radius_mm * Math.cos(t),
      0,
      mouthZ + r.loop_radius_mm * Math.sin(t),
    ]);
  }
  points.push(
    [landingEnd(cfg) + WIRING.landingLead, 0, onLanding],
    [panel - r.outside_mm, 0, onLanding],
  );
  return points;
}
/** The adapter-frame x the landing must stop short of, clear of the slack loop. */
function landingEnd(cfg: Config) {
  const a = cfg.adapter;
  return (
    -a.board_mm[0] / 2 + a.connector_inset_mm - WIRING.landingGap - 2 * cfg.ribbon.loop_radius_mm
  );
}
// Until a build has placed where the ribbon leaves: as if the landing ran up to the loop.
const defaultPanel = (cfg: Config) => landingEnd(cfg) - cfg.ribbon.landing_mm[0] - WIRING.panelGap;

/**
 * The ribbon's landing, on the bottom section: its length and its width, and
 * in the adapter's frame its bottom (on the bottom section) and top (under the ribbon), and the x it must stop short of,
 * clear of the slack loop.
 */
export function landingBox(cfg: Config) {
  const a = cfg.adapter;
  const r = cfg.ribbon;
  return {
    end: landingEnd(cfg),
    length: r.landing_mm[0],
    width: r.landing_mm[1],
    bottom: -a.standoff_mm,
    top: -a.standoff_mm + r.landing_mm[2],
  };
}

/**
 * Two feeds on one hole sit side by side along this world direction: on the
 * adapter its y, along its hole rows; on a Pro Micro its x, along its pin rows.
 */
export function holeAlong(cfg: Config, frames: Record<string, Matrix4>): V3 {
  const e = (controllerStyle(cfg) === 'pro_micro' ? frames.pro_micro : frames.adapter).elements;
  return controllerStyle(cfg) === 'pro_micro' ? [e[0], e[1], e[2]] : [e[4], e[5], e[6]];
}

/**
 * The hand's board and what leaves it, as parts for display and the checks:
 * the adapter, its connector and the ribbon, or the Pro Micro, its TRRS jack
 * and their plugs.
 */
export function controllerParts(
  cfg: Config,
  frames = componentFrames(cfg),
  /** Where the ribbon leaves, in world x, once a build has placed it. */
  panelX?: number,
): Part[] {
  return controllerStyle(cfg) === 'pro_micro'
    ? proMicroParts(cfg, frames)
    : adapterParts(cfg, frames, panelX);
}

/** The adapter, its connector and the ribbon, as parts for display and the checks. */
function adapterParts(
  cfg: Config,
  frames = componentFrames(cfg),
  /** Where the ribbon leaves, in world x, once a build has placed it. */
  panelX?: number,
): Part[] {
  const a = cfg.adapter;
  const r = cfg.ribbon;
  const f = frames.adapter;
  const parts: Part[] = [];
  const [bx, by, bz] = a.board_mm;
  const box = (name: string, group: string, size: V3, center: V3, m: Matrix4 = f) =>
    parts.push({ name, group, size, center, matrix: m.elements.slice() });
  parts.push({
    name: 'Adapter board',
    group: 'adapter',
    size: [bx, by, bz],
    center: [0, 0, bz / 2],
    matrix: f.elements.slice(),
    holes: a.mounting_holes_mm.map((h) => ({ at: h, diameter: a.mounting_hole_diameter_mm })),
  });
  const c = a.connector_mm;
  const cx = -bx / 2 + a.connector_inset_mm + c[0] / 2;
  box('Adapter connector', 'adapter', [c[0], c[1], c[2]], [cx, 0, bz + c[2] / 2]);
  box(
    'Adapter connector latch room',
    'adapter',
    [c[0], c[1], a.latch_room_mm],
    [cx, 0, bz + c[2] + a.latch_room_mm / 2],
  );
  // The end face, along the adapter's x (the ribbon leaves along its -x).
  const e = f.elements;
  const panel = panelX === undefined || e[0] < 0.1 ? undefined : (panelX - e[12]) / e[0];
  const path = ribbonPath(cfg, panel).map((p) => point(f, p));
  const across = point(f, [0, 1, 0]).map((x, i) => x - f.elements[12 + i]) as V3;
  for (let i = 0; i + 1 < path.length; i++)
    parts.push(
      segmentPart(
        `Ribbon ${i + 1}`,
        'ribbon',
        path[i],
        path[i + 1],
        across,
        r.width_mm,
        r.thickness_mm,
      ),
    );
  return parts;
}

/** The pads and holes on every tile, as thin boxes (a hole's ring, round) on the tile's underside. */
export function padParts(cfg: Config, frames = componentFrames(cfg)): Part[] {
  const tile = cfg.tile;
  const z = tileUnderside(cfg) - WIRING.padLift;
  return Object.keys(frames)
    .filter(isKey)
    .flatMap((key) =>
      tile.pads.list.map((p) => ({
        name: `${key}: ${p.name} ${p.hole ? 'hole' : 'pad'}`,
        group: 'pads',
        size: (p.hole
          ? [tile.pads.ring_mm, tile.pads.ring_mm, WIRING.padThickness]
          : [...tile.pads.size_mm, WIRING.padThickness]) as V3,
        center: [p.at_mm[0], p.at_mm[1], z] as V3,
        matrix: frames[key].elements.slice(),
        cylinder: p.hole ? tile.pads.ring_mm / 2 : undefined,
      })),
    );
}

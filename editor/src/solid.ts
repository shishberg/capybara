import type { Manifold, ManifoldToplevel } from 'manifold-3d';
import { Matrix4 } from 'three';
import { openingSpan, seatBox, seatSettings, seatSwitches, clipBox, switchHole } from './seats';
import { RegionIndex, type Region } from './regions';
import { buildChassis } from './chassis';
import { hardware, type Part } from './parts';
import {
  box,
  capsule,
  freeAfter,
  freeAfterAsync,
  keycapSolid,
  meshData,
  place,
  type Factory,
} from './manifold-util';
import { crossings, wiring, type Wiring } from './wiring';
import {
  capClearance,
  capSize,
  keycapEnvelope,
  isKey,
  keyGroups,
  componentFrames,
  validateProject,
  type V3,
  type MeshData,
  type Project,
} from './geometry';
/** Sizes and limits for the clearance checks, in mm (volumes in mm³, areas in mm²). */
const CHECKS = {
  /** Overlap volume below which a collision is ignored. */
  overlap: 0.05,
  /** Volume below which a cut or probe counts as empty. */
  empty: 0.001,
  /** Volume a keycap's room may remove from the chassis before the check fails. */
  roomCut: 0.05,
  /** Opening probes: nine, this far inside the opening's edges, each this wide and this tall. */
  probeInset: 0.25,
  probeSize: 0.3,
  probeHeight: 24,
  /** The punch that clears a probe's column of the opening is this wide. */
  punchSize: 0.4,
  /** The seat's ring check leaves out the hole, this tall. */
  ringHoleHeight: 10,
  /** Seat checks test a shape this far inside the faces they must not touch, so those faces don't count. */
  faceSkip: 0.01,
  /** The seat's outside is tested this far above its plane. */
  outsideReach: 1,
  /** Pieces smaller than this (mm³) are ignored when counting pieces: slivers left by boolean operations. */
  minPiece: 0.5,
  /** The footprint check's section height above the floor, and the smallest area it counts. */
  footprintHeight: 1.5,
  minFootprint: 1,
  /** Highlighted footprints are extruded this tall. */
  footprintShow: 3,
  /** Keycap groups further apart than this are not listed. */
  capGapSearch: 40,
  /** Wire tubes: sides per segment's end sphere. */
  wireSides: 8,
  /**
   * The chassis round each key that its checks test against: past the
   * largest of its keycap with clearance, tile and seat by this much, and this
   * far above and below the plate.
   */
  regionMargin: 3,
  regionHeight: 30,
  /** The regions' shared chunks reach this far past their corners. */
  regionPad: 0.1,
} as const;
export interface Clearance {
  name: string;
  size: V3;
  margin: number;
  atRest: number;
  swept: number;
  passed: boolean;
}
export interface SeatCheck {
  name: string;
  missing: number;
  excess: number;
  clipBlocked: number;
  passed: boolean;
}
export interface Report {
  seats: SeatCheck[];
  passed: boolean;
  keycaps: Clearance[];
  capGaps: { between: string; gap: number }[];
  pieces: number[];
  footprint: number[];
  /** Keys whose keycap room had to remove chassis, and how much (mm³). */
  roomCuts: { name: string; volume: number }[];
  hardware: { name: string; group: string; volume: number }[];
  /** The whole hand's wiring: wire count, solder joints and cut length (mm). */
  wiring: { wires: number; joints: number; length: number };
  /** Pairs of wires that run into each other, named together. */
  crossings: string[];
  openings: {
    name: string;
    removed: number;
    covered: number;
    blocked: number;
    passed: boolean;
  }[];
  volume: number;
  triangles: number;
  milliseconds: number;
}
export interface Highlight {
  name: string;
  kind: 'rest' | 'travel' | 'room' | 'hardware' | 'opening' | 'seat' | 'loose' | 'wire';
  mesh: MeshData;
}
export interface BuildResult {
  mesh: MeshData;
  base: MeshData;
  report: Report;
  highlights: Highlight[];
  /** The routed wiring, which the editor draws with the chassis it was checked against. */
  wiring: Wiring;
}
export function buildSolid(wasm: ManifoldToplevel, project: Project): BuildResult {
  return freeAfter(wasm, () => build(wasm, project));
}
/** The same build, with the wires routed elsewhere (`route`, in another worker). */
export async function buildSolidAsync(
  wasm: ManifoldToplevel,
  project: Project,
  route: (cfg: Project['config']) => Promise<Wiring>,
): Promise<BuildResult> {
  return freeAfterAsync(wasm, async () => {
    validateProject(project);
    const start = performance.now();
    return build(wasm, project, { wired: await route(project.config), start });
  });
}
export type Keys = [string, Matrix4][];

/** The chassis tests a check makes: a shape against the chassis, near the key it belongs to. */
interface Probe {
  M: Factory;
  regions: RegionIndex;
  /** Volume of `envelope` that `body` fills. */
  volume(body: Manifold, envelope: Manifold): number;
  /** The same, recording where it exceeds the overlap limit. */
  collision(
    body: Manifold,
    envelope: Manifold,
    name: string,
    kind: Highlight['kind'],
    out: Highlight[],
  ): number;
}

export function makeProbe(M: Factory, regions: RegionIndex): Probe {
  const volume = (body: Manifold, envelope: Manifold) => {
    const hit = regions.within(body, envelope).intersect(envelope);
    try {
      return Math.max(0, hit.volume());
    } finally {
      hit.delete();
    }
  };
  const collision = (
    body: Manifold,
    envelope: Manifold,
    name: string,
    kind: Highlight['kind'],
    out: Highlight[],
  ) => {
    const hit = regions.within(body, envelope).intersect(envelope);
    try {
      const v = Math.max(0, hit.volume());
      if (v > CHECKS.overlap) out.push({ name, kind, mesh: meshData(hit) });
      return v;
    } finally {
      hit.delete();
    }
  };
  return { M, regions, volume, collision };
}

/** Each key's region: its keycap with clearance, tile and seat, and a margin. */
export function keyRegions(cfg: Project['config'], keys: Keys): Region[] {
  const extraThumbs = new Set(keyGroups(cfg).extra);
  const { outer } = seatSettings(cfg);
  return keys.map(([name, frame]) => {
    const cap = capSize(cfg, name);
    const margin = capClearance(cfg, name);
    const half = [0, 1].map(
      (k) =>
        Math.max(cap[k] / 2 + margin, cfg.tile.size_mm[k] / 2, outer[k] / 2) + CHECKS.regionMargin,
    );
    // Regions of a column or thumb row share a chunk.
    const group = name.startsWith('matrix_')
      ? name.slice(0, name.lastIndexOf('_'))
      : extraThumbs.has(name)
        ? 'extra thumbs'
        : 'thumbs';
    return { frame, half, group };
  });
}

/**
 * Probes each opening at nine points: covered if the chassis is there at all,
 * blocked if any of it is left once the opening's height is punched out.
 */
export function checkOpenings(
  p: Probe,
  cfg: Project['config'],
  keys: Keys,
  body: Manifold,
  cutters: Manifold[],
) {
  const hole = switchHole(cfg);
  const { bottom, top } = openingSpan(cfg);
  const highlights: Highlight[] = [];
  const openings: Report['openings'] = [];
  for (const [i, [name, m]] of keys.entries()) {
    const cutter = cutters[i];
    let covered = 0;
    let blocked = 0;
    const inset = CHECKS.probeInset;
    for (const x of [-hole[0] / 2 + inset, 0, hole[0] / 2 - inset])
      for (const y of [-hole[1] / 2 + inset, 0, hole[1] / 2 - inset]) {
        const probe = place(
          box(p.M, [CHECKS.probeSize, CHECKS.probeSize, CHECKS.probeHeight], [x, y, 0]),
          m,
        );
        const hit = p.regions.within(body, probe).intersect(probe);
        if (hit.volume() > CHECKS.empty) {
          covered++;
          const punch = place(
            box(
              p.M,
              [CHECKS.punchSize, CHECKS.punchSize, top - bottom],
              [x, y, (top + bottom) / 2],
            ),
            m,
          );
          const rest = hit.subtract(punch);
          if (rest.volume() > CHECKS.empty) blocked++;
        }
      }
    const removed = p.volume(body, cutter);
    const passed = covered === 9 && blocked === 0 && removed > CHECKS.empty;
    if (!passed) highlights.push({ name, kind: 'opening', mesh: meshData(cutter) });
    openings.push({ name, removed, covered, blocked, passed });
  }
  return { openings, highlights };
}

/** The bottom section is a separate print, so everything above it must be one piece. */
function checkPieces(cut: Manifold) {
  const pieces = cut
    .decompose()
    .filter((p) => p.volume() > CHECKS.minPiece)
    .sort((a, b) => b.volume() - a.volume());
  const highlights = pieces
    .slice(1)
    .map((p, i): Highlight => ({ name: `loose piece ${i + 1}`, kind: 'loose', mesh: meshData(p) }));
  return { pieces: pieces.map((p) => p.volume()), highlights };
}

/**
 * Without the bottom section the frame must also hold together along its
 * foot: a section just above the base plate it stands on (`floor`) must be
 * one connected area.
 */
function checkFootprint(cut: Manifold, floor: number) {
  const footprint = cut
    .slice(floor + CHECKS.footprintHeight)
    .decompose()
    .map((c) => ({ a: c.area(), c }))
    .filter((x) => x.a > CHECKS.minFootprint)
    .sort((x, y) => y.a - x.a);
  const highlights = footprint.slice(1).map((x, i): Highlight => ({
    name: `separate footprint ${i + 1}`,
    kind: 'loose',
    mesh: meshData(x.c.extrude(CHECKS.footprintShow)),
  }));
  return { footprint: footprint.map((x) => x.a), highlights };
}

/** Chassis built where a keycap goes, which its room had to remove. */
function checkRooms(roomCuts: { name: string; cut: Manifold }[]) {
  const rooms = roomCuts
    .map((r) => ({ name: r.name, volume: r.cut.volume(), cut: r.cut }))
    .filter((r) => r.volume > CHECKS.roomCut);
  const highlights = rooms.map((r): Highlight => ({
    name: `${r.name} keycap room`,
    kind: 'room',
    mesh: meshData(r.cut),
  }));
  return { roomCuts: rooms.map(({ name, volume }) => ({ name, volume })), highlights };
}

/** Each seat must be a complete ring around the hole, with nothing above its plane or in its clip reliefs (below it the sleeve fills round the switch body). */
export function checkSeats(p: Probe, cfg: Project['config'], keys: Keys, result: Manifold) {
  const hole = switchHole(cfg);
  const skip = CHECKS.faceSkip;
  const highlights: Highlight[] = [];
  const seats: SeatCheck[] = [];
  for (const [name, m] of keys) {
    const ring = seatBox(p.M, cfg, m).subtract(
      place(box(p.M, [...hole, CHECKS.ringHoleHeight]), m),
    );
    const missingSolid = ring.subtract(p.regions.within(result, ring));
    const missing = Math.max(0, missingSolid.volume());
    const outer = seatSettings(cfg).outer;
    const outside = place(
      box(
        p.M,
        [outer[0] - 2 * skip, outer[1] - 2 * skip, CHECKS.outsideReach],
        [0, 0, skip + CHECKS.outsideReach / 2],
      ),
      m,
    );
    const excess = p.collision(result, outside, name, 'seat', highlights);
    let clipBlocked = 0;
    for (const sign of [-1, 1])
      clipBlocked += p.collision(
        result,
        clipBox(p.M, cfg, m, sign, skip),
        name,
        'seat',
        highlights,
      );
    if (missing > CHECKS.overlap)
      highlights.push({ name, kind: 'seat', mesh: meshData(missingSolid) });
    seats.push({
      name,
      missing,
      excess,
      clipBlocked,
      passed:
        missing <= CHECKS.overlap && excess <= CHECKS.overlap && clipBlocked <= CHECKS.overlap,
    });
  }
  return { seats, highlights };
}

/**
 * Hardware (the tiles, the Pro Micro, its jack, their plugs and its reset
 * switch) against the chassis and its bottom section; the feeds' Dupont
 * housings, which stand up under the keys, against the tiles, their parts
 * and pads too.
 */
function checkHardware(
  p: Probe,
  project: Project,
  nodes: ReturnType<typeof componentFrames>,
  result: Manifold,
) {
  const parts = hardware(project, nodes);
  const shapeOf = (part: Part) => {
    let shape = part.cylinder
      ? p.M.cylinder(part.size[2], part.cylinder, part.cylinder, 64, true).translate(part.center)
      : box(p.M, part.size, part.center);
    if (part.notch)
      for (const x of [-1, 1])
        for (const y of [-1, 1])
          shape = shape.subtract(
            p.M.cylinder(part.size[2] + 2, part.notch, part.notch, 32, true).translate([
              part.center[0] + (x * part.size[0]) / 2,
              part.center[1] + (y * part.size[1]) / 2,
              part.center[2],
            ]),
          );
    for (const h of part.holes ?? [])
      shape = shape.subtract(
        p.M.cylinder(part.size[2] + 2, h.diameter / 2, h.diameter / 2, 32, true).translate([
          h.at[0],
          h.at[1],
          part.center[2],
        ]),
      );
    return place(shape, new Matrix4().fromArray(part.matrix));
  };
  const tiles = p.M.union(
    parts.filter((x) => ['pcb', 'components', 'pads'].includes(x.group)).map(shapeOf),
  );
  const against: Record<string, Manifold> = {
    pcb: result,
    components: result,
    controller: result,
    cable: result,
    dupont: result.add(tiles),
  };
  const highlights: Highlight[] = [];
  const overlaps: Report['hardware'] = [];
  for (const part of parts)
    if (against[part.group]) {
      const v = p.collision(against[part.group], shapeOf(part), part.name, 'hardware', highlights);
      if (v > CHECKS.overlap) overlaps.push({ name: part.name, group: part.group, volume: v });
    }
  return { hardware: overlaps, highlights };
}

/** Every wire, as a tube of its diameter, must miss every other wire. */
function checkWires(p: Probe, wired: Wiring) {
  const tube = (points: number[][], d: number) =>
    p.M.union(points.slice(1).map((q, i) => capsule(p.M, points[i], q, d / 2, CHECKS.wireSides)));
  const wireName = (w: Wiring['wires'][number]) =>
    `${w.net}: ${w.from.replace(/^(matrix|thumb)_/, '')} to ${w.to.replace(/^(matrix|thumb)_/, '')}`;
  const highlights: Highlight[] = [];
  const crossed = crossings(wired.wires).map(([a, b]) => {
    const [x, y] = [wired.wires[a], wired.wires[b]];
    const name = `${wireName(x)} and ${wireName(y)}`;
    p.collision(tube(x.points, x.diameter), tube(y.points, y.diameter), name, 'wire', highlights);
    return name;
  });
  return { crossings: crossed, highlights };
}

/** Each keycap, at rest and over its full travel grown by its clearance, must miss the chassis. */
function checkKeycaps(p: Probe, cfg: Project['config'], keys: Keys, result: Manifold) {
  const highlights: Highlight[] = [];
  const keycaps: Clearance[] = [];
  const rests: Record<string, Manifold> = {};
  for (const [name, m] of keys) {
    const rest = (rests[name] = place(
      keycapSolid(p.M, keycapEnvelope(cfg, name, { clearance: 0 }), false),
      m,
    ));
    const sweep = place(keycapSolid(p.M, keycapEnvelope(cfg, name)), m);
    const atRest = p.collision(result, rest, name, 'rest', highlights);
    const swept = p.collision(result, sweep, name, 'travel', highlights);
    keycaps.push({
      name,
      size: capSize(cfg, name),
      margin: capClearance(cfg, name),
      atRest,
      swept,
      passed: atRest <= CHECKS.overlap && swept <= CHECKS.overlap,
    });
  }
  return { keycaps, rests, highlights };
}

/** Closest distance between the resting keycaps of the finger columns, the thumb row and the extra thumb row. */
function checkCapGaps(M: Factory, cfg: Project['config'], rests: Record<string, Manifold>) {
  const groups = keyGroups(cfg);
  const unions = (
    [
      ['fingers', groups.fingers],
      ['thumbs', groups.thumbs],
      ['extra thumbs', groups.extra],
    ] as [string, string[]][]
  )
    .filter(([, ns]) => ns.length)
    .map(([label, ns]) => [label, M.union(ns.map((n) => rests[n]))] as const);
  const capGaps: Report['capGaps'] = [];
  for (let i = 0; i < unions.length; i++)
    for (let j = i + 1; j < unions.length; j++) {
      const gap = unions[i][1].minGap(unions[j][1], CHECKS.capGapSearch);
      if (gap < CHECKS.capGapSearch)
        capGaps.push({ between: `${unions[i][0]} – ${unions[j][0]}`, gap });
    }
  return capGaps;
}

function build(
  wasm: ManifoldToplevel,
  project: Project,
  given: { wired?: Wiring; start?: number } = {},
): BuildResult {
  validateProject(project);
  const start = given.start ?? performance.now();
  const cfg = project.config;
  const nodes = componentFrames(cfg);
  const keys: Keys = Object.entries(nodes).filter(([name]) => isKey(name));
  const wired = given.wired ?? wiring(cfg, nodes);
  const chassis = buildChassis(wasm, cfg, nodes, wired);
  if (chassis.body.status() !== 'NoError') throw Error('Invalid chassis: ' + chassis.body.status());
  const M = wasm.Manifold;
  const probe = makeProbe(
    M,
    new RegionIndex(M, keyRegions(cfg, keys), CHECKS.regionHeight, CHECKS.regionPad),
  );

  const seated = seatSwitches(
    M,
    cfg,
    chassis.body,
    keys.map(([, m]) => m),
  );
  const opened = checkOpenings(probe, cfg, keys, seated.body, seated.openings);
  const cut = seated.body.subtract(M.union([...seated.reliefs, ...seated.openings]));
  if (cut.status() !== 'NoError' || cut.volume() <= 0)
    throw Error('Cutouts produced an invalid solid: ' + cut.status());
  const loose = checkPieces(cut);
  const footprint = checkFootprint(cut, cfg.chassis.skin_mm);
  const rooms = checkRooms(chassis.roomCuts);
  // Checked as one solid; the frame and its bottom section are still returned
  // (and printed) separately.
  const result = cut.add(chassis.base);
  const seats = checkSeats(probe, cfg, keys, result);
  const hw = checkHardware(probe, project, nodes, result);
  const wireChecks = checkWires(probe, wired);
  const caps = checkKeycaps(probe, cfg, keys, result);
  const capGaps = checkCapGaps(M, cfg, caps.rests);

  const mesh = meshData(cut);
  const passed =
    seats.seats.every((s) => s.passed) &&
    caps.keycaps.every((k) => k.passed) &&
    hw.hardware.length === 0 &&
    loose.pieces.length === 1 &&
    footprint.footprint.length === 1 &&
    rooms.roomCuts.length === 0 &&
    capGaps.every((c) => c.gap > 0) &&
    opened.openings.every((o) => o.passed) &&
    wireChecks.crossings.length === 0;
  return {
    mesh,
    base: meshData(chassis.base),
    highlights: [
      ...opened.highlights,
      ...loose.highlights,
      ...footprint.highlights,
      ...rooms.highlights,
      ...seats.highlights,
      ...hw.highlights,
      ...wireChecks.highlights,
      ...caps.highlights,
    ],
    wiring: wired,
    report: {
      seats: seats.seats,
      passed,
      keycaps: caps.keycaps,
      capGaps,
      pieces: loose.pieces,
      footprint: footprint.footprint,
      roomCuts: rooms.roomCuts,
      hardware: hw.hardware,
      wiring: {
        wires: wired.wires.length,
        joints: wired.nets.reduce((t, n) => t + n.joints, 0),
        length: wired.nets.reduce((t, n) => t + n.length, 0),
      },
      crossings: wireChecks.crossings,
      openings: opened.openings,
      volume: result.volume(),
      triangles: mesh.indices.length / 3,
      milliseconds: performance.now() - start,
    },
  };
}

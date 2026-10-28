// Types and constants shared by the wiring modules.
import type { Matrix4 } from 'three';
import type { Config, V3 } from '../geometry';

export interface NetSpec {
  name: string;
  /** The Pro Micro pin its feeds land on (pro_micro.pins). */
  pin: number;
  group: string;
  /** The pad a wire arrives at on each key, and the pad the next wire leaves from. */
  pads: string[];
  /** Keys in wiring order; each chain has its own feed. Default: [led_order]. */
  chains?: string[][];
  /** The feed goes to the first key of each chain (LED data flows DI to DO). */
  directed?: boolean;
  /**
   * Each chain is one wire, a rail: a stub (wiring.stub_mm) stands down from
   * its pad (a hole) on each key, and the rail runs from stub to stub,
   * soldered to each. The feed lands on the first stub.
   */
  rail?: boolean;
}
export interface Pad {
  key: string;
  name: string;
  /** The pad's world point, its point in its key's frame (x, y), and its key's downward normal. */
  at: V3;
  xy: [number, number];
  down: V3;
  /** On a rail's pad: how far its stub stands below the tile's underside. A wire joins it anywhere along it. */
  stub?: number;
}
export interface Wire {
  net: string;
  group: string;
  from: string;
  to: string;
  points: V3[];
  diameter: number;
  /** Cut length: along the path, plus end allowances and, on a feed, the service loop. */
  length: number;
  feed: boolean;
  /**
   * On a rail: the stubs it is soldered to, in order. Each one's key, the
   * points (indices into points) where the rail comes onto it and leaves it,
   * and how far along the rail from its cut end its joint is (the middle of
   * those), in mm.
   */
  stubs?: { key: string; points: [number, number]; along: number }[];
}
export interface NetSummary {
  name: string;
  pin: number;
  /** Where its feeds land, for the wiring panel: the Pro Micro pin and its GPIO. */
  label: string;
  group: string;
  wires: number;
  /**
   * Solder joints: both ends of each wire but a feed's, which plugs onto its
   * pin; on a rail, one at each stub and the stub's own in its hole.
   */
  joints: number;
  length: number;
}
export interface Wiring {
  pads: Pad[];
  wires: Wire[];
  nets: NetSummary[];
  /** Each key's row and column net, and their pins. */
  matrix: { key: string; row: string; column: string }[];
}

/** A tile edge: the key axis (0 for x, 1 for y) and its sign. */
export type Edge = [0 | 1, number];

/** How a wire runs. */
export interface Lane {
  /** Depths below the first and second tiles. */
  da: number;
  db: number;
  /** Shift along the tile edge a wire crosses, or in plan for a feed's run to the Pro Micro. */
  aside: number;
  /** Between tiles: the shift along the second tile's edge. */
  asideB?: number;
  /**
   * For a feed: the edge its pad's leg leaves its tile by, if not the pad's
   * own.
   */
  edge?: Edge;
  /** For a feed: its level in the loom, in steps of loomStep from loom_height_mm. */
  level?: number;
  /** For a feed: it comes down past its housing's inner face, between the pin rows, not its outer. */
  inside?: boolean;
  /** For a feed down past its inner face: it runs between the pin rows and out past their far end, away from the USB port. */
  round?: boolean;
  /**
   * For a feed: it leaves its housing straight up, runs across over the
   * housings (pro_micro.dupont's exit_mm over their tops), this many
   * loomStep higher, to just past them and down to the loom, not down past a
   * face: the way from the far pin row across the near one.
   */
  over?: number;
}

/** What the routing modules share about the build. */
export interface Env {
  cfg: Config;
  frames: Record<string, Matrix4>;
  /** Height of a tile's underside in its key's frame. */
  padZ: number;
  /** Height of the loom's bottom level in world z. */
  loomZ: number;
  /** The lowest a wire's underside may run, in world z: the floor's skin above the base (z = 0). */
  floorZ: number;
  /** The tile pocket's half-widths. */
  half: [number, number];
  /** How far below a tile's underside its tallest part reaches, with clearance. */
  componentDepth: number;
  /** Where on a tile (x, y) the pads and holes are that some net's wires end on. */
  wiredPads: [number, number][];
  hole: Record<number, V3>;
  /**
   * Half the width of the room a stub keeps for its joints, which a route
   * puts on the stub's line: the wider of the stub and the rail's wire.
   */
  stubRoom: number;
}

/** Extra sizes for the wiring, in mm unless noted, that are not in the config. */
export const WIRING = {
  /** A hop over the pad's own edge runs this far below the tile's underside, at the shallowest. */
  hopDepth: 0.6,
  /** A run along the pads' strip (under the other pads' drops) starts this far below the tile. */
  stripDepth: 2.7,
  /** A run along the pads' strip goes this much deeper for each pad it passes under. */
  stripStep: 0.9,
  /** The rank of a leg's run along its pad's own edge (the rim), after every depth and aside. */
  rimRank: 5,
  /** How many depths each leg tries. */
  depthChoices: 4,
  /** Spacing of a leg's depth choices. */
  depthStep: 0.7,
  /** A wire clears the tile's parts, and its own radius, by this much more. */
  depthMargin: 0.1,
  /** Between keys at different heights, how far in under the higher tile a wire may step back to find its way down. */
  climbBack: 12,
  /** Spacing of the steps back in under the higher tile. */
  climbBackStep: 1,
  /** Spacing, as a fraction of the leg's run, of the points a climb down is tried from. */
  climbRunStep: 0.05,
  /** Failing that, how far below the lower of the two legs' ends a wire may run across under both. */
  climbUnder: 6,
  /** Spacing of the depths a run across under both legs' ends is tried at. */
  climbUnderStep: 1,
  /** Feeds run to the Pro Micro at their own levels in the loom, this far apart. */
  loomStep: 1,
  /** The levels, in loomStep from the loom's height, nearest first. */
  loomLevels: [0, 1, -1, 2, -2, 3, -3, 4, -4, 5, 6, 7, 8],
  /** Feeds over the housings try only this many of the first loomLevels. */
  overLoomLevels: 7,
  /** The heights a feed over the housings tries, in loomStep over the lowest, nearest first. */
  overLevels: [0, 1, 2, 3, 4, 5, 6],
  /** Sideways shifts of a feed's run to the Pro Micro, in plan, to get past other wires. */
  asides: [0, 1, -1, 2, -2],
  /** Shifts along the tile edge a wire crosses to the next tile. */
  edgeAsides: [0, 0.9, -0.9, 1.6, -1.6, 0.45, -0.45],
  /** The most rounds of negotiating the routes. */
  rounds: 150,
  /** Negotiating stops when the number of wires meeting has not fallen for this many rounds. */
  stall: 60,
  /** The cost of meeting another wire, against 1 per step of rank away from the nearest option. */
  penalty: 4,
  /** The factor the cost of meeting another wire grows by each round. */
  penaltyGrowth: 1.3,
  /** The cost added to an option for each round it met another wire. */
  historyCost: 1,
  /** How many of its cheapest options a meeting wire clears the way for. */
  blockerOptions: 24,
  /** The cost added to each wire in the way of a meeting wire's cheapest options. */
  blockerCost: 0.5,
  /** A wire keeps at most this many options. */
  optionLimit: 3000,
  /** When a wire has no option clear of the tiles, the rank added to each of its options. */
  blockedRank: 100,
  /** The most passes of repairing meeting wires in small groups. */
  repairPasses: 6,
  /** How many of the wires most in a meeting pair's way join it in a repair group. */
  repairBlockers: 4,
  /** The search steps each repaired group may take. */
  repairWork: 5000000,
  /** If any still meet when routing with every choice, negotiating starts again this many times. */
  restarts: 3,
  /** Wires may touch: they count as passing into each other only past this much. */
  touch: 0.02,
  /** Centre spacing of two wires on one pad, along it. */
  padShare: 0.9,
  /** Centre spacing of two wires on one Pro Micro pin, along its row. */
  holeShare: 1,
  /** A wire comes down past its Dupont housing's face this far off it. */
  plugMargin: 0.2,
  /** Feeds try only this many of the depths, until routing with every choice. */
  feedDepths: 2,
  /** Wires are checked against the tiles and their parts every this many mm along. */
  sample: 0.3,
  /** The obstacles are indexed in square cells in plan of this size. */
  gridCell: 6,
  /** A Pro Micro's link wires to its TRRS jack run this far above the higher of its parts and the jack, */
  linkOver: 1,
  /** each this far above the one before. */
  linkStep: 1.2,
  /** A link wire comes onto a reset switch leg from this far behind it. */
  linkBehind: 2,
  /** A pad's drawn box is this thick. */
  padThickness: 0.1,
  /** A pad's drawn box sits this far under the tile's underside. */
  padLift: 0.05,
} as const;

export const length = (ps: V3[]) =>
  ps.reduce((t, p, i) => (i ? t + Math.hypot(...p.map((x, j) => x - ps[i - 1][j])) : t), 0);
export const distance = (a: number[], b: number[]) =>
  Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
export const mid = (a: number[], b: number[]): V3 => [
  (a[0] + b[0]) / 2,
  (a[1] + b[1]) / 2,
  (a[2] + b[2]) / 2,
];

/** The Pro Micro pin a net's feeds land on (pro_micro.pins). */
export function pinOf(cfg: Config, net: string) {
  const n = (cfg.pro_micro.pins as Record<string, number>)[net];
  if (n === undefined) throw Error(`pro_micro.pins has no pin for ${net}`);
  return n;
}

/** The hand's nets (wiring.nets), each with the pin its feeds land on. */
export const nets = (cfg: Config): NetSpec[] =>
  (cfg.wiring.nets as Omit<NetSpec, 'pin'>[]).map((n) => ({ ...n, pin: pinOf(cfg, n.name) }));

/** The names of the pads a rail's stubs stand in. */
export const railPads = (cfg: Config) => new Set(nets(cfg).flatMap((n) => (n.rail ? n.pads : [])));

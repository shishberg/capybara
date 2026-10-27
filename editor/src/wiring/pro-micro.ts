// The hand's controller hardware: an RP2040 board in Pro Micro form factor and a TRRS jack on the bottom
// section, the board's USB-C port facing out of the hand's back end and the
// jack's barrel out of its inner side, and a reset switch in a pocket in the
// back wall, its plunger out through it. Their pins, the parts, the
// plugs, the openings for the plugs and the plunger, the jack's collar and
// the cradles that hold them.
import type { CrossSection, Manifold, ManifoldToplevel, Mat4 } from 'manifold-3d';
import { Matrix4 } from 'three';
import { componentFrames, point, type Config, type V3 } from '../geometry';
import { box, place } from '../manifold-util';
import type { Part } from '../parts';
import { WIRING, nets, type Wire } from './common';

/**
 * Pro Micro pin n's centre on the board's top, in its frame. The port faces
 * -x; seen from above with the port away from you, pins 1 to 12 run down the
 * left edge (-y) from the port end and 13 to 24 back up the right, as on a DIP.
 */
export function pinAt(cfg: Config, n: number): V3 {
  const b = cfg.pro_micro;
  const [bx, , bz] = b.board_mm;
  if (!(Number.isInteger(n) && n >= 1 && n <= 24)) throw Error(`No Pro Micro pin ${n}`);
  const left = n <= 12;
  const i = left ? n - 1 : 24 - n;
  return [
    -bx / 2 + b.first_pin_mm + i * b.pin_pitch_mm,
    ((left ? -1 : 1) * b.row_spacing_mm) / 2,
    bz,
  ];
}

/** Pro Micro pin n and its name (pro_micro.pinout), for the wiring panel. */
export const pinName = (cfg: Config, n: number) => `${n}, ${cfg.pro_micro.pinout[n - 1]}`;

/** The top of a Dupont housing over the board's top (pro_micro.dupont): its header's spacer and the housing on it. */
const plugHeight = (cfg: Config) =>
  cfg.pro_micro.dupont.spacer_mm + cfg.pro_micro.dupont.housing_mm[2];

/** Pin n's Dupont housing's top, in world coordinates, where its wire comes out. */
const plugTop = (cfg: Config, frames: Record<string, Matrix4>, n: number) => {
  const [x, y, z] = pinAt(cfg, n);
  return point(frames.pro_micro, [x, y, z + plugHeight(cfg)]);
};

/** World z over the Pro Micro's Dupont housings: their tops and the room over them for their wires to come out and turn (exit_mm). */
export const overPlugs = (cfg: Config, frames: Record<string, Matrix4>) =>
  point(frames.pro_micro, [0, 0, cfg.pro_micro.board_mm[2] + plugHeight(cfg) + cfg.pro_micro.dupont.exit_mm])[2];

/**
 * How far along (0 to 1) the straight way in plan from a to b a wire of
 * radius r is past the last Dupont housing it passes over, plugMargin off it,
 * leaving out pin `except`'s: 0 if it passes over none.
 */
export function pastPlugs(
  cfg: Config,
  frames: Record<string, Matrix4>,
  a: V3,
  b: V3,
  r: number,
  except?: number,
) {
  const inv = frames.pro_micro.clone().invert();
  const [p, q] = [point(inv, a), point(inv, b)];
  const steps = Math.max(1, Math.ceil(Math.hypot(q[0] - p[0], q[1] - p[1]) / WIRING.sample));
  const reach = cfg.pro_micro.dupont.housing_mm.map((s) => s / 2 + r + WIRING.plugMargin);
  const at = [...plugPins(cfg)].filter((n) => n !== except).map((n) => pinAt(cfg, n));
  for (let i = steps; i >= 0; i--) {
    const [u, v] = [p[0] + (i / steps) * (q[0] - p[0]), p[1] + (i / steps) * (q[1] - p[1])];
    if (at.some(([x, y]) => Math.abs(u - x) < reach[0] && Math.abs(v - y) < reach[1]))
      return Math.min(1, (i + 1) / steps);
  }
  return 0;
}

/** The pins that take a Dupont housing: every net's, the jack's and the reset switch's. */
export const plugPins = (cfg: Config) =>
  new Set([
    ...nets(cfg).map((n) => n.pin),
    ...cfg.trrs.wires.map((x) => x.pin),
    ...cfg.reset.wires.map((x) => x.pin),
  ]);

/**
 * Where each net's feeds land, in world coordinates, keyed by the net's
 * `pin`, the Pro Micro pin pro_micro.pins gives it: the top of the Dupont
 * housing plugged onto that pin, where the feed's wire comes out.
 */
export function holes(cfg: Config, frames = componentFrames(cfg)) {
  const out: Record<number, V3> = {};
  for (const net of nets(cfg)) out[net.pin] = plugTop(cfg, frames, net.pin);
  return out;
}

/**
 * Where a wire of radius r, out of its housing's top at `top`, comes down
 * past it: at that height, just off the housing's outer face, away from the
 * board's middle, or (`inside`) its inner face, between the pin rows.
 */
export function besideHousing(
  cfg: Config,
  frames: Record<string, Matrix4>,
  top: V3,
  r: number,
  inside = false,
) {
  const f = frames.pro_micro;
  const [x, y, z] = point(f.clone().invert(), top);
  const off = (inside ? -1 : 1) * (cfg.pro_micro.dupont.housing_mm[1] / 2 + r + WIRING.plugMargin);
  return point(f, [x, Math.sign(y) * (cfg.pro_micro.row_spacing_mm / 2 + off), z]);
}

/**
 * Where a wire of radius r between the pin rows at p comes out past their far
 * end, away from the port: at p's height, as far across the rows as p, just
 * past the last pins' housings.
 */
export function pastRows(cfg: Config, frames: Record<string, Matrix4>, p: V3, r: number) {
  const f = frames.pro_micro;
  const [, y, z] = point(f.clone().invert(), p);
  const x = pinAt(cfg, 12)[0] + cfg.pro_micro.dupont.housing_mm[0] / 2 + r + WIRING.plugMargin;
  return point(f, [x, y, z]);
}

/** Two feeds on one pin sit side by side along this world direction: the board's x, along its pin rows. */
export function holeAlong(frames: Record<string, Matrix4>): V3 {
  const e = frames.pro_micro.elements;
  return [e[0], e[1], e[2]];
}

/** The jack's lug `name` (trrs.lugs_mm), in world coordinates on the jack's top. */
export const lugAt = (cfg: Config, frames: Record<string, Matrix4>, name: string) => {
  const j = cfg.trrs;
  const at = (j.lugs_mm as Record<string, number[]>)[name];
  if (!at) throw Error(`trrs.lugs_mm has no lug ${name}`);
  return point(frames.trrs, [at[0], at[1], j.body_mm[2]]);
};

/**
 * The reset switch's leg n (1 to 4; reset), in world coordinates on its back
 * (into the hand, as it stands): legs 1 and 2 on its -y side, 3 and 4 on +y,
 * the odd ones lower (-x), each where it stands out past the body, halfway
 * out.
 */
export const legAt = (cfg: Config, frames: Record<string, Matrix4>, n: number) => {
  const r = cfg.reset;
  if (!(Number.isInteger(n) && n >= 1 && n <= 4)) throw Error(`No reset switch leg ${n}`);
  const [, by, bz] = r.body_mm;
  return point(frames.reset, [
    ((n % 2 ? -1 : 1) * r.leg_pitch_mm) / 2,
    ((n <= 2 ? -1 : 1) * (by / 2 + r.leg_span_mm / 2)) / 2,
    bz,
  ]);
};

/**
 * Where each port's plug goes in, in its part's frame: the mouth's x (the
 * plug comes in along +x from there), and its centre's y and z. The USB-C
 * receptacle stands on the board's top, its mouth usb_overhang_mm past the
 * board's port end; the jack's barrel is on its body's port end, centred.
 */
export function mouths(cfg: Config) {
  const b = cfg.pro_micro;
  const j = cfg.trrs;
  return {
    usb: { x: -b.board_mm[0] / 2 - b.usb_overhang_mm, y: 0, z: b.board_mm[2] + b.usb_mm[2] / 2 },
    trrs: { x: -j.body_mm[0] / 2 - j.barrel_mm[0], y: 0, z: j.body_mm[2] / 2 },
  };
}

/** A reset switch leg's width and thickness (mm): a gull-wing leg's flat end. */
const LEG = [0.8, 0.3];

/** A part `size` about `center` in frame f, turned so its z axis (a cylinder's) runs along f's x. */
const alongX = (f: Matrix4) => f.clone().multiply(new Matrix4().makeRotationY(Math.PI / 2));

/** The Pro Micro, its pins' Dupont housings, the jack, both plugs and the reset switch, as parts for display and the checks. */
export function proMicroParts(cfg: Config, frames = componentFrames(cfg)): Part[] {
  const b = cfg.pro_micro;
  const j = cfg.trrs;
  const fb = frames.pro_micro;
  const fj = frames.trrs;
  const m = mouths(cfg);
  const [bx, by, bz] = b.board_mm;
  const [ux, uy, uz] = b.usb_mm;
  const parts: Part[] = [];
  const add = (name: string, group: string, size: V3, center: V3, f: Matrix4, cylinder?: number) =>
    parts.push({ name, group, size, center, matrix: f.elements.slice(), cylinder });
  add('Pro Micro board', 'controller', [bx, by, bz], [0, 0, bz / 2], fb);
  add('Pro Micro USB-C port', 'controller', [ux, uy, uz], [m.usb.x + ux / 2, 0, bz + uz / 2], fb);
  // Its parts on top, between the pin rows, behind the port.
  const [px, py, pz] = b.parts_mm;
  add('Pro Micro parts', 'controller', [px, py, pz], [m.usb.x + ux + px / 2, 0, bz + pz / 2], fb);
  // On each wired pin, its header's spacer, the Dupont housing on it and the
  // room over that for its wire to come out and turn.
  const { spacer_mm: spacer, housing_mm: housing, exit_mm: exit } = b.dupont;
  for (const pin of plugPins(cfg)) {
    const [x, y] = pinAt(cfg, pin);
    const [hx, hy, hz] = housing;
    add(`Pin ${pin} header`, 'dupont', [hx, hy, spacer], [x, y, bz + spacer / 2], fb);
    add(`Pin ${pin} Dupont housing`, 'dupont', [hx, hy, hz], [x, y, bz + spacer + hz / 2], fb);
    add(`Pin ${pin} wire exit`, 'dupont', [hx, hy, exit], [x, y, bz + spacer + hz + exit / 2], fb);
  }
  const [jx, jy, jz] = j.body_mm;
  add('TRRS jack', 'controller', [jx, jy, jz], [0, 0, jz / 2], fj);
  const [bl, bd] = j.barrel_mm;
  // A cylinder's axis is its frame's z: turned onto x, its centre's (x, y, z) is (-z, y, x).
  add(
    'TRRS jack barrel',
    'controller',
    [bd, bd, bl],
    [-m.trrs.z, 0, -jx / 2 - bl / 2],
    alongX(fj),
    bd / 2,
  );
  // The plugs, from their mouths out.
  const [pw, ph, pl] = b.plug_mm;
  add('USB-C plug', 'cable', [pl, pw, ph], [m.usb.x - pl / 2, 0, m.usb.z], fb);
  const [jd, jl] = j.plug_mm;
  add('TRRS plug', 'cable', [jd, jd, jl], [-m.trrs.z, 0, m.trrs.x - jl / 2], alongX(fj), jd / 2);
  // The reset switch, on edge with its plunger out, and its legs out of its back.
  const r = cfg.reset;
  const fr = frames.reset;
  const [rx, ry, rz] = r.body_mm;
  const [pd, pp] = r.plunger_mm;
  add('Reset switch', 'controller', [rx, ry, rz], [0, 0, rz / 2], fr);
  add('Reset switch plunger', 'controller', [pd, pd, pp], [0, 0, -pp / 2], fr, pd / 2);
  const out = (r.leg_span_mm - ry) / 2;
  for (let n = 1; n <= 4; n++)
    add(
      `Reset switch leg ${n}`,
      'controller',
      [LEG[0], out, LEG[1]],
      [
        ((n % 2 ? -1 : 1) * r.leg_pitch_mm) / 2,
        (n <= 2 ? -1 : 1) * (ry / 2 + out / 2),
        rz - LEG[1] / 2,
      ],
      fr,
    );
  return parts;
}

/**
 * The wall's fit round a port (mm): the clearance round its nose (the USB-C
 * receptacle's shell, the jack's barrel), which stands in the wall so that it
 * grips it; and the chamfer round the plug's opening where it meets the
 * wall's outer face.
 */
const GRIP = 0.15;
const CHAMFER = 1;

/**
 * How far (mm) from point `p` along the axis to `q` (in plan, world
 * coordinates) `outline` (plan) is, where the axis first crosses it; or none.
 */
function toOutline(outline: [number, number][], p: V3, q: V3) {
  const d = [q[0] - p[0], q[1] - p[1]];
  let best: number | undefined;
  outline.forEach((a, i) => {
    const e = outline[(i + 1) % outline.length];
    const s = [e[0] - a[0], e[1] - a[1]];
    const den = d[0] * s[1] - d[1] * s[0];
    if (Math.abs(den) < 1e-12) return;
    const w = [a[0] - p[0], a[1] - p[1]];
    const t = (w[0] * s[1] - w[1] * s[0]) / den;
    const u = (w[0] * d[1] - w[1] * d[0]) / den;
    if (t > 0 && u >= 0 && u <= 1 && (best === undefined || t < best)) best = t;
  });
  return best;
}

/**
 * The openings for the plugs, in world coordinates. Each port's nose stands
 * in the wall, its mouth short of the outer face, so the openings are: round
 * the nose, grown by GRIP, from its mouth in (with the board's end under the
 * USB-C receptacle, which reaches into the wall too); and the plug's overmold,
 * grown by clearance_mm, from its mouth out `reach` mm, CHAMFER wider at 45°
 * where it crosses `outline` (plan), the wall's outer face (no deeper than
 * the mouth). Square for the USB-C plug and round for the jack's.
 */
export function plugWays(
  wasm: ManifoldToplevel,
  cfg: Config,
  frames: Record<string, Matrix4>,
  reach: number,
  outline?: [number, number][],
) {
  const M = wasm.Manifold;
  const b = cfg.pro_micro;
  const j = cfg.trrs;
  const m = mouths(cfg);
  // How far out from mouth x (in frame f, along its -x) the outer face is.
  const face = (f: Matrix4, x: number, z: number) =>
    outline && toOutline(outline, point(f, [x, 0, z]), point(f, [x - 1, 0, z]));
  const e = 0.5;
  // The chamfer, no deeper than the mouth, so that the nose stays gripped.
  const chamfer = (d: number) => Math.min(CHAMFER, d);
  // USB-C: the receptacle's shell and the board's end under it, the plug, and
  // the chamfer: a hull from the plug's opening CHAMFER in from the face to it
  // grown CHAMFER (and e past).
  const [bx, by, bz] = b.board_mm;
  const end = -bx / 2 - GRIP;
  const [ux, uy, uz] = b.usb_mm;
  const [pw, ph] = b.plug_mm;
  const c = b.clearance_mm;
  const du = face(frames.pro_micro, m.usb.x, m.usb.z);
  const thin = (x: number, grow: number) =>
    box(M, [0.01, pw + 2 * c + 2 * grow, ph + 2 * c + 2 * grow], [x, 0, m.usb.z]);
  const usb = place(
    M.union([
      box(M, [ux, uy + 2 * GRIP, uz + 2 * GRIP], [m.usb.x + ux / 2, 0, bz + uz / 2]),
      box(
        M,
        [m.usb.x + ux - end, by + 2 * GRIP, bz + 2 * GRIP],
        [(m.usb.x + ux + end) / 2, 0, bz / 2],
      ),
      box(M, [reach, pw + 2 * c, ph + 2 * c], [m.usb.x - reach / 2, 0, m.usb.z]),
      ...(du === undefined
        ? []
        : [M.hull([thin(m.usb.x - du + chamfer(du), 0), thin(m.usb.x - du - e, chamfer(du) + e)])]),
    ]),
    frames.pro_micro,
  );
  // The jack: its barrel, the plug, and the chamfer: a cone the same way.
  const [bl, bd] = j.barrel_mm;
  const r = j.plug_mm[0] / 2 + j.clearance_mm;
  const dj = face(frames.trrs, m.trrs.x, m.trrs.z);
  // Along -x from x, h long, radius r0 there to r1 at its far end.
  const out = (x: number, h: number, r0: number, r1: number) =>
    M.cylinder(h, r0, r1, 48).rotate([0, -90, 0]).translate([x, 0, m.trrs.z]);
  const trrs = place(
    M.union([
      M.cylinder(bl, bd / 2 + GRIP, bd / 2 + GRIP, 48)
        .rotate([0, 90, 0])
        .translate([m.trrs.x, 0, m.trrs.z]),
      out(m.trrs.x, reach, r, r),
      ...(dj === undefined
        ? []
        : [out(m.trrs.x - dj + chamfer(dj), chamfer(dj) + e, r, r + chamfer(dj) + e)]),
    ]),
    frames.trrs,
  );
  return M.union([usb, trrs]);
}

/**
 * The reset switch's way, in world coordinates: a pocket in the inside of the
 * back wall round its body, and round its legs, which stand out of its back,
 * each grown by clearance_mm, which leaves a skin of the wall in front of its
 * plunger face; and a hole round its plunger, grown by clearance_mm, through
 * the skin to the outer face (`outline`, plan), chamfered at 45° there as the
 * plugs' openings are, by no more than half the skin. The plunger stands proud
 * of the face.
 */
export function resetWay(
  wasm: ManifoldToplevel,
  cfg: Config,
  frames: Record<string, Matrix4>,
  outline: [number, number][],
) {
  const M = wasm.Manifold;
  const f = frames.reset;
  const r = cfg.reset;
  const e = 0.5;
  const c = r.clearance_mm;
  const [rx, ry, rz] = r.body_mm;
  const bore = r.plunger_mm[0] / 2 + c;
  // From z0 back to a millimetre behind the body, past the wall's inside.
  const pocket = (x: number, y: number, z0: number) =>
    box(M, [x + 2 * c, y + 2 * c, rz + 1 - z0], [0, 0, (z0 + rz + 1) / 2]);
  const held = [
    pocket(rx, ry, 0),
    pocket(r.leg_pitch_mm + LEG[0], r.leg_span_mm, rz - LEG[1] - 2 * c),
  ];
  const d = toOutline(outline, point(f, [0, 0, 0]), point(f, [0, 0, -1]));
  if (d === undefined)
    return place(M.union([...held, M.cylinder(10 + e, bore, bore, 48).translate([0, 0, -10])]), f);
  const chamfer = Math.min(CHAMFER, d / 2);
  return place(
    M.union([
      ...held,
      M.cylinder(d + 2 * e, bore, bore, 48).translate([0, 0, -d - e]),
      M.cylinder(chamfer + e, bore + chamfer + e, bore, 48).translate([0, 0, -d - e]),
    ]),
    f,
  );
}

/** The collar's wall (mm) round the jack plug's way, outside its chamfer's widest. */
const COLLAR = 1;
/** How far (mm) the filled opening laps into the limbs round it, so that it shares no face with them. */
const LAP = 0.05;

/**
 * The jack's collar, in world coordinates. The jack stands under a wishbone,
 * which forks over its plug's way: the opening between its legs and the rail
 * is filled, `wall` thick inside the outline (`outline`, plan; the rail's
 * outer face) as the legs are, and round the barrel a boss as deep as the
 * barrel, in to the jack's body, so that the wall grips the barrel there too;
 * arched over it, COLLAR outside the chamfer round the plug's way, and down
 * to half a millimetre into the rail (`rail`, its top). The opening is the
 * frame's (`frame`), seen along the barrel; where no opening holds the
 * mouth, the boss stands alone.
 */
export function collar(
  wasm: ManifoldToplevel,
  cfg: Config,
  frames: Record<string, Matrix4>,
  outline: [number, number][],
  rail: number,
  frame: Manifold,
  wall: number,
) {
  const M = wasm.Manifold;
  const j = cfg.trrs;
  const m = mouths(cfg);
  const r = j.plug_mm[0] / 2 + j.clearance_mm + CHAMFER + COLLAR;
  // From the body's face out past the outer face (cut back to it below).
  const [x0, x1] = [m.trrs.x - 10, -j.body_mm[0] / 2];
  const bottom = rail - 0.5 - frames.trrs.elements[14];
  let boss = M.union([
    M.cylinder(x1 - x0, r, r, 64)
      .rotate([0, 90, 0])
      .translate([x0, 0, m.trrs.z]),
    box(M, [x1 - x0, 2 * r, m.trrs.z - bottom], [(x0 + x1) / 2, 0, (m.trrs.z + bottom) / 2]),
  ]);
  let fill: Manifold | undefined;
  const hole = opening(wasm, frame, frames.trrs, [x0, x1], bottom, m.trrs.z);
  if (hole) {
    // The opening, seen as (-z, y) along the frame's x: stood back up through
    // the wall, and down half a millimetre into the rail as the boss is.
    fill = hole
      .offset(LAP, 'Round')
      .extrude(x1 - x0)
      .translate([0, 0, x0])
      .rotate([0, 90, 0])
      .add(box(M, [x1 - x0, 2, 1], [(x0 + x1) / 2, 0, bottom + 0.5]));
    boss = boss.intersect(fill);
  }
  const bb = place(fill ? fill.add(boss) : boss, frames.trrs).boundingBox();
  const cs = new wasm.CrossSection([outline], 'NonZero');
  const prism = (c: CrossSection) =>
    c.extrude(bb.max[2] - bb.min[2] + 2).translate([0, 0, bb.min[2] - 1]);
  const bossIn = place(boss, frames.trrs).intersect(prism(cs));
  if (!fill) return bossIn;
  return place(fill, frames.trrs)
    .intersect(prism(cs.subtract(cs.offset(-wall, 'Miter'))))
    .add(bossIn);
}

/**
 * The frame's opening the jack's mouth (frame y 0, height z) looks out
 * through: the frame between x0 and x1 (in the jack's frame: the wall's
 * depth there) from `bottom` up 30 mm, seen along x, and the hole in it that
 * holds the mouth, as a cross-section in (-z, y); or none.
 */
function opening(
  wasm: ManifoldToplevel,
  frame: Manifold,
  f: Matrix4,
  [x0, x1]: [number, number],
  bottom: number,
  z: number,
) {
  const local = frame
    .transform(f.clone().invert().elements as Mat4)
    .intersect(box(wasm.Manifold, [x1 - x0, 60, 30], [(x0 + x1) / 2, 0, bottom + 15]));
  // A hole winds clockwise.
  const area = (p: [number, number][]) =>
    p.reduce((a, q, i) => a + q[0] * p[(i + 1) % p.length][1] - p[(i + 1) % p.length][0] * q[1], 0);
  const holds = (p: [number, number][], [u, v]: [number, number]) => {
    let inside = false;
    for (let i = 0, k = p.length - 1; i < p.length; k = i++)
      if (
        p[i][1] > v !== p[k][1] > v &&
        u < ((p[k][0] - p[i][0]) * (v - p[i][1])) / (p[k][1] - p[i][1]) + p[i][0]
      )
        inside = !inside;
    return inside;
  };
  const hole = (local.rotate([0, -90, 0]).project().toPolygons() as [number, number][][]).find(
    (p) => area(p) < 0 && holds(p, [-z, 0]),
  );
  return hole && new wasm.CrossSection([[...hole].reverse()], 'Positive');
}

/**
 * The cradles on the bottom section: under the Pro Micro a pedestal between
 * its pin rows (clear of the wire ends under them), guides along its long
 * edges and a stop behind its far end, which takes the push of the USB-C
 * plug; under the jack (lugs up) a pedestal, and round it a wall each side and
 * one behind; behind the reset switch (in its pocket in the back wall) a stop,
 * twice as thick as the walls, which takes the press, narrower than the body
 * so that its legs are clear. Each reaches half a millimetre into the floor.
 */
export function cradles(
  wasm: ManifoldToplevel,
  cfg: Config,
  frames: Record<string, Matrix4>,
): Manifold {
  const M = wasm.Manifold;
  const into = 0.5;
  const b = cfg.pro_micro;
  const j = cfg.trrs;
  const c = b.clearance_mm;
  const k = b.cradle;
  // A block in a part's frame from below the floor (the part stands `standoff` over it) up to `top`.
  const block = (standoff: number, x: number[], y: number[], top: number) =>
    box(
      M,
      [x[1] - x[0], y[1] - y[0], top + standoff + into],
      [(x[0] + x[1]) / 2, (y[0] + y[1]) / 2, (top - standoff - into) / 2],
    );
  const [bx, by, bz] = b.board_mm;
  const hx = bx / 2;
  const hy = by / 2;
  const w = k.wall_mm;
  const board = M.union([
    block(
      b.standoff_mm,
      [-hx + k.pedestal_in_mm[0], hx - k.pedestal_in_mm[1]],
      [-k.pedestal_width_mm / 2, k.pedestal_width_mm / 2],
      0,
    ),
    ...[-1, 1].map((s) =>
      block(
        b.standoff_mm,
        [-hx + k.guide_in_mm, hx + c + w],
        s < 0 ? [-hy - c - w, -hy - c] : [hy + c, hy + c + w],
        bz + k.above_mm,
      ),
    ),
    block(b.standoff_mm, [hx + c, hx + c + w], [-hy - c - w, hy + c + w], bz + k.above_mm),
  ]);
  const [jx, jy, jz] = j.body_mm;
  const jc = j.clearance_mm;
  const jack = M.union([
    block(j.standoff_mm, [-jx / 2, jx / 2], [-jy / 2, jy / 2], 0),
    ...[-1, 1].map((s) =>
      block(
        j.standoff_mm,
        [-jx / 2, jx / 2 + jc + w],
        s < 0 ? [-jy / 2 - jc - w, -jy / 2 - jc] : [jy / 2 + jc, jy / 2 + jc + w],
        jz * k.jack_walls,
      ),
    ),
    block(
      j.standoff_mm,
      [jx / 2 + jc, jx / 2 + jc + w],
      [-jy / 2 - jc - w, jy / 2 + jc + w],
      jz * k.jack_walls,
    ),
  ]);
  // The switch's frame has x up, so the stop runs in x from under the floor's
  // top to the body's top.
  const r = cfg.reset;
  const [rx, ry, rz] = r.body_mm;
  const low = -rx / 2 - r.standoff_mm - into;
  const z0 = rz + r.clearance_mm;
  const reset = box(M, [rx / 2 - low, ry - 2, 2 * w], [(rx / 2 + low) / 2, 0, z0 + w]);
  return M.union([
    place(board, frames.pro_micro),
    place(jack, frames.trrs),
    place(reset, frames.reset),
  ]);
}

/**
 * The link wires: the jack's (trrs.wires) and the reset switch's
 * (reset.wires), each in the order listed, out of the top of the Dupont
 * housing on its Pro Micro pin, over the housing's face toward its end (as a
 * feed's, besideHousing) and down beside it to a level, across to over its
 * lug and down onto it, or over a point linkBehind behind its leg, down to it
 * and onto the leg. The jack's
 * lowest level is linkOver above the board's parts or the jack's top,
 * whichever is higher, and the switch's above the board's parts or its top.
 * The next is linkStep above it, and so on, a level for each link wire.
 * A wire whose way across passes over another pin's housing (the left half's
 * jack's, its pins on the far row) may go over them, straight up out of its
 * own, its lowest level linkOver above the housings' tops and the room over
 * them for their wires (exit_mm); or, ranked after, under them: down past its
 * housing's inner face to a level linkOver above the board's parts and USB-C
 * receptacle, along between the pin rows and out across the far row past
 * either end or at a pin with no housing, then up if it must to its lowest
 * level over its end. Each wire's routes are its options when the wiring
 * negotiates (wiring), so the link wires take the lowest that keep them out
 * of each other and the tiles' wires. A leg is come at from behind since the
 * other leg on its side stands over it.
 * On a pin a feed also lands on (`fed`), the link wire comes out holeShare
 * along the pin row toward the port, so the two sit side by side in the
 * housing.
 */
export function linkWires(cfg: Config, frames: Record<string, Matrix4>, fed: Set<number>): Link[] {
  const b = cfg.pro_micro;
  const f = frames.pro_micro;
  const parts = point(f, [0, 0, b.board_mm[2] + b.parts_mm[2]])[2];
  const top = (frame: Matrix4, p: V3) => Math.max(parts, point(frame, p)[2]);
  const r = cfg.reset;
  const trrsTop = top(frames.trrs, [0, 0, cfg.trrs.body_mm[2]]);
  const resetTop = top(frames.reset, [r.body_mm[0] / 2, 0, 0]);
  const trrs = cfg.trrs.wires.map((x) => ({
    name: x.name,
    net: `TRRS ${x.name}`,
    pin: x.pin,
    to: `TRRS ${x.lug}`,
    end: lugAt(cfg, frames, x.lug),
    floor: trrsTop,
  }));
  const reset = r.wires.map((x) => {
    const end = legAt(cfg, frames, x.leg);
    const back = point(frames.reset, [0, 0, WIRING.linkBehind]);
    const o = frames.reset.elements;
    return {
      name: x.name,
      net: `Reset ${x.name}`,
      pin: x.pin,
      to: `reset leg ${x.leg}`,
      end,
      behind: end.map((v, i) => v + back[i] - o[12 + i]) as V3,
      floor: resetTop,
    };
  });
  return links(cfg, frames, fed, [...trrs, ...reset]);
}

/** A link wire, all but its route, and the routes it may take, each ranked, lower first (linkWires). */
export type Link = Omit<Wire, 'points' | 'length'> & { routes: { points: V3[]; rank: number }[] };

/** Link wires from Pro Micro pins to `end`s, each's lowest level linkOver above its `floor` (linkWires). */
function links(
  cfg: Config,
  frames: Record<string, Matrix4>,
  fed: Set<number>,
  list: {
    name: string;
    net: string;
    pin: number;
    to: string;
    end: V3;
    behind?: V3;
    floor: number;
  }[],
): Link[] {
  const b = cfg.pro_micro;
  const w = cfg.wiring;
  const f = frames.pro_micro;
  const toPort = point(f, [-WIRING.holeShare, 0, 0]).map((x, i) => x - f.elements[12 + i]);
  const inv = f.clone().invert();
  const plugs = plugPins(cfg);
  const levels = list.map((_, k) => k);
  return list.map((x) => {
    const power = x.name === 'VCC' || x.name === 'GND';
    const diameter = power ? w.power_wire_mm : w.signal_wire_mm;
    const at = plugTop(cfg, frames, x.pin);
    const from: V3 = fed.has(x.pin)
      ? [at[0] + toPort[0], at[1] + toPort[1], at[2] + toPort[2]]
      : at;
    const to = x.end;
    const over = x.behind ?? to;
    // Down past whichever of the housing's faces is nearer its end.
    const plan = (p: V3) => Math.hypot(p[0] - over[0], p[1] - over[1]);
    const by = [false, true]
      .map((inside) => besideHousing(cfg, frames, from, diameter / 2, inside))
      .reduce((p, q) => (plan(q) < plan(p) ? q : p));
    // Across over the other housings where its way passes over one, so
    // straight up out of its own.
    const passes = pastPlugs(cfg, frames, by, over, diameter / 2, x.pin) > 0;
    const floor = passes ? Math.max(x.floor, overPlugs(cfg, frames)) : x.floor;
    const run = (z: number): V3[] => [
      from,
      ...(z < from[2] ? [by, [by[0], by[1], z] as V3] : [[from[0], from[1], z] as V3]),
      [over[0], over[1], z],
      ...(x.behind ? [x.behind] : []),
      to,
    ];
    const routes = levels.map((k) => ({
      points: run(floor + WIRING.linkOver + k * WIRING.linkStep),
      rank: k,
    }));
    const link = { net: x.net, group: 'link', from: `pin ${x.pin}`, to: x.to, diameter, feed: false };
    if (!passes) return { ...link, routes };
    // Or under them, out across the far row past an end or at a pin with no
    // housing, nearest its end first.
    const inside = besideHousing(cfg, frames, from, diameter / 2, true);
    const [ix, iy] = point(inv, inside);
    const off = b.dupont.housing_mm[0] / 2 + diameter / 2 + WIRING.plugMargin;
    const out = -Math.sign(iy) * (b.row_spacing_mm / 2 + off);
    const far = Array.from({ length: 12 }, (_, i) => (x.pin <= 12 ? 13 + i : 1 + i));
    const ways = [
      pinAt(cfg, 1)[0] - off,
      pinAt(cfg, 12)[0] + off,
      ...far.filter((n) => !plugs.has(n)).map((n) => pinAt(cfg, n)[0]),
    ].sort((p, q) => plan(point(f, [p, out, 0])) - plan(point(f, [q, out, 0])));
    const rise = x.floor + WIRING.linkOver;
    const under = (gx: number, z: number): V3[] => {
      const [p, q, s] = [
        [ix, iy, z],
        [gx, iy, z],
        [gx, out, z],
      ].map((v) => point(f, v as V3));
      const zo = Math.max(s[2], rise);
      return [
        from,
        inside,
        p,
        q,
        s,
        ...(zo > s[2] ? [[s[0], s[1], zo] as V3] : []),
        [over[0], over[1], zo],
        ...(x.behind ? [x.behind] : []),
        to,
      ];
    };
    const low = b.board_mm[2] + Math.max(b.parts_mm[2], b.usb_mm[2]) + WIRING.linkOver;
    for (const [j, gx] of ways.entries())
      for (const k of levels)
        routes.push({
          points: under(gx, low + k * WIRING.linkStep),
          rank: levels.length + j + k,
        });
    return { ...link, routes };
  });
}

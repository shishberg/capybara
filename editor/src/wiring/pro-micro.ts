// The Pro Micro variant's hardware (controller.style "pro_micro"): an
// nRF52840 board in Pro Micro form factor and a TRRS jack on the bottom
// section, the board's USB-C port facing out of the hand's back end and the
// jack's barrel out of its inner side, and a reset switch standing against
// the back wall, its plunger out through it. Their pins, the parts, the
// plugs, the openings for the plugs and the plunger, the jack's collar and
// the cradles that hold them.
import type { CrossSection, Manifold, ManifoldToplevel, Mat4 } from 'manifold-3d';
import { Matrix4 } from 'three';
import { componentFrames, controllerStyle, point, type Config, type V3 } from '../geometry';
import { box, place } from '../manifold-util';
import type { Part } from '../parts';
import { WIRING, length, nets, type Wire } from './common';
import { touches, tubeOf } from './tubes';

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

/** The Pro Micro pin each net's feeds land on (pro_micro.pins). */
export function pinOf(cfg: Config, net: string) {
  const n = (cfg.pro_micro.pins as Record<string, number>)[net];
  if (n === undefined) throw Error(`pro_micro.pins has no pin for ${net}`);
  return n;
}

/** A net's pin for the wiring panel: its ribbon pin, or its Pro Micro pin and that pin's name (pro_micro.pinout). */
export function pinLabel(cfg: Config, net: string, ribbonPin: number) {
  return controllerStyle(cfg) === 'pro_micro' ? pinName(cfg, pinOf(cfg, net)) : `${ribbonPin}`;
}
/** Pro Micro pin n and its name, for the wiring panel. */
export const pinName = (cfg: Config, n: number) => `${n}, ${cfg.pro_micro.pinout[n - 1]}`;

/** Each net's hole on the Pro Micro, in world coordinates, keyed by the net's `pin` as the adapter's holes are. */
export function proMicroHoles(cfg: Config, frames = componentFrames(cfg)) {
  const out: Record<number, V3> = {};
  for (const net of nets(cfg))
    out[net.pin] = point(frames.pro_micro, pinAt(cfg, pinOf(cfg, net.name)));
  return out;
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

/** A reset switch leg's width and thickness (mm), for display: a gull-wing leg's flat end. */
const LEG = [0.7, 0.3];

/** A part `size` about `center` in frame f, turned so its z axis (a cylinder's) runs along f's x. */
const alongX = (f: Matrix4) => f.clone().multiply(new Matrix4().makeRotationY(Math.PI / 2));

/** The Pro Micro, the jack, both plugs and the reset switch, as parts for display and the checks. */
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
 * The reset switch's way, in world coordinates: a bore round its plunger,
 * grown by clearance_mm, from its body's face out through the back wall to
 * the outer face (`outline`, plan), chamfered CHAMFER at 45° there as the
 * plugs' openings are. The plunger stands proud of the face.
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
  const bore = r.plunger_mm[0] / 2 + r.clearance_mm;
  const d = toOutline(outline, point(f, [0, 0, 0]), point(f, [0, 0, -1]));
  if (d === undefined) return place(M.cylinder(10 + e, bore, bore, 48).translate([0, 0, -10]), f);
  const chamfer = Math.min(CHAMFER, d / 2);
  return place(
    M.union([
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
 * one behind; under the reset switch (on edge against the back wall) a
 * pedestal, and behind it a stop, twice as thick as the walls, which takes the
 * press, narrower than the body so that its legs are clear. Each reaches half
 * a millimetre into the floor.
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
  // The switch's frame has x up, so these run in x from under the floor's top.
  const r = cfg.reset;
  const [rx, ry, rz] = r.body_mm;
  const rc = r.clearance_mm;
  const low = -rx / 2 - r.standoff_mm - into;
  const upTo = (x: number, y: number, z: number[]) =>
    box(M, [x - low, y, z[1] - z[0]], [(x + low) / 2, 0, (z[0] + z[1]) / 2]);
  const reset = M.union([
    upTo(-rx / 2, ry, [0, rz]),
    upTo(rx / 2, ry - 2, [rz + rc, rz + rc + 2 * w]),
  ]);
  return M.union([
    place(board, frames.pro_micro),
    place(jack, frames.trrs),
    place(reset, frames.reset),
  ]);
}

/**
 * The link wires: the jack's (trrs.wires) and the reset switch's
 * (reset.wires), each in the order listed, from its Pro Micro pin straight up
 * to a level, across to over its lug and down onto it, or over a point
 * linkBehind behind its leg, down to it and onto the leg. The jack's
 * lowest level is linkOver above the board's parts or the jack's top,
 * whichever is higher, and the switch's above the board's parts or its top;
 * the next is linkStep above it, and so on. Placed in turn, each wire takes
 * the lowest that keeps it out of those before, so they stay as low as the
 * board and the jack (or the switch) let them; in the first order (the
 * listed one first) that leaves none touching, since a wire coming down onto
 * its lug can pass through one placed lower. A leg is come at from behind
 * since the other leg on its side stands over it.
 * On a pin a feed also lands on (`fed`), the link wire's end is holeShare
 * along the pin row toward the port, so the two sit side by side in the hole.
 */
export function linkWires(cfg: Config, frames: Record<string, Matrix4>, fed: Set<number>): Wire[] {
  const b = cfg.pro_micro;
  const f = frames.pro_micro;
  const parts = point(f, [0, 0, b.board_mm[2] + b.parts_mm[2]])[2];
  const trrs = cfg.trrs.wires.map((x) => ({
    name: x.name,
    net: `TRRS ${x.name}`,
    pin: x.pin,
    to: `TRRS ${x.lug}`,
    end: lugAt(cfg, frames, x.lug),
  }));
  const r = cfg.reset;
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
    };
  });
  const top = (frame: Matrix4, p: V3) => Math.max(parts, point(frame, p)[2]);
  return [
    ...links(cfg, frames, fed, trrs, top(frames.trrs, [0, 0, cfg.trrs.body_mm[2]])),
    ...links(cfg, frames, fed, reset, top(frames.reset, [r.body_mm[0] / 2, 0, 0])),
  ];
}

/** Link wires from Pro Micro pins to `end`s, their lowest level linkOver above `over` (linkWires). */
function links(
  cfg: Config,
  frames: Record<string, Matrix4>,
  fed: Set<number>,
  list: { name: string; net: string; pin: number; to: string; end: V3; behind?: V3 }[],
  over: number,
): Wire[] {
  const w = cfg.wiring;
  const f = frames.pro_micro;
  const toPort = point(f, [-WIRING.holeShare, 0, 0]).map((x, i) => x - f.elements[12 + i]);
  const runs = list.map((x) => {
    const power = x.name === 'VCC' || x.name === 'GND';
    const diameter = power ? w.power_wire_mm : w.signal_wire_mm;
    const at = point(f, pinAt(cfg, x.pin));
    const from: V3 = fed.has(x.pin)
      ? [at[0] + toPort[0], at[1] + toPort[1], at[2] + toPort[2]]
      : at;
    const to = x.end;
    const over = x.behind ?? to;
    const run = (z: number): V3[] => [
      from,
      [from[0], from[1], z],
      [over[0], over[1], z],
      ...(x.behind ? [x.behind] : []),
      to,
    ];
    return { x, diameter, run };
  });
  // Each wire's points, placed in `order`, and whether none touches another.
  const layOut = (order: number[]) => {
    const placed: ReturnType<typeof tubeOf>[] = [];
    const out: V3[][] = [];
    let clear = true;
    for (const i of order) {
      const { diameter, run } = runs[i];
      let points = run(over + WIRING.linkOver);
      let hit = true;
      for (let k = 0; k < runs.length && hit; k++) {
        points = run(over + WIRING.linkOver + k * WIRING.linkStep);
        hit = placed.some((t) => touches(t, tubeOf(points, diameter)));
      }
      clear &&= !hit;
      placed.push(tubeOf(points, diameter));
      out[i] = points;
    }
    return { out, clear };
  };
  const orders = (left: number[]): number[][] =>
    left.length
      ? left.flatMap((i) => orders(left.filter((j) => j !== i)).map((o) => [i, ...o]))
      : [[]];
  const all = orders(runs.map((_, i) => i));
  const { out } = all.map(layOut).find((l) => l.clear) ?? layOut(all[0]);
  return runs.map(({ x, diameter }, i) => ({
    net: x.net,
    group: 'link',
    from: `pin ${x.pin}`,
    to: x.to,
    points: out[i],
    diameter,
    length: length(out[i]) + 2 * w.end_allowance_mm,
    feed: false,
  }));
}

import { test } from 'node:test';
import assert from 'node:assert/strict';
import Module, { type Manifold } from 'manifold-3d';
import { Vector3 } from 'three';
import {
  defaults,
  clone,
  componentFrames,
  validateProject,
  capClearance,
  keycapEnvelope,
  keyGroups,
  tileUnderside,
  controllerStyle,
  point,
} from '../src/geometry';
import { hardware } from '../src/parts';
import { tilePocketDepth } from '../src/plates';
import { box, freeAfter, place } from '../src/manifold-util';
import { buildSolid, buildSolidAsync } from '../src/solid';
import { buildChassis, gluePosts, postAxes, SIZES as CHASSIS } from '../src/chassis';
import { crossings, holes, nets, wiring } from '../src/wiring';
import { WIRING } from '../src/wiring/common';
import { lugAt, mouths, pinAt, pinOf, plugWays } from '../src/wiring/pro-micro';
import { SIZES as CAPYBARA, capybara } from '../src/capybara';
import { solidOf } from './helpers';

const wasm = await Module();
wasm.setup();
const pos = (m: { elements: number[] }) => new Vector3(...m.elements.slice(12, 15));
const normal = (m: { elements: number[] }) => new Vector3(...m.elements.slice(8, 11));
test('column parameters move and tilt their keys, and invalid input is rejected', () => {
  const p = clone(defaults),
    before = componentFrames(p.config),
    mid = p.config.geometry.columns[2];
  mid.heights_mm[0] += 5;
  mid.offset_mm[1] += 2;
  const after = componentFrames(p.config);
  // Stagger moves the whole column; the raised top key also tilts its neighbours.
  for (const r of ['top', 'home', 'bottom'])
    assert(pos(after[`matrix_middle_${r}`]).distanceTo(pos(before[`matrix_middle_${r}`])) > 1.9, r);
  assert(normal(after.matrix_middle_home).distanceTo(normal(before.matrix_middle_home)) > 0.01);
  assert.deepEqual(after.matrix_ring_home.elements, before.matrix_ring_home.elements);
  mid.heights_mm[1] = NaN;
  assert.throws(() => validateProject(p), /finite/);
  assert.throws(() => validateProject({ version: 1 }), /version 2/);
});
test('a project saved with fields since removed, or without ones every build reads, still loads', () => {
  const p = clone(defaults) as any;
  p.config.units = 'mm and degrees';
  p.config.chassis.wall_mm = 2.4;
  p.config.switch.cutout_depth_overrides_mm = { matrix_inner_bottom: 14 };
  Object.assign(p.config.tile, { support_width_mm: 1.6, retaining_tie_y_mm: 0 });
  for (const k of ['seat_outer_mm', 'travel_mm', 'keycap_clearance_mm']) delete p.config.switch[k];
  p.config.chassis.base_thickness_mm = 2.5;
  delete p.config.chassis.skin_mm;
  validateProject(p);
  assert.deepEqual(p.config.switch.seat_outer_mm, defaults.config.switch.seat_outer_mm);
  assert.equal(p.config.switch.travel_mm, defaults.config.switch.travel_mm);
  assert.equal(p.config.switch.keycap_clearance_mm, defaults.config.switch.keycap_clearance_mm);
  assert.equal(p.config.chassis.skin_mm, 2.5);
  assert(!('base_thickness_mm' in p.config.chassis));
});
test("the tile pocket and the drawn parts measure the tile's parts from the board's top", () => {
  // A part's center_mm[2] is from the board's top (its switch side): the
  // socket sits on the underside, so the pocket reaches the plate's depth to
  // the board, the board, the socket and the parts' clearance below the plate top.
  const t = defaults.config.tile;
  const socket = t.components.find((p) => p.name === 'hotswap socket')!;
  const depth = t.plate_top_to_pcb_top_mm + t.size_mm[2] + socket.size_mm[2];
  assert(Math.abs(socket.center_mm[2] + t.size_mm[2] + socket.size_mm[2] / 2) < 1e-9);
  assert(Math.abs(tilePocketDepth(defaults.config) - depth - t.component_clearance_mm) < 1e-9);
  const drawn = hardware(defaults).filter(
    (p) => p.group === 'components' && p.name.startsWith('matrix_index_home: '),
  );
  assert.equal(drawn.length, t.components.length);
  const lowest = Math.min(...drawn.map((p) => p.center[2] - p.size[2] / 2));
  assert(Math.abs(lowest + depth) < 1e-9);
  // The measured tile: 5 mm to the board, 1.6 mm board, 1.9 mm socket, 0.3 mm clearance.
  assert(Math.abs(tilePocketDepth(defaults.config) - 8.8) < 1e-9);
});
test('the glue posts hold the tile from outside it, along its rib, and clear its pads and holes', () => {
  const cfg = defaults.config;
  const t = cfg.tile;
  const half = t.size_mm.map((x) => x / 2);
  const top = -t.plate_top_to_pcb_top_mm;
  const keep = t.pads.ring_mm / 2;
  const holes = t.pads.list.filter((h) => h.hole);
  const edgePads = t.pads.list.filter((h) => !h.hole);
  const e = 1e-9;
  // Every finger key's posts face along y (north and south), along its column.
  const axes = postAxes(cfg, componentFrames(cfg));
  for (const [n, a] of Object.entries(axes)) if (n.startsWith('matrix_')) assert.equal(a, 1, n);
  for (const axis of [0, 1]) {
    const across = 1 - axis;
    const g = gluePosts(cfg, axis);
    // A corner post stands in its notch, postGap clear, and is at least postMin across.
    assert(Math.abs(g.radius - (t.corner_notch_radius_mm - CHASSIS.postGap)) < e);
    assert(2 * g.radius >= CHASSIS.postMin);
    assert(g.reach[0] - (half[across] - g.radius) >= CHASSIS.postMin - e);
    assert(g.boxes.length > 0 && g.glue.length > 0);
    for (const b of [...g.boxes, ...g.legs.flat()]) {
      const lo = [0, 1, 2].map((k) => b.center[k] - b.size[k] / 2);
      const hi = [0, 1, 2].map((k) => b.center[k] + b.size[k] / 2);
      const al = [Math.abs(lo[axis]), Math.abs(hi[axis])].sort((p, q) => p - q);
      // No post past the plate's side, across the rib.
      assert(Math.max(Math.abs(lo[across]), Math.abs(hi[across])) <= g.reach[0] + e);
      if (lo[2] < top - e) {
        // Below the tile's top: a leg, outside the tile's edge, postMin thick,
        // and clear of the edge pads by more than a wire's width.
        assert(al[0] >= half[axis] + CHASSIS.postGap - e && al[1] - al[0] >= CHASSIS.postMin - e);
        const from = Math.min(Math.abs(lo[across]), Math.abs(hi[across]));
        for (const pad of edgePads)
          if (Math.abs(pad.at_mm[axis]) > half[axis] - 2)
            assert(from - (Math.abs(pad.at_mm[across]) + t.pads.size_mm[0] / 2) >= 0.9, pad.name);
      } else {
        // Above it: a shelf, on its leg, over the tile's top edge, outside the
        // switch seat and clear of every hole's ring.
        assert(lo[2] > top);
        assert(al[0] >= cfg.switch.seat_outer_mm[axis] / 2);
        for (const h of holes) {
          const nearest = [0, 1].map((k) => Math.min(Math.max(h.at_mm[k], lo[k]), hi[k]));
          assert(Math.hypot(nearest[0] - h.at_mm[0], nearest[1] - h.at_mm[1]) > keep, h.name);
        }
      }
    }
    // The shelves go glueInto up into the plate, stopping postEdgeIn inside
    // its edge; the legs, fitted to nothing, go as far up into it.
    for (const b of g.boxes) {
      assert(Math.abs(Math.abs(b.center[axis]) + b.size[axis] / 2) <= g.edge + e);
      assert(Math.abs(b.center[2] + b.size[2] / 2 - g.top) < e);
    }
    for (const b of g.legs.flat()) assert(Math.abs(b.center[2] + b.size[2] / 2 - g.top) < e);
    // A shelf on each edge.
    for (const s of [-1, 1]) assert(g.boxes.some((b) => Math.sign(b.center[axis]) === s));
    // Fitted to what is over them, each edge's legs reach up to its highest
    // and glueInto into it, postEdgeIn inside the plate's sides; the rest is
    // as it was.
    const flat = (h: number) => ({
      al: [g.inner, g.outer],
      ac: [-1, 1],
      z: [
        [h, h],
        [h, h],
      ],
    });
    const fitted = gluePosts(cfg, axis, { grow: [0, 0], over: [flat(-3), flat(-2.5)] });
    fitted.legs.forEach((legs, i) =>
      legs.forEach((b) => {
        assert(Math.abs(b.center[2] + b.size[2] / 2 - ([-3, -2.5][i] + CHASSIS.glueInto)) < e);
        const out = Math.abs(b.center[across]) + b.size[across] / 2;
        assert(Math.abs(out - (g.reach[0] - CHASSIS.postEdgeIn)) < e);
      }),
    );
    assert.deepEqual(fitted.boxes, g.boxes);
    assert.deepEqual(fitted.glue, g.glue);
  }
});
test('a project on the provisional tile loads with the measured one, and its nets with its holes', () => {
  const p = clone(defaults) as any;
  const c = p.config;
  c.schema = 5;
  c.tile.provisional = true;
  c.tile.size_mm = [19, 19, 1.6];
  c.tile.pads = { size_mm: [1.2, 1.8], list: [{ name: 'DI', at_mm: [7, -8.6] }] };
  const old: Record<string, string[]> = { DATA: ['DI', 'DO'], '+5V': ['+', '+'], GND: ['G', 'G'] };
  for (const n of c.wiring.nets) if (old[n.name]) n.pads = old[n.name];
  validateProject(p);
  assert.deepEqual(p.config, defaults.config);
});
test('shared per-key helpers', () => {
  const c = defaults.config;
  assert.equal(capClearance(c, 'thumb_home'), c.switch.keycap_clearance_overrides_mm.thumb_home);
  assert.equal(capClearance(c, 'matrix_index_home'), c.switch.keycap_clearance_mm);
  assert.equal(tileUnderside(c), -(c.tile.plate_top_to_pcb_top_mm + c.tile.size_mm[2]));
  const g = keyGroups(c);
  assert.deepEqual(
    [...g.fingers, ...g.thumbs, ...g.extra].sort(),
    Object.keys(componentFrames(c))
      .filter((n) => n !== 'adapter')
      .sort(),
  );
});
test('thumb clusters fan on an arc and tilt into a well', () => {
  // Swung in places each thumb key itself, with no arc; here its row is put
  // back on an arc of 11° steps with a 12° well, each key at its place on it,
  // and the extra keys at theirs on their own cluster's arc.
  const p = clone(defaults),
    th = p.config.geometry.thumb;
  th.arc = { ...th.arc, step_deg: 11, well_deg: 12 };
  for (const k of th.keys) {
    k.offset_mm = [0, 0, 0];
    k.rotation_deg = k.name === 'home' ? [0, 0, -90] : [0, 0, 0];
  }
  for (const k of (p.config.geometry as { thumb_extra: typeof th }).thumb_extra.keys) {
    k.offset_mm = [0, 0, 0];
    k.rotation_deg = [0, 0, 0];
  }
  const f = componentFrames(p.config);
  const far = pos(f.thumb_far),
    home = pos(f.thumb_home),
    near = pos(f.thumb_near);
  assert(Math.abs(far.distanceTo(home) - near.distanceTo(home)) < 1e-6);
  assert(
    Math.abs(
      far.distanceTo(home) -
        (2 * th.arc.radius_mm * Math.sin((th.arc.step_deg * Math.PI) / 360)) /
          Math.cos((th.arc.well_deg * Math.PI) / 360),
    ) < 0.5,
  );
  // Each outer key tilts well_deg toward the middle one.
  for (const n of ['thumb_far', 'thumb_near']) {
    const a = (normal(f[n]).angleTo(normal(f.thumb_home)) * 180) / Math.PI;
    assert(Math.abs(a - th.arc.well_deg) < 0.01, n);
  }
  // The extra pair share the cluster's tilt.
  assert(normal(f.thumb_x1).angleTo(normal(f.thumb_x2)) < 1e-6);
  const none = clone(defaults);
  delete (none.config.geometry as { thumb_extra?: unknown }).thumb_extra;
  assert(!componentFrames(none.config).thumb_x1);
});
const basePieces = (cfg: typeof defaults.config) =>
  freeAfter(wasm, () => {
    const pieces = buildChassis(wasm, cfg, componentFrames(cfg)).base.decompose();
    const big = pieces.filter((p) => p.volume() > 0.5).length;
    pieces.forEach((p) => p.delete());
    return big;
  });
test('a thicker skin builds the frame in one piece, the adapter mount reaching the floor', () => {
  // The chassis alone (the checks are the default's, pinned below).
  const p = clone(defaults);
  p.config.chassis.skin_mm = 3;
  const [body, base] = freeAfter(wasm, () => {
    const built = buildChassis(wasm, p.config, componentFrames(p.config));
    return [built.body, built.base].map((m) => {
      const pieces = m.decompose(),
        big = pieces.filter((x) => x.volume() > 0.5).length;
      pieces.forEach((x) => x.delete());
      return big;
    });
  });
  assert.equal(body, 1);
  assert.equal(base, 1);
  assert.throws(
    () =>
      validateProject({
        ...clone(defaults),
        config: { ...p.config, chassis: { ...p.config.chassis, skin_mm: 1.5 } },
      }),
    /skin_mm/,
  );
});
test("a plate margin past the glue posts' legs still builds", () => {
  // The plate's edge then lies past a leg's outer face, or on it: the grid
  // its top is shaped over must still run in order, with no cell of no width.
  const p = clone(defaults);
  p.config.chassis.plate_margin_mm = 2.5;
  const body = freeAfter(wasm, () =>
    buildChassis(wasm, p.config, componentFrames(p.config)).body.volume(),
  );
  assert(body > 0);
});
test('the default (Swung in) Capybara builds one piece and passes every check', () => {
  const r = buildSolid(wasm, clone(defaults)).report,
    failing = (xs: { name: string; passed: boolean }[]) =>
      xs.filter((x) => !x.passed).map((x) => x.name);
  assert.equal(r.pieces.length, 1);
  assert.equal(r.footprint.length, 1);
  assert.equal(r.seats.length, 20);
  assert.deepEqual(failing(r.seats), []);
  assert.deepEqual(failing(r.keycaps), []);
  assert.deepEqual(r.roomCuts, []);
  assert(r.openings.length > 0);
  assert.deepEqual(failing(r.openings), []);
  assert.deepEqual(r.hardware, []);
  assert.deepEqual(r.crossings, []);
  assert.deepEqual(
    r.capGaps.filter((g) => !(g.gap > 0)).map((g) => g.between),
    [],
  );
  assert.equal(r.passed, true);
});
test('the default bottom section is one piece, the adapter mount on its floor', () => {
  assert.equal(basePieces(defaults.config), 1);
});
// The Pro Micro variant: an nRF52840 board and a TRRS jack in each hand, in
// place of the FFC adapter and its ribbon to the pod.
const proMicro = () => {
  const p = clone(defaults);
  p.config.controller.style = 'pro_micro';
  return p;
};
test('the Capybara on a Pro Micro builds one piece and passes every check', () => {
  // As the default: the board, the jack and both plugs clear the chassis,
  // and no wire runs into another or into the chassis.
  const r = buildSolid(wasm, proMicro()).report,
    failing = (xs: { name: string; passed: boolean }[]) =>
      xs.filter((x) => !x.passed).map((x) => x.name);
  assert.equal(r.pieces.length, 1);
  assert.equal(r.footprint.length, 1);
  assert.deepEqual(failing(r.seats), []);
  assert.deepEqual(failing(r.keycaps), []);
  assert.deepEqual(r.roomCuts, []);
  assert.deepEqual(failing(r.openings), []);
  assert.deepEqual(r.hardware, []);
  assert.deepEqual(r.crossings, []);
  assert.equal(r.passed, true);
});
test('the Pro Micro bottom section is one piece, the cradles on its floor', () => {
  assert.equal(basePieces(proMicro().config), 1);
});
test("on a Pro Micro the wiring lands each net on its pin, and the jack's links on theirs", () => {
  const cfg = proMicro().config;
  const frames = componentFrames(cfg);
  const w = wiring(cfg, frames);
  const hole = holes(cfg, frames);
  const near = (a: number[], b: number[], by = 0.51) =>
    Math.hypot(...a.map((x, i) => x - b[i])) < by;
  // Every net's feeds end on the Pro Micro pin pro_micro.pins gives it.
  for (const net of nets(cfg)) {
    const at = point(frames.pro_micro, pinAt(cfg, pinOf(cfg, net.name)));
    assert.deepEqual(hole[net.pin], at, net.name);
    const feeds = w.wires.filter((x) => x.net === net.name && x.feed);
    assert(feeds.length > 0, net.name);
    for (const f of feeds) assert(near(f.points.at(-1)!, at) || near(f.points[0], at), net.name);
  }
  // Each of the jack's wires runs from its pin to its lug, no higher than
  // its level over the jack's top (the jack stands up into the loom, so that
  // its plug comes in over the rail). On a pin a net's feeds land on too, it
  // starts beside them in the hole.
  const fed = new Set(Object.values(cfg.pro_micro.pins));
  const links = w.wires.filter((x) => x.group === 'link');
  assert.equal(links.length, cfg.trrs.wires.length);
  const top = point(frames.trrs, [0, 0, cfg.trrs.body_mm[2]])[2];
  const highest = top + WIRING.linkOver + (links.length - 1) * WIRING.linkStep;
  for (const t of cfg.trrs.wires) {
    const l = links.find((x) => x.net === `TRRS ${t.name}`)!;
    const share = fed.has(t.pin) ? WIRING.holeShare : 0;
    assert(near(l.points[0], point(frames.pro_micro, pinAt(cfg, t.pin)), share + 0.51), t.name);
    assert(near(l.points.at(-1)!, lugAt(cfg, frames, t.lug)), t.name);
    assert(Math.max(...l.points.map((p) => p[2])) <= highest + 1e-9, t.name);
  }
  // The feeds keep out of the jack: none comes within its radius of the body.
  const [jx, jy, jz] = cfg.trrs.body_mm;
  const inv = frames.trrs.clone().invert();
  for (const f of w.wires.filter((x) => x.feed))
    for (let i = 1; i < f.points.length; i++)
      for (let s = 0; s <= 1; s += 0.02) {
        const q = new Vector3(...f.points[i - 1])
          .lerp(new Vector3(...f.points[i]), s)
          .applyMatrix4(inv);
        const out = Math.hypot(
          Math.max(0, Math.abs(q.x) - jx / 2),
          Math.max(0, Math.abs(q.y) - jy / 2),
          Math.max(0, q.z - jz, -q.z),
        );
        assert(out > f.diameter / 2, `${f.net} ${f.from} to ${f.to} into the jack`);
      }
  assert.deepEqual(crossings(w.wires), []);
  // The wiring panel names each net's pin by its number and its GPIO.
  assert.equal(w.nets.find((n) => n.name === 'DATA')!.label, '5, P0.17');
});
test("on a Pro Micro the walls stand as on the default, the jack's plug in through one, over the rail", () => {
  // The USB-C plug runs out the back, through the rail and the rib over it;
  // the jack's comes in through the inner front web's wishbone, filled in
  // round it.
  const walls = (cfg: typeof defaults.config) => {
    const frames = componentFrames(cfg);
    return capybara(wasm, cfg, frames, wiring(cfg, frames).wires)
      .parts()
      .filter((x) => x.name.startsWith('wall '))
      .map((x) => x.solid);
  };
  const cfg = proMicro().config;
  const mine = walls(cfg);
  assert.equal(mine.length, walls(defaults.config).length);
  const frames = componentFrames(cfg);
  const ways = plugWays(wasm, cfg, frames, CHASSIS.notchLength);
  assert(
    wasm.Manifold.union(mine).intersect(ways).volume() > 50,
    'a wall filled in round the jack',
  );
  // The jack's plug way clears the rail's top.
  const m = mouths(cfg).trrs;
  const mouth = point(frames.trrs, [m.x, 0, m.z]);
  const r = cfg.trrs.plug_mm[0] / 2 + cfg.trrs.clearance_mm;
  assert(mouth[2] - r > CAPYBARA.railHeight, `${mouth[2] - r} over the rail`);
});
test('on a Pro Micro the wall grips the USB-C receptacle and the jack barrel', () => {
  // The chassis keeps out of each port's nose but closes round it: a ring a
  // millimetre thick round the nose, outside the grip, is in the wall for
  // over a millimetre of the receptacle's length and nearly all the barrel's.
  const M = wasm.Manifold;
  const cfg = proMicro().config;
  const frames = componentFrames(cfg);
  const body = buildChassis(wasm, cfg, frames).body;
  const m = mouths(cfg);
  const [ux, uy, uz] = cfg.pro_micro.usb_mm;
  const bz = cfg.pro_micro.board_mm[2];
  const shell = (g: number) =>
    place(
      box(M, [ux, uy + 2 * g, uz + 2 * g], [m.usb.x + ux / 2, 0, bz + uz / 2]),
      frames.pro_micro,
    );
  const [bl, bd] = cfg.trrs.barrel_mm;
  const barrel = (g: number) =>
    place(
      M.cylinder(bl, bd / 2 + g, bd / 2 + g, 48)
        .rotate([0, 90, 0])
        .translate([m.trrs.x, 0, m.trrs.z]),
      frames.trrs,
    );
  // How many millimetres of the nose's length the ring is in the wall for.
  const gripped = (nose: (g: number) => Manifold, length: number) => {
    assert(body.intersect(nose(0)).volume() < 1e-6, 'clear of the nose');
    const ring = nose(1).subtract(nose(0.2));
    return (body.intersect(ring).volume() / ring.volume()) * length;
  };
  const usb = gripped(shell, ux);
  assert(usb > 1, `the receptacle gripped for ${usb} mm`);
  const jack = gripped(barrel, bl);
  assert(jack > 0.9 * bl, `the barrel gripped for ${jack} mm`);
});
test('a project with the Pro Micro and jack placed as before schema 8 takes their new places and pins', () => {
  const p = clone(defaults);
  const c = p.config as Record<string, any>;
  c.schema = 7;
  c.pro_micro.position_mm = [-21, 17];
  Object.assign(c.pro_micro.pins, { RT: 11, RH: 12, RB: 17, RX: 18 });
  Object.assign(c.pro_micro.pins, { C0: 6, C1: 7, C2: 8, C3: 9, C4: 10 });
  c.trrs.position_mm = [-42.3, 14.4];
  c.trrs.wires.find((w: { name: string }) => w.name === 'GND').pin = 3;
  validateProject(p);
  assert.deepEqual(p.config, defaults.config);
});
test('a project with the Pro Micro and jack placed as before schema 7 takes their new places', () => {
  const p = clone(defaults);
  const c = p.config as Record<string, any>;
  c.schema = 6;
  Object.assign(c.pro_micro, { position_mm: [-29.5, 9], rotation_deg: 0 });
  Object.assign(c.trrs, { position_mm: [-39.2, -6], standoff_mm: 0 });
  validateProject(p);
  assert.deepEqual(p.config, defaults.config);
});
test('a project saved before the Pro Micro variant loads on the FFC adapter', () => {
  const p = clone(defaults);
  const c = p.config as Record<string, any>;
  delete c.controller;
  delete c.pro_micro;
  delete c.trrs;
  validateProject(p);
  assert.deepEqual(p.config, defaults.config);
  assert.equal(controllerStyle(p.config), 'ffc');
});
test('the checker reports keycap collisions', () => {
  // Keycaps that press 2 mm into the plate must fail, with matching highlight geometry.
  const low = clone(defaults);
  low.config.switch.keycap_bottom_above_plate_mm = low.config.switch.travel_mm - 2;
  const r = buildSolid(wasm, low),
    home = r.report.keycaps.find((k) => k.name === 'thumb_home')!;
  assert.deepEqual(home.size, [28, 18.5, 11]);
  assert.equal(home.margin, 2.5);
  assert(home.swept > 0.05);
  assert.equal(home.passed, false);
  assert.equal(r.report.passed, false);
  const h = r.highlights.find((h) => h.name === 'thumb_home' && h.kind === 'travel')!;
  assert(h, 'Missing collision geometry');
  const solid = solidOf(wasm, h.mesh);
  try {
    assert.equal(solid.status(), 'NoError');
    assert(Math.abs(solid.volume() - home.swept) < 0.01);
  } finally {
    solid.delete();
  }
});
test('the checker reports chassis built where a keycap goes', () => {
  // The thumb cluster moved 5 mm toward the fingers: the middle bottom key's
  // room cuts into the chassis (Swung in's own room cut is at the pinky
  // bottom key).
  const close = clone(defaults);
  close.config.geometry.thumb.position_mm[1] += 5;
  const r = buildSolid(wasm, close);
  const cut = r.report.roomCuts.find((c) => c.name === 'matrix_middle_bottom');
  assert(cut && cut.volume > 10);
  assert.equal(r.report.passed, false);
  assert(
    r.highlights.some((h) => h.kind === 'room' && h.name === 'matrix_middle_bottom keycap room'),
  );
});
test("the wiring joins each net's pads and adapter hole, for a 4 × 5 matrix", () => {
  const cfg = defaults.config;
  const frames = componentFrames(cfg);
  const w = wiring(cfg, frames);
  const keys = Object.keys(frames).filter((n) => n.startsWith('matrix_') || n.startsWith('thumb_'));
  assert.equal(keys.length, 20);
  // Every key sits on one of four rows and one of five columns, each pair once.
  assert.equal(new Set(w.matrix.map((m) => m.row)).size, 4);
  assert.equal(new Set(w.matrix.map((m) => m.column)).size, 5);
  assert.equal(new Set(w.matrix.map((m) => `${m.row} ${m.column}`)).size, 20);
  const hole = holes(cfg, frames);
  // Two wires on one pad or hole sit side by side on it, up to 0.5 mm off its centre.
  const near = (a: number[], b: number[]) => Math.hypot(...a.map((x, i) => x - b[i])) < 0.51;
  for (const net of nets(cfg)) {
    const wires = w.wires.filter((x) => x.net === net.name);
    // Each pad named for the net, and the hole, is an end of some wire.
    const ends = wires.flatMap((x) => [x.points[0], x.points.at(-1)!]);
    const pads = w.pads.filter((p) => net.pads.includes(p.name));
    const used = pads.filter((p) => ends.some((e) => near(e, p.at)));
    const perKey = new Set(used.map((p) => p.key));
    assert.equal(perKey.size, net.chains ? net.chains.flat().length : 20, net.name);
    assert(
      ends.some((e) => near(e, hole[net.pin])),
      `${net.name} reaches pin ${net.pin}`,
    );
    // A tree over the keys and the hole: a link between neighbours in each chain, and a feed per chain.
    assert.equal(wires.length, perKey.size, net.name);
    assert.equal(wires.filter((x) => x.feed).length, net.chains?.length ?? 1, net.name);
  }
  assert.equal(w.wires.length, 100);
  // One wire to a tile's hole or pad: two don't fit a hole.
  const ends = w.wires.flatMap((x) => [x.points[0], x.points.at(-1)!]);
  for (const p of w.pads)
    assert(ends.filter((e) => near(e, p.at)).length <= 1, `${p.key} ${p.name} at ${p.xy}`);
  const crossed = (w: ReturnType<typeof wiring>) =>
    crossings(w.wires).map(
      ([a, b]) =>
        `${w.wires[a].net} ${w.wires[a].from}-${w.wires[a].to} × ${w.wires[b].net} ${w.wires[b].from}-${w.wires[b].to}`,
    );
  // On Swung in (the default) no wire runs into another.
  assert.deepEqual(crossed(w), []);
  // Every wire's underside stays the floor's skin above the base: its
  // centreline at least skin_mm plus its radius above z = 0.
  for (const x of w.wires)
    for (const p of x.points)
      assert(
        p[2] >= cfg.chassis.skin_mm + x.diameter / 2 - 1e-9,
        `${x.net} ${x.from}-${x.to} at z ${p[2].toFixed(3)}`,
      );
  assert.equal(
    w.nets.reduce((s, n) => s + n.joints, 0),
    200,
  );
});
test('a project saved before the wiring loads with the default adapter, ribbon and wiring', () => {
  const p = clone(defaults);
  const c = p.config as Record<string, any>;
  delete c.schema;
  delete c.ribbon;
  delete c.wiring;
  delete c.tile.pads;
  c.adapter = { position_mm: [0, 0], rotation_deg: 0, board_mm: [30, 16, 1.6] };
  validateProject(p);
  assert.deepEqual(p.config, defaults.config);
});
test('objects made with `new` inside freeAfter are freed too', () => {
  type Freed = { isDeleted(): boolean };
  let m!: Freed, c!: Freed;
  freeAfter(wasm, () => {
    const cube = wasm.Manifold.cube([1, 1, 1]).getMesh();
    m = new wasm.Manifold(cube) as unknown as Freed;
    c = new wasm.CrossSection([
      [
        [0, 0],
        [1, 0],
        [0, 1],
      ],
    ]) as unknown as Freed;
    assert(!m.isDeleted() && !c.isDeleted());
  });
  assert(m.isDeleted() && c.isDeleted());
});
test('a failed wire router rejects the build, and the next build still runs', async () => {
  await assert.rejects(
    buildSolidAsync(wasm, clone(defaults), () => Promise.reject(Error('router crashed'))),
    /router crashed/,
  );
  const r = await buildSolidAsync(wasm, clone(defaults), async (c) => wiring(c));
  assert.equal(r.report.wiring.wires, 100);
  assert.equal(r.report.pieces.length, 1);
});

test('keycapEnvelope: the measured cap grown by its clearance, down to where it is pressed', () => {
  const c = defaults.config,
    close = (a: number[], b: number[]) => a.forEach((x, i) => assert(Math.abs(x - b[i]) < 1e-9));
  const t = keycapEnvelope(c, 'thumb_home');
  close(t.base, [33, 23.5]);
  close(t.top, [28.5, 19]);
  close([t.z0, t.height, t.floor], [6, 13.5, 2.5]);
  const m = keycapEnvelope(c, 'matrix_index_home');
  close(m.base, [19.1, 19.1]);
  close(m.top, [14.6, 14.6]);
  close([m.z0, m.height, m.floor], [6, 11.3, 2.5]);
  const bare = keycapEnvelope(c, 'matrix_index_home', { clearance: 0 });
  close([...bare.base, ...bare.top, bare.height], [18.5, 18.5, 14, 14, 11]);
  const deep = clone(defaults).config;
  deep.switch.travel_mm = 8;
  assert.equal(keycapEnvelope(deep, 'matrix_index_home').floor, -2);
  assert.equal(keycapEnvelope(deep, 'matrix_index_home', { clampFloor: true }).floor, 0);
});
test("the chassis is the same when the thumb row's end keys are renamed", () => {
  const p = clone(defaults),
    names = { far: 'left', near: 'right' } as Record<string, string>;
  for (const k of p.config.geometry.thumb.keys) k.name = names[k.name] ?? k.name;
  validateProject(p);
  const volume = (c: typeof p.config) =>
    freeAfter(wasm, () => buildChassis(wasm, c, componentFrames(c)).body.volume());
  assert.equal(volume(p.config), volume(defaults.config));
});

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
  isKey,
  point,
} from '../src/geometry';
import { hardware } from '../src/parts';
import { tilePocketDepth } from '../src/plates';
import { box, freeAfter, place } from '../src/manifold-util';
import { buildSolid, buildSolidAsync } from '../src/solid';
import { seatSwitches, sleeveBottom, switchHole } from '../src/seats';
import { buildChassis, SIZES as CHASSIS } from '../src/chassis';
import { crossings, holes, nets, wiring } from '../src/wiring';
import { WIRING, pinOf } from '../src/wiring/common';
import { legAt, lugAt, mouths, pinAt } from '../src/wiring/pro-micro';
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
    Object.keys(componentFrames(c)).filter(isKey).sort(),
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
test('a thicker skin builds the frame in one piece, the cradles reaching the floor', () => {
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
test('under each plate the sleeve fills round the switch body, over the tile, to just above it', () => {
  freeAfter(wasm, () => {
    const cfg = clone(defaults).config;
    const frames = componentFrames(cfg);
    const m = frames.matrix_index_home;
    const seated = seatSwitches(wasm.Manifold, cfg, buildChassis(wasm, cfg, frames).body, [m]);
    const cut = seated.body.subtract(wasm.Manifold.union([...seated.reliefs, ...seated.openings]));
    const filled = (x: number, y: number, z: number) =>
      cut.intersect(place(box(wasm.Manifold, [0.05, 0.05, 0.05], [x, y, z]), m)).volume() > 1e-6;
    const bottom = sleeveBottom(cfg);
    const half = cfg.tile.size_mm[0] / 2;
    const hole = switchHole(cfg)[0] / 2;
    assert(Math.abs(bottom - (-cfg.tile.plate_top_to_pcb_top_mm + 0.4)) < 1e-9);
    // Round the hole beside it, out to the tile's edge and in its corners, down to the sleeve's underside.
    for (const [x, y] of [
      [hole + 0.1, 0],
      [-half + 0.1, 0],
      [half - 0.1, half - 0.1],
    ])
      assert(filled(x, y, bottom + 0.05), `${x}, ${y}`);
    // Not below it, nor in the hole or the clip reliefs.
    assert(!filled(hole + 0.1, 0, bottom - 0.05));
    assert(!filled(hole - 0.1, 0, bottom + 0.05));
    assert(!filled(0, hole + 0.1, bottom + 0.05));
    assert(!filled(0, hole + 0.1, -2));
  });
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
test('the default bottom section is one piece, the cradles on its floor', () => {
  assert.equal(basePieces(defaults.config), 1);
});
test("the wiring lands each net on its pin, and the jack's links on theirs", () => {
  const cfg = defaults.config;
  const frames = componentFrames(cfg);
  const w = wiring(cfg, frames);
  const hole = holes(cfg, frames);
  const near = (a: number[], b: number[], by = 0.51) =>
    Math.hypot(...a.map((x, i) => x - b[i])) < by;
  // Every net's feeds end on the top of the Dupont housing on the Pro Micro
  // pin pro_micro.pins gives it.
  const { spacer_mm, housing_mm } = cfg.pro_micro.dupont;
  for (const net of nets(cfg)) {
    const [x, y, z] = pinAt(cfg, pinOf(cfg, net.name));
    const at = point(frames.pro_micro, [x, y, z + spacer_mm + housing_mm[2]]);
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
  const links = w.wires.filter((x) => x.group === 'link' && x.net.startsWith('TRRS '));
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
test("the walls stand clear of the jack's plug, over the rail", () => {
  // The USB-C plug runs out the back, through the rail and the rib over it;
  // the jack's comes in under the wishbone nearest the back, which forks
  // over it (its collar fills the opening and grips the barrel there).
  const walls = (cfg: typeof defaults.config) => {
    const frames = componentFrames(cfg);
    return capybara(wasm, cfg, frames, wiring(cfg, frames).wires)
      .parts()
      .filter((x) => x.name.startsWith('wall '))
      .map((x) => x.solid);
  };
  const cfg = defaults.config;
  const mine = walls(cfg);
  const frames = componentFrames(cfg);
  const m = mouths(cfg).trrs;
  const r = cfg.trrs.plug_mm[0] / 2 + cfg.trrs.clearance_mm;
  const way = place(
    wasm.Manifold.cylinder(CHASSIS.notchLength, r, r, 48)
      .rotate([0, -90, 0])
      .translate([m.x, 0, m.z]),
    frames.trrs,
  );
  assert(wasm.Manifold.union(mine).intersect(way).volume() < 1e-6, "no wall in the jack's way");
  // The jack's plug way clears the rail's top.
  const mouth = point(frames.trrs, [m.x, 0, m.z]);
  assert(mouth[2] - r > CAPYBARA.railHeight, `${mouth[2] - r} over the rail`);
});
test('the wall grips the USB-C receptacle and the jack barrel', () => {
  // The chassis keeps out of each port's nose but closes round it: a ring a
  // millimetre thick round the nose, outside the grip, is in the wall for
  // over a millimetre of the receptacle's length and nearly all the barrel's.
  const M = wasm.Manifold;
  const cfg = defaults.config;
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
  // Over the plug, the wishbone's opening is filled: the wall is solid from
  // past the chamfer up 5 mm, in the wall from the mouth out half a millimetre.
  const r = cfg.trrs.plug_mm[0] / 2 + cfg.trrs.clearance_mm;
  const over = place(
    box(M, [0.5, 2, 5], [m.trrs.x - 0.25, 0, m.trrs.z + r + 1.5 + 2.5]),
    frames.trrs,
  );
  const filled = body.intersect(over).volume() / over.volume();
  assert(filled > 0.99, `the wall over the plug ${filled} filled`);
});
test('the reset switch sits in a pocket in the back wall, its plunger out through it', () => {
  // The switch and its plunger clear the chassis, the body held in its pocket
  // by the wall over and under it and the skin in front, with a stop behind
  // it; its tip stands proud of everything round it, so a fingertip reaches
  // it. Its two link wires run from RST and the GND
  // beside it to two diagonal legs, coming onto them from behind.
  const M = wasm.Manifold;
  const cfg = defaults.config;
  const r = cfg.reset;
  const frames = componentFrames(cfg);
  const { body, base } = buildChassis(wasm, cfg, frames);
  const chassis = body.add(base);
  const [rx, ry, rz] = r.body_mm;
  const [pd, pp] = r.plunger_mm;
  const inSwitch = (m: Manifold) => place(m, frames.reset);
  // Along the plunger, from z0 to z1 in the switch's frame, radius r0 to r1.
  const along = (z0: number, z1: number, r0: number, r1?: number) => {
    const c = (r: number) => M.cylinder(z1 - z0, r, r, 48);
    return inSwitch((r1 ? c(r0).subtract(c(r1)) : c(r0)).translate([0, 0, z0]));
  };
  const switchBody = inSwitch(box(M, [rx, ry, rz], [0, 0, rz / 2]));
  assert(
    chassis.intersect(along(-pp, 0, pd / 2).add(switchBody)).volume() < 1e-6,
    'the switch clears the chassis',
  );
  const solid = (m: Manifold, part: Manifold, what: string) =>
    assert(part.intersect(m).volume() / m.volume() > 0.99, what);
  const c = r.clearance_mm;
  for (const s of [-1, 1])
    solid(
      inSwitch(box(M, [0.2, ry, 1.5], [s * (rx / 2 + c + 0.2), 0, 0.75])),
      body,
      `the wall holds the body ${s < 0 ? 'under' : 'over'} it`,
    );
  const bore = pd / 2 + c;
  solid(along(-0.4, -0.1, rx / 2, bore + 0.3), body, 'the skin stands in front of it');
  solid(inSwitch(box(M, [rx / 2, 2, 0.2], [0, 0, rz + c + 0.2])), base, 'a stop stands behind it');
  assert(
    chassis.intersect(along(-pp - 5, -pp + 0.4, 4)).volume() < 1e-6,
    'the tip stands 0.4 mm proud of everything round it',
  );
  const w = wiring(cfg, frames);
  assert.equal(r.wires.length, 2);
  for (const x of r.wires) {
    const l = w.wires.find((y) => y.net === `Reset ${x.name}`)!;
    assert.equal(cfg.pro_micro.pinout[x.pin - 1], x.name);
    assert.deepEqual(l.points[0], point(frames.pro_micro, pinAt(cfg, x.pin)));
    const leg = legAt(cfg, frames, x.leg);
    assert.deepEqual(l.points.at(-1), leg);
    const behind = l.points.at(-2)!;
    const back = new Vector3(...behind).sub(new Vector3(...leg));
    const into = new Vector3().setFromMatrixColumn(frames.reset, 2);
    assert(Math.abs(back.dot(into) - WIRING.linkBehind) < 1e-9, `${x.name} comes from behind`);
    assert(w.nets.some((n) => n.name === `Reset ${x.name}` && n.wires === 1));
  }
  // Diagonal legs, which a press joins whichever pairs the switch always joins:
  // straight across (1 and 3, 2 and 4) or along a side (1 and 2, 3 and 4).
  const [a, b] = r.wires.map((x) => x.leg);
  assert(a <= 2 !== b <= 2 && a % 2 !== b % 2, `legs ${a} and ${b} are diagonal`);
  assert.deepEqual(crossings(w.wires), []);
});
test('a project with the reset switch placed as before schema 12 takes the new switch', () => {
  const p = clone(defaults);
  const c = p.config as Record<string, any>;
  c.schema = 11;
  Object.assign(c.reset, {
    position_mm: [-5, 38.24],
    rotation_deg: -87.65,
    standoff_mm: 1,
    body_mm: [6, 6, 3.5],
    plunger_mm: [3.5, 3.5],
  });
  validateProject(p);
  assert.deepEqual(p.config, defaults.config);
});
test('a project with the reset switch placed as before schema 11 takes the new switch', () => {
  const p = clone(defaults);
  const c = p.config as Record<string, any>;
  c.schema = 10;
  Object.assign(c.reset, {
    position_mm: [-8, 32.5],
    rotation_deg: 0,
    standoff_mm: 1.8,
    plunger_mm: [3.5, 1.5],
    hole_mm: 2,
  });
  c.pro_micro.cradle.reset_walls = 0.6;
  validateProject(p);
  assert.deepEqual(p.config, defaults.config);
});
test('a project with the jack placed as before schema 14 takes its new place', () => {
  const p = clone(defaults);
  const c = p.config as Record<string, any>;
  c.schema = 13;
  Object.assign(c.trrs, { position_mm: [-43.9, 15.35], rotation_deg: -4.5 });
  validateProject(p);
  assert.deepEqual(p.config, defaults.config);
});
test('a project wired as before schema 15 takes the Dupont feeds’ pins, chains, LED order and loop', () => {
  const p = clone(defaults);
  const c = p.config as Record<string, any>;
  c.schema = 14;
  Object.assign(c.pro_micro.pins, { RB: 12, RX: 15, C4: 11 });
  c.wiring.led_order.reverse();
  for (const n of c.wiring.nets)
    if (n.group === 'column') n.chains = [n.chains[0].slice(0, -1), n.chains[0].slice(-1)];
  c.wiring.service_loop_mm = 40;
  c.wiring.description = c.wiring.description.replace(
    "its column wire chains on from that column's bottom key.",
    "but has its own wire to that column's pin.",
  );
  validateProject(p);
  assert.deepEqual(p.config, defaults.config);
});
test('a project with the jack placed as before schema 10 takes its new place', () => {
  const p = clone(defaults);
  const c = p.config as Record<string, any>;
  c.schema = 9;
  Object.assign(c.trrs, { position_mm: [-42.72, 30.3], rotation_deg: -4.5 });
  validateProject(p);
  assert.deepEqual(p.config, defaults.config);
});
test('a project with the jack placed as before schema 9 takes its new place and pins', () => {
  const p = clone(defaults);
  const c = p.config as Record<string, any>;
  c.schema = 8;
  Object.assign(c.trrs, { position_mm: [-45.05, -7.7], rotation_deg: 0 });
  Object.assign(c.pro_micro.pins, { RB: 12, RX: 15, C3: 16, C4: 11 });
  c.trrs.wires.find((w: { name: string }) => w.name === 'GND').pin = 4;
  validateProject(p);
  assert.deepEqual(p.config, defaults.config);
});
test('a project with the Pro Micro and jack placed as before schema 8 takes their new places and pins', () => {
  const p = clone(defaults);
  const c = p.config as Record<string, any>;
  c.schema = 7;
  c.pro_micro.position_mm = [-21, 17];
  Object.assign(c.pro_micro.pins, { RT: 11, RH: 12, RB: 17, RX: 18 });
  Object.assign(c.pro_micro.pins, { C0: 6, C1: 7, C2: 8, C3: 9, C4: 10 });
  Object.assign(c.trrs, { position_mm: [-42.3, 14.4], rotation_deg: 0 });
  c.trrs.wires.find((w: { name: string }) => w.name === 'GND').pin = 3;
  validateProject(p);
  assert.deepEqual(p.config, defaults.config);
});
test('a project with the Pro Micro and jack placed as before schema 7 takes their new places', () => {
  const p = clone(defaults);
  const c = p.config as Record<string, any>;
  c.schema = 6;
  Object.assign(c.pro_micro, { position_mm: [-29.5, 9], rotation_deg: 0 });
  Object.assign(c.trrs, { position_mm: [-39.2, -6], rotation_deg: 0, standoff_mm: 0 });
  validateProject(p);
  assert.deepEqual(p.config, defaults.config);
});
test('a project saved before the Pro Micro loads on it', () => {
  const p = clone(defaults);
  const c = p.config as Record<string, any>;
  delete c.pro_micro;
  delete c.trrs;
  delete c.reset;
  validateProject(p);
  assert.deepEqual(p.config, defaults.config);
});
test('a project saved on the FFC adapter loads on the Pro Micro, without the adapter, ribbon or ribbon pins', () => {
  const p = clone(defaults);
  const c = p.config as Record<string, any>;
  c.schema = 12;
  c.adapter = { position_mm: [-24, 16], rotation_deg: 0, board_mm: [26, 36, 1.6] };
  c.ribbon = { width_mm: 12.5 };
  c.controller = { style: 'ffc' };
  c.wiring.nets.forEach((n: { pin?: number }, i: number) => (n.pin = i + 1));
  c.wiring.description = 'Hand wiring from the tile holes and pads to the adapter.';
  validateProject(p);
  assert.deepEqual(p.config, defaults.config);
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
test("the wiring joins each net's pads and pin, for a 4 × 5 matrix", () => {
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
  // 100 under the keys, and the jack's three link wires and the reset switch's two.
  assert.equal(w.wires.length, 105);
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
  // Both ends of every wire but the 12 feeds' plugged ones.
  assert.equal(
    w.nets.reduce((s, n) => s + n.joints, 0),
    198,
  );
});
test('a project saved before the wiring loads with the default wiring', () => {
  const p = clone(defaults);
  const c = p.config as Record<string, any>;
  delete c.schema;
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
  assert.equal(r.report.wiring.wires, 105);
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

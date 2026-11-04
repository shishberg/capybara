// The soldering jig: it builds clean, its turn keeps the tiles' places, and its checks fire.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import Module from 'manifold-3d';
import { Matrix4 } from 'three';
import { componentFrames, defaults, isKey } from '../src/geometry';
import { buildJig, jigFaults, turnedOver } from '../src/jig';

const wasm = await Module();
wasm.setup();
const cfg = defaults.config,
  { turn, pockets } = turnedOver(cfg),
  jig = buildJig(wasm, cfg, pockets);

test('the jig builds with no faults', () => {
  assert.deepEqual(jigFaults(wasm, cfg, jig, pockets), []);
});

test('the jig holds every key, turned and not mirrored', () => {
  const nodes = componentFrames(cfg);
  assert.deepEqual(pockets.map((p) => p.name).sort(), Object.keys(nodes).filter(isKey).sort());
  assert.ok(turn.determinant() > 0);
  for (const p of pockets) {
    const want = turn.clone().multiply(nodes[p.name]);
    p.frame.elements.forEach((v, i) => assert.ok(Math.abs(v - want.elements[i]) < 1e-9));
  }
});

test('a tile moved off its ledges is a fault', () => {
  const [first, ...rest] = pockets,
    moved = {
      name: first.name,
      frame: first.frame.clone().multiply(new Matrix4().makeTranslation(0, 3, 0)),
    },
    faults = jigFaults(wasm, cfg, jig, [moved, ...rest]);
  assert.ok(faults.some((f) => f.includes("in the tile's way")));
  assert.ok(faults.some((f) => f.includes('ledge')));
});

test('a jig in two pieces is a fault', () => {
  const stray = wasm.Manifold.cube([1, 1, 1]).translate([500, 0, 0]);
  assert.ok(jigFaults(wasm, cfg, jig.add(stray), pockets).some((f) => f.includes('2 pieces')));
});

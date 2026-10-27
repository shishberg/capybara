import assert from 'node:assert/strict';
import { test } from 'node:test';
import { negotiate, type Option } from '../src/wiring/negotiate';
import { tubeOf } from '../src/wiring/tubes';

const option = (a: number[], b: number[], rank: number): Option => ({
  tube: tubeOf([a, b] as [number, number, number][], 0.6),
  rank,
});

test('negotiation moves a wire off a crossing when its other option is cheap enough', () => {
  const options = [
    // A run along x, or the same run 5 mm away at one more rank.
    [option([0, 0, 0], [10, 0, 0], 0), option([0, 5, 0], [10, 5, 0], 1)],
    // A run across it, or one out of the way at five more.
    [option([5, -5, 0], [5, 2, 0], 0), option([20, -5, 0], [20, 2, 0], 5)],
  ];
  assert.deepEqual(negotiate(options, false), { left: 0, choice: [1, 0] });
  assert.deepEqual(negotiate(options, true), { left: 0, choice: [1, 0] });
});

test('negotiation reports the wires that cannot avoid each other', () => {
  const options = [
    [option([0, 0, 0], [10, 0, 0], 0)],
    [option([5, -5, 0], [5, 2, 0], 0)],
    [option([0, 20, 0], [10, 20, 0], 0)],
  ];
  assert.deepEqual(negotiate(options, true), { left: 2, choice: [0, 0, 0] });
});

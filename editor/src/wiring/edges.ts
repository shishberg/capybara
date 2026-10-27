// The tile edges wires leave by.
import type { Matrix4 } from 'three';
import { point, type V3 } from '../geometry';
import type { Edge, Pad } from './common';

/** The plate edge of a key's frame that faces a plan direction. */
const facing = (m: Matrix4, dir: number[]): Edge => {
  const e = m.elements;
  const options: Edge[] = [
    [0, 1],
    [0, -1],
    [1, 1],
    [1, -1],
  ];
  const score = ([axis, sign]: Edge) => sign * (e[axis * 4] * dir[0] + e[axis * 4 + 1] * dir[1]);
  return options.reduce((a, b) => (score(b) > score(a) ? b : a));
};

/** The edge of a key's tile that faces a world point, in plan. */
export const edgeToward = (frames: Record<string, Matrix4>, key: string, to: V3): Edge => {
  const c = point(frames[key], [0, 0, 0]);
  return facing(frames[key], [to[0] - c[0], to[1] - c[1]]);
};

/** A pad's own edge: the tile edge it sits nearest, `half` the tile pocket's half-widths. */
export const ownEdge = (p: Pick<Pad, 'xy'>, half: number[]): Edge => {
  const axis = half[0] - Math.abs(p.xy[0]) < half[1] - Math.abs(p.xy[1]) ? 0 : 1;
  return [axis, Math.sign(p.xy[axis]) || 1];
};

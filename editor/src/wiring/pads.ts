// The tile pads, as parts.
import { componentFrames, isKey, tileUnderside, type Config, type V3 } from '../geometry';
import type { Part } from '../parts';
import { WIRING } from './common';

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

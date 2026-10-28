// The tile pads and the rails' stubs, as parts.
import { componentFrames, isKey, tilePads, tileUnderside, type Config, type V3 } from '../geometry';
import type { Part } from '../parts';
import { WIRING, railPads } from './common';

/**
 * The pads and holes on every tile, as thin boxes (a hole's ring, round) on
 * the tile's underside, and the rails' stubs standing down from theirs.
 */
export function padParts(cfg: Config, frames = componentFrames(cfg)): Part[] {
  const tile = cfg.tile;
  const z = tileUnderside(cfg) - WIRING.padLift;
  const [stub, length] = cfg.wiring.stub_mm;
  const rail = railPads(cfg);
  return Object.keys(frames)
    .filter(isKey)
    .flatMap((key) =>
      tilePads(cfg).flatMap((p) => [
        {
          name: `${key}: ${p.name} ${p.hole ? 'hole' : 'pad'}`,
          group: 'pads',
          size: (p.hole
            ? [tile.pads.ring_mm, tile.pads.ring_mm, WIRING.padThickness]
            : [...tile.pads.size_mm, WIRING.padThickness]) as V3,
          center: [p.at_mm[0], p.at_mm[1], z] as V3,
          matrix: frames[key].elements.slice(),
          cylinder: p.hole ? tile.pads.ring_mm / 2 : undefined,
        },
        ...(rail.has(p.name)
          ? [
              {
                name: `${key}: ${p.name} stub`,
                group: 'stubs',
                size: [stub, stub, length] as V3,
                center: [p.at_mm[0], p.at_mm[1], tileUnderside(cfg) - length / 2] as V3,
                matrix: frames[key].elements.slice(),
                cylinder: stub / 2,
              },
            ]
          : []),
      ]),
    );
}

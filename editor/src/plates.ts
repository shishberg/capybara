// The key plates' extents, shared with the wiring (which keeps wires out of
// them) and the frame.
import { tileBottom, type Config } from './geometry';
import { seatSettings } from './seats';

/** Sizes in mm, in key coordinates. */
export const PLATES = {
  /** The switch body and pins reach this far below the plate top: kept clear under the switch hole. */
  switchBelowPlate: 13,
};

/** Half-widths along a key's x and y axes. */
export type HalfWidths = [number, number];

/** The tile pocket's half-widths: the tile and its clearance. */
export const tilePocketHalf = (cfg: Config): HalfWidths => [
  cfg.tile.size_mm[0] / 2 + cfg.tile.clearance_mm,
  cfg.tile.size_mm[1] / 2 + cfg.tile.clearance_mm,
];

/** How far the tile pocket reaches below the plate top: the tile, its components and their clearance. */
export const tilePocketDepth = (cfg: Config) => -tileBottom(cfg) + cfg.tile.component_clearance_mm;

/** The plates' half-widths: plate_margin past the seat, and always far enough to cover the tile pocket. */
export function plateHalfWidths(cfg: Config): HalfWidths {
  const seat = seatSettings(cfg).outer;
  const pocket = tilePocketHalf(cfg);
  return [0, 1].map((i) =>
    Math.max(seat[i] / 2 + cfg.chassis.plate_margin_mm, pocket[i]),
  ) as HalfWidths;
}

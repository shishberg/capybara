// Prints the default project's (Swung in's) placement as JSON for lowpro
// (lowpro/layout.py, key_layout "swung_in"): every key, the Pro Micro, the
// TRRS jack and the reset switch as the editor places them in world axes,
// tent and lift included, with z = 0 the desk and the base plate's top
// skin_mm over it.
//   half      "right" or "left" (the argument; the frames are in the right
//             half's coordinates either way, see docs/editor-chassis.md)
//   skin_mm   the base plate's thickness, which the parts stand on
//   frames    { name: 4 x 4 row-major }: a key's origin is the plate's top at
//             the stem, +z out of the key, +y the socket's side; the parts'
//             frames are the editor's (src/geometry.ts componentFrames)
//   units     { key: the cap's width along x in 19.05 mm key units }
// Usage: node --import tsx tests/key-frames.ts [left]
import { capSize, clone, componentFrames, defaults, isKey } from '../src/geometry';

const c = clone(defaults.config);
if (process.argv[2] === 'left') c.half = 'left';
const frames: Record<string, number[][]> = {},
  units: Record<string, number> = {};
for (const [name, m] of Object.entries(componentFrames(c))) {
  const e = m.elements; // column-major
  frames[name] = [0, 1, 2, 3].map((r) => [0, 1, 2, 3].map((k) => e[k * 4 + r]));
  if (isKey(name)) units[name] = 1 + (capSize(c, name)[0] - c.switch.keycap_mm[0]) / 19.05;
}
console.log(JSON.stringify({ half: c.half, skin_mm: c.chassis.skin_mm, frames, units }));

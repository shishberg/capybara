// Prints the default project's (Swung in's) keys as JSON for lowpro
// (lowpro/layout.py, key_layout = "swung_in"):
//   tent_deg  the tent the keys were laid out under
//   keys      { name: { frame, units } }: frame the key's 4 x 4 (row-major) in
//             layout axes, before the tent and the mount lift, its origin at
//             the plate's top at the stem, +z out of the key, +y the socket's
//             side; units the cap's width along x in 19.05 mm key units.
// Usage: node --import tsx tests/key-frames.ts
import { capSize, componentFrames, defaults, isKey, tentFrame } from '../src/geometry';

const c = defaults.config,
  untent = tentFrame(c).invert(),
  keys: Record<string, { frame: number[][]; units: number }> = {};
for (const [name, m] of Object.entries(componentFrames(c))) {
  if (!isKey(name)) continue;
  const e = m.clone().premultiply(untent).elements; // column-major
  keys[name] = {
    frame: [0, 1, 2, 3].map((r) => [0, 1, 2, 3].map((k) => e[k * 4 + r])),
    units: 1 + (capSize(c, name)[0] - c.switch.keycap_mm[0]) / 19.05,
  };
}
console.log(JSON.stringify({ tent_deg: c.geometry.tent_deg, keys }));

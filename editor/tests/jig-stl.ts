// Builds the soldering jig into output/jig/ and checks it.
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import Module from 'manifold-3d';
import { defaults } from '../src/geometry';
import { frameStl } from '../src/hand/frame';
import { buildJig, jigFaults, turnedOver } from '../src/jig';
import { freeAfter, meshData } from '../src/manifold-util';

const wasm = await Module();
wasm.setup();
const cfg = defaults.config,
  out = fileURLToPath(new URL('../../output/jig/', import.meta.url));
mkdirSync(out, { recursive: true });

const faults = freeAfter(wasm, () => {
  const { pockets } = turnedOver(cfg),
    jig = buildJig(wasm, cfg, pockets),
    mesh = meshData(jig),
    b = jig.boundingBox();
  for (const [name, mirror] of [
    ['right', false],
    ['left', true],
  ] as const) {
    const file = `${out}capybara-jig-${name}.stl`;
    writeFileSync(file, new Uint8Array(frameStl(mesh, 0, mirror).buffer));
    console.log(`wrote ${file}`);
  }
  const size = [0, 1, 2].map((i) => (b.max[i] - b.min[i]).toFixed(1));
  console.log(`${size.join(' x ')} mm, ${(jig.volume() / 1000).toFixed(0)} cm3`);
  return jigFaults(wasm, cfg, jig, pockets);
});
for (const f of faults) console.error(f);
console.log(faults.length ? `${faults.length} faults` : 'All checks pass.');
process.exit(faults.length ? 1 : 0);

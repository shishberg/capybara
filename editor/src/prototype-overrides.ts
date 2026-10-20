import { clone, type Project } from './geometry';
import { mouthConfig } from './wiring/trrs-mouth.prototype';

/**
 * PROTOTYPE URL overrides, for trying a variant without editing the project:
 * `?controller=ffc|pro_micro`, what the hand's wires run to (controller.style;
 * wiring/pro-micro.ts), and `?mouth=`, what holds the jack's mouth in the wall
 * (trrs.mouth; wiring/trrs-mouth.prototype.ts), each cycled by a dev editor's
 * switcher bar. Returns the project to build, which is the one the report
 * records.
 */
export function prototypeOverrides(p: Project, search: string): Project {
  const q = new URLSearchParams(search),
    out = clone(p);
  if (q.get('controller')) out.config.controller.style = q.get('controller')!;
  if (q.get('mouth')) (out.config.trrs as { mouth?: string }).mouth = q.get('mouth')!;
  mouthConfig(out.config);
  return out;
}

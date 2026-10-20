import { clone, type Project } from './geometry';

/**
 * PROTOTYPE URL overrides, for trying a variant without editing the project:
 * `?controller=ffc|pro_micro`, what the hand's wires run to (controller.style;
 * wiring/pro-micro.ts), cycled by the dev editor's switcher bar. Returns the
 * project to build, which is the one the report records.
 */
export function prototypeOverrides(p: Project, search: string): Project {
  const q = new URLSearchParams(search),
    out = clone(p);
  if (q.get('controller')) out.config.controller.style = q.get('controller')!;
  return out;
}

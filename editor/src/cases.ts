// The cases the editor can show, and which View toggle governs each piece of a
// low-profile assembly (lowpro/README.md).

export type CaseId = 'capybara' | 'shell' | 'wells' | 'lowpro';
export type LowproBuild = 'capybara' | 'capybara_wells' | 'lowpro';

/** `lowpro` is what `python -m lowpro.build` builds for the case, where it has
 * one: its preset (lowpro/params.py PRESETS), or `lowpro` for none. */
export const CASES: Record<CaseId, { label: string; lowpro?: LowproBuild }> = {
  capybara: { label: 'Capybara frame' },
  shell: { label: 'Low-profile shell on Swung in', lowpro: 'capybara' },
  wells: { label: 'Low-profile shell with wells', lowpro: 'capybara_wells' },
  lowpro: { label: 'Low-profile', lowpro: 'lowpro' },
};

/** The low-profile cases are built by the dev server's make (vite.config.ts). */
export const AVAILABLE = (Object.keys(CASES) as CaseId[]).filter(
  (id) => import.meta.env.DEV || !CASES[id].lowpro,
);
export const isAvailable = (v: unknown): v is CaseId => AVAILABLE.includes(v as CaseId);

export type PieceKind = 'keycaps' | 'base' | 'body' | 'parts';
/** The View toggle a 3MF piece answers to, by the name lowpro/build.py gives it. */
export const pieceKind = (name: string): PieceKind =>
  name.startsWith('keycap ')
    ? 'keycaps'
    : name === 'plinth'
      ? 'base'
      : name === 'body'
        ? 'body'
        : 'parts';

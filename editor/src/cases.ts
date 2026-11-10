// The cases the editor can show, and which View toggle governs each piece of a
// built case (case/README.md).

export type CaseId = 'ribs' | 'capybara' | 'slim' | 'slim_ribs';

/** `built` cases are what `python -m case.build --preset <id>` builds
 * (case/params.py PRESETS); `ribs` is the editor's own model. `wired` is
 * whether the case shows its wires. */
export const CASES: Record<CaseId, { label: string; built?: true; wired?: true }> = {
  ribs: { label: 'Capybara ribs', wired: true },
  capybara: { label: 'Capybara', built: true },
  slim: { label: 'Slim Capybara', built: true, wired: true },
  slim_ribs: { label: 'Slim Capybara ribs', built: true, wired: true },
};

/** The built cases are made by the dev server's make (vite.config.ts). */
export const AVAILABLE = (Object.keys(CASES) as CaseId[]).filter(
  (id) => import.meta.env.DEV || !CASES[id].built,
);
export const isAvailable = (v: unknown): v is CaseId => AVAILABLE.includes(v as CaseId);

export type PieceKind = 'keycaps' | 'base' | 'body' | 'wires' | 'parts';
/** The View toggle a 3MF piece answers to, by the name case/build.py gives it. */
export const pieceKind = (name: string): PieceKind =>
  name.startsWith('keycap ')
    ? 'keycaps'
    : name === 'plinth'
      ? 'base'
      : name === 'body'
        ? 'body'
        : name.startsWith('wire ')
          ? 'wires'
          : 'parts';

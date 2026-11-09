// View persistence: camera, view toggles and opacity, kept in browser storage
// apart from the project.
import { placeCamera } from './three-util';
import { $, S } from './state';
import { camera, controls, material, render, seeThrough } from './viewer';
import { visibility } from './scene-parts';
import { isAvailable, type CaseId } from './cases';
import { pieceVisibility, showCase } from './case-view';

const VIEW_STORAGE = 'rosebear-chassis-editor:view';
const TOGGLES = ['edit', 'caps', 'parts', 'wires', 'controller', 'base', 'bounds', 'edges'];
for (const id of TOGGLES)
  $(id).onchange = () => {
    visibility();
    saveView();
  };
$('case').onchange = () => {
  S.case = $<HTMLSelectElement>('case').value as CaseId;
  showCase();
  saveView();
};
$('opacity').oninput = () => {
  seeThrough(material, Number($<HTMLInputElement>('opacity').value));
  pieceVisibility();
  render();
  saveView();
};
let viewTimer: ReturnType<typeof setTimeout> | undefined;
controls.addEventListener('change', () => {
  clearTimeout(viewTimer);
  viewTimer = setTimeout(saveView, 300);
});
function saveView() {
  try {
    localStorage.setItem(
      VIEW_STORAGE,
      JSON.stringify({
        camera: {
          position: camera.position.toArray(),
          target: controls.target.toArray(),
          up: camera.up.toArray(),
          zoom: camera.zoom,
        },
        toggles: Object.fromEntries(TOGGLES.map((id) => [id, $<HTMLInputElement>(id).checked])),
        opacity: Number($<HTMLInputElement>('opacity').value),
        case: S.case,
      }),
    );
  } catch {}
}
// Restores what saveView stored, skipping anything malformed. A mark in the URL
// sets its own camera, so the stored one is left alone then.
export function restoreView() {
  let v: any;
  try {
    v = JSON.parse(localStorage.getItem(VIEW_STORAGE) ?? 'null');
  } catch {
    return;
  }
  if (!v || typeof v !== 'object') return;
  const vec = (a: unknown) =>
    Array.isArray(a) && a.length === 3 && a.every((n) => Number.isFinite(n));
  const c = v.camera;
  if (
    !new URLSearchParams(location.search).has('mark') &&
    c &&
    vec(c.position) &&
    vec(c.target) &&
    vec(c.up) &&
    Number.isFinite(c.zoom)
  ) {
    placeCamera(camera, controls, {
      ...c,
      zoom: Math.min(controls.maxZoom, Math.max(controls.minZoom, c.zoom)),
    });
  }
  if (v.toggles && typeof v.toggles === 'object')
    for (const id of TOGGLES)
      if (typeof v.toggles[id] === 'boolean') $<HTMLInputElement>(id).checked = v.toggles[id];
  if (isAvailable(v.case)) S.case = v.case;
  visibility();
  const o = v.opacity;
  if (Number.isFinite(o) && o >= 0.1 && o <= 1) {
    $<HTMLInputElement>('opacity').value = String(o);
    $('opacity').dispatchEvent(new Event('input'));
  }
}

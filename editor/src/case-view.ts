// Which case shows. The Capybara frame is the editor's own model; a
// low-profile case is a 3MF assembly the dev server makes (vite.config.ts),
// loaded into lowproGroup while the frame is hidden.
import * as T from 'three';
import { ThreeMFLoader } from 'three/addons/loaders/3MFLoader.js';
import { AVAILABLE, CASES, pieceKind } from './cases';
import { $, S } from './state';
import {
  captureFaceOrder,
  frame,
  lowproGroup,
  lowproPieces,
  material,
  measure,
  render,
  seeThrough,
} from './viewer';

const select = $<HTMLSelectElement>('case');
select.replaceChildren(...AVAILABLE.map((id) => new Option(CASES[id].label, id)));
select.parentElement!.hidden = AVAILABLE.length < 2;

// The Case select's value and the subtitle follow S.case and the project's half.
export function syncCase() {
  select.value = S.case;
  $('subtitle').textContent =
    `${S.project.config.half === 'left' ? 'Left' : 'Right'} hand · ${CASES[S.case].label}`;
}

// The half and design the group holds or is being sent for, and which request
// is the latest, so a slow response for an earlier choice is dropped.
let wanted = '';
let request = 0;

export function showCase() {
  const design = CASES[S.case].lowpro;
  frame.visible = !design;
  lowproGroup.visible = !!design;
  document.body.classList.toggle('lowpro-case', !!design);
  document.body.classList.toggle('unwired-case', !CASES[S.case].wired);
  syncCase();
  if (!design) {
    request++;
    wanted = '';
    measure();
    render();
    return;
  }
  const half = S.project.config.half,
    key = `${design}/${half}`;
  if (key === wanted) return;
  wanted = key;
  void load(design, half, CASES[S.case].label);
}

async function load(design: string, half: string, label: string) {
  const mine = ++request;
  $('view-state').textContent = `Building the ${label[0].toLowerCase() + label.slice(1)}…`;
  try {
    const res = await fetch(`/__lowpro/${design}/${half}.3mf`);
    if (!res.ok) throw Error(await res.text());
    const loaded = new ThreeMFLoader().parse(await res.arrayBuffer());
    if (mine !== request) return disposeAll(loaded);
    disposeAll(lowproGroup);
    bodyEdges = undefined;
    for (const o of meshes(loaded)) o.userData.kind = pieceKind(o.name);
    lowproGroup.add(loaded);
    // The loader's meshes are unindexed: the body gets an index, which render
    // re-sorts by depth while it is see-through.
    const body = lowproPieces('body')[0] as T.Mesh,
      corners = body.geometry.getAttribute('position').count;
    body.geometry.setIndex(
      new T.BufferAttribute(
        Uint32Array.from({ length: corners }, (_, i) => i),
        1,
      ),
    );
    captureFaceOrder(body);
    pieceVisibility();
    measure();
    render();
    $('view-state').textContent =
      `${label}, built from the repository's default project, not your edits.`;
  } catch (e) {
    if (mine !== request) return;
    $('view-state').textContent = e instanceof Error ? e.message : String(e);
  }
}

const meshes = (root: T.Object3D) => {
  const found: T.Mesh[] = [];
  root.traverse((o) => (o as T.Mesh).isMesh && found.push(o as T.Mesh));
  return found;
};

function disposeAll(root: T.Object3D) {
  root.traverse((o) => {
    const m = o as T.Mesh;
    m.geometry?.dispose();
    for (const mat of [m.material ?? []].flat()) mat.dispose();
  });
  root.clear();
}

let bodyEdges: T.LineSegments | undefined;
/**
 * The View toggles on the pieces: Keycaps, Bottom section, Wiring and pads and
 * Tiles and components by kind, and Chassis opacity and Show wireframe on the body.
 */
export function pieceVisibility() {
  const checked = (id: string) => $(id).matches(':checked');
  const on = {
    keycaps: checked('caps'),
    base: checked('base'),
    body: true,
    wires: checked('wires'),
    parts: checked('parts'),
  };
  for (const o of lowproPieces()) o.visible = on[o.userData.kind as keyof typeof on];
  const body = lowproPieces('body')[0] as T.Mesh | undefined;
  if (!body) return;
  seeThrough(body.material as T.Material, material.opacity);
  if (!bodyEdges?.parent && checked('edges'))
    body.add(
      (bodyEdges = new T.LineSegments(
        new T.EdgesGeometry(body.geometry, 1),
        new T.LineBasicMaterial({ color: 0x24343a }),
      )),
    );
  if (bodyEdges) bodyEdges.visible = checked('edges');
}

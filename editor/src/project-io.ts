// Saving and opening: project JSON, the clearance report and the review STLs.
import * as T from 'three';
import { STLExporter } from 'three/addons/exporters/STLExporter.js';
import { $, S } from './state';
import { shell, basePlate } from './viewer';
import { commit } from './project-store';

function download(name: string, data: BlobPart, type: string) {
  const url = URL.createObjectURL(new Blob([data], { type })),
    a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$('export').onclick = () =>
  download('rosebear-chassis-project.json', JSON.stringify(S.project, null, 2), 'application/json');
$('report').onclick = () => {
  if (S.solidRevision === S.revision && S.report && S.evaluated)
    download(
      'rosebear-clearance-report.json',
      JSON.stringify({ report: S.report, evaluatedProject: S.evaluated }, null, 2),
      'application/json',
    );
};
/** A mesh as shown: the left half mirrored, its triangles turned back the right way out. */
function asShown(mesh: T.Mesh) {
  const g = mesh.geometry.clone().applyMatrix4(mesh.matrixWorld),
    index = g.getIndex()!;
  if (mesh.matrixWorld.determinant() < 0)
    for (let i = 0; i < index.count; i += 3) {
      const b = index.getX(i + 1);
      index.setX(i + 1, index.getX(i + 2));
      index.setX(i + 2, b);
    }
  return new T.Mesh(g);
}
const exportStl = (id: string, name: string, mesh: T.Mesh) =>
  ($(id).onclick = () => {
    if (S.solidRevision !== S.revision) return;
    const shown = asShown(mesh);
    download(
      `rosebear-${S.evaluated!.config.half}-${name}.stl`,
      new STLExporter().parse(shown, { binary: true }) as DataView<ArrayBuffer>,
      'application/octet-stream',
    );
    shown.geometry.dispose();
  });
exportStl('stl', 'review', shell);
exportStl('stl-base', 'bottom', basePlate);
$('import').onclick = () => $<HTMLInputElement>('file').click();
$('file').onchange = async () => {
  const input = $<HTMLInputElement>('file'),
    file = input.files?.[0];
  if (!file) return;
  try {
    if (file.size > 2_000_000) throw Error('Project file exceeds 2 MB');
    const next = JSON.parse(await file.text());
    commit(next, true);
    $('load-error').textContent = '';
  } catch (e) {
    $('load-error').textContent = String(e);
  } finally {
    input.value = '';
  }
};

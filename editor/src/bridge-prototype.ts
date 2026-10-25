// PROTOTYPE, throwaway: a floating bar cycling how bridges meet the plates
// (capybara.ts's bridgeStyle) through ?bridge=, with ← and →. Dev only.
import { BRIDGE_STYLES } from './capybara';
import { S } from './state';
import { requestBuild } from './build-client';

const NAMES: Record<string, string> = {
  now: 'as now (hard corners)',
  sweep: 'sides swept into the edges, quarter circle',
  spline: 'waisted, curve leaving along each plate',
  steep: 'waisted, curve leaving steeper',
  curve: 'square corners, curve leaving along each plate',
  'curve-steep': 'square corners, curve leaving steeper',
};

export function setupBridgePrototype() {
  const bar = document.createElement('div');
  bar.style.cssText =
    'position:fixed;bottom:16px;left:50%;transform:translateX(-50%);z-index:1000;' +
    'display:flex;gap:10px;align-items:center;padding:6px 12px;border-radius:999px;' +
    'background:#111;color:#fff;font:13px system-ui;box-shadow:0 4px 16px #0006';
  const label = document.createElement('span');
  const button = (text: string, by: number) => {
    const b = document.createElement('button');
    b.textContent = text;
    b.style.cssText = 'background:none;border:0;color:#fff;font-size:16px;cursor:pointer';
    b.onclick = () => go(by);
    return b;
  };
  bar.append(button('←', -1), label, button('→', 1));
  document.body.append(bar);
  const current = () =>
    Math.max(0, BRIDGE_STYLES.indexOf(new URLSearchParams(location.search).get('bridge') as never));
  const show = () => {
    const style = BRIDGE_STYLES[current()];
    label.textContent = `bridge: ${style} (${NAMES[style]})`;
  };
  const go = (by: number) => {
    const n = BRIDGE_STYLES.length;
    const url = new URL(location.href);
    url.searchParams.set('bridge', BRIDGE_STYLES[(current() + by + n) % n]);
    history.replaceState(null, '', url);
    show();
    S.revision++;
    requestBuild();
  };
  addEventListener('keydown', (e) => {
    const t = e.target as HTMLElement;
    if (t.closest('input, textarea, select, [contenteditable]')) return;
    if (e.key === 'ArrowLeft') go(-1);
    else if (e.key === 'ArrowRight') go(1);
  });
  show();
}

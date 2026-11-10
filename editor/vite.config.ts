import { execFile, execFileSync } from 'node:child_process';
import { mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import { defineConfig, type Plugin } from 'vite';

const root = fileURLToPath(new URL('.', import.meta.url));
const repo = fileURLToPath(new URL('..', import.meta.url));

// Artifact marks painted on the editor (src/marks.ts), one JSON file and one
// screenshot per mark in marks/. Dev server only.
//   GET /__marks          every mark (without screenshots)
//   POST /__marks         save a mark: JSON with `shot` as a PNG data URL
//   DELETE /__marks/<id>  remove a mark
//   DELETE /__marks       remove every mark
function marks(): Plugin {
  const dir = root + 'marks/';
  const git = (...a: string[]) => execFileSync('git', a, { cwd: root, encoding: 'utf8' }).trim();
  return {
    name: 'marks',
    apply: 'serve',
    config: () => ({ server: { watch: { ignored: [dir + '**'] } } }),
    configureServer(server) {
      server.middlewares.use('/__marks', (req, res) => {
        const send = (code: number, body: unknown) => {
          res.statusCode = code;
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify(body));
        };
        mkdirSync(dir, { recursive: true });
        if (req.method === 'GET') {
          const marks = readdirSync(dir)
            .filter((f) => f.endsWith('.json'))
            .sort()
            .map((f) => JSON.parse(readFileSync(dir + f, 'utf8')));
          return send(200, marks);
        }
        if (req.method === 'DELETE') {
          const id = (req.url ?? '').replace(/^\//, '');
          if (!id) {
            // Only plain mark files: names from the folder itself, nothing else.
            const files = readdirSync(dir).filter((f) => /^[\w-]+\.(json|png)$/.test(f));
            files.forEach((f) => rmSync(dir + f, { force: true }));
            return send(200, { removed: files.length });
          }
          if (!/^[\w-]+$/.test(id)) return send(400, { error: 'bad id' });
          rmSync(dir + id + '.json', { force: true });
          rmSync(dir + id + '.png', { force: true });
          return send(200, { id });
        }
        if (req.method !== 'POST') return send(405, { error: 'method' });
        const chunks: Buffer[] = [];
        req.on('data', (c: Buffer) => chunks.push(c));
        req.on('end', () => {
          let mark;
          try {
            mark = JSON.parse(Buffer.concat(chunks).toString('utf8'));
          } catch {
            return send(400, { error: 'bad json' });
          }
          const t = new Date(),
            pad = (n: number) => String(n).padStart(2, '0'),
            stamp = `${t.getFullYear()}${pad(t.getMonth() + 1)}${pad(t.getDate())}-${pad(t.getHours())}${pad(t.getMinutes())}${pad(t.getSeconds())}`,
            id = `${stamp}-${String(mark.variant).replace(/[^\w-]/g, '')}`;
          const shot = String(mark.shot ?? '').replace(/^data:image\/png;base64,/, '');
          if (shot) writeFileSync(dir + id + '.png', Buffer.from(shot, 'base64'));
          // The geometry the mark was drawn on: the commit, and whether the
          // shape code had uncommitted changes.
          const dirty = git('status', '--porcelain', '--', 'src').length > 0;
          const saved = {
            id,
            time: t.toISOString(),
            commit: git('rev-parse', '--short', 'HEAD') + (dirty ? '+dirty' : ''),
            ...mark,
            shot: shot ? id + '.png' : undefined,
          };
          writeFileSync(dir + id + '.json', JSON.stringify(saved, null, 1) + '\n');
          send(200, saved);
        });
      });
    },
  };
}

// The low-profile cases (lowpro/README.md): one half's assembly as 3MF, built
// by the Makefile when its inputs changed. Dev server only.
//   GET /__lowpro/<capybara|capybara_wells|frame|lowpro>/<right|left>.3mf
// Two requests for one file share one make.
function lowproCases(): Plugin {
  const run = promisify(execFile);
  const making = new Map<string, Promise<unknown>>();
  return {
    name: 'lowpro-cases',
    apply: 'serve',
    config: () => ({ server: { watch: { ignored: [repo + 'output/**'] } } }),
    configureServer(server) {
      server.middlewares.use('/__lowpro', async (req, res) => {
        const m = /^\/(capybara|capybara_wells|frame|lowpro)\/(right|left)\.3mf$/.exec(req.url ?? '');
        res.setHeader('Content-Type', 'text/plain');
        if (!m) {
          res.statusCode = 400;
          return res.end('bad case');
        }
        // A preset's files sit in a folder of their own (Makefile).
        const target = `output/lowpro/${m[1] === 'lowpro' ? '' : m[1] + '/'}${m[2]}-assembly.3mf`;
        let build = making.get(target);
        if (!build) {
          build = run('make', [target], { cwd: repo, maxBuffer: 1 << 26 }).finally(() =>
            making.delete(target),
          );
          making.set(target, build);
        }
        try {
          await build;
          const file = await readFile(repo + target);
          res.setHeader('Content-Type', 'model/3mf');
          res.end(file);
        } catch (e: any) {
          res.statusCode = 500;
          res.end(`make ${target} failed:\n` + String(e.stderr || e.stdout || e).slice(-2000));
        }
      });
    },
  };
}

// Workers as modules: the build worker starts the wiring worker.
export default defineConfig({ plugins: [marks(), lowproCases()], worker: { format: 'es' } });

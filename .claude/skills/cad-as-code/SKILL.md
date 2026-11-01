---
name: cad-as-code
description: Set up a project that builds 3D-printed parts from Python, mesh-first with Manifold, with checks an agent can trust.
disable-model-invocation: true
---

# CAD as code

Set up a build where the design is plain Python numbers and every output is generated: one command builds the parts, runs the checks, and exits non-zero when anything is wrong. The agent's eyes are the **checks**, not the renders: renders are for the human, and in practice they miss breaks the checks catch.

The worked example is `lowpro/` in github.com/shishberg/capybara (`lowpro/build.py`, `lowpro/chassis.py`, `lowpro/README.md`). Read it before step 3 and reuse what fits.

## Steps

### 1. Pin the outputs

Ask what leaves the build. Printed parts need meshes: STL per part, 3MF for an assembly (one file, named and coloured pieces). Exact surfaces (STEP) are needed only when someone will open the part in CAD to measure or edit it by hand; the source of truth is the code either way.

- Meshes only → **mesh-first** (the rest of this skill).
- STEP required → build123d/OpenCascade, with every rule below still applying; see "When it has to be a B-rep".

Done when the README's outputs table lists every file the build writes, and the output directory is gitignored.

### 2. Numbers first

Write the layout as a module of plain numbers and 4×4 frames: positions, routes, clearances, every dimension, each parameter commented with its unit and where it came from (mark guesses PROVISIONAL). It imports numpy and nothing that builds geometry.

Done when the layout module imports and prints its key positions with the geometry libraries uninstalled.

### 3. Blanks you write yourself

Each part starts as a **blank**: one closed triangle mesh built straight from functions of the design.

- The outline is a polygon at a fixed station spacing (`mesh_mm`), with curves within `mesh_tol_mm` of their chords.
- A wall is one vertical quad per outline segment, from its bottom ring to its top ring, so it is exactly vertical with no seams.
- Top and underside surfaces are functions z(x, y), sampled over one triangulation of the plan (the `triangle` package) shared by every surface of the part, so the rings meet vertex for vertex.
- Rounds are arcs computed at each station, stitched as rings.

Done when every blank is one closed manifold (`Manifold.status()` is `NoError`, `decompose()` gives one piece) and its walls' triangles all have |normal.z| below 1e-5 in the written STL.

### 4. Cuts as exact solids

Everything cut from or added to a blank (pockets, channels, holes, bosses, the parts' rooms) is an exact Manifold solid placed by a frame from the layout, applied with Manifold's booleans. Keep each cutter as its own named solid in a list before cutting: the checks need them separately.

Done when the full build of every part runs in about a second or less (`--verbose` prints each stage's time).

### 5. One command

`python -m <pkg>.build` with `--part`, `--set NAME=VALUE` (any parameter, for sweeps), `--check` (checks only), `--verbose`, `--out`. Before writing a part it refuses one that is not a single closed manifold solid with volume spanning the expected footprint, naming what is wrong and where, and writes nothing. It exits 1 when a check fails. Add a `make` target for the build and one for the checks.

Done when a deliberately broken parameter makes the command exit non-zero with a message that names the part and the place.

### 6. Checks, each proven red

Each invariant the design must keep is a check in the build, run on the exact cutters and solids before anything is written. The usual set:

- Moving or neighbouring parts don't meet (at rest and at full travel).
- The wall round each fastener: its holes against every other cutter of that part and against the outline. Check cutters against each other, not only the finished part, since a cut that breaks into another cut leaves a valid-looking solid.
- Mating parts don't overlap.
- Every wire or hose has a path to where it goes that it fits through. Model the space as what each part actually loses (its blank within its cutters, since cutters reach past the part), then shrink it by the wire's radius so a sliver where one cut grazes another doesn't count as a route.
- Whatever the user named as must-not-happen.

Make each check **red** once: break the design with `--set` (or a one-line edit) so the check must fail, confirm it fails naming the culprit, then confirm green on the defaults. Record the breaking `--set` for each check in the README's checks section, beside what the checks don't cover.

Done when every check has been seen red and green, and the README lists the unchecked risks.

### 7. Renders for the human

A render script in the repo (pyvista, off-screen) writes PNGs to the output directory: iso, underside, a section through the busiest region, close-ups of the smallest features. Show them to the user after any change to the shape; the checks are what you report as verification.

Done when one command produces the PNGs and you have looked at them yourself before showing them.

## Reference

**When it has to be a B-rep.** OpenCascade costs: fillets that fail by seam position, booleans against a part-wide spline that take minutes, solids that come out invalid, split planes for speed that leave seams in the mesh. If STEP is required, gate every written part on `BRepCheck_Analyzer`, refuse fragments, compute rounds in closed form rather than with the fillet API, and keep Manifold as an independent check on the exported mesh.

**Ports and refactors.** Compare the new outputs numerically against the old ones (outline sections, feature centres, surface distance percentiles, volumes) and explain every difference over a tenth of a millimetre before trusting the new build.

**Cloud sessions.** Keep the dependencies to pip packages (`manifold3d`, `numpy`, `scipy`, `triangle`, `pyvista` for renders) so the build runs anywhere Python does, with no CAD install or paid service.

**STL precision.** STL stores single-precision floats, so geometry exact in double precision can be off by about 1e-6 mm when written; set check tolerances above that.

---
name: audit
description: Pre-print audit of a lowpro build. Measures every fit, assembly and print defect on the real meshes, ranks them, and leaves rerunnable probes.
disable-model-invocation: true
argument-hint: "[preset ...] [special requirements]"
---

# Audit a lowpro build before printing

Go over a built lowpro case with a fine-toothed comb: anything that won't fit where it's meant to, won't go together, or will print badly. The build's own checks already pass or fail on their own; the audit is the **gaps** they leave. Every finding is a number taken from the real meshes by a probe someone can rerun.

The repo is read-only for the whole audit: change nothing tracked, and leave `output/` to the build. Fixes are the user's call after the report.

## Inputs

- **Presets**: those named in the arguments. With none named, audit the preset the recent commits and conversation are working on; say which you picked and why. Presets live in `lowpro/params.py`.
- **Special requirements**: anything in the arguments or the conversation that this build has to meet beyond printing and fitting, such as moving an already-wired harness of tiles from an older chassis into this body. Each gets its own probes, written for it in the scratch dir, and its own section of the report.
- **The last audit**: if the conversation or the user points at an earlier report, re-measure each of its findings and say which are fixed, still open, or changed.

## Steps

### 1. Baseline

Note `git status` and HEAD. Run `.venv/bin/python -m lowpro.build --preset <p> --out <scratch>/build/<p>` (without `--out` it writes `output/`) and `make lowpro-test`, and record what passes. Read `lowpro/README.md` and the checks in `lowpro/build.py` so you know what is already covered, and `git log` since the last audit for what changed. Every feature added since then needs a probe of its own.

Done when you can list what the build's checks cover and what they don't.

### 2. Set up

Make a scratch dir (the job's tmp dir if there is one, else `mktemp -d`) and copy `scripts/` into it. Builds, probe output and new probes all live there, never in the repo. If `.venv/bin/python -c "import trimesh, embreex"` fails, install the probes' dependencies with `uv pip install --python .venv/bin/python -r .claude/skills/audit/scripts/requirements.txt`.

Run probes from the checkout: `AUDIT_REPO=$PWD AUDIT_PRESET=<p> <scratch>/run_bounded.sh <half> <probe> [args]`. It finds the probe beside itself, sets `AUDIT_HALF`, and writes `<scratch>/out/<preset>/`. Probes read meshes from `<scratch>/build/<preset>/`, building them there on first use if step 1's build isn't there; `output/` can be stale. `<scratch>/run_all.sh <p>` runs the whole table on the right half, `namecheck.py` first: it lists every lowpro name a probe uses that no longer exists.

Ray casting has to use embree. Without it trimesh falls back to a pure-Python caster that took 20 GB of RAM, so `common.cast` refuses to run without it. Run every heavy probe (thickness, overhang, ways in) through `run_bounded.sh`, which kills it past 2 GB.

### 3. Probe

Run every probe in the table below on both halves (left is a mirror, so `mirror.py` plus the right half's full set covers it), then write new probes for:

- each feature new since the last audit;
- each special requirement;
- anything a probe turned up that needs a closer look (`whatis.py` names what makes a spot thin; `under_map.py` maps what is under a tile; `part_gap.py` locates a gap `room_gaps.py` only sizes).

Every number under a threshold gets a location and a cause: where it is and which features make it. A probe prints its design values from `P`, never as literals, so its labels don't go stale when a parameter changes.

Done when every row of the table has a result for each preset, every under-threshold number is located, and every new feature and special requirement has a probe that answered it.

### 4. Verify

Re-measure every number a helper or subagent gave you before it goes in the report. If HEAD moved during the audit, re-run the affected probes on the new HEAD and say so. Tag each claim **measured** (a probe read it off the meshes), **inferred** (it follows from measured numbers plus a known printing or hardware fact), or **guess**.

### 5. Report

In this order:

1. **Build checks and tests at HEAD**, per preset, and what they don't cover.
2. **Findings, ranked**: *blocks the build*, *degrades it*, *cosmetic*, then *doc drift*. Each one gives its location (world coordinates and the nearest key or part), its number, the probe that measured it, its tag, and a fix.
3. **One section per special requirement**: hard blocks, tight spots, and fine.
4. **The last audit's findings** (if there was one): fixed, open or changed, with numbers.
5. **Checked and sound**: what was measured and came out fine, with the numbers, so the next audit knows it was looked at.
6. **Not run**, and why.
7. **How to rerun**: the scratch dir, the probes run and their arguments.
8. **Repo state**: `git status` and HEAD at the end.

## Keeping the probes current

`scripts/` is this skill's own code. When a probe breaks because lowpro renamed or moved something, fix the probe in `scripts/` and commit it. When you write a probe that would apply to any lowpro build, give it a docstring saying what it measures and how to run it, add it to `scripts/` and to the table, and commit it. Probes for a special requirement stay in the scratch dir.

When a finding is something the build should always catch, say so in the report: it belongs in `lowpro/build.py`'s checks, not here.

## Probes

All take `AUDIT_PRESET`, `AUDIT_HALF` and `AUDIT_REPO` from the environment; arguments are in each docstring.

| Probe | Measures |
|---|---|
| `mesh_validity.py` | The STLs as a slicer reads them: watertight, winding, degenerate faces; Manifold's status |
| `voids.py` | Shells, sealed voids and islands on Manifold's own mesh (the STL's body split is misleading) |
| `mirror.py` | Left against right mirrored: what differs besides the handed holes |
| `thickness.py` | Wall and skin thickness, by ray cast and by eroded plan slices |
| `overhang.py` | Overhang area, support volume, bridges, in the print orientation |
| `print3mf.py` | The print 3MF as the slicer reads it: settings, placement, what the support volumes mark and miss |
| `plinth.py` | Plinth flatness, contact, skirt, thin features, how the body lands on it |
| `way_free.py` | How far each tile can back out of its pocket before it hits the body |
| `ways_in.py` | Each tile's way into its pocket from the seam side, and what blocks it |
| `tile_path_gap.py` | Least gap from each tile to the body along its way off its pegs, and where |
| `under_map.py` | Map of the body under one key's tile |
| `pockets.py` | Seated tile gaps, pegs, pocket ceiling and ledges, walls between rooms |
| `room_gaps.py` | Least gap between each tile room and every other cut |
| `part_gap.py` | Where each tile room comes near a part's room |
| `switches_caps.py` | Switch hole, clip land, rim room; cap to cap and cap to body, at rest and pressed |
| `capgap.py` | Where each cap comes near the body, written out for marking |
| `screws.py` | Screw holes, inserts, bosses, counterbores, engagement |
| `ports.py` | USB-C, TRRS and reset openings, sliced square to each part |
| `parts_fit.py` | Whether the controller, jack and reset switch go in, and the plinth comes up under them |
| `wells.py` | Wells only: each well's rim height round the cap, what lowers it, wall-top width, overhang |
| `well_holes.py` | Wells only: openings from a well into the case |
| `whatis.py` | What makes the body thin at given points |
| `namecheck.py` | Lowpro names the probes use that no longer exist |
| `run_bounded.sh` | Runs a probe with its memory capped at 2 GB, output to `out/<preset>/` |
| `run_all.sh` | Every probe above that runs without arguments, on one preset's right half |

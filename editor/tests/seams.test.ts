// The seam check (tests/seams.ts) on Swung in: the frame builds as one piece
// on one footprint, every drop stands flush on the rail (but where a fused
// neighbour overlaps it), and the seams found between each class of parts
// (rib, bridge, rail or tie, wall) are no more than they were when pinned. A
// class's count can only fall: if it falls, lower its pin. Two fused drops'
// ribs leave no gap or thin skin between them (no slit), and no more slivers
// than FUSED_SLIVERS.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import Module from 'manifold-3d';
import type { CrossSection, Manifold } from 'manifold-3d';
import { clone, componentFrames, defaults } from '../src/geometry';
import { SIZES, capybara } from '../src/capybara';
import { capybaraSeams, type Seam } from './seams';

const wasm = await Module();
wasm.setup();

/** The class of junction a seam is in: the kinds of part meeting there. */
const kindOf = (name: string) =>
  name.startsWith('bridge')
    ? 'bridge'
    : name.startsWith('wall')
      ? 'wall'
      : name === 'rail' || name === 'tie'
        ? 'rail'
        : 'rib';
function classOf(s: Seam) {
  const kinds = [...new Set(s.parts.map(kindOf))].sort();
  const ribs = s.parts.filter((p) => kindOf(p) === 'rib').length;
  return kinds.length === 1 && kinds[0] === 'rib' && ribs > 1 ? 'rib+rib' : kinds.join('+') || '-';
}

/**
 * Spots per junction class, at most. What is left in each, and why it isn't
 * fixed:
 *  - rib+rib: none. Each finger column's back end turns over its plate's own
 *    across and its drop leans as the plate does, straightening by its foot,
 *    so the backs no longer twist (their creases, ledges and shadings are
 *    gone) and the index's and middle's back drops no longer fuse. Drops that
 *    do fuse (facing corners nearly meeting, widened into each other) must
 *    meet along one line: no gap, no thin skin, and no more than
 *    FUSED_SLIVERS slivers of no area.
 *  - rib: a rib's own seams where it is cut (the joined ends, the switch
 *    seats' trims meeting a rounded end) and its sweep's own slivers, the
 *    thumb row's and the extra keys' among them. The union triangulates a rib
 *    differently with every change near it, though the rib is unchanged
 *    triangle for triangle. A low end (the thumb row's far key's front and
 *    the second extra key's) is cut off level with the rail's top (lowCut),
 *    and so is its plate's underside where that comes lower, beside the
 *    rail's inner edge: a shading each.
 *  - rail: the rail's own corners where its outline turns tighter than the
 *    mesh (the straight outline's corners, and its one turn in, at the
 *    front), and the tie's strip and fillets meeting it (kept inside the
 *    outline). The outline turns in at each drop's corners and runs straight
 *    on to the next (trimmed), so it has a corner at each side of a drop
 *    standing in from the hull (the ring's and pinky's backs, the pinky's
 *    front), each a spot or two where the rail's top and bottom are
 *    triangulated. The rail is level everywhere, never dipping: under the
 *    second extra key's front it stands in the band beside its plate's edge,
 *    over the tile pocket, a sliver there.
 *  - rail+rib: where a column front hangs joined into a thumb plate, the
 *    rail's inner edge passing under a rib's sweep near its foot; shadings
 *    where the leaning back drops' feet meet the rail, and a sliver and a
 *    ledge where the tie meets the rail beside the ring's back foot. The two
 *    low ends stand on the rail's top, their faces its faces (lowDrop,
 *    lowCut): the second extra key's lower side ends 0.28 mm in from where
 *    the outline turns in along it (a ledge), and its plate's underside meets
 *    the rail's top at 15° just inside its inner corner (a crease). Every
 *    other drop's foot is keyed into the rail or tie (footKey), so no foot
 *    meets it edge to edge; the drops on the tie stand wholly on it, clear of
 *    its bends and fillets by tieGap.
 *  - the walls: the outline's hull takes in the limbs' feet, so its inner
 *    side runs straight along them, about 5 mm further out than without
 *    them, and turns in to the inner column's front drops where they stand:
 *    the rail's corners and its meeting with those drops and the thumbs'
 *    (rail, rail+rib) are cut differently there; and where the run passes
 *    the pinky's pillar's foot and the inner home and top keys' fork's back
 *    leg's, the rail's inner edge has two points 0.01 mm and a few nm apart,
 *    a sliver each (rail). rib+wall: none. Each limb's root stands on its
 *    web's own outer edge, its section the lip's, so its sides meet the
 *    web's edge face square however the web slopes, and run straight on
 *    into the lip. Where the web slopes, each limb's section leans across
 *    its sweep's tight turn out of the rib; carried round it untwisted, and
 *    meshed finely enough down its sides, it leaves nothing there. rail+wall: a shading where the inner front fork's front
 *    leg's foot meets the rail's top. wall: a sliver where the pinky's back
 *    pillar's foot meets the rail. The thumb extra row's carried web has a
 *    wishbone about 11 mm on from thumb_x1's corner; the outline's run from thumb_x2's corner goes to its
 *    foot, so the tie meets the rail at an angle and its fillet there leaves
 *    a sliver and a gap (rail).
 *  - bridges (PROTOTYPE): a stepped bridge between facing neighbouring keys
 *    where one fits, and from a key's edge to a web's side facing it (those
 *    on Swung in are in docs/editor-chassis.md); where one lands on a web, what is within landMeet of its
 *    landing is meant. The walls
 *    don't read the bridges, but the frame's one union re-meshes with them,
 *    and the walls' and rail's spots of no area or a few hundredths come and
 *    go with it. bridge+rib 4: the middle–ring and ring–pinky bottom
 *    bridges each leave two ledges where their curved sides meet the ring's
 *    rib (a strip under a millimetre across, or a curl of the side past the
 *    rib's face).
 *  - the base plate under the frame: the frame is cut off level with the
 *    plate's top (skin_mm), and a base screw's boss stands on the plate
 *    against the rail at each of six spots (screwSpots), mostly the outline's
 *    corners, where drops stand; what is within bossMeet of a boss is meant.
 *    rail+rib by 3 down (the corners' joins, now the bosses'); rail by 1 up
 *    (a shading on the cut's underside 3.2 mm from the pinky's back boss).
 *    The thumb row's tip boss was then slid 10.6 mm along the outline, clear
 *    of thumb_x2, which hangs to z 3.7 over the tip: rail+rib by 2 up (the
 *    tip's join, a crease and a ledge at the rail's top, no longer the
 *    boss's); rail by 1 down.
 *  - the Pro Micro: the USB-C and TRRS plugs' ways and the reset switch's
 *    pocket cut through the rail and the back wall, and the jack's collar
 *    fills the inner side's back wishbone round its barrel (wall 2). Pinned
 *    when the FFC adapter was dropped and these became the default, with no
 *    change to the geometry: rail by 4, rail+rib by 2, rail+wall by 1 (a
 *    ledge where the collar meets the rail, at x −49.9, y 21.4) and rib by 1
 *    over the counts with the adapter. The collar's fill meets the fork's
 *    legs and crotch face to face (wall: a sliver each side; at the crotch a
 *    crease and a gap of a hundredth). Its back leg's foot stands exactly on the rail's top,
 *    as every limb's does; with the fill over both, the union keeps the
 *    foot's underside and the rail's top there, a fold (a 180° crease) and a
 *    sliver beside it (rail+wall, by 1 up when the wishbones' sweeps moved
 *    the inner side out and the jack with it, where it was a ledge).
 *  - leaning fronts (PROTOTYPE): each finger column's front end turns over
 *    its plate's own across too, as its back does, so it doesn't twist, and
 *    its drop curves back from the lean to land where it did upright. rib
 *    by 2 down (the shadings where the inner's and pinky's front rounds
 *    twisted); rail+rib by 1 down (a ledge where the pinky's front foot met
 *    the rail).
 *  - the sleeve (seats.ts sleeveBox) replaces the glue posts: under each
 *    plate it fills down round the switch body over the tile, part of its
 *    rib (so a low end's cut takes it too). The posts' legs at the two low
 *    ends filled the wedge where the plate's underside comes down onto the
 *    rail's top beside its inner corner, and their zones were meant; without
 *    them that wedge shows: rail+rib by 7 up (thumb_far and thumb_x2 each a
 *    sliver, a gap of a tenth at its tip and a ledge, thumb_x2 a thin skin
 *    there; the crease and shading each had move), rib by 1 down.
 */
const PINS: Record<string, number> = {
  'bridge+rib': 4,
  rail: 15,
  'rail+rib': 19,
  'rail+wall': 3,
  rib: 7,
  wall: 5,
};

/** Each drop's outer face is checked this far in from its ends, and this far in or out of it. */
const END = 0.3;
const OFF = 0.05;

const inside = (cs: CrossSection, x: number, y: number) =>
  cs
    .intersect(
      new wasm.CrossSection([
        [
          [x - 0.01, y - 0.01],
          [x + 0.01, y - 0.01],
          [x + 0.01, y + 0.01],
          [x - 0.01, y + 0.01],
        ],
      ]),
    )
    .area() > 1e-5;

/** Slivers allowed between two fused drops' ribs (see rib+rib above). */
const FUSED_SLIVERS = 1;

const p = clone(defaults);

test('Capybara: the seams by junction class are no more than pinned', () => {
  const r = capybaraSeams(wasm, p.config);
  // (Not counting zero-volume slivers the booleans leave, as the checks don't.)
  const pieces = r.drawn.decompose();
  assert.equal(pieces.filter((x) => x.volume() > 0.5).length, 1, 'one piece');
  pieces.forEach((x) => x.delete());
  assert.equal(
    new wasm.CrossSection([r.outline], 'NonZero').decompose().length,
    1,
    'one footprint',
  );
  const got: Record<string, number> = {};
  for (const s of r.seams) got[classOf(s)] = (got[classOf(s)] ?? 0) + 1;
  const over = Object.entries(got).filter(([c, n]) => n > (PINS[c] ?? 0));
  assert.deepEqual(
    over,
    [],
    `over the pins (class, spots): ${JSON.stringify(got)} vs ${JSON.stringify(PINS)}\n` +
      r.seams
        .filter((s) => over.some(([c]) => c === classOf(s)))
        .map(
          (s) =>
            `  ${classOf(s)} ${s.kind} at ${s.at.map((x) => x.toFixed(1))} ${s.parts.join(' | ')}`,
        )
        .join('\n'),
  );
  // Fused drops meet along a line: no gap, no thin skin, no slit.
  for (const f of r.fused) {
    const at = r.seams.filter((s) => f.names.every((n) => s.parts.includes(n)));
    const say = (k: string) =>
      `${f.names.join('+')}: ${k} ` +
      at.map((s) => `${s.kind} at ${s.at.map((x) => x.toFixed(1))}`).join('; ');
    assert.deepEqual(
      at.filter((s) => s.kind === 'gap' || s.kind === 'thin'),
      [],
      say('gap or slit'),
    );
    assert(at.filter((s) => s.kind === 'sliver').length <= FUSED_SLIVERS, say('slivers'));
  }
});

test("Capybara: every drop's outer face is flush with the rail over its whole height", () => {
  const frames = componentFrames(p.config);
  const built = capybara(wasm, p.config, frames);
  const parts = built.parts();
  const under: Manifold = wasm.Manifold.union(
    parts.filter((q) => q.name === 'rail' || q.name === 'tie').map((q) => q.solid),
  );
  assert(built.drops.length > 0);
  const bad: string[] = [];
  // The rail (and the tie) is level: railHeight high, the same plan all the way up.
  const H = SIZES.railHeight;
  assert(Math.abs(under.boundingBox().max[2] - H) < 1e-6, 'rail top at railHeight');
  const [foot, top] = [under.slice(0.02).area(), under.slice(H - 0.02).area()];
  assert(Math.abs(foot - top) < 1e-3 * foot, `rail level: ${foot} vs ${top} mm²`);
  for (const dr of built.drops) {
    const at = (c: number, m: number): [number, number] => [
      dr.p[0] + c * dr.c[0] + m * dr.n[0],
      dr.p[1] + c * dr.c[1] + m * dr.n[1],
    ];
    const cs: number[] = [];
    // Where it is fused, its side runs into its neighbour's: only its own face is checked.
    for (let c = dr.free[0] + END; c <= dr.free[1] - END; c += 0.5) cs.push(c);
    // The rail (or the tie) runs under its foot.
    const [over, below] = [under.slice(H + 0.02), under.slice(H - 0.02)];
    for (const c of cs) {
      if (inside(over, ...at(c, -0.5))) bad.push(`${dr.name} ${dr.e}: rail above its foot at ${c}`);
      if (!inside(below, ...at(c, -0.5)))
        bad.push(`${dr.name} ${dr.e}: rail not under its foot at ${c}`);
    }
    // Its foot runs at least dropBend below where its round ends, or
    // it is a low end, come down into the rail.
    if (!dr.into && H > dr.low - SIZES.dropBend + 1e-6)
      bad.push(`${dr.name} ${dr.e}: foot too near the round's end ${dr.low}`);
    if (dr.into && !(dr.low < H + SIZES.dropBend))
      bad.push(`${dr.name} ${dr.e}: into the rail, but its round ends at ${dr.low}`);
    // The frame's face is the plane of its outer face, the floor to its foot.
    for (let z = 0.1; z < H - OFF; z += 0.5) {
      const s = built.frame.slice(z);
      for (const c of cs) {
        if (!inside(s, ...at(c, -OFF)))
          bad.push(`${dr.name} ${dr.e}: notch at c ${c.toFixed(1)}, z ${z}`);
        if (inside(s, ...at(c, OFF)))
          bad.push(`${dr.name} ${dr.e}: proud at c ${c.toFixed(1)}, z ${z}`);
      }
    }
  }
  assert.deepEqual(bad.slice(0, 20), []);
});

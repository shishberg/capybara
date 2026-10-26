# Editor chassis and wiring

How the [editor](../editor/README.md) builds the right hand's chassis and wires it. The
editor guide covers running it, the key layout parameters and the clearance
checks. The tile, its parts, holes and pads are measured from the bought tiles
(see [design status](design-status.md)). The wiring and the
[Pro Micro](pro-micro.md), its TRRS jack and its reset switch are
**provisional**, each marked `provisional` in the configuration. File paths are
relative to `editor/`.

## Construction

The chassis is the **Capybara** frame (`src/capybara.ts`; first inspired by
BastardKB's Skeletyl, and called that until 20 Oct 2026): a rib along each finger column and each thumb row, and one rail
round the outline on the floor. A rib is one swept solid: the key plates as
slabs, curved webs between them tangent to the plates, and a lip and round at
each end, clear of the tile pocket and the switch. Each side of a round
turns over in its own upright plane, so the end comes out heading straight
down, except PROTOTYPE on each finger column's ends: there the round turns
over the plate's own across, so the end keeps the plate's section without
twisting and comes out heading down leaning across as the plate does (about
15° on Swung in). PROTOTYPE: the outline
runs straight from foot to foot: it is the hull of where the ends would drop
straight down and of the outer sides of the first and last columns and the
thumb rows (their plates and tile pockets), with no margin past them, so the
rail is under their edges, taken out round any switch hole's column or tile
that comes down near the floor, so the rail keeps clear of it. Its corners out stay
sharp. Where a drop stands on it, it turns in to the drop's outer face and
runs straight on from the face's corners to the next thing it must take in.
Otherwise it turns in only over open
floor: where the hull bridges a pocket more than 30 mm across its mouth and
more than 2 mm deep that no drop or wall stands in, it turns in once, with one
crisp corner where the lines from the mouth's two ends, tangent to what lies
under, meet. On Swung in that is only between the thumbs and the finger
columns' fronts. An end of the rib that comes down low (whose round would end
less than 1 mm above the rail) has its round drawn as tight as still clears the tile pocket,
the switch and the keys, down to a radius of the wall plus 0.5 mm. An end near the outline
drops to the floor: the rib carried on down from its round as one sweep,
keeping the across and the width it has at the bottom of the round all the
way down to a square foot, so it never twists or splays. It stands straight
down (PROTOTYPE: a finger column's back drop leaves its round leaning and
straightens by its foot, about as an arc would, its foot out along the lean
by its height times the tangent of half the lean: 4.5 to 8 mm on Swung in; a
front drop runs on straight along its lean for half its height, then curves
back to stand upright where it would if its round turned upright, so the
outline and the tie are as they would be without the lean),
or bends out in the end's own plane, along its
heading, until the nearer corner of its outer face meets the outline (on Swung
in only the ring column's back, 0.5 mm); an end whose outline is more than
12 mm out hangs. Its outer face is flush with the rail's
over the rail's whole height, and it bends or rounds only above it. The rail
is level everywhere, its top 6 mm over the floor (4 mm over the base plate it
stands on), and never dips: a low end, whose round,
drawn as tight as it clears, still ends less than 1 mm above the rail's top,
has no drop of its own. Standing on the outline, its round stops 0.5 mm over
the rail's top, and below that its section carries straight on down onto the
rail, its outer face the rail's outer face and its inner face the rail's
inner face (a full wall in), its sides in the round's own upright planes; the
outline turns in along its sides. Whatever of it comes lower (the round's
lower side, the lip, the plate's underside corner) is cut off level with the
rail's top, so it meets the rail along one crisp line, with no fill and no
fairing. On Swung in these are the fronts of the thumb row's far key and the
second extra key; under the second extra key's front the rail stands in the
band beside its plate's edge, over its tile pocket (the tile and the switch
stay clear). Ends further from
the outline would hang, so they are carried on or tied down. First a thumb
row's hanging end is carried on into a hanging column front as one rib (a
sweep from the row's end plate edge to the front's, tangent to both), each row
end and front once, nearest first, where it clears the other keys and doesn't
fold back. Then each column front still hanging within 20 mm of a thumb key's
plate is carried on in a web to that plate's facing edge, so the finger rib
and the thumb rib are one, with no round there. A floor tie, a bar of the
rail's own section, runs across the floor under the ends still hanging, rail
to rail, its legs turning (rounded) to meet the rail square and filleted into
it; the ends that can drop onto it clear of the keys become ordinary drops,
landing square on it clear of its bends and junctions. Each drop stands on the rail alone; between
neighbouring drops the rail runs straight on. PROTOTYPE: two drops of
different ribs whose facing sides stand within 1.5 mm of each other (too
narrow a slit to print cleanly) are **fused**: each is widened on that side
(its section, and its round's, made wider) by half the widest gap plus
0.4 mm, so the two overlap and the union joins them along one crisp line, as
any two ribs meet. The widening runs from their feet up as far as they stand
that close, measured every 0.25 mm, and runs out over 1 mm above that; there
is no fill and no fairing. The rail runs on under the pair without turning in
between them, taking in both widened feet, its outer edge stepping from one
face to the other where they meet (each face flush with it). On Swung in no
drops fuse. PROTOTYPE: **bridges**
tie neighbouring ribs together up at the plates. Where two keys of different
ribs face each other (their facing edges turned at most 35° from square on in
plan, their plates at most 35° apart), a bridge spans the gap, however wide,
at the middle of the stretch both plates' edges share, or the nearest place
to it (tried every 0.5 mm either way) where it can go, 4 mm wide. A key's
plate edge that faces the side of a web (a rib's end carried on from its
key's plate to another key's) within 15 mm, of another rib and joining
neither of the web's keys nor bridged to either of their plates, is bridged
to it as to a plate, landing on the web's side. (A web runs on past the plate
it leaves, so a key bridged to that plate would otherwise be bridged again
across the same gap, just past the first.)

Every bridge is a **step**: out of the higher plate's edge in its plane, down
a leg and in to the lower plate in its plane, so it passes under the lower
key's keycap room rather than through it. It keeps clear of what the keys
hold (the two keys' keycaps only as low as they are pressed) and every other
key's plate; for now it ignores the wires, which are very approximate. The
leg's near face stands just out of the lower plate's edge, or out past what
is under the lower plate's top there with its corner chamfered back past a
keycap room that overhangs it; failing that, out past all of it; failing
that, square to the higher plate's edge, as far out as the leg needs to be
thick. The bridge's top and underside are each one cubic curve across the
leg, leaving the higher plate along its plane and reaching the lower along
its own, the two curves' middles halfway across; the leg is the hull of the
curves' control points, so it holds the curves. Where the bridge is steep
the top is drawn toward the lower plate and the underside toward the higher,
so each bends round its outer corner more gently than round its inner, as a
bent plate's faces do, only as far as leaves the bridge 1.3 mm thick where
it is thinnest. Where no step that thick fits anywhere along the edge, the
thickest that fits, down to 0.4 mm.

On Swung in there are fifteen: between every two neighbouring finger keys
of the matrix (inner–index, index–middle, middle–ring and ring–pinky at every
row), between the thumb rows (thumb_far–thumb_x2, thumb_home–thumb_x1), and
thumb_near to thumb_x1's web. One is thinner, no step 1.3 mm thick fitting
anywhere along its edge: ring_bottom–pinky_bottom (0.8 mm).

The editor's `?bridge=` bar (dev only, ← →) switches to `wired`, where bridges
keep 0.5 mm off the routed wires too; on Swung in that loses none.

Where two keys are too steep or too far round to
web, the rib is parted there, and each end is rounded if the round clears the
other keys' tiles, switches and keycaps, else stops flush at its plate. Drops
are left out where they would hit another key. Nothing is cut out
of the frame. The **base plate** is the bottom section, a separate print: the
outline, `skin_mm` (2 mm) thick, with the frame standing on it. The frame is
cut off level with the plate's top, so the two meet in one flat seam, the
plate's edge flush with the rail's outer face. Six M2×4 pan-head machine screws come up
through the plate (2.3 mm holes) into M2×3 heat-set inserts (about 3.6 mm
across), pressed up from the frame's underside into bosses on the rail's
inside, 6 mm across, from the plate to the rail's top. Each head sits flush
in a counterbore 4.4 mm across and 1.6 mm deep. Over it the plate stands up
in a pad 4.8 mm across and 0.8 mm high, into a socket in the boss's
underside, so 1.2 mm of plate is clamped under the head. The insert's 3.2 mm
hole runs from the pad's top (z 2.8) to the rail's top (z 6), and the screw
reaches z 5.6. The spots (`screwSpots` in `src/chassis.ts`): one at each
corner of the outline that turns out 45° or more, sharpest first, none within
40 mm of another along the outline, and the runs between split evenly so none
is over 80 mm, each boss 3.1 mm in from the outline. A spot whose boss would
come within 0.5 mm of a key tile slides along the outline, half a millimetre
at a time either way, until it doesn't. On Swung in they are at the pinky's
front and back corners, the middle's back, the inner back corner and the
middle of the inner side, about 55 to 80 mm apart, and beside the thumb
row's tip: thumb_x2 hangs to z 3.7 over the tip itself, so that screw is
10.6 mm along the outer edge, toward thumb_x1. The
plate carries the cradles of the Pro Micro, its TRRS jack and its reset
switch (`src/wiring/pro-micro.ts`). The USB-C receptacle is gripped in the back
wall, the jack's plug comes in over the rail on the inner side under the
wishbone nearest the back, whose opening is filled round the barrel (the
collar), and the reset switch sits in a pocket in the back wall; the
[Pro Micro](pro-micro.md) doc describes each. The walls
are **wishbones** (`src/capybara-walls.ts`, `src/capybara-wishbone.ts`): limbs
standing on the outer sides. Each leaves its rib
at the middle of the web between two neighbouring keys, starting from the
web's own outer edge as the rib's mesh has it, in the rib's section, 3.4 mm
wide (every limb and every part of one, root to feet). After a 0.5 mm lip it
sweeps down in one cubic Bézier, leaving along the rib and arriving upright on
the rail, flush, its leading handle reaching no further out than its foot, so
it never leans out past upright. Of those curves it takes the roundest: no
point of its section comes nearer the centre of a bend than 0.5 mm (the ends'
least inner radius), counting the section's lower corner where the web's edge
slopes and the section leans across the bend, and of the curves that allow,
the one whose tightest bend is loosest, so it turns out of the rib only as
tightly as it must and comes on down in a long curve. Its section is carried
round the bend with it and twists to stand along the run only by how far along
the sweep it is, easing in and out, so its tight turn out of the rib doesn't
twist. It comes down as near its web as such a sweep fits, so it stands as
near under its column as clears and a key press loads it down the limb more
than across its joint. A wishbone's trunk sweeps down to upright just over its
fork. A wishbone's
trunk forks into two legs, each slanting at 45° and standing 9 mm
from the trunk's middle (or as near as clears, and no further than halfway to
the next web), so the fork is as high as that spread needs; where no fork fits
under where its sweep can come upright it is a pillar. A limb comes down as near its web as
clears, its legs narrower there before it goes further out. A limb in a plug's way forks
over it: its opening centred on the plug, 2 mm clear each side
and above. Every limb keeps clear of the keys, the drops, the tie and the
plugs. The outline's hull takes in the limbs' feet, so it runs
straight along them, and each foot is turned along its run (up to 5°) so it
stands flush. On Swung in the inner column has a limb at both its webs: at the
bottom–home web a wishbone forking 9.7 mm over the rail, legs 8.8 and 9.0 mm out, and at the home–top web a fork over the TRRS plug, 18.1 mm
up, legs 6.1 and 8.3 mm out. Their rib rises 15° out of the column, so their
sweep turns 105°; they stand 7.1 and 6.9 mm out from their webs' edges, about
5 mm past the outline without them, so the inner side runs that much further
out (the footprint 109.5 mm wide). The pinky has a pillar at both its webs (too
low to fork): they leave falling 15° and would stand 3.4 and 4.3 mm out, but
the outline there is 4.0 and 4.4 mm out, so they run on out to it. The thumbs'
webs between keys are too short. A web an end carries on in to a column's
front is a span with nothing under it, so it gets a limb too, as near the
plate it leaves as clears (from 2.2 mm on from the plate's corner, then each
1 mm further). On Swung in that puts a wishbone under the thumb extra row's
41 mm web to the middle column, about 11 mm on from `thumb_x1`'s corner, just
past where the tie meets the rail, 3.7 mm out from the web's edge, forking
9.7 mm over the rail, legs 7.3 and 9.0 mm out; the outline runs straight from
`thumb_x2`'s corner to its foot. The thumb row's carried web
faces in, over the thumb extra row: no limb is placed where the outline across
its feet is more than 10 mm out. The
assembly is soldered first and lifted in, so the frame has no wire ways and
the checks don't test the wires against it. The board's height to the keycaps'
tops shows under its size.

Under the plates:

- **Tile**: the bought 1U key PCB under each switch (see [the v4 README](../README.md)),
  17 × 17 × 1.6 mm with notched corners, its top 5 mm below the plate top. Its
  **tile pocket** is the space under the plate kept clear for the tile, its parts
  (the hotswap socket, 1.9 mm deep, is the deepest: the pocket reaches 8.8 mm below
  the plate top) and the switch body, open below. A part's `center_mm[2]` is measured from
  the board's top; `src/geometry.ts` has the helpers every use goes through.
- **Plate**: the square a switch clips into, 3 mm thick. It reaches 0.9 mm
  past the 15.8 mm switch seat on each side, or to the edge of the tile pocket if
  that is further, so the plate always covers the tile.
- **Sleeve**: under each plate the chassis fills down round the switch body,
  over the tile's 17 mm footprint, to 0.4 mm over the tile's top (room for
  solder left proud of its holes, and for the print). The switch hole (14.15
  mm) and the clip reliefs are cut through it, so the switch body is held
  over its whole 5 mm below the plate, not only at the 1.5 mm seat. Nothing
  else holds the tile: it hangs from its switch, the hotswap socket's grip on
  the pins holding it up to the sleeve; glue between the two is optional. The
  sleeve is part of its rib, so a low end's cut level with the rail's top
  takes it too.
- Above each plate the chassis is kept clear of the switch housing's rim (the
  seat footprint, up to the keycap's lowest point) and of the keycap's travel.

## Wiring

`src/wiring/` models the hand wiring from these assumptions:

- **Tile holes and pads** (`tile.pads`, measured): through holes near the tile's
  sides, two C, two R, in and out, and V and G nearer the LED; a pad for each of
  in, out, V and G on both the socket and the LED edges, on the underside; and a
  spare C and R hole under the socket, which no wire uses. **One wire per hole or
  pad**: a 22 AWG wire fits a hole, two don't.
- **Matrix**: each hand is 4 rows × 5 columns. The finger rows are RT, RH and RB;
  the five thumbs are row RX. Columns C0–C4 run pinky to inner. Each thumb sits
  on a finger column: x2 on C0, near on C1, x1 on C2, home on C3, far on C4. A
  thumb's column wire goes to its column's pin, so two wires share each column
  pin.
- **Pins**: each net's feeds land on the Pro Micro pin `pro_micro.pins` gives it
  (the [Pro Micro](pro-micro.md#pins) doc says which pins can do what). The
  jack's three link wires and the reset switch's two run from their pins to the
  jack's lugs and the switch's legs.
- **Chains**: each finger column chains its C holes top → home → bottom; each row
  chains its R holes across the columns. A wire arrives at the tile's C (or R)
  hole nearer where it comes from, and the next leaves from the other. LED data
  runs out → in through `wiring.led_order` (the thumbs, then the columns in
  alternating directions). +5 V and GND daisy-chain every tile, arriving at the V
  (or G) hole or the LED-edge V (or G) pad, whichever is nearer, and leaving from
  the other. Each chain has one **feed**, a wire from its nearer end to its
  net's pin.
- **Paths**: wires run close under the tiles. Each end leaves its tile by a
  **leg**, in the key's frame: 0.6 mm down from the pad, an optional shift
  sideways, down to the leg's depth, then straight out to the tile edge facing
  where the wire goes. A pad's own edge is the tile edge it is nearest. A leg over
  that edge runs 0.6 mm below the tile; one along it runs from 2.7 mm down, 0.9 mm
  deeper for each wired pad near the same edge it passes under; between two
  tiles it may also, last of its choices, shift out to the pad's own edge just
  inside the pocket and run along it 0.6 mm below the tile (the **rim**), which
  keeps it shallow where a low edge would take the run under the pads below the
  floor; one across the tile runs just under its parts. A wire between
  two tiles joins its two legs with a straight run. Where that would run into a
  plate, it steps back under the higher tile and drops, or turns a
  corner in plan, or runs under both ends.
- **Wire port**: thumb wires reach the fingers through the wire port, a round
  way (`wiring.port_diameter_mm`, 5 mm) in front of the gap between the inner
  and index columns' bottom keys. Each takes
  its own place in a hexagonal grid across the port, 1.02 mm apart, chosen to
  suit the directions its two ends lie in. A thumb's wires gather just off its
  edge facing the port, each offset as its place, so they run to the port side
  by side. Feeds run down to a **loom** 10 mm above the bottom section, then
  across to the Pro Micro, clear of the jack and the reset switch.
- **Routing**: each wire has many candidate routes (depths, shifts, port places
  and loom levels). Routes
  that run into a tile, its parts or a plate, that shift out past the
  tile's pocket, or whose underside runs below the base plate's top
  (`chassis.skin_mm` above z = 0) are dropped; a wire left with no route fails
  the routing. The wires then negotiate: each takes its cheapest
  route given the others, and routes that meet another wire cost more each
  round until none meet. Pairs that still meet are repaired together with the
  wires most in their way. Routing runs in a worker of its own
  (`src/wiring-worker.ts`) while the build worker builds the chassis, so the wires
  follow an edit when the chassis rebuilds.
- **Wire**: 30 AWG (0.6 mm) for signals, 26 AWG (0.9 mm) for power and ground.
- **Cut length**: each wire's path plus 5 mm at each end. A feed also has a
  40 mm **service loop**: spare wire left slack so the bottom section, with the
  Pro Micro on it, can be lifted off and set beside the body without pulling on a
  solder joint.

The default hand has 105 wires (100 under the keys and five link wires),
210 solder joints and about 6 m of wire.

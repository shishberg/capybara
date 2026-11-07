# Soldering jig

A printed frame that holds a hand's key tiles in their real places, parts side up, while the wires between them are cut and soldered. Each tile sits where it sits under its switch, so the wires come out the right length, and both sides of its holes can be reached.

`make jig` writes `output/jig/capybara-jig-right.stl` and `capybara-jig-left.stl` and fails if a check does. The geometry and its settings are in [`editor/src/jig.ts`](../editor/src/jig.ts).

## How it is built

The chassis is turned over, not mirrored, and levelled on the keys' average normal. The tiles keep their relative positions but not the chassis's tent.

- **Bars:** each tile lies on two ledges on the unused edge-pad bands, past every hole's copper ring, with a post in each corner notch.
- **Stringers:** rails run along each tile's left and right, sharing the gap with the next tile's rails. They stand 0.8 mm clear of the tile, or closer in the narrowest gaps, so every tile's bars are tied at both ends. Tilted rails that cross are filled out to one stringer, so their corners are tied too.
- **Webs:** these join the bars of tiles next to each other along a column. The fingers and thumbs are joined only by the frame.
- **Frame:** a chord runs round the outer edge of the tiles, with triangular struts down to a rail on the bed. A column rises from each foot clear of the tiles to the stand, a matching rail level with the bed and clear over the tiles. Nothing else stands under the tiles.

The build checks that the jig is one piece, each tile and the space over it are clear, every hole has a clear line through it, and both ledges are whole.

## Using it

Print with supports. Drop the tiles in parts side up. To reach the switch side, turn the jig over onto its stand. The tiles are held only by gravity and the posts, so wire or tape them in first.

Struts sit under some of the steeper thumb tiles, past the depth of the bars, so lean the iron past them.

If the iron can't get close enough beside the bars, reduce `JIG.depth`. If the tiles don't fit the posts, change `JIG.fit`.

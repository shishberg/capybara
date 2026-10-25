# Editor cleanup: open decisions

A cleanup of the chassis editor and the `?hand` prototype (tasks T0 to T20,
16 to 19 Oct 2026) is done; its plan, with each task and commit, is in git
history (this file before the C64 case was dropped). The audits behind it
raised these, which change behaviour or need a design call, so they are
listed but not done.

1. **The at-rest and swept keycap checks in solid.ts can barely fail.**
   - The chassis already carved each keycap room, so `atRest` is always 0, and
     `swept` fails only when a pressed cap goes below the plate, which the UI
     rejects.
   - They cost about 40 booleans per build.
   - Option: replace them with config validation plus `roomCuts`.
2. **The wire tubes in the checks are under-sized** (8-segment spheres), so
   they under-report contact.
3. **The `thumbs` fingerprint variant already fails its checks.** Is that
   intended, or should the variant be adjusted?
4. **The thumb-row solver** is three nested fixed-point and bisection layers.
   It could become one joint solve, but the presets would need refitting.
5. **The bottom section is never checked for loose pieces.** A floating
   cradle would pass every check. T4 added a test for the default and a
   3 mm skin, but the report doesn't check it.
6. **The tile pocket is 1.6 mm deeper than its own definition.**
    - chassis.ts measures `tile.components[].center_mm[2]` from the tile's
      underside, where parts.ts, wiring and the config measure it from the top.
      The pocket comes out 11.0 mm deep; its definition gives 9.4.
    - T8 tried the fix. It is unchanged on every variant except `thumbs`: there
      it adds 13 mm³. So the fix was not kept.
7. **The `?hand` solver doesn't say when a loop fails to converge.** This was
    T13 item 5.
    - The loops are `keyAt`, the `thumbRow` home-key settle and the extra
      keys' Newton loop.
    - `thumbRow` already adds an unsettled residual to `miss`, so it shows as
      "short".
    - A visible flag would be a new readout, not a refactor, so T13 left it
      out.
8. **The hardware check doesn't include the switch pads** (`padParts`).
    - Only the solder-access check looks at them.
    - The README used to say pads were checked. T19 corrected the doc
      instead of changing the check.
    - Adding pads to `checkHardware` would be a behaviour change.

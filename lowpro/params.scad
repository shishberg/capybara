// Every parameter of the low-profile Capybara, in millimetres and degrees.
// The layout (layout.scad) reads the hand from hand.scad; everything else is here.
// Sizes marked PROVISIONAL are from datasheets or memory, not measured parts.

// ---------------------------------------------------------------- the key field
// Tent: the whole hand turned about the Y axis, raising the thumb side. 0 is flat.
tent_deg = 6;
// Pitch: the whole hand turned about the X axis, + raising the back (away from you).
pitch_deg = 0;
// Key pitch along a column, between neighbouring caps at their skirts (where
// the column's curve brings them closest). The plate pitch comes out wider.
row_pitch_mm = 19.05;
// Rows per column: home, and this many above (away from you) and below.
rows_above = 1;
rows_below = 1;
// Where the fingertip's reach between rows pivots: 0 at the PIP joint (tight
// well), 1 at the knuckle (MCP: wide, flat). Sets each column's arc radius from
// the measured joints; the home key always faces up, the others tilt to face
// a point that far above it.
reach_mix = 0.5;
// Scale of the measured finger splay (the columns' angles in plan). 0 makes them parallel.
splay_scale = 1;
// Extra fifth column inside the index column (reached by the index finger), its
// gap from the index column centre to centre and its angle to it.
inner_gap_mm = 19.9;
inner_angle_deg = 0;
// How far the columns' home row drops below the measured fingertip prints along
// the key normal (0: the cap tops sit where the fingertips rested).
finger_sink_mm = 0;

// ---------------------------------------------------------------- the thumb
// The thumb keys lie on the circle the thumb's pad swept (hand.scad), at this
// pitch along it (at the caps' skirts, as row_pitch_mm). around_deg is the home key's place round that circle (the
// resting print is at 112 deg; swept in 92, swept out 140, pulled back 168);
// the far key is further round (swept out), the near key less (swept in).
thumb_pitch_mm = 19.05;
thumb_around_deg = 112;
// The thumb keys' cap tops this far below the finger home keys' (0: level, as
// the pads were on the paper).
thumb_drop_mm = 1;
// How much the keys fan round the arc: 1 each key's y along its own radius,
// 0 every key headed like the home key (parallel, as Swung in has them).
// Fanned 1u Cherry caps need a pitch of about 23 mm not to meet at their
// inner corners; parallel ones fit at 19.05.
thumb_fan = 0;
// Each thumb key tilted toward the cluster's middle, degrees per key step
// (a shallow well along the row), and the whole row tilted about its length,
// + facing the thumb's base.
thumb_well_deg = 6;
thumb_tilt_deg = 0;
// The home thumb key's cap, in key units (1 or 1.5; 1.5 lies along the row).
thumb_home_u = 1;
// A second thumb row (x1, x2) toward the thumb's base: flat, on the circle
// inside the row's by thumb_row_gap_mm, a cell apart and centred on the home
// key's angle plus thumb_extra_around_deg, this much lower along their normals.
thumb_extra = true;
thumb_row_gap_mm = 22;
thumb_extra_around_deg = 0;
thumb_extra_lower_mm = 0;

// ---------------------------------------------------------------- the switch (MX)
// The hole, with its print clearance, the 1.5 mm plate the clips land on and
// the housing below the plate.
switch_cutout_mm = 14;
switch_cutout_clearance_mm = 0.15;
plate_mm = 1.5;
switch_rim_mm = 15.6;              // the housing flange over the plate, square
switch_below_plate_mm = 5;         // lower housing, from the plate top to its bottom
switch_clip_width_mm = 5;          // the two clips, centred on the +-y sides
switch_clip_relief_mm = 1.2;       // how far past the hole each relief goes
switch_top_above_plate_mm = 6.6;   // the housing's top over the plate
// Posts and pins below the housing, from the stem centre, +y the pin side (north).
switch_centre_post_d = 4;
switch_side_post_d = 1.7;
switch_side_post_x = 5.08;
switch_pin_d = 1.5;
switch_pins = [[2.54, 5.08], [-3.81, 2.54]];
post_clearance_mm = 0.3;
// The layer a PCB would be (the pins pass through it into the socket).
pcb_layer_mm = 1.6;

// ---------------------------------------------------------------- the keycap (Cherry profile)
// PROVISIONAL: Cherry profile, nominal. Base and top in plan, heights per row
// (R1 top to R4 bottom) at the cap's highest point, the skirt's bottom above
// the plate at rest, and the travel.
cap_base_mm = 18.2;
cap_top_mm = [12.5, 14];
cap_height_mm = [9.3, 8.4, 7.6, 7.6];   // R1, R2, R3, R4
cap_row = [2, 3, 4];                    // the Cherry row of the top, home and bottom rows
cap_row_thumb = 3;
cap_bottom_above_plate_mm = 6;
cap_travel_mm = 4;
cap_clearance_mm = 0.5;                 // caps must stay this far apart
cap_unit_mm = 19.05;                    // a 1.5u cap is 1.5 units less (unit - base)

// ---------------------------------------------------------------- the hotswap socket (Kailh MX)
// Measured on the key tiles (docs/design-status.md): body 11.6 x 6.2 x 1.9,
// centred 0.7 mm to -x and 4 mm to +y of the stem, seen from the switch side.
// Its two solder tabs stick out of the +-x ends, PROVISIONAL sizes.
socket_body_mm = [11.6, 6.2, 1.9];
socket_centre_mm = [-0.7, 4.0];
socket_tab_mm = [2.0, 2.6];             // each tab's reach past the body, and its width
socket_tab_y = [2.54, 5.08];            // the -x tab's y, the +x tab's y
socket_clearance_mm = 0.25;
// Room under each tab to solder a wire to it, from the floor up to the tab.
solder_well_mm = [4.5, 5];

// ---------------------------------------------------------------- wiring
// Channels in the body's underside for the wires, closed by the bottom plate.
channel_w_mm = 2.2;
// The trunks (the inner column's channel, which the row wires join, and the
// one behind the top row that the columns' wires follow to the controller).
trunk_w_mm = 3.5;
// The per-key diode (DO-35, 1N4148), in the column channel: body length and diameter.
diode_mm = [4.0, 2.0];
// Each key's diode leg runs up its column in the channel past the -x tabs;
// each row's wire joins the +x tabs along the cells' north edges. See the README.

// ---------------------------------------------------------------- the body and bottom plate
wall_mm = 4.5;               // the body's wall past the key cells (the back trunk channel runs in it)
outline_round_mm = 2;        // round of the outline's corners (0: sharp)
outline_close_mm = 12;       // gaps between cells narrower than twice this are filled
cell_mm = 19.05;             // the cell each key owns in plan, square
// The body's underside is this far below the lowest socket's top (room for the
// socket, the wires under it and the print's tolerance), flat; the bottom
// plate closes it.
under_socket_mm = 0.6;
bottom_plate_mm = 2;
// The body steps down behind the top row to a roof this thick over the bay's
// pockets (0: no step, the surface blends over the bay).
bay_roof_mm = 3;
plate_gap_mm = 0.1;          // the plate's clearance in the body's rim
// Bosses on the bottom plate hold each socket up against its pocket's ceiling.
boss_clearance_mm = 0.15;
boss_inset_mm = 0.6;         // the boss is this much smaller than the socket body all round
// M2 screws from below into heat-set inserts in the body: insert hole and depth,
// the screw's clearance hole and countersink in the plate.
insert_d = 3.2;
insert_depth_mm = 4;
screw_d = 2.4;
screw_head_d = 4.2;
screw_head_mm = 1.2;
// Screws between these cell corners (pairs of [column index, row offset] etc.)
// are placed by layout.scad; see screw_points() there.

// ---------------------------------------------------------------- controller, battery, switch
// PROVISIONAL: a Pro Micro form factor nRF52840 (nice!nano v2 / SuperMini):
// board, the parts' height over it (the USB-C port is the tallest), how far
// the port stands past the board's end, the port's opening in the wall.
mcu_board_mm = [18, 33.5, 1.0];
mcu_parts_mm = 3.3;
mcu_usb_mm = [9.0, 3.3];         // the port's width and height
mcu_usb_overhang_mm = 1.3;
mcu_usb_opening_mm = [10.5, 5];  // the hole through the back wall for the plug
mcu_clearance_mm = 0.3;
// The board lies along the back wall in a bay behind the inner and index
// columns (layout.scad mcu_bay), its USB-C port out of the inner side wall.
// mcu_turn_deg turns it in plan about its port end.
mcu_turn_deg = 0;
// The reset button on the board, from the port end: across (x) and along (y) the board.
mcu_reset_mm = [0, 14.5];
// Battery: PROVISIONAL 402030 LiPo (about 200 mAh), lying flat in the bay
// beside the board, its 30 mm along the back wall.
battery_mm = [30, 20, 4.2];
battery_clearance_mm = 0.5;
// Power switch: PROVISIONAL MSK-12C02 slide switch, body and its knob's reach.
power_switch = true;
power_switch_mm = [8.6, 3.7, 3.5];
power_switch_knob_mm = [1.5, 3.0, 1.5];  // width, travel + width, how far it stands out
power_switch_offset_mm = 0;              // along the back wall from the board's middle, toward +x

// ---------------------------------------------------------------- rendering
surface_step_mm = 2;   // the top surface's mesh step; finer is slower
$fn = 24;

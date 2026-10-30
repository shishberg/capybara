// The bought parts, each drawn in its own frame, and the room cut for each.
// Key parts are in the key frame (layout.scad): origin at the plate top under
// the stem, +z up, +y the pin side. "room" modules are what the body loses.
// Included by chassis.scad after params.scad, lib.scad and layout.scad.

module box(size, centre = [0, 0, 0]) translate(centre - size / 2) cube(size);

// ---------------------------------------------------------------- MX switch
/** The switch as it stands in the plate: housing over and under the plate,
 * posts and pins below. */
module mx_switch() {
  color("gray") {
    box([switch_rim_mm, switch_rim_mm, switch_top_above_plate_mm], [0, 0, switch_top_above_plate_mm / 2]);
    box([switch_cutout_mm, switch_cutout_mm, switch_below_plate_mm], [0, 0, -switch_below_plate_mm / 2]);
    translate([0, 0, -switch_below_plate_mm - 3.3]) cylinder(d = switch_centre_post_d, h = 3.3);
    for (sx = [-1, 1]) translate([sx * switch_side_post_x, 0, -switch_below_plate_mm - 3.3])
      cylinder(d = switch_side_post_d, h = 3.3);
  }
  color("gold") for (p = switch_pins) translate([p[0], p[1], -switch_below_plate_mm - 3.3])
    cylinder(d = switch_pin_d, h = 3.3);
}
/** The switch's room in the body: the hole through the plate, the housing's
 * pocket under it with the clip reliefs, and the posts' and pins' holes down
 * to the socket's top. */
module mx_switch_room() {
  hole = switch_cutout_mm + 2 * switch_cutout_clearance_mm;
  up = switch_top_above_plate_mm + 20;
  // The hole and the housing below the plate.
  box([hole, hole, up + switch_below_plate_mm], [0, 0, (up - switch_below_plate_mm) / 2]);
  // Clip reliefs on the +-y sides, under the plate's clip land.
  for (sy = [-1, 1]) let(d = switch_clip_relief_mm + switch_cutout_clearance_mm + 0.1)
    box([switch_clip_width_mm, d, switch_below_plate_mm - plate_mm],
        [0, sy * (hole / 2 + d / 2 - 0.1), -plate_mm - (switch_below_plate_mm - plate_mm) / 2]);
  // Posts and pins through the PCB layer, to just above the socket's bottom.
  depth = pcb_layer_mm + socket_body_mm[2] - 0.2;
  translate([0, 0, -switch_below_plate_mm - depth]) {
    cylinder(d = switch_centre_post_d + 2 * post_clearance_mm, h = depth + 0.1);
    for (sx = [-1, 1]) translate([sx * switch_side_post_x, 0, 0])
      cylinder(d = switch_side_post_d + 2 * post_clearance_mm, h = depth + 0.1);
    for (p = switch_pins) translate([p[0], p[1], 0])
      cylinder(d = switch_pin_d + 2 * post_clearance_mm, h = depth + 0.1);
  }
}

// ---------------------------------------------------------------- keycap (Cherry profile)
/** The cap for Cherry row r, u units wide along x, `pressed` mm down. */
module keycap(r, u = 1, pressed = 0) {
  base = [cap_base_mm + (u - 1) * cap_unit_mm, cap_base_mm];
  top = [cap_top_mm[0] + (u - 1) * cap_unit_mm, cap_top_mm[1]];
  h = cap_height_mm[r - 1];
  translate([0, 0, cap_bottom_above_plate_mm - pressed])
    hull() {
      box([base[0], base[1], 0.01], [0, 0, 0.005]);
      box([top[0], top[1], 0.01], [0, 0, h - 0.005]);
    }
}
/** The cap grown by the clearance caps must keep: the collision probe. */
module keycap_probe(r, u = 1, pressed = 0) {
  c = cap_clearance_mm / 2;
  base = [cap_base_mm + (u - 1) * cap_unit_mm + 2 * c, cap_base_mm + 2 * c];
  top = [cap_top_mm[0] + (u - 1) * cap_unit_mm + 2 * c, cap_top_mm[1] + 2 * c];
  h = cap_height_mm[r - 1] + 2 * c;
  translate([0, 0, cap_bottom_above_plate_mm - pressed - c])
    hull() {
      box([base[0], base[1], 0.01], [0, 0, 0.005]);
      box([top[0], top[1], 0.01], [0, 0, h - 0.005]);
    }
}

// ---------------------------------------------------------------- hotswap socket
/** The socket's top (its PCB face) below the plate top. */
function socket_top_z() = -switch_below_plate_mm - pcb_layer_mm;
function socket_bottom_z() = socket_top_z() - socket_body_mm[2];
/** The socket body as two boxes (its dogleg round the centre post), each
 * about a pin cup, within the measured 11.6 x 6.2 envelope; `grow` is the
 * clearance all round. */
module socket_body(grow = 0) {
  e = socket_body_mm; c = socket_centre_mm; t = socket_body_mm[2] + 2 * grow;
  x0 = c[0] - e[0] / 2; x1 = c[0] + e[0] / 2; y0 = c[1] - e[1] / 2; y1 = c[1] + e[1] / 2;
  translate([0, 0, socket_top_z() - t / 2 + grow]) {
    // North-east box about pin 1 (2.54, 5.08).
    translate([(x1 - 2.0 + x0 + 4.5) / 2, (y1 + y0 + 2.3) / 2, 0])
      cube([x1 - x0 - 4.5 - 2.0 + 4.0 + 2 * grow, y1 - y0 - 2.3 + 2 * grow, t], center = true);
    // South-west box about pin 2 (-3.81, 2.54).
    translate([(x0 + x0 + 7.0) / 2, (y0 + y1 - 2.3) / 2, 0])
      cube([7.0 + 2 * grow, y1 - y0 - 2.3 + 2 * grow, t], center = true);
  }
}
/** The two solder tabs, flat in the socket's top face, out of its +-x ends. */
module socket_tabs(grow = 0) {
  e = socket_body_mm; c = socket_centre_mm;
  for (s = [[-1, socket_tab_y[0]], [1, socket_tab_y[1]]])
    translate([c[0] + s[0] * (e[0] / 2 + socket_tab_mm[0] / 2 - 0.3), s[1], socket_top_z() - 0.2])
      cube([socket_tab_mm[0] + 0.6 + 2 * grow, socket_tab_mm[1] + 2 * grow, 0.4 + 2 * grow], center = true);
}
/** The position of the -x (column) and +x (row) tabs' tips in the key frame. */
function socket_tab_tip(side) = [socket_centre_mm[0] + side * (socket_body_mm[0] / 2 + socket_tab_mm[0]),
  side < 0 ? socket_tab_y[0] : socket_tab_y[1], socket_top_z()];
module hotswap_socket() {
  color("dimgray") socket_body();
  color("silver") socket_tabs();
}
/** The socket's pocket: body with clearance and the tabs' slots. Its shaft
 * down to the bottom plate is cut in world axes (chassis.scad socket_shaft),
 * so it stands square to the plate under a tilted key. */
module hotswap_socket_room() {
  socket_body(socket_clearance_mm);
  socket_tabs(socket_clearance_mm);
}

// ---------------------------------------------------------------- diode
module diode() color("orange") rotate([-90, 0, 0]) cylinder(d = diode_mm[1], h = diode_mm[0], center = true);

// ---------------------------------------------------------------- controller (nRF52840 Pro Micro)
/** The board in its frame (layout.scad mcu_frame): origin at the middle of its
 * port end on the floor, +y along the board into the hand, components down
 * toward the bottom plate. The board's underside (its component side) is
 * mcu_parts_mm over the floor. */
function mcu_pcb_z() = mcu_parts_mm;
module mcu_board() {
  b = mcu_board_mm;
  color("darkgreen") translate([-b[0] / 2, 0, mcu_pcb_z()]) cube([b[0], b[1], b[2]]);
  // USB-C port, on the component side, standing past the board's end.
  color("silver") translate([-mcu_usb_mm[0] / 2, -mcu_usb_overhang_mm, mcu_pcb_z() - mcu_usb_mm[1]])
    cube([mcu_usb_mm[0], 7.5 + mcu_usb_overhang_mm, mcu_usb_mm[1]]);
  // Reset button, component side.
  color("white") translate([mcu_reset_mm[0], mcu_reset_mm[1], mcu_pcb_z() - 1.5]) cylinder(d = 3, h = 1.5);
}
/** The board's pocket: from the floor up over the board, with the wall's
 * opening for the plug. */
module mcu_room() {
  b = mcu_board_mm; c = mcu_clearance_mm;
  translate([-b[0] / 2 - c, -c, -1]) cube([b[0] + 2 * c, b[1] + 2 * c, mcu_pcb_z() + b[2] + c + 1]);
  // Through the back wall: the plug's opening, chamfered outward.
  o = mcu_usb_opening_mm;
  translate([0, -wall_mm - 5, mcu_pcb_z() - mcu_usb_mm[1] / 2]) rotate([-90, 0, 0])
    hull() {
      translate([0, 0, 0]) box([o[0] + 2, o[1] + 2, 0.01]);
      translate([0, 0, wall_mm + 5]) box([o[0], o[1], 0.01]);
    }
}
/** The pinhole in the bottom plate over the reset button. */
module mcu_reset_hole() translate([mcu_reset_mm[0], mcu_reset_mm[1], -10]) cylinder(d = 2, h = 20);

// ---------------------------------------------------------------- battery
module battery() color("steelblue") translate([0, 0, battery_mm[2] / 2 + 0.2])
  cube(battery_mm, center = true);
module battery_room() { c = battery_clearance_mm;
  translate([0, 0, (battery_mm[2] + c) / 2 - 1]) cube(battery_mm + [2 * c, 2 * c, c + 2], center = true); }

// ---------------------------------------------------------------- power switch
/** A slide switch in its frame: body centred, knob out of -y (through the wall). */
module power_switch_part() {
  b = power_switch_mm; k = power_switch_knob_mm;
  color("black") cube(b, center = true);
  color("red") translate([0, -b[1] / 2 - k[2] / 2, 0]) cube([k[0], k[2], k[0]], center = true);
}
module power_switch_room() {
  b = power_switch_mm; k = power_switch_knob_mm; c = 0.3;
  cube(b + [2 * c, 2 * c, 2 * c], center = true);
  translate([0, -b[1] / 2 - 5, 0]) cube([k[1] + 2 * c, 10, k[0] + 2 * c], center = true);
  // Open to the floor so the switch drops in from below.
  translate([0, 0, -10]) cube([b[0] + 2 * c, b[1] + 2 * c, 20], center = true);
}

// ---------------------------------------------------------------- screws
module insert_hole() translate([0, 0, -1]) cylinder(d = insert_d, h = insert_depth_mm + 1);
/** The screw's hole through the bottom plate, countersunk from below (z = 0 the plate's underside). */
module screw_hole() {
  translate([0, 0, -1]) cylinder(d = screw_d, h = bottom_plate_mm + 2);
  translate([0, 0, -0.01]) cylinder(d1 = screw_head_d + 2 * screw_head_mm, d2 = screw_d, h = screw_head_mm + screw_d / 2);
}

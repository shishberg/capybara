// The body: the key field's top surface blended from the key cells, walled
// and floored, with the switch and socket pockets, the wire channels, the bay
// for the controller and battery, and the bottom plate with its socket bosses.
// Everything here is in world axes (layout.scad).
include <layout.scad>
include <parts.scad>

// ---------------------------------------------------------------- the top surface
// A height field over the plan: inside a key's cell, its plate's plane; outside
// every cell, the nearby cells' planes blended by distance, each taken at its
// cell's nearest point (so no plane is extrapolated). Over the bays it is
// capped at the bay roof.
INV = [for (k = KEYS) rinv(k[K_FRAME])];
blend_mm = 1.5;

function plane_z(k, x, y) = let(o = origin(k[K_FRAME]), n = axis_z(k[K_FRAME]))
  o[2] - (n[0] * (x - o[0]) + n[1] * (y - o[1])) / n[2];
/** [distance outside key i's cell in its plane, the plane's height at the cell's nearest point]. */
function cell_sample(i, x, y) = let(
    k = KEYS[i], l = xform(INV[i], [x, y, plane_z(k, x, y)]), s = cell_size(k) / 2,
    cx = clamp(l[0], -s[0], s[0]), cy = clamp(l[1], -s[1], s[1])
  ) [norm([abs(l[0]) - cx, abs(l[1]) - cy]), xform(k[K_FRAME], [cx, cy, 0])[2]];
/** The pocket height the bays need, from the floor, and their roof over it. */
function bay_pocket_h() = max(mcu_parts_mm + mcu_board_mm[2] + mcu_clearance_mm,
  battery_mm[2] + battery_clearance_mm, power_switch ? power_switch_mm[2] + 0.6 : 0);
function bay_roof_z() = FLOOR_Z + bay_pocket_h() + bay_roof_mm;
function in_rect(r, x, y) = x >= r[0][0] && x <= r[1][0] && y >= r[0][1] && y <= r[1][1];
function in_bay(x, y) = len([for (b = bays()) if (in_rect(b, x, y)) 1]) > 0;
/** The shelf that steps down to the bay roof: the bays' span with their
 * walls, except
 * within a mesh step and a millimetre of any cell (so the step starts clear of it). */
function shelf_rect() = let(B = bays(), e = wall_mm + outline_round_mm + 1)
  [[vmin([for (b = B) b[0][0]]) - e, vmin([for (b = B) b[0][1]])], [vmax([for (b = B) b[1][0]]) + e, vmax([for (b = B) b[1][1]]) + e]];
function on_shelf(x, y, ss) = in_rect(shelf_rect(), x, y) && vmin([for (s = ss) s[0]]) > surface_step_mm + 1;
function top_z(x, y) = let(
    ss = [for (i = [0 : len(KEYS) - 1]) cell_sample(i, x, y)],
    inside = [for (s = ss) if (s[0] <= 0) s[1]],
    w = [for (s = ss) 1 / pow(s[0] + blend_mm, 3)],
    z = len(inside) > 0 ? vmax(inside) : sum([for (i = [0 : len(ss) - 1]) w[i] * ss[i][1]]) / sum(w)
  ) bay_roof_mm > 0 && on_shelf(x, y, ss) ? min(z, bay_roof_z()) : z;

// ---------------------------------------------------------------- the outline
SCREWS = screw_points();
/** The cells, bays and channel paths in plan, before the wall. */
module cells_2d() {
  for (k = KEYS) polygon(cell_corners(k));
  for (b = bays()) translate(b[0]) square(b[1] - b[0]);
  for (c = channels(), i = [0 : len(c[1]) - 2]) hull() for (p = [c[1][i], c[1][i + 1]])
    translate(xy(p)) circle(r = c[0] / 2 + 1, $fn = 16);
}
/** The body's footprint: the cells closed up (gaps narrower than
 * 2 * outline_close_mm filled, with a round of that radius where they meet
 * the outline), the wall round them, and the convex corners rounded. */
module footprint_2d() offset(r = outline_round_mm) offset(r = -outline_round_mm) offset(r = wall_mm)
  offset(r = -outline_close_mm) offset(r = outline_close_mm) cells_2d();
/** The plan's bounding box, [[x0, y0], [x1, y1]], with room for the wall. */
function plan_bbox() = let(
    pts = concat([for (k = KEYS) each cell_corners(k)], SCREWS, [for (b = bays()) each b]),
    xs = [for (p = pts) p[0]], ys = [for (p = pts) p[1]], m = wall_mm + outline_round_mm + 2
  ) [[vmin(xs) - m, vmin(ys) - m], [vmax(xs) + m, vmax(ys) + m]];
BBOX = plan_bbox();

// ---------------------------------------------------------------- the surface solid
/** The height field as a solid, from below the floor up to the surface. */
module surface_solid() {
  b = BBOX; st = surface_step_mm;
  nx = ceil((b[1][0] - b[0][0]) / st) + 1; ny = ceil((b[1][1] - b[0][1]) / st) + 1;
  xs = [for (i = [0 : nx - 1]) b[0][0] + i * st]; ys = [for (j = [0 : ny - 1]) b[0][1] + j * st];
  top = [for (j = [0 : ny - 1], i = [0 : nx - 1]) [xs[i], ys[j], top_z(xs[i], ys[j])]];
  bot = [for (j = [0 : ny - 1], i = [0 : nx - 1]) [xs[i], ys[j], FLOOR_Z - 1]];
  N = nx * ny;
  function t(i, j) = j * nx + i;
  function u(i, j) = N + j * nx + i;
  faces = concat(
    [for (j = [0 : ny - 2], i = [0 : nx - 2]) each
      [[t(i, j), t(i, j + 1), t(i + 1, j + 1)], [t(i, j), t(i + 1, j + 1), t(i + 1, j)]]],
    [for (j = [0 : ny - 2], i = [0 : nx - 2]) [u(i, j), u(i + 1, j), u(i + 1, j + 1), u(i, j + 1)]],
    [for (i = [0 : nx - 2]) [t(i, 0), t(i + 1, 0), u(i + 1, 0), u(i, 0)]],
    [for (i = [0 : nx - 2]) [t(i + 1, ny - 1), t(i, ny - 1), u(i, ny - 1), u(i + 1, ny - 1)]],
    [for (j = [0 : ny - 2]) [t(0, j + 1), t(0, j), u(0, j), u(0, j + 1)]],
    [for (j = [0 : ny - 2]) [t(nx - 1, j), t(nx - 1, j + 1), u(nx - 1, j + 1), u(nx - 1, j)]]);
  polyhedron(points = concat(top, bot), faces = faces, convexity = 20);
}
/** The body before anything is cut from it. */
module blank() intersection() {
  surface_solid();
  translate([0, 0, FLOOR_Z]) linear_extrude(200) footprint_2d();
}

// ---------------------------------------------------------------- wiring points
// In a key's frame, at the socket's top: the column line past the -x tab
// (col_x), the row riser over the +x tab (row_x), and the north edge (ne_y).
col_x = socket_centre_mm[0] - socket_body_mm[0] / 2 - socket_tab_mm[0] + 1.1;
row_x = socket_centre_mm[0] + socket_body_mm[0] / 2 + socket_tab_mm[0];
ne_y = cell_mm / 2 - channel_w_mm / 2;
out_y = cell_mm / 2 + 1.5;    // a trunk point just past a cell's edge
function at(k, p) = xform(k[K_FRAME], [p[0], p[1], socket_top_z()]);
function c_tab(k) = at(k, [col_x, socket_tab_y[0]]);
function r_tab(k) = at(k, [row_x, socket_tab_y[1]]);
function nw(k) = at(k, [col_x, ne_y]);
function ne(k) = at(k, [row_x, ne_y]);
/** The back trunk's point behind a top key, held under the bay roof. */
function back_pt(k) = let(p = at(k, [col_x, out_y]))
  [p[0], p[1], bay_roof_mm > 0 ? min(p[2], bay_roof_z() - 1.5) : p[2]];
function front_pt(k) = at(k, [col_x, -out_y]);
/** Where the trunks enter the controller's bay: just inside its back corner by the column. */
function bay_entry() = let(b = mcu_bay()) [b[1][0] - 3, b[1][1] - 3, FLOOR_Z + bay_pocket_h() - 0.3];
function finger_key(col, row) = [for (k = KEYS) if (k[K_GROUP] == "finger" && k[K_COL] == col && k[K_ROW] == row) k][0];
function thumb(name) = key_named(str("thumb_", name));
/** The channels as polylines [width, [points...]] in world. */
function channels() = concat(
  // Each finger column: front trunk point, its keys' column tabs, back trunk point.
  [for (c = [0 : 4]) [c == 0 ? trunk_w_mm : channel_w_mm, concat(
    [front_pt(finger_key(c, -rows_below))],
    [for (r = [-rows_below : rows_above]) c_tab(finger_key(c, r))],
    [back_pt(finger_key(c, rows_above))])]],
  // The back trunk, pinky to inner column and into the bay, and the front trunk.
  [[trunk_w_mm, concat([for (c = [4 : -1 : 0]) back_pt(finger_key(c, rows_above))], [bay_entry()])]],
  [[trunk_w_mm, concat([for (c = [4 : -1 : 0]) front_pt(finger_key(c, -rows_below))])]],
  [[trunk_w_mm, [front_pt(finger_key(1, -rows_below)), ne(thumb("near"))]]],
  // Each finger row: from each key's tab up to its north edge, across to the
  // next cell's north edge and along it to that key's tab; the inner column's
  // feeds its wire into the column channel.
  [for (r = [-rows_below : rows_above]) each concat(
    [[channel_w_mm, [r_tab(finger_key(0, r)), ne(finger_key(0, r)), nw(finger_key(0, r))]]],
    [for (c = [0 : 3]) [channel_w_mm,
      [r_tab(finger_key(c, r)), ne(finger_key(c, r)), nw(finger_key(c + 1, r)), ne(finger_key(c + 1, r)), r_tab(finger_key(c + 1, r))]]])],
  // The thumb row: a trunk along the three keys' north edges (the row wire and
  // the column wires on their way to the front trunk), each key's tabs risen to it.
  [[trunk_w_mm, [ne(thumb("near")), nw(thumb("near")), ne(thumb("home")), nw(thumb("home")), ne(thumb("far")), nw(thumb("far"))]]],
  [for (n = ["near", "home", "far"]) each [[channel_w_mm, [r_tab(thumb(n)), ne(thumb(n))]], [channel_w_mm, [c_tab(thumb(n)), nw(thumb(n))]]]],
  // The extra keys: their tabs risen to their north edges, joined to the gap
  // between the row keys over them.
  thumb_extra ? [for (x = [["x1", "near", "home"], ["x2", "home", "far"]]) let(k = thumb(x[0]),
      g = (nw(thumb(x[1])) + ne(thumb(x[2]))) / 2) each [
    [channel_w_mm, [r_tab(k), ne(k), nw(k), c_tab(k)]],
    [channel_w_mm, [(ne(k) + nw(k)) / 2, g]]]] : []);
/** A channel's post at a world point: from under the floor up to the point,
 * or to the bay's pocket where the point is in a bay. */
module post(p, w) {
  z = in_bay(p[0], p[1]) ? min(p[2], FLOOR_Z + bay_pocket_h() - 0.3) : p[2];
  translate([p[0] - w / 2, p[1] - w / 2, FLOOR_Z - 1]) cube([w, w, z - FLOOR_Z + 1]);
}
module channel(w, pts) for (i = [0 : len(pts) - 2]) hull() { post(pts[i], w); post(pts[i + 1], w); }
module channels() for (c = channels()) channel(c[0], c[1]);
/** Room for the diode in the column channel, over the column tab. */
module diode_rooms() for (k = KEYS) multmatrix(k[K_FRAME])
  translate([col_x, (socket_tab_y[0] + ne_y) / 2 + 1, socket_top_z() - diode_mm[1] / 2 - 0.4])
    cube([diode_mm[1] + 0.8, diode_mm[0] + 0.8, diode_mm[1] + 0.8], center = true);
function diode_frame(k) = k[K_FRAME] * trans([col_x, (socket_tab_y[0] + ne_y) / 2 + 1, socket_top_z() - diode_mm[1] / 2 - 0.4]);
/** Room under each socket tab to solder to it. */
module solder_wells() for (k = KEYS) multmatrix(k[K_FRAME]) for (side = [-1, 1]) let(t = socket_tab_tip(side))
  translate([t[0] - solder_well_mm[0] / 2, t[1] - solder_well_mm[1] / 2, -40]) cube([solder_well_mm[0], solder_well_mm[1], 40 + t[2]]);

// ---------------------------------------------------------------- the body
module key_rooms() for (k = KEYS) multmatrix(k[K_FRAME]) { mx_switch_room(); hotswap_socket_room(); }
module bay_rooms() {
  multmatrix(MCU) mcu_room();
  multmatrix(BATTERY) battery_room();
  if (power_switch) multmatrix(POWER_SWITCH) power_switch_room();
}
module insert_holes() for (p = SCREWS) translate([p[0], p[1], FLOOR_Z]) insert_hole();
module body() difference() {
  blank();
  key_rooms();
  solder_wells();
  channels();
  diode_rooms();
  bay_rooms();
  insert_holes();
}

// ---------------------------------------------------------------- the bottom plate
/** The boss under key k's socket: the socket's shaft, inset, from the plate up
 * to just under the socket. */
module socket_boss(k) intersection() {
  multmatrix(k[K_FRAME]) hull() { socket_body(-boss_inset_mm); translate([0, 0, -60]) socket_body(-boss_inset_mm); }
  multmatrix(k[K_FRAME]) translate([0, 0, socket_bottom_z() - boss_clearance_mm - 100]) cube([80, 80, 200], center = true);
  translate([BBOX[0][0], BBOX[0][1], FLOOR_Z - 0.01]) cube([BBOX[1][0] - BBOX[0][0], BBOX[1][1] - BBOX[0][1], 100]);
}
module bottom_plate() {
  difference() {
    linear_extrude(bottom_plate_mm) footprint_2d();
    for (p = SCREWS) translate([p[0], p[1], 0]) screw_hole();
    multmatrix(MCU) mcu_reset_hole();
  }
  for (k = KEYS) socket_boss(k);
}

// ---------------------------------------------------------------- the parts, for the assembly
module switches() for (k = KEYS) multmatrix(k[K_FRAME]) mx_switch();
module keycaps(pressed = 0) for (k = KEYS) multmatrix(k[K_FRAME]) color("ivory") keycap(k[K_CAPROW], k[K_UNITS], pressed);
module sockets() for (k = KEYS) multmatrix(k[K_FRAME]) hotswap_socket();
module diodes() for (k = KEYS) multmatrix(diode_frame(k)) diode();
module electronics() {
  multmatrix(MCU) mcu_board();
  multmatrix(BATTERY) battery();
  if (power_switch) multmatrix(POWER_SWITCH) power_switch_part();
}

// ---------------------------------------------------------------- checks
/** Pairs of keys near enough for their caps to meet. */
function near_pairs() = [for (i = [0 : len(KEYS) - 2], j = [i + 1 : len(KEYS) - 1])
  if (norm(origin(KEYS[i][K_FRAME]) - origin(KEYS[j][K_FRAME])) < 2.2 * cell_mm) [i, j]];
/** Where caps meet, with their clearance: at rest, and each key pressed with
 * its neighbours at rest. Empty when the layout is clear. */
module cap_collisions() for (p = near_pairs(), press = [[0, 0], [cap_travel_mm, 0], [0, cap_travel_mm]])
  intersection() {
    multmatrix(KEYS[p[0]][K_FRAME]) keycap_probe(KEYS[p[0]][K_CAPROW], KEYS[p[0]][K_UNITS], press[0]);
    multmatrix(KEYS[p[1]][K_FRAME]) keycap_probe(KEYS[p[1]][K_CAPROW], KEYS[p[1]][K_UNITS], press[1]);
  }
/** The board's height: from the floor to the highest cap's top, and the lowest. */
function cap_tops() = [for (k = KEYS) cap_top(k)[2]];
function report() = let(
    b = BBOX, tops = cap_tops(), plates = [for (k = KEYS) origin(k[K_FRAME])[2]]
  ) str("plate tops ", r2(vmin(plates)), " to ", r2(vmax(plates)), " mm over the desk; cap tops ",
        r2(vmin(tops)), " to ", r2(vmax(tops)), " mm; bay roof ", r2(bay_roof_z()),
        " mm; fingertip reach between rows ",
        [for (i = [0 : 3]) r2(finger_plate_pitch(i) * finger_reach_radius(i) / finger_plate_radius(i))],
        " mm (index to pinky); plan about ", r2(b[1][0] - b[0][0] - 2 * (outline_round_mm + 2)), " x ", r2(b[1][1] - b[0][1] - 2 * (outline_round_mm + 2)), " mm");

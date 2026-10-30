// The body: the key field's top surface blended from the key cells, walled,
// a shell of one thickness, with the switch and socket pockets and the wire
// channels; and the bottom plate: a plinth up to the body's underside, with
// the socket bosses and the well for the controller and battery.
// Everything here is in world axes (layout.scad).
include <layout.scad>
include <parts.scad>

// ---------------------------------------------------------------- the top surface
// A height field over the plan: inside a key's cell, its plate's plane; outside
// every cell, the nearby cells' planes blended by distance, each taken at its
// cell's nearest point (so no plane is extrapolated). The body's underside is
// the same field FLOOR_DROP lower, the plate's top plate_gap_mm under that.
INV = [for (k = KEYS) rinv(k[K_FRAME])];
blend_mm = 1.5;

function plane_z(k, x, y) = let(o = origin(k[K_FRAME]), n = axis_z(k[K_FRAME]))
  o[2] - (n[0] * (x - o[0]) + n[1] * (y - o[1])) / n[2];
/** [distance outside key i's cell in its plane, the plane's height at the cell's nearest point]. */
function cell_sample(i, x, y) = let(
    k = KEYS[i], l = xform(INV[i], [x, y, plane_z(k, x, y)]), s = cell_size(k) / 2,
    cx = clamp(l[0], -s[0], s[0]), cy = clamp(l[1], -s[1], s[1])
  ) [norm([l[0] - cx, l[1] - cy]), xform(k[K_FRAME], [cx, cy, 0])[2]];
function top_z(x, y) = let(
    ss = [for (i = [0 : len(KEYS) - 1]) cell_sample(i, x, y)],
    inside = [for (s = ss) if (s[0] <= 0) s[1]],
    w = [for (s = ss) 1 / pow(s[0] + blend_mm, 3)]
  ) len(inside) > 0 ? vmax(inside) : sum([for (i = [0 : len(ss) - 1]) w[i] * ss[i][1]]) / sum(w);
function floor_z(x, y) = top_z(x, y) - FLOOR_DROP;
function plate_z(x, y) = floor_z(x, y) - plate_gap_mm;

// ---------------------------------------------------------------- the outline
SCREWS = screw_points();
/** The cells, bays and channel paths in plan, before the wall. */
module cells_2d() {
  for (k = KEYS) polygon(cell_corners(k));
  for (b = bays()) translate(b[0]) square(b[1] - b[0]);
  channels_2d();
}
/** The channel paths in plan, with a margin round them. */
module channels_2d(group) for (c = channels(), i = [0 : len(c[1]) - 2]) if (is_undef(group) || c[2] == group)
  hull() for (p = [c[1][i], c[1][i + 1]]) translate(xy(p)) circle(r = c[0] / 2 + 1, $fn = 16);
/** The finger field (its cells, the bays and its channels) and the thumb
 * cluster each as a convex hull, and the bridge joining them: the thumb row,
 * the two bottom keys nearest it, the bays on the inner side and the channel
 * between the two, so the inner edge runs straight from the bays to the thumb. */
module hulls_2d() {
  hull() { for (k = KEYS) if (k[K_GROUP] == "finger") polygon(cell_corners(k)); for (b = bays()) translate(b[0]) square(b[1] - b[0]); channels_2d("finger"); }
  hull() { for (k = KEYS) if (k[K_GROUP] != "finger") polygon(cell_corners(k)); channels_2d("thumb"); }
  hull() {
    for (k = KEYS) if (k[K_GROUP] == "thumb" || (k[K_GROUP] == "finger" && k[K_COL] <= 1 && k[K_ROW] == -rows_below)) polygon(cell_corners(k));
    for (b = bays()) translate(b[0]) square(b[1] - b[0]);
    channels_2d("bridge");
  }
}
/** The body's footprint: outline_style "hulls" is the hulls joined, "closed"
 * the cells and channel paths closed up (gaps narrower than 2 * outline_close_mm
 * filled). Either way the gaps that remain get a round of outline_close_mm, the
 * wall goes round it and the convex corners are rounded to outline_round_mm. */
module footprint_2d() offset(r = outline_round_mm) offset(r = -outline_round_mm) offset(r = wall_mm)
  offset(r = -outline_close_mm) offset(r = outline_close_mm) {
    if (outline_style == "hulls") hulls_2d(); else cells_2d();
  }
/** The plan's bounding box, [[x0, y0], [x1, y1]], with room for the wall. */
function plan_bbox() = let(
    pts = concat([for (k = KEYS) each cell_corners(k)], SCREWS, [for (b = bays()) each b]),
    xs = [for (p = pts) p[0]], ys = [for (p = pts) p[1]], m = wall_mm + outline_round_mm + 2
  ) [[vmin(xs) - m, vmin(ys) - m], [vmax(xs) + m, vmax(ys) + m]];
BBOX = plan_bbox();

// ---------------------------------------------------------------- the surface solids
// The height field sampled on a grid over the plan, once.
GRID = let(b = BBOX, st = surface_step_mm) [
  ceil((b[1][0] - b[0][0]) / st) + 1, ceil((b[1][1] - b[0][1]) / st) + 1];
GRID_XS = [for (i = [0 : GRID[0] - 1]) BBOX[0][0] + i * surface_step_mm];
GRID_YS = [for (j = [0 : GRID[1] - 1]) BBOX[0][1] + j * surface_step_mm];
TOP = [for (j = [0 : GRID[1] - 1], i = [0 : GRID[0] - 1]) top_z(GRID_XS[i], GRID_YS[j])];
/** The solid between two height fields over the grid, each a z per grid point
 * (row by row) or a single z. */
module field_solid(hi, lo) {
  nx = GRID[0]; ny = GRID[1]; N = nx * ny;
  function z(f, n) = is_list(f) ? f[n] : f;
  top = [for (j = [0 : ny - 1], i = [0 : nx - 1]) [GRID_XS[i], GRID_YS[j], z(hi, j * nx + i)]];
  bot = [for (j = [0 : ny - 1], i = [0 : nx - 1]) [GRID_XS[i], GRID_YS[j], z(lo, j * nx + i)]];
  function t(i, j) = j * nx + i;
  function u(i, j) = N + j * nx + i;
  faces = concat(
    [for (j = [0 : ny - 2], i = [0 : nx - 2]) each
      [[t(i, j), t(i, j + 1), t(i + 1, j + 1)], [t(i, j), t(i + 1, j + 1), t(i + 1, j)]]],
    [for (j = [0 : ny - 2], i = [0 : nx - 2]) each
      [[u(i, j), u(i + 1, j + 1), u(i, j + 1)], [u(i, j), u(i + 1, j), u(i + 1, j + 1)]]],
    [for (i = [0 : nx - 2]) [t(i, 0), t(i + 1, 0), u(i + 1, 0), u(i, 0)]],
    [for (i = [0 : nx - 2]) [t(i + 1, ny - 1), t(i, ny - 1), u(i, ny - 1), u(i + 1, ny - 1)]],
    [for (j = [0 : ny - 2]) [t(0, j + 1), t(0, j), u(0, j), u(0, j + 1)]],
    [for (j = [0 : ny - 2]) [t(nx - 1, j), t(nx - 1, j + 1), u(nx - 1, j + 1), u(nx - 1, j)]]);
  polyhedron(points = concat(top, bot), faces = faces, convexity = 20);
}
/** The body before anything is cut from it: the shell between the top surface
 * and its underside, within the footprint, its top edge rounded. The round is
 * a stack: at each of top_round_steps insets from the wall, the top lowered by
 * the quarter circle's drop there, all unioned, then the underside cut. */
module blank() {
  r = top_round_mm; n = r > 0 ? ($preview ? min(4, top_round_steps) : top_round_steps) : 0;
  difference() {
    union() for (i = [0 : n]) let(a = 90 * i / max(n, 1), d = r * (1 - cos(a)), dz = r * (1 - sin(a)))
      intersection() {
        translate([0, 0, -dz]) field_solid(TOP, -1);
        linear_extrude(200) offset(r = -d) footprint_2d();
      }
    field_solid([for (z = TOP) z - FLOOR_DROP], -2);
  }
}
/** The plinth before anything is cut from it: from the desk up to the body's underside. */
module plinth_blank() intersection() {
  field_solid([for (z = TOP) z - FLOOR_DROP - plate_gap_mm], -1);
  linear_extrude(200) footprint_2d();
}

// ---------------------------------------------------------------- the bay's well
/** The pocket height the parts need over the well's floor. */
function bay_pocket_h() = max(mcu_parts_mm + mcu_board_mm[2] + mcu_clearance_mm,
  battery_mm[2] + battery_clearance_mm, power_switch ? power_switch_mm[2] + 0.6 : 0);
/** The well's floor: bay_under_mm below the parts' room under the lowest point
 * of the body's underside over the bays, but never thinner than the plate's minimum. */
function bay_floor_z() = let(
    lows = [for (b = bays(), i = [0 : 4], j = [0 : 4])
      floor_z(b[0][0] + (b[1][0] - b[0][0]) * i / 4, b[0][1] + (b[1][1] - b[0][1]) * j / 4)]
  ) max(bottom_plate_mm, vmin(lows) - bay_pocket_h() - bay_under_mm);
BAY_Z = bay_floor_z();
MCU = trans([0, 0, BAY_Z]) * mcu_frame();
BATTERY = trans([0, 0, BAY_Z]) * battery_frame();
POWER_SWITCH = trans([0, 0, BAY_Z]) * power_switch_frame();
/** The well: both bays' rectangles, open from the well's floor up through the
 * plate's top (and into the body, where the parts need more than the plate has). */
module well() for (b = bays()) translate([b[0][0], b[0][1], BAY_Z]) cube([b[1][0] - b[0][0], b[1][1] - b[0][1], 100]);

// ---------------------------------------------------------------- wiring points
// In a key's frame, at the socket's top: the column line past the -x tab
// (col_x), the row riser over the +x tab (row_x), and the north edge (ne_y).
col_x = socket_centre_mm[0] - socket_body_mm[0] / 2 - 0.3;   // overlapping the socket's shaft, so no sliver is left between them under the tent
row_x = socket_centre_mm[0] + socket_body_mm[0] / 2 + socket_tab_mm[0];
ne_y = cell_mm / 2 - channel_w_mm / 2;
out_y = cell_mm / 2 + 1.5;    // a trunk point just past a cell's edge
function at(k, p) = xform(k[K_FRAME], [p[0], p[1], socket_top_z()]);
function c_tab(k) = at(k, [col_x, socket_tab_y[0]]);
function r_tab(k) = at(k, [row_x, socket_tab_y[1]]);
function nw(k) = at(k, [col_x, ne_y]);
function ne(k) = at(k, [row_x, ne_y]);
function back_pt(k) = at(k, [col_x, out_y]);
function front_pt(k) = at(k, [col_x, -out_y]);
/** Where the back trunk reaches the well: just inside its back corner by the column. */
function bay_entry() = let(b = mcu_bay(), x = b[1][0] - 3, y = b[1][1] - 3) [x, y, floor_z(x, y) + 3];
function finger_key(col, row) = [for (k = KEYS) if (k[K_GROUP] == "finger" && k[K_COL] == col && k[K_ROW] == row) k][0];
function thumb(name) = key_named(str("thumb_", name));
/** The channels as polylines [width, [points...], group] in world; the group
 * ("finger", "thumb" or "bridge") says which hull of the footprint holds it. */
function channels() = concat(
  // Each finger column: front trunk point, its keys' column tabs, back trunk point.
  [for (c = [0 : 4]) [c == 0 ? trunk_w_mm : channel_w_mm, concat(
    [front_pt(finger_key(c, -rows_below))],
    [for (r = [-rows_below : rows_above]) c_tab(finger_key(c, r))],
    [back_pt(finger_key(c, rows_above))]), "finger"]],
  // The back trunk, pinky to inner column and into the bay, and the front trunk.
  [[trunk_w_mm, concat([for (c = [4 : -1 : 0]) back_pt(finger_key(c, rows_above))], [bay_entry()]), "finger"]],
  [[trunk_w_mm, concat([for (c = [4 : -1 : 0]) front_pt(finger_key(c, -rows_below))]), "finger"]],
  [[trunk_w_mm, [front_pt(finger_key(1, -rows_below)), ne(thumb("near"))], "bridge"]],
  // Each finger row: from each key's tab up to its north edge, across to the
  // next cell's north edge and along it to that key's tab; the inner column's
  // feeds its wire into the column channel.
  [for (r = [-rows_below : rows_above]) each concat(
    [[channel_w_mm, [r_tab(finger_key(0, r)), ne(finger_key(0, r)), nw(finger_key(0, r))], "finger"]],
    [for (c = [0 : 3]) [channel_w_mm,
      [r_tab(finger_key(c, r)), ne(finger_key(c, r)), nw(finger_key(c + 1, r)), ne(finger_key(c + 1, r)), r_tab(finger_key(c + 1, r))], "finger"]])],
  // The thumb row: a trunk along the three keys' north edges (the row wire and
  // the column wires on their way to the front trunk), each key's tabs risen to it.
  [[trunk_w_mm, [ne(thumb("near")), nw(thumb("near")), ne(thumb("home")), nw(thumb("home")), ne(thumb("far")), nw(thumb("far"))], "thumb"]],
  [for (n = ["near", "home", "far"]) each [[channel_w_mm, [r_tab(thumb(n)), ne(thumb(n))], "thumb"], [channel_w_mm, [c_tab(thumb(n)), nw(thumb(n))], "thumb"]]],
  // The extra keys: their tabs risen to their north edges, joined to the gap
  // between the row keys over them.
  thumb_extra ? [for (x = [["x1", "near", "home"], ["x2", "home", "far"]]) let(k = thumb(x[0]),
      g = (nw(thumb(x[1])) + ne(thumb(x[2]))) / 2) each [
    [channel_w_mm, [r_tab(k), ne(k), nw(k), c_tab(k)], "thumb"],
    [channel_w_mm, [(ne(k) + nw(k)) / 2, g], "thumb"]]] : []);
/** A channel's post at a world point: from under the body's underside up to
 * the point. It starts 3 mm under, so the hull between two posts stays open
 * to the underside where that curves up between them. */
module post(p, w) {
  f = floor_z(p[0], p[1]) - 3;
  translate([p[0] - w / 2, p[1] - w / 2, f]) cube([w, w, p[2] - f]);
}
module channel(w, pts) for (i = [0 : len(pts) - 2]) hull() { post(pts[i], w); post(pts[i + 1], w); }
module channels() for (c = channels()) channel(c[0], c[1]);
/** Room for the diode in the column channel, over the column tab. */
module diode_rooms() for (k = KEYS) multmatrix(k[K_FRAME])
  translate([col_x, (socket_tab_y[0] + ne_y) / 2 + 1, socket_top_z() - diode_mm[1] / 2 - 0.4])
    cube([diode_mm[1] + 0.8, diode_mm[0] + 0.8, diode_mm[1] + 0.8], center = true);
function diode_frame(k) = k[K_FRAME] * trans([col_x, (socket_tab_y[0] + ne_y) / 2 + 1, socket_top_z() - diode_mm[1] / 2 - 0.4]);
/** Something in key k's frame carried straight down (in world) to below the
 * desk: shafts and wells stand square to the desk however the key tilts. */
module dropped(k) hull() { multmatrix(k[K_FRAME]) children(); translate([0, 0, -60]) multmatrix(k[K_FRAME]) children(); }
/** The socket's shaft from its pocket down through the body's underside, `grow` round the body. */
module socket_shaft(k, grow) dropped(k) socket_body(grow);
/** Room under each socket tab to solder to it. */
module solder_wells() for (k = KEYS, side = [-1, 1]) let(t = socket_tab_tip(side)) dropped(k)
  translate([t[0] - solder_well_mm[0] / 2, t[1] - solder_well_mm[1] / 2, t[2] - 0.6]) cube([solder_well_mm[0], solder_well_mm[1], 0.6]);

// ---------------------------------------------------------------- the body
module key_rooms() for (k = KEYS) { multmatrix(k[K_FRAME]) { mx_switch_room(); hotswap_socket_room(); } socket_shaft(k, socket_clearance_mm); }
/** The parts' rooms in the well, cut from the plinth (where the switch's
 * pocket opens up through the plate's top) and from the body where they reach
 * above the plate's top. */
module bay_rooms(plinth = false) {
  multmatrix(MCU) mcu_room();
  multmatrix(BATTERY) battery_room();
  if (power_switch) multmatrix(POWER_SWITCH) power_switch_room(plinth ? 100 : 0);
}
module insert_holes() for (p = SCREWS) translate([p[0], p[1], floor_z(p[0], p[1])]) insert_hole();
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
/** The boss under key k's socket: the socket's shaft, inset, from the desk up
 * to just under the socket (it merges with the plinth below the plate's top). */
module socket_boss(k) intersection() {
  socket_shaft(k, -boss_inset_mm);
  multmatrix(k[K_FRAME]) translate([0, 0, socket_bottom_z() - boss_clearance_mm - 100]) cube([80, 80, 200], center = true);
  translate([BBOX[0][0], BBOX[0][1], 0]) cube([BBOX[1][0] - BBOX[0][0], BBOX[1][1] - BBOX[0][1], 100]);
}
/** The plinth: up to the body's underside, with the well, the screw holes and
 * the pinhole over the reset button, and the socket bosses standing on it. */
module bottom_plate() {
  difference() {
    plinth_blank();
    well();
    bay_rooms(plinth = true);
    for (p = SCREWS) translate([p[0], p[1], 0]) screw_hole(plate_z(p[0], p[1]));
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
/** The board's height: from the desk to the highest cap's top, and the lowest. */
function cap_tops() = [for (k = KEYS) cap_top(k)[2]];
function report() = let(
    b = BBOX, tops = cap_tops(), plates = [for (k = KEYS) origin(k[K_FRAME])[2]],
    floors = [for (k = KEYS) floor_z(origin(k[K_FRAME])[0], origin(k[K_FRAME])[1])]
  ) str("plate tops ", r2(vmin(plates)), " to ", r2(vmax(plates)), " mm over the desk; cap tops ",
        r2(vmin(tops)), " to ", r2(vmax(tops)), " mm; body shell ", r2(FLOOR_DROP),
        " mm thick; plinth ", r2(vmin(floors)), " to ", r2(vmax(floors)), " mm under the keys; well floor ", r2(BAY_Z),
        " mm; fingertip reach between rows ",
        [for (i = [0 : 3]) r2(finger_plate_pitch(i) * finger_reach_radius(i) / finger_plate_radius(i))],
        " mm (index to pinky); plan about ", r2(b[1][0] - b[0][0] - 2 * (outline_round_mm + 2)), " x ", r2(b[1][1] - b[0][1] - 2 * (outline_round_mm + 2)), " mm");

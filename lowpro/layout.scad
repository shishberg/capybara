// The key layout from the measured hand: every key's frame, and the world
// frame (the tent and the lift that stands the body on the floor).
//
// A key frame has its origin at the plate's top at the stem centre, +z out of
// the key (up through the cap), +y along the column away from you (the switch's
// pin side, north) and +x across it toward the pinky. Layout axes are the
// hand's (hand.scad); world axes are those tented, pitched and lifted.
//
// A key is [name, frame, group, column, row, cap_row, cap_units, cell]:
//   group    "finger", "thumb" or "extra"
//   column   0 inner, 1 index, 2 middle, 3 ring, 4 pinky; thumb keys take the
//            column whose wire they chain onto, as the matrix in
//            docs/design-status.md has it (x2 C0, near C1, x1 C2, home C3, far C4)
//   row      finger rows counted from the home row, + away from you; thumb row
//            keys -2 (the row), extras -3
//   cap_row  the Cherry row (1..4) of its cap
//   cap_units the cap's width in units along the key's x
//   cell     [width along x, depth along y] of the plate it owns, in its frame
include <params.scad>
include <hand.scad>
include <lib.scad>

K_NAME = 0; K_FRAME = 1; K_GROUP = 2; K_COL = 3; K_ROW = 4; K_CAPROW = 5; K_UNITS = 6; K_CELL = 7;

/** A cap's top over the plate for Cherry row r (1..4). */
function cap_top_height(r) = cap_bottom_above_plate_mm + cap_height_mm[r - 1];
function row_cap_row(r) = cap_row[clamp(rows_above - r, 0, len(cap_row) - 1)];
function deg(rad) = rad * 180 / PI;
function rad(d) = d * PI / 180;

// ---------------------------------------------------------------- finger columns
/** The arc the fingertip sweeps between rows: its radius at the cap tops, from
 * the pivot reach_mix of the way from the PIP to the MCP (hand.scad). */
function finger_reach_radius(i) = let(
    j = HAND_JOINTS[i], pivot = j[1] + reach_mix * (j[0] - j[1])
  ) norm(pivot - HAND_REST[i]);
/** The plate's radius about the column's arc centre, and the pitch along it
 * that leaves the caps row_pitch_mm apart at their skirts (the arc is tighter
 * there, cap_bottom_above_plate_mm closer to its centre). */
function finger_plate_radius(i) = finger_reach_radius(i) + cap_top_height(row_cap_row(0));
function finger_plate_pitch(i) = let(R = finger_plate_radius(i)) row_pitch_mm * R / (R - cap_bottom_above_plate_mm);
/** Finger i's column: the home key's plate top under the resting print (facing
 * up), the other rows round the arc about a point that radius above it. */
function finger_column_frames(i) = let(
    h = HAND_HEADING[i] * splay_scale,
    dir = [sin(h), cos(h), 0],
    H = cap_top_height(row_cap_row(0)),
    R = finger_plate_radius(i),
    o = HAND_REST[i] - [0, 0, H + finger_sink_mm],
    C = o + [0, 0, R]
  ) [for (r = [-rows_below : rows_above]) let(
      a = deg(r * finger_plate_pitch(i) / R),
      p = C + R * (sin(a) * dir - cos(a) * [0, 0, 1]),
      n = unit(C - p)
    ) frame_at(p, n, dir)];
function finger_keys(i, col) = let(F = finger_column_frames(i), name = HAND_FINGERS[i])
  [for (k = [0 : len(F) - 1]) let(r = k - rows_below)
    [str(name, "_", r), F[k], "finger", col, r, row_cap_row(r), 1, [cell_mm, finger_plate_pitch(i)]]];
/** The inner column: the index column carried inner_gap_mm toward the thumb,
 * square to itself, and turned inner_angle_deg about its home key. */
function inner_keys() = let(
    F = finger_column_frames(0), home = F[rows_below],
    side = -axis_x(home) * inner_gap_mm,
    pivot = origin(home) + side,
    T = trans(pivot) * rot_z(inner_angle_deg) * trans(-pivot) * trans(side)
  ) [for (k = [0 : len(F) - 1]) let(r = k - rows_below)
    [str("inner_", r), T * F[k], "finger", 0, r, row_cap_row(r), 1, [cell_mm, finger_plate_pitch(0)]]];

// ---------------------------------------------------------------- thumb
/** The thumb's row of three on the measured arc (hand.scad), step s: -1 near
 * (swept in), 0 home (thumb_around_deg), +1 far (swept out). The pitch along
 * the arc at the plate leaves the caps thumb_pitch_mm apart at their skirts
 * through the well's tilt. The key's y points out along the radius (away from
 * the thumb's base), x along the arc. */
function thumb_plate_pitch() = thumb_pitch_mm + 2 * cap_bottom_above_plate_mm * sin(thumb_well_deg / 2);
/** The angle round the arc between neighbouring keys: their centres a plate
 * pitch apart along the home key's x. */
function thumb_step_deg() = asin(thumb_plate_pitch() / HAND_THUMB_ARC_RADIUS);
/** A thumb key's frame at `a` degrees round the arc, `radius` from its centre,
 * its cap top `lower` mm under the finger home keys' less `rise`, tilted
 * `well` degrees about its y (+ facing -x, toward greater angles). Its heading
 * is the home key's turned toward its own radius by thumb_fan. */
function thumb_key_frame(a, radius, lower, rise, well) = let(
    top = [HAND_THUMB_ARC_CENTRE[0] + radius * cos(a), HAND_THUMB_ARC_CENTRE[1] + radius * sin(a),
           -thumb_drop_mm - lower + rise],
    heading = thumb_around_deg + thumb_fan * (a - thumb_around_deg),
    F0 = trans(top) * rot_z(heading - 90) * rot_x(thumb_tilt_deg) * rot_y(well),
    H = cap_top_height(cap_row_thumb)
  ) F0 * trans([0, 0, -H]);
THUMB_ROW = [["near", -1, 1], ["home", 0, 3], ["far", 1, 4]];
function thumb_keys() = [for (t = THUMB_ROW) let(s = t[1], w = thumb_well_deg,
    Rw = w == 0 ? 0 : thumb_plate_pitch() / rad(w), rise = w == 0 ? 0 : Rw * (1 - cos(s * w)),
    u = t[0] == "home" ? thumb_home_u : 1)
  [str("thumb_", t[0]), thumb_key_frame(thumb_around_deg + s * thumb_step_deg(), HAND_THUMB_ARC_RADIUS, 0, rise, s * w),
   "thumb", t[2], -2, cap_row_thumb, u, [thumb_plate_pitch() + (u - 1) * cap_unit_mm, cell_mm]]];
/** The extra pair on the circle thumb_row_gap_mm inside the row's, flat, a
 * cell apart along it and centred on the home key's angle: x1 toward the
 * index, x2 toward the far key. The measured curled-in print falls on x2. */
function extra_keys() = thumb_extra ? let(
    Ri = HAND_THUMB_ARC_RADIUS - thumb_row_gap_mm, step = 2 * asin(cell_mm / (2 * Ri)))
  [for (t = [["x1", -0.5, 2], ["x2", 0.5, 0]])
    [str("thumb_", t[0]),
     thumb_key_frame(thumb_around_deg + thumb_extra_around_deg + t[1] * step, Ri, thumb_extra_lower_mm, 0, 0),
     "extra", t[2], -3, cap_row_thumb, 1, [cell_mm, cell_mm]]] : [];

// ---------------------------------------------------------------- all keys, world
/** Every key in layout axes. */
function layout_keys() = concat(
  inner_keys(),
  [for (i = [0 : 3]) each finger_keys(i, i + 1)],
  thumb_keys(), extra_keys());
/** The tent and pitch, about the layout origin. */
function tent_frame() = rot_x(pitch_deg) * rot_y(tent_deg);
/** How far below a key's plate top the body's underside must reach: the socket's
 * bottom and the room under it. */
function body_depth() = switch_below_plate_mm + pcb_layer_mm + socket_body_mm[2] + under_socket_mm;
/** The lowest point any key's cell needs the body to reach, in tented axes. */
function tented_floor_z(T) = vmin([for (k = layout_keys()) each
  [for (sx = [-1, 1], sy = [-1, 1]) let(
    c = [sx * k[K_CELL][0] / 2, sy * k[K_CELL][1] / 2, -body_depth()]
  ) xform(T * k[K_FRAME], c)[2]]]);
/** Layout axes to world: tented, then lifted so the body's underside sits on
 * the bottom plate, which stands on z = 0. */
function world_frame() = let(T = tent_frame())
  trans([0, 0, bottom_plate_mm - tented_floor_z(T)]) * T;
WORLD = world_frame();
/** Every key in world axes. */
function keys() = [for (k = layout_keys())
  [k[K_NAME], WORLD * k[K_FRAME], k[K_GROUP], k[K_COL], k[K_ROW], k[K_CAPROW], k[K_UNITS], k[K_CELL]]];
KEYS = keys();
function key_named(name) = [for (k = KEYS) if (k[K_NAME] == name) k][0];
/** The body's underside: the bottom plate's top. */
FLOOR_Z = bottom_plate_mm;
/** A key's cell in its frame: [width along x, depth along y]. */
function cell_size(k) = k[K_CELL];
/** The cell's four corners in world plan, counterclockwise. */
function cell_corners(k, grow = 0) = let(s = cell_size(k) / 2 + [grow, grow])
  [for (c = [[-s[0], -s[1]], [s[0], -s[1]], [s[0], s[1]], [-s[0], s[1]]])
    xy(xform(k[K_FRAME], [c[0], c[1], 0]))];
/** The cap's top centre in world. */
function cap_top(k) = xform(k[K_FRAME], [0, 0, cap_top_height(k[K_CAPROW])]);

// ---------------------------------------------------------------- the bay: controller, battery, power switch
// Nothing with a socket over it can sit on the floor (each socket's shaft is
// open to the bottom plate), so the controller and the battery lie in a bay
// on the inner side of the inner column, in world axes: the board along the
// column with its port out of the back wall, the power switch beside it in
// the inner side wall, and the battery in front of the board. The bay's
// rectangles are [[x0, y0], [x1, y1]] in plan.
function cell_back(k) = vmax([for (c = cell_corners(k)) c[1]]);
function cell_x0(k) = vmin([for (c = cell_corners(k)) c[0]]);
function cell_x1(k) = vmax([for (c = cell_corners(k)) c[0]]);
bay_gap_mm = 1;   // between a cell and a pocket
function column_key(col, row) = [for (k = KEYS) if (k[K_GROUP] == "finger" && k[K_COL] == col && k[K_ROW] == row) k][0];
/** The strip beside the board for the power switch. */
function switch_strip() = power_switch ? power_switch_mm[1] + 1.2 : 0;
/** The controller's bay: beside the inner column's cells, its back at the
 * top cell's back, as long as the board, as wide as the board and the switch. */
function mcu_bay() = let(
    c = mcu_clearance_mm,
    x1 = vmin([for (r = [-rows_below : rows_above]) cell_x0(column_key(0, r))]) - bay_gap_mm,
    y1 = cell_back(column_key(0, rows_above))
  ) [[x1 - mcu_board_mm[0] - 2 * c - switch_strip(), y1 - mcu_board_mm[1] - 2 * c], [x1, y1]];
/** The controller board's frame in world (parts.scad mcu_board): origin at the
 * middle of its port end on the floor, +y along the board, components down.
 * The board lies along the column, its port facing the back (+y). */
function mcu_frame() = let(b = mcu_bay(), c = mcu_clearance_mm)
  trans([b[1][0] - c - mcu_board_mm[0] / 2, b[1][1] + mcu_usb_overhang_mm, FLOOR_Z]) * rot_z(180 + mcu_turn_deg);
MCU = mcu_frame();
/** The power switch's frame: body centred in its strip, knob out of the inner side (-x). */
function power_switch_frame() = let(b = mcu_bay(), c = 0.3)
  trans([b[0][0] + c + power_switch_mm[1] / 2, b[1][1] - power_switch_back_mm - power_switch_mm[0] / 2,
         FLOOR_Z + power_switch_mm[2] / 2 + c]) * rot_z(-90);
POWER_SWITCH = power_switch_frame();
/** The battery's bay: in front of the controller's, the same width. */
function battery_bay() = let(m = mcu_bay(), c = battery_clearance_mm, y1 = m[0][1] - bay_gap_mm)
  [[m[0][0], y1 - battery_mm[1] - 2 * c], [m[1][0], y1]];
/** The battery's frame: its centre on the floor (parts.scad battery). */
function battery_frame() = let(b = battery_bay())
  trans([(b[0][0] + b[1][0]) / 2, (b[0][1] + b[1][1]) / 2, FLOOR_Z]);
BATTERY = battery_frame();
function bays() = [mcu_bay(), battery_bay()];

// ---------------------------------------------------------------- screws
/** Where the bottom plate screws into the body's wall, in world plan: a point
 * on a cell's or a bay's edge carried screw_out_mm outward, on edges the trunk
 * channels (chassis.scad) keep clear of: the pinky's outer side, the thumb
 * cluster's far side and front, and the bay's inner side and front. */
function screw_points() = let(s = screw_out_mm,
    edge = function(k, d) let(c = cell_size(k) / 2)
      xy(xform(k[K_FRAME], [d[0] * c[0] + (abs(d[0]) == 1 ? d[0] * s : 0), d[1] * c[1] + (abs(d[1]) == 1 ? d[1] * s : 0), 0])),
    m = mcu_bay(), b = battery_bay())
  [edge(key_named("pinky_1"), [1, 0.3]), edge(key_named("pinky_-1"), [1, -0.3]),
   edge(key_named("thumb_far"), [-1, 0]),
   edge(key_named(thumb_extra ? "thumb_x2" : "thumb_home"), [0, -1]),
   edge(key_named(thumb_extra ? "thumb_x1" : "thumb_near"), [0, -1]),
   [m[0][0] - s, (m[0][1] + m[1][1]) / 2 - 6], [b[0][0] - s, (b[0][1] + b[1][1]) / 2],
   [(b[0][0] + b[1][0]) / 2, b[0][1] - s]];

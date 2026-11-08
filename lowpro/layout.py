"""The key layout: every key's frame, and the world frame (the tent and the
lift that stands the body on the bottom plate). The lowpro design lays the
keys out from the measured hand; the capybara design takes them from the
Capybara's editor (swung_in), with the Pro Micro, jack and reset switch.

A key frame has its origin at the plate's top at the stem centre, +z out of
the key (up through the cap), +y along the column away from you (the switch's
pin side, north) and +x across it toward the pinky. Layout axes are the
hand's (see hand()); world axes are those tented, pitched and lifted. The
editor's frames are already in world axes but for the plinth's thickness.

A Key has:
  group    "finger", "thumb" or "extra"
  col      0 inner, 1 index, 2 middle, 3 ring, 4 pinky; thumb keys take the
           column whose wire they chain onto, as the matrix in
           docs/design-status.md has it (x2 C0, near C1, x1 C2, home C3, far C4)
  row      finger rows counted from the home row, + away from you; thumb row
           keys -2 (the row), x1 and x2 -3
  cap_row  the Cherry row (1..4) of its cap
  units    the cap's width in units along the key's x
  cell     (width along x, depth along y) of the plate it owns, in its frame

Everything is cached; call reset() after changing a parameter.
"""
import functools
import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import params as P
from . import parts as R
from .lib import (axis_x, axis_z, basis, clamp, cosd, frame_at, origin, rinv, rot_x, rot_y, rot_z,
                  sind, trans, unit, xform, xy)

ROOT = Path(__file__).resolve().parent.parent
FINGERS = ["index", "middle", "ring", "pinky"]


@dataclass(frozen=True)
class Key:
    name: str
    frame: np.ndarray
    group: str
    col: int
    row: int
    cap_row: int
    units: float
    cell: tuple
    # What hangs under the plate that the top has to cover (chassis.field), as
    # (half, top, bottom, skin): a square slab of that half side in the key's
    # frame from `top` to `bottom` below the plate's top (the tile's pocket and
    # the tile in it), which the top stays `skin` over wherever the
    # slab leans out past the cell. Empty when nothing hangs below.
    pocket: tuple = ()

    def moved(self, m):
        return Key(self.name, m @ self.frame, self.group, self.col, self.row, self.cap_row, self.units, self.cell, self.pocket)


_cached = []


def cached(f):
    g = functools.lru_cache(maxsize=None)(f)
    _cached.append(g)
    return g


def reset():
    """Forget everything computed from the parameters (after changing one)."""
    for g in _cached:
        g.cache_clear()


# ---------------------------------------------------------------- the hand
@cached
def hand():
    """The measured left hand (hand/left-hand.json) in the layout axes, which
    read as the right half: origin at the middle fingertip's resting print, +X
    toward the pinky, +Y away from you, +Z up from the flat surface.
      rest       where each fingertip rested on the flat paper
      heading    the finger's direction in plan, degrees from +Y toward +X
      joints     resting joint centres [MCP, PIP, DIP] per finger, for the reach radius
      thumb_arc  (centre, radius) of the circle the thumb's pad prints 1 to 4 lie on"""
    h = json.loads((ROOT / "hand" / "left-hand.json").read_text())
    arc = h["thumb"]["arc_through_prints_1_to_4"]
    return {
        "rest": [np.array(h["measured"]["fingertip_rest"][f][:3], float) for f in FINGERS],
        "heading": [float(h["fingers"][f]["rest"]["heading_deg"]) for f in FINGERS],
        "joints": [[np.array(h["fingers"][f]["rest"]["joints"][j][:3], float) for j in ("mcp", "pip", "dip")]
                   for f in FINGERS],
        "thumb_arc": (np.array(arc["centre"][:2], float), float(arc["radius_mm"])),
    }


# ---------------------------------------------------------------- caps and rows
def cap_top_height(r):
    """A cap's top over the plate for Cherry row r (1..4)."""
    return P.cap_bottom_above_plate_mm + P.cap_height_mm[r - 1]


def row_cap_row(r):
    return P.cap_row[clamp(P.rows_above - r, 0, len(P.cap_row) - 1)]


# ---------------------------------------------------------------- finger columns
def finger_reach_radius(i):
    """The arc the fingertip sweeps between rows: its radius at the cap tops,
    from the pivot reach_mix of the way from the PIP to the MCP."""
    j = hand()["joints"][i]
    pivot = j[1] + P.reach_mix * (j[0] - j[1])
    return float(np.linalg.norm(pivot - hand()["rest"][i]))


def finger_plate_radius(i):
    """The plate's radius about the column's arc centre."""
    return finger_reach_radius(i) + cap_top_height(row_cap_row(0))


def finger_plate_pitch(i):
    """The pitch along the plate's arc that leaves the caps row_pitch_mm apart at
    their skirts (the arc is tighter there, cap_bottom_above_plate_mm closer to its centre)."""
    R = finger_plate_radius(i)
    return P.row_pitch_mm * R / (R - P.cap_bottom_above_plate_mm)


def finger_column_frames(i):
    """Finger i's column: the home key's plate top under the resting print (facing
    up), the other rows round the arc about a point that radius above it."""
    h = hand()["heading"][i] * P.splay_scale
    d = np.array([sind(h), cosd(h), 0.0])
    H = cap_top_height(row_cap_row(0))
    R = finger_plate_radius(i)
    o = hand()["rest"][i] - np.array([0, 0, H + P.finger_sink_mm])
    C = o + np.array([0, 0, R])
    frames = []
    for r in range(-P.rows_below, P.rows_above + 1):
        a = math.degrees(r * finger_plate_pitch(i) / R)
        p = C + R * (sind(a) * d - cosd(a) * np.array([0, 0, 1.0]))
        frames.append(frame_at(p, unit(C - p), d))
    return frames


def finger_keys(i, col):
    F = finger_column_frames(i)
    name = FINGERS[i]
    return [Key(f"{name}_{k - P.rows_below}", F[k], "finger", col, k - P.rows_below,
                row_cap_row(k - P.rows_below), 1, (P.cell_mm, finger_plate_pitch(i)))
            for k in range(len(F))]


def inner_keys():
    """The inner column: the index column carried inner_gap_mm toward the thumb,
    square to itself, and turned inner_angle_deg about its home key."""
    F = finger_column_frames(0)
    home = F[P.rows_below]
    side = -axis_x(home) * P.inner_gap_mm
    pivot = origin(home) + side
    T = trans(pivot) @ rot_z(P.inner_angle_deg) @ trans(-pivot) @ trans(side)
    return [Key(f"inner_{k - P.rows_below}", T @ F[k], "finger", 0, k - P.rows_below,
                row_cap_row(k - P.rows_below), 1, (P.cell_mm, finger_plate_pitch(0)))
            for k in range(len(F))]


# ---------------------------------------------------------------- thumb
def thumb_plate_pitch():
    """The pitch along the arc at the plate that leaves the caps thumb_pitch_mm
    apart at their skirts through the well's tilt."""
    return P.thumb_pitch_mm + 2 * P.cap_bottom_above_plate_mm * sind(P.thumb_well_deg / 2)


def thumb_step_deg():
    """The angle round the arc between neighbouring keys: their centres a plate
    pitch apart along the home key's x."""
    return math.degrees(math.asin(thumb_plate_pitch() / hand()["thumb_arc"][1]))


def thumb_key_frame(a, radius, rise, well):
    """A thumb key's frame at `a` degrees round the arc, `radius` from its centre,
    its cap top thumb_drop_mm under the finger home keys' less `rise`, tilted `well`
    degrees about its y (+ facing -x, toward greater angles). Its heading is the
    home key's turned toward its own radius by thumb_fan."""
    centre = hand()["thumb_arc"][0]
    top = np.array([centre[0] + radius * cosd(a), centre[1] + radius * sind(a), -P.thumb_drop_mm + rise])
    heading = P.thumb_around_deg + P.thumb_fan * (a - P.thumb_around_deg)
    F0 = trans(top) @ rot_z(heading - 90) @ rot_x(P.thumb_tilt_deg) @ rot_y(well)
    return F0 @ trans([0, 0, -cap_top_height(P.cap_row_thumb)])


THUMB_ROW = [("near", -1, 1), ("home", 0, 3), ("far", 1, 4)]


def thumb_keys():
    """The thumb's row of three, step s: -1 near (swept in) and +1 far (swept out)
    on the measured arc, either side of thumb_around_deg, 0 home on the straight
    line between them at that angle, the key's y out along the radius (away from
    the thumb's base) and x along the row. The row is then turned thumb_turn_deg counterclockwise in plan about near's centre,
    and leaned thumb_lean_deg about near's y through its centre, far going down."""
    w = P.thumb_well_deg
    R = hand()["thumb_arc"][1]
    step = thumb_step_deg()
    keys = []
    for name, s, col in THUMB_ROW:
        Rw = 0 if w == 0 else thumb_plate_pitch() / math.radians(w)
        rise = 0 if w == 0 else Rw * (1 - cosd(s * w))
        u = P.thumb_home_u if name == "home" else 1
        keys.append(Key(f"thumb_{name}", thumb_key_frame(P.thumb_around_deg + s * step, R * cosd(step) / cosd(s * step), rise, s * w),
                        "thumb", col, -2, P.cap_row_thumb, u, (thumb_plate_pitch() + (u - 1) * P.cap_unit_mm, P.cell_mm)))
    p = origin(keys[0].frame)
    turn = trans(p) @ rot_z(P.thumb_turn_deg) @ trans(-p)
    near = turn @ keys[0].frame
    return [k.moved(near @ rot_y(-P.thumb_lean_deg) @ rinv(near) @ turn) for k in keys]


def extra_keys():
    """The extra pair, a fourth row under the middle (x1) and ring (x2) columns:
    flat and square to the layout, a cell apart, each thumb_extra_gap_mm south of
    its column's bottom key's south edge, x1 thumb_extra_left_mm toward the thumb."""
    if not P.thumb_extra:
        return []
    edges = [xform(finger_keys(i, i + 1)[0].frame, [0, -finger_keys(i, i + 1)[0].cell[1] / 2, 0]) for i in (1, 2)]
    edges[0][0] -= P.thumb_extra_left_mm
    edges[1][0] = edges[0][0] + P.cell_mm
    place = trans([0, -P.cell_mm / 2 - P.thumb_extra_gap_mm, -P.thumb_extra_lower_mm])
    return [Key(f"thumb_{name}", frame_at(e, [0, 0, 1], [0, 1, 0]) @ place, "extra", col, -3, P.cap_row_thumb, 1, (P.cell_mm, P.cell_mm))
            for name, col, e in (("x1", 2, edges[0]), ("x2", 0, edges[1]))]


# ---------------------------------------------------------------- Swung in (design "capybara")
# The Capybara's default project, Swung in, as its editor places it, through
# editor/tests/key-frames.ts: every key, the Pro Micro, the TRRS jack and the
# reset switch in the editor's world axes (the desk z = 0, the base plate's top
# skin_mm over it), tent and lift included, for this half (the left half is
# built as the right and mirrored, as the editor does, docs/editor-chassis.md).
@cached
def swung_in():
    run = subprocess.run(["node", "--import", "tsx", "tests/key-frames.ts", P.half], cwd=ROOT / "editor",
                         capture_output=True, text=True)
    if run.returncode:
        raise RuntimeError(f"editor/tests/key-frames.ts failed (npm --prefix editor install?):\n{run.stderr}")
    return json.loads(run.stdout)


COLUMNS = ["inner", "index", "middle", "ring", "pinky"]
ROWS = {"top": 1, "home": 0, "bottom": -1}
THUMB_COLS = {name: col for name, _, col in THUMB_ROW} | {"x1": 2, "x2": 0}


def swung_in_keys():
    """Swung in's keys under the editor's names, in its world axes, grouped as the
    hand layout's are. Each cell is a key unit square, wider along x for a wider cap."""
    out = []
    room = R.tile_room_box()
    pocket = (room[0] / 2, -room[1], -room[1] + room[2], P.top_skin_mm)
    for name, u in swung_in()["units"].items():
        m = np.array(swung_in()["frames"][name], float)
        cell = (P.cell_mm + (u - 1) * P.cap_unit_mm, P.cell_mm)
        if name.startswith("matrix_"):
            _, col, row = name.split("_")
            r = ROWS[row]
            out.append(Key(name, m, "finger", COLUMNS.index(col), r, row_cap_row(r), u, cell, pocket))
        else:
            t = name.removeprefix("thumb_")
            in_row = t in THUMB_COLS and t not in ("x1", "x2")
            out.append(Key(name, m, "thumb" if in_row else "extra", THUMB_COLS[t], -2 if in_row else -3, P.cap_row_thumb, u, cell, pocket))
    return out


def design():
    """The module that builds this design's body and plinth."""
    from . import chassis, shell
    return shell if P.design == "capybara" else chassis


# ---------------------------------------------------------------- all keys, world
@cached
def layout_keys():
    """Every key in layout axes."""
    if P.design == "capybara":
        return swung_in_keys()
    keys = list(inner_keys())
    for i in range(4):
        keys += finger_keys(i, i + 1)
    return keys + thumb_keys() + extra_keys()


def tent_frame():
    """The tent and pitch, about the layout origin."""
    return rot_x(P.pitch_deg) @ rot_y(P.tent_deg)


def body_depth():
    return P.under_socket_mm - R.socket_bottom_z()


def seam_turn():
    """The seam's turn from the home plates, in layout axes."""
    return rot_y(P.seam_tent_deg - P.tent_deg)


def seam_in_layout():
    m = rinv(seam_turn())

    def lowest(k, points):
        return min(xform(m @ k.frame, p)[2] for p in points)
    return min(min(lowest(k, R.socket_underside_either_hand()) - P.under_socket_mm, lowest(k, R.diode_rim_points()) - P.under_diode_mm)
               for k in layout_keys())


def lowest_seam_in(T):
    """The seam's lowest point under the key field and its wall, in tented axes."""
    m, s = rinv(seam_turn()), seam_in_layout()
    edge = [xform(m @ k.frame, [sx * (k.cell[0] / 2 + P.wall_mm), sy * (k.cell[1] / 2 + P.wall_mm), 0])
            for k in layout_keys() for sx in (-1, 1) for sy in (-1, 1)]
    return min(xform(T @ seam_turn(), [p[0], p[1], s])[2] for p in edge)


@cached
def world_frame():
    """Layout axes to world: tented, then lifted so the seam's lowest point sits
    bottom_plate_mm over the desk, which is z = 0. The editor's axes are the
    world's with its base plate's top at the seam."""
    if P.design == "capybara":
        return trans([0, 0, P.bottom_plate_mm - swung_in()["skin_mm"]])
    T = tent_frame()
    return trans([0, 0, P.bottom_plate_mm - lowest_seam_in(T)]) @ T


@cached
def seam_frame():
    """The seam, the plane between the body and the plinth, as a frame: its z = 0
    the plane, its z up out of the plinth. The capybara design's is the flat
    plinth's top, the floor the wires lie on, so it's level."""
    if P.design == "capybara":
        return trans([0, 0, P.bottom_plate_mm])
    return world_frame() @ seam_turn() @ trans([0, 0, seam_in_layout()])


@cached
def keys():
    """Every key in world axes."""
    W = world_frame()
    return [k.moved(W) for k in layout_keys()]


def key_named(name):
    return next(k for k in keys() if k.name == name)


def editor_frame(name):
    """A part's frame as the editor places it ("pro_micro", "trrs" or "reset"), in world."""
    return world_frame() @ np.array(swung_in()["frames"][name], float)


def cell_corners(k, grow=0, z=0):
    """The cell's four corners in world plan, counterclockwise, at height z in
    the key's frame (0 the plate's top)."""
    sx, sy = k.cell[0] / 2 + grow, k.cell[1] / 2 + grow
    return [xy(xform(k.frame, [cx, cy, z])) for cx, cy in ((-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy))]


def cap_top(k):
    """The cap's top centre in world."""
    return xform(k.frame, [0, 0, cap_top_height(k.cap_row)])


# ---------------------------------------------------------------- the bay: controller, battery, power switch
# Nothing with a socket over it can sit under the body's floor (each socket's
# shaft is open to the bottom plate), so the controller and the battery lie in
# a well in the bottom plate on the inner side of the inner column, in world
# axes: the board along the column with its port out of the back wall and the
# battery in front of the board. The bay's rectangles are ((x0, y0), (x1, y1))
# in plan; the parts' frames here are on z = 0, chassis.py lifts them to the
# well's floor, and the power switch, beside the board, to the plinth's top.
def cell_back(k):
    return max(c[1] for c in cell_corners(k))


def cell_x0(k):
    """The cell's least x in plan from the plate's top down to the body's
    underside (the key's cuts lean with it)."""
    return min(c[0] for z in (0, -body_depth()) for c in cell_corners(k, z=z))


def column_key(col, row):
    return next(k for k in keys() if k.group == "finger" and k.col == col and k.row == row)


@cached
def mcu_bay():
    """The controller's bay: beside the inner column's cells, its back at the
    top cell's back, as wide as the board, and reaching as far
    forward as the board's room (the board sits mcu_usb_overhang_mm back past
    the bay's back, toward the port's opening: mcu_frame)."""
    c = P.mcu_clearance_mm
    x1 = min(cell_x0(column_key(0, r)) for r in range(-P.rows_below, P.rows_above + 1)) - P.mcu_bay_wall_mm
    y1 = cell_back(column_key(0, P.rows_above))
    y0 = y1 + P.mcu_usb_overhang_mm - P.mcu_board_mm[1] - c
    return ((x1 - P.mcu_board_mm[0] - 2 * c, y0), (x1, y1))


def mcu_frame():
    """The controller board's frame (parts.py mcu_board): origin at the middle
    of its port end on the well's floor, +y along the board, components down.
    The board lies along the column, its port facing the back (+y)."""
    b, c = mcu_bay(), P.mcu_clearance_mm
    return trans([b[1][0] - c - P.mcu_board_mm[0] / 2, b[1][1] + P.mcu_usb_overhang_mm, 0]) @ rot_z(180 + P.mcu_turn_deg)


def power_switch_frame():
    """The power switch's frame in plan: in the strip beside the board, at the
    battery's end of it, its knob out through the inner side wall (-x) and proud of it."""
    x = bay_rect()[0][0] - P.wall_mm - P.power_switch_proud_mm + P.power_switch_knob_mm[2] + P.power_switch_mm[1] / 2
    y = mcu_bay()[0][1] + P.power_switch_clearance_mm + P.power_switch_mm[0] / 2
    return trans([x, y, 0]) @ rot_z(-90)


def reset_button_frame():
    """The reset button's frame in plan: in the strip beside the board, north of
    the power switch, its plunger's tip flush with the inner side wall (-x)."""
    x = bay_rect()[0][0] - P.wall_mm + P.reset_plunger_mm[1] + P.reset_button_mm[1] / 2
    y = mcu_bay()[0][1] + P.power_switch_clearance_mm + P.power_switch_mm[0] + P.reset_button_gap_mm + P.reset_leg_mm[0] / 2
    return trans([x, y, 0]) @ rot_z(-90)


@cached
def battery_bay():
    """The battery's bay: in front of the controller's, against the same inner
    column, as long and as wide as the battery, which lies along the column."""
    m, c = mcu_bay(), P.battery_clearance_mm
    x1, y1 = m[1][0], m[0][1] - P.min_wall_mm
    return ((x1 - P.battery_mm[1] - 2 * c, y1 - P.battery_mm[0] - 2 * c), (x1, y1))


def battery_frame():
    """The battery's frame: its centre on the well's floor, its length (+x in
    parts.py battery) along the column."""
    b = battery_bay()
    return trans([(b[0][0] + b[1][0]) / 2, (b[0][1] + b[1][1]) / 2, 0]) @ rot_z(90)


def bays():
    return [mcu_bay(), battery_bay()]


def bay_rect():
    """The plan rectangle round both bays, which the outline follows: as wide
    as the wider one, so the inner side wall runs straight past the narrower,
    and wide enough that the strip beside the board, with the outline's wall,
    leaves min_wall_mm either side of the screw's counterbore there."""
    m, b = mcu_bay(), battery_bay()
    strip = P.screw_head_d + P.screw_head_clearance_mm + 2 * P.min_wall_mm
    return ((min(m[0][0] - strip + P.wall_mm, b[0][0]), b[0][1]), (m[1][0], m[1][1]))


def bay_outline_rect():
    """bay_rect as the outline's wall goes round it: its back wall's face square to
    the port, mcu_usb_recess_mm past the port's end."""
    (x0, y0), (x1, y1) = bay_rect()
    return ((x0, y0), (x1, y1 + 2 * P.mcu_usb_overhang_mm + P.mcu_usb_recess_mm - P.wall_mm))


def lead_notch():
    """The notch for the battery's leads through the wall between the bays,
    reaching half a millimetre into each."""
    m, b = mcu_bay(), battery_bay()
    x, w = (b[0][0] + b[1][0]) / 2, P.battery_lead_notch_mm
    return ((x - w / 2, b[1][1] - 0.5), (x + w / 2, m[0][1] + 0.5))


# ---------------------------------------------------------------- screws
def screw_points():
    """Where the bottom plate screws into the body, in world plan. The wall is
    too thin to hold an insert, so the screws stand inside the field: in a
    key's cell, in the web south of its switch's pocket and under its PCB
    layer, where no socket, tab or channel comes (the (x, y) in the key's frame
    are picked for the wall they leave, which a key's lean moves); one past the
    home thumb key's north edge, between the row and the battery; and one in the
    strip beside the board, which is narrower than the battery, midway between
    the well and the outline and near the USB port."""
    def cell(name, x, y):
        return xy(xform(key_named(name).frame, [x, y, 0]))

    m = mcu_bay()
    strip = (m[0][0] + bay_rect()[0][0] - P.wall_mm) / 2, m[1][1] - 8
    return [cell("ring_0", 4, -9.5), cell("middle_1", 8, -7.5),
            cell("thumb_x2", 9, -8.5) if P.thumb_extra else cell("ring_-1", 4, -9.5), strip, cell("thumb_home", 10, -9.5), cell("thumb_far", -9, -9.5), cell("thumb_home", 3, 12.5)]

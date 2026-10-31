"""The key layout from the measured hand: every key's frame, and the world
frame (the tent and the lift that stands the body on the bottom plate).

A key frame has its origin at the plate's top at the stem centre, +z out of
the key (up through the cap), +y along the column away from you (the switch's
pin side, north) and +x across it toward the pinky. Layout axes are the
hand's (see hand()); world axes are those tented, pitched and lifted.

A Key has:
  group    "finger", "thumb" or "extra"
  col      0 inner, 1 index, 2 middle, 3 ring, 4 pinky; thumb keys take the
           column whose wire they chain onto, as the matrix in
           docs/design-status.md has it (x2 C0, near C1, x1 C2, home C3, far C4)
  row      finger rows counted from the home row, + away from you; thumb row
           keys -2 (the row), extras -3
  cap_row  the Cherry row (1..4) of its cap
  units    the cap's width in units along the key's x
  cell     (width along x, depth along y) of the plate it owns, in its frame

Everything is cached; call reset() after changing a parameter.
"""
import functools
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import params as P
from .lib import (axis_x, axis_z, basis, clamp, cosd, frame_at, origin, rot_x, rot_y, rot_z,
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

    def moved(self, m):
        return Key(self.name, m @ self.frame, self.group, self.col, self.row, self.cap_row, self.units, self.cell)


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


def thumb_key_frame(a, radius, lower, rise, well):
    """A thumb key's frame at `a` degrees round the arc, `radius` from its centre,
    its cap top `lower` mm under the finger home keys' less `rise`, tilted `well`
    degrees about its y (+ facing -x, toward greater angles). Its heading is the
    home key's turned toward its own radius by thumb_fan."""
    centre = hand()["thumb_arc"][0]
    top = np.array([centre[0] + radius * cosd(a), centre[1] + radius * sind(a), -P.thumb_drop_mm - lower + rise])
    heading = P.thumb_around_deg + P.thumb_fan * (a - P.thumb_around_deg)
    F0 = trans(top) @ rot_z(heading - 90) @ rot_x(P.thumb_tilt_deg) @ rot_y(well)
    return F0 @ trans([0, 0, -cap_top_height(P.cap_row_thumb)])


THUMB_ROW = [("near", -1, 1), ("home", 0, 3), ("far", 1, 4)]


def thumb_keys():
    """The thumb's row of three on the measured arc, step s: -1 near (swept in),
    0 home (thumb_around_deg), +1 far (swept out). The key's y points out along
    the radius (away from the thumb's base), x along the arc."""
    w = P.thumb_well_deg
    R = hand()["thumb_arc"][1]
    keys = []
    for name, s, col in THUMB_ROW:
        Rw = 0 if w == 0 else thumb_plate_pitch() / math.radians(w)
        rise = 0 if w == 0 else Rw * (1 - cosd(s * w))
        u = P.thumb_home_u if name == "home" else 1
        keys.append(Key(f"thumb_{name}", thumb_key_frame(P.thumb_around_deg + s * thumb_step_deg(), R, 0, rise, s * w),
                        "thumb", col, -2, P.cap_row_thumb, u, (thumb_plate_pitch() + (u - 1) * P.cap_unit_mm, P.cell_mm)))
    return keys


def extra_keys():
    """The extra pair on the circle thumb_row_gap_mm inside the row's, flat, a
    cell apart along it and centred on the home key's angle: x1 toward the
    index, x2 toward the far key. The measured curled-in print falls on x2."""
    if not P.thumb_extra:
        return []
    Ri = hand()["thumb_arc"][1] - P.thumb_row_gap_mm
    step = math.degrees(2 * math.asin(P.cell_mm / (2 * Ri)))
    return [Key(f"thumb_{name}",
                thumb_key_frame(P.thumb_around_deg + P.thumb_extra_around_deg + s * step, Ri, P.thumb_extra_lower_mm, 0, 0),
                "extra", col, -3, P.cap_row_thumb, 1, (P.cell_mm, P.cell_mm))
            for name, s, col in (("x1", -0.5, 2), ("x2", 0.5, 0))]


# ---------------------------------------------------------------- all keys, world
@cached
def layout_keys():
    """Every key in layout axes."""
    keys = list(inner_keys())
    for i in range(4):
        keys += finger_keys(i, i + 1)
    return keys + thumb_keys() + extra_keys()


def tent_frame():
    """The tent and pitch, about the layout origin."""
    return rot_x(P.pitch_deg) @ rot_y(P.tent_deg)


def body_depth():
    """How far below a key's plate top the body's underside must reach along the
    key's normal: the socket's bottom and the room under it."""
    return P.switch_below_plate_mm + P.pcb_layer_mm + P.socket_body_mm[2] + P.under_socket_mm


def floor_drop_in(T):
    """The body's underside is the top surface dropped straight down by this much:
    body_depth() along the normal of the most tilted key, so no socket's room
    comes up short."""
    return body_depth() / min(axis_z(T @ k.frame)[2] for k in layout_keys())


def tented_floor_z(T):
    """The lowest point any key's cell puts the body's underside, in tented axes."""
    zs = [xform(T @ k.frame, [sx * k.cell[0] / 2, sy * k.cell[1] / 2, 0])[2]
          for k in layout_keys() for sx in (-1, 1) for sy in (-1, 1)]
    return min(zs) - floor_drop_in(T)


@cached
def world_frame():
    """Layout axes to world: tented, then lifted so the body's lowest point sits
    bottom_plate_mm over the desk, which is z = 0."""
    T = tent_frame()
    return trans([0, 0, P.bottom_plate_mm - tented_floor_z(T)]) @ T


@cached
def keys():
    """Every key in world axes."""
    W = world_frame()
    return [k.moved(W) for k in layout_keys()]


def key_named(name):
    return next(k for k in keys() if k.name == name)


@cached
def floor_drop():
    """The body's underside drops this far below its top surface (chassis.py floor_z)."""
    return floor_drop_in(tent_frame())


def cell_corners(k, grow=0):
    """The cell's four corners in world plan, counterclockwise."""
    sx, sy = k.cell[0] / 2 + grow, k.cell[1] / 2 + grow
    return [xy(xform(k.frame, [cx, cy, 0])) for cx, cy in ((-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy))]


def cap_top(k):
    """The cap's top centre in world."""
    return xform(k.frame, [0, 0, cap_top_height(k.cap_row)])


# ---------------------------------------------------------------- the bay: controller, battery, power switch
# Nothing with a socket over it can sit under the body's floor (each socket's
# shaft is open to the bottom plate), so the controller and the battery lie in
# a well in the bottom plate on the inner side of the inner column, in world
# axes: the board along the column with its port out of the back wall, the
# power switch beside it in the inner side wall, and the battery in front of
# the board. The bay's rectangles are ((x0, y0), (x1, y1)) in plan; the
# parts' frames here are on z = 0, chassis.py lifts them to the well's floor.
bay_gap_mm = 1   # between a cell and a pocket


def cell_back(k):
    return max(c[1] for c in cell_corners(k))


def cell_x0(k):
    return min(c[0] for c in cell_corners(k))


def column_key(col, row):
    return next(k for k in keys() if k.group == "finger" and k.col == col and k.row == row)


def switch_strip():
    """The strip beside the board for the power switch."""
    return P.power_switch_mm[1] + 1.2 if P.power_switch else 0


@cached
def mcu_bay():
    """The controller's bay: beside the inner column's cells, its back at the
    top cell's back, as long as the board, as wide as the board and the switch."""
    c = P.mcu_clearance_mm
    x1 = min(cell_x0(column_key(0, r)) for r in range(-P.rows_below, P.rows_above + 1)) - bay_gap_mm
    y1 = cell_back(column_key(0, P.rows_above))
    return ((x1 - P.mcu_board_mm[0] - 2 * c - switch_strip(), y1 - P.mcu_board_mm[1] - 2 * c), (x1, y1))


def mcu_frame():
    """The controller board's frame (parts.py mcu_board): origin at the middle
    of its port end on the well's floor, +y along the board, components down.
    The board lies along the column, its port facing the back (+y)."""
    b, c = mcu_bay(), P.mcu_clearance_mm
    return trans([b[1][0] - c - P.mcu_board_mm[0] / 2, b[1][1] + P.mcu_usb_overhang_mm, 0]) @ rot_z(180 + P.mcu_turn_deg)


def power_switch_frame():
    """The power switch's frame: body centred in its strip, knob out of the inner side (-x)."""
    b, c = mcu_bay(), 0.3
    return trans([b[0][0] + c + P.power_switch_mm[1] / 2,
                  b[1][1] - P.power_switch_back_mm - P.power_switch_mm[0] / 2,
                  P.power_switch_mm[2] / 2 + c]) @ rot_z(-90)


@cached
def battery_bay():
    """The battery's bay: in front of the controller's, the same width."""
    m, c = mcu_bay(), P.battery_clearance_mm
    y1 = m[0][1] - bay_gap_mm
    return ((m[0][0], y1 - P.battery_mm[1] - 2 * c), (m[1][0], y1))


def battery_frame():
    """The battery's frame: its centre on the well's floor (parts.py battery)."""
    b = battery_bay()
    return trans([(b[0][0] + b[1][0]) / 2, (b[0][1] + b[1][1]) / 2, 0])


def bays():
    return [mcu_bay(), battery_bay()]


# ---------------------------------------------------------------- screws
@cached
def screw_points():
    """Where the bottom plate screws into the body's wall, in world plan: a point
    on a cell's or a bay's edge carried screw_out_mm outward, on edges the trunk
    channels (chassis.py) keep clear of: the pinky's outer side, the thumb
    cluster's far side and front, and the bay's inner side and front."""
    s = P.screw_out_mm

    def edge(k, d):
        cx, cy = k.cell[0] / 2, k.cell[1] / 2
        return xy(xform(k.frame, [d[0] * cx + (d[0] * s if abs(d[0]) == 1 else 0),
                                  d[1] * cy + (d[1] * s if abs(d[1]) == 1 else 0), 0]))

    m, b = mcu_bay(), battery_bay()
    return [edge(key_named("pinky_1"), (1, 0.3)), edge(key_named("pinky_-1"), (1, -0.3)),
            edge(key_named("thumb_far"), (-1, 0)),
            edge(key_named("thumb_x2" if P.thumb_extra else "thumb_home"), (0, -1)),
            edge(key_named("thumb_x1" if P.thumb_extra else "thumb_near"), (0, -1)),
            (m[0][0] - s, (m[0][1] + m[1][1]) / 2 - 6), (b[0][0] - s, (b[0][1] + b[1][1]) / 2),
            ((b[0][0] + b[1][0]) / 2, b[0][1] - s)]

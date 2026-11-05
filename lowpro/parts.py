"""The bought parts, each drawn in its own frame, and the room cut for each.

Key parts are in the key frame (layout.py): origin at the plate top under the
stem, +z up, +y the pin side. "room" functions return the solids the body (or
the plinth) loses; the others return the part itself as coloured, named
pieces, for the assembly. chassis.py places them. Solids are Manifold's
(manifold3d): exact boxes, and cylinders as prisms whose chords stay within
mesh_tol_mm of the circle.
"""
import math
from dataclasses import dataclass

import numpy as np
from manifold3d import Manifold, OpType

from . import params as P
from .lib import basis


@dataclass(frozen=True)
class Piece:
    """A part's piece for the assembly: one colour, one solid."""
    label: str
    colour: str
    solid: Manifold


def segments(r):
    """How many sides a circle of radius r needs for its chords to stay within mesh_tol_mm."""
    if r <= P.mesh_tol_mm:
        return 4
    return max(8, 4 * math.ceil(math.pi / math.acos(1 - P.mesh_tol_mm / r) / 4))


def union(solids):
    return Manifold.batch_boolean(list(solids), OpType.Add)


def box(size, centre=(0, 0, 0)):
    """A box of `size` about `centre`."""
    return Manifold.cube(tuple(map(float, size)), center=True).translate(tuple(map(float, centre)))


def box_corners(size, centre=(0, 0, 0)):
    """The eight corners of box(size, centre)."""
    s, c = np.asarray(size, float) / 2, np.asarray(centre, float)
    return np.array([c + s * (sx, sy, sz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])


def cylinder(d, h, at=(0, 0, 0)):
    """A cylinder of diameter d, from `at` up by h along z."""
    return Manifold.cylinder(float(h), d / 2, d / 2, segments(d / 2)).translate(tuple(map(float, at)))


def frustum(base, top, z0, h):
    """A box tapering from `base` (w, d) at z0 to `top` at z0 + h."""
    pts = [(sx * w / 2, sy * d / 2, z) for (w, d), z in ((base, z0), (top, z0 + h)) for sx in (-1, 1) for sy in (-1, 1)]
    return Manifold.hull_points(pts)


def pieces(solids, colour, label):
    return [Piece(label, colour, union(solids))]


# ---------------------------------------------------------------- MX switch
def mx_switch():
    """The switch as it stands in the plate: housing over and under the plate,
    posts and pins below."""
    b, pins = P.switch_below_plate_mm, P.switch_pins
    grey = [box((P.switch_rim_mm, P.switch_rim_mm, P.switch_top_above_plate_mm), (0, 0, P.switch_top_above_plate_mm / 2)),
            box((P.switch_cutout_mm, P.switch_cutout_mm, b), (0, 0, -b / 2)),
            cylinder(P.switch_centre_post_d, 3.3, (0, 0, -b - 3.3))]
    grey += [cylinder(P.switch_side_post_d, 3.3, (sx * P.switch_side_post_x, 0, -b - 3.3)) for sx in (-1, 1)]
    gold = [cylinder(P.switch_pin_d, 3.3, (p[0], p[1], -b - 3.3)) for p in pins]
    return pieces(grey, "gray", "housing") + pieces(gold, "gold", "pins")


def mx_switch_room():
    """The switch's room in the body: the hole through the plate, the housing's
    pocket under it with the clip reliefs, and the posts' and pins' holes down
    to the socket's top."""
    hole = P.switch_cutout_mm + 2 * P.switch_cutout_clearance_mm
    up = P.switch_top_above_plate_mm + 20
    b = P.switch_below_plate_mm
    rooms = [box((hole, hole, up + b), (0, 0, (up - b) / 2))]
    # Clip reliefs on the +-y sides, under the plate's clip land.
    d = P.switch_clip_relief_mm + P.switch_cutout_clearance_mm + 0.1
    rooms += [box((P.switch_clip_width_mm, d, b - P.plate_mm),
                  (0, sy * (hole / 2 + d / 2 - 0.1), -P.plate_mm - (b - P.plate_mm) / 2)) for sy in (-1, 1)]
    # Posts and pins through the PCB layer, to just above the socket's bottom.
    depth = P.pcb_layer_mm + P.socket_body_mm[2] - 0.2
    z, c = -b - depth, 2 * P.post_clearance_mm
    rooms.append(cylinder(P.switch_centre_post_d + c, depth + 0.1, (0, 0, z)))
    rooms += [cylinder(P.switch_side_post_d + c, depth + 0.1, (sx * P.switch_side_post_x, 0, z)) for sx in (-1, 1)]
    rooms += [cylinder(P.switch_pin_d + c, depth + 0.1, (p[0], p[1], z)) for p in P.switch_pins]
    return rooms


# ---------------------------------------------------------------- keycap (Cherry profile)
def keycap(r, u=1, pressed=0, grow=0):
    """The cap for Cherry row r, u units wide along x, `pressed` mm down, grown
    by `grow` all round (the collision probe grows it by half the clearance)."""
    extra = (u - 1) * P.cap_unit_mm
    base = (P.cap_base_mm + extra + 2 * grow, P.cap_base_mm + 2 * grow)
    top = (P.cap_top_mm[0] + extra + 2 * grow, P.cap_top_mm[1] + 2 * grow)
    return frustum(base, top, P.cap_bottom_above_plate_mm - pressed - grow, P.cap_height_mm[r - 1] + 2 * grow)


def keycap_probe(r, u=1, pressed=0):
    """The cap grown by the clearance caps must keep: the collision probe."""
    return keycap(r, u, pressed, P.cap_clearance_mm / 2)


# ---------------------------------------------------------------- hotswap socket
def socket_top_z():
    """The socket's top (its PCB face) below the plate top."""
    return -P.switch_below_plate_mm - P.pcb_layer_mm


def socket_bottom_z():
    return socket_top_z() - P.socket_body_mm[2]


def socket_boxes(grow=0):
    """The socket body as two boxes (its dogleg round the centre post), each
    about a pin cup, within the measured 11.6 x 6.2 envelope; `grow` is the
    clearance all round. Each box as (size, centre)."""
    e, c = P.socket_body_mm, P.socket_centre_mm
    t = e[2] + 2 * grow
    x0, x1, y0, y1 = c[0] - e[0] / 2, c[0] + e[0] / 2, c[1] - e[1] / 2, c[1] + e[1] / 2
    z = socket_top_z() - t / 2 + grow
    return [
        # North-east box about pin 1 (2.54, 5.08).
        ((x1 - x0 - 4.5 - 2.0 + 4.0 + 2 * grow, y1 - y0 - 2.3 + 2 * grow, t),
         ((x1 - 2.0 + x0 + 4.5) / 2, (y1 + y0 + 2.3) / 2, z)),
        # South-west box about pin 2 (-3.81, 2.54).
        ((7.0 + 2 * grow, y1 - y0 - 2.3 + 2 * grow, t), ((x0 + x0 + 7.0) / 2, (y0 + y1 - 2.3) / 2, z)),
    ]


def socket_body(grow=0):
    return [box(s, c) for s, c in socket_boxes(grow)]


def socket_tabs(grow=0):
    """The two solder tabs, flat in the socket's top face, out of its +-x ends."""
    e, c = P.socket_body_mm, P.socket_centre_mm
    return [box((P.socket_tab_mm[0] + 0.6 + 2 * grow, P.socket_tab_mm[1] + 2 * grow, 0.4 + 2 * grow),
                (c[0] + s * (e[0] / 2 + P.socket_tab_mm[0] / 2 - 0.3), y, socket_top_z() - 0.2))
            for s, y in ((-1, P.socket_tab_y[0]), (1, P.socket_tab_y[1]))]


def socket_tab_tip(side):
    """The position of the -x (column) and +x (row) tabs' tips in the key frame."""
    return np.array([P.socket_centre_mm[0] + side * (P.socket_body_mm[0] / 2 + P.socket_tab_mm[0]),
                     P.socket_tab_y[0] if side < 0 else P.socket_tab_y[1], socket_top_z()])


def hotswap_socket():
    return pieces(socket_body(), "dimgray", "socket") + pieces(socket_tabs(), "silver", "tabs")


def hotswap_socket_room():
    """The socket's pocket: body with clearance and the tabs' slots. Its shaft
    down to the bottom plate is cut in world axes (chassis.py socket_shaft),
    so it stands square to the plate under a tilted key."""
    return socket_body(P.socket_clearance_mm) + socket_tabs(P.socket_clearance_mm)


# ---------------------------------------------------------------- diode
def diode():
    """The diode's body, along y about the origin."""
    d = cylinder(P.diode_mm[1], P.diode_mm[0]).rotate((-90, 0, 0)).translate((0, -P.diode_mm[0] / 2, 0))
    return pieces([d], "orange", "diode")


# ---------------------------------------------------------------- controller (nRF52840 Pro Micro)
def mcu_pcb_z():
    """The board's underside (its component side) is this far over the well's floor."""
    return P.mcu_parts_mm


def mcu_board():
    """The board in its frame (layout.py mcu_frame): origin at the middle of its
    port end on the well's floor, +y along the board into the hand, components
    down toward the bottom plate."""
    b, u = P.mcu_board_mm, P.mcu_usb_mm
    board = box(b, (0, b[1] / 2, mcu_pcb_z() + b[2] / 2))
    usb_len = 7.5 + P.mcu_usb_overhang_mm
    usb = box((u[0], usb_len, u[1]), (0, usb_len / 2 - P.mcu_usb_overhang_mm, mcu_pcb_z() - u[1] / 2))
    reset = cylinder(3, 1.5, (P.mcu_reset_mm[0], P.mcu_reset_mm[1], mcu_pcb_z() - 1.5))
    return (pieces([board], "darkgreen", "board") + pieces([usb], "silver", "usb")
            + pieces([reset], "white", "reset"))


def mcu_room():
    """The board's pocket: from the well's floor up over the board, with the
    wall's opening for the plug, chamfered outward."""
    b, c, o = P.mcu_board_mm, P.mcu_clearance_mm, P.mcu_usb_opening_mm
    h = mcu_pcb_z() + b[2] + c + 1
    pocket = box((b[0] + 2 * c, b[1] + 2 * c, h), (0, b[1] / 2, h / 2 - 1))
    # The opening runs along -y through the back wall: drawn along z, then
    # turned so that its z runs along +y from wall_mm + 5 out.
    opening = frustum((o[0] + 2, o[1] + 2), o, 0, P.wall_mm + 5)
    turn = basis((1, 0, 0), (0, 0, -1), (0, 1, 0), (0, -P.wall_mm - 5, mcu_pcb_z() - P.mcu_usb_mm[1] / 2))
    return [pocket, opening.transform(turn[:3])]


def mcu_reset_hole():
    """The pinhole in the bottom plate over the reset button."""
    return cylinder(2, 20, (P.mcu_reset_mm[0], P.mcu_reset_mm[1], -10))


# ---------------------------------------------------------------- battery
def battery():
    return pieces([box(P.battery_mm, (0, 0, P.battery_mm[2] / 2 + 0.2))], "steelblue", "battery")


def battery_room():
    c, b = P.battery_clearance_mm, P.battery_mm
    return [box((b[0] + 2 * c, b[1] + 2 * c, b[2] + c + 2), (0, 0, (b[2] + c) / 2 - 1))]


# ---------------------------------------------------------------- power switch
def power_switch_part():
    """A slide switch in its frame: body centred, knob out of -y (through the wall)."""
    b, k = P.power_switch_mm, P.power_switch_knob_mm
    return (pieces([box(b)], "black", "switch")
            + pieces([box((k[0], k[2], k[0]), (0, -b[1] / 2 - k[2] / 2, 0))], "red", "knob"))


def power_switch_room():
    """The switch's pocket in the body, a close fit round it, with the knob's
    slot through the wall and a notch behind for the pins and their wires, all
    open down through the underside: it goes in from below, knob in its slot,
    and the plinth's seat holds it against the ceiling."""
    b, k, c = P.power_switch_mm, P.power_switch_knob_mm, P.power_switch_clearance_mm
    pins = P.power_switch_pins_mm
    h = b[2] + 2 * c + 20
    z = b[2] / 2 + c - h / 2
    return [box((b[0] + 2 * c, b[1] + 2 * c, h), (0, 0, z)),
            box((k[1] + 2 * c, 10, h), (0, -b[1] / 2 - 5, z)),
            box((pins[0], pins[1] + c, h), (0, b[1] / 2 + (pins[1] + c) / 2, z))]


# ---------------------------------------------------------------- screws
def insert_hole():
    return cylinder(P.insert_d, P.insert_depth_mm + 1, (0, 0, -1))


def counterbore_d():
    return P.screw_head_d + P.screw_head_clearance_mm


def screw_hole(h):
    """The screw's hole up through the bottom plate, which is h thick here (z = 0
    its underside): counterbored from below for the head so that every screw
    grips the same screw_grip_mm of plate under the body."""
    holes = [cylinder(P.screw_d, h + 2, (0, 0, -1))]
    if h > P.screw_grip_mm:
        holes.append(cylinder(counterbore_d(), h - P.screw_grip_mm + 1, (0, 0, -1)))
    return holes

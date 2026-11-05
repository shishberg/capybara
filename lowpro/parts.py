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


def handed(x):
    """A key-frame x on a switch or socket as this half draws it: the left half
    is built as the right and mirrored, so it draws them mirrored to come out true."""
    return -x if P.half == "left" else x


def switch_pins():
    return [(handed(x), y) for x, y in P.switch_pins]


# ---------------------------------------------------------------- MX switch
def mx_switch():
    """The switch as it stands in the plate: housing over and under the plate,
    posts and pins below."""
    b, pins, post = P.switch_below_plate_mm, switch_pins(), P.switch_post_mm
    grey = [box((P.switch_rim_mm, P.switch_rim_mm, P.switch_top_above_plate_mm), (0, 0, P.switch_top_above_plate_mm / 2)),
            box((P.switch_cutout_mm, P.switch_cutout_mm, b), (0, 0, -b / 2)),
            cylinder(P.switch_centre_post_d, post, (0, 0, -b - post))]
    grey += [cylinder(P.switch_side_post_d, post, (sx * P.switch_side_post_x, 0, -b - post)) for sx in (-1, 1)]
    gold = [cylinder(P.switch_pin_d, post, (p[0], p[1], -b - post)) for p in pins]
    return pieces(grey, "gray", "housing") + pieces(gold, "gold", "pins")


def mx_switch_room():
    """The switch's room in the body: the hole through the plate, the housing's
    pocket under it with the clip reliefs, and the posts' holes and the socket's
    collars' holes, which the pins come down, through the PCB layer."""
    hole = P.switch_cutout_mm + 2 * P.switch_cutout_clearance_mm
    up = P.switch_top_above_plate_mm + 20
    b = P.switch_below_plate_mm
    rooms = [box((hole, hole, up + b), (0, 0, (up - b) / 2))]
    # Clip reliefs on the +-y sides, under the plate's clip land.
    d = P.switch_clip_relief_mm + P.switch_cutout_clearance_mm + 0.1
    rooms += [box((P.switch_clip_width_mm, d, b - P.plate_mm),
                  (0, sy * (hole / 2 + d / 2 - 0.1), -P.plate_mm - (b - P.plate_mm) / 2)) for sy in (-1, 1)]
    # Through the PCB layer, past the posts' tips.
    depth = P.switch_post_mm + P.post_clearance_mm
    z, c = -b - depth, 2 * P.post_clearance_mm
    rooms.append(cylinder(P.switch_centre_post_d + c, depth + 0.1, (0, 0, z)))
    rooms += [cylinder(P.switch_side_post_d + c, depth + 0.1, (sx * P.switch_side_post_x, 0, z)) for sx in (-1, 1)]
    collar = P.socket_collar_mm[0] + 2 * P.socket_clearance_mm
    rooms += [cylinder(collar, depth + 0.1, (p[0], p[1], z)) for p in switch_pins()]
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


def keycap_room(r, u=1):
    """The room the cap takes from whatever stands near it: its sweep from rest
    to the bottom of its travel, with the clearance caps keep."""
    return (keycap_probe(r, u) + keycap_probe(r, u, P.cap_travel_mm)).hull()


# ---------------------------------------------------------------- hotswap socket
def socket_top_z():
    """The socket's top (its PCB face) below the plate top."""
    return -P.switch_below_plate_mm - P.pcb_layer_mm


def socket_bottom_z():
    return socket_top_z() - P.socket_body_mm[2]


def socket_boxes(grow=0):
    """The socket body as two boxes round its step at the centre post, the rear
    lobe the body's whole length and the front lobe up to the step; `grow` is
    the clearance all round. Each box as (size, centre)."""
    e, c = P.socket_body_mm, P.socket_centre_mm
    front, lobe = P.socket_lobe_mm
    t = e[2] + 2 * grow
    x0, x1, y0, y1 = c[0] - e[0] / 2, c[0] + e[0] / 2, c[1] - e[1] / 2, c[1] + e[1] / 2
    z = socket_top_z() - t / 2 + grow
    return [((e[0] + 2 * grow, lobe + 2 * grow, t), (handed(c[0]), y1 - lobe / 2, z)),
            ((front + 2 * grow, lobe + 2 * grow, t), (handed(x0 + front / 2), y0 + lobe / 2, z))]


def socket_body(grow=0):
    return [box(s, c) for s, c in socket_boxes(grow)]


def socket_tab_boxes(grow=0):
    """The two terminals as (size, centre), the -x one first, out of the socket's
    ends, down from just over its top."""
    e, c = P.socket_body_mm, P.socket_centre_mm
    reach, width, height = P.socket_tab_mm
    return sorted([((reach + 0.6 + 2 * grow, width + 2 * grow, height + 2 * grow),
                    (handed(c[0] + s * (e[0] / 2 + reach / 2 - 0.3)), y, socket_bottom_z() + height / 2))
                   for s, y in ((-1, P.socket_tab_y[0]), (1, P.socket_tab_y[1]))], key=lambda b: b[1][0])


def socket_tabs(grow=0):
    return [box(s, c) for s, c in socket_tab_boxes(grow)]


def socket_collars():
    """The two collars, up from the socket's top round its pin cups."""
    d, h = P.socket_collar_mm
    return [cylinder(d, h, (p[0], p[1], socket_top_z())) for p in switch_pins()]


def socket_tab_tip(side):
    """The position of the -x and +x tabs' tips in the key frame."""
    s = handed(side)
    return np.array([handed(P.socket_centre_mm[0] + s * (P.socket_body_mm[0] / 2 + P.socket_tab_mm[0])),
                     P.socket_tab_y[0] if s < 0 else P.socket_tab_y[1], socket_top_z()])


def hotswap_socket():
    return pieces(socket_body() + socket_collars(), "dimgray", "socket") + pieces(socket_tabs(), "silver", "tabs")


def hotswap_socket_room():
    """The socket's pocket: body with clearance and the tabs' slots. Its shaft
    down to the bottom plate is cut in world axes (chassis.py socket_shaft),
    so it stands square to the plate under a tilted key."""
    return socket_body(P.socket_clearance_mm) + socket_tabs(P.socket_clearance_mm)


# ---------------------------------------------------------------- diode
def diode_body():
    """The diode's body, along y about the origin."""
    return cylinder(P.diode_mm[1], P.diode_mm[0]).rotate((-90, 0, 0)).translate((0, -P.diode_mm[0] / 2, 0))


def diode():
    return pieces([diode_body()], "orange", "diode")


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
    return pieces([board], "red", "board") + pieces([usb], "silver", "usb")


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
    """The switch's pocket in the plinth, a close fit round it, with the knob's
    slot through the wall and a notch behind for the pins and their wires into
    the well, a wire deeper than the pocket, all open up through the plinth's
    top: it drops in from above, knob in its slot, and the body's underside
    closes over it."""
    b, k, c = P.power_switch_mm, P.power_switch_knob_mm, P.power_switch_clearance_mm
    pins = P.power_switch_pins_mm
    h = b[2] + 2 * c + 20
    z = h / 2 - b[2] / 2 - c
    return [box((b[0] + 2 * c, b[1] + 2 * c, h), (0, 0, z)),
            box((k[1] + 2 * c, 10, h), (0, -b[1] / 2 - 5, z)),
            box((pins[0], pins[1] + c, h + P.wire_d_mm), (0, b[1] / 2 + (pins[1] + c) / 2, z - P.wire_d_mm / 2))]


# ---------------------------------------------------------------- reset button
def reset_button_part():
    """The switch in its frame, on edge: body centred, plunger out of -y (through
    the wall), legs along the back at either side."""
    b, (d, proud), (span, pitch, w, t) = P.reset_button_mm, P.reset_plunger_mm, P.reset_leg_mm
    plunger = cylinder(d, proud).rotate((90, 0, 0)).translate((0, -b[1] / 2, 0))
    legs = [box((span, t, w), (0, b[1] / 2 - t / 2, s * pitch / 2)) for s in (-1, 1)]
    return pieces([box(b), plunger], "black", "reset button") + pieces(legs, "silver", "reset button's legs")


def reset_wire_ways():
    """Where the two wires pass the stop, as (x, y) in the switch's frame: the
    middle of each way, between the stop and the end of the legs' slot."""
    c, (w, deep) = P.reset_button_clearance_mm, P.reset_stop_mm
    x = (w / 2 + P.reset_leg_mm[0] / 2 + c) / 2
    return [(s * x, P.reset_button_mm[1] / 2 + c + deep / 2) for s in (-1, 1)]


def reset_button_room():
    """The switch's pocket, its body against the skin of the wall, with a round
    hole through the skin for the plunger, a wider slot along its back for the
    legs, and a way for each wire either side of the stop into the well. It's cut
    from the plinth and the body alike: the frame's on the seam between them, so
    each has half, and each half of the stop takes half the press."""
    b, c, (d, _), (span, _, _, t) = P.reset_button_mm, P.reset_button_clearance_mm, P.reset_plunger_mm, P.reset_leg_mm
    w, deep = P.reset_stop_mm
    h = b[2] + 2 * c
    way = span / 2 + c - w / 2
    return ([box((b[0] + 2 * c, b[1] + c, h), (0, c / 2, 0)),
             box((span + 2 * c, t + c, h), (0, b[1] / 2 + (c - t) / 2, 0)),
             cylinder(d + 2 * c, 10).rotate((90, 0, 0)).translate((0, -b[1] / 2, 0))]
            + [box((way, deep + 1, h), (x, y - 0.5, 0)) for x, y in reset_wire_ways()])


def reset_plunger_slot():
    """The plinth's half of the hole, opened upward so that the plunger drops
    in from above wherever the seam, which slopes, is over the frame's middle."""
    b, c, d = P.reset_button_mm, P.reset_button_clearance_mm, P.reset_plunger_mm[0]
    return [box((d + 2 * c, 10, b[2] / 2), (0, -b[1] / 2 - 5, b[2] / 4))]


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

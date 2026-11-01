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


# ---------------------------------------------------------------- key tile
TILE_COLOURS = {"hotswap socket": "dimgray", "RGB LED": "white", "diode": "black"}


def tile_board(grow=0):
    """The tile's board as (size, centre): its top switch_below_plate_mm under the plate's."""
    s, t = P.tile_mm + 2 * grow, P.pcb_layer_mm + 2 * grow
    return (s, s, t), (0, 0, -P.switch_below_plate_mm - P.pcb_layer_mm / 2)


def hanging_boxes():
    """What hangs under a key's switch, with its clearance, as boxes (size,
    centre) in the key's frame: the tile's board and the parts under it, or
    the socket."""
    if P.key_parts == "tiles":
        top = -P.switch_below_plate_mm
        c = P.tile_clearance_mm
        return [tile_board(c)] + [(tuple(s + 2 * c for s in size), (x, y, top + z)) for _, size, (x, y, z) in P.tile_parts]
    return socket_boxes(P.socket_clearance_mm)


def key_tile():
    """The tile as it hangs from the switch: the board and the parts under it."""
    top = -P.switch_below_plate_mm
    return (pieces([box(*tile_board())], "darkgreen", "tile")
            + [p for name, size, (x, y, z) in P.tile_parts
               for p in pieces([box(size, (x, y, top + z))], TILE_COLOURS.get(name, "black"), name)])


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
    b, c = P.mcu_board_mm, P.mcu_clearance_mm
    h = mcu_pcb_z() + b[2] + c + 1
    pocket = box((b[0] + 2 * c, b[1] + 2 * c, h), (0, b[1] / 2, h / 2 - 1))
    return [pocket, mcu_opening()]


def mcu_opening():
    """The wall's opening for the plug, chamfered outward: drawn along z, then
    turned so that its z runs along -y from wall_mm + 5 out."""
    o = P.mcu_usb_opening_mm
    opening = frustum((o[0] + 2, o[1] + 2), o, 0, P.wall_mm + 5)
    turn = basis((1, 0, 0), (0, 0, -1), (0, 1, 0), (0, -P.wall_mm - 5, mcu_pcb_z() - P.mcu_usb_mm[1] / 2))
    return opening.transform(turn[:3])


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


def power_switch_room(up=0):
    """The switch's pocket, with the knob's slot through the wall; `up` opens it
    that far upward (through the plate's top, so the switch drops in from the body's side)."""
    b, k, c = P.power_switch_mm, P.power_switch_knob_mm, 0.3
    rooms = [box((b[0] + 2 * c, b[1] + 2 * c, b[2] + 2 * c)),
             box((k[1] + 2 * c, 10, k[0] + 2 * c), (0, -b[1] / 2 - 5, 0))]
    if up > 0:
        rooms.append(box((b[0] + 2 * c, b[1] + 2 * c, up), (0, 0, up / 2)))
    return rooms


# ---------------------------------------------------------------- TRRS jack
def along_y(d, length, at):
    """A cylinder of diameter d along +y from `at` by length."""
    return cylinder(d, length).rotate((-90, 0, 0)).translate(tuple(map(float, at)))


def trrs_jack():
    """The jack in its frame (layout.py trrs_frame): its body behind the origin
    (-y), lugs up, the barrel along +y from the origin."""
    b, (bl, bd) = P.trrs_body_mm, P.trrs_barrel_mm
    return (pieces([box((b[1], b[0], b[2]), (0, -b[0] / 2, b[2] / 2))], "black", "jack")
            + pieces([along_y(bd, bl, (0, 0, b[2] / 2))], "silver", "barrel"))


def trrs_room(up=0):
    """The jack's pocket, room over it for the wires on its lugs, the barrel's
    hole and the plug's through the wall; `up` opens the pocket that far upward
    (so the jack drops in from the body's side)."""
    b, (bl, bd), c = P.trrs_body_mm, P.trrs_barrel_mm, P.trrs_clearance_mm
    h = b[2] + 2 * c + 2
    rooms = [box((b[1] + 2 * c, b[0] + 2 * c, h), (0, -b[0] / 2, h / 2 - c)),
             along_y(bd + 2 * c, bl + 0.1, (0, -0.05, b[2] / 2)), trrs_plug_hole()]
    if up > 0:
        rooms.append(box((b[1] + 2 * c, b[0] + 2 * c, up), (0, -b[0] / 2, up / 2)))
    return rooms


# ---------------------------------------------------------------- reset switch
def trrs_plug_hole():
    """The plug's hole through the wall, from the barrel's end."""
    b, (bl, _), c = P.trrs_body_mm, P.trrs_barrel_mm, P.trrs_clearance_mm
    return along_y(P.trrs_plug_d + 2 * c, P.wall_mm + 5, (0, bl, b[2] / 2))


def reset_switch():
    """The switch on edge in its frame (layout.py reset_frame): origin at the
    middle of its plunger face, its body behind (+x), the plunger out along -x,
    the legs out of its sides at the back."""
    (h, w, d), (pd, pp) = P.reset_body_mm, P.reset_plunger_mm
    legs = [box((0.6, (P.reset_leg_span_mm - w) / 2, 0.8), (d - 0.4, s * (w + P.reset_leg_span_mm) / 4, 0))
            for s in (-1, 1)]
    plunger = cylinder(pd, pp).rotate((0, -90, 0))
    return (pieces([box((d, w, h), (d / 2, 0, 0))], "silver", "reset")
            + pieces([plunger], "black", "plunger") + pieces(legs, "silver", "legs"))


def reset_room(up=0):
    """The switch's pocket in the wall, reaching back into the bay for its
    wires, and the plunger's hole through the skin in front of it; `up` opens
    the pocket that far upward (so it drops in from the body's side)."""
    (h, w, d), (pd, pp), c = P.reset_body_mm, P.reset_plunger_mm, P.reset_clearance_mm
    reach = P.wall_mm + 1
    rooms = [box((reach, P.reset_leg_span_mm + 2 * c, h + 2 * c), (reach / 2 - c, 0, 0)), reset_plunger_hole()]
    if up > 0:
        rooms.append(box((reach, P.reset_leg_span_mm + 2 * c, up), (reach / 2 - c, 0, up / 2)))
    return rooms


def reset_plunger_hole():
    """The plunger's hole through the skin in front of the switch."""
    (_, _, _), (pd, _), c = P.reset_body_mm, P.reset_plunger_mm, P.reset_clearance_mm
    return cylinder(pd + 2 * c, P.reset_skin_mm + 2).rotate((0, -90, 0)).translate((0.1, 0, 0))


# ---------------------------------------------------------------- the AS5600 knob
# In its frame (chassis.py knob_frame): origin on the axis at the wall's outer
# face, +x in along the axis. Outside: the knob on its shaft. In the wall, from
# the face in: the bearing, flush with the face; the shaft's end a millimetre
# past it with the magnet in it; the magnet's gap; the sensor board, chip
# toward the magnet, its pads up.
def along_x(d, x0, x1):
    """A cylinder of diameter d along x from x0 to x1."""
    return cylinder(d, x1 - x0).rotate((0, 90, 0)).translate((float(x0), 0, 0))


def knob_shaft_end():
    return P.knob_bearing_mm[2] + 1


def knob_sensor_x():
    """The sensor board's face (the chip's) and back."""
    x = knob_shaft_end() + P.knob_magnet_mm[2]
    return x, x + P.knob_sensor_mm[2]


def knob():
    (kd, kh, kg), (bore, od, bw), (md, ml, _), s = P.knob_mm, P.knob_bearing_mm, P.knob_magnet_mm, P.knob_sensor_mm
    end, (f, b) = knob_shaft_end(), knob_sensor_x()
    ring = along_x(od, 0, bw) - along_x(bore, -1, bw + 1)
    return (pieces([along_x(kd, -kg - kh, -kg)], "dimgray", "knob")
            + pieces([along_x(bore, -kg - kh + 2, end) - along_x(md, end - ml, end + 1)], "silver", "shaft")
            + pieces([ring], "lightgray", "bearing") + pieces([along_x(md, end - ml, end)], "firebrick", "magnet")
            + pieces([box((b - f, s[0], s[1]), ((f + b) / 2, 0, 0))], "purple", "sensor"))


def knob_room(reach, up=0):
    """The knob's rooms: the bearing's pocket open to the outside; room behind
    it for the shaft's end, clear of the bearing's outer race (the pocket's
    floor, between the two races, holds that); the sensor's slot; and its
    wires' slot, `reach` along +y into the well, over the sensor's pads. `up`
    opens both slots that far upward (so the board drops in from the body's
    side)."""
    (bore, od, bw), s, c = P.knob_bearing_mm, P.knob_sensor_mm, P.knob_clearance_mm
    f, b = knob_sensor_x()
    w = P.channel_w_mm
    sensor_h, wires_h = s[1] + 2 * c + up, 2 * w + c + up
    return [knob_bearing_pocket(), along_x((bore + od) / 2, bw - 0.1, f),
            box((b - f + 2 * c, s[0] + 2 * c, sensor_h), ((f + b) / 2, 0, sensor_h / 2 - s[1] / 2 - c)),
            box((w, reach, wires_h), (b - w / 2 + c, reach / 2, wires_h / 2 + s[1] / 2 - 2 * w))]


def knob_bearing_pocket():
    """The bearing's pocket, open to the outside."""
    (_, od, bw), c = P.knob_bearing_mm, P.knob_clearance_mm
    return along_x(od + 2 * c, -1, bw)


def knob_clear():
    """The room the knob turns in outside the wall."""
    (kd, kh, kg), c = P.knob_mm, P.knob_clearance_mm
    return along_x(kd + 2 * c, -kg - kh - c, -kg + c)


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

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


def along_x(d, h, at=(0, 0, 0), d_end=None):
    """A cylinder of diameter d (tapering to d_end) from `at` along +x by h."""
    r1 = d / 2 if d_end is None else d_end / 2
    return (Manifold.cylinder(float(h), d / 2, r1, segments(max(d, d_end or 0) / 2)).rotate((0, 90, 0))
            .translate(tuple(map(float, at))))


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


def mx_switch_rim_room():
    """The room over the plate for the switch's rim (its seat's footprint, with
    the hole's clearance) up to where the cap's sweep takes over, as the
    Capybara keeps it (docs/editor-chassis.md): a tilted key's rim leans out
    past the plate's land."""
    w = P.switch_rim_mm + 2 * P.switch_cutout_clearance_mm
    h = P.cap_bottom_above_plate_mm - P.cap_travel_mm + 0.1
    return [box((w, w, h), (0, 0, h / 2))]


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


def socket_underside_either_hand():
    return [(hand * (c[0] + i * s[0] / 2), c[1] + j * s[1] / 2, socket_bottom_z())
            for s, c in socket_boxes() + socket_tab_boxes() for i in (-1, 1) for j in (-1, 1) for hand in (-1, 1)]


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
def diode_y():
    return -P.switch_centre_post_d / 2 - P.post_clearance_mm - P.min_wall_mm - P.diode_room_mm - P.diode_mm[1] / 2


def diode_z():
    return socket_top_z() - P.diode_mm[1] / 2 - P.diode_room_mm


def diode_rim_points():
    n, r = 24, P.diode_mm[1] / 2
    return [(x, diode_y() + r * math.cos(a), diode_z() + r * math.sin(a))
            for x in (-P.diode_mm[0] / 2, P.diode_mm[0] / 2) for a in (2 * math.pi * i / n for i in range(n))]


def diode_body():
    """The diode's body, along y about the origin."""
    return cylinder(P.diode_mm[1], P.diode_mm[0]).rotate((-90, 0, 0)).translate((0, -P.diode_mm[0] / 2, 0))


def diode():
    return pieces([diode_body()], "orange", "diode")


# ---------------------------------------------------------------- controller (nRF52840 Pro Micro)
def mcu_pcb_z():
    """The board's underside (its component side) is this far over the rest."""
    return P.mcu_parts_mm


def mcu_board():
    """The board in its frame (chassis.py mcu_frame): origin at the middle of its
    port end on the rest, +y along the board into the hand, components down
    toward the bottom plate."""
    b, u = P.mcu_board_mm, P.mcu_usb_mm
    board = box(b, (0, b[1] / 2, mcu_pcb_z() + b[2] / 2))
    usb_len = 7.5 + P.mcu_usb_overhang_mm
    usb = box((u[0], usb_len, u[1]), (0, usb_len / 2 - P.mcu_usb_overhang_mm, mcu_pcb_z() - u[1] / 2))
    return pieces([board], "red", "board") + pieces([usb], "silver", "usb")


def mcu_pocket(h):
    """The board's room in plan, from the floor of the plinth's pocket up to h."""
    b, c, d = P.mcu_board_mm, P.mcu_clearance_mm, P.bay_pocket_mm
    return box((b[0] + 2 * c, b[1] + 2 * c, h + d), (0, b[1] / 2, (h - d) / 2))


def mcu_room(plinth=False):
    """The board's pocket: from the plinth's pocket up over the board, the port's
    slot past the board's end, and the hole for the plug and its moulding, from
    the port's end out through the wall's face, flaring at 45 degrees. The port
    stands on the rest, so the plinth's slot stops level with the rest's top; the
    body's goes on under it, past the seam, which dips under the rest on one side."""
    b, c, u, r = P.mcu_board_mm, P.mcu_clearance_mm, P.mcu_usb_mm, P.mcu_usb_relief_mm
    pocket = mcu_pocket(mcu_pcb_z() + b[2] + c)
    # The hole runs along -y through the back wall: drawn along z, then turned so
    # that its z runs along +y, in to the port's end.
    centre = mcu_pcb_z() - u[1] / 2
    floor, roof = 0 if plinth else -c, u[1] + c
    port = box((u[0] + 2 * c, P.mcu_usb_overhang_mm + 2, roof - floor), (0, -P.mcu_usb_overhang_mm / 2, (floor + roof) / 2))
    flare = 5
    hole = frustum((r[0] + 2 * flare, r[1] + 2 * flare), r, 0, flare)
    turn = basis((1, 0, 0), (0, 0, -1), (0, 1, 0), (0, -P.mcu_usb_overhang_mm - flare, centre))
    return [pocket, port, hole.transform(turn[:3])]


# ---------------------------------------------------------------- battery
def battery():
    return pieces([box(P.battery_mm, (0, 0, P.battery_mm[2] / 2))], "steelblue", "battery")


def battery_room():
    c, b = P.battery_clearance_mm, P.battery_mm
    return [box((b[0] + 2 * c, b[1] + 2 * c, b[2] + c), (0, 0, (b[2] + c) / 2))]


# ---------------------------------------------------------------- power switch
def power_switch_part():
    """A slide switch in its frame: body centred, knob out of -y (through the wall)."""
    b, k = P.power_switch_mm, P.power_switch_knob_mm
    return (pieces([box(b)], "black", "switch")
            + pieces([box((k[0], k[2], k[0]), (0, -b[1] / 2 - k[2] / 2, 0))], "red", "knob"))


def power_switch_room():
    """The switch's pocket in the body, a close fit round it, with the knob's
    slot through the wall and a notch behind for the pins and their wires into
    the well, a wire deeper than the pocket, all open down through the body's
    underside: with the body turned over it drops in, knob in its slot, and the
    plinth closes under it."""
    b, k, c = P.power_switch_mm, P.power_switch_knob_mm, P.power_switch_clearance_mm
    pins = P.power_switch_pins_mm
    h = b[2] + 2 * c + 20
    z = b[2] / 2 + c - h / 2
    return [box((b[0] + 2 * c, b[1] + 2 * c, h), (0, 0, z)),
            box((k[1] + 2 * c, 10, h), (0, -b[1] / 2 - 5, z)),
            box((pins[0], pins[1] + c, h + P.wire_d_mm), (0, b[1] / 2 + (pins[1] + c) / 2, z + P.wire_d_mm / 2))]


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
    hole through the skin for the plunger, chamfered at the wall's face, a wider slot along its back for the
    legs, and a way for each wire either side of the stop into the well. It's cut
    from the plinth and the body alike: the frame's on the seam between them, so
    each has half, and each half of the stop takes half the press."""
    b, c, (d, skin), (span, _, _, t) = P.reset_button_mm, P.reset_button_clearance_mm, P.reset_plunger_mm, P.reset_leg_mm
    w, deep = P.reset_stop_mm
    h = b[2] + 2 * c
    way = span / 2 + c - w / 2
    k = P.reset_chamfer_mm
    chamfer = Manifold.cylinder(k + 1, d / 2 + c + k + 1, d / 2 + c).rotate((-90, 0, 0)).translate((0, -b[1] / 2 - skin - 1, 0))
    return ([box((b[0] + 2 * c, b[1] + c, h), (0, c / 2, 0)),
             box((span + 2 * c, t + c, h), (0, b[1] / 2 + (c - t) / 2, 0)),
             cylinder(d + 2 * c, 11).rotate((90, 0, 0)).translate((0, 1 - b[1] / 2, 0)), chamfer]
            + [box((way, deep + 1, h), (x, y - 0.5, 0)) for x, y in reset_wire_ways()])


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


# ---------------------------------------------------------------- the Capybara's parts (design "capybara")
# Drawn from the editor project (params.capybara; docs/editor-chassis.md and
# docs/pro-micro.md describe them): the key tile in the key frame, its parts'
# x handed like the switch's pins; and the Pro Micro, the TRRS jack and the
# reset switch each in the editor's frame for it, which stands on the floor
# (the seam) at the part's standoff. The rooms are what the shell loses to
# them; the cradles are what the plinth gains.
def tile_top_z():
    return -P.capybara["tile"]["plate_top_to_pcb_top_mm"]


def tile_boxes(clear=False):
    """The tile's board and the parts under it as (size, centre) in the key
    frame, each grown by its clearance when `clear`."""
    t = P.capybara["tile"]
    s, c = t["size_mm"], t["clearance_mm"] if clear else 0
    boxes = [((s[0] + 2 * c, s[1] + 2 * c, s[2] + 2 * c), (0, 0, tile_top_z() - s[2] / 2))]
    c = t["component_clearance_mm"] if clear else 0
    for p in t["components"]:
        ps, pc = p["size_mm"], p["center_mm"]
        boxes.append(((ps[0] + 2 * c, ps[1] + 2 * c, ps[2] + 2 * c), (handed(pc[0]), pc[1], tile_top_z() + pc[2])))
    return boxes


def notch_corners():
    """Each corner notch's centre in the key frame's plan, and the corner's signs."""
    t = P.capybara["tile"]
    d = t["size_mm"][0] / 2 - t["corner_notch_mm"]["inset_mm"]
    return [((sx * d, sy * d), (sx, sy)) for sx in (-1, 1) for sy in (-1, 1)]


def notch_cuts(r, out, z0, h):
    """What a notch takes out of the tile, from z0 up by h: the circle of radius
    r at its centre, and the square from there out by `out` to the corner."""
    return [s for (cx, cy), (sx, sy) in notch_corners()
            for s in (cylinder(2 * r, h, (cx, cy, z0)), box((out, out, h), (cx + sx * out / 2, cy + sy * out / 2, z0 + h / 2)))]


def tile():
    (bs, bc), *parts = tile_boxes()
    t = P.capybara["tile"]
    board = box(bs, bc) - union(notch_cuts(t["corner_notch_mm"]["radius_mm"], t["corner_notch_mm"]["inset_mm"], bc[2] - bs[2] / 2 - 1, bs[2] + 2))
    colours = {"hotswap socket": "dimgray", "RGB LED": "white", "diode": "orange"}
    return (pieces([board], "darkgreen", "tile")
            + [Piece(p["name"], colours[p["name"]], box(*b)) for p, b in zip(t["components"], parts)])


def posts():
    """The pegs in the tile's corner notches, in the key frame: round, the
    notch less peg_fit_mm, from the board's underside up into the sleeve, each
    webbed out to the pocket's corner (the tile's corner outside the notch is
    cut away too)."""
    t = P.capybara["tile"]
    under = tile_top_z() - t["size_mm"][2]
    out = t["corner_notch_mm"]["inset_mm"] + t["clearance_mm"] + 0.1
    return union(notch_cuts(t["corner_notch_mm"]["radius_mm"] - P.peg_fit_mm, out, under, sleeve_bottom_z() + 0.1 - under))


def tile_room():
    """The tile and its parts with their clearances, less the pegs: its pocket."""
    (bs, bc), *parts = tile_boxes(True)
    return [box(bs, bc) - posts()] + [box(s, c) for s, c in parts]


def tile_bottom_z():
    return min(c[2] - s[2] / 2 for s, c in tile_boxes(True))


def tile_room_box():
    """The pocket's bounding box in the key frame: (side, top z, depth)."""
    s, c = tile_boxes(True)[0]
    return s[0], c[2] + s[2] / 2, c[2] + s[2] / 2 - tile_bottom_z()


def plate_half():
    """Half the plate's side: past the switch's seat by the Capybara's margin, or
    out to the tile's clearance when that's further, so the plate covers the tile."""
    t = P.capybara["tile"]
    return max(P.switch_rim_mm / 2 + P.capybara["chassis"]["plate_margin_mm"], t["size_mm"][0] / 2 + t["clearance_mm"])


def sleeve_bottom_z():
    return tile_top_z() + P.sleeve_gap_mm


def plate_block():
    """The plate and the sleeve under it: the plate's square from just over its
    top (the shell trims it to the top) down through its thickness, and the
    sleeve over the tile's footprint from inside the plate down to the sleeve's
    underside over the tile (the editor's seats.ts sleeveBox)."""
    w, top, plate = 2 * plate_half(), 0.1, P.top_skin_mm
    tile, bottom = P.capybara["tile"]["size_mm"], sleeve_bottom_z()
    return union([box((w, w, top + plate), (0, 0, (top - plate) / 2)),
                  box((tile[0], tile[1], -plate / 2 - bottom), (0, 0, (-plate / 2 + bottom) / 2))])


def mcu():
    return P.capybara["pro_micro"]


def pin_at(n):
    """Pro Micro pin n's centre on the board's top: pins 1 to 12 down one edge
    from the port end, 13 to 24 back up the other, as on a DIP."""
    b = mcu()
    bx, _, bz = b["board_mm"]
    left = n <= 12
    i = n - 1 if left else 24 - n
    return (-bx / 2 + b["first_pin_mm"] + i * b["pin_pitch_mm"], (-1 if left else 1) * b["row_spacing_mm"] / 2, bz)


def plug_pins():
    """The pins that take a Dupont housing: every net's, the jack's and the reset switch's."""
    return sorted(set(mcu()["pins"].values()) | {w["pin"] for w in P.capybara["trrs"]["wires"]}
                  | {w["pin"] for w in P.capybara["reset"]["wires"]})


def usb_mouth_x():
    """The USB-C receptacle's mouth, past the board's port end, which faces -x."""
    return -mcu()["board_mm"][0] / 2 - mcu()["usb_overhang_mm"]


def pro_micro():
    """The board on its standoff, components up: its USB-C receptacle at the
    port end, its parts behind that, and on each wired pin a header's spacer,
    the Dupont housing on it and the room over that for its wire to come out."""
    b = mcu()
    bx, by, bz = b["board_mm"]
    ux, uy, uz = b["usb_mm"]
    px, py, pz = b["parts_mm"]
    m = usb_mouth_x()
    spacer, (hx, hy, hz), exit = b["dupont"]["spacer_mm"], b["dupont"]["housing_mm"], b["dupont"]["exit_mm"]
    at = [pin_at(n) for n in plug_pins()]
    housings = [box((hx, hy, spacer), (x, y, bz + spacer / 2)) for x, y, _ in at]
    housings += [box((hx, hy, hz), (x, y, bz + spacer + hz / 2)) for x, y, _ in at]
    exits = [box((hx, hy, exit), (x, y, bz + spacer + hz + exit / 2)) for x, y, _ in at]
    return (pieces([box((bx, by, bz), (0, 0, bz / 2))], "red", "Pro Micro")
            + pieces([box((ux, uy, uz), (m + ux / 2, 0, bz + uz / 2))], "silver", "USB-C receptacle")
            + pieces([box((px, py, pz), (m + ux + px / 2, 0, bz + pz / 2))], "black", "Pro Micro parts")
            + pieces(housings, "black", "Dupont housings") + pieces(exits, "gray", "the wires' room over the housings"))


def usb_plug():
    b = mcu()
    pw, ph, pl = b["plug_mm"]
    return pieces([box((pl, pw, ph), (usb_mouth_x() - pl / 2, 0, b["board_mm"][2] + b["usb_mm"][2] / 2))], "silver", "USB-C plug")


def plug_way(mouth_x, face_x, section, centre_z, c):
    """The opening for a plug out through the wall: its section (a box's (w, h)
    or a cylinder's diameter) with clearance c, from the mouth out plug_way_mm,
    chamfered port_chamfer_mm at the wall's face, at face_x."""
    k, far = P.port_chamfer_mm, P.plug_way_mm
    if isinstance(section, tuple):
        w, h = section[0] + 2 * c, section[1] + 2 * c
        hole = box((far, w, h), (mouth_x - far / 2, 0, centre_z))
        flare = Manifold.hull_points([(face_x + k, sy * w / 2, centre_z + sz * h / 2) for sy in (-1, 1) for sz in (-1, 1)]
                                     + [(face_x - 0.01, sy * (w / 2 + k), centre_z + sz * (h / 2 + k)) for sy in (-1, 1) for sz in (-1, 1)])
    else:
        d = section + 2 * c
        hole = along_x(d, far, (mouth_x - far, 0, centre_z))
        flare = along_x(d + 2 * k, k + 0.01, (face_x - 0.01, 0, centre_z), d)
    return [hole, flare]


def pro_micro_room():
    """The board's room, which stays inside the walls: the board, and over each
    wired pin its header, Dupont housing and wire."""
    b = mcu()
    bx, by, bz = b["board_mm"]
    c = b["clearance_mm"]
    spacer, (hx, hy, hz), exit = b["dupont"]["spacer_mm"], b["dupont"]["housing_mm"], b["dupont"]["exit_mm"]
    tall = spacer + hz + exit
    headers = [box((hx + 2 * c, hy + 2 * c, tall + c), (x, y, bz + tall / 2)) for x, y, _ in map(pin_at, plug_pins())]
    return [box((bx + 2 * c, by + 2 * c, bz + 2 * c), (0, 0, bz / 2))] + headers


def usb_port(face_x):
    """The USB-C port through the wall, whose face is at face_x: the receptacle's grip and the plug's opening."""
    b = mcu()
    ux, uy, uz = b["usb_mm"]
    bz, g, m = b["board_mm"][2], P.port_grip_mm, usb_mouth_x()
    return ([box((ux + 2 * g, uy + 2 * g, uz + 2 * g), (m + ux / 2, 0, bz + uz / 2))]
            + plug_way(m, face_x, tuple(b["plug_mm"][:2]), bz + uz / 2, b["clearance_mm"]))


def mcu_cradle():
    """The board's cradle on the plinth (editor pro_micro.cradle): a rest down
    the board's middle, between the pin rows' solder, from the plinth's top to
    the board's underside, and guides round its far end, a wall thick, up to
    above_mm over the board."""
    b, cr = mcu(), mcu()["cradle"]
    bx, by, bz = b["board_mm"]
    c, w, g = b["clearance_mm"], cr["wall_mm"], cr["guide_in_mm"]
    floor = -b["standoff_mm"] - P.plate_gap_mm - 0.1
    top = bz + cr["above_mm"]
    x0, x1 = -bx / 2 + cr["pedestal_in_mm"][0], bx / 2 - cr["pedestal_in_mm"][1]
    rest = box((x1 - x0, cr["pedestal_width_mm"], -floor), ((x0 + x1) / 2, 0, floor / 2))
    sides = [box((g, w, top - floor), (bx / 2 + c - g / 2, sy * (by / 2 + c + w / 2), (top + floor) / 2)) for sy in (-1, 1)]
    end = box((w, by + 2 * c + 2 * w, top - floor), (bx / 2 + c + w / 2, 0, (top + floor) / 2))
    return [rest, *sides, end]


def jack():
    return P.capybara["trrs"]


def trrs_mouth_x():
    """The barrel's end, out of the body's -x end."""
    return -jack()["body_mm"][0] / 2 - jack()["barrel_mm"][0]


def trrs_jack():
    j = jack()
    jx, jy, jz = j["body_mm"]
    bl, bd = j["barrel_mm"]
    return (pieces([box((jx, jy, jz), (0, 0, jz / 2))], "black", "TRRS jack")
            + pieces([along_x(bd, bl, (trrs_mouth_x(), 0, jz / 2))], "silver", "TRRS barrel"))


def trrs_plug():
    jd, jl = jack()["plug_mm"]
    return pieces([along_x(jd, jl, (trrs_mouth_x() - jl, 0, jack()["body_mm"][2] / 2))], "silver", "TRRS plug")


def trrs_room():
    """The jack's body's room, which stays inside the walls."""
    j = jack()
    jx, jy, jz = j["body_mm"]
    c = j["clearance_mm"]
    return [box((jx + 2 * c, jy + 2 * c, jz + 2 * c), (0, 0, jz / 2))]


def trrs_port(face_x):
    """The TRRS port through the wall, whose face is at face_x: the barrel's grip and the plug's opening."""
    j = jack()
    jz, (bl, bd) = j["body_mm"][2], j["barrel_mm"]
    g, m = P.port_grip_mm, trrs_mouth_x()
    return [along_x(bd + 2 * g, bl + 0.1, (m - 0.05, 0, jz / 2))] + plug_way(m, face_x, j["plug_mm"][0], jz / 2, j["clearance_mm"])


def jack_cradle():
    """The jack's cradle on the plinth: a pedestal under its body from the
    plinth's top to its standoff, with walls (editor pro_micro.cradle.jack_walls)
    along its sides and across its back end up to its top."""
    j = jack()
    jx, jy, jz = j["body_mm"]
    c, w = j["clearance_mm"], mcu()["cradle"]["jack_walls"]
    floor = -j["standoff_mm"] - P.plate_gap_mm - 0.1
    outer = box((jx + 2 * c + w, jy + 2 * c + 2 * w, jz - floor), (w / 2, 0, (jz + floor) / 2))
    return [outer - box((jx + 2 * c, jy + 2 * c, jz + 1), (0, 0, jz / 2 + 0.5))]


# The reset switch's frame is the editor's: origin at the middle of its plunger
# face, x up, y across the wall, z back from the face into the case, so the
# plunger stands out along -z through the wall's skin.
def reset():
    return P.capybara["reset"]


def reset_switch():
    r = reset()
    rx, ry, rz = r["body_mm"]
    pd, pp = r["plunger_mm"]
    out = (r["leg_span_mm"] - ry) / 2
    legs = [box((0.8, out, 0.3), ((-1 if n % 2 else 1) * r["leg_pitch_mm"] / 2, (-1 if n <= 2 else 1) * (ry / 2 + out / 2), rz - 0.15))
            for n in (1, 2, 3, 4)]
    return (pieces([box((rx, ry, rz), (0, 0, rz / 2)), cylinder(pd, pp, (0, 0, -pp))], "black", "reset switch")
            + pieces(legs, "silver", "reset switch's legs"))


def reset_seam_x():
    """The seam in the switch's frame: its x (up) runs from the floor."""
    return -reset()["standoff_mm"] - reset()["body_mm"][0] / 2


def reset_room():
    """What the shell loses to the switch: a slot in the inside of the wall
    behind its skin, from the seam up past the body and as wide as its legs,
    open into the case; and the plunger's hole through the skin."""
    r = reset()
    rx, ry, rz = r["body_mm"]
    pd, pp = r["plunger_mm"]
    c, skin = r["clearance_mm"], P.reset_skin_mm
    x0, x1 = reset_seam_x() - 1, rx / 2 + c
    return [box((x1 - x0, r["leg_span_mm"] + 2 * c, 10), ((x0 + x1) / 2, 0, 5)),
            cylinder(pd + 2 * c, skin + 2, (0, 0, -skin - 1))]


def reset_stop():
    """The stop on the plinth behind the switch's body, in its slot, which
    takes the press, with the legs' wires either side of it."""
    r = reset()
    rx, ry, rz = r["body_mm"]
    w, deep = P.reset_stop_mm
    x0, x1 = reset_seam_x() - P.plate_gap_mm - 0.1, rx / 2
    z0 = rz + r["clearance_mm"]
    return [box((x1 - x0, w, deep), ((x0 + x1) / 2, 0, z0 + deep / 2))]

"""Every parameter of the low-profile Capybara, in millimetres and degrees.

The layout (layout.py) reads the hand from hand/left-hand.json; everything else
is here. Sizes marked PROVISIONAL are from datasheets or memory, not measured
parts. Override any of them from the command line: see build.py. PRESETS at
the end are named sets of overrides (build.py --preset).
"""
import json
from pathlib import Path

# The Capybara's editor project: the parts it shares with this one are read from it.
_capybara = json.loads((Path(__file__).resolve().parent.parent / "editor" / "src" / "default-config.json").read_text())

# ---------------------------------------------------------------- the design's choices
# Where the keys come from: "hand", laid out here from the fingertips' resting
# prints on flat paper (layout.py); or "swung_in", the Capybara's keys as its
# editor places them (its default project, read through
# editor/tests/key-frames.ts), its tent included, so tent_deg and pitch_deg
# and everything under "the key field" and "the thumb" below are the hand
# layout's alone.
key_layout = "hand"
# What sits under each switch: "sockets", a hotswap socket in a pocket with a
# DO-35 diode in the column channel; or "tiles", a bought RGB key tile (the
# socket, diode and LED on a small board, tile_* below) hanging from the
# switch in a shaft open to the underside, its LED's data and power wired
# down the columns as well (column_w_mm).
key_parts = "sockets"
# How the halves talk: "ble", an nRF52840 Pro Micro with a battery and a power
# switch in each half; or "trrs", an RP2040 Pro Micro on USB with a TRRS jack
# (trrs_* below) and a reset switch (reset_* below), no battery.
link = "ble"

# ---------------------------------------------------------------- the key field
# Tent: the whole hand turned about the Y axis, raising the thumb side. 0 is flat.
tent_deg = 6
# Pitch: the whole hand turned about the X axis, + raising the back (away from you).
pitch_deg = 0
# Key pitch along a column, between neighbouring caps at their skirts (where
# the column's curve brings them closest). The plate pitch comes out wider.
row_pitch_mm = 19.05
# Rows per column: home, and this many above (away from you) and below.
rows_above = 1
rows_below = 1
# Where the fingertip's reach between rows pivots: 0 at the PIP joint (tight
# well), 1 at the knuckle (MCP: wide, flat). Sets each column's arc radius from
# the measured joints; the home key always faces up, the others tilt to face
# a point that far above it.
reach_mix = 0.5
# Scale of the measured finger splay (the columns' angles in plan). 0 makes them parallel.
splay_scale = 1
# Extra fifth column inside the index column (reached by the index finger), its
# gap from the index column centre to centre and its angle to it.
inner_gap_mm = 19.9
inner_angle_deg = 0
# How far the columns' home row drops below the measured fingertip prints along
# the key normal (0: the cap tops sit where the fingertips rested).
finger_sink_mm = 0

# ---------------------------------------------------------------- the thumb
# The thumb keys lie on the circle the thumb's pad swept (the hand), at this
# pitch along it (at the caps' skirts, as row_pitch_mm). thumb_around_deg is the
# home key's place round that circle (the resting print is at 112 deg; swept in
# 92, swept out 140, pulled back 168); the far key is further round (swept
# out), the near key less (swept in).
thumb_pitch_mm = 19.05
thumb_around_deg = 112
# The thumb keys' cap tops this far below the finger home keys' (0: level, as
# the pads were on the paper).
thumb_drop_mm = 1
# How much the keys fan round the arc: 1 each key's y along its own radius,
# 0 every key headed like the home key (parallel, as Swung in has them).
# Fanned 1u Cherry caps need a pitch of about 23 mm not to meet at their
# inner corners; parallel ones fit at 19.05.
thumb_fan = 0
# Each thumb key tilted toward the cluster's middle, degrees per key step
# (a shallow well along the row), and the whole row tilted about its length,
# + facing the thumb's base.
thumb_well_deg = 6
thumb_tilt_deg = 0
# The home thumb key's cap, in key units (1 or 1.5; 1.5 lies along the row).
thumb_home_u = 1
# A second thumb row (x1, x2) toward the thumb's base: flat, on the circle
# inside the row's by thumb_row_gap_mm, a cell apart and centred on the home
# key's angle plus thumb_extra_around_deg, this much lower along their normals.
thumb_extra = True
thumb_row_gap_mm = 22
thumb_extra_around_deg = 0
thumb_extra_lower_mm = 0

# ---------------------------------------------------------------- the switch (MX)
# The hole, with its print clearance, the 1.5 mm plate the clips land on and
# the housing below the plate.
switch_cutout_mm = 14
switch_cutout_clearance_mm = 0.15
plate_mm = 1.5
switch_rim_mm = 15.6              # the housing flange over the plate, square
switch_below_plate_mm = 5         # lower housing, from the plate top to its bottom
switch_clip_width_mm = 5          # the two clips, centred on the +-y sides
switch_clip_relief_mm = 1.2       # how far past the hole each relief goes
switch_top_above_plate_mm = 6.6   # the housing's top over the plate
# Posts and pins below the housing, from the stem centre, +y the pin side (north).
switch_centre_post_d = 4
switch_side_post_d = 1.7
switch_side_post_x = 5.08
switch_pin_d = 1.5
switch_pins = [(2.54, 5.08), (-3.81, 2.54)]
post_clearance_mm = 0.3
# The layer a PCB would be (the pins pass through it into the socket).
pcb_layer_mm = 1.6

# ---------------------------------------------------------------- the keycap (Cherry profile)
# PROVISIONAL: Cherry profile, nominal. Base and top in plan, heights per row
# (R1 top to R4 bottom) at the cap's highest point, the skirt's bottom above
# the plate at rest, and the travel.
cap_base_mm = 18.2
cap_top_mm = (12.5, 14)
cap_height_mm = (9.3, 8.4, 7.6, 7.6)   # R1, R2, R3, R4
cap_row = (2, 3, 4)                    # the Cherry row of the top, home and bottom rows
cap_row_thumb = 3
cap_bottom_above_plate_mm = 6
cap_travel_mm = 4
cap_clearance_mm = 0.5                 # caps must stay this far apart
cap_unit_mm = 19.05                    # a 1.5u cap is 1.5 units less (unit - base)

# ---------------------------------------------------------------- the hotswap socket (Kailh MX)
# Measured on the key tiles (docs/design-status.md): body 11.6 x 6.2 x 1.9,
# centred 0.7 mm to -x and 4 mm to +y of the stem, seen from the switch side.
# Its two solder tabs stick out of the +-x ends, PROVISIONAL sizes.
socket_body_mm = (11.6, 6.2, 1.9)
socket_centre_mm = (-0.7, 4.0)
socket_tab_mm = (2.0, 2.6)             # each tab's reach past the body, and its width
socket_tab_y = (2.54, 5.08)            # the -x tab's y, the +x tab's y
socket_clearance_mm = 0.25
# Room under each tab to solder a wire to it, from the floor up to the tab,
# centred on the tab's tip and cut back to stay min_wall_mm inside the cell.
solder_well_mm = (4.5, 5)

# ---------------------------------------------------------------- the key tile (key_parts "tiles")
# The Capybara's measured tile, from the editor (default-config.json, tile):
# the board's side, the fit of its shaft round it, the parts under it as
# (name, size, centre) in the key frame from the board's top, and the holes
# the column (C) and row (R) wires are soldered into, (x, y) in the key frame
# (the north C, and the east and west R). Its socket is socket_body_mm at
# socket_centre_mm, the board's top switch_below_plate_mm under the plate's
# and its thickness pcb_layer_mm, as they are for "sockets".
_tile = _capybara["tile"]
tile_mm = _tile["size_mm"][0]
tile_clearance_mm = _tile["clearance_mm"]
tile_parts = [(p["name"], tuple(p["size_mm"]), tuple(p["center_mm"])) for p in _tile["components"]]
tile_c_hole = next(tuple(p["at_mm"]) for p in _tile["pads"]["list"] if p["name"] == "C" and p["at_mm"][1] > 0)
tile_r_hole = next(tuple(p["at_mm"]) for p in _tile["pads"]["list"] if p["name"] == "R" and p["at_mm"][0] > 0)
tile_r_west_hole = next(tuple(p["at_mm"]) for p in _tile["pads"]["list"] if p["name"] == "R" and p["at_mm"][0] < 0)

# ---------------------------------------------------------------- wiring
# Channels in the body's underside for the wires, closed by the bottom plate.
channel_w_mm = 2.2
# The column channels: with tiles they carry the LEDs' data and power along
# with the column wire, so they are as wide as the trunks.
column_w_mm = 2.2
# The thickest wire (the battery's leads): the wiring check counts only the
# passages it fits through.
wire_d_mm = 1.0
# The trunks (the inner column's channel, which the row wires join, and the
# one behind the top row that the columns' wires follow to the controller).
trunk_w_mm = 3.5
# How far past the end cells' edges the back and front trunks' centre lines run.
trunk_out_mm = 1.5
# The room the outline leaves round each channel, past its width.
channel_margin_mm = 1
# The per-key diode (DO-35, 1N4148), in the column channel: body length and diameter.
diode_mm = (4.0, 2.0)
# Each key's diode leg runs up its column in the channel past the -x tabs;
# each row's wire joins the +x tabs along the cells' north edges. See the README.

# ---------------------------------------------------------------- the body and bottom plate
# The thinnest wall between the rooms of different parts (each key's, the
# bay's), and between the bay and every channel but the one into it; the
# build checks every pair.
min_wall_mm = 1
wall_mm = 6                 # the body's wall past the key cells; the trunk channels and the screws' inserts sit in it
# The outline: "hulls" joins a convex hull round the finger field and one
# round the thumb cluster (straight sides); "closed" follows the cells.
outline_style = "hulls"
outline_round_mm = 6        # round of the outline's convex corners
outline_close_mm = 10       # gaps narrower than twice this are filled, with a round of this radius
cell_mm = 19.05             # the cell each key owns in plan, square
# The body's top edge is rounded (a rolling-ball fillet) to this radius; 0 leaves
# it sharp. It must leave room at the outline's convex corners: outline_round_mm
# less this, less this times the sine of the top's tilt there, has to stay positive.
top_round_mm = 4
# The body is a shell of one thickness: its underside is its top surface
# dropped by the room every key needs, the socket's bottom and this much
# under it (room for the wires under it and the print's tolerance), cut off
# plate_gap_mm over the plinth's floor. The bottom plate is a plinth, flat on
# the desk, its top the same surface plate_gap_mm lower; it is at least
# bottom_plate_mm thick.
under_socket_mm = 0.6
bottom_plate_mm = 2
plate_gap_mm = 0.1
# Bosses on the bottom plate hold each socket up against its pocket's ceiling.
boss_clearance_mm = 0.15
boss_inset_mm = 0.6         # the boss is this much smaller than the socket body all round
# M2 screws from below into heat-set inserts in the body's wall: insert hole
# and depth, the screw's clearance hole through the plate, the head's
# diameter and the clearance round it (its counterbore), and how much plate
# every screw grips under the body (the counterbore goes up to it, so one
# screw length fits everywhere: screw_grip_mm + insert_depth_mm). Each screw
# sits in the middle of the wall, wall_mm / 2 past the cell's or bay's edge,
# so the counterbore leaves (wall_mm - screw_head_d - screw_head_clearance_mm) / 2
# of wall on each side; the build checks the holes against everything else.
insert_d = 3.2
insert_depth_mm = 4
screw_d = 2.4
screw_head_d = 4.2
screw_head_clearance_mm = 0.6
screw_grip_mm = 3
# Which edges carry screws: see screw_points() in layout.py.

# ---------------------------------------------------------------- controller, battery, switch
# PROVISIONAL: a Pro Micro form factor nRF52840 (nice!nano v2 / SuperMini):
# board, the parts' height over it (the USB-C port is the tallest), how far
# the port stands past the board's end, the port's opening in the wall.
mcu_board_mm = (18, 33.5, 1.0)
mcu_parts_mm = 3.3
mcu_usb_mm = (9.0, 3.3)         # the port's width and height
mcu_usb_overhang_mm = 1.3
mcu_usb_opening_mm = (10.5, 5)  # the hole through the back wall for the plug
mcu_clearance_mm = 0.3
mcu_plug_mm = (12.5, 7)         # the USB-C plug's housing: width, height
plug_desk_mm = 1                # how far over the desk a plug's housing stays
# The board lies in a well in the bottom plate on the inner side of the inner
# column (layout.py mcu_bay), along the column, its USB-C port out of the
# back wall; the well's floor is as low as the plinth's thinnest
# (bottom_plate_mm), unless a plug's housing would then come within
# plug_desk_mm of the desk.
# mcu_turn_deg turns it in plan about its port end.
mcu_turn_deg = 0
# The reset button on the board, from the port end: across (x) and along (y) the board.
mcu_reset_mm = (0, 14.5)
# Battery: PROVISIONAL 402030 LiPo (about 200 mAh), lying flat in the bay in
# front of the board, its 30 mm along the column.
battery_mm = (30, 20, 4.2)
battery_clearance_mm = 0.5
# The notch in the wall between the battery's bay and the controller's, at the
# middle of the battery's back end, for its leads.
battery_lead_notch_mm = 4
# Power switch: PROVISIONAL MSK-12C02 slide switch, body and its knob's reach.
power_switch = True
power_switch_mm = (8.6, 3.7, 3.5)
power_switch_knob_mm = (1.5, 3.0, 1.5)  # width, travel + width, how far it stands out
power_switch_back_mm = 8                # along the inner side wall, from the bay's back
# Where the controller's bay is (layout.py mcu_bay): "beside" the inner
# column, or "under" the inner and index columns' top keys, for a plinth tall
# enough to hold it there.
bay_place = "beside"
# An AS5600 magnetic knob on the inner side wall, in front of the bay, its
# axis square to the wall (parts.py knob), its bearing in a boss out of the
# wall (knob_boss_wall_mm round the bearing's pocket) so the magnet and
# sensor fit in the wall. The knob, knob_d_mm across, is a cup over the boss
# and stands knob_above_mm over the case's top there, which sets the axis's
# height (chassis.py knob_frame), so a finger reaching over the edge turns
# it by its top. PROVISIONAL sizes, from the parts in hand. Knob: its face's
# thickness in front of the boss, its gap to the boss and the wall (and the
# room behind the bearing for its inner race). Bearing (608 2RS): bore,
# outside diameter, width; its pocket is drawn at its size, a press fit.
# Magnet: diameter, length, and its gap to the chip. Sensor board, from its
# drawing: wide, high, thick (board and chip), the board alone; its rounded
# end (its three pads', down) is cut on a circle knob_sensor_r_mm round the
# chip; two holes, knob_sensor_holes_mm (pitch, diameter), either side of
# the chip on its line. Two pegs, knob_peg_d_mm across, stand on the body's
# side of the board's slot, toward the board: with the plinth off, the board
# drops into the slot behind their tips and slides onto them, and a tongue
# on the plinth fills the room behind it when the two are screwed together.
# So the body, which holds the bearing, holds the chip on the axis. The
# chip: the AS5600's SOIC-8 body, wide and high.
knob = False
knob_d_mm = 36
knob_above_mm = 5
knob_mm = (3, 0.5)
knob_boss_wall_mm = 1.5
knob_bearing_mm = (8, 22, 7)
knob_magnet_mm = (5, 2, 1)
knob_sensor_mm = (15, 17, 2.6, 1)
knob_sensor_r_mm = 9
knob_sensor_holes_mm = (12, 2.2)
knob_peg_d_mm = 2
knob_chip_mm = (4.9, 3.9)
knob_clearance_mm = 0.2
# link "trrs": the Capybara's TRRS jack and reset switch, their sizes the
# editor's (editor/src/default-config.json, trrs and reset). The jack lies
# beside the board, lugs up, its barrel out of the back wall: body (along the
# barrel, across, high), barrel (length, diameter), the plug's diameter, and
# the fit. The reset switch stands on edge in the inner side wall in front of
# the jack, its plunger out through the wall: body (high, along the wall,
# deep), plunger (diameter, how far it stands proud), the legs' span along
# the wall, and the fit.
trrs_body_mm = tuple(_capybara["trrs"]["body_mm"])
trrs_barrel_mm = tuple(_capybara["trrs"]["barrel_mm"])
trrs_plug_d = _capybara["trrs"]["plug_mm"][0]
trrs_clearance_mm = _capybara["trrs"]["clearance_mm"]
reset_body_mm = tuple(_capybara["reset"]["body_mm"])
reset_plunger_mm = tuple(_capybara["reset"]["plunger_mm"])
reset_leg_span_mm = _capybara["reset"]["leg_span_mm"]
reset_clearance_mm = _capybara["reset"]["clearance_mm"]
reset_skin_mm = 0.6       # the wall left over the switch's plunger face, which the plunger stands through

# ---------------------------------------------------------------- modelling
# The top surface is a smooth (quadratic) spline through the key field sampled
# at this step. Between cells the field blends the cells' planes, from this
# far inside each cell's edge (chassis.py field).
surface_step_mm = 2
surface_blend_mm = 3
# Each cell's plane is put back exactly this far past its edge (chassis.py plane_groups).
cell_step_mm = 0.6
# The meshes: the top surface, the underside and the plinth's top are
# triangles about this big, with the outline's stations no further apart;
# every curve (the outline's arcs, the top edge's round, the cylinders) is
# chords no further than mesh_tol_mm from it.
mesh_mm = 1
mesh_tol_mm = 0.01

# ---------------------------------------------------------------- presets
# Named sets of overrides (build.py and render.py --preset), each built from
# where its values live.
_switch, _pro_micro = _capybara["switch"], _capybara["pro_micro"]
PRESETS = {
    # The Capybara's choices on this chassis: Swung in's keys and tent, the
    # key tiles with their LEDs, the Capybara's keycaps (one profile for every
    # row), an RP2040 Pro Micro with its TRRS jack and reset switch, no battery.
    "capybara": {
        "key_layout": "swung_in",
        "key_parts": "tiles",
        "link": "trrs",
        "bay_place": "under",
        "cap_base_mm": _switch["keycap_mm"][0],
        "cap_top_mm": tuple(_switch["keycap_top_mm"]),
        "cap_height_mm": (_switch["keycap_mm"][2],) * 4,
        "cap_bottom_above_plate_mm": _switch["keycap_bottom_above_plate_mm"],
        "cap_travel_mm": _switch["travel_mm"],
        "cap_clearance_mm": _switch["keycap_clearance_mm"],
        "mcu_board_mm": (_pro_micro["board_mm"][1], _pro_micro["board_mm"][0], _pro_micro["board_mm"][2]),
        "mcu_usb_mm": (_pro_micro["usb_mm"][1], _pro_micro["usb_mm"][2]),
        "mcu_parts_mm": _pro_micro["usb_mm"][2],
        "mcu_usb_overhang_mm": _pro_micro["usb_overhang_mm"],
        "mcu_plug_mm": tuple(_pro_micro["plug_mm"][:2]),
        "wire_d_mm": _capybara["wiring"]["power_wire_mm"],
        # Room under the tiles for the wires off their holes and the rails' stubs.
        "under_socket_mm": 1.5,
        "column_w_mm": 5,
        "trunk_w_mm": 5,
        # Swung in's steep thumbs and pinky top key curve the top too tightly
        # at the outline for a 2 mm round.
        "top_round_mm": 1.5,
    },
}

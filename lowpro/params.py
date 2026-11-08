"""Every parameter of the low-profile Capybara, in millimetres and degrees.

The layout (layout.py) reads the hand from hand/left-hand.json; everything else
is here. Sizes marked PROVISIONAL are from datasheets or memory, not measured
parts. Override any of them from the command line: see build.py. PRESETS at
the end are named sets of overrides (build.py --preset).
"""
import json
from pathlib import Path

# The Capybara's editor project: the parts this design shares with it are read
# from there, so each size lives in one place.
_capybara = json.loads((Path(__file__).resolve().parent.parent / "editor" / "src" / "default-config.json").read_text())

# ---------------------------------------------------------------- the design
# "lowpro": the keys laid out here from the measured hand (the key field and the
# thumb below), hotswap sockets in pockets in a solid body with wire channels,
# and the nRF52840 board, battery and power switch in a well beside the keys
# (chassis.py). "capybara": the Capybara's keys as its editor places them, its
# RGB key tiles hanging from the switches in an open shell for loose hand
# wiring, and its Pro Micro, TRRS jack and reset switch where the editor puts
# them (layout.py swung_in, shell.py). The parameters below hold for both,
# except those the editor's project fixes (the tent, the lift, the parts).
design = "lowpro"

# Which half is being built. The left half is the right's mirror image, but a
# switch and its socket are the same parts in both, and they can't be mirrored:
# on the left they're drawn the other way round here, so that the mirror puts
# them right (parts.py handed). build.py sets this for each half.
half = "right"

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
# The near and far thumb keys lie on the circle the thumb's pad swept (the hand),
# the home key on the line between them, at this pitch along it (at the caps'
# skirts, as row_pitch_mm). thumb_around_deg is the home key's angle round that circle (the resting print is at 112 deg; swept in
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
# The row is then turned counterclockwise in plan about the near key's centre,
# and leaned about the near key's y through its centre, the far key going down.
thumb_turn_deg = 20
thumb_lean_deg = 10
# The home thumb key's cap, in key units (1 or 1.5; 1.5 lies along the row).
thumb_home_u = 1
# The extra pair (x1, x2): a fourth row under the middle and ring columns, flat
# and a cell apart, past the south edge of the column's bottom key by the gap,
# which keeps min_wall_mm from the front trunk to their sockets, x1 this far
# toward the thumb, and this much lower.
thumb_extra = True
thumb_extra_gap_mm = 4.2
thumb_extra_left_mm = 3
thumb_extra_lower_mm = 0

# ---------------------------------------------------------------- the switch (MX)
# The hole, with its print clearance, the 1.5 mm plate the clips land on and
# the housing below the plate.
switch_cutout_mm = 14
switch_cutout_clearance_mm = 0.15
switch_land_mm = 1                # the plate's flat past the cutout, for the switch's 0.8 mm lip to sit on
switch_taper_mm = 1               # past that, the taper to the top surface
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
switch_post_mm = 3.3              # how far the posts and pins reach below the housing
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
# Kailh's drawing: body 10.9 x 5.89 x 1.8, centred on the midpoint of the two
# pins, seen from the switch side. The body is that rectangle less the corner
# by the stem: it steps round the centre post, so the +x end is one lobe wide
# and the part towards -x runs its whole width. 3.05 thick over the collars, the
# two barrels round the pin cups that a PCB's holes take.
socket_body_mm = (10.9, 5.89, 1.8)
socket_centre_mm = (-0.635, 3.81)
socket_lobe_mm = (5.8, 4.0)            # the front lobe's length from the -x end, each lobe's width
socket_collar_mm = (2.9, 1.25)         # diameter, height over the body
# Its two terminals stick out of the +-x ends, 14.5 tip to tip: stubs about
# square in section, as tall as the body and 0.05 proud of its top, to reach a PCB.
socket_tab_mm = (1.8, 1.68, 1.85)      # each terminal's reach past the body, width, height
socket_tab_y = (2.54, 5.08)            # the -x tab's y, the +x tab's y
socket_clearance_mm = 0.25
# Room round each terminal to solder a wire to it, from the floor up to the
# socket's top, reaching solder_well_reach_mm past the tip (a wire's room and a
# little) and cut back to stay solder_well_inset_mm inside the cell: min_wall_mm
# and the little that a column channel stands past the next cell's edge.
solder_well_mm = (4.5, 5)
solder_well_reach_mm = 1.75
solder_well_inset_mm = 1.2

# ---------------------------------------------------------------- wiring
# Channels in the body's underside for the wires, sunk into the bottom plate.
channel_w_mm = 2.2
# The thickest wire (the keys' hookup wire): the wiring check counts only the
# passages it fits through.
wire_d_mm = 1.6
# A column channel reaches past each -x terminal's tip by a wire and this much.
wire_gap_mm = 0.2
# The trunks (the inner column's channel up to the home key, which the lower
# rows' wires share to the well, and the one behind the top row that the other
# columns' wires and the top row's follow to the controller).
trunk_w_mm = 3.5
# How far the channels and the trunks go on down into the plinth, each leaving
# it at least bottom_plate_mm: a row wire crosses a column wire, and a trunk
# holds its bundle two wires wide.
channel_sink_mm = 1
trunk_sink_mm = 5.5
# The per-key diode (DO-35, 1N4148): body length and diameter.
diode_mm = (4.0, 2.0)
diode_room_mm = 0.4         # the diode's room round it
# Each key's diode has its own pocket across the key, south of the centre post,
# with a slot for each leg, so no wire runs past it. On a finger key its +x leg
# goes round the side post's hole to the +x tab and its -x leg out to the column
# wire, which runs beside the tabs' tips; each row's wire goes straight along a
# cell's north edge into the next column and down it to that key's -x tab. A thumb
# key's is the other way round: its -x leg goes to the -x tab and its +x leg out to
# the column wire, which runs past the +x tab's tip.
diode_leg_d_mm = 0.5
diode_leg_slot_mm = 1.0
# The wall between a bottom-row diode's pocket and the front trunk, in the key's
# frame at the socket's top: the end rows lean, so the pocket comes closer below,
# on its way down to the seam, and this leaves min_wall_mm at the seam.
front_trunk_wall_mm = 3.9

# ---------------------------------------------------------------- the body and bottom plate
# The thinnest wall between the rooms of different parts (each key's, the
# bay's), and between the bay and every channel but those into it; the
# build checks every pair.
min_wall_mm = 1
wall_mm = 3                 # the body's wall past the key cells and the bays
# The well's wall on the keys' side, in plan at the seam, which has three slots
# through it. The well leans with the seam, so the wall thins as it climbs, and
# this leaves min_wall_mm to the back trunk at the top.
mcu_bay_wall_mm = 1.6
# The outline: "hulls" joins a convex hull round the finger field and one
# round the thumb cluster (straight sides); "closed" follows the cells.
outline_style = "closed"
outline_round_mm = 3        # round of the outline's convex corners
outline_close_mm = 6        # gaps narrower than twice this are filled, with a round of this radius
ring_corner_round_mm = 4    # the corner at the ring column's foot: the one arc that takes in both the cell's round and the trunk's end
cell_mm = 19.05             # the cell each key owns in plan, square
# The body's top edge is rounded (a rolling-ball fillet) to this radius; 0 leaves
# it sharp. It must leave room at the outline's convex corners: outline_round_mm
# less this, less this times the sine of the top's tilt there, has to stay positive.
top_round_mm = 1.5
# The seam between the body and the plinth is one plane, so the body prints flat
# on it: tilted seam_tent_deg up toward the thumb (tent_deg is parallel to the home
# plates, and flatter lets the thumb row lean further for the same case height),
# and under what hangs from every key, in either half: the sockets and their
# terminals by under_socket_mm, for the print's tolerance and the boss, and the
# diodes' glass by under_diode_mm. It has bottom_plate_mm of plinth at its lowest,
# and plate_gap_mm between the parts.
seam_tent_deg = 1.6
under_socket_mm = 0.3
under_diode_mm = 0.1
bottom_plate_mm = 1.75
plate_gap_mm = 0.1
# The plinth's skirt, past the outline in its concave stretches: the radius of
# the arcs that bridge them, its height over the desk, and the cove where it
# meets the plinth's wall (less than outline_close_mm - wall_mm - 0.5).
skirt_radius_mm = 25
skirt_h_mm = 2
skirt_cove_mm = 2
# Bosses on the bottom plate hold each socket up against its pocket's ceiling.
boss_clearance_mm = 0.15
boss_inset_mm = 0.6         # the boss is this much smaller than the socket body all round
# M2 socket-head screws from below into M2 heat-set inserts in the body, inside
# the key field: the insert's length, its hole and the hole's depth (the depth
# leaves the PCB layer over the hole), the screw's length and its clearance hole
# through the plate, the head's diameter, height and the clearance round it (its
# counterbore), and how much plate every screw grips under the body (the
# counterbore goes up to it, so one screw length fits everywhere). The screws are
# what locate the plinth under the body. Where they stand: screw_points() in layout.py.
insert_len_mm = 3
insert_d = 3.2
insert_depth_mm = 3.5
screw_len_mm = 4
screw_d = 2.4
screw_head_d = 3.8
screw_head_h_mm = 1.2
screw_head_clearance_mm = 0.4
screw_grip_mm = 1.2

# ---------------------------------------------------------------- controller, battery, switch
# The Tenstar red ProMicro NRF52840, its size PROVISIONAL until measured:
# board, the parts' height over it (the USB-C port is the tallest), how far
# the port stands past the board's end.
mcu_board_mm = (18, 33.5, 1.0)
mcu_parts_mm = 3.3
mcu_usb_mm = (9.0, 3.3)         # the port's width and height
mcu_usb_overhang_mm = 1.3
# The hole through the back wall for the plug and its moulding: this size at the
# port's end, flaring out to the wall's face.
mcu_usb_relief_mm = (13, 7)
mcu_usb_recess_mm = 1.25        # how far the port's end sits back from the wall's face: the flare's depth
mcu_clearance_mm = 0.3
# The board lies in a well on the inner side of the inner column (layout.py
# mcu_bay), along the column, its USB-C port out of the back wall. The well's
# walls and ceiling are the body's and its floor is the plinth's top, on the
# seam, so all the electronics are in the body and the plinth comes away free of
# them. Its ceiling follows the top surface this far under it.
well_roof_mm = 2
# The board and its port are level on the desk, the port's middle on the seam, so
# the seam crosses the hole at seam_tent_deg. Under the board and the battery the
# plinth has a pocket this far under the seam. The port stands on a rest as wide
# as it is, down the board's middle, which leaves the pin rows' solder a gutter
# either side: how far the rest runs from the port's end, stopping short of the
# board's south end so the battery's leads can turn into a gutter.
bay_pocket_mm = 2
mcu_rest_mm = 28
# A strip stands down from the ceiling along the middle of the board, clear of the
# wires, and foam on it holds the board down: wide, long, how far from the port
# end it starts, and the gap the foam takes up.
mcu_press_mm = (6, 18)
mcu_press_start_mm = 6
mcu_press_gap_mm = 0.7
# mcu_turn_deg turns it in plan about its port end.
mcu_turn_deg = 0
# Battery: PROVISIONAL 402030 LiPo (about 200 mAh), lying flat in the bay in
# front of the board, its 30 mm along the column.
battery_mm = (30, 20, 4.2)
battery_clearance_mm = 0.5
# The notch in the wall between the battery's bay and the controller's, at the
# middle of the battery's back end, for its leads.
battery_lead_notch_mm = 4
# Power switch: PROVISIONAL MSK-12C02 slide switch, its body and handle as the
# distributors list them; the rest is unmeasured until it is checked on a real part.
# It sits on the well's floor beside the board (layout.py power_switch_frame).
power_switch = True
power_switch_mm = (8.0, 2.8, 1.4)
power_switch_knob_mm = (1.0, 3.0, 1.6)  # width, travel + width, how far it stands out of the switch
power_switch_proud_mm = 1.0             # how far its tip stands past the wall's outside, to reach it; the wall outside the pocket goes under min_wall_mm for this
power_switch_pins_mm = (5.5, 3.0)       # the notch behind it, into the well: wide, deep
power_switch_clearance_mm = 0.2
# Reset button: the board has none, so the main build's PROVISIONAL SMD tactile
# switch (docs/pro-micro.md) is wired to RST and GND. It stands on edge north of
# the power switch, its plunger out through the inner side wall, on the seam
# between the plinth and the body (layout.py and chassis.py reset_button_frame).
reset_button_mm = (6.5, 2.0, 6.5)   # across, thick, tall
reset_plunger_mm = (3.25, 1.0)      # diameter, how far it stands out of the body
reset_leg_mm = (8.7, 4.4, 0.8, 0.3) # span, pitch, width, thick
reset_stop_mm = (4.5, 4.0)          # the stop behind it, with the wires either side: wide, deep to the well
reset_chamfer_mm = 0.8              # the hole's chamfer at the wall's face
reset_button_clearance_mm = 0.2
reset_button_gap_mm = 3             # from the power switch's north end

# ---------------------------------------------------------------- the open shell (design "capybara")
# The Capybara's parts are its editor project's (default-config.json), read
# here as it has them so each size lives in one place: the key tile, the Pro
# Micro with its Dupont housings, the TRRS jack and the reset switch, and the
# project's switch, cap and wiring sizes. parts.py draws them from this.
capybara = _capybara
# The shell's top between the keys, measured straight down, and the plate at each key:
# the Capybara's plate thickness. The body's walls are wall_mm.
top_skin_mm = _capybara["chassis"]["plate_thickness_mm"]
# Under each plate the body fills down round the switch body over the tile's
# footprint, stopping this far over the tile's top for solder proud of its
# holes (the editor's sleeve, docs/editor-chassis.md).
sleeve_gap_mm = 0.4
# Under the sleeve each tile hangs in a pocket: walls this thick round the
# tile's clearance, from the plate down to the board's underside and no
# further, so the wires that leave under the board's edges pass beneath the
# rim (docs/editor-chassis.md, Paths). A round peg stands down from the sleeve
# into each corner notch, the notch's radius less this fit (the solder jig's,
# editor/src/jig.ts JIG.fit), webbed out to the pocket's corner, which the
# tile's cut-away corner leaves free.
pocket_wall_mm = 1.2
peg_fit_mm = 0.15
# A tile goes into its pocket square to its plate for its own hang and this much
# more, then straight down to the open underside: the way the build keeps clear.
tile_lead_mm = 0.5
# Each screw's insert sits in a boss in the wall, this wide and
# screw_boss_h_mm tall from its seat. The seat is the plinth's top or, where
# the plinth is thinner than a screw's head and screw_grip_mm, a round pad on
# the plinth up to that, min_wall_mm wide round the head's counterbore, which
# goes up into a recess in the body's underside plate_gap_mm wider (shell.py
# screw_seat_z, seat_pads). The screws stand at the outline's corners that
# turn screw_corner_deg or more, sharpest first, none within screw_apart_mm
# of another along the outline, with the runs between split so none is over
# screw_gap_mm: the fewest that hold the plinth at its corners. The tiles'
# ways in fill the plan to the wall, so no boss fits inside the outline: each
# is pushed out through the wall, where the wall lugs out round it (the lug's
# radius leaves min_wall_mm outside the recess), until it's screw_clearance_mm
# clear of every tile's way in and part's room; a spot slides along the
# outline, screw_slide_mm at a time, when that needs less push (shell.py
# screw_spots).
screw_boss_mm = 6
screw_boss_h_mm = 4.5
screw_corner_deg = 60
screw_apart_mm = 40
screw_gap_mm = 120
screw_clearance_mm = 0.5
screw_slide_mm = 0.5
# The ports: the wall grips the USB-C receptacle and the jack's barrel with
# this fit, each plug's opening is chamfered this much at the wall's face and
# reaches this far out past it, and the reset switch sits behind a skin of the
# wall this thick (docs/pro-micro.md). Each part sits where the editor puts it,
# slid along its port's axis until its mouth is on the wall's face.
port_grip_mm = 0.15
port_chamfer_mm = 1
plug_way_mm = 40
reset_skin_mm = 0.5

# ---------------------------------------------------------------- modelling
# The top surface is a smooth (quadratic) spline through the key field sampled
# at this step. Between cells the field blends the cells' planes, from this
# far inside each cell's edge (chassis.py field).
surface_step_mm = 2
surface_blend_mm = 3
# The meshes: the top surface, the underside and the plinth's top are
# triangles about this big, with the outline's stations no further apart;
# every curve (the outline's arcs, the top edge's round, the cylinders) is
# chords no further than mesh_tol_mm from it.
mesh_mm = 1
mesh_tol_mm = 0.01


# ---------------------------------------------------------------- presets
# Named sets of overrides (build.py and render.py --preset).
_switch = _capybara["switch"]
PRESETS = {
    # The capybara design with the Capybara's keycaps (one profile, every row)
    # and its switches' sizes. The plinth is a flat plate on the desk, as thick
    # as the editor's base plate; a screw's head and screw_grip_mm don't fit in
    # it, so each screw has a seat on it (screw_boss_mm). The screws stay M2 x 4
    # in 3 mm inserts: a 4 mm insert's hole would come within min_wall_mm of
    # the top over the thumb's outer corner, where the body is 8.3 mm tall.
    "capybara": {
        "design": "capybara",
        "cap_base_mm": _switch["keycap_mm"][0],
        "cap_top_mm": tuple(_switch["keycap_top_mm"]),
        "cap_height_mm": (_switch["keycap_mm"][2],) * 4,
        "cap_bottom_above_plate_mm": _switch["keycap_bottom_above_plate_mm"],
        "cap_travel_mm": _switch["travel_mm"],
        "cap_clearance_mm": _switch["keycap_clearance_mm"],
        "switch_cutout_clearance_mm": _switch["cutout_clearance_mm"] / 2,   # the editor's is the whole hole's
        "switch_rim_mm": _switch["seat_outer_mm"][0],
        "switch_below_plate_mm": _switch["body_below_plate_mm"],
        "bottom_plate_mm": _capybara["chassis"]["skin_mm"],
        # The top falls 45 degrees off the far thumb key's low corner to the
        # next key: a 1.5 mm ball can't roll round the edge there.
        "top_round_mm": 1,
    },
}

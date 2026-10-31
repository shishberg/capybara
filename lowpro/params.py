"""Every parameter of the low-profile Capybara, in millimetres and degrees.

The layout (layout.py) reads the hand from hand/left-hand.json; everything else
is here. Sizes marked PROVISIONAL are from datasheets or memory, not measured
parts. Override any of them from the command line: see build.py.
"""

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
# Room under each tab to solder a wire to it, from the floor up to the tab.
solder_well_mm = (4.5, 5)

# ---------------------------------------------------------------- wiring
# Channels in the body's underside for the wires, closed by the bottom plate.
channel_w_mm = 2.2
# The trunks (the inner column's channel, which the row wires join, and the
# one behind the top row that the columns' wires follow to the controller).
trunk_w_mm = 3.5
# The per-key diode (DO-35, 1N4148), in the column channel: body length and diameter.
diode_mm = (4.0, 2.0)
# Each key's diode leg runs up its column in the channel past the -x tabs;
# each row's wire joins the +x tabs along the cells' north edges. See the README.

# ---------------------------------------------------------------- the body and bottom plate
wall_mm = 6                 # the body's wall past the key cells; the trunk channels and the screws' inserts sit in it
# The outline: "hulls" joins a convex hull round the finger field and one
# round the thumb cluster (straight sides); "closed" follows the cells.
outline_style = "hulls"
outline_round_mm = 6        # round of the outline's convex corners
outline_close_mm = 10       # gaps narrower than twice this are filled, with a round of this radius
cell_mm = 19.05             # the cell each key owns in plan, square
# The body's top edge is rounded (filleted) to this radius; 0 leaves it sharp.
top_round_mm = 4
# The body is a shell of one thickness: its underside is its top surface
# dropped by the room every key needs, the socket's bottom and this much
# under it (room for the wires under it and the print's tolerance). The
# bottom plate is a plinth, flat on the desk, its top the same surface
# plate_gap_mm lower; it is at least bottom_plate_mm thick.
under_socket_mm = 0.6
bottom_plate_mm = 2
plate_gap_mm = 0.1
# Bosses on the bottom plate hold each socket up against its pocket's ceiling.
boss_clearance_mm = 0.15
boss_inset_mm = 0.6         # the boss is this much smaller than the socket body all round
# M2 screws from below into heat-set inserts in the body's wall: insert hole
# and depth, the screw's clearance hole through the plate, the head's
# diameter (its counterbore is 0.6 wider), how much plate every screw grips
# under the body (the counterbore goes up to it, so one screw length fits
# everywhere: screw_grip_mm + insert_depth_mm), and how far past a cell's or
# bay's edge each insert's centre sits.
insert_d = 3.2
insert_depth_mm = 4
screw_d = 2.4
screw_head_d = 4.2
screw_grip_mm = 3
screw_out_mm = 2.2
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
bay_under_mm = 1
# The board lies in a well in the bottom plate on the inner side of the inner
# column (layout.py mcu_bay), along the column, its USB-C port out of the
# back wall; the well's floor sits bay_under_mm below the parts' room under
# the body (so the port's opening stays in the plate's wall).
# mcu_turn_deg turns it in plan about its port end.
mcu_turn_deg = 0
# The reset button on the board, from the port end: across (x) and along (y) the board.
mcu_reset_mm = (0, 14.5)
# Battery: PROVISIONAL 402030 LiPo (about 200 mAh), lying flat in the bay in
# front of the board, its 30 mm along the column.
battery_mm = (30, 20, 4.2)
battery_clearance_mm = 0.5
# Power switch: PROVISIONAL MSK-12C02 slide switch, body and its knob's reach.
power_switch = True
power_switch_mm = (8.6, 3.7, 3.5)
power_switch_knob_mm = (1.5, 3.0, 1.5)  # width, travel + width, how far it stands out
power_switch_back_mm = 8                # along the inner side wall, from the bay's back

# ---------------------------------------------------------------- modelling
# The top surface is fitted through the key field sampled at this step, to
# this tolerance. Between cells the field blends the cells' planes, from this
# far inside each cell's edge (chassis.py field). The footprint's outline is
# smoothed into one spline through points this far apart. The top edge's
# fillet is particular about both: it fails with a looser fit (0.05) or a
# coarser outline (2 mm).
surface_step_mm = 2
surface_fit_mm = 0.01
surface_blend_mm = 3
outline_sample_mm = 1
# Each cell's plane is cut clear this far past its edge (chassis.py body_blank).
cell_step_mm = 0.6

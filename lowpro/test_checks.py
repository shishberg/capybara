"""The wiring checks have to fail when a channel is blocked: a check that can't
fail looks the same as a clear board. From the repository root:

    .venv/bin/python -m unittest lowpro.test_checks
"""
import unittest
from unittest import mock

import numpy as np

from . import chassis as C
from . import layout as L
from . import params as P
from . import parts as R
from . import wires as W
from .build import mesh_of, set_params
from .lib import origin, xform


def key_plane_meet(k, p, q):
    """The old column_meet: on k's plane carried on past the key, which falls
    away from the column's channel and took row channels out of the underside."""
    c, d = C.at(k, (C.col_x(), 0)), C.at(k, (C.col_x(), 1))
    t = np.linalg.solve(np.c_[(q - p)[:2], (c - d)[:2]], (c - p)[:2])[1]
    return C.at(k, (C.col_x(), t))


class PinchedRuns(unittest.TestCase):
    def setUp(self):
        self.addCleanup(L.reset)
        self.addCleanup(setattr, P, "half", P.half)
        L.reset()

    def test_every_run_is_clear_on_both_halves(self):
        for half in ("right", "left"):
            P.half = half
            L.reset()
            with self.subTest(half=half):
                self.assertEqual(C.pinched_runs(), [])

    def test_a_channel_leaving_the_underside_is_caught(self):
        with mock.patch.object(C, "column_meet", key_plane_meet):
            L.reset()
            self.assertTrue(C.pinched_runs())

    def test_a_plug_in_a_channel_is_caught(self):
        """A block of plinth across one row channel: every other way round is
        still open, so only this check sees it."""
        a, b, w = next((a, b, w) for a, b, w in C.channel_segments() if w == P.channel_w_mm and a[1] > -30)
        mid = (a + b) / 2
        plug = R.box((3, 3, 40), (mid[0], mid[1], mid[2] - 20))
        plinth = C.bottom_plate()
        with mock.patch.object(C, "bottom_plate", lambda: C.add(plinth, [plug])):
            self.assertEqual(C.unwired(), [])
            self.assertIn(f"the channel ({a[0]:.1f}, {a[1]:.1f}) to ({b[0]:.1f}, {b[1]:.1f})",
                          [name for name, _, _ in C.pinched_runs()])


class Wires(unittest.TestCase):
    def setUp(self):
        self.addCleanup(L.reset)
        self.addCleanup(setattr, P, "half", P.half)

    def test_every_matrix_wire_has_a_way_clear_of_the_case_and_parts_on_both_halves(self):
        for half in ("right", "left"):
            P.half = half
            L.reset()
            with self.subTest(half=half):
                self.assertEqual(W.unrouted(), [])
                solid = W.solids()
                for w in W.wires():
                    self.assertLess((W.tube(w.points) ^ solid).volume(), 0.5, msg=f"{w.net} {w.ends}")


class Wells(unittest.TestCase):
    def setUp(self):
        self.addCleanup(L.reset)
        for name in P.PRESETS["wells"]:
            self.addCleanup(setattr, P, name, getattr(P, name))
        set_params([], "wells")
        L.reset()

    def test_a_key_on_the_edge_has_its_wells_wall_outside_it(self):
        """The top stands at the key's top plane, well_depth_mm over its plate,
        over the wall on the side that faces no other key."""
        edge = [(f"pinky_{r}", (1, 0)) for r in (-1, 0, 1)] + [(f"{c}_1", (0, 1)) for c in ("inner", "index", "middle", "ring", "pinky")]
        for name, (sx, sy) in edge:
            k = L.key_named(name)
            hx, hy = R.keycap_room_half(k.units)
            p = xform(C.top_frame(k), [sx * (hx + P.cap_wall_mm / 2), sy * (hy + P.cap_wall_mm / 2), 0])
            self.assertGreater(float(C.top_height(p[None, :2])[0]), p[2] - 0.2, msg=name)

    def test_no_room_comes_through_the_top(self):
        self.assertEqual(C.thin_tops(), [])

    def test_nothing_stands_between_the_keys_of_one_well(self):
        """Midway between two neighbours, from half a millimetre over the
        higher of their plates' planes there, is clear: in a column, across
        two columns, along the thumb row and between the extra pair."""
        def plate_z(k, x, y):
            o, n = origin(k.frame), k.frame[:3, 2]
            return o[2] - (n[0] * (x - o[0]) + n[1] * (y - o[1])) / n[2]

        for a, b in (("inner_0", "inner_1"), ("inner_0", "index_0"), ("ring_0", "pinky_0"), ("thumb_near", "thumb_home"), ("thumb_x1", "thumb_x2")):
            ka, kb = L.key_named(a), L.key_named(b)
            x, y, _ = (origin(ka.frame) + origin(kb.frame)) / 2
            z = max(plate_z(ka, x, y), plate_z(kb, x, y)) + 1
            self.assertLess((C.body() ^ R.box((1, 1, 1), (x, y, z))).volume(), 1e-6, msg=f"{a} to {b}")


class SocketWalls(unittest.TestCase):
    def setUp(self):
        self.addCleanup(L.reset)
        self.addCleanup(setattr, P, "half", P.half)
        L.reset()

    def left_walls(self):
        P.half = "left"
        L.reset()
        return C.thin_walls()

    def test_both_halves_are_clear(self):
        for half in ("right", "left"):
            P.half = half
            L.reset()
            with self.subTest(half=half):
                self.assertEqual(C.thin_walls(), [])

    def test_a_spur_leaving_a_rib_beside_a_socket_is_caught(self):
        """On the tab's own line, the left half's spur left 0.4 mm of wall to the
        shaft north of the solder well."""
        with mock.patch.object(C, "row_x", lambda: R.socket_tab_tip(1)[0]):
            self.assertIn("thumb_home's shaft", [wall[0] for wall in self.left_walls()])

    def test_a_channel_leaving_a_fin_beside_a_socket_is_caught(self):
        """The row channel along the cell's north edge left 0.2 to 0.3 mm of wall
        between it and the socket's shaft, too thin to print."""
        with mock.patch.object(C, "ne_y", lambda: P.cell_mm / 2 - P.channel_w_mm / 2):
            L.reset()
            self.assertTrue([wall for wall in C.thin_walls() if wall[0] == "ring_0's shaft"])

    def test_a_channel_leaving_a_rib_beside_a_collar_is_caught(self):
        """Stopping at the shaft left 0.12 mm of wall to the north collar's hole,
        where a row channel climbs into the collar's layer toward a higher key."""
        shaft = P.socket_centre_mm[1] + P.socket_body_mm[1] / 2 + P.socket_clearance_mm - 0.1
        with mock.patch.object(C, "shaft_edge_y", lambda: shaft):
            L.reset()
            self.assertTrue([wall for wall in C.thin_walls() if wall[0] == "ring_0's north collar"])


class Openings(unittest.TestCase):
    """Two cuts that only touch leave a skin of no thickness between them, which
    has no volume for a check to see and prints as a wall across the opening."""

    def setUp(self):
        self.addCleanup(L.reset)
        L.reset()
        v, t = mesh_of(C.body())
        c = v[t]
        self.centres = c.mean(axis=1)
        n = np.cross(c[:, 1] - c[:, 0], c[:, 2] - c[:, 0])
        self.normals = n / np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]

    def test_nothing_crosses_the_usb_port(self):
        x0, _, z0, x1, _, z1 = C.place(C.mcu_frame(), R.mcu_room())[1].bounding_box()
        x, y, z = self.centres.T
        past_well = L.mcu_bay()[1][1] + P.mcu_usb_overhang_mm + P.mcu_clearance_mm + 0.1
        across = (x > x0) & (x < x1) & (z > z0) & (z < z1) & (y > past_well) & (np.abs(self.normals[:, 1]) > 0.5)
        self.assertEqual(int(across.sum()), 0)

    def test_nothing_crosses_the_reset_hole(self):
        f = C.reset_button_frame()
        d = self.centres - f[:3, 3]
        along, axis = d @ f[:3, 1], f[:3, 1]
        off_axis = np.linalg.norm(d - np.outer(along, axis), axis=1)
        hole = P.reset_plunger_mm[0] / 2 + P.reset_button_clearance_mm
        across = (off_axis < hole - 0.05) & (along < 0) & (np.abs(self.normals @ axis) > 0.5)
        self.assertEqual(int(across.sum()), 0)


class Bay(unittest.TestCase):
    def setUp(self):
        self.addCleanup(L.reset)
        L.reset()
        self.plinth = C.bottom_plate()
        self.parts = {p.label: p.solid for p in C.electronics()}

    def plinth_in(self, frame, size, centre):
        return (self.plinth ^ C.placed(frame, R.box(size, centre))).volume()

    def test_the_board_and_its_port_lie_level(self):
        for label, thick in (("board", P.mcu_board_mm[2]), ("usb", P.mcu_usb_mm[1])):
            box = self.parts[label].bounding_box()
            self.assertAlmostEqual(box[5] - box[2], thick, places=6)

    def test_the_hole_for_the_port_is_level(self):
        hole = C.place(C.mcu_frame(), R.mcu_room())[2].bounding_box()
        self.assertAlmostEqual(hole[5] - hole[2], P.mcu_usb_relief_mm[1] + 10, places=6)

    def test_the_port_stands_on_the_rest(self):
        w = P.mcu_usb_mm[0] - 0.2
        self.assertEqual(self.plinth_in(C.mcu_frame(), (w, 5, 1), (0, 3, 0.5)), 0)
        self.assertAlmostEqual(self.plinth_in(C.mcu_frame(), (w, 5, 1), (0, 3, -0.5)), w * 5, places=6)

    def test_the_rest_runs_through_the_wall_with_no_groove_beside_it(self):
        c, u = P.mcu_clearance_mm, P.mcu_usb_mm
        o = P.mcu_usb_overhang_mm
        wall = o - c - 0.02
        under = C.placed(C.mcu_frame(), R.box((u[0] + 2 * c + 1, wall, 1), (0, -(o + c) / 2, -0.5)))
        self.assertLess(((C.plinth_shell() ^ under) - self.plinth).volume(), 1e-6)

    def test_the_pin_rows_have_a_gutter_either_side_of_the_rest(self):
        b, u, d = P.mcu_board_mm, P.mcu_usb_mm, P.bay_pocket_mm
        wide = (b[0] - u[0]) / 2
        for side in (-1, 1):
            at = (side * (u[0] + wide) / 2, b[1] / 2, 1 - d / 2)
            self.assertEqual(self.plinth_in(C.mcu_frame(), (wide - 0.1, b[1], d + 2 - 0.1), at), 0)

    def test_the_battery_has_a_pocket_to_lie_in(self):
        b, d = P.battery_mm, P.bay_pocket_mm
        self.assertEqual(self.plinth_in(C.battery_frame(), (b[0], b[1], d), (0, 0, d / 2)), 0)
        self.assertAlmostEqual(self.plinth_in(C.battery_frame(), (b[0], b[1], 1), (0, 0, -0.5)), b[0] * b[1], places=6)


class Lands(unittest.TestCase):
    def setUp(self):
        self.addCleanup(L.reset)
        L.reset()

    def test_each_land_is_flat_on_its_plate_and_meets_the_top_past_its_taper(self):
        for k in C.keys():
            flat, past = C.land_half(), C.land_half() + P.switch_taper_mm
            on = C.land_loop(k, flat)
            self.assertLess(np.abs(C.top_height(on) - C.top_plane_at(k, *on.T)[0]).max(), 1e-9)
            beyond = C.land_loop(k, past + 0.01)
            self.assertLess(np.abs(C.top_height(beyond) - C.top_surface(beyond)).max(), 1e-9)

    def test_a_room_reaching_the_top_past_a_land_is_caught(self):
        self.assertEqual(C.thin_tops(), [])
        k = C.keys()[0]
        p = C.land_loop(k, C.land_half() + 0.8)[0]
        z = float(C.top_height(p[None])[0])
        room = R.box((0.4, 0.4, 2), (p[0], p[1], z - 1))
        with mock.patch.object(C, "body_cuts", lambda: [("a plug", [room])]):
            self.assertEqual([w for w, _ in C.thin_tops()], ["a plug"])


class Seam(unittest.TestCase):
    def setUp(self):
        self.addCleanup(L.reset)
        self.addCleanup(setattr, P, "half", P.half)

    def test_the_body_stands_on_one_plane_on_both_halves(self):
        """The body prints on the seam, so nothing of it may stand below the plane,
        and the plane has to carry the whole of the body's outline."""
        for half in ("right", "left"):
            P.half = half
            L.reset()
            m = C.rinv(L.seam_frame())
            v = C.body().to_mesh64().vert_properties[:, :3]
            z = (m[:3, :3] @ v.T).T[:, 2] + m[2, 3]
            self.assertGreater(z.min(), -1e-6)
            self.assertGreater((z < 1e-6).sum(), len(C.outline()) / 2)

    def test_the_seam_clears_what_hangs_from_the_keys_by_no_more_than_it_must(self):
        slack = []
        for half in ("right", "left"):
            P.half = half
            L.reset()
            m = C.rinv(L.seam_frame())

            def over_seam(pieces):
                v = np.vstack([p.solid.to_mesh64().vert_properties[:, :3] for p in pieces])
                return ((m[:3, :3] @ v.T).T[:, 2] + m[2, 3]).min()
            slack += [over_seam(C.sockets()) - P.under_socket_mm, over_seam(C.diodes()) - P.under_diode_mm]
        self.assertGreater(min(slack), -0.01)
        self.assertLess(min(slack), 0.01)

    def test_both_halves_stand_at_one_height(self):
        tops = []
        for half in ("right", "left"):
            P.half = half
            L.reset()
            tops.append(max(L.cap_top(k)[2] for k in C.keys()))
        self.assertAlmostEqual(*tops)

    def test_the_plinth_stops_under_the_seam_but_for_what_stands_on_it(self):
        """Without the bosses and the board's rest, the plinth's top is plate_gap_mm under the plane,
        so it meets the body flat."""
        P.half = "right"
        L.reset()
        below = C.half_space(L.seam_frame(), -P.plate_gap_mm + 1e-3, below=False, size=600)
        self.assertLess((C.plinth_shell() ^ below).volume(), 1e-6)


class Screws(unittest.TestCase):
    def test_the_screws_fit_the_inserts(self):
        self.assertEqual(C.screw_length_faults(), [])

    def test_a_screw_past_the_insert_is_caught(self):
        with mock.patch.object(P, "screw_len_mm", 6):
            self.assertTrue(C.screw_length_faults())

    def test_a_screw_short_of_the_insert_is_caught(self):
        with mock.patch.object(P, "screw_len_mm", P.screw_grip_mm):
            self.assertTrue(C.screw_length_faults())

    def test_an_insert_longer_than_its_hole_is_caught(self):
        with mock.patch.object(P, "insert_len_mm", P.insert_depth_mm + 1):
            self.assertTrue(C.screw_length_faults())

if __name__ == "__main__":
    unittest.main()

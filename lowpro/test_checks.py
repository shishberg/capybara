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

    def test_a_thumb_column_crowding_the_next_key_is_caught(self):
        """A whole wire's gap past the left half's further tip left 0.74 mm between
        thumb_x2's column channel and thumb_x1's solder well."""
        with mock.patch.object(C, "thumb_col_x", lambda: R.socket_tab_tip(1)[0] + P.wire_gap_mm + P.wire_d_mm / 2):
            self.assertIn(("thumb_x2's column channel", "thumb_x1"), [wall[:2] for wall in self.left_walls()])

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


if __name__ == "__main__":
    unittest.main()

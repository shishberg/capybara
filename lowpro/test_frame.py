"""The frame design has lowpro's keys in parallel, evenly spaced columns with
the extra thumb keys in line, is one solid, has a way for every wire, and its
open-from-below check fails when a rail crosses the floor under the keys, as
the Capybara's tie did. From the repository root:

    .venv/bin/python -m unittest lowpro.test_frame
"""
import unittest

import numpy as np

from . import build as B
from . import chassis as C
from . import frame as F
from . import layout as L
from . import params as P
from . import parts as R
from . import wires as W


def key_frames(preset):
    B.set_params([], preset)
    L.reset()
    return {k.name: k.frame.copy() for k in L.keys()}


class Frame(unittest.TestCase):
    def setUp(self):
        self.addCleanup(L.reset)
        self.addCleanup(setattr, P, "design", P.design)

    def test_the_columns_are_parallel_and_evenly_spaced(self):
        frame = key_frames("frame")
        self.assertEqual(key_frames(None).keys(), frame.keys())
        homes = [frame[f"{c}_0"] for c in ("inner", "index", "middle", "ring", "pinky")]
        for f in homes:
            np.testing.assert_allclose(f[:2, 1] / np.linalg.norm(f[:2, 1]), (0, 1), atol=1e-9)
        gaps = np.diff([f[0, 3] for f in homes])
        np.testing.assert_allclose(gaps, gaps[0], atol=1e-9)

    def test_the_extra_thumb_keys_are_a_fourth_key_in_their_columns(self):
        frame = key_frames("frame")
        for extra, column in (("thumb_x1", "middle"), ("thumb_x2", "ring")):
            f, last = frame[extra], frame[f"{column}_-1"]
            self.assertAlmostEqual(f[0, 3], last[0, 3], delta=0.5, msg=extra)
            self.assertLess(f[1, 3], last[1, 3], msg=extra)
            np.testing.assert_allclose(f[:2, 1] / np.linalg.norm(f[:2, 1]), (0, 1), atol=0.05, err_msg=extra)

    def test_every_wire_has_a_way_clear_of_the_frame_and_parts(self):
        key_frames("frame")
        self.assertEqual(W.unrouted(), [])
        solid = W.solids()
        for w in W.wires():
            self.assertLess((W.tube(w.points) ^ solid).volume(), 0.01, msg=f"{w.net} {w.ends}")

    def test_the_frame_is_one_solid_open_from_below(self):
        key_frames("frame")
        self.assertEqual(len(F.body().decompose()), 1)
        self.assertEqual(F.covered(), [])

    def test_a_rail_across_the_floor_is_caught(self):
        key_frames("frame")
        q = C.outline()
        y = float(np.mean([L.key_named(n).frame[1, 3] for n in ("middle_0", "ring_0")]))
        tie = R.box((np.ptp(q[:, 0]), 2.4, 60), (q[:, 0].mean(), y, 0)) ^ F.rail_slab()
        self.assertNotEqual(F.covered(F.body() + tie), [])


if __name__ == "__main__":
    unittest.main()

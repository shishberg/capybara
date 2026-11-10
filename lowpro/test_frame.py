"""The frame design keeps lowpro's keys and heights, is one solid, and its
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


def key_frames(preset):
    B.set_params([], preset)
    L.reset()
    return {k.name: k.frame.copy() for k in L.keys()}


class Frame(unittest.TestCase):
    def setUp(self):
        self.addCleanup(L.reset)
        self.addCleanup(setattr, P, "design", P.design)

    def test_keys_sit_where_lowpro_puts_them(self):
        lowpro, frame = key_frames(None), key_frames("frame")
        self.assertEqual(lowpro.keys(), frame.keys())
        for name in lowpro:
            np.testing.assert_allclose(frame[name], lowpro[name], atol=1e-9, err_msg=name)

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

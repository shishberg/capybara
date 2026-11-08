"""The capybara design's keys and parts have to be exactly where the Capybara's
editor puts them, or the wired harness won't drop in. From the repository root:

    .venv/bin/python -m unittest lowpro.test_swung_in
"""
import json
import subprocess
import unittest

import numpy as np

from . import layout as L
from . import params as P
from .build import set_params

ROOT = L.ROOT


def editor_placement(half):
    """The editor's own placement for `half`, run here independently of layout.py."""
    run = subprocess.run(["node", "--import", "tsx", "tests/key-frames.ts", half], cwd=ROOT / "editor",
                         capture_output=True, text=True, check=True)
    return json.loads(run.stdout)


class SwungIn(unittest.TestCase):
    def setUp(self):
        was = {name: getattr(P, name) for name in PRESET_NAMES} | {"half": P.half}
        self.addCleanup(lambda: [setattr(P, n, v) for n, v in was.items()])
        self.addCleanup(L.reset)
        set_params([], "capybara")

    def test_keys_and_parts_sit_where_the_editor_puts_them(self):
        for half in ("right", "left"):
            P.half = half
            L.reset()
            editor = editor_placement(half)
            lift = np.array([0, 0, P.bottom_plate_mm - editor["skin_mm"]])
            with self.subTest(half=half):
                self.assertEqual(sorted(k.name for k in L.keys()), sorted(editor["units"]))
                for k in L.keys():
                    want = np.array(editor["frames"][k.name], float)
                    want[:3, 3] += lift
                    np.testing.assert_allclose(k.frame, want, atol=1e-6, rtol=0, err_msg=k.name)
                    self.assertEqual(k.units, editor["units"][k.name])
                for name in ("pro_micro", "trrs", "reset"):
                    want = np.array(editor["frames"][name], float)
                    want[:3, 3] += lift
                    np.testing.assert_allclose(L.editor_frame(name), want, atol=1e-6, rtol=0, err_msg=name)

    def test_the_seam_is_the_editors_base_plate_top(self):
        self.assertEqual(float(L.seam_frame()[2, 3]), P.bottom_plate_mm)
        np.testing.assert_allclose(L.seam_frame()[:3, 2], [0, 0, 1])


PRESET_NAMES = list(P.PRESETS["capybara"])

if __name__ == "__main__":
    unittest.main()

import copy
import json
import unittest
from pathlib import Path
import pcbnew as pcb
from rosebear import seed, routing, assembly, pod_pins
from rosebear.pcb import load_board, pad_of, net, vec
ROOT=Path(__file__).resolve().parents[1]

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads((ROOT/'config.json').read_text())

    def test_staging_override_fails_on_missing_or_duplicate_function(self):
        for text in ['','foo foo']:
            with self.assertRaises(ValueError): seed.replace_once('foo','bar',text)

    def test_pod_pins_resolve_and_reject_ambiguous_names(self):
        spec=pod_pins.load()
        self.assertEqual(pod_pins.resolve(spec,'IO32'),('J_R',17,'IO32'))
        self.assertEqual(pod_pins.resolve(spec,'J_R:26'),('J_R',26,'GND'))
        with self.assertRaisesRegex(ValueError,'HEADER:number'): pod_pins.resolve(spec,'GND')

    def test_pod_check_rejects_unbuilt_fixed_group_and_used_reserved_pin(self):
        spec=pod_pins.load()
        pod=load_board(str(ROOT/'output/seeded/pod.kicad_pcb'))
        self.assertEqual(pod_pins.check(spec,pod,[]),[])
        # rgb isn't built, so checked as built its nets are missing from its pins.
        self.assertTrue(any('RGB_L_3V3' in e for e in pod_pins.check(spec,pod,['rgb'])))
        socket=next(f for f in pod.GetFootprints() if f.GetReference()=='J_R')
        pad_of(socket,pod_pins.resolve(spec,'IO30')[1]).SetNet(net(pod,'COL_R_RING'))
        self.assertIn('pod: IO30 is reserved for rgb but carries COL_R_RING',pod_pins.check(spec,pod,[]))

    def test_seed_staging_hides_reserved_pins_and_uses_pod_json_costs(self):
        staged=pod_pins.stage_seed(pod_pins.load(),(ROOT/'seed/baml_src/pod.baml').read_text(),seed.replace_once)
        self.assertIn('"RSV_IO30"',staged); self.assertNotIn('"IO30"',staged)
        self.assertIn('return 4;',staged)

    def test_via_touching_bend_is_rejected(self):
        b=pcb.BOARD(); v=pcb.PCB_VIA(b); v.SetPosition(vec(1.2,0)); v.SetWidth(600000); v.SetDrill(300000); v.SetLayerPair(pcb.F_Cu,pcb.B_Cu); b.Add(v)
        self.assertTrue(routing.check_bends(b,[[-1,-1,1,1]]))

    def test_collision_detection_handles_rotated_bodies(self):
        a={'frame':{'origin':[0,0,0],'axes':[[1,0,0],[0,1,0],[0,0,1]]}}
        a['corners']=assembly.box_corners(a['frame'],[-1,-1,-1,1,1,1])
        b=copy.deepcopy(a); b['frame']['origin']=[1,0,0]
        b['corners']=assembly.box_corners(b['frame'],[-1,-1,-1,1,1,1])
        self.assertTrue(assembly.boxes_intersect(a,b))
        b['frame']['origin']=[3,0,0]; b['corners']=assembly.box_corners(b['frame'],[-1,-1,-1,1,1,1])
        self.assertFalse(assembly.boxes_intersect(a,b))

    def test_geometry_cache_invalidates_config_change(self):
        chassis=json.loads((ROOT/'mechanical/chassis.json').read_text())
        seed.verify_cache(ROOT,ROOT/'output',chassis,self.config)
        changed=copy.deepcopy(self.config); changed['plate_top_to_pcb_mm']+=.1
        with self.assertRaisesRegex(ValueError,'Stale geometry'):
            seed.verify_cache(ROOT,ROOT/'output',chassis,changed)

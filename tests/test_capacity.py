"""Capacity summaries distinguish compute, memory and unavailable measurements."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/aistation-a800/scripts'))
from a800_capacity import summarize,inspect
from a800_probe import ProbeError


class CapacityTests(unittest.TestCase):
    def test_separate_devices_and_compute_memory(self):
        a={'uuid':'GPU-a','name':'test','GPU_util_percent':100,'used_MiB':20,'total_MiB':80}
        b={'uuid':'GPU-b','name':'test','GPU_util_percent':0,'used_MiB':79,'total_MiB':80}
        result=summarize([[a,b],[dict(a,GPU_util_percent=60),dict(b,GPU_util_percent=20)]])
        self.assertEqual(result[0]['GPU_util_percent']['mean'],80)
        self.assertEqual(result[1]['GPU_util_percent']['mean'],10)
        self.assertEqual(result[0]['used_MiB']['mean'],20)
        self.assertIsNone(result[0]['power_W'])

    def test_unavailable_is_not_zero(self):
        result=summarize([[{'uuid':'a','name':'test','GPU_util_percent':None}],[{'uuid':'a','name':'test','GPU_util_percent':80}]])
        self.assertEqual(result[0]['GPU_util_percent'],{'observed':1,'min':80,'mean':80,'max':80})

    def test_long_wait_rejected_before_ssh(self):
        with self.assertRaises(ProbeError):inspect({},samples=60,interval=1)
        with self.assertRaises(ProbeError):inspect({},samples=0,interval=1)


if __name__=='__main__':unittest.main()

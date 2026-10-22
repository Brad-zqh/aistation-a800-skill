"""Behavioral invariants: active appends, duplicate IDs and strict trust."""
from pathlib import Path
import importlib.util,json,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('probe',ROOT/'skills/aistation-a800/scripts/a800_probe.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)

    def tearDown(self):self.tmp.cleanup()

    def test_live_append_never_truncated_and_duplicates_detected(self):
        p=self.root/'main_NO_TEXT.jsonl'
        data=b'{"item":"a","valid":true}\n{"item":"a","valid":false}\n{"item":'
        p.write_bytes(data);r=probe.count_checkpoint(p,[self.root])
        self.assertEqual((r['complete_rows'],r['valid_true_rows'],r['duplicate_ID_rows']),(2,1,1))
        self.assertTrue(r['trailing_partial_ignored']);self.assertEqual(p.read_bytes(),data)

    def test_private_boundary_enforced(self):
        p=self.root/'outside_NO_TEXT.jsonl';p.write_text('{}\n')
        with self.assertRaises(probe.ProbeError):probe.count_checkpoint(p,[self.root/'subdirectory'])

    def test_raw_source_payload_rejected(self):
        p=self.root/'misnamed_NO_TEXT.jsonl';p.write_text('{"body":"synthetic test value"}\n')
        with self.assertRaises(probe.ProbeError):probe.count_checkpoint(p,[self.root])

    def test_remote_state_cannot_escape_project(self):
        for value in ['../other/state.json','/etc/passwd','state/../../file','state\\other.json']:
            with self.assertRaises(probe.ProbeError):probe.relative_remote(value)

    def test_ssh_never_uses_unverified_host(self):
        identity=self.root/'identity';identity.touch();known=self.root/'known';known.touch()
        cfg={'ssh':{'host':'example.edu','user':'researcher','port':22222,'identity_file':str(identity),'known_hosts':str(known)}}
        args=probe.ssh_argv(cfg)
        self.assertIn('StrictHostKeyChecking=yes',args);self.assertIn('BatchMode=yes',args)
        self.assertIn('IdentitiesOnly=yes',args);self.assertNotIn('StrictHostKeyChecking=no',args)


if __name__=='__main__':unittest.main()

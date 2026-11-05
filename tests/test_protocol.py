import importlib.util
import json
import os
from pathlib import Path
import struct
import tempfile
import time
import unittest
from unittest.mock import patch

from common import bridge_protocol as p
from common.job_runner import process_job

spec = importlib.util.spec_from_file_location("stl_writer", Path(__file__).resolve().parents[1] / "blender/blender_fusion_bridge/stl_writer.py")
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def make_job(self):
        folder = p.create_job(self.root)
        stl = folder / "mesh_0000.stl"
        writer.write_binary_stl(stl, [((0, 0, 0), (10, 0, 0), (0, 20, 0))])
        data = p.publish_job(folder, "Zażółć gęślą", [{"file": stl.name, "name": "Łącznik", "triangles": 1, "sha256": p.digest(stl)}])
        return folder, data

    def test_units(self):
        self.assertEqual(p.millimeters_per_unit("SCENE", 0.001), 1)
        self.assertEqual(p.millimeters_per_unit("SCENE", 1), 1000)
        self.assertEqual(p.millimeters_per_unit("INCH", 1), 25.4)
        self.assertEqual(p.millimeters_per_unit("MM", 1), 1)
        for mode, scale in (("NO", 1), ("SCENE", float("nan")), ("SCENE", 0)):
            with self.assertRaises(ValueError):
                p.millimeters_per_unit(mode, scale)

    def test_stl_bytes_normals_and_dimensions(self):
        folder, _ = self.make_job()
        raw = (folder / "mesh_0000.stl").read_bytes()
        self.assertEqual(len(raw), 134)
        self.assertEqual(struct.unpack_from("<I", raw, 80), (1,))
        values = struct.unpack_from("<12fH", raw, 84)
        self.assertEqual(values[:3], (0, 0, 1))
        self.assertEqual(values[3:12], (0, 0, 0, 10, 0, 0, 0, 20, 0))

    def test_empty_or_nonfinite_mesh_rejected(self):
        for triangles in ([], [((float("nan"), 0, 0), (0, 0, 0), (0, 1, 0))]):
            with self.assertRaises(ValueError):
                writer.write_binary_stl(self.root / "bad.stl", triangles)

    def test_unpublished_job_invisible(self):
        p.create_job(self.root)
        self.assertEqual(p.pending_jobs(self.root), [])

    def test_status_write_retries_transient_windows_sharing_error(self):
        replace = os.replace
        calls = []
        def transient(source, target):
            calls.append(1)
            if len(calls) == 1:
                raise PermissionError("File temporarily opened by Blender")
            replace(source, target)
        with patch.object(p.os, "replace", side_effect=transient):
            p.atomic_json(self.root / "status.json", {"state": "done"})
        self.assertEqual(len(calls), 2)
        self.assertEqual(p.read_json(self.root / "status.json"), {"state": "done"})
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_success_consumed_once_and_unicode_preserved(self):
        folder, data = self.make_job()
        calls = []
        self.assertEqual(p.pending_jobs(self.root), [folder])
        self.assertTrue(process_job(folder, lambda f, m: calls.append(m["name"])))
        self.assertFalse(process_job(folder, lambda f, m: calls.append("duplicate")))
        self.assertEqual(calls, ["Zażółć gęślą"])
        self.assertEqual(p.read_json(folder / "status.json")["state"], "done")
        self.assertTrue((folder / "finished.json").exists())
        self.assertEqual(p.pending_jobs(self.root), [])

    def test_import_failure_is_terminal(self):
        folder, _ = self.make_job()
        def fail(*args):
            raise RuntimeError("Import failed")
        process_job(folder, fail)
        self.assertEqual(p.read_json(folder / "status.json")["state"], "error")
        self.assertFalse(process_job(folder, fail))

    def test_tampering_prevents_import(self):
        folder, _ = self.make_job()
        stl = folder / "mesh_0000.stl"
        raw = bytearray(stl.read_bytes())
        raw[100] ^= 1
        stl.write_bytes(raw)
        process_job(folder, lambda *args: self.fail("Corrupted mesh reached Fusion"))
        self.assertEqual(p.read_json(folder / "status.json")["state"], "error")

    def test_reject_path_traversal_duplicate_version_and_wrong_size(self):
        for change in (lambda d: d["objects"][0].update(file="../../secret.stl"),
                       lambda d: d.update(protocol=999),
                       lambda d: d.update(units="cm"),
                       lambda d: d["objects"].append(d["objects"][0]),
                       lambda d: d["objects"][0].update(triangles=2)):
            folder, data = self.make_job()
            change(data)
            with self.assertRaises(ValueError):
                p.validate_job(folder, data)

    def test_recovery_never_replays_uncertain_import(self):
        folder, _ = self.make_job()
        self.assertTrue(p.claim_job(folder))
        p.write_status(folder, "processing", "Importing")
        p.recover_interrupted(self.root)
        self.assertEqual(p.read_json(folder / "status.json")["state"], "uncertain")
        self.assertFalse(process_job(folder, lambda *args: self.fail("Replayed")))

    def test_recovery_keeps_completed_status(self):
        folder, _ = self.make_job()
        p.claim_job(folder)
        p.write_status(folder, "done", "Imported")
        p.recover_interrupted(self.root)
        self.assertEqual(p.read_json(folder / "status.json")["state"], "done")

    def test_heartbeat_expires_and_bad_json_is_offline(self):
        path = self.root / "receiver.json"
        p.atomic_json(path, {"state": "ready", "updated_at": time.time()})
        self.assertEqual(p.receiver_status(self.root), "ready")
        p.atomic_json(path, {"state": "ready", "updated_at": time.time() - 20})
        self.assertEqual(p.receiver_status(self.root), "offline")
        path.write_text("{")
        self.assertEqual(p.receiver_status(self.root), "offline")

    @unittest.skipUnless(os.name == "nt", "Windows byte-range lock")
    def test_only_one_receiver_and_release(self):
        first, second = p.ReceiverLock(self.root), p.ReceiverLock(self.root)
        first.acquire()
        try:
            with self.assertRaises(RuntimeError):
                second.acquire()
        finally:
            first.release()
        second.acquire()
        second.release()


if __name__ == "__main__":
    unittest.main()

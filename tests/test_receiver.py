"""Verify idle scheduling without invoking real Fusion modeling APIs."""
import importlib.util
from pathlib import Path
import sys
import threading
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from common import bridge_protocol, job_runner


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / "fusion/BlenderFusionBridge"
        adsk = ModuleType("adsk")
        adsk.core = ModuleType("adsk.core")
        adsk.fusion = ModuleType("adsk.fusion")
        adsk.core.CustomEventHandler = type("CustomEventHandler", (), {})
        package = ModuleType("fusion_receiver_test")
        package.__path__ = [str(base)]
        importer = ModuleType("fusion_receiver_test.importer")
        importer.import_meshes = Mock()
        modules = {"adsk": adsk, "adsk.core": adsk.core, "adsk.fusion": adsk.fusion, "fusion_receiver_test": package,
                   "fusion_receiver_test.bridge_protocol": bridge_protocol,
                   "fusion_receiver_test.job_runner": job_runner, "fusion_receiver_test.importer": importer}
        self.patch = patch.dict(sys.modules, modules)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        spec = importlib.util.spec_from_file_location("fusion_receiver_test.BlenderFusionBridge", base / "BlenderFusionBridge.py")
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.runtime = NS(stop_event=threading.Event(), pending=threading.Event(),
                          app=NS(userInterface=NS(activeCommand="SelectCommand")), root=Path("/queue"),
                          state="ready", logger=Mock(), refresh_document=Mock(), report_outgoing=Mock(), document_token="abc")
        self.runtime.pending.set()

    def test_busy_command_defers_import_and_allows_next_event(self):
        self.runtime.app.userInterface.activeCommand = "Extrude"
        with patch.object(self.module, "process_job") as process:
            self.module.ReceiveHandler(self.runtime).notify(None)
            process.assert_not_called()
        self.assertEqual(self.runtime.state, "busy")
        self.assertFalse(self.runtime.pending.is_set())

    def test_idle_processes_only_one_job_per_event(self):
        with patch.object(bridge_protocol, "pending_jobs", return_value=[Path("first"), Path("second")]), \
                patch.object(self.module, "process_job") as process:
            self.module.ReceiveHandler(self.runtime).notify(None)
            self.assertEqual(process.call_count, 1)
            self.assertEqual(process.call_args.args[0], Path("first"))
        self.assertFalse(self.runtime.pending.is_set())
        self.assertEqual(self.runtime.state, "ready")

    def test_stop_prevents_queued_event_import(self):
        self.runtime.stop_event.set()
        with patch.object(self.module, "process_job") as process:
            self.module.ReceiveHandler(self.runtime).notify(None)
            process.assert_not_called()
        self.assertFalse(self.runtime.pending.is_set())

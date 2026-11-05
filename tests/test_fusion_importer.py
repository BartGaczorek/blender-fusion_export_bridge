import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import patch


class FusionImporterTests(unittest.TestCase):
    def setUp(self):
        self.adsk = ModuleType("adsk")
        self.adsk.core = ModuleType("adsk.core")
        self.adsk.fusion = ModuleType("adsk.fusion")
        self.adsk.core.DocumentTypes = NS(FusionDesignDocumentType="design")
        self.adsk.fusion.MeshUnits = NS(MillimeterMeshUnit="mm")
        self.adsk.fusion.Design = NS(cast=lambda obj: obj)
        self.patch = patch.dict(sys.modules, {"adsk": self.adsk, "adsk.core": self.adsk.core, "adsk.fusion": self.adsk.fusion})
        self.patch.start()
        self.addCleanup(self.patch.stop)
        path = Path(__file__).resolve().parents[1] / "fusion/BlenderFusionBridge/importer.py"
        spec = importlib.util.spec_from_file_location("fusion_importer_test", path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.calls, self.closed, self.activated = [], [], []
        self.document = NS(name="", close=lambda save: self.closed.append(save) or True)
        self.previous = NS(isValid=True, activate=lambda: self.activated.append(True))
        self.app = NS(activeDocument=self.previous,
                      documents=NS(add=lambda kind: self.document),
                      activeProduct=NS(rootComponent=NS(meshBodies=NS(add=self.add_mesh))),
                      activeViewport=NS(fit=lambda: None))
        self.manifest = {"name": "Two objects", "objects": [
            {"file": "mesh_0000.stl", "name": "First"}, {"file": "mesh_0001.stl", "name": "Second"}]}
        self.fail_at = None

    def add_mesh(self, filename, unit):
        body = NS(name="")
        self.calls.append((filename, unit, body))
        if self.fail_at == len(self.calls):
            raise RuntimeError("Fusion import failed")
        return NS(count=1, item=lambda index: body)

    def test_import_separate_named_bodies_explicit_mm(self):
        result = self.module.import_meshes(self.app, Path("/queue"), self.manifest)
        self.assertEqual(result, {"document": "Two objects", "objects": 2})
        self.assertEqual([x[1] for x in self.calls], ["mm", "mm"])
        self.assertEqual([x[2].name for x in self.calls], ["First", "Second"])
        self.assertEqual(self.closed, [])

    def test_partial_failure_closes_only_new_document_without_saving(self):
        self.fail_at = 2
        with self.assertRaisesRegex(RuntimeError, "Fusion import failed"):
            self.module.import_meshes(self.app, Path("/queue"), self.manifest)
        self.assertEqual(self.closed, [False])
        self.assertEqual(self.activated, [True])

    def test_view_fit_failure_does_not_turn_success_into_error(self):
        def fail():
            raise RuntimeError("No viewport")
        self.app.activeViewport.fit = fail
        self.assertEqual(self.module.import_meshes(self.app, Path("/queue"), self.manifest)["objects"], 2)
        self.assertEqual(self.closed, [])

    def test_failed_cleanup_is_reported(self):
        self.fail_at = 1
        self.document.close = lambda save: False
        with self.assertRaisesRegex(RuntimeError, "częściowy dokument"):
            self.module.import_meshes(self.app, Path("/queue"), self.manifest)

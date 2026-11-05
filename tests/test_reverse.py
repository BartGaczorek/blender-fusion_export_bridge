import importlib.util
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import patch, Mock
from common import bridge_protocol as p
from common.stl_reader import indexed_mesh

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('writer_reverse', ROOT/'blender/blender_fusion_bridge/stl_writer.py')
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)


class Point:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z
    def copy(self):
        return Point(self.x, self.y, self.z)
    def transformBy(self, m):
        self.x += 3
        return True


class ReverseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        adsk = ModuleType('adsk')
        adsk.fusion = ModuleType('adsk.fusion')
        adsk.fusion.MeshBody = NS(cast=lambda x: x if x.kind == 'mesh' else None)
        adsk.fusion.BRepBody = NS(cast=lambda x: x if x.kind == 'brep' else None)
        adsk.fusion.TriangleMeshQualityOptions = NS(NormalQualityTriangleMesh=11)
        package = ModuleType('reverse_test')
        package.__path__ = [str(ROOT/'fusion/BlenderFusionBridge')]
        self.patches = patch.dict(sys.modules, {'adsk': adsk, 'adsk.fusion': adsk.fusion,
            'reverse_test': package, 'reverse_test.bridge_protocol': p, 'reverse_test.stl_writer': writer})
        self.patches.start()
        self.addCleanup(self.patches.stop)
        self.module = self.load('exporter')
        self.launcher = self.load('launcher')
        self.mesh = NS(nodeIndices=[0, 1, 2], nodeCoordinates=[Point(0, 0, 0), Point(1, 0, 0), Point(0, 2, 0)])

    def load(self, name):
        spec = importlib.util.spec_from_file_location('reverse_test.'+name, ROOT/f'fusion/BlenderFusionBridge/{name}.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def body(self, kind='mesh'):
        calculator = NS(setQuality=Mock(), calculate=Mock(return_value=self.mesh))
        return NS(kind=kind, nativeObject=None, assemblyContext=None, name='Test', displayMesh=self.mesh,
                  meshManager=NS(createMeshCalculator=Mock(return_value=calculator)))

    def test_mesh_as_is_and_mm_roundtrip(self):
        body = self.body()
        folder = self.module.export_bodies(self.root, [body], 'Test')
        body.meshManager.createMeshCalculator.assert_not_called()
        data = p.read_json(folder/'ready.json')
        self.assertEqual(data['target'], 'BLENDER')
        vertices, faces = indexed_mesh(folder/'mesh_0000.stl', 1000)
        self.assertEqual(vertices, [(0, 0, 0), (.01, 0, 0), (0, .02, 0)])
        self.assertEqual(faces, [(0, 1, 2)])

    def test_brep_and_open_surface_use_normal_preset(self):
        for is_solid in (True, False):
            body = self.body('brep')
            body.isSolid = is_solid
            self.module.export_bodies(self.root, [body], 'Body')
            calculator = body.meshManager.createMeshCalculator.return_value
            calculator.setQuality.assert_called_once_with(11)
            calculator.calculate.assert_called_once()

    def test_occurrence_transform_applied_once(self):
        body = self.body()
        body.nativeObject = self.body()
        body.assemblyContext = NS(transform2=NS(asArray=lambda: [1,0,0,3, 0,1,0,0, 0,0,1,0, 0,0,0,1]))
        folder = self.module.export_bodies(self.root, [body], 'Moved')
        vertices, _ = indexed_mesh(folder/'mesh_0000.stl', 1)
        self.assertEqual(vertices[0], (30, 0, 0))
        self.assertEqual(vertices[1], (40, 0, 0))

    def test_partial_export_failure_does_not_publish(self):
        body = self.body()
        body.displayMesh = None
        with self.assertRaises(RuntimeError):
            self.module.export_bodies(self.root, [self.body(), body], 'Bad')
        self.assertEqual(list((self.root/'jobs').iterdir()), [])

    def test_no_launch_if_receiver_is_busy(self):
        with patch.object(self.launcher, 'receiver_running', return_value=True), \
                patch.object(self.launcher.subprocess, 'Popen') as popen:
            self.launcher.ensure_blender(self.root, None)
            popen.assert_not_called()

    def test_startup_passes_executable_and_bootstrap_as_separate_arguments(self):
        lock = Mock()
        with patch.object(self.launcher, 'receiver_running', return_value=False), \
                patch.object(self.launcher, 'resolve_executable', return_value=Path('C:/Program Files/Blender/blender.exe')), \
                patch.object(self.launcher, 'process_running', return_value=False), \
                patch.object(p, 'ReceiverLock', return_value=lock), \
                patch.object(self.launcher.subprocess, 'Popen') as popen:
            self.launcher.ensure_blender(self.root, None)
            args = popen.call_args.args[0]
            self.assertEqual(len(args), 3)
            self.assertEqual(args[1], '--python')
            self.assertFalse(popen.call_args.kwargs['shell'])
            self.launcher.ensure_blender(self.root, None)
            self.assertEqual(popen.call_count, 1)
            self.assertEqual(lock.release.call_count, 2)

    def test_existing_process_without_receiver_does_not_open_second_window(self):
        with patch.object(self.launcher, 'receiver_running', return_value=False), \
                patch.object(self.launcher, 'resolve_executable', return_value=Path('blender.exe')), \
                patch.object(self.launcher, 'process_running', return_value=True), \
                patch.object(p, 'ReceiverLock', return_value=Mock()), \
                patch.object(self.launcher.subprocess, 'Popen') as popen:
            result = self.launcher.ensure_blender(self.root, None)
            self.assertIn('włącz dodatek', result)
            popen.assert_not_called()

    def test_active_target_requires_fresh_receiver_and_token(self):
        import time
        with self.assertRaises(ValueError):
            p.receiver_document(self.root)
        p.atomic_json(self.root/'receiver.json', {'state':'ready','updated_at':time.time(), 'protocol':2, 'document_token':'abc'})
        self.assertEqual(p.receiver_document(self.root), 'abc')
        p.atomic_json(self.root/'receiver.json', {'state':'ready','updated_at':0, 'protocol':2, 'document_token':'abc'})
        with self.assertRaises(ValueError):
            p.receiver_document(self.root)

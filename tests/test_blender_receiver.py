import importlib.util
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import patch
from common import bridge_protocol, job_runner, stl_reader

ROOT = Path(__file__).resolve().parents[1]


class Store:
    def __init__(self, factory):
        self.factory, self.items = factory, []
    def new(self, *args):
        item = self.factory(*args)
        self.items.append(item)
        return item
    def remove(self, item, **kwargs):
        self.items.remove(item)


class BlenderReceiverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.links = []
        self.existing = NS(name='Existing object')
        bpy = ModuleType('bpy')
        self.scene = NS(name='Open Scene', bfb_units='SCENE', unit_settings=NS(scale_length=.001),
                        collection=NS(children=NS(link=self.links.append)))
        bpy.context = NS(scene=self.scene, mode='OBJECT')
        self.meshes = Store(lambda name: NS(name=name, users=0, from_pydata=lambda *args: None, update=lambda: None))
        self.objects = Store(lambda name, mesh: NS(name=name, data=mesh))
        self.objects.items.append(self.existing)
        self.collections = Store(lambda name: NS(name=name, objects=NS(link=lambda obj: None)))
        bpy.data = NS(meshes=self.meshes, objects=self.objects, collections=self.collections)
        package = ModuleType('blender_receive_test')
        package.__path__ = [str(ROOT/'blender/blender_fusion_bridge')]
        self.patch = patch.dict(sys.modules, {'bpy':bpy, 'blender_receive_test':package,
            'blender_receive_test.bridge_protocol':bridge_protocol,
            'blender_receive_test.job_runner':job_runner, 'blender_receive_test.stl_reader':stl_reader})
        self.patch.start()
        self.addCleanup(self.patch.stop)
        spec = importlib.util.spec_from_file_location('blender_receive_test.receiver', ROOT/'blender/blender_fusion_bridge/receiver.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.manifest = {'target':'BLENDER','name':'Fusion','objects':[{'name':'A','file':'a.stl'},{'name':'B','file':'b.stl'}]}

    def test_append_preserves_existing_scene_and_selection(self):
        with patch.object(self.module, 'indexed_mesh', return_value=([(0,0,0)], [])) as reader:
            result = self.module.import_meshes(self.root, self.manifest)
        self.assertEqual(result, {'scene':'Open Scene','objects':2})
        self.assertIn(self.existing, self.objects.items)
        self.assertEqual(len(self.objects.items), 3)
        self.assertEqual(reader.call_args.args[1], 1.0)
        self.assertEqual(len(self.collections.items), 1)

    def test_failure_rolls_back_only_this_transfer(self):
        with patch.object(self.module, 'indexed_mesh', side_effect=[([(0,0,0)], []), ValueError('bad STL')]):
            with self.assertRaises(ValueError):
                self.module.import_meshes(self.root, self.manifest)
        self.assertEqual(self.objects.items, [self.existing])
        self.assertEqual(self.meshes.items, [])
        self.assertEqual(self.collections.items, [])

    def test_reject_wrong_channel_without_changing_scene(self):
        self.manifest['target'] = 'NEW'
        with self.assertRaises(ValueError):
            self.module.import_meshes(self.root, self.manifest)
        self.assertEqual(self.objects.items, [self.existing])

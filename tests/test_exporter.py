"""Behavioral geometry tests using small Blender data doubles, no bpy dependency."""
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
from types import ModuleType, SimpleNamespace as NS
import unittest

from common import bridge_protocol

BASE = Path(__file__).resolve().parents[1] / "blender/blender_fusion_bridge"
package = ModuleType("bridge_export_test")
package.__path__ = [str(BASE)]
sys.modules[package.__name__] = package
sys.modules[package.__name__ + ".bridge_protocol"] = bridge_protocol
spec = importlib.util.spec_from_file_location(package.__name__ + ".exporter", BASE / "exporter.py")
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class Vector(tuple):
    def __mul__(self, scale):
        return Vector(x * scale for x in self)


class Matrix:
    def __init__(self, scale=(1, 1, 1), offset=(0, 0, 0)):
        self.scale, self.offset = scale, offset

    def copy(self):
        return self

    def to_3x3(self):
        return self

    def determinant(self):
        x, y, z = self.scale
        return x * y * z

    def __matmul__(self, point):
        return Vector(point[i] * self.scale[i] + self.offset[i] for i in range(3))


class Object:
    type = "MESH"
    name = "Test mesh"

    def __init__(self, matrix=None, empty=False):
        self.matrix_world = matrix or Matrix()
        self.cleared = False
        self.evaluated = False
        self.mesh = NS(vertices=[NS(co=(0, 0, 0)), NS(co=(1, 0, 0)), NS(co=(0, 1, 0))],
                       loop_triangles=[] if empty else [NS(vertices=(0, 1, 2))],
                       calc_loop_triangles=lambda: None)

    def evaluated_get(self, graph):
        self.evaluated = True
        return self

    def to_mesh(self):
        return self.mesh

    def to_mesh_clear(self):
        self.cleared = True


class ExporterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def context(self, objects, scale=0.001, mode="OBJECT"):
        return NS(mode=mode, selected_objects=objects,
                  scene=NS(unit_settings=NS(scale_length=scale)), evaluated_depsgraph_get=lambda: object())

    def test_evaluated_world_transform_and_mirrored_winding(self):
        obj = Object(Matrix((-2, 3, 1), (10, 20, 30)))
        folder, count = exporter.export_selection(self.context([obj]), self.root)
        values = struct.unpack_from("<12fH", (folder / "mesh_0000.stl").read_bytes(), 84)
        self.assertEqual(values[:3], (0, 0, 1))
        self.assertEqual(values[3:12], (10, 20, 30, 10, 23, 30, 8, 20, 30))
        self.assertEqual(count, 1)
        self.assertTrue(obj.evaluated and obj.cleared)

    def test_scene_unit_conversion(self):
        folder, _ = exporter.export_selection(self.context([Object()], scale=1), self.root)
        values = struct.unpack_from("<12fH", (folder / "mesh_0000.stl").read_bytes(), 84)
        self.assertEqual(values[6], 1000)
        self.assertEqual(values[10], 1000)

    def test_multiple_objects_and_nonascii_names(self):
        a, b = Object(), Object()
        a.name, b.name = "Obudowa/Łącznik", "Śruba"
        folder, _ = exporter.export_selection(self.context([a, b]), self.root)
        data = bridge_protocol.read_json(folder / "ready.json")
        self.assertEqual([x["name"] for x in data["objects"]], [a.name, b.name])
        self.assertEqual([x["file"] for x in data["objects"]], ["mesh_0000.stl", "mesh_0001.stl"])

    def test_failure_cleans_partial_export_and_evaluated_mesh(self):
        good, bad = Object(), Object(empty=True)
        with self.assertRaises(ValueError):
            exporter.export_selection(self.context([good, bad]), self.root)
        self.assertTrue(good.cleared and bad.cleared)
        self.assertEqual(list((self.root / "jobs").iterdir()), [])

    def test_reject_edit_mode_unsupported_and_empty_selection(self):
        camera = Object()
        camera.type = "CAMERA"
        for context in (self.context([]), self.context([camera]), self.context([Object()], mode="EDIT_MESH")):
            with self.assertRaises(ValueError):
                exporter.export_selection(context, self.root)
        self.assertFalse((self.root / "jobs").exists())

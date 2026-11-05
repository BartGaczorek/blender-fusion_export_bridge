"""Run with Blender --background --factory-startup --python tools/blender_smoke.py.

Build first: python tools/build.py. This test touches only a temporary scene/process.
"""
from pathlib import Path
import struct
import sys
import tempfile

import bpy
from mathutils import Euler, Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build"))
import blender_fusion_bridge as addon
from blender_fusion_bridge.exporter import export_selection
from blender_fusion_bridge import bridge_protocol as protocol


def bounds(path):
    raw = path.read_bytes()
    count = struct.unpack_from("<I", raw, 80)[0]
    vertices = []
    for i in range(count):
        record = struct.unpack_from("<12fH", raw, 84 + 50*i)
        vertices.extend((record[3:6], record[6:9], record[9:12]))
    return tuple(min(v[i] for v in vertices) for i in range(3)), tuple(max(v[i] for v in vertices) for i in range(3))


addon.register()
try:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 0.001
    bpy.ops.mesh.primitive_cube_add(size=2)
    cube = bpy.context.object
    cube.name = "Łącznik testowy"
    cube.location = (10, 20, 30)
    cube.scale = (-5, 10, 15)
    bpy.context.view_layer.update()
    before_matrix = cube.matrix_world.copy()
    with tempfile.TemporaryDirectory() as temporary:
        folder, count = export_selection(bpy.context, Path(temporary))
        assert count == 12, count
        assert bounds(folder / "mesh_0000.stl") == ((5, 10, 15), (15, 30, 45))
        assert cube.matrix_world == before_matrix
        modifier = cube.modifiers.new("Bevel test", "BEVEL")
        modifier.width = 0.1
        modifier.segments = 2
        folder, count = export_selection(bpy.context, Path(temporary))
        assert count > 12, count
        assert len(cube.modifiers) == 1
        protocol.validate_job(folder, protocol.read_json(folder / "ready.json"))
        cube.modifiers.remove(modifier)
        cube.rotation_euler = (0, 0, 1.5707963267948966)
        bpy.context.view_layer.update()
        folder, _ = export_selection(bpy.context, Path(temporary))
        lo, hi = bounds(folder / "mesh_0000.stl")
        assert all(abs(a-b) < 0.0001 for a, b in zip(lo + hi, (0, 15, 15, 20, 25, 45)))
    print("BLENDER BRIDGE SMOKE TEST PASSED", bpy.app.version_string)
finally:
    addon.unregister()

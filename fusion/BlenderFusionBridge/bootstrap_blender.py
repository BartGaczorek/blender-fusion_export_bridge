"""Executed by Blender --python when Fusion opens a new Blender window."""
from pathlib import Path
import sys
import bpy

# The Windows kit embeds the same add-on for first-launch support, even if no
# Blender add-on has been enabled yet. No user preference or startup file is saved.
existing = sys.modules.get("blender_fusion_bridge")
if existing and getattr(existing, "bl_info", {}).get("version", (0,)) < (0, 2, 0):
    if hasattr(bpy.types.Scene, "bfb_units"):
        existing.unregister()
    for name in list(sys.modules):
        if name == "blender_fusion_bridge" or name.startswith("blender_fusion_bridge."):
            del sys.modules[name]
    existing = None
if existing is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import blender_fusion_bridge as existing
if not hasattr(bpy.types.Scene, "bfb_target"):
    existing.register()

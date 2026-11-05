"""Blender reloads the package entry point, but can retain older child modules."""
import importlib
import sys

DEPENDENCIES = ('bridge_protocol', 'stl_writer', 'job_runner', 'stl_reader', 'exporter', 'receiver')


def reload_dependencies(package):
    importlib.invalidate_caches()
    modules = {}
    for name in DEPENDENCIES:
        fullname = package + '.' + name
        if fullname in sys.modules:
            modules[name] = importlib.reload(sys.modules[fullname])
        else:
            modules[name] = importlib.import_module('.' + name, package)
    return modules


def cleanup(namespace, bpy):
    """Also works after a partially failed register(). Stop IO before reloading."""
    receiver = namespace.get('receiver')
    if receiver is not None:
        receiver.stop()
    redraw = namespace.get('_redraw')
    if redraw is not None and bpy.app.timers.is_registered(redraw):
        bpy.app.timers.unregister(redraw)
    menu = namespace.get('_export_menu')
    if menu is not None:
        try:
            bpy.types.TOPBAR_MT_file_export.remove(menu)
        except (ValueError, RuntimeError):
            pass  # Menu was not registered (or was already removed by Blender).
    for name in ('bfb_target', 'bfb_units'):
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)
    for cls in reversed(namespace.get('_classes', ())):
        if getattr(cls, 'is_registered', False):
            bpy.utils.unregister_class(cls)

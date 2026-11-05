import importlib.util
import sys
import tempfile
from pathlib import Path
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

path = Path(__file__).resolve().parents[1]/'blender/blender_fusion_bridge/module_loader.py'
spec = importlib.util.spec_from_file_location('loader_under_test', path)
loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loader)


class ModuleReloadTests(unittest.TestCase):
    def test_upgrade_reloads_stale_protocol_and_dependent_function_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = ModuleType('upgrade_test')
            package.__path__ = [str(root)]
            (root/'bridge_protocol.py').write_text('PROTOCOL_VERSION = 1\n')
            (root/'exporter.py').write_text('from .bridge_protocol import PROTOCOL_VERSION\n')
            with patch.dict(sys.modules, {'upgrade_test':package}), \
                    patch.object(loader, 'DEPENDENCIES', ('bridge_protocol', 'exporter')):
                first = loader.reload_dependencies('upgrade_test')
                self.assertFalse(hasattr(first['bridge_protocol'], 'channel_root'))
                (root/'bridge_protocol.py').write_text('PROTOCOL_VERSION = 2\ndef channel_root(channel):\n    return channel\n')
                upgraded = loader.reload_dependencies('upgrade_test')
                self.assertEqual(upgraded['bridge_protocol'].channel_root('fusion'), 'fusion')
                self.assertEqual(upgraded['exporter'].PROTOCOL_VERSION, 2)
                self.assertIs(first['bridge_protocol'], upgraded['bridge_protocol'])

    def test_partial_registration_cleanup_is_repeatable_and_stops_receiver_first(self):
        events = []
        scene = type('Scene', (), {'bfb_target':1})
        cls = NS(is_registered=True)
        active_timers = { 'timer' }
        def unreg(c):
            events.append('class')
            c.is_registered=False
        bpy = NS(types=NS(Scene=scene, TOPBAR_MT_file_export=NS(remove=Mock(side_effect=ValueError))),
                 app=NS(timers=NS(is_registered=lambda t:t in active_timers, unregister=active_timers.remove)),
                 utils=NS(unregister_class=unreg))
        ns={'receiver':NS(stop=lambda:events.append('receiver')), '_redraw':'timer',
            '_export_menu':'menu', '_classes':[cls, NS(is_registered=False)]}
        loader.cleanup(ns, bpy)
        loader.cleanup(ns, bpy)
        self.assertEqual(events, ['receiver','class','receiver'])
        self.assertFalse(hasattr(scene,'bfb_target'))
        self.assertFalse(active_timers)

import importlib.util
from pathlib import Path
import re
import sys
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
from common import bridge_protocol


class FusionCommandTests(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1]/'fusion/BlenderFusionBridge'
        adsk = ModuleType('adsk')
        adsk.core = ModuleType('adsk.core')
        adsk.fusion = ModuleType('adsk.fusion')
        for name in ('CommandEventHandler','CommandCreatedEventHandler'):
            setattr(adsk.core, name, type(name, (), {}))
        package = ModuleType('command_test')
        package.__path__ = [str(base)]
        exporter = NS(selected_bodies=Mock(), export_bodies=Mock())
        launcher = NS(ensure_blender=Mock())
        self.patch = patch.dict(sys.modules, {'adsk':adsk,'adsk.core':adsk.core,'adsk.fusion':adsk.fusion,
            'command_test':package,'command_test.bridge_protocol':bridge_protocol,
            'command_test.exporter':exporter,'command_test.launcher':launcher})
        self.patch.start()
        self.addCleanup(self.patch.stop)
        spec=importlib.util.spec_from_file_location('command_test.commands',base/'commands.py')
        self.module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.definition=NS(isValid=True,deleteMe=Mock(),commandCreated=NS(add=Mock()))
        self.control=NS(isValid=True,deleteMe=Mock(),isPromoted=False,isPromotedByDefault=False)
        self.controls=NS(itemById=Mock(return_value=None),addCommand=Mock(return_value=self.control))
        self.defs=NS(itemById=Mock(return_value=None),addButtonDefinition=Mock(side_effect=self.add_definition))
        self.runtime=NS(app=NS(userInterface=NS(commandDefinitions=self.defs,
            allToolbarPanels=NS(itemById=Mock(return_value=NS(controls=self.controls))))))

    def add_definition(self, identifier, *args):
        # Autodesk API contract: dots are NOT permitted in command definition IDs.
        if not re.fullmatch('[A-Za-z0-9_]+',identifier):
            raise RuntimeError('3 : invalid id')
        return self.definition

    def test_id_contract_and_promoted_button(self):
        with self.assertRaisesRegex(RuntimeError,'invalid id'):
            self.add_definition('BartGaczorek.BlenderFusionBridge.SendToBlender.v2')
        handles=self.module.install(self.runtime)
        self.assertIs(handles[0],self.definition)
        self.assertTrue(self.control.isPromoted)
        self.assertTrue(self.control.isPromotedByDefault)
        self.controls.addCommand.assert_called_once_with(self.definition)

    def test_failed_control_creation_removes_definition(self):
        self.controls.addCommand.side_effect=RuntimeError('UI unavailable')
        with self.assertRaisesRegex(RuntimeError,'Rejestracja przycisku'):
            self.module.install(self.runtime)
        self.definition.deleteMe.assert_called_once()

    def test_restart_removes_our_stale_control_and_definition(self):
        old_control=NS(deleteMe=Mock())
        old_definition=NS(deleteMe=Mock())
        self.controls.itemById.return_value=old_control
        self.defs.itemById.return_value=old_definition
        self.module.install(self.runtime)
        old_control.deleteMe.assert_called_once()
        old_definition.deleteMe.assert_called_once()
        self.defs.itemById.assert_called_once_with(self.module.COMMAND_ID)

    def test_missing_panel_creates_nothing(self):
        self.runtime.app.userInterface.allToolbarPanels.itemById.return_value=None
        with self.assertRaisesRegex(RuntimeError,'panelu'):
            self.module.install(self.runtime)
        self.defs.addButtonDefinition.assert_not_called()

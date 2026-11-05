import adsk.core
import adsk.fusion
from . import bridge_protocol as protocol
from .exporter import selected_bodies, export_bodies
from .launcher import ensure_blender

COMMAND_ID = 'BartGaczorek_BlenderFusionBridge_SendToBlender_v2'


class Execute(adsk.core.CommandEventHandler):
    def __init__(self, runtime, entities):
        super().__init__()
        self.runtime, self.entities = runtime, entities

    def notify(self, args):
        app = self.runtime.app
        try:
            design = adsk.fusion.Design.cast(app.activeProduct)
            if not design:
                raise ValueError('Przejdź do dokumentu Design.')
            selection = args.command.commandInputs.itemById("bridgeBodies")
            entities = [selection.selection(i).entity for i in range(selection.selectionCount)]
            bodies = selected_bodies(entities)
            root = protocol.channel_root('blender')
            folder = export_bodies(root, bodies, app.activeDocument.name)
            self.runtime.outgoing.append(folder)
            try:
                message = ensure_blender(root, app.userInterface)
            except Exception as exc:
                message = 'Model zapisany w kolejce. ' + str(exc)
                app.userInterface.messageBox(message)
            app.userInterface.palettes.itemById('TextCommands').writeText(message)
        except Exception as exc:
            app.userInterface.messageBox('Blender Fusion Bridge: ' + str(exc))


class Created(adsk.core.CommandCreatedEventHandler):
    def __init__(self, runtime):
        super().__init__()
        self.runtime = runtime
        self.active_handlers = []

    def notify(self, args):
        selection = args.command.commandInputs.addSelectionInput(
            'bridgeBodies', 'Ciała', 'Wybierz ciała Mesh, bryły lub powierzchnie')
        for selection_filter in ('MeshBodies', 'SolidBodies', 'SurfaceBodies'):
            selection.addSelectionFilter(selection_filter)
        selection.setSelectionLimits(1, 0)
        # Fusion automatically carries compatible pre-selections into this input.
        execute = Execute(self.runtime, [])
        cleanup = Destroyed(self, execute)
        self.active_handlers.extend([execute, cleanup])
        args.command.execute.add(execute)
        args.command.destroy.add(cleanup)


class Destroyed(adsk.core.CommandEventHandler):
    def __init__(self, owner, execute):
        super().__init__()
        self.owner, self.execute = owner, execute

    def notify(self, args):
        for handler in (self.execute, self):
            if handler in self.owner.active_handlers:
                self.owner.active_handlers.remove(handler)


def install(runtime):
    ui = runtime.app.userInterface
    panel = ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
    if not panel:
        raise RuntimeError('Nie znaleziono panelu dodatków w Fusion Design.')
    # Remove only our own leftover UI after a partially failed earlier start.
    old_control = panel.controls.itemById(COMMAND_ID)
    if old_control:
        old_control.deleteMe()
    old_definition = ui.commandDefinitions.itemById(COMMAND_ID)
    if old_definition:
        old_definition.deleteMe()
    definition = None
    control = None
    try:
        definition = ui.commandDefinitions.addButtonDefinition(
            COMMAND_ID, 'Wyślij do Blendera', 'Wyślij zaznaczone ciała Mesh, BRep lub powierzchniowe do Blendera')
        handler = Created(runtime)
        definition.commandCreated.add(handler)
        control = panel.controls.addCommand(definition)
        control.isPromotedByDefault = True
        control.isPromoted = True
        return definition, handler, control
    except Exception as exc:
        for item in (control, definition):
            if item and item.isValid:
                item.deleteMe()
        raise RuntimeError('Rejestracja przycisku Wyślij do Blendera: ' + str(exc)) from exc


def uninstall(handles):
    if handles:
        definition, handler, control = handles
        if control.isValid:
            control.deleteMe()
        if definition.isValid:
            definition.deleteMe()

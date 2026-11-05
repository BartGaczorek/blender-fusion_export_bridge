bl_info = {
    "name": "Blender → Fusion Bridge", "author": "BartGaczorek",
    "version": (0, 1, 0), "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Fusion", "category": "Import-Export",
    "description": "Wyślij zaznaczone modele do Autodesk Fusion na Windows",
}

import os
from pathlib import Path

import bpy
from bpy.props import EnumProperty, StringProperty

from . import bridge_protocol as protocol
from .exporter import export_selection

_last_folder = None
_last_message = ""


class BFBPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    fusion_launcher: StringProperty(
        name="Skrót lub program Fusion", subtype="FILE_PATH",
        description="Opcjonalny .lnk lub .exe; uruchamiany po eksporcie, gdy odbiornik jest wyłączony")

    def draw(self, context):
        self.layout.label(text="Windows • lokalny transfer • siatki STL w milimetrach")
        self.layout.prop(self, "fusion_launcher")
        self.layout.label(text="Puste pole: uruchom Fusion samodzielnie.")


class BFB_OT_send(bpy.types.Operator):
    bl_idname = "export_mesh.send_to_fusion"
    bl_label = "Wyślij do Fusion"
    bl_description = "Wyślij zaznaczone obiekty po modyfikatorach do nowego dokumentu Fusion"

    @classmethod
    def poll(cls, context):
        return os.name == "nt" and context.mode == "OBJECT" and bool(context.selected_objects)

    def execute(self, context):
        global _last_folder, _last_message
        context.window_manager.progress_begin(0, 100)
        try:
            root = protocol.bridge_root()
            folder, count = export_selection(context, root, context.scene.bfb_units)
            _last_folder = folder
            _last_message = "W kolejce: {:,} trójkątów".format(count)
        except Exception as exc:
            _last_message = "Błąd eksportu: " + str(exc)
            self.report({"ERROR"}, _last_message)
            return {"CANCELLED"}
        finally:
            context.window_manager.progress_end()
        if protocol.receiver_status(root) == "offline":
            prefs = context.preferences.addons[__package__].preferences
            launcher = bpy.path.abspath(prefs.fusion_launcher) if prefs.fusion_launcher else ""
            if launcher:
                try:
                    path = Path(launcher)
                    if path.suffix.lower() not in {".exe", ".lnk"} or not path.is_file():
                        raise ValueError("Wskaż istniejący skrót .lnk lub program .exe w ustawieniach dodatku.")
                    os.startfile(str(path))
                except Exception as exc:
                    self.report({"WARNING"}, "Eksport czeka w kolejce. Nie uruchomiono Fusion: " + str(exc))
                    return {"FINISHED"}
            _last_message = "W kolejce — uruchom Fusion i odbiornik."
        self.report({"INFO"}, _last_message)
        return {"FINISHED"}


class BFB_OT_open_queue(bpy.types.Operator):
    bl_idname = "wm.bfb_open_queue"
    bl_label = "Otwórz folder transferów"

    def execute(self, context):
        try:
            root = protocol.bridge_root()
            root.mkdir(parents=True, exist_ok=True)
            os.startfile(str(root))
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        return {"FINISHED"}


class BFB_PT_panel(bpy.types.Panel):
    bl_label = "Blender → Fusion"
    bl_idname = "BFB_PT_bridge"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Fusion"

    def draw(self, context):
        layout = self.layout
        if os.name != "nt":
            layout.label(text="Dodatek wymaga Windows.", icon="ERROR")
            return
        try:
            root = protocol.bridge_root()
            receiver = protocol.receiver_status(root)
            labels = {"ready": "Fusion: gotowy", "busy": "Fusion: zakończ aktywne polecenie",
                      "importing": "Fusion: importuje", "offline": "Fusion: odbiornik wyłączony"}
            layout.label(text=labels.get(receiver, receiver), icon="LINKED" if receiver != "offline" else "UNLINKED")
            layout.prop(context.scene, "bfb_units", text="Jednostki")
            scale = protocol.millimeters_per_unit(context.scene.bfb_units, context.scene.unit_settings.scale_length)
            layout.label(text="1 jednostka Blendera = {:g} mm".format(scale))
            button = layout.row()
            button.scale_y = 1.6
            button.operator(BFB_OT_send.bl_idname, icon="EXPORT")
            layout.label(text="Nowy dokument • osobne siatki • Z w górę")
            layout.label(text="Bez materiałów i historii CAD")
            if context.mode != "OBJECT":
                layout.label(text="Przejdź do Object Mode.", icon="INFO")
            if _last_folder:
                try:
                    status = protocol.read_json(_last_folder / "status.json")
                    states = {"queued": "W kolejce", "processing": "Importowanie", "done": "Zaimportowano",
                              "error": "Błąd importu", "uncertain": "Import przerwany"}
                    box = layout.box()
                    box.label(text=states.get(status["state"], status["state"]))
                    # Multiple short lines keep errors readable in a narrow sidebar.
                    import textwrap
                    for line in textwrap.wrap(status.get("message", ""), width=38):
                        box.label(text=line)
                except (OSError, ValueError, KeyError):
                    layout.label(text=_last_message)
            elif _last_message:
                layout.label(text=_last_message)
            layout.operator(BFB_OT_open_queue.bl_idname, icon="FILE_FOLDER")
        except Exception as exc:
            layout.label(text=str(exc), icon="ERROR")


def _redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
    return 1.0


def _export_menu(self, context):
    self.layout.operator(BFB_OT_send.bl_idname, text="Wyślij do Fusion")


_classes = (BFBPreferences, BFB_OT_send, BFB_OT_open_queue, BFB_PT_panel)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.bfb_units = EnumProperty(
        name="Jednostki", default="SCENE", items=[
            ("SCENE", "Ze sceny", "1 BU = Unit Scale × 1000 mm, także przy Unit System=None"),
            ("MM", "1 BU = 1 mm", "Dla modeli tworzonych w umownych milimetrach"),
            ("CM", "1 BU = 1 cm", "Jeden BU to 10 mm"),
            ("M", "1 BU = 1 m", "Jeden BU to 1000 mm"),
            ("INCH", "1 BU = 1 cal", "Jeden BU to 25,4 mm")])
    bpy.types.TOPBAR_MT_file_export.append(_export_menu)
    bpy.app.timers.register(_redraw, first_interval=1.0, persistent=True)


def unregister():
    if bpy.app.timers.is_registered(_redraw):
        bpy.app.timers.unregister(_redraw)
    bpy.types.TOPBAR_MT_file_export.remove(_export_menu)
    del bpy.types.Scene.bfb_units
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)

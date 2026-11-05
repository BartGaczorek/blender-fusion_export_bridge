"""Read evaluated geometry without changing objects, selection or modifier stacks."""
import shutil

from . import bridge_protocol as protocol
from .stl_writer import write_binary_stl

SUPPORTED_TYPES = {"MESH", "CURVE", "SURFACE", "FONT"}


def export_selection(context, root, mode="SCENE", target="NEW", target_document=None):
    if context.mode != "OBJECT":
        raise ValueError("Przejdź do Object Mode przed wysłaniem modelu.")
    objects = list(context.selected_objects)
    if not objects:
        raise ValueError("Zaznacz przynajmniej jeden obiekt.")
    unsupported = [obj.name for obj in objects if obj.type not in SUPPORTED_TYPES]
    if unsupported:
        raise ValueError("Zaznaczenie zawiera nieobsługiwane obiekty: " + ", ".join(unsupported[:5]))
    if len(objects) > protocol.MAX_OBJECTS:
        raise ValueError("Jednorazowo można wysłać maksymalnie 500 obiektów.")
    scale = protocol.millimeters_per_unit(mode, context.scene.unit_settings.scale_length)
    depsgraph = context.evaluated_depsgraph_get()
    folder = protocol.create_job(root)
    records = []
    total = 0
    try:
        for index, obj in enumerate(objects):
            evaluated = obj.evaluated_get(depsgraph)
            try:
                mesh = evaluated.to_mesh()
                if mesh is None:
                    raise ValueError("Nie można odczytać siatki: " + obj.name)
                mesh.calc_loop_triangles()
                total += len(mesh.loop_triangles)
                if total > protocol.MAX_TRIANGLES:
                    raise ValueError("Limit 5 mln trójkątów. Zmniejsz siatkę lub zaznaczenie.")
                matrix = evaluated.matrix_world.copy()
                mirrored = matrix.to_3x3().determinant() < 0

                def triangles():
                    for triangle in mesh.loop_triangles:
                        ids = tuple(triangle.vertices)
                        if mirrored:
                            ids = (ids[0], ids[2], ids[1])
                        yield tuple(tuple((matrix @ mesh.vertices[i].co) * scale) for i in ids)

                filename = "mesh_{:04d}.stl".format(index)
                count = write_binary_stl(folder / filename, triangles())
                records.append({"name": obj.name[:120], "file": filename,
                                "triangles": count, "sha256": protocol.digest(folder / filename)})
            finally:
                evaluated.to_mesh_clear()
        name = objects[0].name if len(objects) == 1 else "Blender - {} obiektów".format(len(objects))
        protocol.publish_job(folder, name, records, target, target_document)
        return folder, total
    except Exception:
        # No commit marker exists on failures; Fusion cannot see partial exports.
        shutil.rmtree(folder, ignore_errors=True)
        raise

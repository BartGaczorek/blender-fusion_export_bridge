"""Fusion API adapter. All calls must run on Fusion's main thread."""
import adsk.core
import adsk.fusion


def import_meshes(app, folder, manifest):
    previous = app.activeDocument
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    if not document:
        raise RuntimeError("Fusion nie utworzył nowego dokumentu.")
    try:
        document.name = manifest["name"]
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            raise RuntimeError("Nowy dokument nie jest projektem Fusion Design.")
        total = 0
        for obj in manifest["objects"]:
            # Explicit mm prevents the cm internal unit from changing the scale.
            bodies = design.rootComponent.meshBodies.add(
                str(folder / obj["file"]), adsk.fusion.MeshUnits.MillimeterMeshUnit)
            if not bodies or bodies.count != 1:
                raise RuntimeError("Nie udało się zaimportować siatki: " + obj["name"])
            bodies.item(0).name = obj["name"]
            total += 1
    except Exception as exc:
        # Roll back only the new, unsaved document created by this transfer.
        try:
            if not document.close(False):
                raise RuntimeError("Fusion odmówił zamknięcia dokumentu.")
            if previous and previous.isValid:
                previous.activate()
        except Exception as cleanup_error:
            raise RuntimeError(str(exc) + " Pozostał częściowy dokument: " + str(cleanup_error)) from exc
        raise
    try:
        app.activeViewport.fit()
    except Exception:
        pass  # View fitting is cosmetic; the import itself has succeeded.
    return {"document": document.name, "objects": total}

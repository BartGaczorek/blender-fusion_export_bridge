"""Fusion API adapter; main thread only. Existing documents are never closed."""
import adsk.core
import adsk.fusion


def import_meshes(app, folder, manifest, document_token=None):
    if manifest.get("target", "NEW") not in {"NEW", "ACTIVE"}:
        raise ValueError("Nieprawidłowy kanał transferu Fusion.")
    previous = app.activeDocument
    active = manifest.get("target", "NEW") == "ACTIVE"
    if active:
        if not document_token or manifest.get("target_document") != document_token:
            raise RuntimeError("Dokument Fusion zmienił się po wysłaniu. Wybierz właściwy dokument i wyślij ponownie.")
        document = previous
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not document or not design:
            raise RuntimeError("Otwórz dokument Design w Fusion.")
    else:
        document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        if not document:
            raise RuntimeError("Fusion nie utworzył nowego dokumentu.")
        design = adsk.fusion.Design.cast(app.activeProduct)
    created = []
    try:
        if not active:
            document.name = manifest["name"]
        if not design:
            raise RuntimeError("Dokument nie jest projektem Fusion Design.")
        for obj in manifest["objects"]:
            bodies = design.rootComponent.meshBodies.add(
                str(folder / obj["file"]), adsk.fusion.MeshUnits.MillimeterMeshUnit)
            if bodies:
                created.extend(bodies.item(i) for i in range(bodies.count))
            if not bodies or bodies.count != 1:
                raise RuntimeError("Nie udało się zaimportować siatki: " + obj["name"])
            bodies.item(0).name = obj["name"]
    except Exception as exc:
        try:
            if active:
                for body in reversed(created):
                    if body.isValid and not body.deleteMe():
                        raise RuntimeError("Nie usunięto części importu.")
            else:
                if not document.close(False):
                    raise RuntimeError("Fusion odmówił zamknięcia dokumentu.")
                if previous and previous.isValid:
                    previous.activate()
        except Exception as cleanup_error:
            raise RuntimeError(str(exc) + " Pozostał częściowy dokument/import: " + str(cleanup_error)) from exc
        raise
    try:
        app.activeViewport.fit()
    except Exception:
        pass
    return {"document": document.name, "objects": len(created), "target": "ACTIVE" if active else "NEW"}

"""One job at a time; the caller must hold ReceiverLock and run on Fusion's UI thread."""
import os
from . import bridge_protocol as protocol


def process_job(folder, importer):
    if not protocol.claim_job(folder):
        return False
    try:
        manifest = protocol.validate_job(folder, protocol.read_json(folder / "processing.json"))
        protocol.write_status(folder, "processing", "Importowanie modeli…")
        result = importer(folder, manifest)
    except Exception as exc:
        protocol.write_status(folder, "error", str(exc))
    else:
        protocol.write_status(folder, "done", "Import zakończony.", result=result)
    # If writing the outcome fails, retain processing.json for recovery on restart.
    os.replace(folder / "processing.json", folder / "finished.json")
    return True

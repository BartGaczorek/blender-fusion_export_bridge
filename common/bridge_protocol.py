"""Versioned on-disk transport. No Blender/Fusion imports or network services."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import time
import uuid

PROTOCOL_VERSION = 2
MAX_TRIANGLES = 5_000_000
MAX_OBJECTS = 500
MAX_JSON_BYTES = 1_000_000
JOB_PATTERN = re.compile(r"^[0-9a-f]{32}$")
FILE_PATTERN = re.compile(r"^mesh_[0-9]{4}\.stl$")


def bridge_root():
    if os.name != "nt":
        raise RuntimeError("Blender Fusion Bridge obsługuje wyłącznie Windows.")
    return Path(os.environ["LOCALAPPDATA"]) / "BlenderFusionBridge"


def atomic_json(path, value):
    path = Path(path)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        # Windows readers can briefly deny replacing an open status file.
        for attempt in range(8):
            try:
                os.replace(temp, path)
                break
            except PermissionError:
                if attempt == 7:
                    raise
                time.sleep(0.025)
    finally:
        temp.unlink(missing_ok=True)


def read_json(path):
    path = Path(path)
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError("Plik metadanych jest zbyt duży.")
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def digest(path):
    sha = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def millimeters_per_unit(mode, scene_scale):
    value = {"MM": 1.0, "CM": 10.0, "M": 1000.0, "INCH": 25.4}.get(mode)
    if mode == "SCENE":
        value = float(scene_scale) * 1000.0
    if value is None or not math.isfinite(value) or value <= 0:
        raise ValueError("Nieprawidłowa skala jednostek.")
    return value


def create_job(root):
    job_id = uuid.uuid4().hex
    folder = Path(root) / "jobs" / job_id
    folder.mkdir(parents=True)
    return folder


def publish_job(folder, name, objects, target="NEW", target_document=None):
    """ready.json is the commit marker, published only after every STL is closed."""
    manifest = {
        "protocol": PROTOCOL_VERSION, "job_id": folder.name,
        "created_at": time.time(), "name": name[:120],
        "units": "mm", "axes": "XYZ_Z_UP", "objects": objects,
        "target": target, "target_document": target_document,
    }
    validate_job(folder, manifest)
    write_status(folder, "queued", "Oczekuje na odbiornik.")
    atomic_json(folder / "ready.json", manifest)
    return manifest


def validate_job(folder, manifest):
    folder = Path(folder).resolve()
    if not isinstance(manifest, dict):
        raise ValueError("Nieprawidłowy manifest.")
    if manifest.get("protocol") != PROTOCOL_VERSION:
        raise ValueError("Niezgodna wersja protokołu. Zaktualizuj oba dodatki.")
    if not JOB_PATTERN.fullmatch(folder.name) or manifest.get("job_id") != folder.name:
        raise ValueError("Nieprawidłowy identyfikator eksportu.")
    if manifest.get("units") != "mm" or manifest.get("axes") != "XYZ_Z_UP":
        raise ValueError("Nieobsługiwane jednostki lub osie.")
    if not isinstance(manifest.get("name"), str) or not 1 <= len(manifest["name"]) <= 120:
        raise ValueError("Nieprawidłowa nazwa dokumentu.")
    if manifest.get("target", "NEW") not in {"NEW", "ACTIVE", "BLENDER"}:
        raise ValueError("Nieznany cel transferu.")
    if manifest.get("target") == "ACTIVE" and not isinstance(manifest.get("target_document"), str):
        raise ValueError("Brak identyfikatora dokumentu docelowego.")
    objects = manifest.get("objects")
    if not isinstance(objects, list) or not 1 <= len(objects) <= MAX_OBJECTS:
        raise ValueError("Eksport musi zawierać od 1 do 500 obiektów.")
    total = 0
    seen = set()
    for obj in objects:
        if not isinstance(obj, dict):
            raise ValueError("Nieprawidłowe dane obiektu.")
        filename = obj.get("file", "")
        if not isinstance(filename, str) or not FILE_PATTERN.fullmatch(filename) or filename in seen:
            raise ValueError("Nieprawidłowa lub powtórzona nazwa pliku STL.")
        seen.add(filename)
        path = folder / filename
        if path.is_symlink() or path.resolve().parent != folder:
            raise ValueError("Plik STL znajduje się poza eksportem.")
        triangles = obj.get("triangles")
        if type(triangles) is not int or not 1 <= triangles <= MAX_TRIANGLES:
            raise ValueError("Nieprawidłowa liczba trójkątów.")
        total += triangles
        if total > MAX_TRIANGLES:
            raise ValueError("Eksport przekracza limit 5 mln trójkątów.")
        if not isinstance(obj.get("name"), str) or not 1 <= len(obj["name"]) <= 120:
            raise ValueError("Nieprawidłowa nazwa obiektu.")
        if path.stat().st_size != 84 + 50 * triangles:
            raise ValueError("Niepełny plik STL: " + filename)
        with path.open("rb") as stream:
            stream.seek(80)
            if struct.unpack("<I", stream.read(4))[0] != triangles:
                raise ValueError("Nagłówek STL nie zgadza się z manifestem.")
        if digest(path) != obj.get("sha256"):
            raise ValueError("Suma kontrolna STL nie zgadza się: " + filename)
    return manifest


def write_status(folder, state, message, **details):
    atomic_json(Path(folder) / "status.json", {
        "state": state, "message": str(message)[:2000],
        "updated_at": time.time(), **details,
    })


def pending_jobs(root):
    jobs = Path(root) / "jobs"
    if not jobs.exists():
        return []
    return sorted((p.parent for p in jobs.glob("*/ready.json")
                   if JOB_PATTERN.fullmatch(p.parent.name) and not p.parent.is_symlink()),
                  key=lambda p: (p / "ready.json").stat().st_mtime)


def claim_job(folder):
    """Only the single locked receiver calls this. Never automatically replay."""
    folder = Path(folder)
    if (folder / "processing.json").exists():
        return False
    try:
        os.rename(folder / "ready.json", folder / "processing.json")
    except FileNotFoundError:
        return False
    return True


def recover_interrupted(root):
    jobs = Path(root) / "jobs"
    for marker in jobs.glob("*/processing.json"):
        if not JOB_PATTERN.fullmatch(marker.parent.name) or marker.parent.is_symlink():
            continue
        try:
            state = read_json(marker.parent / "status.json").get("state")
        except (OSError, ValueError):
            state = None
        if state not in {"done", "error"}:
            write_status(marker.parent, "uncertain",
                         "Odbiornik przerwał import. Sprawdź dokumenty i wyślij ponownie, jeśli potrzeba.")
        os.replace(marker, marker.with_name("finished.json"))


def receiver_status(root):
    try:
        status = read_json(Path(root) / "receiver.json")
        if 0 <= time.time() - status["updated_at"] < 8:
            return status["state"]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return "offline"


class ReceiverLock:
    """OS-owned lock released even if Fusion crashes. Windows only."""
    def __init__(self, root):
        self.root = Path(root)
        self.stream = None

    def acquire(self):
        import msvcrt
        self.root.mkdir(parents=True, exist_ok=True)
        stream = (self.root / "receiver.lock").open("a+b")
        try:
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except Exception:
            stream.close()
            raise RuntimeError("Odbiornik działa już w innej instancji Fusion.")
        self.stream = stream

    def release(self):
        if self.stream is not None:
            import msvcrt
            self.stream.seek(0)
            msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
            self.stream.close()
            self.stream = None


def channel_root(channel):
    if channel not in {"fusion", "blender"}:
        raise ValueError("Unknown channel")
    root = bridge_root() / "v2" / channel
    root.mkdir(parents=True, exist_ok=True)
    return root


def receiver_document(root):
    if receiver_status(root) == "offline":
        raise ValueError("Uruchom odbiornik 0.2.0 w Fusion i otwórz dokument Design.")
    info = read_json(Path(root) / "receiver.json")
    token = info.get("document_token")
    if info.get("protocol") != PROTOCOL_VERSION or not token:
        raise ValueError("Brak aktywnego dokumentu Fusion lub odbiornik ma starszą wersję.")
    return token

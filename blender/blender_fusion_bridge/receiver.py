"""Blender receiver runs on an app timer, never in a background bpy thread."""
import logging
import os
from pathlib import Path
import time
import bpy
from . import bridge_protocol as protocol
from .job_runner import process_job
from .stl_reader import indexed_mesh

_lock = None
_root = None
last_message = "wyłączony"


def import_meshes(folder, manifest):
    if manifest.get("target") != "BLENDER":
        raise ValueError("Nieprawidłowy kanał transferu.")
    scene = bpy.context.scene
    if scene is None:
        raise RuntimeError("Brak aktywnej sceny Blendera.")
    scale = protocol.millimeters_per_unit(getattr(scene, 'bfb_units', 'SCENE'), scene.unit_settings.scale_length)
    collection = bpy.data.collections.new("Fusion - " + manifest['name'])
    objects, meshes = [], []
    try:
        scene.collection.children.link(collection)
        for record in manifest['objects']:
            vertices, faces = indexed_mesh(folder / record['file'], scale)
            mesh = bpy.data.meshes.new(record['name'])
            meshes.append(mesh)
            mesh.from_pydata(vertices, [], faces)
            mesh.update()
            obj = bpy.data.objects.new(record['name'], mesh)
            objects.append(obj)
            collection.objects.link(obj)
    except Exception:
        for obj in objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in meshes:
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        bpy.data.collections.remove(collection)
        raise
    return {'scene': scene.name, 'objects': len(objects)}


def tick():
    global last_message
    if _lock is None:
        return None
    try:
        busy = bpy.context.mode != 'OBJECT' or bpy.app.is_job_running('RENDER')
        protocol.atomic_json(_root / 'receiver.json', {
            'protocol': protocol.PROTOCOL_VERSION, 'state': 'busy' if busy else 'ready',
            'updated_at': time.time(), 'pid': os.getpid()})
        if not busy:
            jobs = protocol.pending_jobs(_root)
            if jobs:
                process_job(jobs[0], import_meshes)
                last_message = protocol.read_json(jobs[0] / 'status.json')['message']
    except Exception as exc:
        last_message = str(exc)
        logging.getLogger(__name__).exception('Fusion import failed')
    return 1.0


def start():
    global _lock, _root, last_message
    if os.name != 'nt' or _lock:
        return
    _root = protocol.channel_root('blender')
    candidate = protocol.ReceiverLock(_root)
    try:
        candidate.acquire()
    except RuntimeError:
        last_message = 'aktywny w innym oknie/procesie Blendera'
        return
    _lock = candidate
    try:
        protocol.recover_interrupted(_root)
        protocol.atomic_json(_root / 'launcher.json', {'executable': bpy.app.binary_path})
        bpy.app.timers.register(tick, first_interval=1.0, persistent=True)
        last_message = 'gotowy'
    except Exception:
        stop()
        raise


def stop():
    global _lock, last_message
    if bpy.app.timers.is_registered(tick):
        bpy.app.timers.unregister(tick)
    if _lock:
        _lock.release()
        _lock = None
    last_message = 'wyłączony'

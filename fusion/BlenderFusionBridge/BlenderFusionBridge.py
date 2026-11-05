"""Windows Fusion receiver. Background IO only; modeling uses CustomEvent."""
import logging
from logging.handlers import RotatingFileHandler
import threading
import time

import adsk.core

from . import bridge_protocol as protocol
from .job_runner import process_job
from .importer import import_meshes

EVENT_ID = "BartGaczorek.BlenderFusionBridge.Receive.v1"
_runtime = None


class ReceiveHandler(adsk.core.CustomEventHandler):
    def __init__(self, runtime):
        super().__init__()
        self.runtime = runtime

    def notify(self, args):
        runtime = self.runtime
        try:
            if runtime.stop_event.is_set():
                return
            if runtime.app.userInterface.activeCommand not in ("", "SelectCommand"):
                runtime.state = "busy"
                return
            jobs = protocol.pending_jobs(runtime.root)
            if jobs:
                runtime.state = "importing"
                process_job(jobs[0], lambda folder, data: import_meshes(runtime.app, folder, data))
            runtime.state = "ready"
        except Exception:
            runtime.logger.exception("Receiver event failed")
        finally:
            runtime.pending.clear()


class Runtime:
    def __init__(self, app):
        self.app = app
        self.root = protocol.bridge_root()
        self.lock = protocol.ReceiverLock(self.root)
        self.stop_event = threading.Event()
        self.pending = threading.Event()
        self.state = "ready"
        self.event = None
        self.handler = None
        self.thread = None
        self.logger = logging.getLogger("BlenderFusionBridge")
        self.log_handler = None

    def start(self):
        self.lock.acquire()
        self.log_handler = RotatingFileHandler(self.root / "receiver.log", maxBytes=1_000_000,
                                              backupCount=2, encoding="utf-8")
        self.log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        self.logger.addHandler(self.log_handler)
        self.logger.setLevel(logging.INFO)
        protocol.recover_interrupted(self.root)
        self.event = self.app.registerCustomEvent(EVENT_ID)
        self.handler = ReceiveHandler(self)
        self.event.add(self.handler)
        self.thread = threading.Thread(target=self.watch, name="BlenderFusionBridge", daemon=True)
        self.thread.start()

    def watch(self):
        while not self.stop_event.is_set():
            try:
                protocol.atomic_json(self.root / "receiver.json", {
                    "state": self.state, "updated_at": time.time(), "protocol": protocol.PROTOCOL_VERSION})
                if not self.pending.is_set() and protocol.pending_jobs(self.root):
                    self.pending.set()
                    # The one Fusion API method documented for use from a worker.
                    if not self.app.fireCustomEvent(EVENT_ID):
                        self.pending.clear()
            except Exception:
                self.logger.exception("Queue watcher failed")
                self.pending.clear()
            self.stop_event.wait(1.0)

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=3)
            if self.thread.is_alive():
                raise RuntimeError("Odbiornik kończy operację IO. Spróbuj zatrzymać dodatek ponownie.")
        if self.event:
            self.event.remove(self.handler)
            self.app.unregisterCustomEvent(EVENT_ID)
            self.event = None
        if self.lock.stream:
            try:
                protocol.atomic_json(self.root / "receiver.json", {"state": "offline", "updated_at": time.time()})
            finally:
                self.lock.release()
        if self.log_handler:
            self.logger.removeHandler(self.log_handler)
            self.log_handler.close()
            self.log_handler = None


def run(context):
    global _runtime
    if _runtime:
        return
    app = adsk.core.Application.get()
    candidate = None
    try:
        candidate = Runtime(app)
        candidate.start()
        _runtime = candidate
    except Exception as exc:
        if candidate:
            candidate.stop()
        app.userInterface.messageBox("Blender Fusion Bridge: " + str(exc))


def stop(context):
    global _runtime
    if _runtime:
        _runtime.stop()
        _runtime = None

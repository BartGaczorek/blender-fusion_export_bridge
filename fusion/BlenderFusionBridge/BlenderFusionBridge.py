"""Windows Fusion receiver. Background IO only; modeling uses CustomEvent."""
import logging
from logging.handlers import RotatingFileHandler
import threading
import time
import uuid
import traceback
import adsk.fusion

import adsk.core

from . import bridge_protocol as protocol
from .job_runner import process_job
from .importer import import_meshes

EVENT_ID = "BartGaczorek.BlenderFusionBridge.Receive.v2"
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
            runtime.refresh_document()
            runtime.report_outgoing()
            if runtime.app.userInterface.activeCommand not in ("", "SelectCommand"):
                runtime.state = "busy"
                return
            jobs = protocol.pending_jobs(runtime.root)
            if jobs:
                runtime.state = "importing"
                process_job(jobs[0], lambda folder, data: import_meshes(runtime.app, folder, data, runtime.document_token))
            runtime.state = "ready"
        except Exception:
            runtime.logger.exception("Receiver event failed")
        finally:
            runtime.pending.clear()


class Runtime:
    def __init__(self, app):
        self.app = app
        self.root = protocol.channel_root("fusion")
        self.lock = protocol.ReceiverLock(self.root)
        self.stop_event = threading.Event()
        self.pending = threading.Event()
        self.state = "ready"
        self.event = None
        self.handler = None
        self.thread = None
        self.logger = logging.getLogger("BlenderFusionBridge")
        self.log_handler = None
        self.document = None
        self.document_token = None
        self.document_name = ""
        self.outgoing = []
        self.commands = None
        self.start_stage = "inicjalizacja"

    def refresh_document(self):
        document = self.app.activeDocument if adsk.fusion.Design.cast(self.app.activeProduct) else None
        if document != self.document:
            self.document = document
            self.document_token = uuid.uuid4().hex if document else None
        self.document_name = document.name if document else ""

    def report_outgoing(self):
        for folder in list(self.outgoing):
            status = protocol.read_json(folder / "status.json")
            if status['state'] in {'done', 'error', 'uncertain'}:
                self.outgoing.remove(folder)
                self.app.userInterface.palettes.itemById('TextCommands').writeText(
                    'Blender: ' + status['message'])
                if status['state'] != 'done':
                    self.app.userInterface.messageBox('Blender: ' + status['message'])

    def start(self):
        self.start_stage = "blokada odbiornika"
        self.lock.acquire()
        self.log_handler = RotatingFileHandler(self.root / "receiver.log", maxBytes=1_000_000,
                                              backupCount=2, encoding="utf-8")
        self.log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        self.logger.addHandler(self.log_handler)
        self.logger.setLevel(logging.INFO)
        self.start_stage = "odtwarzanie kolejki"
        protocol.recover_interrupted(self.root)
        self.start_stage = "rejestracja zdarzenia Fusion"
        self.event = self.app.registerCustomEvent(EVENT_ID)
        self.handler = ReceiveHandler(self)
        self.event.add(self.handler)
        self.start_stage = "odczyt dokumentu"
        self.refresh_document()
        self.start_stage = "rejestracja przycisku"
        from . import commands
        self.commands = commands.install(self)
        self.thread = threading.Thread(target=self.watch, name="BlenderFusionBridge", daemon=True)
        self.thread.start()

    def watch(self):
        while not self.stop_event.is_set():
            try:
                protocol.atomic_json(self.root / "receiver.json", {
                    "state": self.state, "updated_at": time.time(), "protocol": protocol.PROTOCOL_VERSION,
                    "document_token": self.document_token, "document_name": self.document_name})
                if not self.pending.is_set():
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
        if self.commands:
            from . import commands
            commands.uninstall(self.commands)
            self.commands = None
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
        details = traceback.format_exc()
        stage = candidate.start_stage if candidate else 'inicjalizacja'
        if candidate:
            candidate.logger.error('Startup failed at %s\n%s', stage, details)
            try:
                candidate.stop()
            except Exception:
                details += '\nCleanup: ' + traceback.format_exc()
        app.userInterface.messageBox(
            "Blender Fusion Bridge — " + stage + ": " + str(exc) + "\n\n" + details)


def stop(context):
    global _runtime
    if _runtime:
        _runtime.stop()
        _runtime = None

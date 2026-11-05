"""Start Blender only if no receiver (including a busy one) owns the OS lock."""
import csv
from pathlib import Path
import subprocess
import time
from . import bridge_protocol as protocol


def receiver_running(root):
    lock = protocol.ReceiverLock(root)
    try:
        lock.acquire()
    except RuntimeError:
        return True
    lock.release()
    return False


def process_running(executable):
    result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq ' + executable.name, '/FO', 'CSV', '/NH'],
                            capture_output=True, text=True, timeout=5, creationflags=0x08000000)
    if result.returncode:
        raise RuntimeError('Nie można sprawdzić, czy Blender jest uruchomiony.')
    return any(row and row[0].lower() == executable.name.lower() for row in csv.reader(result.stdout.splitlines()))


def resolve_executable(root, ui):
    try:
        path = Path(protocol.read_json(root / 'launcher.json')['executable'])
        if path.is_file() and path.suffix.lower() == '.exe':
            return path
    except (OSError, ValueError, KeyError, TypeError):
        pass
    dialog = ui.createFileDialog()
    dialog.title = 'Wskaż blender.exe (tylko przy pierwszym uruchomieniu)'
    dialog.filter = 'Blender (blender.exe)'
    import adsk.core
    if dialog.showOpen() != adsk.core.DialogResults.DialogOK:
        raise ValueError('Nie wskazano Blendera. Transfer pozostaje w kolejce.')
    path = Path(dialog.filename)
    if not path.is_file() or path.suffix.lower() != '.exe':
        raise ValueError('Wskaż plik blender.exe.')
    protocol.atomic_json(root / 'launcher.json', {'executable': str(path)})
    return path


def ensure_blender(root, ui):
    if receiver_running(root):
        return 'Oczekuje na otwartą scenę Blendera.'
    path = resolve_executable(root, ui)
    startup_lock = protocol.ReceiverLock(root / 'startup')
    startup_lock.acquire()
    try:
        if receiver_running(root):
            return 'Oczekuje na otwartą scenę Blendera.'
        if process_running(path):
            return 'Blender działa. Jeśli import nie ruszy, włącz dodatek 0.2.0 w otwartym Blenderze.'
        try:
            launched = protocol.read_json(root / 'launching.json')['time']
        except (OSError, ValueError, KeyError):
            launched = 0
        if 0 <= time.time() - launched < 30:
            return 'Oczekiwanie na uruchomienie Blendera.'
        bootstrap = Path(__file__).with_name('bootstrap_blender.py')
        subprocess.Popen([str(path), '--python', str(bootstrap)], shell=False)
        protocol.atomic_json(root / 'launching.json', {'time': time.time()})
        return 'Uruchamianie Blendera; transfer czeka w kolejce.'
    finally:
        startup_lock.release()

"""Build both installable add-ons and a Windows kit using only Python stdlib."""
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def zip_tree(source, destination, prefix=""):
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, str(Path(prefix) / path.relative_to(source)))


def build():
    staging = ROOT / "build" / "windows-kit"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    blender = ROOT / "build" / "blender_fusion_bridge"
    if blender.exists():
        shutil.rmtree(blender)
    shutil.copytree(ROOT / "blender" / "blender_fusion_bridge", blender, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("bridge_protocol.py", "job_runner.py", "stl_reader.py"):
        shutil.copy2(ROOT / "common" / name, blender)
    zip_tree(blender, staging / "blender_fusion_bridge-0.2.2.zip", "blender_fusion_bridge")
    fusion = staging / "BlenderFusionBridge"
    shutil.copytree(ROOT / "fusion" / "BlenderFusionBridge", fusion, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(blender, fusion / "blender_fusion_bridge", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(ROOT / "blender/blender_fusion_bridge/stl_writer.py", fusion)
    for name in ("bridge_protocol.py", "job_runner.py"):
        shutil.copy2(ROOT / "common" / name, fusion)
    for name in ("README.md", "install/Install-Fusion.cmd", "install/install-fusion.ps1"):
        shutil.copy2(ROOT / name, staging / Path(name).name)
    shutil.copytree(ROOT / "docs", staging / "docs")
    # Includes editable sources, tests and documentation; no runtime dependencies.
    source = staging / "source"
    source.mkdir()
    for name in ("blender", "fusion", "common", "tools", "tests", "docs", "install", ".github"):
        shutil.copytree(ROOT / name, source / name, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("README.md", ".gitignore"):
        shutil.copy2(ROOT / name, source / name)
    kit = dist / "Blender-Fusion-Bridge-0.2.2-Windows.zip"
    zip_tree(staging, kit, "Blender-Fusion-Bridge-0.2.2-Windows")
    print(kit)
    return kit


if __name__ == "__main__":
    build()

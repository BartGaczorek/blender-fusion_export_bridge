"""Read selected body geometry; leave source bodies and mesh density untouched."""
import shutil
import adsk.fusion
from . import bridge_protocol as protocol
from .stl_writer import write_binary_stl


def selected_bodies(entities):
    bodies = []
    for entity in entities:
        body = adsk.fusion.MeshBody.cast(entity) or adsk.fusion.BRepBody.cast(entity)
        if not body:
            raise ValueError('Zaznacz całe ciała Mesh/BRep/powierzchniowe w drzewie Fusion, nie ściany ani komponenty.')
        if not any(body == other for other in bodies):
            bodies.append(body)
    if not 1 <= len(bodies) <= protocol.MAX_OBJECTS:
        raise ValueError('Zaznacz od 1 do 500 ciał w Fusion.')
    return bodies


def body_triangles(body):
    native = body.nativeObject or body
    occurrence = body.assemblyContext
    transform = occurrence.transform2 if occurrence else None
    if adsk.fusion.MeshBody.cast(native):
        mesh = native.displayMesh  # Existing triangles; no mesh calculator / remeshing.
    else:
        calculator = native.meshManager.createMeshCalculator()
        if not calculator:
            raise RuntimeError('Nie można utworzyć triangulacji: ' + body.name)
        calculator.setQuality(adsk.fusion.TriangleMeshQualityOptions.NormalQualityTriangleMesh)
        mesh = calculator.calculate()  # Standard preset, no settings dialog.
    if not mesh:
        raise RuntimeError('Nie można odczytać siatki: ' + body.name)
    indices = mesh.nodeIndices
    points = mesh.nodeCoordinates
    if len(indices) % 3 or not indices:
        raise ValueError('Nieprawidłowe trójkąty: ' + body.name)
    if len(indices) // 3 > protocol.MAX_TRIANGLES:
        raise ValueError('Limit 5 mln trójkątów.')
    mirrored = False
    if transform:
        m = transform.asArray()
        mirrored = (m[0]*(m[5]*m[10]-m[6]*m[9]) - m[1]*(m[4]*m[10]-m[6]*m[8])
                    + m[2]*(m[4]*m[9]-m[5]*m[8])) < 0
    def generate():
        for offset in range(0, len(indices), 3):
            ids = list(indices[offset:offset+3])
            if mirrored:
                ids[1], ids[2] = ids[2], ids[1]
            triangle = []
            for index in ids:
                point = points[index].copy()
                if transform:
                    if not point.transformBy(transform):
                        raise ValueError('Nieprawidłowa transformacja komponentu.')
                triangle.append((point.x * 10, point.y * 10, point.z * 10))  # Fusion cm -> mm
            yield triangle
    return len(indices) // 3, generate()


def export_bodies(root, bodies, name):
    folder = protocol.create_job(root)
    records, total = [], 0
    try:
        for index, body in enumerate(bodies):
            count, triangles = body_triangles(body)
            total += count
            if total > protocol.MAX_TRIANGLES:
                raise ValueError('Limit 5 mln trójkątów na transfer.')
            filename = 'mesh_{:04d}.stl'.format(index)
            written = write_binary_stl(folder / filename, triangles)
            records.append({'file': filename, 'name': body.name[:120], 'triangles': written,
                            'sha256': protocol.digest(folder / filename)})
        protocol.publish_job(folder, name, records, target='BLENDER')
        return folder
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise

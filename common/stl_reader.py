"""Strict binary STL reader for bridge-generated files (millimeters)."""
import math
import struct
from .bridge_protocol import MAX_TRIANGLES


def triangles(path):
    with open(path, 'rb') as stream:
        header = stream.read(84)
        if len(header) != 84:
            raise ValueError("Niepełny nagłówek STL.")
        count = struct.unpack_from('<I', header, 80)[0]
        if not 0 < count <= MAX_TRIANGLES:
            raise ValueError("Nieprawidłowa liczba trójkątów STL.")
        for _ in range(count):
            raw = stream.read(50)
            if len(raw) != 50:
                raise ValueError("Niepełny STL.")
            values = struct.unpack('<12fH', raw)[3:12]
            if not all(math.isfinite(v) for v in values):
                raise ValueError("Nieprawidłowe współrzędne STL.")
            yield values[:3], values[3:6], values[6:9]
        if stream.read(1):
            raise ValueError("Dodatkowe dane w STL.")


def indexed_mesh(path, mm_per_unit):
    points, faces, lookup = [], [], {}
    for triangle in triangles(path):
        face = []
        for point in triangle:
            if point not in lookup:
                lookup[point] = len(points)
                points.append(tuple(v / mm_per_unit for v in point))
            face.append(lookup[point])
        faces.append(tuple(face))
    return points, faces

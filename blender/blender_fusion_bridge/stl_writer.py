"""Small binary STL writer, independent of Blender's changing export operators."""
import math
import struct


def write_binary_stl(path, triangles):
    count = 0
    with open(path, "wb") as stream:
        stream.write(b"Blender Fusion Bridge / millimeters / Z up".ljust(80, b"\0"))
        stream.write(struct.pack("<I", 0))
        for points in triangles:
            a, b, c = points
            flat = tuple(float(v) for point in points for v in point)
            if len(flat) != 9 or not all(math.isfinite(v) for v in flat):
                raise ValueError("Siatka zawiera nieprawidłowe współrzędne.")
            u = tuple(b[i] - a[i] for i in range(3))
            v = tuple(c[i] - a[i] for i in range(3))
            n = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
            length = math.sqrt(sum(x*x for x in n))
            n = tuple(x / length for x in n) if length else (0.0, 0.0, 0.0)
            stream.write(struct.pack("<12fH", *n, *flat, 0))
            count += 1
        if not count:
            raise ValueError("Obiekt nie zawiera powierzchni do eksportu.")
        stream.seek(80)
        stream.write(struct.pack("<I", count))
    return count

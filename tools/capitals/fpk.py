"""Read-only extractor for Civ 5 .fpk archives (used to study stock models)."""
import struct, sys, os, fnmatch

def entries(path):
    d = open(path, 'rb').read()
    ver, magic = struct.unpack_from('<I4s', d, 0)
    assert magic == b'FPK_', magic
    (count,) = struct.unpack_from('<I', d, 10)
    p = 14
    out = []
    for _ in range(count):
        (n,) = struct.unpack_from('<I', d, p); p += 4
        name = d[p:p+n].decode('latin1'); p += n
        p += (4 - n % 4) % 4 + 8
        size, off = struct.unpack_from('<II', d, p); p += 8
        out.append((name, d[off:off+size]))
    return out

if __name__ == '__main__':
    src, pattern, dst = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else None)
    for name, data in entries(src):
        if fnmatch.fnmatch(name.lower(), pattern.lower()):
            print(len(data), name)
            if dst:
                os.makedirs(dst, exist_ok=True)
                open(os.path.join(dst, name), 'wb').write(data)

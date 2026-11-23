"""Civ5Map (WorldBuilder) reader - terrain block only."""
import struct, sys, collections

def read_map(path):
    d = open(path, 'rb').read()
    p = 0
    ver = d[0]; p = 1
    w, h = struct.unpack_from('<II', d, p); p += 8
    players = d[p]; p += 1
    settings, = struct.unpack_from('<I', d, p); p += 4
    lens = struct.unpack_from('<7I', d, p); p += 28
    def strlist(n):
        nonlocal p
        s = d[p:p+n]; p += n
        return [x.decode('latin1') for x in s.split(b'\0') if x] if n else []
    terrains = strlist(lens[0]); features = strlist(lens[1]); wonders = strlist(lens[2]); resources = strlist(lens[3])
    moddata = d[p:p+lens[4]]; p += lens[4]
    name = d[p:p+lens[5]]; p += lens[5]
    desc = d[p:p+lens[6]]; p += lens[6]
    wsize = b''
    if (ver & 0x7f) >= 11:
        n, = struct.unpack_from('<I', d, p); p += 4
        wsize = d[p:p+n]; p += n
    plots = []
    for i in range(w*h):
        plots.append(tuple(d[p:p+8])); p += 8
    return dict(ver=ver, w=w, h=h, players=players, settings=settings, terrains=terrains,
                features=features, wonders=wonders, resources=resources, name=name, desc=desc,
                worldsize=wsize, plots=plots, rest=len(d)-p)

if __name__ == '__main__':
    m = read_map(sys.argv[1])
    print({k: v for k, v in m.items() if k not in ('plots',)})
    for idx, nm in enumerate(['terrain','res','feat','river','elev','cont','wonder','amt']):
        c = collections.Counter(pl[idx] for pl in m['plots'])
        print(nm, sorted(c.items()))

"""Minimal Granny2 (.gr2) reader/writer for Civ 5 (32-bit little-endian, file format v7).

Reader: decompresses sections (Oodle1 via oodle1.py), applies pointer fixups,
and walks the embedded type tree into plain Python objects.

Writer: serialises a Python object tree against a type tree (normally the one
read from a stock Civ 5 model, so the layout and type tag match exactly what
the game expects). Sections are written uncompressed.
"""
import collections
import struct
import zlib

from oodle1 import decompress

# Granny member types
END, INLINE, REF, REF_ARRAY, ARRAY_REFS, VAR_REF, _UNUSED6, REF_VAR_ARRAY, STRING, TRANSFORM, REAL32, \
    INT8, UINT8, BINORMAL_INT8, NORMAL_UINT8, INT16, UINT16, BINORMAL_INT16, NORMAL_UINT16, \
    INT32, UINT32, REAL16, EMPTY_REF = range(23)

SCALAR = {REAL32: ('f', 4), INT8: ('b', 1), UINT8: ('B', 1), BINORMAL_INT8: ('b', 1), NORMAL_UINT8: ('B', 1),
          INT16: ('h', 2), UINT16: ('H', 2), BINORMAL_INT16: ('h', 2), NORMAL_UINT16: ('H', 2),
          INT32: ('i', 4), UINT32: ('I', 4), REAL16: ('H', 2)}
PTR_SIZE = {REF: 4, REF_ARRAY: 8, ARRAY_REFS: 8, VAR_REF: 8, REF_VAR_ARRAY: 12, STRING: 4, TRANSFORM: 68, EMPTY_REF: 4}

import os as _os

def name_hash(s):
    """Hash Civ 5 uses for stripped Granny strings (CRC32, no final xor)."""
    return (~zlib.crc32(s.encode('latin1'))) & 0xffffffff

KNOWN = {}
try:
    for _l in open(_os.path.join(_os.path.dirname(__file__), 'names.txt'), encoding='latin1'):
        _l = _l.rstrip('\n')
        KNOWN[name_hash(_l)] = _l
except OSError:
    pass
KNOWN[name_hash('')] = ''

MAGIC_LE32 = bytes.fromhex('29de6cc0baa4532b25f5b7a5f666e2ee')
NODE_SIZE = 32  # 32-bit type node


class Member:
    __slots__ = ('type', 'name', 'children', 'array', 'extra', 'extra4')

    def __init__(self, type, name, children, array, extra=(0, 0, 0), extra4=0):
        self.type, self.name, self.children, self.array, self.extra, self.extra4 = type, name, children, array, extra, extra4

    def __repr__(self):
        return f'Member({self.type},{self.name!r},{self.array})'


def struct_size(members):
    s = 0
    for m in members:
        if m.type == INLINE:
            one = struct_size(m.children)
        elif m.type in SCALAR:
            one = SCALAR[m.type][1]
        else:
            one = PTR_SIZE[m.type]
        s += one * max(m.array, 1)
    return s


class Variant:
    """A value carrying its own type (for VAR_REF / REF_VAR_ARRAY)."""
    __slots__ = ('members', 'value')

    def __init__(self, members, value):
        self.members, self.value = members, value


# --------------------------------------------------------------------------- reading

class Gr2File:
    def __init__(self, data):
        self.raw = data
        assert data[:16] == MAGIC_LE32, 'only 32-bit little-endian gr2 supported'
        self.format_version, total, self.crc, so, sc = struct.unpack_from('<5I', data, 0x20)
        self.type_ref = struct.unpack_from('<2I', data, 0x34)
        self.root_ref = struct.unpack_from('<2I', data, 0x3c)
        self.tag, = struct.unpack_from('<I', data, 0x44)
        self.extra_tags = data[0x48:0x68]
        self.sections = []
        self.base = []
        mem = bytearray()
        for i in range(sc):
            h = struct.unpack_from('<11I', data, 0x20 + so + i * 44)
            comp, off, clen, dlen, align, s0, s1, fxo, fxn, mo, mn = h
            if comp == 0:
                blob = data[off:off + dlen]
            elif comp == 2:
                blob = decompress(data[off:off + clen], dlen, s0, s1)
            else:
                raise ValueError(f'compression {comp} unsupported')
            while len(mem) % 32:
                mem.append(0)
            self.base.append(len(mem))
            mem += blob
            self.sections.append(h)
        self.mem = mem
        self.ptr_targets = set()
        for i, h in enumerate(self.sections):
            fxo, fxn = h[7], h[8]
            for k in range(fxn):
                src, dsec, doff = struct.unpack_from('<3I', data, fxo + k * 12)
                addr = self.base[dsec] + doff + 1  # +1 so that 0 stays "null"
                struct.pack_into('<I', mem, self.base[i] + src, addr)
                self.ptr_targets.add(self.base[i] + src)
        self.types = {}
        self.root_type = self.read_types(self.addr(self.type_ref))

    def addr(self, ref):
        return self.base[ref[0]] + ref[1]

    def u32(self, a):
        return struct.unpack_from('<I', self.mem, a)[0]

    def ptr(self, a):
        if a not in self.ptr_targets:
            v = self.u32(a)
            return None if v == 0 else KNOWN.get(v, '#%08x' % v)
        return self.u32(a) - 1

    def cstr(self, a):
        if a is None or isinstance(a, str):
            return a
        e = self.mem.index(0, a)
        return self.mem[a:e].decode('latin1')

    def read_types(self, a):
        if a in self.types:
            return self.types[a]
        lst = []
        self.types[a] = lst
        while True:
            t, name_p, child_p, arr, e0, e1, e2, e4 = struct.unpack_from('<IIIiIIII', self.mem, a)
            if t == END:
                break
            if (a + 4) in self.ptr_targets:
                name = self.cstr(name_p - 1)
            else:  # stock Civ 5 files replace names by a hash (string database)
                name = KNOWN.get(name_p, '#%08x' % name_p)
            children = self.read_types(child_p - 1) if child_p else None
            lst.append(Member(t, name, children, arr, (e0, e1, e2), e4))
            a += NODE_SIZE
        return lst

    def read_shared(self, members, a):
        """Objects reached through pointers are shared: same address -> same dict."""
        if not hasattr(self, '_cache'):
            self._cache = {}
        k = (a, id(members))
        if k not in self._cache:
            self._cache[k] = None
            self._cache[k] = self.read_struct(members, a)
        return self._cache[k]

    def read_struct(self, members, a):
        out = {}
        for m in members:
            n = max(m.array, 1)
            vals = []
            for _ in range(n):
                v, size = self.read_member(m, a)
                vals.append(v)
                a += size
            out[m.name] = vals if m.array else vals[0]
        return out

    def read_member(self, m, a):
        t = m.type
        if t == INLINE:
            return self.read_struct(m.children, a), struct_size(m.children)
        if t in SCALAR:
            f, s = SCALAR[t]
            return struct.unpack_from('<' + f, self.mem, a)[0], s
        if t == STRING:
            return self.cstr(self.ptr(a)), 4
        if t == REF:
            p = self.ptr(a)
            return (None if p is None else self.read_shared(m.children, p)), 4
        if t == REF_ARRAY:
            cnt = self.u32(a)
            p = self.ptr(a + 4)
            sz = struct_size(m.children)
            return [self.read_struct(m.children, p + i * sz) for i in range(cnt)] if p is not None else [], 8
        if t == ARRAY_REFS:
            cnt = self.u32(a)
            p = self.ptr(a + 4)
            res = []
            for i in range(cnt):
                q = self.ptr(p + 4 * i)
                res.append(None if q is None else self.read_shared(m.children, q))
            return res, 8
        if t == VAR_REF:
            tp, p = self.ptr(a), self.ptr(a + 4)
            if tp is None or p is None:
                return None, 8
            mem = self.read_types(tp)
            return Variant(mem, self.read_struct(mem, p)), 8
        if t == REF_VAR_ARRAY:
            tp = self.ptr(a)
            cnt = self.u32(a + 4)
            p = self.ptr(a + 8)
            if tp is None:
                return Variant([], []), 12
            mem = self.read_types(tp)
            sz = struct_size(mem)
            return Variant(mem, [self.read_struct(mem, p + i * sz) for i in range(cnt)]), 12
        if t == TRANSFORM:
            v = struct.unpack_from('<I3f4f9f', self.mem, a)
            return {'Flags': v[0], 'Position': list(v[1:4]), 'Orientation': list(v[4:8]),
                    'ScaleShear': list(v[8:17])}, 68
        if t == EMPTY_REF:
            return None, 4
        raise ValueError(t)

    def root(self):
        return self.read_struct(self.root_type, self.addr(self.root_ref))


def read(path):
    return Gr2File(open(path, 'rb').read())


def dump_types(members, indent=0, seen=None):
    seen = set() if seen is None else seen
    lines = []
    for m in members:
        lines.append('  ' * indent + f'{m.name}: t{m.type}' + (f'[{m.array}]' if m.array else '') +
                     (f' extra={m.extra}' if any(m.extra) else ''))
        if m.children is not None:
            if id(m.children) in seen:
                lines.append('  ' * (indent + 1) + '...')
            else:
                seen.add(id(m.children))
                lines += dump_types(m.children, indent + 1, seen)
                seen.discard(id(m.children))
    return lines


# --------------------------------------------------------------------------- writing

# Standard Granny sections, as used by every stock Civ 5 .gr2 (checked: Polynesian palace, Colossus,
# Great Lighthouse, United Nations): 0 main objects, 1/2 rigid vertex/index data, 3/4 deformable (skinned)
# vertex/index data, 6 type tree ("discardable"). Animation curves stay in section 0.
SEC_MAIN, SEC_RIGID_VERTS, SEC_RIGID_INDICES, SEC_DEFORM_VERTS, SEC_DEFORM_INDICES, SEC_TYPES = 0, 1, 2, 3, 4, 6
_SEC_SHIFT = 28     # internal address = section << 28 | offset


class Writer:
    """Serialises objects into Granny sections. sections=False puts everything into section 0 (the
    original civ5me layout); sections=True uses the stock layout above."""

    def __init__(self, hashed=False, sections=False):
        # hashed=True: like stock Civ 5 files, every string (data and type-tree names) is stored as its
        # name_hash() instead of a pointer, and the header's StringDatabaseCRC is set (see write()).
        self.hashed = hashed
        self.sections = sections
        self.bufs = collections.defaultdict(bytearray)
        self.fixups = []  # (src_addr, dst_addr), internal addresses
        self.strings = {}
        self.type_addr = {}
        self._cur = SEC_MAIN        # section for the struct being written
        self._deform = False        # inside the topology of a mesh with skinned vertices
        self.deform_topologies = set()  # id() of every PrimaryTopology whose mesh is skinned (set by write())

    # -- addressing
    def _buf(self, a):
        return self.bufs[a >> _SEC_SHIFT], a & ((1 << _SEC_SHIFT) - 1)

    def pack(self, fmt, a, *vals):
        b, o = self._buf(a)
        struct.pack_into(fmt, b, o, *vals)

    def put(self, a, data):
        b, o = self._buf(a)
        b[o:o + len(data)] = data

    def alloc(self, size, align=4, sec=None):
        sec = (self._cur if sec is None else sec) if self.sections else SEC_MAIN
        buf = self.bufs[sec]
        while len(buf) % align:
            buf.append(0)
        a = len(buf)
        buf += b'\0' * size
        return (sec << _SEC_SHIFT) | a

    def set_ptr(self, at, target):
        if target is None:
            return
        self.pack('<I', at, 0)
        self.fixups.append((at, target))

    def string(self, s, sec=None):
        if s is None:
            return None
        sec = (self._cur if sec is None else sec) if self.sections else SEC_MAIN
        if (s, sec) not in self.strings:
            b = s.encode('latin1') + b'\0'
            a = self.alloc(len(b), 1, sec)
            self.put(a, b)
            self.strings[(s, sec)] = a
        return self.strings[(s, sec)]

    def write_types(self, members):
        key = id(members)
        if key in self.type_addr:
            return self.type_addr[key]
        a = self.alloc(NODE_SIZE * (len(members) + 1), sec=SEC_TYPES)
        self.type_addr[key] = a
        for i, m in enumerate(members):
            o = a + i * NODE_SIZE
            self.pack('<IIIiIIII', o, m.type, 0, 0, m.array, *m.extra, m.extra4)
            if self.hashed:
                self.pack('<I', o + 4, name_hash(m.name) if m.name is not None else 0)
            else:
                self.set_ptr(o + 4, self.string(m.name, SEC_TYPES))
            if m.children is not None:
                self.set_ptr(o + 8, self.write_types(m.children))
        return a

    def write_struct_at(self, members, value, a):
        deform_before = self._deform
        if id(value) in self.deform_topologies:     # index data of a skinned mesh
            self._deform = True
        for m in members:
            n = max(m.array, 1)
            vals = value.get(m.name) if isinstance(value, dict) else None
            if m.array:
                vals = list(vals) if vals is not None else []
                vals += [None] * (n - len(vals))
            else:
                vals = [vals]
            for v in vals:
                a += self.write_member(m, v, a)
        self._deform = deform_before

    def new_struct(self, members, value):
        a = self.alloc(struct_size(members))
        self.write_struct_at(members, value, a)
        return a

    def new_struct_array(self, members, values, sec=None):
        sz = struct_size(members)
        a = self.alloc(sz * len(values), sec=sec)
        for i, v in enumerate(values):
            self.write_struct_at(members, v, a + i * sz)
        return a

    def _data_section(self, name, members=None):
        """Section for a vertex / index array member, as in stock files (None = main). Vertices are
        skinned when their vertex type has BoneWeights; indices when their mesh's vertices are."""
        if name == 'Vertices':
            skinned = members is not None and any(m.name == 'BoneWeights' for m in members)
            return SEC_DEFORM_VERTS if skinned else SEC_RIGID_VERTS
        if name in ('Indices16', 'Indices'):
            return SEC_DEFORM_INDICES if self._deform else SEC_RIGID_INDICES
        return None

    def write_member(self, m, v, a):
        t = m.type
        if t == INLINE:
            self.write_struct_at(m.children, v or {}, a)
            return struct_size(m.children)
        if t in SCALAR:
            f, s = SCALAR[t]
            self.pack('<' + f, a, v if v is not None else 0)
            return s
        if t == STRING:
            if self.hashed:
                self.pack('<I', a, name_hash(v) if v is not None else 0)
            else:
                self.set_ptr(a, self.string(v))
            return 4
        if t == REF:
            if v is not None:
                self.set_ptr(a, self.obj_addr(m.children, v))
            return 4
        if t == REF_ARRAY:
            v = v or []
            self.pack('<I', a, len(v))
            if v:
                sec = self._data_section(m.name)
                if isinstance(v, (bytes, bytearray)):  # pre-packed raw array
                    sz = struct_size(m.children)
                    p = self.alloc(len(v), 16, sec)
                    self.put(p, v)
                    self.pack('<I', a, len(v) // sz)
                else:
                    p = self.new_struct_array(m.children, v, sec)
                self.set_ptr(a + 4, p)
            return 8
        if t == ARRAY_REFS:
            v = v or []
            self.pack('<I', a, len(v))
            if v:
                p = self.alloc(4 * len(v))
                self.set_ptr(a + 4, p)
                for i, item in enumerate(v):
                    if item is not None:
                        self.set_ptr(p + 4 * i, self.obj_addr(m.children, item))
            return 8
        if t == VAR_REF:
            if v is not None:
                self.set_ptr(a, self.write_types(v.members))
                self.set_ptr(a + 4, self.obj_addr(v.members, v.value))
            return 8
        if t == REF_VAR_ARRAY:
            if v is not None and v.members:
                self.set_ptr(a, self.write_types(v.members))
                items = v.value
                sec = self._data_section(m.name, v.members)
                if isinstance(items, (bytes, bytearray)):
                    sz = struct_size(v.members)
                    self.pack('<I', a + 4, len(items) // sz)
                    p = self.alloc(len(items), 16, sec)
                    self.put(p, items)
                    self.set_ptr(a + 8, p)
                elif items:
                    self.pack('<I', a + 4, len(items))
                    self.set_ptr(a + 8, self.new_struct_array(v.members, items, sec))
            return 12
        if t == TRANSFORM:
            v = v or {'Flags': 0, 'Position': [0, 0, 0], 'Orientation': [0, 0, 0, 1],
                      'ScaleShear': [1, 0, 0, 0, 1, 0, 0, 0, 1]}
            self.pack('<I3f4f9f', a, v['Flags'], *v['Position'], *v['Orientation'], *v['ScaleShear'])
            return 68
        if t == EMPTY_REF:
            return 4
        raise ValueError(t)

    # Shared objects (e.g. a material referenced from several places) are
    # written once: identity of the Python object decides sharing.
    def obj_addr(self, members, value):
        if not hasattr(self, '_objs'):
            self._objs = {}
        k = id(value)
        if k not in self._objs:
            self._objs[k] = (self.new_struct(members, value), value)
        return self._objs[k][0]


STRING_DB_CRC_STOCK = 2     # header value in every stock Civ 5 .gr2 (strings stored as hashes)


def write(path, root_members, root_value, tag, extra_tags=b'\0' * 32, nsections=8, hashed=False, sections=False):
    """sections=True: stock section layout (see SEC_*); False: everything in section 0 (old layout)."""
    w = Writer(hashed, sections)
    if hashed:      # ExtraTags[4] (16 bytes), then StringDatabaseCRC
        extra_tags = extra_tags[:16].ljust(16, b'\0') + struct.pack('<I', STRING_DB_CRC_STOCK) + extra_tags[20:32]
    w._objs = {}
    for mesh in (root_value.get('Meshes') or []) if isinstance(root_value, dict) else []:
        vd = (mesh or {}).get('PrimaryVertexData') or {}
        verts = vd.get('Vertices') if isinstance(vd, dict) else None
        if isinstance(verts, Variant) and any(m.name == 'BoneWeights' for m in verts.members) \
                and mesh.get('PrimaryTopology') is not None:
            w.deform_topologies.add(id(mesh['PrimaryTopology']))
    root_addr = w.new_struct(root_members, root_value)
    type_addr = w.write_types(root_members)
    mask = (1 << _SEC_SHIFT) - 1
    datas = []
    for i in range(nsections):
        b = w.bufs.get(i, bytearray())
        while len(b) % 4:
            b.append(0)
        datas.append(bytes(b))
    fix = [[] for _ in range(nsections)]
    for src, dst in w.fixups:
        fix[src >> _SEC_SHIFT].append((src & mask, dst >> _SEC_SHIFT, dst & mask))
    header_size = 0x20 + 0x48 + 44 * nsections  # = 456 for 8 sections
    # layout: header, section table, all section data, then all fixup tables
    off = header_size
    data_offs = []
    for d in datas:
        data_offs.append(off)
        off += len(d)
    fix_offs, fixblobs = [], []
    for i in range(nsections):
        blob = b''.join(struct.pack('<3I', s, ds, do) for s, ds, do in sorted(fix[i]))
        fix_offs.append(off)
        fixblobs.append(blob)
        off += len(blob)
    total = off
    secs = b''
    for i in range(nsections):
        n = len(datas[i])
        if n or fix[i]:
            secs += struct.pack('<11I', 0, data_offs[i], n, n, 4, n, n, fix_offs[i], len(fix[i]), total, 0)
        else:
            secs += struct.pack('<11I', 0, total, 0, 0, 4, 0, 0, total, 0, total, 0)
    info = struct.pack('<5I', 7, total, 0, 0x48, nsections) + \
        struct.pack('<2I', type_addr >> _SEC_SHIFT, type_addr & mask) + \
        struct.pack('<2I', root_addr >> _SEC_SHIFT, root_addr & mask) + struct.pack('<I', tag) + \
        extra_tags[:32].ljust(32, b'\0')
    assert len(info) == 0x48
    head = MAGIC_LE32 + struct.pack('<I', header_size) + struct.pack('<I', 0) + b'\0' * 8
    body = secs + b''.join(datas) + b''.join(fixblobs)
    crc = zlib.crc32(body) & 0xffffffff
    info = info[:8] + struct.pack('<I', crc) + info[12:]
    out = head + info + body
    assert len(out) == total
    open(path, 'wb').write(out)
    return total

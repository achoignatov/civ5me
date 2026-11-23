"""Empty-tile probes made from a landmark's Test 1 (static) model (docs/CITY_MODELS.md §8).

Every stock Civ 5 .gr2 stores ALL strings (names, file names, shader names, type-tree names) as
CRC32 hashes and sets the header's StringDatabaseCRC to 2. Ours store real text (StringDatabaseCRC 0),
and they are the only meshes that sometimes vanish. Stock meshes also leave the bone bindings'
OBBMin/OBBMax at zero, while ours fill in real boxes. Each probe changes one of these to match stock:

  <model>_T1H   strings hashed like stock
  <model>_T1Z   OBBMin/OBBMax zeroed like stock
  <model>_T1HZ  both

Same mesh and textures as Test 1, so in a bad launch the probe that draws names the cause.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'capitals'))
import gr2  # noqa: E402

sys.path.insert(0, HERE)
from landmarks import T1_PROBES as VARIANTS  # noqa: E402  (suffix, label, hashed, zero OBB, stock sections)


def to_stock_sections(src, dst):
    """Copy a .gr2 rewritten in the stock section layout (vertices / indices / types in their own sections)."""
    f = gr2.read(src)
    gr2.write(dst, f.root_type, f.root(), f.tag, sections=True)


def _zero_obb(v, seen=None):
    seen = set() if seen is None else seen
    if id(v) in seen:
        return
    seen.add(id(v))
    if isinstance(v, dict):
        for k in ('OBBMin', 'OBBMax'):
            if k in v:
                v[k] = [0.0, 0.0, 0.0]
        for x in v.values():
            _zero_obb(x, seen)
    elif isinstance(v, list):
        for x in v:
            _zero_obb(x, seen)
    elif isinstance(v, gr2.Variant):
        _zero_obb(v.value, seen)


def fxsxml_name(model, suffix):
    return model + suffix + '.fxsxml'


def build(model, src_dir, art_dir):
    """Write the probe .gr2/.fxsxml files for one landmark from <model>_Static.gr2 and <model>_T1.fxsxml.
    Returns the file names written."""
    t1_fx = open(os.path.join(src_dir, model + '_T1.fxsxml'), encoding='utf-8').read()
    mesh = re.search(r'<Mesh file="([^"]+)"', t1_fx).group(1)
    written = []
    for suffix, _, hashed, zero, sections in VARIANTS:
        f = gr2.read(os.path.join(src_dir, mesh))
        root = f.root()
        if zero:
            _zero_obb(root)
        name = model + suffix
        gr2.write(os.path.join(art_dir, name + '.gr2'), f.root_type, root, f.tag, hashed=hashed, sections=sections)
        fx = t1_fx.replace('<Mesh file="%s"' % mesh, '<Mesh file="%s.gr2"' % name)
        assert fx != t1_fx
        open(os.path.join(art_dir, fxsxml_name(model, suffix)), 'w', encoding='utf-8', newline='\r\n').write(fx)
        written += [name + '.gr2', fxsxml_name(model, suffix)]
    return written

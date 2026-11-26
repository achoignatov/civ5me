"""Quick CLAY render of a model module's geometry (no bake): checks shapes and composition fast.

Run:  blender -b --factory-startup -P tools/landmarks/clay_preview.py -- <module> <out_dir> [parts...] [--views N]
Parts: 'main' (build), 'eye' (build_eye), or EXTRA_STATICS suffixes; default all. Glowing materials (ao=False) emit.
"""
import importlib
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, 'models'), os.path.join(HERE, '..', 'capitals')]
sys.path.append(os.path.join(HERE, '..', '..', 'build', 'venv', 'lib', 'python%d.%d' % sys.version_info[:2],
                             'site-packages'))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
import blib  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:]
modname, out = argv[0], argv[1]
want = [a for a in argv[2:] if not a.startswith('--')]
mod = importlib.import_module(modname)
fns = [('main', lambda b: mod.build(b, eye=False))]
if hasattr(mod, 'build_eye'):
    fns.append(('eye', mod.build_eye))
fns += [(s, f) for s, f, _ in getattr(mod, 'EXTRA_STATICS', ())]
bpy.ops.wm.read_factory_settings(use_empty=True)
objs = []
for name, fn in fns:
    if want and name not in want:
        continue
    t0 = time.time()
    b = blib.Builder(seed=1)
    fn(b)
    bpy.ops.wm.read_factory_settings(use_empty=True) if False else None
    me = bpy.data.meshes.new(name)
    me.from_pydata(b.verts, [], b.faces)
    me.update()
    mats = {}
    for n in b.mat_names:
        p = blib.PALETTE[n]
        m = bpy.data.materials.new(n)
        m.use_nodes = True
        bs = m.node_tree.nodes['Principled BSDF']
        c = p['color']
        lin = tuple((x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c)
        if p.get('ao', True) is False:
            bs.inputs['Emission Color'].default_value = lin + (1,)
            bs.inputs['Emission Strength'].default_value = 3.0
        if p.get('lava'):
            lin = (0.09, 0.08, 0.075)
        bs.inputs['Base Color'].default_value = lin + (1,)
        bs.inputs['Roughness'].default_value = 0.6
        me.materials.append(m)
    me.polygons.foreach_set('material_index', b.fmat)
    me.polygons.foreach_set('use_smooth', [True] * len(b.faces))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    # drop the hires helper objects the builders may have created
    for o in list(bpy.data.objects):
        if o.name not in [x[0] for x in fns] and o.type == 'MESH' and o is not ob and o.name not in [x.name for x in objs]:
            bpy.data.objects.remove(o)
    objs.append(ob)
    print('CLAY %s: %d verts %d faces (%.1fs)' % (name, len(b.verts), len(b.faces), time.time() - t0))
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -0.05))
g = bpy.context.active_object
gm = bpy.data.materials.new('g'); gm.use_nodes = True
gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.25, 0.22, 0.17, 1)
g.data.materials.append(gm)
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.energy = 4.0
sun.rotation_euler = (math.radians(50), math.radians(-25), math.radians(-30))
bpy.context.scene.collection.objects.link(sun)
w = bpy.data.worlds.new('w'); w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.62, 0.75, 1)
w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.7
sc = bpy.context.scene
sc.world = w
sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'CYCLES'
sc.render.resolution_x, sc.render.resolution_y = 900, 700
sc.view_settings.view_transform = 'Standard'
if sc.render.engine == 'CYCLES':
    sc.cycles.samples = 16
os.makedirs(out, exist_ok=True)
for i, (loc, tgt, lens) in enumerate(getattr(mod, 'PREVIEW', [])):
    cam = bpy.data.objects.new('cam%d' % i, bpy.data.cameras.new('cam%d' % i))
    cam.data.lens = lens
    cam.data.clip_end = 2000
    cam.location = loc
    d = Vector(tgt) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.filepath = os.path.join(out, 'clay_%d.png' % i)
    bpy.ops.render.render(write_still=True)
print('CLAY done')

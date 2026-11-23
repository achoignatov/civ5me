"""Write a Civ 5 building model (.gr2 + .fxsxml) from plain mesh arrays.

The Granny type tree, the "Tree cut" ground stencil and the BuildingShader material
setup are taken from the stock Polynesian palace (vendor/civ5/template_poly_palace.gr2),
so the file has exactly the layout the game's wonder/palace renderer expects.
Only the building mesh, its texture names and a few labels are ours.
"""
import copy
import math
import os
import struct

import gr2

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_VERTS = 32000
TEMPLATE = os.path.join(HERE, '..', '..', 'vendor', 'civ5', 'template_poly_palace.gr2')


def _scrub(obj, path='root', found=None):
    """Replace any string still hashed ('#xxxxxxxx') by '' and report it."""
    found = [] if found is None else found
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and v.startswith('#') and len(v) == 9:
                found.append(path + '.' + k)
                obj[k] = ''
            else:
                _scrub(v, path + '.' + k, found)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _scrub(v, '%s[%d]' % (path, i), found)
    elif isinstance(obj, gr2.Variant):
        _scrub(obj.value, path + '<v>', found)
    return found


HEX_IN = 31.2                               # same as blib.HEX_IN (city hexagon, model units)
HEX_OUT = HEX_IN / math.cos(math.pi / 6)


def _hex_tree_cut(vd, topo):
    """The template's "Tree cut" stencil (where the game removes forest trees under the model)
    is a 60 x 56 rectangle; make it the city hexagon, so the whole tile is cleared and the
    neighbouring tiles keep their trees."""
    proto = vd['Vertices'].value[0]
    pts = [(0.0, 0.0)] + [(HEX_OUT * math.cos(math.radians(30 + 60 * k)),
                           HEX_OUT * math.sin(math.radians(30 + 60 * k))) for k in range(6)]
    verts = []
    for x, y in pts:
        v = copy.deepcopy(proto)
        v['Position'] = [x, y, 0.0]
        v['TextureCoordinates0'] = [0.5 + x / (2 * HEX_OUT), 0.5 - y / (2 * HEX_OUT), 0.0]
        verts.append(v)
    vd['Vertices'].value = verts
    idx = []
    for k in range(6):
        idx += [0, 1 + k, 1 + (k + 1) % 6]
    topo['Indices16'] = [{'Int16': i} for i in idx]
    topo['Groups'][0]['TriCount'] = 6


def write_model(out_dir, name, verts, tris, diffuse, sref, fx=(), wonder=True, hex_cut=True):
    """verts: list of (pos3, normal3, tangent3, binormal3, uv2); tris: list of index triples.
    Writes <name>.gr2 and <name>.fxsxml into out_dir.
    hex_cut=False keeps the template's own (stock) "Tree cut" stencil untouched."""
    f = gr2.read(TEMPLATE)
    root = f.root()
    tc_mat, b_tmpl = root['Materials'][0], root['Materials'][1]
    tc_skel, tc_vd, tc_topo, tc_mesh, tc_model = (root['Skeletons'][0], root['VertexDatas'][0],
                                                  root['TriTopologies'][0], root['Meshes'][0], root['Models'][0])
    # stock files use a (stripped) string database for these; give them real values
    for m in tc_mat['Maps']:
        m['Map']['Texture']['FromFileName'] = 'Generic_Grey_8.dds'
        m['Map']['ExtendedData'].value['File Name'] = 'Generic_Grey_8.dds'
    for i in (0, 4, 8):
        tc_mat['ExtendedData'].value['ParameterSet0']['ParamDataT'][i]['String'] = 'Generic_Grey_8.dds'
    # the UV component's stripped name is unknown; the name list is informational only
    tc_vd['VertexComponentNames'][4]['String'] = 'TextureCoordinates0'
    if wonder and hex_cut:
        _hex_tree_cut(tc_vd, root['TriTopologies'][0])

    # ---- building material: copy of the stock BuildingShader material
    mat = copy.deepcopy(b_tmpl)
    mat['Name'] = name
    for m, tex in zip(mat['Maps'], (diffuse, sref)):
        m['Map']['Name'] = tex
        m['Map']['Texture']['FromFileName'] = tex
        m['Map']['ExtendedData'].value['File Name'] = tex
    ext = mat['ExtendedData'].value
    ext['FallbackMtl'] = [{'String': ''}]
    dt = ext['ParameterSet1']['ParamDataT']
    for i, d in enumerate(dt):
        d['String'] = ''
    dt[0]['String'] = diffuse
    dt[4]['String'] = sref

    # ---- vertex / index data, split into parts of < 32k vertices (Indices16 is a signed
    # Int16 member, and the stock palaces only use 16-bit indices). Each part becomes its
    # own model, exactly like the template's separate "Tree cut" model.
    vmembers = tc_vd['Vertices'].members
    assert [m.name for m in vmembers] == ['Position', 'Normal', 'Tangent', 'Binormal', 'TextureCoordinates0']
    parts = []
    cur_map, cur_tris = {}, []
    for tri in tris:
        new = [i for i in tri if i not in cur_map]
        if len(cur_map) + len(new) > MAX_VERTS:
            parts.append((cur_map, cur_tris))
            cur_map, cur_tris = {}, []
            new = list(tri)
        for i in tri:
            if i not in cur_map:
                cur_map[i] = len(cur_map)
        cur_tris.append(tuple(cur_map[i] for i in tri))
    parts.append((cur_map, cur_tris))

    skels, vds, topos, meshes, models = [], [], [], [], []
    for k, (vmap, ptris) in enumerate(parts):
        pname = name if len(parts) == 1 else '%s_%d' % (name, k + 1)
        order = sorted(vmap, key=vmap.get)
        vb = bytearray()
        for i in order:
            p, n, t, b, uv = verts[i]
            vb += struct.pack('<15f', *p, *n, *t, *b, uv[0], uv[1], 0.0)
        flat = [i for tri in ptris for i in tri]
        ib = struct.pack('<%dH' % len(flat), *flat)
        vd = {'Vertices': gr2.Variant(vmembers, bytes(vb)),
              'VertexComponentNames': [{'String': s} for s in ('Position', 'Normal', 'Tangent', 'Binormal',
                                                                'TextureCoordinates0')],
              'VertexAnnotationSets': []}
        topo = {'Groups': [{'MaterialIndex': 0, 'TriFirst': 0, 'TriCount': len(ptris)}],
                'Indices': [], 'Indices16': ib,
                'VertexToVertexMap': [], 'VertexToTriangleMap': [], 'SideToNeighborMap': [],
                'BonesForTriangle': [], 'TriangleToBoneIndices': [], 'TriAnnotationSets': []}
        xs = [verts[i][0] for i in order]
        lo = [min(p[j] for p in xs) for j in range(3)]
        hi = [max(p[j] for p in xs) for j in range(3)]
        bone = copy.deepcopy(tc_skel['Bones'][0])
        bone['Name'] = pname
        skel = {'Name': pname, 'Bones': [bone], 'LODType': 0, 'ExtendedData': None}
        mesh = {'Name': pname, 'PrimaryVertexData': vd, 'MorphTargets': [], 'PrimaryTopology': topo,
                'MaterialBindings': [{'Material': mat}],
                'BoneBindings': [{'BoneName': pname, 'OBBMin': lo, 'OBBMax': hi, 'TriangleIndices': []}],
                'ExtendedData': None}
        model = {k2: v for k2, v in tc_model.items()}
        model.update({'Name': pname, 'Skeleton': skel, 'MeshBindings': [{'Mesh': mesh}]})
        skels.append(skel); vds.append(vd); topos.append(topo); meshes.append(mesh); models.append(model)

    # ---- effect bones (FX_*) on the first building model, like the Great Lighthouse's FX_FireLight
    fx = list(fx)
    if fx:
        bones = skels[0]['Bones']
        for bname, (x, y, z), effect in fx:
            bone = copy.deepcopy(bones[0])
            bone.update({'Name': bname, 'ParentIndex': 0,
                         'Transform': {'Flags': 1, 'Position': [x, y, z], 'Orientation': [0.0, 0.0, 0.0, 1.0],
                                       'ScaleShear': [1.0, 0, 0, 0, 1.0, 0, 0, 0, 1.0]},
                         'InverseWorldTransform': [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, -x, -y, -z, 1.0]})
            bones.append(bone)
        assert len({b['Name'] for b in bones}) == len(bones), 'duplicate FX bone names'

    root['ArtToolInfo']['FromArtToolName'] = 'Blender'
    root['ExporterInfo']['ExporterName'] = 'civ5me tools/capitals'
    root['FromFileName'] = name + '.blend'
    root['Materials'] = [tc_mat, mat]
    root['Skeletons'] = [tc_skel] + skels
    root['VertexDatas'] = [tc_vd] + vds
    root['TriTopologies'] = [tc_topo] + topos
    root['Meshes'] = [tc_mesh] + meshes
    root['Models'] = [tc_model] + models
    left = _scrub(root)
    if left:
        print('  note: blanked stripped strings at', left)

    os.makedirs(out_dir, exist_ok=True)
    size = gr2.write(os.path.join(out_dir, name + '.gr2'), f.root_type, root, f.tag)
    lines = ['<Asset>', '\t<Mesh file="%s.gr2"/>' % name, '\t<Texture file="Generic_Grey_8.dds"/>',
             '\t<Texture file="%s"/>' % diffuse, '\t<Texture file="%s"/>' % sref]
    trig = 'FX_Triggers_%s.ftsxml' % name
    if fx:
        lines.append('\t<BoneUsage>')
        lines += ['\t\t<Bone name="%s"/>' % bname for bname, _, _ in fx]
        lines.append('\t</BoneUsage>')
        lines.append('\t<TimedTrigger file="%s" source="Tool" model="%s" state="0,1,2,3"/>' % (trig, models[0]['Name']))
        tl = ['<trigger_system type="FGrannyTimedTriggerSystem">', '  <event_tracks>', '    <event_track ec="1000">',
              '      <track id="1" name="Sound" />', '      <track id="2" name="Effect" />',
              '      <track id="3" name="Transfer" />', '    </event_track>', '  </event_tracks>', '  <triggers>']
        for i, (bname, _, effect) in enumerate(fx):
            tl.append('    <trigger type="FTimedTriggerEffect" id="%d" time="0" duration="10" repeat="0" ec="1000" '
                      'track="2" tier="0" event="%s" bone="%s" />' % (i + 1, effect, bname))
        tl += ['  </triggers>', '</trigger_system>']
        with open(os.path.join(out_dir, trig), 'w', newline='\r\n') as f2:
            f2.write('\n'.join(tl) + '\n')
    elif os.path.exists(os.path.join(out_dir, trig)):
        os.remove(os.path.join(out_dir, trig))
    if wonder:
        # like every stock wonder (Big Ben, Forbidden City, Colossus ...): the wonder state machine
        lines.append('\t<DecisionTree file="Wonder_DecisionTree.ddtxml" source="Tool"/>')
    lines.append('</Asset>')
    with open(os.path.join(out_dir, name + '.fxsxml'), 'w', newline='\r\n') as f2:
        f2.write('\n'.join(lines) + '\n')
    return size

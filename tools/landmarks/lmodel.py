"""Write an ANIMATED landmark: building .gr2 + idle animation .gr2 + .fxsxml + effect triggers.

Modelled on the stock United Nations wonder (the one stock wonder with a looping idle animation):
  * one .gr2 with three models: the stock "Tree cut" stencil, the static building
    (BuildingShader, exactly as the proven static landmarks), and a SKINNED model
    (BuildingShader_Skinned, vertices with BoneWeights/BoneIndices) whose bones the animation moves;
  * <Name>_Idle.gr2: one TrackGroup per model (named like the model), one track per bone (named
    like the bone, sorted by name), played as Animation ec="1000" by the UN wonder's decision tree;
  * effects hang on bones of the skinned model (TimedTrigger, like the Great Lighthouse's fire).
Curves use the stock formats only: DaIdentity, D3Constant32f, D4nK16uC15u (see granim.py).
Material: the proven building material with ShaderSet BuildingShader_Skinned and SkinBoneCount 32,
which is exactly how the UN's skinned material differs from its static one.
"""
import copy
import math
import os
import struct

import gr2
import granim

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
VENDOR = os.path.join(ROOT, 'vendor', 'civ5')
BUILDING_TEMPLATE = os.path.join(VENDOR, 'template_poly_palace.gr2')    # stock Polynesian palace
FX_TEMPLATE = os.path.join(VENDOR, 'fx_ind_lighthouse.gr2')               # stock skinned effect mesh
ANIM_TEMPLATE = os.path.join(VENDOR, 'fx_ind_lighthouse_idlea.gr2')       # stock idle animation
ANIMATED_DT = 'United_Nations_DecistionTree.ddtxml'    # stock; the decision tree of the animated UN wonder
STATIC_DT = 'Wonder_DecisionTree.ddtxml'
MAX_PART_VERTS = 32000


# --------------------------------------------------------------------------- small helpers
def inv_translation(p):
    """Granny InverseWorldTransform (row-major, translation in the last row) of a bone at p."""
    return [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, -p[0], -p[1], -p[2], 1.0]


def make_bone(proto, name, parent, local, world):
    b = copy.deepcopy(proto)
    b.update({'Name': name, 'ParentIndex': parent,
              'Transform': {'Flags': 1 if any(local) else 0, 'Position': list(local),
                            'Orientation': [0.0, 0.0, 0.0, 1.0],
                            'ScaleShear': [1.0, 0, 0, 0, 1.0, 0, 0, 0, 1.0]},
              'InverseWorldTransform': inv_translation(world)})
    return b


def obb(points):
    return ([min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)])


def building_material(proto, name, diffuse, sref, skinned=False):
    mat = copy.deepcopy(proto)
    mat['Name'] = name
    for m, tex in zip(mat['Maps'], (diffuse, sref)):
        m['Map']['Name'] = tex
        m['Map']['Texture']['FromFileName'] = tex
        m['Map']['ExtendedData'].value['File Name'] = tex
    ext = mat['ExtendedData'].value
    ext['FallbackMtl'] = [{'String': ''}]
    dt = ext['ParameterSet1']['ParamDataT']
    for d in dt:
        d['String'] = ''
    dt[0]['String'] = diffuse
    dt[4]['String'] = sref
    if skinned:
        ext['ShaderSet'] = 'BuildingShader_Skinned'
        ext['SkinBoneCount'] = 32
    return mat


def topology(tris):
    flat = [i for t in tris for i in t]
    return {'Groups': [{'MaterialIndex': 0, 'TriFirst': 0, 'TriCount': len(tris)}],
            'Indices': [], 'Indices16': struct.pack('<%dH' % len(flat), *flat),
            'VertexToVertexMap': [], 'VertexToTriangleMap': [], 'SideToNeighborMap': [],
            'BonesForTriangle': [], 'TriangleToBoneIndices': [], 'TriAnnotationSets': []}


# --------------------------------------------------------------------------- building .gr2
def write_building(out_dir, name, static, eye=None, rig=None):
    """static / eye: dict(verts, tris, diffuse, sref) in MODEL units; verts = (pos, nrm, tan, bin, uv).
    rig: dict(pivot=(x,y,z), bones=[(name, parent_name, world_pos)]) for the skinned model; its bones
    are 'eyeroot' (origin) and 'eyepivot' (at pivot) plus the extra ones. Returns the bone list."""
    f = gr2.read(BUILDING_TEMPLATE)
    root = f.root()
    tc_mat, b_tmpl = root['Materials'][0], root['Materials'][1]
    tc_skel, tc_vd, tc_topo, tc_mesh, tc_model = (root['Skeletons'][0], root['VertexDatas'][0],
                                                  root['TriTopologies'][0], root['Meshes'][0], root['Models'][0])
    # as in the proven static writer (tools/capitals/civ5model.py)
    for m in tc_mat['Maps']:
        m['Map']['Texture']['FromFileName'] = 'Generic_Grey_8.dds'
        m['Map']['ExtendedData'].value['File Name'] = 'Generic_Grey_8.dds'
    for i in (0, 4, 8):
        tc_mat['ExtendedData'].value['ParameterSet0']['ParamDataT'][i]['String'] = 'Generic_Grey_8.dds'
    tc_vd['VertexComponentNames'][4]['String'] = 'TextureCoordinates0'
    bone_proto = tc_skel['Bones'][0]

    # ---- static building (identical construction to the proven landmarks)
    vmembers = tc_vd['Vertices'].members
    sv, st = static['verts'], static['tris']
    assert len(sv) < MAX_PART_VERTS, 'static part too big for 16-bit indices'
    vb = bytearray()
    for p, n, t, b, uv in sv:
        vb += struct.pack('<15f', *p, *n, *t, *b, uv[0], uv[1], 0.0)
    s_mat = building_material(b_tmpl, name, static['diffuse'], static['sref'])
    s_vd = {'Vertices': gr2.Variant(vmembers, bytes(vb)),
            'VertexComponentNames': [{'String': s} for s in ('Position', 'Normal', 'Tangent', 'Binormal',
                                                              'TextureCoordinates0')],
            'VertexAnnotationSets': []}
    s_topo = topology(st)
    lo, hi = obb([v[0] for v in sv])
    s_bone = make_bone(bone_proto, name, -1, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    s_skel = {'Name': name, 'Bones': [s_bone], 'LODType': 0, 'ExtendedData': None}
    s_mesh = {'Name': name, 'PrimaryVertexData': s_vd, 'MorphTargets': [], 'PrimaryTopology': s_topo,
              'MaterialBindings': [{'Material': s_mat}],
              'BoneBindings': [{'BoneName': name, 'OBBMin': lo, 'OBBMax': hi, 'TriangleIndices': []}],
              'ExtendedData': None}
    s_model = dict(tc_model)
    s_model.update({'Name': name, 'Skeleton': s_skel, 'MeshBindings': [{'Mesh': s_mesh}]})

    mats, skels, vds, topos, meshes, models = [tc_mat, s_mat], [tc_skel, s_skel], [tc_vd, s_vd], \
        [tc_topo, s_topo], [tc_mesh, s_mesh], [tc_model, s_model]
    bones_out = []
    if eye is not None:
        ename = name + '_Eye'
        pivot = tuple(rig['pivot'])
        # skeleton: eyeroot (origin) -> eyepivot (animated) -> effect bones; parents before children
        spec = [('eyeroot', None, (0.0, 0.0, 0.0)), ('eyepivot', 'eyeroot', pivot)] + list(rig['bones'])
        index, world = {}, {}
        bones = []
        for bname, parent, wpos in spec:
            assert bname == bname.lower() and ' ' not in bname, 'bone names: lower case only (track order)'
            pi = -1 if parent is None else index[parent]
            local = tuple(wpos[i] - (world[parent][i] if parent else 0.0) for i in range(3))
            bones.append(make_bone(bone_proto, bname, pi, local, wpos))
            index[bname], world[bname] = len(bones) - 1, tuple(wpos)
            bones_out.append((bname, parent, tuple(wpos), local))
        e_skel = {'Name': ename, 'Bones': bones, 'LODType': 0, 'ExtendedData': None}
        # skinned vertex layout: copied from the stock skinned effect mesh (same as the UN's)
        fx = gr2.read(FX_TEMPLATE).root()
        smembers = fx['Meshes'][0]['PrimaryVertexData']['Vertices'].members
        assert [m.name for m in smembers] == ['Position', 'BoneWeights', 'BoneIndices', 'Normal', 'Tangent',
                                              'Binormal', 'TextureCoordinates0'], [m.name for m in smembers]
        ev, et = eye['verts'], eye['tris']
        assert len(ev) < MAX_PART_VERTS
        vb = bytearray()
        still = eye.get('still') or [False] * len(ev)     # True: on binding 1 = eyeroot (never moves)
        for (p, n, t, b, uv), st in zip(ev, still):     # else fully on mesh bone binding 0 = eyepivot
            vb += struct.pack('<3f4B4B12f', *p, 255, 0, 0, 0, 1 if st else 0, 0, 0, 0, *n, *t, *b, uv[0], uv[1], 0.0)
        e_mat = building_material(b_tmpl, ename, eye['diffuse'], eye['sref'], skinned=True)
        e_vd = {'Vertices': gr2.Variant(smembers, bytes(vb)),
                'VertexComponentNames': [{'String': m.name} for m in smembers], 'VertexAnnotationSets': []}
        e_topo = topology(et)
        lo, hi = obb([tuple(v[0][i] - pivot[i] for i in range(3)) for v in ev])      # in eyepivot space
        e_mesh = {'Name': ename, 'PrimaryVertexData': e_vd, 'MorphTargets': [], 'PrimaryTopology': e_topo,
                  'MaterialBindings': [{'Material': e_mat}],
                  'BoneBindings': [{'BoneName': 'eyepivot', 'OBBMin': lo, 'OBBMax': hi, 'TriangleIndices': []}],
                  'ExtendedData': None}
        if any(still):
            slo, shi = obb([v[0] for v, st in zip(ev, still) if st])                       # eyeroot = origin
            e_mesh['BoneBindings'].append({'BoneName': 'eyeroot', 'OBBMin': slo, 'OBBMax': shi, 'TriangleIndices': []})
        e_model = dict(tc_model)
        e_model.update({'Name': ename, 'Skeleton': e_skel, 'MeshBindings': [{'Mesh': e_mesh}]})
        mats.append(e_mat); skels.append(e_skel); vds.append(e_vd); topos.append(e_topo)
        meshes.append(e_mesh); models.append(e_model)

    root['ArtToolInfo']['FromArtToolName'] = 'Blender'
    root['ExporterInfo']['ExporterName'] = 'civ5me tools/landmarks'
    root['FromFileName'] = name + '.blend'
    root.update({'Materials': mats, 'Skeletons': skels, 'VertexDatas': vds, 'TriTopologies': topos,
                 'Meshes': meshes, 'Models': models})
    os.makedirs(out_dir, exist_ok=True)
    size = gr2.write(os.path.join(out_dir, name + '.gr2'), f.root_type, root, f.tag)
    return size, bones_out


# --------------------------------------------------------------------------- idle animation .gr2
class Curves:
    """Curve variants built from the member definitions of the stock template animation."""

    def __init__(self, anim_root):
        tracks = {t['Name']: t for t in anim_root['TrackGroups'][0]['TransformTracks']}
        self.m_ident = tracks['World']['PositionCurve']['CurveData'].members
        self.m_const3 = tracks['Point02']['PositionCurve']['CurveData'].members
        self.m_quat = tracks['Point01']['OrientationCurve']['CurveData'].members

    def identity(self, dim):
        return {'CurveData': gr2.Variant(self.m_ident, {'CurveDataHeader_DaIdentity': {'Format': 2, 'Degree': 0},
                                                        'Dimension': dim})}

    def const3(self, v):
        return {'CurveData': gr2.Variant(self.m_const3, {'CurveDataHeader_D3Constant32f': {'Format': 4, 'Degree': 0},
                                                         'Padding': 0, 'Controls': [float(x) for x in v]})}

    def yaw(self, c):
        return {'CurveData': gr2.Variant(self.m_quat, {
            'CurveDataHeader_D4nK16uC15u': {'Format': 8, 'Degree': 2}, 'ScaleOffsetTableEntries': c['entries'],
            'OneOverKnotScale': c['one_over'], 'KnotsControls': [{'UInt16': k} for k in c['knots'] + c['controls']]})}


def track(curves, name, local=(0.0, 0.0, 0.0), yaw=None):
    return {'Name': name, 'Flags': 0,
            'OrientationCurve': curves.yaw(yaw) if yaw else curves.identity(4),
            'PositionCurve': curves.const3(local) if any(abs(x) > 1e-9 for x in local) else curves.identity(3),
            'ScaleShearCurve': curves.identity(9)}


def write_animation(path, anim_name, duration, groups):
    """groups: [(model name, [track dicts])]. Tracks are sorted by name like the stock files."""
    f = gr2.read(ANIM_TEMPLATE)
    root = f.root()
    tg_proto = root['TrackGroups'][0]
    tgs = []
    for gname, tracks in groups:
        tg = {k: v for k, v in tg_proto.items()}
        names = [t['Name'] for t in tracks]
        assert len(set(n.lower() for n in names)) == len(names)
        tg.update({'Name': gname, 'TransformTracks': sorted(tracks, key=lambda t: t['Name'].lower()),
                   'VectorTracks': [], 'TransformLODErrors': [], 'TextTracks': [],
                   'InitialPlacement': {'Flags': 0, 'Position': [0.0, 0.0, 0.0], 'Orientation': [0.0, 0.0, 0.0, 1.0],
                                        'ScaleShear': [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]},
                   'LoopTranslation': [0.0, 0.0, 0.0], 'PeriodicLoop': None, 'RootMotion': None,
                   'ExtendedData': None})
        tgs.append(tg)
    anim = dict(root['Animations'][0])
    anim.update({'Name': anim_name, 'Duration': float(duration), 'TrackGroups': tgs})
    root['TrackGroups'] = tgs
    root['Animations'] = [anim]
    root['FromFileName'] = anim_name + '.blend'
    root['ExporterInfo']['ExporterName'] = 'civ5me tools/landmarks'
    return gr2.write(path, f.root_type, root, f.tag)


def write_idle(out_dir, name, bones, gaze):
    """Idle animation for write_building's models: everything still except eyepivot, which turns
    about +Z by gaze['fn'](t) degrees. Returns (file name, curve dict)."""
    curves = Curves(gr2.read(ANIM_TEMPLATE).root())
    c = granim.yaw_curve_value(gaze['fn'], gaze['T'], gaze['spans'])
    eye_tracks = [track(curves, bname, local, yaw=c if bname == 'eyepivot' else None)
                  for bname, parent, wpos, local in bones]
    groups = [('Tree cut', [track(curves, 'Tree cut')]), (name, [track(curves, name)]),
              (name + '_Eye', eye_tracks)]
    fn = name + '_Idle.gr2'
    write_animation(os.path.join(out_dir, fn), name + '_Idle', gaze['T'], groups)
    return fn, c


# --------------------------------------------------------------------------- .fxsxml + triggers
def write_triggers(path, triggers):
    """triggers: [(bone, visual effect name)] (from the loop's start, lasting) or [(bone, effect, time, duration)]:
    a one-shot effect at `time` seconds of the animation (duration 0, like the stock cannon smoke)."""
    tl = ['<trigger_system type="FGrannyTimedTriggerSystem">', '  <event_tracks>', '    <event_track ec="1000">',
          '      <track id="1" name="Sound" />', '      <track id="2" name="Effect" />',
          '      <track id="3" name="Transfer" />', '    </event_track>', '  </event_tracks>', '  <triggers>']
    for i, tr in enumerate(triggers):
        bone, effect = tr[:2]
        time_, dur = (tr[2], tr[3]) if len(tr) > 2 else (0, 10)
        tl.append('    <trigger type="FTimedTriggerEffect" id="%d" time="%s" duration="%s" repeat="0" ec="1000" '
                  'track="2" tier="0" event="%s" bone="%s" />' % (i + 1, ('%g' % time_), ('%g' % dur), effect, bone))
    tl += ['  </triggers>', '</trigger_system>']
    with open(path, 'w', newline='\r\n') as f:
        f.write('\n'.join(tl) + '\n')


def write_fxsxml(path, mesh, textures, animation=None, triggers_file=None, trigger_model=None, bones=(),
                 decision_tree=STATIC_DT):
    L = ['<Asset>', '\t<Mesh file="%s"/>' % mesh]
    if animation:
        L.append('\t<Animation file="%s" name="Idle" ec="1000" source="Max"/>' % animation)
    L += ['\t<Texture file="%s"/>' % t for t in textures]
    if bones:
        L.append('\t<BoneUsage>')
        L += ['\t\t<Bone name="%s"/>' % b for b in bones]
        L.append('\t</BoneUsage>')
    if triggers_file:
        L.append('\t<TimedTrigger file="%s" source="Tool" model="%s" state="0,1,2,3"/>' % (triggers_file, trigger_model))
    L.append('\t<DecisionTree file="%s" source="Tool"/>' % decision_tree)
    L.append('</Asset>')
    with open(path, 'w', newline='\r\n') as f:
        f.write('\n'.join(L) + '\n')

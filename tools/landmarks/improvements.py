"""Landmark IMPROVEMENTS (docs/LANDMARKS.md; research in docs/CITY_ARCHITECTURE_RESEARCH.md).

A landmark is a purely visual tile improvement that MEC_LandmarkImprovements.lua puts on a city's plot with
Plot:SetImprovementType. The city's own art (houses, buildings) is never touched. Improvement art is ordinary
ArtDefine_* database rows; effects use the DLC's VisEffect defines.

Which city gets which landmark: the city's name KEY (synchronised, the same with or without Dynamic City Naming),
or a name a player typed (aliases, case-insensitive). Every other city keeps stock art.

The art is vendored (vendor/landmarks/<Model>/): the exact files that drew in game, so the pack builds without
Blender. The Blender sources are tools/landmarks/models/*.py.

History of tests (all with this mechanism, 2026-11-24): Barad-dur v4 (static) on every city and city-state + control
plots (Elven Battle Tower, stock citadel art): all drew. Moria v3 on every city and city-state: all drew.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
VENDOR = os.path.join(ROOT, 'vendor', 'landmarks')

GAMEDATA_XML = 'MEDLC_LandmarkImprovements.xml'
TEXT_XML = 'MEDLC_Text_LandmarkImprovements.xml'
VISEFFECTS_XML = 'MEDLC_LandmarkImprovements_VisEffects.xml'
VISMODELS_XML = 'MEDLC_LandmarkImprovements_VisEffectModels.xml'
LUA = 'MEC_LandmarkImprovements.lua'

# One row per landmark.
#   key        -> IMPROVEMENT_MEC_LM_<key>, art tag ART_DEF_IMPROVEMENT_MEC_LM_<key>, fxsxml MEC_LMI_<Key>.fxsxml
#   dir        -> vendor/landmarks/<dir>: every file there is copied into the pack as-is
#   gr2 / textures -> what the generated .fxsxml names
#   scale      -> ArtDefine_Landmarks.Scale (in-game size = file size x scale; the hex is about +-32..41)
#   animation  -> (file, name) of an idle loop: played by the stock LandmarkDecisionTree (like the stock oil rig)
#   trigger    -> (ftsxml, model) TimedTrigger for effects on bones; bones = BoneUsage
#   name_keys / aliases -> which cities get it
IMPROVEMENTS = [
    # Moria v3 (tools/landmarks/models/moria.py): baked, 16.4k vertices, static. File +-391 x (-268..+435) x 471;
    # Scale 0.094 -> ~+-37 x (-25..+41), ~44 high. Drew on every city and city-state (test 2, 2026-11-24).
    dict(key='MORIA', title='Moria', dir='Moria',
         gr2='MEC_LM_Moria.gr2',
         textures=['Generic_Grey_8.dds', 'MEC_LM_Moria_DIFF.dds', 'MEC_LM_Moria_SREF.dds'],
         scale=0.094,
         name_keys=['TXT_KEY_CITY_NAME_MEC_MORIA'],
         aliases=['Moria', 'Khazad-dum', 'Khazad-dûm', 'Khazad Dum', 'Khazad Dûm']),
    # Barad-dur v3, the Eye of Sauron (models/barad_dur.py at commit 384416f): fortress + tower (static) and a skinned
    # Eye that looks around (6 s idle loop), 8 fires around the Eye + a blaze in it (stock Great Lighthouse fire)
    # and a searchlight beam (our model effect, MEC_EyeBeam). File +-94 x +-109 x 188 (made for wonder fScale 0.25,
    # where the effect sizes were tuned). Scale 0.3 -> ~+-28 x +-33, ~56 high (inside the proven 57).
    dict(key='BARAD_DUR', title='Barad-dûr', dir='BaradDur',
         gr2='MEC_LM_BaradDur.gr2',
         textures=['Generic_Grey_8.dds', 'MEC_LM_BaradDur_DIFF.dds', 'MEC_LM_BaradDur_SREF.dds',
                   'MEC_LM_BaradDur_Eye_DIFF.dds', 'MEC_LM_BaradDur_Eye_SREF.dds'],
         animation=('MEC_LM_BaradDur_Idle.gr2', 'Idle'),
         bones=['fxfire%d' % i for i in range(8)] + ['fxcore', 'fxbeam'],
         trigger=('FX_Triggers_MEC_LM_BaradDur.ftsxml', 'MEC_LM_BaradDur_Eye'),
         scale=0.3,
         name_keys=['TXT_KEY_CITY_NAME_MEC_BARAD_DUR'],
         aliases=['Barad Dur', 'Barad-dur', 'Barad-dûr', 'Barad Dûr', 'Baraddur']),
]

# Effects used by the triggers above (VisEffectInfoDefines / VisEffectModelDefines in the DLC package).
# Values as tuned for Barad-dur v3 in the old city-art path (tools/landmarks/landmarks.py EFFECTS, 2026-11-22).
VIS_EFFECTS = [
    # (name, rotation x, scale, particle effect or None, model effect or None)
    ('ART_DEF_VEFFECT_MEC_EYE_FIRE', 90.0, 0.4, 'ART_DEF_PEFFECT_GREAT_LIGHTHOUSE_FIRE', None),
    ('ART_DEF_VEFFECT_MEC_EYE_BLAZE', 90.0, 1.0, 'ART_DEF_PEFFECT_GREAT_LIGHTHOUSE_FIRE', None),
    ('ART_DEF_VEFFECT_MEC_EYE_BEAM', 0.0, 13.0, None, 'ART_DEF_MEFFECT_MEC_EYE_BEAM'),
]
VIS_MODELS = [('ART_DEF_MEFFECT_MEC_EYE_BEAM', 'MEC_EyeBeam.fxsxml')]     # file in vendor/landmarks/BaradDur

# ----- test switches (all off in a release) -------------------------------------------------------------------
# A key of IMPROVEMENTS: EVERY city and city-state gets that landmark, ignoring the names (render tests).
ALL_CITIES = None
# Control plots next to the anchor capital: (letter, key). Test 1 used A Barad-dur / B Elven Battle Tower /
# C stock citadel art (all drew); those rows were removed after the test.
CONTROLS = []
ANCHOR_CIV = 'CIVILIZATION_MEC_MORDOR'      # fallback: the first human player's capital
# Fog of war off for human teams.
REVEAL_MAP = True                           # ON for the user's check of this build; False for the release commit


def improvement(row):
    return 'IMPROVEMENT_MEC_LM_' + row['key']


def art_tag(row):
    return 'ART_DEF_IMPROVEMENT_MEC_LM_' + row['key']


def own_fxsxml(row):
    return 'MEC_LMI_%s.fxsxml' % row['key'].title().replace('_', '')


def src_dir(row):
    return os.path.join(VENDOR, row['dir'])


def fxsxml_text(row):
    """Like the stock improvement files: mesh + textures; an animated model gets its idle animation and the stock
    LandmarkDecisionTree (Oil_Rig.fxsxml); effects are TimedTriggers on bones (the stock gold mine)."""
    L = ['<Asset>', '  <Mesh file="%s" source="Max" />' % row['gr2']]
    if row.get('animation'):
        L.append('  <Animation file="%s" name="%s" ec="1000" source="Max" layer="None" />' % row['animation'])
    L += ['  <Texture file="%s" source="Max" />' % t for t in row['textures']]
    if row.get('bones'):
        L += ['  <BoneUsage>'] + ['    <Bone name="%s" />' % b for b in row['bones']] + ['  </BoneUsage>']
    if row.get('trigger'):
        L.append('  <TimedTrigger file="%s" source="Tool" model="%s" state="0,1,2,3" />' % row['trigger'])
    if row.get('animation'):
        L.append('  <DecisionTree file="LandmarkDecisionTree.ddtxml" source="Tool" />')
    L.append('</Asset>')
    return '\n'.join(L) + '\n'


def _x(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def gamedata():
    L = ['<?xml version="1.0" encoding="utf-8"?>',
         '<!-- Middle-earth landmark improvements: purely visual, placed only by MEC_LandmarkImprovements.lua '
         '(no Build row, no yields) -->',
         '<GameData>', '\t<ArtDefine_LandmarkTypes>']
    for r in IMPROVEMENTS:
        L.append('\t\t<Row><Type>%s</Type><LandmarkType>Improvement</LandmarkType><FriendlyName>%s</FriendlyName></Row>'
                 % (art_tag(r), _x(r['title'])))
    L += ['\t</ArtDefine_LandmarkTypes>', '\t<ArtDefine_Landmarks>']
    for r in IMPROVEMENTS:
        for state in ('Constructed', 'Pillaged'):
            L.append('\t\t<Row><Era>Any</Era><State>%s</State><Scale>%s</Scale><ImprovementType>%s</ImprovementType>'
                     '<LayoutHandler>SNAPSHOT</LayoutHandler><ResourceType>ART_DEF_RESOURCE_ALL</ResourceType>'
                     '<Model>%s</Model><TerrainContour>1</TerrainContour></Row>'
                     % (state, r['scale'], art_tag(r), own_fxsxml(r)))
    L += ['\t</ArtDefine_Landmarks>', '\t<ArtDefine_StrategicView>']
    for r in IMPROVEMENTS:
        L.append('\t\t<Row><StrategicViewType>%s</StrategicViewType><TileType>Improvement</TileType>'
                 '<Asset>SV_Citadel.dds</Asset></Row>' % art_tag(r))
    L += ['\t</ArtDefine_StrategicView>', '\t<Improvements>']
    for r in IMPROVEMENTS:
        t = improvement(r)
        L.append('\t\t<Row>')
        for k, v in (('Type', t), ('Description', 'TXT_KEY_' + t), ('Civilopedia', 'TXT_KEY_' + t + '_HELP'),
                     ('Help', 'TXT_KEY_' + t + '_HELP'), ('ArtDefineTag', art_tag(r)),
                     ('Permanent', 'true'), ('PillageGold', 0),
                     ('PortraitIndex', 35), ('IconAtlas', 'TERRAIN_ATLAS')):     # the citadel icon
            L.append('\t\t\t<%s>%s</%s>' % (k, _x(str(v)), k))
        L.append('\t\t</Row>')
    L += ['\t</Improvements>', '</GameData>']
    return '\n'.join(L) + '\n'


def text():
    L = ['<?xml version="1.0" encoding="utf-8"?>', '<GameData>', '\t<Language_en_US>']
    for r in IMPROVEMENTS:
        t = improvement(r)
        L.append('\t\t<Row Tag="TXT_KEY_%s"><Text>%s (landmark)</Text></Row>' % (t, _x(r['title'])))
        L.append('\t\t<Row Tag="TXT_KEY_%s_HELP"><Text>The landmark of %s. Purely visual: no effect on the game.'
                 '</Text></Row>' % (t, _x(r['title'])))
    L += ['\t</Language_en_US>', '</GameData>']
    return '\n'.join(L) + '\n'


def vis_effects():
    L = ['<?xml version="1.0" encoding="utf-8"?>',
         '<VisEffectArtInfos xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
         'xsi:noNamespaceSchemaLocation="Civ5ArtDefines_VisEffects.xsd">']
    for name, rotx, scale, particle, model in VIS_EFFECTS:
        L += ['\t<VisEffectArtInfo>', '\t\t<Name>%s</Name>' % name, '\t\t<Transform>',
              '\t\t\t<Translation x="0.0" y="0.0" z="0.0"/>', '\t\t\t<Rotation x="%.1f" y="0.0" z="0.0"/>' % rotx,
              '\t\t\t<Scale>%s</Scale>' % scale, '\t\t</Transform>',
              '\t\t<fBaseDuration>0.01</fBaseDuration>', '\t\t<fBaseDurationScale>1.0</fBaseDurationScale>']
        if particle:
            L += ['\t\t<ParticleEffects>', '\t\t\t<ParticleEffect>', '\t\t\t\t<Name>%s</Name>' % particle,
                  '\t\t\t</ParticleEffect>', '\t\t</ParticleEffects>']
        if model:
            L += ['\t\t<ModelEffects>', '\t\t\t<ModelEffect>', '\t\t\t\t<Name>%s</Name>' % model,
                  '\t\t\t</ModelEffect>', '\t\t</ModelEffects>']
        L.append('\t</VisEffectArtInfo>')
    L.append('</VisEffectArtInfos>')
    return '\n'.join(L) + '\n'


def vis_effect_models():
    L = ['<?xml version="1.0" encoding="utf-8"?>',
         '<VisEffectModelArtInfos xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
         'xmlns:xsd="http://www.w3.org/2001/XMLSchema">']
    for name, fx in VIS_MODELS:
        L += ['\t<VisEffectModelArtInfo>', '\t\t<Name>%s</Name>' % name, '\t\t<File>%s</File>' % fx,
              '\t\t<fScale>1.0</fScale>', '\t\t<fScrollTime>1.0</fScrollTime>', '\t</VisEffectModelArtInfo>']
    L.append('</VisEffectModelArtInfos>')
    return '\n'.join(L) + '\n'


def lua_table():
    """Replaces the -- @@LANDMARK_TABLE@@ line of MEC_LandmarkImprovements.lua."""
    def s(v):
        return '"%s"' % v if v is not None else 'false'

    def q(v):   # Lua string literal (UTF-8 kept)
        return '"%s"' % v.replace('\\', '\\\\').replace('"', '\\"')
    defs = ', '.join('{ Improvement = %s, Keys = { %s }, Aliases = { %s } }' % (
        q(improvement(r)), ', '.join(q(k) for k in r['name_keys']), ', '.join(q(a) for a in r['aliases']))
        for r in IMPROVEMENTS)
    all_cities = next((improvement(r) for r in IMPROVEMENTS if r['key'] == ALL_CITIES), None)
    return ('g_LandmarkDefs = { %s }\n' % defs
            + 'g_AllCities = %s\n' % s(all_cities)
            + 'g_Controls = { %s }\n' % ', '.join('{ "%s", "IMPROVEMENT_MEC_LM_%s" }' % (c, k) for c, k in CONTROLS)
            + 'g_AnchorCiv = %s\n' % s(ANCHOR_CIV)
            + 'g_RevealMap = %s' % ('true' if REVEAL_MAP else 'false'))

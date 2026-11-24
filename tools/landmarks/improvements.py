"""Landmark IMPROVEMENTS (docs/CITY_ARCHITECTURE_RESEARCH.md, Approach C).

A landmark is a purely visual tile improvement that MEC_LandmarkImprovements.lua puts on a city's plot with
Plot:SetImprovementType. The city's own art (houses, buildings) is never touched. Improvement art is ordinary
ArtDefine_* database rows, so it needs no WonderDefines.

2026-11-24 TEST (user: "test Mordor and its capital Barad-dur relentlessly ... every city and every city state"):
  * EVERY city and city-state plot gets Barad-dur (ALL_CITIES = True),
  * three CONTROL plots next to Mordor's capital (or the human's capital if Mordor isn't in the game):
      A  Barad-dur on a plain plot  -> does our model draw as an improvement at all?
      B  Elven Battle Tower (Nomad's BFME II conversion, shipped by ME Civilizations v9) -> community art
      C  stock citadel art          -> does a Lua-placed improvement draw at all?
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'build', 'landmarks', 'out')        # prebuilt models (tools/landmarks/build_models.py)

GAMEDATA_XML = 'MEDLC_LandmarkImprovements.xml'
TEXT_XML = 'MEDLC_Text_LandmarkImprovements.xml'
LUA = 'MEC_LandmarkImprovements.lua'

# One row per landmark improvement.
#   key     -> IMPROVEMENT_MEC_LM_<key>, art tag ART_DEF_IMPROVEMENT_MEC_LM_<key> (unless art_tag reuses a stock one)
#   gr2     -> our model in build/landmarks/out, written into a new improvement .fxsxml (fxsxml_textures)
#   fxsxml  -> an existing .fxsxml already in the pack (built, pillaged)
#   scale   -> ArtDefine_Landmarks.Scale. Stock improvements are authored at Scale 1 with the hex ~ +-45 units.
#              Barad-dur v4's file is +-308 x +-346, 478 high (written for wonder fScale 0.05), so 0.12 makes it
#              ~+-41 x 57 high: tile-filling. Calibrate from the in-game screenshot (research plan step 2).
IMPROVEMENTS = [
    dict(key='BARAD_DUR', title='Barad-dûr',
         gr2='MEC_LM_BaradDur.gr2',
         fxsxml_textures=['MEC_LM_BaradDur_DIFF.dds', 'MEC_LM_BaradDur_SREF.dds', 'Generic_Grey_8.dds'],
         copy=['MEC_LM_BaradDur_DIFF.dds', 'MEC_LM_BaradDur_SREF.dds'],
         scale=0.12, sv='SV_Citadel.dds'),
    dict(key='TOWER', title='Elven Battle Tower (control)',
         fxsxml=('Battle_Tower_B.fxsxml', 'Battle_Tower_P.fxsxml'),   # MEC Wood Elves/Art/Improvements (in the pack)
         scale=1.0, sv='SV_Citadel.dds'),
    dict(key='CITADEL', title='Citadel art (control)',
         art_tag='ART_DEF_IMPROVEMENT_CITADEL'),                       # stock art rows, nothing new
]

# Which landmark every city plot gets during the test (None = name rules only, not implemented yet).
ALL_CITIES = 'BARAD_DUR'

# Control plots around the anchor capital: (control letter, improvement key), filled in direction order.
CONTROLS = [('A', 'BARAD_DUR'), ('B', 'TOWER'), ('C', 'CITADEL')]
ANCHOR_CIV = 'CIVILIZATION_MEC_MORDOR'      # fallback: the first human player's capital

# Fog of war off for human teams (test only; set False before sharing the pack).
REVEAL_MAP = True


def improvement(row):
    return 'IMPROVEMENT_MEC_LM_' + row['key']


def art_tag(row):
    return row.get('art_tag') or 'ART_DEF_IMPROVEMENT_MEC_LM_' + row['key']


def own_fxsxml(row):
    """Name of the .fxsxml we write for a row with our own gr2 (None otherwise)."""
    return 'MEC_LMI_%s.fxsxml' % row['key'].title().replace('_', '') if row.get('gr2') else None


def fxsxml_text(row):
    """Like the stock improvement files (Anc_Citadel.fxsxml): a mesh and its textures, no decision tree."""
    L = ['<Asset>', '  <Mesh file="%s" source="Max" />' % row['gr2']]
    L += ['  <Texture file="%s" source="Max" />' % t for t in row['fxsxml_textures']]
    L.append('</Asset>')
    return '\n'.join(L) + '\n'


def asset_files(row):
    """Files copied from build/landmarks/out for this row."""
    return ([row['gr2']] if row.get('gr2') else []) + row.get('copy', [])


def _x(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def gamedata():
    L = ['<?xml version="1.0" encoding="utf-8"?>',
         '<!-- Middle-earth landmark improvements: purely visual, placed only by MEC_LandmarkImprovements.lua '
         '(no Build row, no yields) -->',
         '<GameData>']
    own = [r for r in IMPROVEMENTS if not r.get('art_tag')]
    L.append('\t<ArtDefine_LandmarkTypes>')
    for r in own:
        L.append('\t\t<Row><Type>%s</Type><LandmarkType>Improvement</LandmarkType><FriendlyName>%s</FriendlyName></Row>'
                 % (art_tag(r), _x(r['title'])))
    L += ['\t</ArtDefine_LandmarkTypes>', '\t<ArtDefine_Landmarks>']
    for r in own:
        built, pillaged = r.get('fxsxml') or (own_fxsxml(r), own_fxsxml(r))
        for state, model in (('Constructed', built), ('Pillaged', pillaged)):
            L.append('\t\t<Row><Era>Any</Era><State>%s</State><Scale>%s</Scale><ImprovementType>%s</ImprovementType>'
                     '<LayoutHandler>SNAPSHOT</LayoutHandler><ResourceType>ART_DEF_RESOURCE_ALL</ResourceType>'
                     '<Model>%s</Model><TerrainContour>1</TerrainContour></Row>'
                     % (state, r['scale'], art_tag(r), model))
    L += ['\t</ArtDefine_Landmarks>', '\t<ArtDefine_StrategicView>']
    for r in own:
        L.append('\t\t<Row><StrategicViewType>%s</StrategicViewType><TileType>Improvement</TileType>'
                 '<Asset>%s</Asset></Row>' % (art_tag(r), r['sv']))
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
        L.append('\t\t<Row Tag="TXT_KEY_%s_HELP"><Text>A Middle-earth landmark. Purely visual: no effect on the game.'
                 '</Text></Row>' % t)
    L += ['\t</Language_en_US>', '</GameData>']
    return '\n'.join(L) + '\n'


def lua_table():
    """Replaces the -- @@LANDMARK_TABLE@@ line of MEC_LandmarkImprovements.lua."""
    def s(v):
        return '"%s"' % v if v is not None else 'nil'
    return ('g_AllCities = %s\n' % s(improvement(dict(key=ALL_CITIES)) if ALL_CITIES else None)
            + 'g_Controls = { %s }\n' % ', '.join('{ "%s", "%s" }' % (c, improvement(dict(key=k))) for c, k in CONTROLS)
            + 'g_AnchorCiv = %s\n' % s(ANCHOR_CIV)
            + 'g_Improvements = { %s }\n' % ', '.join('"%s"' % improvement(r) for r in IMPROVEMENTS)
            + 'g_RevealMap = %s' % ('true' if REVEAL_MAP else 'false'))

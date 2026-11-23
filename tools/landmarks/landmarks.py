"""Per-city landmark models (docs/CITY_MODELS.md, Plan A).

One invisible dummy building per landmark. The in-game script MEC_Landmarks.lua gives it to the
city whose name matches (text key, or a literal name typed by a player), and the building's plain
ArtDefineTag points at our WonderArtInfo. Cities without a matching name never get one, so they
keep the stock art.

Add a landmark = add one row here + one model module in tools/landmarks/models/.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'build', 'landmarks', 'out')        # made by tools/landmarks/build_models.py (Blender)
PREVIEW = os.path.join(ROOT, 'build', 'landmarks', 'preview')

# Buildings.DisplayPosition is a bit mask of art slots: 1/2/4/64 wonders (+ castle, colosseum,
# stadium), 8 lighthouse, 16 harbor, 32 palace.
# The landmark takes the palace slot (32), the city centre. (2026-11-23: slots 1/2/4 were tried; in a correct
# automated run, nothing drew in them for a size-1 city, not even stock art. An earlier manual "slots work" result
# came from GameInfo.Buildings["TYPE"] returning the wrong row.)
DISPLAY_POSITION = 32

# ---------------------------------------------------------------------------------------------
# Render envelope, enforced by build_models.py. Every landmark is AUTHORED IN WORLD UNITS (origin =
# tile centre, z = 0 ground) and must fit inside these limits. Evidence (2026-11-22, docs/CITY_MODELS.md):
#  * the same Barad-dur file rendered at fScale 0.25 (26 world units tall) and left the whole city tile
#    empty at fScale 1.0 (106 tall). Footprint, fScale (stock Machu Picchu uses 1.0) and tree-cut size
#    (stock up to +-50) were all inside proven ranges, so HEIGHT is the variable that broke it;
#  * tallest stock wonder/palace art: 58 (Spaceship), then 39 (CN Tower); tallest custom model that
#    rendered: 46-47 (Minas Tirith at 0.77);
#  * the city hexagon is ~24 world units from centre to its flat sides (E/W), ~27.7 to its corners (N/S)
#    (Minas Tirith's 31.2-unit base at fScale 0.77 filled it exactly);
#  * largest stock wonder meshes: ~22k vertices (Colossus, Great Lighthouse), 512x512 textures.
# The vertices are multiplied by 1/scale when written, so fScale stays at the proven 0.25 and the
# world size comes from the geometry alone.
ENVELOPE = dict(max_height=48.0, min_z=-4.0, hex_in=24.0, hex_out=24.0 / 0.8660254, max_verts=22000,
                max_tris=20000)

LANDMARKS = [
    dict(key='BARAD_DUR',                      # BUILDING_MEC_LM_<key>, art tag MEC_LM_<key>
         title='Barad-dûr',
         module='barad_dur',                   # tools/landmarks/models/<module>.py
         model='MEC_LM_BaradDur',              # asset base name (.gr2/.fxsxml/_DIFF.dds/_SREF.dds)
         scale=0.25,                           # WonderArtInfo fScale: keep 0.25 (see ENVELOPE)
         name_keys=['TXT_KEY_CITY_NAME_MEC_BARAD_DUR'],
         # literal names a player may type when renaming a city (compared case-insensitively)
         aliases=['Barad Dur', 'Barad-dur', 'Barad-dûr', 'Barad Dûr', 'Baraddur'],
         # the module has build_eye()/rig()/GAZE: the Eye is a separate skinned, animated part with effects
         animated=True,
         test_prefix='Barad'),                 # diagnostic cities "Barad Test 1..3" (DIAGNOSTICS)
    dict(key='MOUNT_DOOM',
         title='Mount Doom',
         module='mount_doom',                  # a new volcano (not the stock Krakatoa) in Barad-dur's style
         model='MEC_LM_MountDoom',
         scale=0.25,
         # the same key whether the city got it from Mordor's city list or from Dynamic City Naming
         # (METSL_InGame stores the key with city:SetName). "Orodruin" is a different city name: no volcano.
         name_keys=['TXT_KEY_CITY_NAME_MEC_MOUNT_DOOM'],
         aliases=['Mount Doom'],
         # build_eye()/rig()/GAZE like Barad-dur: the animated part = three fell beasts circling the summit,
         # the effects = the eruption and fires on static bones
         animated=True,
         test_prefix='Doom',                   # diagnostic cities "Doom Test 1..3"
         # 2026-11-23 empty-tile hunt: show Barad-dur's art (the same files) so both cities use ONE asset.
         # Remove this line to bring back the volcano (models/mount_doom.py is unchanged).
         art_of='BARAD_DUR'),
]

# 2026-11-23 experiment (docs/CITY_MODELS.md §8, "one registration"): the second city has never drawn, while
# the capital usually does. Test whether the SECOND building / WonderArtInfo registration is the problem:
# Mount Doom's names go onto Barad-dur's row, so both cities get BUILDING_MEC_LM_BARAD_DUR and the pack has
# only ONE landmark building and ONE WonderArtInfo. Set to False to restore the separate Mount Doom row.
ONE_REGISTRATION = True
if ONE_REGISTRATION:
    _doom = [x for x in LANDMARKS if x['key'] == 'MOUNT_DOOM'][0]
    _barad = [x for x in LANDMARKS if x['key'] == 'BARAD_DUR'][0]
    _barad['name_keys'] = _barad['name_keys'] + _doom['name_keys']
    _barad['aliases'] = _barad['aliases'] + _doom['aliases']
    LANDMARKS.remove(_doom)

# 2026-11-23 experiment "capital 100%": which variant the real landmark shows. None = the full model (Eye animation,
# fire, beam). 'T1' = static fortress + tower only (no skinned Eye, no animation, no effects): an empty-tile launch
# showed the Eye's fire on the ground west of the tile, so the animated part is the first suspect.
SHOW_VARIANT = None   # 2026-11-23: back to the full model for the 'build it later' test (static was never tested)

# 2026-11-23 experiment (user): the model is NOT given at founding. The landmark is a normal building costing 1
# production, buildable only in a city whose name matches (GameEvents.CityCanConstruct in MEC_Landmarks.lua).
# Until it's built the city shows stock art; once built (next turn), our model is added to an existing city.
# False = given by Lua (see GIVE_AT_FOUNDING), never buildable.
# Result (user, 4 tries): drew on completion 3 times, not the 4th.
BUILDABLE = False

# 2026-11-23 (user): no building to choose. Lua gives the landmark on the owner's first turn AFTER the city was
# founded (PlayerDoTurn), never in the founding event itself, so the art is added to a city whose art already exists.
# True = old behaviour (given in PlayerCityFounded / CityCaptureComplete).
GIVE_AT_FOUNDING = False

# 2026-11-23: every stock .gr2 leaves the BoneBinding OBBMin/OBBMax at zero; ours had real boxes. If the engine uses
# them for the city group's bounds, a wrong box could stop the whole tile (houses too) from drawing. Never validly
# tested before (the T1Z probe went through the broken Cycle button). True = written zeroed like stock.
ZERO_OBB = True

# DEFAULT since 2026-11-24 (docs/CITY_MODELS.md §10): the landmark shows a known-good model that is NOT made by us
# (not Blender, not our .gr2 writer): vendor/landmarks/BaradDur/MEC_LM_BaradDur_Base.gr2 (source in SOURCE.md there),
# copied byte-identical. Our own models (build/landmarks/out) made the whole city tile vanish in some games; this one
# drew 5/5 through the same mechanism. None = our Blender model again (needs build_models.py output).
EXTERNAL_ART = dict(dir=os.path.join(ROOT, 'vendor', 'landmarks', 'BaradDur'), model='MEC_LM_BaradDur_Base', scale=0.05,
                    textures=['HBHagiaSophia_DIFF.dds', 'HBHagiaSophia_SREF.dds', 'Hagia_Sophia_DIFF.dds',
                              'Hagia_Sophia_SREF.dds', 'Generic_Grey_8.dds'])


def external_fxsxml():
    x = EXTERNAL_ART
    return ('<Asset>\n\t<Mesh file="%s.gr2"/>\n' % x['model']
            + ''.join('\t<Texture file="%s"/>\n' % t for t in x['textures'])
            + '\t<DecisionTree file="Wonder_DecisionTree.ddtxml" source="Tool"/>\n</Asset>\n')

# ---------------------------------------------------------------------------------------------
# Effects on the animated part's bones (rig() in the model module names the key per bone).
# Particle/model effects are the game's own systems; only the transform is ours. Effect sizes are
# multiplied by the building's fScale (0.25), like the stock ones (e.g. the Great Lighthouse's fire:
# scale 2.2 at fScale 0.05; the industrial lighthouse beam: 15.8 at 0.05).
EFFECTS = {
    'EYE_FIRE': dict(name='ART_DEF_VEFFECT_MEC_EYE_FIRE', particle='ART_DEF_PEFFECT_GREAT_LIGHTHOUSE_FIRE',
                     scale=0.4, rotation=(90.0, 0.0, 0.0)),          # flames round the rim of the Eye
    'EYE_FIRE_BIG': dict(name='ART_DEF_VEFFECT_MEC_EYE_BLAZE', particle='ART_DEF_PEFFECT_GREAT_LIGHTHOUSE_FIRE',
                         scale=1.0, rotation=(90.0, 0.0, 0.0)),      # the blaze behind it
    'EYE_BEAM': dict(name='ART_DEF_VEFFECT_MEC_EYE_BEAM', model='ART_DEF_MEFFECT_MEC_EYE_BEAM',
                     file='MEC_EyeBeam.fxsxml', scale=13.0, rotation=(0.0, 0.0, 0.0)),   # ~80 units of light
    # Mount Doom. The eruption is the stock Krakatoa's own particle system (ART_DEF_VEFFECT_VOLCANIC_ERUPTION:
    # scale 0.65 on a feature drawn at world scale, so 0.65 / 0.25 = 2.6 here is Krakatoa's size; a bit more).
    # Fire = the Great Lighthouse fire that already burns round the Eye (0.4 there = flames ~2 units).
    'DOOM_ERUPTION': dict(name='ART_DEF_VEFFECT_MEC_DOOM_ERUPTION', particle='ART_DEF_PEFFECT_VOLCANIC_ERUPTION_01',
                          scale=3.0, rotation=(90.0, 0.0, 0.0)),
    'DOOM_ERUPTION_SMALL': dict(name='ART_DEF_VEFFECT_MEC_DOOM_ERUPTION_SMALL',
                                particle='ART_DEF_PEFFECT_VOLCANIC_ERUPTION_01', scale=1.8, rotation=(90.0, 0.0, 0.0)),
    'DOOM_CRATER_FIRE': dict(name='ART_DEF_VEFFECT_MEC_DOOM_CRATER', particle='ART_DEF_PEFFECT_GREAT_LIGHTHOUSE_FIRE',
                             scale=1.3, rotation=(90.0, 0.0, 0.0)),
    'DOOM_VENT_FIRE': dict(name='ART_DEF_VEFFECT_MEC_DOOM_VENT', particle='ART_DEF_PEFFECT_GREAT_LIGHTHOUSE_FIRE',
                           scale=0.45, rotation=(90.0, 0.0, 0.0)),
    'DOOM_DOOR_FIRE': dict(name='ART_DEF_VEFFECT_MEC_DOOM_DOOR', particle='ART_DEF_PEFFECT_GREAT_LIGHTHOUSE_FIRE',
                           scale=0.35, rotation=(90.0, 0.0, 0.0)),
}
BEAM_TILT = 34.0           # degrees below horizontal: from the Eye (z 41) the ~68-unit beam reaches the land

# Diagnostic variants of an animated landmark, shown on cities a player RENAMES to these names. Each adds
# one layer to the previous one, so a single game shows which layer works (see docs/CITY_MODELS.md).
DIAGNOSTICS = [
    ('T1', 'Test 1', 'static'),          # the proven static model (Eye fixed), Wonder_DecisionTree
    ('T2', 'Test 2', 'animated'),        # + skinned Eye and idle animation, no effects
    ('T3', 'Test 3', 'fire'),            # + the fire effects, no beam
]                                        # the landmark itself = + the beam ('full')

STOCK_FXSXML, STOCK_SCALE = 'Poly_Palace.fxsxml', 0.2   # stock art for --landmark-stock-art and _STOCK

# Empty-tile probes (docs/CITY_MODELS.md §8): per animated landmark, extra buildings with other art, cycled
# in game by the "Cycle landmark" debug button. In a bad launch our models all fail while _STOCK draws.
#   _STOCK  small stock mesh (18 KB Polynesian palace), from the game's .fpk archive
#   _BIG    big stock mesh (Colossus, 660 KB compressed, ~our size), from the .fpk archive
#   _LOOSE  the same small Polynesian palace mesh shipped as a LOOSE file under a new name, like ours
# Made from each landmark's Test 1 model by probes.py: (suffix, label, strings hashed like stock, OBB zeroed)
# (_T1H / _T1HZ, strings hashed like stock, were dropped 2026-11-23: the engine then looks our names up in its
# string database, finds nothing and draws the red missing-material box, so plain text is right for us.)
# Every landmark .gr2 ships in the stock SECTION layout (build_dlc converts them, see gr2.SEC_*); T1F keeps
# the old all-in-section-0 layout as the control. Tuple: (suffix, label, hashed, OBB zeroed, stock sections)
# (_T1F old layout and _T1Z zeroed bounds were ruled out in game 2026-11-23: both failed exactly like Test 1.)
T1_PROBES = []

# Same Test 1 model at smaller fScale (no rebuild): which size still draws in a city that never draws ours?
# Our model is 47 world units tall vs <= 25 for every stock model that always draws. (suffix, label, factor)
# Same full-size Test 1 art through other art slots (Buildings.DisplayPosition). The second city never draws ours
# above 50% in the palace slot (32), the capital up to 75-100%: is the palace slot's space the limit?
# Stock: 1/2/4 land wonders + castle/colosseum, 64 Machu Picchu / Neuschwanstein (8/16 coastal: skipped).
SLOT_PROBES = []

SIZE_PROBES = [
    ('_S90', 'Test 90', 0.90),
    ('_S75', 'Test 75', 0.75),
    ('_S50', 'Test 50', 0.50),
    ('_S25', 'Test 25', 0.25),
]
LOOSE_MODEL = 'MEC_LoosePalace'       # .gr2 = vendor/civ5/template_poly_palace.gr2 (stock bytes), stock textures
PROBES = [
    ('_STOCK', 'Test Stock', STOCK_FXSXML, STOCK_SCALE),
    ('_BIG', 'Test Big', 'Colossus.fxsxml', 0.05),
    ('_LOOSE', 'Test Loose', LOOSE_MODEL + '.fxsxml', STOCK_SCALE),
]


def loose_probe_fxsxml():
    return ('<Asset>\n\t<Mesh file="%s.gr2"/>\n\t<Texture file="Generic_Grey_8.dds"/>\n'
            '\t<Texture file="Poly_palace_DIFF.dds"/>\n\t<Texture file="Poly_palace_SREF.dds"/>\n</Asset>\n'
            % LOOSE_MODEL)

GAMEDATA_XML = 'MEDLC_Landmarks.xml'
TEXT_XML = 'MEDLC_Text_Landmarks.xml'
WONDER_XML = 'MEDLC_Landmarks_Wonders.xml'
VISEFFECTS_XML = 'MEDLC_Landmarks_VisEffects.xml'
VISMODELS_XML = 'MEDLC_Landmarks_VisEffectModels.xml'
LUA = 'MEC_Landmarks.lua'


def art_model(lm):
    """Asset base name this landmark shows: its own model, or another landmark's (art_of)."""
    if lm.get('art_of'):
        return [x for x in LANDMARKS if x['key'] == lm['art_of']][0]['model']
    return lm['model']


def building(lm):
    return 'BUILDING_MEC_LM_' + lm['key']


def art_tag(lm):
    return 'MEC_LM_' + lm['key']


def entries(with_diagnostics=True):
    """One building per entry: the landmark itself, plus the diagnostic variants of animated ones."""
    out = []
    for lm in LANDMARKS:
        main = art_model(lm) + ('_%s' % SHOW_VARIANT if SHOW_VARIANT and lm.get('animated') else '') + '.fxsxml'
        scale = lm['scale']
        if EXTERNAL_ART:
            main, scale = EXTERNAL_ART['model'] + '.fxsxml', EXTERNAL_ART['scale']
        out.append(dict(building=building(lm), tag=art_tag(lm), title=lm['title'], fxsxml=main,
                        scale=scale, keys=lm['name_keys'], aliases=lm['aliases']))
        if lm.get('animated') and with_diagnostics:
            first = lm.get('test_prefix') or lm['aliases'][0].split()[0]     # "Barad Test 1", "Doom Test 1" ...
            for suffix, label, _ in DIAGNOSTICS:
                out.append(dict(building=building(lm) + '_' + suffix, tag=art_tag(lm) + '_' + suffix,
                                title='%s %s' % (lm['title'], label), fxsxml='%s_%s.fxsxml' % (art_model(lm), suffix),
                                scale=lm['scale'], keys=[], aliases=['%s %s' % (first, label)]))
            for suffix, label, slot in SLOT_PROBES:     # shares Test 1's WonderArtInfo (no art entry of its own)
                out.append(dict(building=building(lm) + suffix, tag=art_tag(lm) + '_T1',
                                title='%s %s' % (lm['title'], label), fxsxml=art_model(lm) + '_T1.fxsxml',
                                scale=lm['scale'], keys=[], aliases=['%s %s' % (first, label)],
                                display=slot, shared_art=True))
            for suffix, label, factor in SIZE_PROBES:
                out.append(dict(building=building(lm) + suffix, tag=art_tag(lm) + suffix,
                                title='%s %s' % (lm['title'], label), fxsxml=art_model(lm) + '_T1.fxsxml',
                                scale=round(lm['scale'] * factor, 4), keys=[], aliases=['%s %s' % (first, label)]))
            for suffix, label, _, _, _ in T1_PROBES:
                out.append(dict(building=building(lm) + suffix, tag=art_tag(lm) + suffix,
                                title='%s %s' % (lm['title'], label), fxsxml=art_model(lm) + suffix + '.fxsxml',
                                scale=lm['scale'], keys=[], aliases=['%s %s' % (first, label)]))
            # same mechanism, other art (see PROBES): separates mechanism / size / loose-file loading
            for suffix, label, fx, sc in PROBES:
                out.append(dict(building=building(lm) + suffix, tag=art_tag(lm) + suffix,
                                title='%s %s' % (lm['title'], label), fxsxml=fx, scale=sc,
                                keys=[], aliases=['%s %s' % (first, label)], stock=True))
    return out


def manifest_path(lm):
    return os.path.join(OUT, art_model(lm) + '.files.json')


def asset_files(lm):
    """Every file build_models.py wrote for this landmark (listed in its manifest)."""
    return json.load(open(manifest_path(lm)))['files']


def vis_effects():
    L = ['<?xml version="1.0" encoding="utf-8"?>',
         '<VisEffectArtInfos xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
         'xsi:noNamespaceSchemaLocation="Civ5ArtDefines_VisEffects.xsd">']
    for key, e in EFFECTS.items():
        L += ['\t<VisEffectArtInfo>', '\t\t<Name>%s</Name>' % e['name'], '\t\t<Transform>',
              '\t\t\t<Translation x="0.0" y="0.0" z="0.0"/>',
              '\t\t\t<Rotation x="%.1f" y="%.1f" z="%.1f"/>' % e['rotation'],
              '\t\t\t<Scale>%s</Scale>' % e['scale'], '\t\t</Transform>',
              '\t\t<fBaseDuration>0.01</fBaseDuration>', '\t\t<fBaseDurationScale>1.0</fBaseDurationScale>']
        if 'particle' in e:
            L += ['\t\t<ParticleEffects>', '\t\t\t<ParticleEffect>', '\t\t\t\t<Name>%s</Name>' % e['particle'],
                  '\t\t\t</ParticleEffect>', '\t\t</ParticleEffects>']
        if 'model' in e:
            L += ['\t\t<ModelEffects>', '\t\t\t<ModelEffect>', '\t\t\t\t<Name>%s</Name>' % e['model'],
                  '\t\t\t</ModelEffect>', '\t\t</ModelEffects>']
        L.append('\t</VisEffectArtInfo>')
    L.append('</VisEffectArtInfos>')
    return '\n'.join(L) + '\n'


def vis_effect_models():
    L = ['<?xml version="1.0" encoding="utf-8"?>',
         '<VisEffectModelArtInfos xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
         'xmlns:xsd="http://www.w3.org/2001/XMLSchema">']
    for key, e in EFFECTS.items():
        if 'model' in e:
            L += ['\t<VisEffectModelArtInfo>', '\t\t<Name>%s</Name>' % e['model'], '\t\t<File>%s</File>' % e['file'],
                  '\t\t<fScale>1.0</fScale>', '\t\t<fScrollTime>1.0</fScrollTime>', '\t</VisEffectModelArtInfo>']
    L.append('</VisEffectModelArtInfos>')
    return '\n'.join(L) + '\n'


def _x(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def gamedata(with_diagnostics=True):
    L = ['<?xml version="1.0" encoding="utf-8"?>',
         '<!-- Middle-earth landmark buildings: no gameplay; buildable for 1 production only in the matching city (BUILDABLE), or given by MEC_Landmarks.lua -->',
         '<GameData>', '\t<BuildingClasses>']
    for e in entries(with_diagnostics):
        b = e['building']
        L.append('\t\t<Row><Type>%s</Type><DefaultBuilding>%s</DefaultBuilding><Description>TXT_KEY_%s</Description>'
                 '<NoLimit>true</NoLimit></Row>' % (b.replace('BUILDING_', 'BUILDINGCLASS_'), b, b))
    L += ['\t</BuildingClasses>', '\t<Buildings>']
    for e in entries(with_diagnostics):
        b = e['building']
        L.append('\t\t<Row>')
        for k, v in (('Type', b), ('BuildingClass', b.replace('BUILDING_', 'BUILDINGCLASS_')),
                     ('Description', 'TXT_KEY_' + b), ('Help', 'TXT_KEY_' + b + '_HELP'),
                     ('Civilopedia', 'TXT_KEY_' + b + '_HELP'),
                     ('Cost', 1 if BUILDABLE and e['keys'] else -1), ('FaithCost', -1), ('GoldMaintenance', 0), ('ConquestProb', 100),
                     ('NeverCapture', 'false'), ('NukeImmune', 'true'), ('HurryCostModifier', -1),
                     ('MinAreaSize', -1), ('ArtDefineTag', e['tag']), ('DisplayPosition', e.get('display', DISPLAY_POSITION)),
                     ('ArtInfoCulturalVariation', 'false'), ('ArtInfoEraVariation', 'false'),
                     ('ArtInfoRandomVariation', 'false'),
                     ('IconAtlas', 'BW_ATLAS_1'), ('PortraitIndex', 19)):   # the palace icon
            L.append('\t\t\t<%s>%s</%s>' % (k, _x(str(v)), k))
        L.append('\t\t</Row>')
    L += ['\t</Buildings>', '</GameData>']
    return '\n'.join(L) + '\n'


def text(with_diagnostics=True):
    L = ['<?xml version="1.0" encoding="utf-8"?>', '<GameData>', '\t<Language_en_US>']
    for e in entries(with_diagnostics):
        b = e['building']
        L.append('\t\t<Row Tag="TXT_KEY_%s"><Text>%s (landmark)</Text></Row>' % (b, _x(e['title'])))
        L.append('\t\t<Row Tag="TXT_KEY_%s_HELP"><Text>The landmark of %s. Purely visual: no effect on the game.</Text></Row>'
                 % (b, _x(e['title'])))
    L += ['\t</Language_en_US>', '</GameData>']
    return '\n'.join(L) + '\n'


def wonder_defines(stock_art=False, with_diagnostics=True):
    """stock_art=True: diagnostic build, every landmark shows the stock Polynesian palace instead
    of our model (separates the mechanism from our assets)."""
    L = ['<?xml version="1.0" encoding="utf-8"?>',
         '<WonderArtInfos xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
         'xsi:noNamespaceSchemaLocation="Civ5ArtDefineSchemas_Wonders.xsd">']
    for e in entries(with_diagnostics):
        if e.get('shared_art'):
            continue
        granny, scale = ((STOCK_FXSXML, STOCK_SCALE) if stock_art else (e['fxsxml'], e['scale']))
        L += ['\t<!-- %s -->' % e['building'], '\t<WonderArtInfo>', '\t\t<Type>%s</Type>' % e['tag'],
              '\t\t<WonderArtState state="Any">', '\t\t\t<fScale>%s</fScale>' % scale,
              '\t\t\t<Granny>%s</Granny>' % granny, '\t\t</WonderArtState>', '\t</WonderArtInfo>']
    L.append('</WonderArtInfos>')
    return '\n'.join(L) + '\n'


def lua_table(with_diagnostics=True):
    """Lua source for the name -> building table (inserted into MEC_Landmarks.lua)."""
    def lstr(s):
        return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'
    L = ['g_LandmarkDefs = {']
    for e in entries(with_diagnostics):
        L.append('\t{ Building = %s, Keys = { %s }, Aliases = { %s } },' % (
            lstr(e['building']), ', '.join(lstr(k) for k in e['keys']),
            ', '.join(lstr(a) for a in e['aliases'])))
    L.append('}')
    L.append('g_Buildable = %s' % ('true' if BUILDABLE else 'false'))
    L.append('g_GiveAtFounding = %s' % ('true' if GIVE_AT_FOUNDING else 'false'))
    return '\n'.join(L)

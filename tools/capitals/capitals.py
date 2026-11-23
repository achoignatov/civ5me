"""The capital models and how they are hooked into the game (no Blender needed here).

How the game picks a building's 3D model (reverse-engineered from CivilizationV_DX11.exe,
function at 0x6cd0a0; buildings with DisplayPosition > 0 are sent there by the game core):
    if ArtInfoCulturalVariation:  name = civ ArtStylePrefix + " " + ArtDefineTag
    elif ArtInfoEraVariation:     name = era + " " + ArtDefineTag
    elif ArtInfoRandomVariation:  name = ArtDefineTag + " ONE" / " TWO"
    else:                         name = ArtDefineTag
and `name` is looked up among the WonderArtInfo <Type>s. The stock Palace has no variation
flag, so the game looks for a model named just "PALACE", which does not exist: stock capitals
never show a palace (the "EUROPEAN PALACE"... art in the game files is unused).

So the pack (DLC build) sets ArtInfoCulturalVariation on BUILDING_PALACE and gives every
Middle-earth civ its own ArtStylePrefix *without* trailing space ("MEC_GONDOR"); the game then
asks for "MEC_GONDOR PALACE", which our <WonderDefines> maps to the capital model. Palace art
does not depend on era or city size, and the model stays for the whole game.
"""

# civilization, Blender model module, asset name, new ArtStylePrefix, previous prefix
CAPITALS = [
    ('CIVILIZATION_MEC_GONDOR', 'gondor', 'MEC_MinasTirith', 'MEC_GONDOR', 'EUROPEAN'),
    ('CIVILIZATION_MEC_ROHAN', 'rohan', 'MEC_Edoras', 'MEC_ROHAN', 'EUROPEAN'),
    ('CIVILIZATION_MEC_ISENGARD', 'isengard', 'MEC_Orthanc', 'MEC_ISENGARD', 'EUROPEAN'),
    ('CIVILIZATION_MEC_HOBBITS', 'hobbits', 'MEC_BagEnd', 'MEC_HOBBITS', 'EUROPEAN'),
    ('CIVILIZATION_MEC_MORDOR', 'mordor', 'MEC_BaradDur', 'MEC_MORDOR', 'EUROPEAN'),
    ('CIVILIZATION_MEC_DWARVES', 'dwarves', 'MEC_Erebor', 'MEC_DWARVES', 'EUROPEAN'),
    ('CIVILIZATION_MEC_GOBLINS', 'goblins', 'MEC_Moria', 'MEC_GOBLINS', 'EUROPEAN'),
    ('CIVILIZATION_MEC_HIGH_ELVES', 'high_elves', 'MEC_Rivendell', 'MEC_HIGH_ELVES', 'MEDITERRANEAN'),
    ('CIVILIZATION_MEC_WOOD_ELVES', 'wood_elves', 'MEC_ElvenkingsHalls', 'MEC_WOOD_ELVES', 'MEDITERRANEAN'),
    ('CIVILIZATION_MEC_ANGMAR', 'angmar', 'MEC_CarnDum', 'MEC_ANGMAR', 'EUROPEAN'),
    ('CIVILIZATION_MEC_ARNOR', 'arnor', 'MEC_Annuminas', 'MEC_ARNOR', 'EUROPEAN'),
    ('CIVILIZATION_MEC_EASTERLINGS', 'easterlings', 'MEC_Rhun', 'MEC_EASTERLINGS', 'ASIAN'),
    ('CIVILIZATION_MEC_SOUTHRONS', 'southrons', 'MEC_Harad', 'MEC_SOUTHRONS', 'AFRICAN'),
    ('CIVILIZATION_MEC_UMBAR', 'umbar', 'MEC_Umbar', 'MEC_UMBAR', 'AFRICAN'),
]

# Stock castle / colosseum models per old prefix (from Civ5ArtDefines_Wonders.xml)
STOCK = {
    'EUROPEAN': ('Assets/Buildings/City Buildings/Castle/Euro_Castle.fxsxml',
                 'Assets/Buildings/City Buildings/Colesseum/Colesseum_Euro.fxsxml'),
    'MEDITERRANEAN': ('Assets/Buildings/City Buildings/Castle/Medit_Castle.fxsxml',
                      'Assets/Buildings/City Buildings/Colesseum/Colesseum_Euro.fxsxml'),
    'AFRICAN': ('Assets/Buildings/City Buildings/Castle/African_Castle.fxsxml',
                'Assets/Buildings/City Buildings/Colesseum/Colesseum_Afri.fxsxml'),
    'ASIAN': ('Assets/Buildings/City Buildings/Castle/Asian_Castle.fxsxml',
              'Assets/Buildings/City Buildings/Colesseum/Colesseum_Asia.fxsxml'),
}

# Size of the capital models in the world. The stock palaces use 0.2 for a ~45 unit wide
# model (a small building in the middle of the tile).
SCALE = 0.77   # fills the city hexagon (measured in game: hex ~48 world units, models ~62 units wide)
STOCK_SCALE = 0.2
EMPTY = 'MEC_NoCity.fxsxml'   # empty model (cityhouses.py), always packed

WONDER_XML = 'MEDLC_Capitals_Wonders.xml'
GAMEDATA_XML = 'MEDLC_Capitals_ArtStyle.xml'


# Diagnostic builds (build_dlc.py --diag): these prefixes get a stock palace model instead of ours,
# to tell "the game never looks up our palace names" apart from "our model files don't load".
DIAG_STOCK = {'MEC_MORDOR': 'Assets/Buildings/City Buildings/Palace/Euro_Palace.fxsxml'}


def wonder_defines(diag=False):
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<WonderArtInfos xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xsi:noNamespaceSchemaLocation="Civ5ArtDefineSchemas_Wonders.xsd">']

    def entry(typ, scale, granny):
        out.extend(['\t<WonderArtInfo>', '\t\t<Type>%s</Type>' % typ, '\t\t<WonderArtState state="Any">',
                    '\t\t\t<fScale>%s</fScale>' % scale, '\t\t\t<Granny>%s</Granny>' % granny,
                    '\t\t</WonderArtState>', '\t</WonderArtInfo>'])
    for civ, module, asset, prefix, old in CAPITALS:
        castle, colesseum = STOCK[old]
        out.append('\t<!-- %s: %s -->' % (civ, asset))
        # the game builds prefix + " " + tag
        for sep in (' ',):
            if diag and prefix in DIAG_STOCK:
                entry(prefix + sep + 'PALACE', STOCK_SCALE, DIAG_STOCK[prefix])
            else:
                entry(prefix + sep + 'PALACE', SCALE, asset + '.fxsxml')
            # no stock buildings beside the landmark: castle/colosseum art is the empty model
            entry(prefix + sep + 'CASTLE', STOCK_SCALE, EMPTY)
            entry(prefix + sep + 'COLESSEUM', STOCK_SCALE, EMPTY)
    out.append('</WonderArtInfos>')
    return '\n'.join(out) + '\n'


def gamedata():
    rows = ''.join('\t\t<Update>\n\t\t\t<Where Type="%s"/>\n\t\t\t<Set ArtStylePrefix="%s"/>\n\t\t</Update>\n'
                   % (civ, prefix) for civ, module, asset, prefix, old in CAPITALS)
    return ('<?xml version="1.0" encoding="utf-8"?>\n<GameData>\n\t<Civilizations>\n' + rows +
            '\t</Civilizations>\n'
            '\t<Buildings>\n\t\t<Update>\n\t\t\t<Where Type="BUILDING_PALACE"/>\n'
            '\t\t\t<Set ArtInfoCulturalVariation="true"/>\n\t\t</Update>\n\t</Buildings>\n</GameData>\n')


# --------------------------------------------------------------------------- animated effects
# Wonders/palaces play particle effects on "FX_" bones of their model (the Great Lighthouse's fire,
# the Colossus' torch): the model's .fxsxml names a TimedTrigger file that starts a VisEffect on
# each bone, driven by the stock Wonder_DecisionTree. Particles animate and flicker by themselves.
# Sizes cannot be checked outside the game: FX_SCALE multiplies every effect below.
FX_SCALE = 1.0

# VisEffect -> (particle effects, scale, rotation x)
EFFECTS = {
    # Barad-dûr: flames wrapping the Eye + a fiery core and glow
    'ART_DEF_VEFFECT_MEC_EYE_FLAMES': (['ART_DEF_PEFFECT_FIRE_FLAMES', 'ART_DEF_PEFFECT_FIRE_FLAME_GLOWS'], 0.6, 90),
    'ART_DEF_VEFFECT_MEC_EYE_CORE': (['ART_DEF_PEFFECT_GREAT_LIGHTHOUSE_FIRE', 'ART_DEF_PEFFECT_FIRE_BASE_GLOW_LG'],
                                     0.8, 90),
    # Bag End: candle light flickering in the windows
    'ART_DEF_VEFFECT_MEC_CANDLE': (['ART_DEF_PEFFECT_CANDLE_FLAME_01', 'ART_DEF_PEFFECT_FIRE_BASE_GLOW_SM'], 0.25, 90),
    # Moria: blue ithildin glow and sparkle (particles recoloured from stock ones, see particles.py)
    'ART_DEF_VEFFECT_MEC_ITHILDIN_GLOW': (['ART_DEF_PEFFECT_MEC_ITHILDIN_GLOW'], 0.6, 0),
    'ART_DEF_VEFFECT_MEC_ITHILDIN_SPARKLE': (['ART_DEF_PEFFECT_MEC_ITHILDIN_SPARKLE'], 0.4, 90),
    # Erebor: gold glittering on the great door
    'ART_DEF_VEFFECT_MEC_GOLD_GLITTER': (['ART_DEF_PEFFECT_GLITTERING_GOLD_01', 'ART_DEF_PEFFECT_GLITTERING_GOLD_02'],
                                        0.4, 90),
    # --- city-state effects (tools/capitals/models/*, see citystates.py)
    # chimney / hearth smoke
    'ART_DEF_VEFFECT_MEC_SMOKE': (['ART_DEF_PEFFECT_STEAM_STACK_SM_01'], 0.25, 90),
    # torches on walls and gates, braziers, camp and forge fires
    'ART_DEF_VEFFECT_MEC_TORCH': (['ART_DEF_PEFFECT_FIRE_TORCH_SM', 'ART_DEF_PEFFECT_FIRE_BASE_GLOW_SM'], 0.3, 90),
    'ART_DEF_VEFFECT_MEC_BRAZIER': (['ART_DEF_PEFFECT_FIRE_BRAZIER_01', 'ART_DEF_PEFFECT_FIRE_BASE_GLOW_MD'], 0.35, 90),
    'ART_DEF_VEFFECT_MEC_CAMPFIRE': (['ART_DEF_PEFFECT_FIRE_PIT_SM', 'ART_DEF_PEFFECT_FIRE_BASE_GLOW_SM'], 0.35, 90),
    # wizards' light: blue (the Blue Wizards, Radagast), white (Mithrandir, Curumo)
    'ART_DEF_VEFFECT_MEC_MAGIC_BLUE': (['ART_DEF_PEFFECT_GREAT_PERSON_SCIENCE_GLOW'], 0.35, 90),
    'ART_DEF_VEFFECT_MEC_MAGIC_WHITE': (['ART_DEF_PEFFECT_GREAT_PERSON_CULTURE_GLOW'], 0.35, 90),
    # Gandalf's fireworks
    'ART_DEF_VEFFECT_MEC_FIREWORKS': (['ART_DEF_PEFFECT_SPARKS_01', 'ART_DEF_PEFFECT_SPARK_YELLOW_MD'], 0.5, 90),
    # the Dead (green ghost light), spider eyes (red)
    'ART_DEF_VEFFECT_MEC_GHOST': (['ART_DEF_PEFFECT_MECH_EYE_GLOW_GREEN'], 0.6, 0),
    'ART_DEF_VEFFECT_MEC_RED_EYES': (['ART_DEF_PEFFECT_MECH_EYE_GLOW_RED'], 0.25, 0),
    # spray of falls and springs, dragon's breath
    'ART_DEF_VEFFECT_MEC_MIST': (['ART_DEF_PEFFECT_FOUNTAIN_MIST'], 0.5, 90),
    'ART_DEF_VEFFECT_MEC_DRAGON_SMOKE': (['ART_DEF_PEFFECT_EMBERS_PLUME', 'ART_DEF_PEFFECT_D3_SMOKEPLUME_01'], 0.3, 90),
}

# custom particle systems: name -> (stock source .psb in EffectData.fpk, new RGB colour, output file)
PARTICLES = {
    'ART_DEF_PEFFECT_MEC_ITHILDIN_GLOW': ('fxp_mecheye_glow_green.psb', (0.45, 0.78, 1.0), 'MEC_Ithildin_Glow.psb'),
    'ART_DEF_PEFFECT_MEC_ITHILDIN_SPARKLE': ('fx_glittering_silver_01.psb', (0.55, 0.85, 1.0), 'MEC_Ithildin_Sparkle.psb'),
}

VISEFFECT_XML = 'MEDLC_Capitals_VisEffects.xml'
PARTICLE_XML = 'MEDLC_Capitals_VisEffectParticles.xml'


def viseffects():
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<VisEffectArtInfos xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xsi:noNamespaceSchemaLocation="Civ5ArtDefines_VisEffects.xsd">']
    for name, (parts, scale, rx) in EFFECTS.items():
        out += ['\t<VisEffectArtInfo>', '\t\t<Name>%s</Name>' % name, '\t\t<Transform>',
                '\t\t\t<Translation x="0.0" y="0.0" z="0.0"/>',
                '\t\t\t<Rotation x="%.1f" y="0.0" z="0.0"/>' % rx,
                '\t\t\t<Scale>%.3f</Scale>' % (scale * FX_SCALE), '\t\t</Transform>',
                '\t\t<fBaseDuration>0.01</fBaseDuration>', '\t\t<fBaseDurationScale>1.0</fBaseDurationScale>',
                '\t\t<ParticleEffects>']
        for p in parts:
            out += ['\t\t\t<ParticleEffect>', '\t\t\t\t<Name>%s</Name>' % p, '\t\t\t</ParticleEffect>']
        out += ['\t\t</ParticleEffects>', '\t</VisEffectArtInfo>']
    out.append('</VisEffectArtInfos>')
    return '\n'.join(out) + '\n'


def particle_defines():
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<VisEffectParticleArtInfos xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xmlns:xsd="http://www.w3.org/2001/XMLSchema">']
    for name, (src, rgb, fn) in PARTICLES.items():
        out += ['\t<VisEffectParticleArtInfo>', '\t\t<Name>%s</Name>' % name, '\t\t<File>%s</File>' % fn,
                '\t</VisEffectParticleArtInfo>']
    out.append('</VisEffectParticleArtInfos>')
    return '\n'.join(out) + '\n'

"""The 26 Middle-earth city-state models and how they are hooked into the game.

City-states are minor civilizations, so they use the same Palace art hook as the major
capitals: set ArtInfoCulturalVariation on BUILDING_PALACE, give every minor civ its own
ArtStylePrefix, and map ``<prefix> PALACE`` to the model in a WonderDefines file.  The
only difference is the table that owns the prefix (MinorCivilizations instead of
Civilizations).

The models are listed in the order of the two source mods (EXP then VAN), with a lore
note in each model script.  Where Tolkien describes no town (Avathar, Tol Fuin, ...), the
model is an appropriate landmark, ruin, camp or natural feature instead of an invented
major city.
"""

# minor civilization, Blender model module, asset name, new ArtStylePrefix, old prefix
CITYSTATES = [
    # --- Middle Earth City States (EXP)
    ('MINOR_CIV_MECS_BREE', 'bree', 'MEC_Bree', 'MEC_BREE', 'EUROPEAN'),
    ('MINOR_CIV_MECS_DALE', 'dale', 'MEC_Dale', 'MEC_DALE', 'EUROPEAN'),
    ('MINOR_CIV_MECS_DORWINION', 'dorwinion', 'MEC_Dorwinion', 'MEC_DORWINION', 'EUROPEAN'),
    ('MINOR_CIV_MECS_ESGAROTH', 'esgaroth', 'MEC_Esgaroth', 'MEC_ESGAROTH', 'EUROPEAN'),
    ('MINOR_CIV_MECS_EPHEL_BRANDIR', 'ephel_brandir', 'MEC_EphelBrandir', 'MEC_EPHEL_BRANDIR', 'EUROPEAN'),
    ('MINOR_CIV_MECS_RHOSGOBEL', 'rhosgobel', 'MEC_Rhosgobel', 'MEC_RHOSGOBEL', 'EUROPEAN'),
    ('MINOR_CIV_MECS_MITHRANDIR', 'mithrandir', 'MEC_Mithrandir', 'MEC_MITHRANDIR', 'EUROPEAN'),
    ('MINOR_CIV_MECS_ALATAR', 'alatar', 'MEC_Alatar', 'MEC_ALATAR', 'EUROPEAN'),
    ('MINOR_CIV_MECS_PALLANDO', 'pallando', 'MEC_Pallando', 'MEC_PALLANDO', 'EUROPEAN'),
    ('MINOR_CIV_MECS_CURUMO', 'curumo', 'MEC_Curumo', 'MEC_CURUMO', 'EUROPEAN'),
    # --- Middle Earth City States (VAN)
    ('MINOR_CIV_MECS_AVATHAR', 'avathar', 'MEC_Avathar', 'MEC_AVATHAR', 'EUROPEAN'),
    ('MINOR_CIV_MECS_KINGDOM_OF_RHOVANION', 'rhovanion', 'MEC_Rhovanion', 'MEC_RHOVANION', 'EUROPEAN'),
    ('MINOR_CIV_MECS_SMAUGS_LAIR', 'smaugs_lair', 'MEC_SmaugsLair', 'MEC_SMAUGS_LAIR', 'EUROPEAN'),
    ('MINOR_CIV_MECS_DUNLAND', 'dunland', 'MEC_Dunland', 'MEC_DUNLAND', 'EUROPEAN'),
    ('MINOR_CIV_MECS_PATHS_OF_THE_DEAD', 'paths_of_the_dead', 'MEC_PathsOfTheDead', 'MEC_PATHS_OF_THE_DEAD', 'EUROPEAN'),
    ('MINOR_CIV_MECS_SHELOBS_LAIR', 'shelobs_lair', 'MEC_ShelobsLair', 'MEC_SHELOBS_LAIR', 'EUROPEAN'),
    ('MINOR_CIV_MECS_CRISSAEGRIM', 'crissaegrim', 'MEC_Crissaegrim', 'MEC_CRISSAEGRIM', 'EUROPEAN'),
    ('MINOR_CIV_MECS_BEORNS_HALL', 'beorns_hall', 'MEC_BeornsHall', 'MEC_BEORNS_HALL', 'EUROPEAN'),
    ('MINOR_CIV_MECS_ENTWOOD', 'entwood', 'MEC_Entwood', 'MEC_ENTWOOD', 'EUROPEAN'),
    ('MINOR_CIV_MECS_TOM_BOMBADILS_HOUSE', 'tom_bombadils_house', 'MEC_TomBombadilsHouse', 'MEC_TOM_BOMBADILS_HOUSE', 'EUROPEAN'),
    ('MINOR_CIV_MECS_EAGLES_EYRIE', 'eagles_eyrie', 'MEC_EaglesEyrie', 'MEC_EAGLES_EYRIE', 'EUROPEAN'),
    ('MINOR_CIV_MECS_LAKE_TOWN', 'lake_town', 'MEC_LakeTown', 'MEC_LAKE_TOWN', 'EUROPEAN'),
    ('MINOR_CIV_MECS_TOL_MORWEN', 'tol_morwen', 'MEC_TolMorwen', 'MEC_TOL_MORWEN', 'EUROPEAN'),
    ('MINOR_CIV_MECS_TOL_FUIN', 'tol_fuin', 'MEC_TolFuin', 'MEC_TOL_FUIN', 'EUROPEAN'),
    ('MINOR_CIV_MECS_HIMLING', 'himling', 'MEC_Himling', 'MEC_HIMLING', 'EUROPEAN'),
    ('MINOR_CIV_MECS_LOSSOTH', 'lossoth', 'MEC_Lossoth', 'MEC_LOSSOTH', 'EUROPEAN'),
]

# Same world size as the capital landmarks: the model fills the city hexagon.
SCALE = 0.77
STOCK_SCALE = 0.2
EMPTY = 'MEC_NoCity.fxsxml'   # empty model (cityhouses.py), always packed

WONDER_XML = 'MEDLC_CityStates_Wonders.xml'
GAMEDATA_XML = 'MEDLC_CityStates_ArtStyle.xml'


def _stock():
    # Import lazily so the table above can be read without the rest of the pipeline.
    import capitals
    return capitals.STOCK


PLACEHOLDER = 'Assets/Buildings/City Buildings/Palace/Euro_Palace.fxsxml'


def wonder_defines(built=None):
    """built: asset names whose model files exist (None = all); the others get a stock palace."""
    stock = _stock()
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<WonderArtInfos xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xsi:noNamespaceSchemaLocation="Civ5ArtDefineSchemas_Wonders.xsd">']

    def entry(typ, scale, granny):
        out.extend(['\t<WonderArtInfo>', '\t\t<Type>%s</Type>' % typ, '\t\t<WonderArtState state="Any">',
                    '\t\t\t<fScale>%s</fScale>' % scale, '\t\t\t<Granny>%s</Granny>' % granny,
                    '\t\t</WonderArtState>', '\t</WonderArtInfo>'])
    for civ, module, asset, prefix, old in CITYSTATES:
        castle, colesseum = stock[old]
        out.append('\t<!-- %s: %s -->' % (civ, asset))
        if built is None or asset in built:
            entry(prefix + ' PALACE', SCALE, asset + '.fxsxml')
        else:
            entry(prefix + ' PALACE', STOCK_SCALE, PLACEHOLDER)
        entry(prefix + ' CASTLE', STOCK_SCALE, EMPTY)
        entry(prefix + ' COLESSEUM', STOCK_SCALE, EMPTY)
    out.append('</WonderArtInfos>')
    return '\n'.join(out) + '\n'


def gamedata():
    rows = ''.join('\t\t<Update>\n\t\t\t<Where Type="%s"/>\n\t\t\t<Set ArtStylePrefix="%s"/>\n\t\t</Update>\n'
                   % (civ, prefix) for civ, module, asset, prefix, old in CITYSTATES)
    return ('<?xml version="1.0" encoding="utf-8"?>\n<GameData>\n\t<MinorCivilizations>\n' + rows +
            '\t</MinorCivilizations>\n'
            '\t<Buildings>\n\t\t<Update>\n\t\t\t<Where Type="BUILDING_PALACE"/>\n'
            '\t\t\t<Set ArtInfoCulturalVariation="true"/>\n\t\t</Update>\n\t</Buildings>\n</GameData>\n')

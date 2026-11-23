"""Remove the stock city houses ("population buildings") from every city.

How Civ 5 draws a city's houses (reverse-engineered, see README "Capital and city-state
models"): the executable picks one library model per *culture* and era from the
<CityDefines> (Civ5ArtDefines_CityBuildings.xml) - "Europe", "Asia", ... chosen by the
owner's hardcoded ArtStyleType - and shows more of its houses as the population grows.
This cannot differ between a capital and the civ's other cities, and our capital and
city-state landmarks fill the whole hexagon, so the pack replaces the house library of
every culture with an empty model: cities then show only their landmark (capitals,
city-states) or bare ground (other cities, until they get Middle-earth house sets).

The empty model is written with the same writer as the landmarks (one degenerate
triangle below the ground) so the game loads it like any other city model.
"""
import os

CULTURES = ['Africa', 'America', 'Asia', 'Europe', 'Mediterranean', 'Polynesian']
ERAS = ['Ancient', 'Rennaisance', 'Industrial', 'Modern']     # sic, as in the game files
MODEL = 'MEC_NoCity'
CITY_XML = 'MEDLC_CityBuildings.xml'


def write_model(out_dir):
    import civ5model
    n, t, bn = (0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)
    verts = [((0.0, 0.0, -6.0), n, t, bn, (0.0, 0.0)), ((0.01, 0.0, -6.0), n, t, bn, (1.0, 0.0)),
             ((0.0, 0.01, -6.0), n, t, bn, (0.0, 1.0))]
    civ5model.write_model(out_dir, MODEL, verts, [(0, 1, 2)], 'Generic_Grey_8.dds', 'Generic_Grey_8.dds',
                          wonder=False)
    return [MODEL + '.gr2', MODEL + '.fxsxml']


def city_defines():
    out = ['<?xml version="1.0" encoding="utf-8"?>', '<BuildingArtInfos>',
           '\t<!-- Middle-earth DLC: no stock houses in any city (see tools/capitals/cityhouses.py) -->']
    for c in CULTURES:
        out.append('\t<Culture name="%s">' % c)
        for e in ERAS:
            out += ['\t\t<Era name="%s">' % e, '\t\t\t<PopulationBuildings>',
                    '\t\t\t\t<Granny>%s.gr2</Granny>' % MODEL, '\t\t\t</PopulationBuildings>', '\t\t</Era>']
        out.append('\t</Culture>')
    out.append('</BuildingArtInfos>')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(d, exist_ok=True)
    print(write_model(d))

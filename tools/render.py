import sys, xml.etree.ElementTree as ET
from civ5map import read_map
mapf, prefix = sys.argv[1], sys.argv[2]
m = read_map(mapf); W, H = m['w'], m['h']
X = '../mods/Middle Earth True Start Location (v 2)/XML/'
marks = {}
for fn, tag, ch in [('METSL_CivilizationStartPos.xml', 'Civilizations_%sStartPosition', 'C'), ('METSL_MinorStartPos.xml', 'MinorCiv_%sStartPosition', 'c')]:
    for t in ET.parse(X+fn).getroot():
        if t.tag == tag % prefix:
            for r in t:
                x, y = int(r.find('X').text), int(r.find('Y').text)
                pl = m['plots'][y*W+x]
                bad = pl[0] in (5,6) or pl[4] == 2
                marks[(x,y)] = '!' if bad else ch
                if bad: print('BAD', r.find('Type').text, x, y, 'terrain', m['terrains'][pl[0]], 'elev', pl[4])
for y in range(H-1, -1, -1):
    row = (' ' if y % 2 else '')
    for x in range(W):
        pl = m['plots'][y*W+x]
        c = marks.get((x,y)) or ('~' if pl[0]==6 else '-' if pl[0]==5 else '^' if pl[4]==2 else 'n' if pl[4]==1 else 'f' if pl[2]==5 else '.')
        row += c
    print('%2d %s' % (y, row))

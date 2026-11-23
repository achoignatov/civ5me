"""Run a METSL map script through the Civ5 mock (Lua 5.1 via lupa) with real game Lua + modded DB.
usage: simulate.py <db> <mapKey> [seed] [opt1,opt2,...] [nMajors] [nMinors] [--render]
"""
import sys, os, glob, sqlite3, collections
from lupa.lua51 import LuaRuntime

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'src')
GAME = os.path.expanduser("~/.local/share/Steam/steamapps/common/Sid Meier's Civilization V/Assets")
SEARCH = [os.path.join(GAME, 'DLC', 'Expansion2', 'Gameplay', 'Lua'), os.path.join(GAME, 'DLC', 'Expansion', 'Gameplay', 'Lua'),
          os.path.join(GAME, 'Gameplay', 'Lua')]


def find_src(name):
    base = name if name.lower().endswith('.lua') else name + '.lua'
    for root in [SRC] + SEARCH:
        for p in glob.glob(os.path.join(root, '**', '*.lua'), recursive=True):
            if os.path.basename(p).lower() == base.lower():
                return p
    return None


def run(dbpath, key, seed=1, options=None, majors=None, minors=None):
    db = sqlite3.connect(dbpath)
    lua = LuaRuntime(unpack_returned_tuples=True)
    G = lua.globals()

    def rows(name):
        try:
            info = list(db.execute('pragma table_info("%s")' % name))
        except Exception:
            return None
        if not info:
            return None
        cols = [c[1] for c in info]
        types = {c[1]: (c[2] or '').lower() for c in info}
        out = lua.table()
        order = ' ORDER BY ID' if 'ID' in cols else ' ORDER BY rowid'
        for i, r in enumerate(db.execute('select * from "%s"%s' % (name, order))):
            t = lua.table()
            for c, v in zip(cols, r):
                if v is None:
                    continue
                if types[c] == 'boolean':
                    v = bool(v) if not isinstance(v, str) else v.lower() in ('1', 'true')
                t[c] = v
            out[i + 1] = t
        return out

    def include(name):
        p = find_src(name)
        if not p:
            return None, None
        return open(p, encoding='latin-1').read(), p

    G.PY_GameInfoRows = rows
    G.PY_Include = include
    G.MOCK_SEED = seed
    G.MOCK_OPTIONS = lua.table(*(options or []))
    G.MOCK_MAJORS = lua.table(*(majors or []))
    G.MOCK_MINORS = lua.table(*(minors or []))
    lua.execute(open(os.path.join(HERE, 'mockciv.lua')).read())
    lua.execute('include("METSL_%s")' % key)
    W, H = lua.eval('MOCK_InitMap()')
    lua.execute('GenerateMap()')
    dump = [tuple(v.values()) for v in lua.eval('MOCK_Dump()').values()]
    starts = [tuple(v.values()) for v in lua.eval('MOCK_Starts()').values()]
    return lua, db, W, H, dump, starts


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dbp, key = args[0], args[1]
    seed = int(args[2]) if len(args) > 2 else 1
    opts = [int(x) for x in args[3].split(',')] if len(args) > 3 and args[3] else []
    db = sqlite3.connect(dbp)
    allciv = [r[0] for r in db.execute("select Type from Civilizations where Type like 'CIVILIZATION_MEC_%' order by ID")]
    allmin = [r[0] for r in db.execute("select Type from MinorCivilizations order by ID")]
    nmaj = int(args[4]) if len(args) > 4 else len(allciv)
    nmin = int(args[5]) if len(args) > 5 else 22
    lua, db, W, H, dump, starts = run(dbp, key, seed, opts, allciv[:nmaj], allmin[:nmin])
    res_names = {r[0]: r[1] for r in db.execute('select ID, Type from Resources')}
    cnt = collections.Counter(res_names[d[3]] for d in dump if d[3] != -1)
    print('map %dx%d, starts=%d, resources placed=%d' % (W, H, len(starts), sum(cnt.values())))
    for s in starts:
        print('  start', s)
    print(sorted(cnt.items()))
    print('rivers plots:', sum(1 for d in dump if d[7]), 'mountains:', sum(1 for d in dump if d[0] == 0),
          'hills:', sum(1 for d in dump if d[0] == 1), 'water:', sum(1 for d in dump if d[0] == 3))
    if '--render' in sys.argv:
        startpos = {(s[2], s[3]): ('C' if s[0] < 22 else 'c') for s in starts}
        for y in range(H - 1, -1, -1):
            row = ' ' if y % 2 else ''
            for x in range(W):
                d = dump[y * W + x]
                c = startpos.get((x, y))
                if not c:
                    c = '~' if d[0] == 3 else '^' if d[0] == 0 else ('*' if d[3] != -1 else 'n' if d[0] == 1 else '.')
                row += c
            print('%2d %s' % (y, row))

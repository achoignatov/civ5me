"""Offline test of MEC_LandmarkImprovements.lua (as built into dist/) against a strict mock of the Civ 5 Lua API.

Run: build/venv/bin/python tools/landmarks/test_improvements.py      (needs lupa; run build_dlc.py first)
Checks: Barad-dur and Moria get their landmarks by name key at founding, every other city and city-state stays
stock, capture (CvCity::init clears the plot) is repaired, typed names match, a rename removes the landmark,
syncing is idempotent, SetImprovementType is always called with the -1 builder.
"""
import os
import sys

from lupa.lua51 import LuaRuntime  # Civ 5 uses Lua 5.1

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import improvements  # noqa: E402
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
SCRIPT = os.path.join(ROOT, 'dist', 'DLC', 'MiddleEarth', 'UI', improvements.LUA)

MOCK = r'''
GameDefines = { MAX_PLAYERS = 5, MAX_MAJOR_CIVS = 3 }
local imps = { { ID = 0, Type = "IMPROVEMENT_FARM" }, @@IMPS@@ }
local civs = { { ID = 0, Type = "CIVILIZATION_MEC_ARNOR" }, @@CIVS@@ }
local function rows(t) return setmetatable({}, {
  __call = function() local i = 0; return function() i = i + 1; return t[i] end end,
  __index = function(_, k) error("direct GameInfo lookup [" .. tostring(k) .. "] (unreliable in game)", 2) end }) end
GameInfo = { Improvements = rows(imps), Civilizations = rows(civs) }
local handlers = {}
local function event(name) handlers[name] = {}; return { Add = function(f) table.insert(handlers[name], f) end } end
GameEvents = { PlayerCityFounded = event("PlayerCityFounded"), CityCaptureComplete = event("CityCaptureComplete"),
               PlayerDoTurn = event("PlayerDoTurn"), SetPopulation = event("SetPopulation") }
function Fire(name, ...) for _, f in ipairs(handlers[name]) do f(...) end end

-- 12 x 12 map; water at x = 0, a mountain at (6,5)
W = 12
Plots = {}
SetCalls = 0
Revealed = 0
for y = 0, W - 1 do for x = 0, W - 1 do
  local pl = { x = x, y = y, imp = -1, city = nil }
  function pl:GetX() return self.x end
  function pl:GetY() return self.y end
  function pl:IsWater() return self.x == 0 end
  function pl:IsMountain() return self.x == 6 and self.y == 5 end
  function pl:IsImpassable() return false end
  function pl:IsCity() return self.city ~= nil end
  function pl:GetPlotCity() return self.city end
  function pl:GetImprovementType() return self.imp end
  function pl:SetImprovementType(id, builder)
    assert(builder == -1, "builder must be -1"); assert(type(id) == "number")
    SetCalls = SetCalls + 1; self.imp = id
  end
  function pl:SetRevealed(team, b) Revealed = Revealed + 1 end
  function pl:ChangeVisibilityCount(team, n, inv, a, b) end
  Plots[y * W + x] = pl
end end
Map = {
  GetPlot = function(x, y) return Plots[y * W + x] end,
  GetNumPlots = function() return W * W end,
  GetPlotByIndex = function(i) return Plots[i] end,
  -- simplified hex directions (enough for the test: 6 distinct neighbours)
  PlotDirection = function(x, y, d)
    local dx = ({ 1, 1, 0, -1, -1, 0 })[d + 1]; local dy = ({ 0, -1, -1, 0, 1, 1 })[d + 1]
    return Plots[(y + dy) * W + (x + dx)]
  end }

Players = {}
-- player 1 = Mordor, player 4 = the Hobbits, the others a civilization without a landmark
for i = 0, 4 do
  local p = { id = i, cities = {}, civ = (i == 1) and @@MORDOR@@ or ((i == 4) and @@HOBBITS@@ or 0) }
  function p:IsAlive() return true end
  function p:IsHuman() return self.id == 0 end
  function p:GetTeam() return self.id end
  function p:GetCivilizationType() return self.civ end
  function p:GetCapitalCity() return self.cities[1] end
  function p:Cities() local k = 0; return function() k = k + 1; return self.cities[k] end end
  Players[i] = p
end
-- like CvCity::init: the plot's improvement is cleared, then PlayerCityFounded fires
function Found(owner, x, y, key)
  local pl = Plots[y * W + x]
  local c = { owner = owner, plot = pl, key = key, orig = owner, first = #Players[owner].cities == 0 }
  function c:GetNameKey() return self.key end
  function c:GetOriginalOwner() return self.orig end
  function c:IsOriginalCapital() return self.first end
  function c:GetX() return self.plot.x end
  function c:GetY() return self.plot.y end
  function c:Plot() return self.plot end
  pl.imp = -1; pl.city = c
  table.insert(Players[owner].cities, c)
  Fire("PlayerCityFounded", owner, x, y)
  return c
end
function Capture(c, newOwner)
  local old = Players[c.owner].cities
  for i, v in ipairs(old) do if v == c then table.remove(old, i) break end end
  c.owner = newOwner; table.insert(Players[newOwner].cities, c)
  c.plot.imp = -1
  Fire("CityCaptureComplete", 0, false, c.plot.x, c.plot.y, newOwner)
end
setmetatable(_G, { __index = function(_, k) error("unknown global " .. tostring(k), 2) end })
'''


def run(script, anchor_present=True):
    lua = LuaRuntime(unpack_returned_tuples=True)
    out = []
    lua.globals().print = lambda *a: out.append(' '.join(str(x) for x in a))
    imps = ', '.join('{ ID = %d, Type = "%s" }' % (10 + i, improvements.improvement(r))
                     for i, r in enumerate(improvements.IMPROVEMENTS))
    civ_types = sorted({r['civ'] for r in improvements.IMPROVEMENTS if r.get('civ')})
    civ_id = {c: 20 + i for i, c in enumerate(civ_types)}
    civs = ', '.join('{ ID = %d, Type = "%s" }' % (i, c) for c, i in civ_id.items())
    lua.execute(MOCK.replace('@@IMPS@@', imps).replace('@@CIVS@@', civs)
                .replace('@@MORDOR@@', str(civ_id['CIVILIZATION_MEC_MORDOR']))
                .replace('@@HOBBITS@@', str(civ_id['CIVILIZATION_MEC_HOBBITS'])))
    if not anchor_present:
        lua.execute('rawget(_G, "Players")[1].civ = 0')
    lua.execute(script)
    return lua, out


def main():
    script = open(SCRIPT, encoding='utf-8').read()
    ids = {r['key']: 10 + i for i, r in enumerate(improvements.IMPROVEMENTS)}
    lua, out = run(script)
    g = lua.globals()
    imp = lambda x, y: g.Map.GetPlot(x, y).GetImprovementType(g.Map.GetPlot(x, y))
    if improvements.ALL_CITIES:
        lua.execute('Found(3, 9, 9, "TXT_KEY_CITY_NAME_MEC_DALE")')
        assert imp(9, 9) == ids[improvements.ALL_CITIES]
        print('OK (ALL_CITIES test mode only)')
        return
    # Mordor's capital and the Goblins' capital get their landmarks at founding
    lua.execute('Found(1, 5, 5, "TXT_KEY_CITY_NAME_MEC_BARAD_DUR")')
    lua.execute('Found(2, 8, 2, "TXT_KEY_CITY_NAME_MEC_MORIA")')
    assert imp(5, 5) == ids['BARAD_DUR'] and imp(8, 2) == ids['MORIA'], (imp(5, 5), imp(8, 2))
    # every other city and city-state keeps stock art (or, in the size-ladder test, gets its variant)
    lad = improvements.TEST_LADDER
    other = lambda x, y: ids[lad[(5 * x + 3 * y) % len(lad)]] if lad else -1
    lua.execute('Found(0, 2, 2, "TXT_KEY_CITY_NAME_MEC_PELARGIR")')
    lua.execute('Found(3, 9, 9, "TXT_KEY_CITY_NAME_MEC_DALE")')
    assert imp(2, 2) == other(2, 2) and imp(9, 9) == other(9, 9), (imp(2, 2), imp(9, 9))
    # no control plots: nothing but city plots was touched
    touched = [(x, y) for x in range(12) for y in range(12) if imp(x, y) != -1]
    assert sorted(touched) == sorted([(5, 5), (8, 2)] + ([(2, 2), (9, 9)] if lad else [])), touched
    # capture clears the plot (CvCity::init); the event puts the landmark back (the name stays)
    lua.execute('Capture(Players[2].cities[1], 0)')
    assert imp(8, 2) == ids['MORIA']
    # a player-typed name matches case-insensitively, also with the accent
    lua.execute('Found(0, 3, 9, "barad-dûr")')
    assert imp(3, 9) == ids['BARAD_DUR']
    # renamed away: the next turn removes the landmark
    lua.execute('Map.GetPlot(3, 9).city.key = "Lugburz"')
    lua.execute('Fire("PlayerDoTurn", 0)')
    assert imp(3, 9) == other(3, 9)
    # idempotent: another turn changes nothing
    n = g.SetCalls
    lua.execute('Fire("PlayerDoTurn", 1)')
    assert g.SetCalls == n, (n, g.SetCalls)
    lua.execute('Fire("SetPopulation", 5, 5, 1, 2)')
    assert imp(5, 5) == ids['BARAD_DUR']
    # the Third Age maps rename by founding tile (game of 2026-11-25): the Hobbits' capital, founded as The Shire,
    # becomes Bag End and keeps its landmark as their original capital; their 2nd city (The Shire -> Longcleave)
    # gets none; captured, the capital keeps it
    lua.execute('Found(4, 7, 7, "TXT_KEY_CITY_NAME_MEC_THE_SHIRE")')
    lua.execute('Found(4, 7, 9, "TXT_KEY_CITY_NAME_MEC_THE_SHIRE")')
    assert imp(7, 7) == ids['BAG_END'] and imp(7, 9) == ids['BAG_END']
    lua.execute('Map.GetPlot(7, 7).city.key = "TXT_KEY_CITY_NAME_MEC_BAG_END"')
    lua.execute('Map.GetPlot(7, 9).city.key = "TXT_KEY_CITY_NAME_MEC_LONGCLEAVE"')
    lua.execute('Fire("PlayerDoTurn", 4)')
    assert imp(7, 7) == ids['BAG_END'] and imp(7, 9) == other(7, 9), (imp(7, 7), imp(7, 9))
    lua.execute('Capture(Players[4].cities[1], 0)')
    assert imp(7, 7) == ids['BAG_END'], imp(7, 7)
    # a later city of a landmark civilization stays stock (only the original capital)
    lua.execute('Found(1, 4, 7, "TXT_KEY_CITY_NAME_MEC_UDUN")')
    assert imp(4, 7) == other(4, 7), imp(4, 7)
    assert g.Revealed == (144 if improvements.REVEAL_MAP else 0), g.Revealed
    # every other capital with a landmark gets its own (by name key, and by a typed alias)
    for k, (x, y) in zip([r['key'] for r in improvements.IMPROVEMENTS if r['key'] not in ('MORIA', 'BARAD_DUR')],
                         [(10, 1), (10, 4), (10, 7), (10, 10), (6, 10), (1, 6)]):
        row = next(r for r in improvements.IMPROVEMENTS if r['key'] == k)
        lua.execute('Found(0, %d, %d, "%s")' % (x, y, row['name_keys'][0]))
        assert imp(x, y) == ids[k], (k, imp(x, y))
        if row['aliases']:
            lua.execute('Found(0, %d, %d, "%s")' % (x - 1, y, row['aliases'][0].upper()))
            assert imp(x - 1, y) == ids[k], (k, 'alias', imp(x - 1, y))
    print('\n'.join(out))
    print('OK: test_improvements (%d log lines, %d SetImprovementType calls)' % (len(out), g.SetCalls))


if __name__ == '__main__':
    main()

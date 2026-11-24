"""Offline test of MEC_LandmarkImprovements.lua (as built into dist/) against a strict mock of the Civ 5 Lua API.

Run: build/venv/bin/python tools/landmarks/test_improvements.py      (needs lupa; run build_dlc.py first)
Checks: every city plot gets the test landmark at founding; founding/capture clearing (CvCity::init) is repaired;
control plots A/B/C next to Mordor's capital skip water, mountains and cities; syncing is idempotent;
the human fallback anchor; SetImprovementType is always called with the -1 builder.
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
GameDefines = { MAX_PLAYERS = 4, MAX_MAJOR_CIVS = 3 }
local imps = { { ID = 0, Type = "IMPROVEMENT_FARM" }, @@IMPS@@ }
local civs = { { ID = 0, Type = "CIVILIZATION_MEC_GONDOR" }, { ID = 7, Type = "CIVILIZATION_MEC_MORDOR" } }
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
for i = 0, 3 do
  local p = { id = i, cities = {}, civ = (i == 1) and 7 or 0 }
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
  local c = { owner = owner, plot = pl, key = key }
  function c:GetNameKey() return self.key end
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
    lua.execute(MOCK.replace('@@IMPS@@', imps))
    if not anchor_present:
        lua.execute('rawget(_G, "Players")[1].civ = 0')
    lua.execute(script)
    return lua, out


def main():
    script = open(SCRIPT, encoding='utf-8').read()
    barad = 10 + [r['key'] for r in improvements.IMPROVEMENTS].index(improvements.ALL_CITIES)
    ctrl = {c: 10 + [r['key'] for r in improvements.IMPROVEMENTS].index(k) for c, k in improvements.CONTROLS}

    lua, out = run(script)
    g = lua.globals()
    imp = lambda x, y: g.Map.GetPlot(x, y).GetImprovementType(g.Map.GetPlot(x, y))
    # Mordor (player 1) founds Barad-dur at (5,5); its neighbour (6,5) is a mountain
    lua.execute('Found(1, 5, 5, "TXT_KEY_CITY_NAME_MEC_BARAD_DUR")')
    assert imp(5, 5) == barad, imp(5, 5)
    ctl = [l for l in out if 'control ' in l and ' = ' in l]
    assert len(ctl) == 3, out
    assert '(6,5)' not in ' '.join(ctl), ctl                     # the mountain is skipped
    # the three control plots carry A/B/C
    placed = {}
    for x in range(12):
        for y in range(12):
            if (x, y) != (5, 5) and imp(x, y) >= 0:
                placed[imp(x, y)] = (x, y)
    assert set(placed) == set(ctrl.values()), placed
    # a human city and a city-state (player 3) get Barad-dur too
    lua.execute('Found(0, 2, 2, "TXT_KEY_CITY_NAME_MEC_MINAS_TIRITH")')
    lua.execute('Found(3, 9, 9, "TXT_KEY_CITY_NAME_MEC_DALE")')
    assert imp(2, 2) == barad and imp(9, 9) == barad
    # capture clears the plot (CvCity::init); the event puts it back
    lua.execute('Capture(Players[0].cities[1], 1)')
    assert imp(2, 2) == barad
    # idempotent: a full turn changes nothing
    n = g.SetCalls
    lua.execute('Fire("PlayerDoTurn", 0)')
    assert g.SetCalls == n, (n, g.SetCalls)
    # something else wipes a plot (e.g. a pillage-replace): the next turn repairs it
    lua.execute('Players[3].cities[1].plot.imp = -1')
    lua.execute('Fire("PlayerDoTurn", 3)')
    assert imp(9, 9) == barad
    lua.execute('Fire("SetPopulation", 9, 9, 1, 2)')
    assert g.Revealed == 144, g.Revealed                           # fog removed for the human team only
    print('\n'.join(out[:6]))

    # no Mordor in the game: the human's capital anchors the controls
    lua2, out2 = run(script, anchor_present=False)
    lua2.execute('Found(0, 3, 3, "TXT_KEY_CITY_NAME_MEC_MINAS_TIRITH")')
    assert any('control A' in l and 'MINAS_TIRITH' in l for l in out2), out2
    print('OK: test_improvements (%d log lines, %d SetImprovementType calls)' % (len(out), g.SetCalls))


if __name__ == '__main__':
    main()

"""Offline test of MEC_Landmarks.lua (as built into dist/) against a small mock of the Civ 5 Lua API.

Run: build/venv/bin/python tools/landmarks/test_landmarks.py      (needs lupa; run build_dlc.py first)
Checks: founding, Dynamic-City-Naming rename, manual rename (picked up on PlayerDoTurn), capture,
renaming away (building removed), literal player-typed names, cities that must stay stock.
"""
import os
import sys

from lupa.lua51 import LuaRuntime  # Civ 5 uses Lua 5.1

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
SCRIPT = os.path.join(ROOT, 'dist', 'DLC', 'MiddleEarth', 'UI', 'MEC_Landmarks.lua')

MOCK = r'''
GameDefines = { MAX_PLAYERS = 4 }
local buildings = {
  { ID = 0, Type = "BUILDING_PALACE" },
  { ID = 7, Type = "BUILDING_MEC_LM_BARAD_DUR" },
  { ID = 8, Type = "BUILDING_MEC_LM_BARAD_DUR_T1" },
  { ID = 9, Type = "BUILDING_MEC_LM_BARAD_DUR_T2" },
  { ID = 10, Type = "BUILDING_MEC_LM_BARAD_DUR_T3" },
  { ID = 11, Type = "BUILDING_MEC_LM_MOUNT_DOOM" },
  { ID = 12, Type = "BUILDING_MEC_LM_MOUNT_DOOM_T1" },
  { ID = 13, Type = "BUILDING_MEC_LM_MOUNT_DOOM_T2" },
  { ID = 14, Type = "BUILDING_MEC_LM_MOUNT_DOOM_T3" },
}
-- strict: only iteration (GameInfo.Buildings()) is allowed; direct indexing returned wrong rows in game
GameInfo = { Buildings = setmetatable({}, {
  __call = function() local i = 0; return function() i = i + 1; return buildings[i] end end,
  __index = function(_, k) error("direct GameInfo.Buildings[" .. tostring(k) .. "] lookup (unreliable in game)", 2) end }) }
local handlers = {}
local function event(name) handlers[name] = {}; return { Add = function(f) table.insert(handlers[name], f) end } end
GameEvents = { PlayerCityFounded = event("PlayerCityFounded"), CityCaptureComplete = event("CityCaptureComplete"),
               PlayerDoTurn = event("PlayerDoTurn") }
function Fire(name, ...) for _, f in ipairs(handlers[name]) do f(...) end end

local plots = {}
Players = {}
for i = 0, 3 do
  local p = { id = i, cities = {} }
  function p:IsAlive() return true end
  function p:Cities() local i2 = 0; return function() i2 = i2 + 1; return self.cities[i2] end end
  Players[i] = p
end
function NewCity(owner, x, y, key)
  local c = { owner = owner, x = x, y = y, key = key, b = {} }
  function c:GetNameKey() return self.key end
  function c:SetName(k) self.key = k end
  function c:GetX() return self.x end
  function c:GetY() return self.y end
  function c:GetNumRealBuilding(id) return self.b[id] or 0 end
  function c:SetNumRealBuilding(id, n) self.b[id] = n end
  table.insert(Players[owner].cities, c)
  plots[x .. "," .. y] = c
  return c
end
function MoveCity(c, newOwner)
  local old = Players[c.owner].cities
  for i, v in ipairs(old) do if v == c then table.remove(old, i) break end end
  c.owner = newOwner
  table.insert(Players[newOwner].cities, c)
end
Map = { GetPlot = function(x, y) local c = plots[x .. "," .. y]; return { GetPlotCity = function() return c end } end }
'''


def main():
    if not os.path.exists(SCRIPT):
        sys.exit('build first: python3 tools/build_dlc.py')
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK)
    # a city that exists before the script loads (loaded game)
    pre = lua.eval('NewCity(2, 9, 9, "TXT_KEY_CITY_NAME_MEC_BARAD_DUR")')
    lua.execute(open(SCRIPT, encoding='utf-8').read())
    LM = 7
    n = lambda c: c.GetNumRealBuilding(c, LM)
    fails = []

    def check(label, got, want):
        print('%-55s %s' % (label, 'ok' if got == want else 'FAIL (got %s, want %s)' % (got, want)))
        if got != want:
            fails.append(label)

    check('existing city on load gets the landmark', n(pre), 1)
    # Mordor founds its capital: named Barad-dur from Civilization_CityNames
    cap = lua.eval('NewCity(1, 5, 5, "TXT_KEY_CITY_NAME_MEC_BARAD_DUR")')
    lua.eval('Fire("PlayerCityFounded", 1, 5, 5)')
    check('capital founded as Barad-dur', n(cap), 1)
    other = lua.eval('NewCity(1, 6, 6, "TXT_KEY_CITY_NAME_MEC_GORGOROTH")')
    lua.eval('Fire("PlayerCityFounded", 1, 6, 6)')
    check('other Mordor city stays stock', n(other), 0)
    other2 = lua.eval('NewCity(0, 1, 1, "TXT_KEY_CITY_NAME_MEC_HOBBITON")')
    lua.eval('Fire("PlayerCityFounded", 0, 1, 1)')
    check('other civ city stays stock', n(other2), 0)
    # captured by player 0: keeps it (name unchanged)
    lua.eval('MoveCity')(cap, 0)
    lua.eval('Fire("CityCaptureComplete", 1, true, 5, 5, 0, 3, true)')
    check('captured Barad-dur keeps the landmark', n(cap), 1)
    # renamed away -> removed on the next turn of its owner
    cap.SetName(cap, 'Dark Tower')
    lua.eval('Fire("PlayerDoTurn", 0)')
    check('renamed away: landmark removed', n(cap), 0)
    # player types "barad-dûr" as a literal name -> landmark
    other.SetName(other, 'barad-dûr')
    lua.eval('Fire("PlayerDoTurn", 1)')
    check('player-typed "barad-dûr" gets the landmark', n(other), 1)
    other.SetName(other, 'Barad Dur')
    lua.eval('Fire("PlayerDoTurn", 1)')
    check('player-typed "Barad Dur" keeps it', n(other), 1)
    # other buildings untouched
    check('no other building set', sorted(k for k in cap.b.keys()), [LM])
    # diagnostic variants: a city renamed "Barad Test 2" gets exactly that variant, and switching works
    other2.SetName(other2, 'Barad Test 2')
    lua.eval('Fire("PlayerDoTurn", 0)')
    check('"Barad Test 2" gets the T2 variant only', (n(other2), other2.GetNumRealBuilding(other2, 9)), (0, 1))
    other2.SetName(other2, 'barad test 3')
    lua.eval('Fire("PlayerDoTurn", 0)')
    check('renamed to "barad test 3": T3 only', tuple(other2.GetNumRealBuilding(other2, i) for i in (7, 8, 9, 10)),
          (0, 0, 0, 1))
    # ---- Mount Doom: the volcano only for a city NAMED Mount Doom, with or without Dynamic City Naming
    MD = 11
    md = lambda c: c.GetNumRealBuilding(c, MD)
    doom = lua.eval('NewCity(1, 20, 20, "TXT_KEY_CITY_NAME_MEC_MOUNT_DOOM")')
    lua.eval('Fire("PlayerCityFounded", 1, 20, 20)')
    check('city-list "Mount Doom" gets the volcano', md(doom), 1)
    check('... and not Barad-dur', n(doom), 0)
    dcn = lua.eval('NewCity(0, 21, 21, "TXT_KEY_CITY_NAME_MEC_HOBBITON")')
    dcn.SetName(dcn, 'TXT_KEY_CITY_NAME_MEC_MOUNT_DOOM')
    lua.eval('Fire("PlayerCityFounded", 0, 21, 21)')
    check('DCN-renamed to Mount Doom (any civ) gets the volcano', md(dcn), 1)
    away = lua.eval('NewCity(1, 22, 22, "TXT_KEY_CITY_NAME_MEC_MOUNT_DOOM")')
    away.SetName(away, 'TXT_KEY_CITY_NAME_MEC_UDUN_VALE')
    lua.eval('Fire("PlayerCityFounded", 1, 22, 22)')
    check('DCN renamed away from Mount Doom: no volcano', md(away), 0)
    oro = lua.eval('NewCity(1, 23, 23, "TXT_KEY_CITY_NAME_MEC_ORODRUIN")')
    lua.eval('Fire("PlayerCityFounded", 1, 23, 23)')
    check('"Orodruin" is not "Mount Doom": no volcano', md(oro), 0)
    oro.SetName(oro, 'mount doom')
    lua.eval('Fire("PlayerDoTurn", 1)')
    check('player-typed "mount doom" gets the volcano', md(oro), 1)
    doom.SetName(doom, 'Doom Test 1')
    lua.eval('Fire("PlayerDoTurn", 1)')
    check('"Doom Test 1" gets the static variant only', (md(doom), doom.GetNumRealBuilding(doom, 12)), (0, 1))
    lua.eval('MoveCity')(dcn, 2)
    dcn.SetName(dcn, 'TXT_KEY_CITY_NAME_MEC_GORGOROTH')
    lua.eval('Fire("CityCaptureComplete", 0, false, 21, 21, 2, 3, true)')
    check('captured and renamed by DCN: volcano removed', md(dcn), 0)
    if fails:
        sys.exit('%d check(s) failed' % len(fails))
    print('all landmark checks passed')


if __name__ == '__main__':
    main()

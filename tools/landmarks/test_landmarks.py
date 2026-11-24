"""Offline test of MEC_Landmarks.lua (as built into dist/) against a small mock of the Civ 5 Lua API.

Run: build/venv/bin/python tools/landmarks/test_landmarks.py      (needs lupa; run build_dlc.py first)
Checks: founding, Dynamic-City-Naming rename, manual rename (picked up on PlayerDoTurn), capture,
renaming away (building removed), literal player-typed names, cities that must stay stock.
"""
import os
import sys

from lupa.lua51 import LuaRuntime  # Civ 5 uses Lua 5.1

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import landmarks  # noqa: E402
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
SCRIPT = os.path.join(ROOT, 'dist', 'DLC', 'MiddleEarth', 'UI', 'MEC_Landmarks.lua')

MOCK = r'''
GameDefines = { MAX_PLAYERS = 4, MAX_MAJOR_CIVS = 3 }
local buildings = { { ID = 0, Type = "BUILDING_PALACE" }, @@BUILDINGS@@ }
-- strict: only iteration (GameInfo.Buildings()) is allowed; direct indexing returned wrong rows in game
GameInfo = { Buildings = setmetatable({}, {
  __call = function() local i = 0; return function() i = i + 1; return buildings[i] end end,
  __index = function(_, k) error("direct GameInfo.Buildings[" .. tostring(k) .. "] lookup (unreliable in game)", 2) end }) }
local handlers = {}
local function event(name) handlers[name] = {}; return { Add = function(f) table.insert(handlers[name], f) end } end
GameEvents = { PlayerCityFounded = event("PlayerCityFounded"), CityCaptureComplete = event("CityCaptureComplete"),
               PlayerDoTurn = event("PlayerDoTurn"), CityCanConstruct = event("CityCanConstruct") }
-- like the game: every handler must allow it
function CanConstruct(p, c, b) for _, f in ipairs(handlers.CityCanConstruct) do if not f(p, c, b) then return false end end return true end
function Fire(name, ...) for _, f in ipairs(handlers[name]) do f(...) end end

local plots = {}
Players = {}
for i = 0, 3 do
  local p = { id = i, cities = {} }
  function p:IsAlive() return true end
  function p:IsHuman() return self.id == 0 end
  function p:IsMinorCiv() return self.id == 3 end     -- player 3 = a city-state
  function p:GetTeam() return self.id end
  function p:Cities() local i2 = 0; return function() i2 = i2 + 1; return self.cities[i2] end end
  function p:GetCityByID(id) for _, c in ipairs(self.cities) do if c.id == id then return c end end end
  Players[i] = p
end
function NewCity(owner, x, y, key)
  NextCityID = (NextCityID or 100) + 1
  local c = { owner = owner, x = x, y = y, key = key, b = {}, id = NextCityID }
  function c:GetNameKey() return self.key end
  function c:GetOwner() return self.owner end
  function c:IsCapital() return Players[self.owner].cities[1] == self end
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
-- 10 plots for the fog-of-war reveal; record what was done per team
Revealed, Visible, NextCityID = {}, {}, 100
local mapPlots = {}
for i = 0, 9 do
  local pl = {}
  function pl:SetRevealed(team, b) Revealed[team] = (Revealed[team] or 0) + (b and 1 or 0) end
  function pl:ChangeVisibilityCount(team, n, inv, a, b) Visible[team] = (Visible[team] or 0) + n end
  mapPlots[i] = pl
end
Map.GetNumPlots = function() return 10 end
Map.GetPlotByIndex = function(i) return mapPlots[i] end
-- strict globals: an API the mock doesn't define is an error, not a silent nil
setmetatable(_G, { __index = function(_, k) error("unknown global " .. tostring(k), 2) end })
'''


def buildable_tests(lua, pre, LM, n, check, fails):
    """landmarks.BUILDABLE: never given by Lua; buildable (1 production) only in the matching city."""
    can = lambda c, b=LM: lua.eval('CanConstruct')(c.owner, c.id, b)
    check('existing Barad-dur on load is NOT given the landmark', n(pre), 0)
    cap = lua.eval('NewCity(1, 5, 5, "TXT_KEY_CITY_NAME_MEC_BARAD_DUR")')
    lua.eval('Fire("PlayerCityFounded", 1, 5, 5)')
    check('capital founded as Barad-dur: nothing given (stock art)', n(cap), 0)
    lua.eval('Fire("PlayerDoTurn", 1)')
    check('... still nothing after a turn', n(cap), 0)
    check('Barad-dur CAN build the landmark', can(cap), True)
    other = lua.eval('NewCity(1, 6, 6, "TXT_KEY_CITY_NAME_MEC_GORGOROTH")')
    check('other city can NOT build it', can(other), False)
    check('other buildings unaffected', can(other, 0), True)
    doom = lua.eval('NewCity(1, 7, 7, "TXT_KEY_CITY_NAME_MEC_MOUNT_DOOM")')
    check('Mount Doom can build it (ONE_REGISTRATION)', can(doom), True)
    cap.SetNumRealBuilding(cap, LM, 1)          # the city finishes building it
    lua.eval('Fire("PlayerDoTurn", 1)')
    check('built landmark stays', n(cap), 1)
    cap.SetName(cap, 'Dark Tower')
    lua.eval('Fire("PlayerDoTurn", 1)')
    check('renamed away: landmark removed', n(cap), 0)
    check('renamed away: can no longer build it', can(cap), False)
    other.SetName(other, 'barad-dûr')
    check('player-typed "barad-dûr" can build it', can(other), True)
    if fails:
        sys.exit('%d check(s) failed' % len(fails))
    print('all checks passed (buildable mode)')


def delayed_tests(lua, pre, LM, n, check, fails, lm):
    """landmarks.GIVE_AT_FOUNDING = False: given on the owner's next PlayerDoTurn, never in the founding event.
    Runs for the first enabled landmark (lm); the Mount Doom part only while Barad-dur / Mount Doom are enabled."""
    t = lm['title']
    check('existing %s on load gets the landmark' % t, n(pre), 1)
    cap = lua.eval('NewCity(1, 5, 5, "%s")' % lm['name_keys'][0])
    lua.eval('Fire("PlayerCityFounded", 1, 5, 5)')
    check('founding turn: nothing yet (stock art)', n(cap), 0)
    lua.eval('Fire("PlayerDoTurn", 0)')
    check("another player's turn: still nothing", n(cap), 0)
    lua.eval('Fire("PlayerDoTurn", 1)')
    check("owner's next turn: landmark given", n(cap), 1)
    other = lua.eval('NewCity(1, 6, 6, "TXT_KEY_CITY_NAME_MEC_GORGOROTH")')
    lua.eval('Fire("PlayerCityFounded", 1, 6, 6)')
    lua.eval('Fire("PlayerDoTurn", 1)')
    check('other city stays stock', n(other), 0)
    lua.eval('MoveCity')(cap, 0)
    lua.eval('Fire("CityCaptureComplete", 1, true, 5, 5, 0, 3, true)')
    check('captured %s keeps it' % t, n(cap), 1)
    cap.SetName(cap, 'Dark Tower')
    lua.eval('Fire("CityCaptureComplete", 1, true, 5, 5, 0, 3, true)')
    check('capture event removes it after a rename', n(cap), 0)
    lua.eval('Fire("PlayerDoTurn", 0)')
    check('renamed away: stays removed', n(cap), 0)
    typed = lm['aliases'][-1].lower()
    other.SetName(other, typed)
    lua.eval('Fire("PlayerDoTurn", 1)')
    check('player-typed "%s": given on the next turn' % typed, n(other), 1)
    check('no other building set', sorted(k for k in other.b.keys()), [LM])
    if lm['key'] != 'BARAD_DUR':
        if fails:
            sys.exit('%d check(s) failed' % len(fails))
        print('all checks passed (given on the next turn)')
        return
    doom = lua.eval('NewCity(1, 7, 7, "TXT_KEY_CITY_NAME_MEC_MOUNT_DOOM")')
    lua.eval('Fire("PlayerCityFounded", 1, 7, 7)')
    check('Mount Doom founding turn: nothing', n(doom), 0)
    lua.eval('Fire("PlayerDoTurn", 1)')
    check('Mount Doom next turn: Barad-dur landmark (ONE_REGISTRATION)', n(doom), 1)
    if fails:
        sys.exit('%d check(s) failed' % len(fails))
    print('all checks passed (given on the next turn)')


def all_cities_tests(lua, pre, LM, n, check, fails):
    """landmarks.ALL_CITIES_TEST + REVEAL_MAP (+ GIVE_AT_FOUNDING): every city (or, with TEST_MINORS_ONLY, every
    city-state city) gets ONE of the test landmarks, picked by ((A x + B y) mod M) mod count, at founding."""
    ids = {e['building']: 7 + i for i, e in enumerate(landmarks.entries('--landmark-tests' in sys.argv))}
    tests = [ids[b] for b in landmarks.test_buildings()]
    A, B, M = landmarks.TEST_HASH
    scope = landmarks.TEST_SCOPE
    moria = ids['BUILDING_MEC_LM_MORIA']

    def got(c):         # the landmark buildings the city has
        return sorted(k for k, v in c.b.items() if v == 1 and k in ids.values())

    def want(c):
        minor = c.owner == 3                     # player 3 = the city-state in the mock
        if (scope == 'minors' and not minor) or (scope == 'majors' and minor):
            return [moria] if c.GetNameKey(c) == 'TXT_KEY_CITY_NAME_MEC_MORIA' else []
        return [tests[((A * c.GetX(c) + B * c.GetY(c)) % M) % len(tests)]]
    check('fog: human team 0 revealed (10 plots)', lua.eval('Revealed[0]'), 10)
    check('fog: human team 0 made visible (10 plots)', lua.eval('Visible[0]'), 10)
    check('fog: AI team 1 untouched', lua.eval('Revealed[1]'), None)
    check('existing city on load: as expected', got(pre), want(pre))
    at_founding = lua.eval('g_GiveAtFounding')
    cities = []
    for owner, x, y, key in [(1, 5, 5, 'MEC_GORGOROTH'), (1, 6, 6, 'MEC_MORIA'), (3, 7, 7, 'MECS_DALE')]:
        c = lua.eval('NewCity(%d, %d, %d, "TXT_KEY_CITY_NAME_%s")' % (owner, x, y, key))
        lua.eval('Fire("PlayerCityFounded", %d, %d, %d)' % (owner, x, y))
        check('%s at %d,%d: as expected at founding' % (key, x, y), got(c), want(c) if at_founding else [])
        cities.append(c)
    # cities (of the tested kind) at positions that hit every version
    owner = 3 if scope == 'minors' else 1
    spots, seen = [], set()
    for x in range(10, 40):
        v = ((A * x + B * 9) % M) % len(tests)
        if v not in seen:
            seen.add(v)
            spots.append(x)
    css = []
    for x in spots:
        c = lua.eval('NewCity(%d, %d, 9, "TXT_KEY_CITY_NAME_MECS_X%d")' % (owner, x, x))
        lua.eval('Fire("PlayerCityFounded", %d, %d, 9)' % (owner, x))
        css.append(c)
    check('tested cities get every version (%d)' % len(tests), sorted(got(c)[0] for c in css), sorted(tests))
    missed = lua.eval('NewCity(%d, 8, 8, "TXT_KEY_CITY_NAME_MECS_EDORAS")' % owner)
    lua.eval('Fire("PlayerDoTurn", 0)')
    check("missed city: given on ANOTHER player's turn", got(missed), want(missed))
    if fails:
        sys.exit('%d check(s) failed' % len(fails))
    print('all checks passed (render test, %d versions, %s, + no fog)'
          % (len(tests), 'scope ' + scope))


def main():
    if not os.path.exists(SCRIPT):
        sys.exit('build first: python3 tools/build_dlc.py')
    lua = LuaRuntime(unpack_returned_tuples=True)
    # the landmark rows get IDs 7, 8, ... (with Barad-dur enabled: 7 = Barad-dur, 8-10 its tests, as below)
    ents = landmarks.entries('--landmark-tests' in sys.argv)
    lua.execute(MOCK.replace('@@BUILDINGS@@', ', '.join('{ ID = %d, Type = "%s" }' % (7 + i, e['building'])
                                                        for i, e in enumerate(ents))))
    lm = landmarks.LANDMARKS[0]
    # a city that exists before the script loads (loaded game)
    pre = lua.eval('NewCity(2, 9, 9, "%s")' % lm['name_keys'][0])
    lua.execute(open(SCRIPT, encoding='utf-8').read())
    LM = 7
    n = lambda c: c.GetNumRealBuilding(c, LM)
    fails = []

    def check(label, got, want):
        print('%-55s %s' % (label, 'ok' if got == want else 'FAIL (got %s, want %s)' % (got, want)))
        if got != want:
            fails.append(label)

    if lua.eval('g_AllCitiesTest'):
        return all_cities_tests(lua, pre, LM, n, check, fails)
    if lua.eval('g_Buildable'):
        return buildable_tests(lua, pre, LM, n, check, fails)
    if not lua.eval('g_GiveAtFounding'):
        return delayed_tests(lua, pre, LM, n, check, fails, lm)
    return founding_tests(lua, pre, LM, n, check, fails, lm)


def founding_tests(lua, pre, LM, n, check, fails, lm):
    """landmarks.GIVE_AT_FOUNDING = True (normal mode): the city named like the landmark gets it when founded;
    every other city (other names, other civs, city-states) keeps stock art."""
    t = lm['title']
    reveal = lua.eval('g_RevealMap')
    check('fog of war removed for the human team' if reveal else 'fog of war untouched',
          lua.eval('Revealed[0]'), 10 if reveal else None)
    check('existing %s on load gets the landmark' % t, n(pre), 1)
    cap = lua.eval('NewCity(1, 5, 5, "%s")' % lm['name_keys'][0])
    lua.eval('Fire("PlayerCityFounded", 1, 5, 5)')
    check('%s founded: landmark at once' % t, n(cap), 1)
    other = lua.eval('NewCity(1, 6, 6, "TXT_KEY_CITY_NAME_MEC_MOUNT_GUNDABAD")')
    lua.eval('Fire("PlayerCityFounded", 1, 6, 6)')
    check('same civ, other city: stock', n(other), 0)
    cap2 = lua.eval('NewCity(0, 1, 1, "TXT_KEY_CITY_NAME_MEC_HOBBITON")')
    lua.eval('Fire("PlayerCityFounded", 0, 1, 1)')
    check('other civ capital: stock', n(cap2), 0)
    cs = lua.eval('NewCity(3, 2, 2, "TXT_KEY_CITY_NAME_MECS_DALE")')
    lua.eval('Fire("PlayerCityFounded", 3, 2, 2)')
    check('city-state: stock', n(cs), 0)
    lua.eval('Fire("PlayerDoTurn", 1)')
    check('after a turn: still only %s' % t, [n(c) for c in (cap, other, cap2, cs)], [1, 0, 0, 0])
    lua.eval('MoveCity')(cap, 0)
    lua.eval('Fire("CityCaptureComplete", 1, true, 5, 5, 0, 3, true)')
    check('captured %s keeps it' % t, n(cap), 1)
    cap.SetName(cap, 'Goblin Hole')
    lua.eval('Fire("PlayerDoTurn", 0)')
    check('renamed away: removed', n(cap), 0)
    typed = lm['aliases'][-1].lower()
    other.SetName(other, typed)
    lua.eval('Fire("PlayerDoTurn", 1)')
    check('player-typed "%s": given' % typed, n(other), 1)
    check('no other building set', sorted(k for k, v in other.b.items() if v), [LM])
    if fails:
        sys.exit('%d check(s) failed' % len(fails))
    print('all checks passed (%s only, given at founding%s)' % (t, ', no fog' if reveal else ''))


if __name__ == '__main__':
    main()

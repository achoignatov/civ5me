import sys, sqlite3
import simulate
dbp = sys.argv[1]
db = sqlite3.connect(dbp)
allciv = [r[0] for r in db.execute("select Type from Civilizations where Type like 'CIVILIZATION_MEC_%' order by ID")]
allmin = [r[0] for r in db.execute("select Type from MinorCivilizations order by ID")]
lua, _, W, H, dump, starts = simulate.run(dbp, 'TaHugeRndWw', 5, [1,3,1,1,1,1,2,2], allciv, allmin[:22])
lua.execute(r'''
PreGame = { GetMapScript = function() return "C:\\Users\\x\\MODS\\Middle Earth MP (v 1)\\METSL\\Maps\\METSL_TaHugeRndWw.lua" end,
            GetMapOption = function(id) return MOCK_OPTIONS[id] or -1 end }
Locale = { ConvertTextKey = function(k) return "loc:" .. k end }
local handlers = {}
GameEvents = setmetatable({}, { __index = function(t, k) local e = { Add = function(f) handlers[k] = handlers[k] or {}; table.insert(handlers[k], f) end }; rawset(t, k, e); return e end })
function FireEvent(name, ...) for _, f in ipairs(handlers[name] or {}) do f(...) end end
-- units & cities
local P = getmetatable(Players[0]).__index
local Unit = {}; Unit.__index = Unit
function Unit:Kill() self.owner.units[self.id] = nil; KILLED = (KILLED or 0) + 1 end
function Unit:IsFound() return self.found == true end
function Unit:GetUnitType() return self.utype end
function Unit:GetX() return self.x end
function Unit:GetY() return self.y end
for i = 0, 63 do local p = Players[i]; p.units = {}; p.cities = {}
  if p.alive and p.start then UnitAITypes = nil  -- not available to the real in-game script
for u = 1, 2 do p.units[u] = setmetatable({ id = u, owner = p, found = (u == 1), utype = 100 + u, x = 5, y = 7 }, Unit) end end end
function P:InitUnit(t, x, y, ai) local id = #self.units + 1; self.units[id] = setmetatable({ id = id, owner = self, found = (t == 101), utype = t, x = x, y = y }, Unit); return self.units[id] end
function CountSettlers() local n, c = 0, 0 for i = 0, 21 do local p = Players[i]
  if p.alive and p.start then c = c + 1 for _, u in pairs(p.units) do if u.found then n = n + 1 end end end end return n, c end
function P:Units() local t = {} for _, u in pairs(self.units) do t[#t+1] = u end local i = 0 return function() i = i + 1 return t[i] end end
function P:Cities() local i = 0 return function() i = i + 1 return self.cities[i] end end
function P:GetNumCities() return #self.cities end
function P:IsAlive() return self.alive and (next(self.units) ~= nil or #self.cities > 0) end
local City = {}; City.__index = City
function City:GetName() return Locale.ConvertTextKey(self.name) end
function City:SetName(n) self.name = n end
function City:GetOwner() return self.owner end
function City:GetID() return self.id end
function FoundCity(pid, x, y) local p = Players[pid]; local c = setmetatable({ name = "DEFAULT_NAME", owner = pid, id = #p.cities + 1 }, City)
  table.insert(p.cities, c); Map.GetPlot(x, y).city = c; FireEvent("PlayerCityFounded", pid, x, y); return c end
local PL = getmetatable(Map.GetPlot(0,0)).__index
function PL:GetPlotCity() return self.city end
''')
src = open('../src/METSL/LUA/METSL_InGame.lua').read()
lua.execute(src)
print('units killed on turn 0:', lua.eval('KILLED'))
print('settlers / major civs after turn 0 (option on):', tuple(lua.eval('{CountSettlers()}').values()))
lua.execute(src)  # reload of a turn-0 save must not add more
print('settlers / major civs after re-running the script:', tuple(lua.eval('{CountSettlers()}').values()))
alive_minors = lua.eval('(function() local n=0 for i=22,62 do if Players[i]:IsAlive() then n=n+1 end end return n end)()')
print('city-states alive after cleanup:', alive_minors)
# Hobbits found a city next to Hobbiton (32,55); Mordor near Mount Doom
hob = allciv.index('CIVILIZATION_MEC_HOBBITS')
print('Hobbit city at 32,55 ->', lua.eval('FoundCity(%d, 32, 55).name' % hob))
print('Hobbit 2nd city at 32,55-adjacent 33,55 ->', lua.eval('FoundCity(%d, 33, 55).name' % hob))
row = db.execute("select CityX, CityY, CityName from TaHugeRndWw_DynamicCityNames where CivilizationType='CIVILIZATION_MEC_MORDOR' limit 1").fetchone()
mor = allciv.index('CIVILIZATION_MEC_MORDOR')
print('Mordor city at %d,%d -> %s (expected %s)' % (row[0], row[1], lua.eval('FoundCity(%d, %d, %d).name' % (mor, row[0], row[1])), row[2]))
# capture: Gondor takes the Hobbit city
gon = allciv.index('CIVILIZATION_MEC_GONDOR')
lua.execute('FireEvent("CityCaptureComplete", %d, false, 32, 55, %d, 3, true)' % (hob, gon))
print('after Gondor captures 32,55 ->', lua.eval('Map.GetPlot(32,55).city.name'))
# compile check of the Wood Elves script
f = lua.eval('loadstring')(open("../src/MEC/Wood Elves/LUA/Wood_Elves_Units_Promotions.lua").read())
print('Wood elves script compiles:', f is not None)
# option off (ExtraSettler is option 9 on the full maps): one settler stays one settler
lua.execute('for i = 0, 21 do local p = Players[i]; if p.units[3] then p.units[3] = nil end p.cities = {} end MOCK_OPTIONS[9] = 2')
lua.execute(src)
print('settlers / major civs with the option off:', tuple(lua.eval('{CountSettlers()}').values()))

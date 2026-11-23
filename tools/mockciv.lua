-- Minimal mock of the Civ5 map-generation Lua API, for offline testing of map scripts.
-- Python (simulate.py) provides: PY_GameInfoRows(tableName) -> list of rows, PY_Include(name) -> source,
-- MOCK_SEED, MOCK_W/H set by GetMapInitData, MOCK_OPTIONS, MOCK_MAJORS, MOCK_MINORS.

local W, H, WRAPX = 0, 0, false
local plots = {}
local rngState = MOCK_SEED or 12345
RAND_LOG = {}

-- ---------- enums ----------
PlotTypes = { PLOT_MOUNTAIN = 0, PLOT_HILLS = 1, PLOT_LAND = 2, PLOT_OCEAN = 3 }
FlowDirectionTypes = { NO_FLOWDIRECTION = -1, FLOWDIRECTION_NORTH = 0, FLOWDIRECTION_NORTHEAST = 1, FLOWDIRECTION_SOUTHEAST = 2,
	FLOWDIRECTION_SOUTH = 3, FLOWDIRECTION_SOUTHWEST = 4, FLOWDIRECTION_NORTHWEST = 5, NUM_FLOWDIRECTION_TYPES = 6 }
DirectionTypes = { NO_DIRECTION = -1, DIRECTION_NORTHEAST = 0, DIRECTION_EAST = 1, DIRECTION_SOUTHEAST = 2,
	DIRECTION_SOUTHWEST = 3, DIRECTION_WEST = 4, DIRECTION_NORTHWEST = 5, NUM_DIRECTION_TYPES = 6 }
GameOptionTypes = setmetatable({}, { __index = function(t, k) return k end })
YieldTypes = { YIELD_FOOD = 0, YIELD_PRODUCTION = 1, YIELD_GOLD = 2, YIELD_SCIENCE = 3 }
ResourceUsageTypes = { RESOURCEUSAGE_BONUS = 0, RESOURCEUSAGE_STRATEGIC = 1, RESOURCEUSAGE_LUXURY = 2 }
GameDefines = { MAX_MAJOR_CIVS = 22, MAX_CIV_PLAYERS = 63, MAX_PLAYERS = 64, MAX_MINOR_CIVS = 41,
	SHALLOW_WATER_TERRAIN = 5, DEEP_WATER_TERRAIN = 6, MIN_WATER_SIZE_FOR_OCEAN = 10 }

-- ---------- GameInfo ----------
local gi_cache = {}
local function makeTable(name)
	local rows = PY_GameInfoRows(name)
	if rows == nil then return nil end
	local list, byID, byType = {}, {}, {}
	for i = 1, #rows do
		local r = rows[i]
		list[#list + 1] = r
		if r.ID ~= nil then byID[r.ID] = r end
		if r.Type ~= nil then byType[r.Type] = r end
	end
	local t = {}
	setmetatable(t, {
		__index = function(_, k)
			if type(k) == "number" then return byID[k] end
			return byType[k]
		end,
		__call = function(_, filter)
			local i = 0
			return function()
				while true do
					i = i + 1
					local r = list[i]
					if r == nil then return nil end
					local ok = true
					if type(filter) == "table" then
						for fk, fv in pairs(filter) do
							local rv = r[fk]
							if type(rv) == "boolean" then rv = rv and 1 or 0 end
							if type(fv) == "boolean" then fv = fv and 1 or 0 end
							if rv ~= fv then ok = false end
						end
					elseif type(filter) == "string" then
						local col, val = string.match(filter, "^%s*(%w+)%s*=%s*'([^']*)'%s*$")
						if col then ok = (r[col] == val) else error("unsupported filter " .. filter) end
					end
					if ok then return r end
				end
			end
		end,
		__len = function() return #list end,
	})
	return t
end
GameInfo = setmetatable({}, { __index = function(t, name)
	if gi_cache[name] == nil then gi_cache[name] = makeTable(name) or false end
	return gi_cache[name] or nil
end })
GameInfoTypes = setmetatable({}, { __index = function(t, k)
	for _, tn in ipairs({ "Features", "Terrains", "Resources", "Improvements", "UnitPromotions", "Civilizations" }) do
		local r = GameInfo[tn][k]; if r then return r.ID end
	end
end })

TerrainTypes = {}; FeatureTypes = {}
for r in GameInfo.Terrains() do TerrainTypes[r.Type] = r.ID end
for r in GameInfo.Features() do if r.ID <= 7 then FeatureTypes[r.Type] = r.ID end end
FeatureTypes.NO_FEATURE = -1

-- ---------- RNG ----------
local function rand(n, log)
	rngState = (rngState * 1103515245 + 12345) % 2147483648
	RAND_LOG[#RAND_LOG + 1] = log
	if n == nil or n <= 0 then return 0 end
	return rngState % n
end

-- ---------- geometry ----------
local function wrapX(x) if WRAPX then return x % W end return x end
local function getPlot(x, y)
	if x == nil or y == nil then return nil end
	x = wrapX(x)
	if x < 0 or x >= W or y < 0 or y >= H then return nil end
	return plots[y * W + x]
end
local NEIGH_EVEN = { { 0, 1 }, { 1, 0 }, { 0, -1 }, { -1, -1 }, { -1, 0 }, { -1, 1 } } -- NE,E,SE,SW,W,NW
local NEIGH_ODD = { { 1, 1 }, { 1, 0 }, { 1, -1 }, { 0, -1 }, { -1, 0 }, { 0, 1 } }
local function plotDirection(x, y, dir)
	local t = (y % 2 == 1) and NEIGH_ODD or NEIGH_EVEN
	local d = t[dir + 1]
	return getPlot(x + d[1], y + d[2])
end
local function toCube(x, y)
	local q = x - (y - (y % 2)) / 2
	return q, y
end
local function hexDist(x1, y1, x2, y2)
	local best = 1e9
	local offsets = WRAPX and { -W, 0, W } or { 0 }
	for _, o in ipairs(offsets) do
		local q1, r1 = toCube(x1, y1)
		local q2, r2 = toCube(x2 + o, y2)
		local dq, dr = q1 - q2, r1 - r2
		local d = (math.abs(dq) + math.abs(dr) + math.abs(dq + dr)) / 2
		if d < best then best = d end
	end
	return best
end

-- ---------- areas ----------
local areas = {}
local Area = {}
Area.__index = Area
function Area:GetID() return self.id end
function Area:GetNumTiles() return #self.plots end
function Area:IsWater() return self.water end
function Area:CountNumUniqueResourceTypes()
	local seen, n = {}, 0
	for _, p in ipairs(self.plots) do
		if p.resource ~= -1 and not seen[p.resource] then seen[p.resource] = true; n = n + 1 end
	end
	return n
end
function Area:GetNumImprovements(id)
	local n = 0
	for _, p in ipairs(self.plots) do if p.improvement == id then n = n + 1 end end
	return n
end

-- ---------- plots ----------
local Plot = {}
Plot.__index = Plot
function Plot:GetX() return self.x end
function Plot:GetY() return self.y end
function Plot:GetIndex() return self.y * W + self.x end
function Plot:GetPlotType() return self.plotType end
function Plot:SetPlotType(t) self.plotType = t end
function Plot:GetTerrainType() return self.terrain end
function Plot:SetTerrainType(t) self.terrain = t end
function Plot:GetFeatureType() return self.feature end
function Plot:SetFeatureType(f) self.feature = f end
function Plot:GetResourceType() return self.resource end
function Plot:GetNumResource() return self.resourceNum end
function Plot:SetResourceType(r, n) self.resource = r; self.resourceNum = n or 1 end
function Plot:IsWater() return self.plotType == PlotTypes.PLOT_OCEAN end
function Plot:IsMountain() return self.plotType == PlotTypes.PLOT_MOUNTAIN end
function Plot:IsHills() return self.plotType == PlotTypes.PLOT_HILLS end
function Plot:IsFlatlands() return self.plotType == PlotTypes.PLOT_LAND end
function Plot:IsImpassable()
	if self:IsMountain() then return true end
	local f = self.feature >= 0 and GameInfo.Features[self.feature]
	return f and f.Impassable == true or false
end
function Plot:SetWOfRiver(b, d) self.wRiver = b; self.wFlow = d end
function Plot:SetNWOfRiver(b, d) self.nwRiver = b; self.nwFlow = d end
function Plot:SetNEOfRiver(b, d) self.neRiver = b; self.neFlow = d end
function Plot:IsWOfRiver() return self.wRiver == true end
function Plot:IsNWOfRiver() return self.nwRiver == true end
function Plot:IsNEOfRiver() return self.neRiver == true end
function Plot:IsRiverSide()
	if self.wRiver or self.nwRiver or self.neRiver then return true end
	local w = plotDirection(self.x, self.y, DirectionTypes.DIRECTION_WEST)
	if w and w.wRiver then return true end
	local nw = plotDirection(self.x, self.y, DirectionTypes.DIRECTION_NORTHWEST)
	if nw and nw.nwRiver then return true end
	local ne = plotDirection(self.x, self.y, DirectionTypes.DIRECTION_NORTHEAST)
	if ne and ne.neRiver then return true end
	return false
end
Plot.IsRiver = Plot.IsRiverSide
function Plot:IsAdjacentToLand()
	for d = 0, 5 do local p = plotDirection(self.x, self.y, d); if p and not p:IsWater() then return true end end
	return false
end
function Plot:IsAdjacentToShallowWater()
	for d = 0, 5 do local p = plotDirection(self.x, self.y, d); if p and p.terrain == TerrainTypes.TERRAIN_COAST then return true end end
	return false
end
function Plot:IsCoastalLand()
	if self:IsWater() then return false end
	for d = 0, 5 do local p = plotDirection(self.x, self.y, d); if p and p:IsWater() and not p:IsLake() then return true end end
	return false
end
function Plot:IsLake() return self:IsWater() and self.area and #self.area.plots < GameDefines.MIN_WATER_SIZE_FOR_OCEAN end
function Plot:IsFreshWater()
	if self:IsWater() then return false end
	if self:IsRiverSide() then return true end
	for d = 0, 5 do local p = plotDirection(self.x, self.y, d); if p and p:IsLake() then return true end end
	return false
end
function Plot:Area() return self.area end
function Plot:GetArea() return self.area and self.area.id or -1 end
function Plot:IsStartingPlot() return self.isStart == true end
function Plot:SetContinentArtType(c) self.continent = c end
function Plot:GetContinentArtType() return self.continent end
function Plot:GetPlotCity() return nil end
function Plot:GetOwner() return -1 end
function Plot:IsOwned() return false end
function Plot:CanHaveImprovement(i) return not self:IsWater() and not self:IsImpassable() and self.improvement == -1 end
function Plot:GetImprovementType() return self.improvement end
function Plot:SetImprovementType(i) self.improvement = i end
function Plot:GetLatitude() return math.floor(math.abs((H / 2) - self.y) * 90 / (H / 2)) end
local function tbool(tbl, resType, other, col)
	for r in GameInfo[tbl]{ ResourceType = resType } do
		if r[col] == other then return true end
	end
	return false
end
function Plot:CanHaveResource(resID, ignoreLat)
	if self.resource ~= -1 then return false end
	local res = GameInfo.Resources[resID]
	if not res then return false end
	if self:IsMountain() then return false end
	local terrain = GameInfo.Terrains[self.terrain].Type
	if self.feature ~= -1 then
		local f = GameInfo.Features[self.feature]
		if f.NaturalWonder then return false end
		if not tbool("Resource_FeatureBooleans", res.Type, f.Type, "FeatureType") then return false end
		if not tbool("Resource_FeatureTerrainBooleans", res.Type, terrain, "TerrainType") then return false end
	else
		local ok = tbool("Resource_TerrainBooleans", res.Type, terrain, "TerrainType")
		if self:IsHills() then
			ok = tbool("Resource_TerrainBooleans", res.Type, "TERRAIN_HILL", "TerrainType") or (ok and res.Hills)
		end
		if not ok then return false end
	end
	if self:IsFlatlands() and res.Flatlands == false and self.feature == -1 and not self:IsWater() then
		-- Flatlands=false resources only on hills
		if not tbool("Resource_TerrainBooleans", res.Type, terrain, "TerrainType") then return false end
	end
	if res.NoRiverSide and self:IsRiverSide() then return false end
	if self:IsWater() and res.MinAreaSize and res.MinAreaSize > 0 and #self.area.plots < res.MinAreaSize then return false end
	if not ignoreLat then
		local lat = self:GetLatitude()
		if lat < (res.MinLatitude or 0) or lat > (res.MaxLatitude or 90) then return false end
	end
	return true
end

-- ---------- Map ----------
Map = {}
function Map.GetGridSize() return W, H end
function Map.GetNumPlots() return W * H end
function Map.GetPlot(x, y) return getPlot(x, y) end
function Map.GetPlotByIndex(i) return plots[i] end
function Map.GetPlotXY(x, y, dx, dy) return getPlot(x + (dx or 0), y + (dy or 0)) end
function Map.PlotXYWithRangeCheck(x, y, dx, dy, range)
	local p = getPlot(x + dx, y + dy)
	if p == nil then return nil end
	if hexDist(x, y, p.x, p.y) > range then return nil end
	return p
end
function Map.PlotDirection(x, y, dir) return plotDirection(x, y, dir) end
function Map.PlotDistance(x1, y1, x2, y2) return hexDist(x1, y1, x2, y2) end
function Map.Rand(n, log) return rand(n, log) end
function Map.IsWrapX() return WRAPX end
function Map.IsWrapY() return false end
function Map.GetCustomOption(id) return MOCK_OPTIONS[id] or -1 end
function Map.RecalculateAreas()
	areas = {}
	for i = 0, W * H - 1 do plots[i].area = nil end
	local nextID = 1
	for i = 0, W * H - 1 do
		local p = plots[i]
		if p.area == nil then
			local a = setmetatable({ id = nextID, plots = {}, water = p:IsWater() }, Area)
			nextID = nextID + 1
			areas[#areas + 1] = a
			local stack = { p }
			p.area = a
			while #stack > 0 do
				local q = table.remove(stack)
				a.plots[#a.plots + 1] = q
				for d = 0, 5 do
					local n = plotDirection(q.x, q.y, d)
					if n and n.area == nil and n:IsWater() == a.water then
						n.area = a
						stack[#stack + 1] = n
					end
				end
			end
		end
	end
end
function Map.GetArea(id) for _, a in ipairs(areas) do if a.id == id then return a end end end
function Map.Areas()
	local i = 0
	return function() i = i + 1; local a = areas[i]; if a then return a.id, a end end
end
function Map.GetNumResources(id)
	local n = 0
	for i = 0, W * H - 1 do if plots[i].resource == id then n = n + 1 end end
	return n
end
function Map.GetNumResourcesOnLand(id)
	local n = 0
	for i = 0, W * H - 1 do if plots[i].resource == id and not plots[i]:IsWater() then n = n + 1 end end
	return n
end
function Map.GetRandomResourceQuantity(id)
	local r = GameInfo.Resources[id]
	if r.ResourceUsage == 1 then return 2 + rand(3, "qty") end
	return 1
end
function Map.DefaultContinentStamper() end
function Map.ChangeAIMapHint() end

-- ---------- players ----------
local Player = {}
Player.__index = Player
function Player:GetID() return self.id end
function Player:IsEverAlive() return self.alive end
function Player:IsAlive() return self.alive end
function Player:IsMinorCiv() return self.minor ~= nil end
function Player:IsBarbarian() return false end
function Player:GetCivilizationType()
	if self.minor then return GameInfo.Civilizations.CIVILIZATION_MINOR.ID end
	return self.civ or -1
end
function Player:GetMinorCivType() return self.minor or -1 end
function Player:SetStartingPlot(p)
	if self.start then self.start.isStart = false end
	self.start = p; p.isStart = true
end
function Player:GetStartingPlot() return self.start end
function Player:GetTeam() return self.id end
Players = {}
for i = 0, GameDefines.MAX_PLAYERS - 1 do
	Players[i] = setmetatable({ id = i, alive = false }, Player)
end
for i, civType in ipairs(MOCK_MAJORS) do
	local p = Players[i - 1]; p.alive = true; p.civ = GameInfo.Civilizations[civType].ID
end
for i, minorType in ipairs(MOCK_MINORS) do
	local p = Players[GameDefines.MAX_MAJOR_CIVS + i - 1]; p.alive = true; p.minor = GameInfo.MinorCivilizations[minorType].ID
end

Game = {}
function Game.CountCivPlayersAlive()
	local n = 0
	for i = 0, GameDefines.MAX_CIV_PLAYERS - 1 do if Players[i].alive then n = n + 1 end end
	return n
end
function Game.GetStartEra() return 0 end
function Game.IsOption() return false end
function Game.GetElapsedGameTurns() return 0 end
function Game.Rand(n, log) return rand(n, log) end

-- ---------- include ----------
local included = {}
function include(name)
	local key = string.lower(string.gsub(name, "%.lua$", ""))
	if included[key] then return end
	included[key] = true
	local src, path = PY_Include(name)
	if not src then print("include: NOT FOUND " .. name); return end
	local f, err = loadstring(src, "@" .. path)
	if not f then error(err) end
	f()
end

-- ---------- run ----------
function MOCK_InitMap()
	local d = GetMapInitData(3)
	W, H, WRAPX = d.Width, d.Height, d.WrapX
	for y = 0, H - 1 do
		for x = 0, W - 1 do
			plots[y * W + x] = setmetatable({ x = x, y = y, plotType = PlotTypes.PLOT_OCEAN, terrain = 6, feature = -1,
				resource = -1, resourceNum = 0, improvement = -1, continent = 0 }, Plot)
		end
	end
	return W, H
end

function MOCK_Dump()
	-- returns per-plot arrays for Python checks
	local out = {}
	for i = 0, W * H - 1 do
		local p = plots[i]
		out[i + 1] = { p.plotType, p.terrain, p.feature, p.resource, p.resourceNum, p.improvement, p.isStart and 1 or 0,
			(p.wRiver and 1 or 0) + (p.nwRiver and 2 or 0) + (p.neRiver and 4 or 0), p.continent }
	end
	return out
end

function MOCK_Starts()
	local out = {}
	for i = 0, GameDefines.MAX_CIV_PLAYERS - 1 do
		local p = Players[i]
		if p.alive and p.start then
			local name = p.minor and GameInfo.MinorCivilizations[p.minor].Type or GameInfo.Civilizations[p.civ].Type
			out[#out + 1] = { i, name, p.start.x, p.start.y }
		end
	end
	return out
end

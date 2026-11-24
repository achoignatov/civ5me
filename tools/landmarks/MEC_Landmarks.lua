-- MEC_Landmarks
-- Per-city landmark models (docs/CITY_MODELS.md, Plan A).
--
-- A city whose name matches a landmark gets that landmark's dummy building (no gameplay effect);
-- the building's art is the landmark model. Every other city never gets one and keeps the stock art.
--
-- Multiplayer: runs on every client and changes game state only from synchronised GameEvents,
-- deciding from synchronised data only (the city's name KEY, never the localised display name),
-- so every client gives and removes exactly the same buildings.
--------------------------------------------------------------

-- @@LANDMARK_TABLE@@  (replaced at build time by tools/landmarks/landmarks.py: g_LandmarkDefs = {...})

-- Building lookups by iterating the rows: GameInfo.Buildings["TYPE"] returned the WRONG row in game for some of
-- our buildings (2026-11-23: "..._P32" gave "..._LOOSE"), so never index GameInfo.Buildings directly.
local g_BuildingID, g_BuildingType = {}, {}
for row in GameInfo.Buildings() do
	g_BuildingID[row.Type] = row.ID
	g_BuildingType[row.ID] = row.Type
end

local g_ByName = {}      -- name key or lower-cased literal name -> building ID
local g_AllIDs = {}      -- every landmark building ID

for _, def in ipairs(g_LandmarkDefs) do
	local id = g_BuildingID[def.Building]
	if id then
		table.insert(g_AllIDs, id)
		for _, k in ipairs(def.Keys) do g_ByName[k] = id end
		for _, a in ipairs(def.Aliases) do g_ByName[string.lower(a)] = id end
	else
		print("MEC_Landmarks: building " .. def.Building .. " missing from the database")
	end
end
table.sort(g_AllIDs)

-- g_AllCitiesTest (landmarks.ALL_CITIES_TEST): render test. EVERY city (major civs and city-states) gets one of the
-- test landmarks (g_AllCitiesBuildings), whatever its name, picked by map position: ((A x + B y) mod M) mod #list with
-- g_TestHash = { A, B, M } (chosen per test so the cities of the fixed-start test map split evenly, see landmarks.py).
-- g_TestScope: "all", "minors" (city-states only) or "majors" (major civ cities only); the others follow the name rules.
-- Synchronised data only (plot coordinates), so every client picks the same one.
local g_TestIDs = {}
if g_AllCitiesTest then
	for _, b in ipairs(g_AllCitiesBuildings) do
		if g_BuildingID[b] then table.insert(g_TestIDs, g_BuildingID[b]) else print("MEC_Landmarks: test building " .. b .. " missing") end
	end
end
local g_TestID = g_TestIDs[1]

local function LandmarkFor(city)
	local owner = Players[city:GetOwner()]
	local minor = owner ~= nil and owner:IsMinorCiv()
	if g_TestID and (g_TestScope == "all" or (g_TestScope == "minors" and minor) or (g_TestScope == "majors" and not minor)) then
		local h = (g_TestHash[1] * city:GetX() + g_TestHash[2] * city:GetY()) % g_TestHash[3]
		return g_TestIDs[h % #g_TestIDs + 1]
	end
	local key = city:GetNameKey()
	if not key then return nil end
	return g_ByName[key] or g_ByName[string.lower(key)]
end

-- g_Buildable (landmarks.BUILDABLE): the landmark is built by the city (1 production, only where the name matches),
-- so Lua never ADDS it; it only removes a landmark from a city whose name no longer matches.
-- canAdd = false: only remove (g_GiveAtFounding = false: founding/capture events never add the art; the owner's next
-- PlayerDoTurn does, so the model goes into a city whose art already exists).
local function SyncCity(city, canAdd)
	if not city then return end
	local want = LandmarkFor(city)
	for _, id in ipairs(g_AllIDs) do
		local n = (id == want) and 1 or 0
		if (g_Buildable or canAdd == false) and n == 1 then n = city:GetNumRealBuilding(id) end
		if city:GetNumRealBuilding(id) ~= n then
			city:SetNumRealBuilding(id, n)
			print("MEC_Landmarks: " .. tostring(city:GetNameKey()) .. " (" .. city:GetX() .. "," .. city:GetY() .. ") "
				.. g_BuildingType[id] .. " = " .. n)
		end
	end
end

local function SyncPlayer(playerID)
	local player = Players[playerID]
	if player and player:IsAlive() then
		for city in player:Cities() do SyncCity(city, true) end
	end
end

local function SyncAll()
	for playerID = 0, GameDefines.MAX_PLAYERS - 1 do SyncPlayer(playerID) end
end

local function SyncAt(x, y)
	local plot = Map.GetPlot(x, y)
	if plot then SyncCity(plot:GetPlotCity(), g_GiveAtFounding) end
end

local g_IsLandmark = {}
for _, id in ipairs(g_AllIDs) do g_IsLandmark[id] = true end

if #g_AllIDs > 0 then
	if g_Buildable then
		-- a landmark can only be built in the city whose name matches it (synchronised data only)
		GameEvents.CityCanConstruct.Add(function(playerID, cityID, buildingType)
			if not g_IsLandmark[buildingType] then return true end
			local player = Players[playerID]
			local city = player and player:GetCityByID(cityID)
			return city ~= nil and LandmarkFor(city) == buildingType
		end)
	end
	-- registered after METSL_InGame (loaded first), so a Dynamic City Naming rename has already happened
	GameEvents.PlayerCityFounded.Add(function(playerID, x, y) SyncAt(x, y) end)
	GameEvents.CityCaptureComplete.Add(function(oldOwner, isCapital, x, y, newOwner) SyncAt(x, y) end)
	-- catches renames (and anything missed): every player's turn re-checks EVERY city (2026-11-24: in the all-capitals
	-- test only Moria was ever given its landmark here, so this no longer relies on the owner's own turn)
	GameEvents.PlayerDoTurn.Add(function(playerID) SyncAll() end)
	-- loaded games, and cities that exist before this script runs
	SyncAll()
	print("MEC_Landmarks: active, " .. #g_AllIDs .. " landmark(s)"
		.. (g_TestID and (", TEST (" .. g_TestScope .. "): each city gets one of "
			.. table.concat(g_AllCitiesBuildings, " / ")) or "")
		.. (g_GiveAtFounding and ", given at founding" or ", given on the next turn"))
end

-- g_RevealMap (landmarks.REVEAL_MAP): render test without fog of war. Every plot is revealed to and kept visible
-- for every human player's team (the same for every client, so it also works in multiplayer).
if g_RevealMap then
	local teams, n = {}, 0
	for playerID = 0, GameDefines.MAX_MAJOR_CIVS - 1 do
		local player = Players[playerID]
		if player and player:IsAlive() and player:IsHuman() then teams[player:GetTeam()] = true end
	end
	for team in pairs(teams) do
		for i = 0, Map.GetNumPlots() - 1 do
			local plot = Map.GetPlotByIndex(i)
			plot:SetRevealed(team, true)
			plot:ChangeVisibilityCount(team, 1, -1, true, true)
		end
		n = n + 1
	end
	print("MEC_Landmarks: TEST: fog of war removed for " .. n .. " human team(s), " .. Map.GetNumPlots() .. " plots")
end

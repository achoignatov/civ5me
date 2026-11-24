-- MEC_LandmarkImprovements
-- Landmark models as tile IMPROVEMENTS (docs/CITY_ARCHITECTURE_RESEARCH.md, Approach C).
--
-- Each city plot gets a purely visual landmark improvement; the city's own art is never touched.
-- Founding and capture clear a city plot's improvement (CvCity::init), so every sync re-applies it.
--
-- Multiplayer: runs on every client and changes game state only from synchronised GameEvents, deciding from
-- synchronised data only (players, plots, civilization types), so every client sets exactly the same plots.
-- Log lines start with "MEC_LMI" and report what the plot says AFTER the change (read back from the game).
--------------------------------------------------------------

-- @@LANDMARK_TABLE@@  (replaced at build time by tools/landmarks/improvements.py)

-- Lookups by iterating the rows (direct GameInfo.X["TYPE"] indexing returned wrong rows in game, 2026-11-23).
local g_ID, g_Type = {}, {}
for row in GameInfo.Improvements() do
	g_ID[row.Type] = row.ID
	g_Type[row.ID] = row.Type
end
local g_IsOurs = {}
for _, t in ipairs(g_Improvements) do
	if g_ID[t] then g_IsOurs[g_ID[t]] = true else print("MEC_LMI: improvement " .. t .. " missing from the database") end
end
local g_CivID
for row in GameInfo.Civilizations() do
	if row.Type == g_AnchorCiv then g_CivID = row.ID end
end

local function Name(id)
	if id == nil or id < 0 then return "none" end
	return g_Type[id] or tostring(id)
end

-- Set the plot's improvement (no builder: -1 is the DLL's own default) and log what the game reports back.
local function SetPlot(plot, id, why)
	local before = plot:GetImprovementType()
	if before == id then return end
	plot:SetImprovementType(id, -1)
	print("MEC_LMI: " .. why .. " (" .. plot:GetX() .. "," .. plot:GetY() .. ") " .. Name(before) .. " -> " .. Name(id)
		.. ", plot now reports " .. Name(plot:GetImprovementType()))
end

local function LandmarkFor(city)
	if g_AllCities then return g_ID[g_AllCities] end
	return nil
end

local function SyncCity(city)
	if not city then return end
	local plot = city:Plot()
	local want = LandmarkFor(city)
	if want then
		SetPlot(plot, want, "city " .. tostring(city:GetNameKey()))
	elseif g_IsOurs[plot:GetImprovementType()] then
		SetPlot(plot, -1, "city " .. tostring(city:GetNameKey()) .. " (no landmark)")
	end
end

-- Control plots next to the anchor capital (Mordor's, else the first human's): land, not a mountain, not impassable,
-- no city, and no improvement other than ours. Fixed direction order 0..5, so every client picks the same plots.
local g_ControlPlots = nil
local function ControlCity()
	for playerID = 0, GameDefines.MAX_MAJOR_CIVS - 1 do
		local p = Players[playerID]
		if p and p:IsAlive() and g_CivID and p:GetCivilizationType() == g_CivID and p:GetCapitalCity() then
			return p:GetCapitalCity()
		end
	end
	for playerID = 0, GameDefines.MAX_MAJOR_CIVS - 1 do
		local p = Players[playerID]
		if p and p:IsAlive() and p:IsHuman() and p:GetCapitalCity() then return p:GetCapitalCity() end
	end
end

local function SyncControls()
	local city = ControlCity()
	if not city then return end
	if not g_ControlPlots then
		g_ControlPlots = {}
		local n = 1
		for dir = 0, 5 do
			local plot = Map.PlotDirection(city:GetX(), city:GetY(), dir)
			if n <= #g_Controls and plot and not plot:IsWater() and not plot:IsMountain() and not plot:IsImpassable()
				and not plot:IsCity() and (plot:GetImprovementType() < 0 or g_IsOurs[plot:GetImprovementType()]) then
				g_ControlPlots[n] = plot
				print("MEC_LMI: control " .. g_Controls[n][1] .. " = " .. g_Controls[n][2] .. " at ("
					.. plot:GetX() .. "," .. plot:GetY() .. "), next to " .. tostring(city:GetNameKey()))
				n = n + 1
			end
		end
	end
	for i, plot in ipairs(g_ControlPlots) do
		local id = g_ID[g_Controls[i][2]]
		if id and not plot:IsCity() then SetPlot(plot, id, "control " .. g_Controls[i][1]) end
	end
end

local function SyncAll()
	for playerID = 0, GameDefines.MAX_PLAYERS - 1 do
		local player = Players[playerID]
		if player and player:IsAlive() then
			for city in player:Cities() do SyncCity(city) end
		end
	end
	SyncControls()
end

local function SyncAt(x, y)
	local plot = Map.GetPlot(x, y)
	if plot then SyncCity(plot:GetPlotCity()) end
	SyncControls()
end

GameEvents.PlayerCityFounded.Add(function(playerID, x, y) SyncAt(x, y) end)
GameEvents.CityCaptureComplete.Add(function(oldOwner, isCapital, x, y, newOwner) SyncAt(x, y) end)
GameEvents.SetPopulation.Add(function(x, y, oldPop, newPop) SyncAt(x, y) end)
GameEvents.PlayerDoTurn.Add(function(playerID) SyncAll() end)
SyncAll()     -- loaded games, and cities that exist before this script runs
print("MEC_LMI: active" .. (g_AllCities and (", TEST: every city gets " .. g_AllCities) or "")
	.. ", controls " .. #g_Controls .. ", anchor " .. tostring(g_AnchorCiv) .. (g_CivID and "" or " (not in the database)"))

-- g_RevealMap: render test without fog of war; every plot revealed and kept visible for every human team
-- (the same on every client, so it also works in multiplayer).
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
	print("MEC_LMI: TEST: fog of war removed for " .. n .. " human team(s), " .. Map.GetNumPlots() .. " plots")
end

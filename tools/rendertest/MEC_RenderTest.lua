-- MEC_RenderTest: automated landmark render check (test builds only: build_dlc.py --rendertest).
-- Founds the active player's capital with the settler's real Found mission and a SECOND city of the same
-- player 4-7 tiles away, reveals the map, then for each landmark variant puts it on one city (the capital
-- gets BUILDING_MEC_LM_BARAD_DUR<suffix>, the second city BUILDING_MEC_LM_MOUNT_DOOM<suffix>: the same art),
-- points the camera at it and prints "RT_SHOT <n> <tag> ..." to Lua.log; tools/rendertest/rendertest.py
-- captures the window then. (The earlier version, capital + other players' cities, is in git history.)
include("FLuaVector")
print("RT_LOADED")

-- never index GameInfo.Buildings directly (it returned wrong rows in game, 2026-11-23)
local g_BuildingID = {}
for row in GameInfo.Buildings() do g_BuildingID[row.Type] = row.ID end

local shots, state, t, i = {}, "init", 0, 0
local WAIT_START, WAIT_MOVE, WAIT_SHOT = 10.0, 3.0, 1.0

local VARIANTS = { {"", "full"}, {"_T1", "t1"}, {"_S90", "t1_90"}, {"_S75", "t1_75"}, {"_S50", "t1_50"},
	{"_S25", "t1_25"}, {"_STOCK", "stock"}, {"_BIG", "colossus"}, {"_LOOSE", "loose"}, {"NONE", "none"} }

local function cityInfo(c)
	local pl = c:Plot()
	local lm = {}
	for b in GameInfo.Buildings() do
		if string.find(b.Type, "MEC_LM_") and c:GetNumRealBuilding(b.ID) > 0 then
			table.insert(lm, b.Type .. "@" .. tostring(b.DisplayPosition))
		end
	end
	return string.format("name=%s cap=%s xy=%d,%d hills=%s lm=%s", tostring(c:GetName()), tostring(c:IsCapital()),
		c:GetX(), c:GetY(), tostring(pl:IsHills()), table.concat(lm, "+"))
end

local function addShot(tag, x, y, action)
	table.insert(shots, {tag = tag, x = x, y = y, action = action})
end

-- like the "Cycle landmark" button: remove every landmark, rebuild the city art (art events), add the variant
local function setLandmark(city, base, suffix)
	local wantID = (suffix ~= "NONE") and g_BuildingID[base .. suffix] or nil
	if suffix ~= "NONE" and not wantID then print("RT_ERROR missing building " .. base .. suffix) end
	for b in GameInfo.Buildings() do
		if string.find(b.Type, "MEC_LM_") and city:GetNumRealBuilding(b.ID) > 0 then city:SetNumRealBuilding(b.ID, 0) end
	end
	local owner = Players[city:GetOwner()]
	local h = ToHexFromGrid(Vector2(city:GetX(), city:GetY()))
	local hex = Vector3(h.x, h.y, 0)
	local pop = city:GetPopulation()
	local civ = GameInfo.Civilizations[owner:GetCivilizationType()]
	Events.SerialEventCityDestroyed(hex, owner:GetID(), city:GetID(), -1)
	Events.SerialEventCityCreated(hex, owner:GetID(), city:GetID(), (civ and GameInfoTypes[civ.ArtStyleType]) or 0,
		owner:GetCurrentEra(), city:Plot():GetContinentArtType(), pop, Game.GetVariableCitySizeFromPopulation(pop), 2)
	if wantID then city:SetNumRealBuilding(wantID, 1) end
end

-- LOAD TEST: every major civ and every city-state founds its capital at its start, and every one of them
-- gets the full Barad-dur landmark at founding (no redraw events, no swaps). One shot per city.
local LM = "BUILDING_MEC_LM_BARAD_DUR"

local function Setup()
	Events.LoadScreenClose()
	UI.SetDontShowPopups(true)
	local active = Game.GetActivePlayer()
	local me = Players[active]
	local team = me:GetTeam()
	local lm = g_BuildingID[LM]
	if not lm then print("RT_ERROR missing " .. LM); return end
	for u in me:Units() do
		if u:IsFound() then u:PushMission(MissionTypes.MISSION_FOUND); break end
	end
	for p = 0, GameDefines.MAX_CIV_PLAYERS - 1 do
		local pl = Players[p]
		if pl and pl:IsAlive() then
			if pl:GetNumCities() == 0 then
				local sp = pl:GetStartingPlot()
				if sp and not sp:IsCity() then
					for u in pl:Units() do if u:IsFound() then u:Kill(false, -1) end end
					pl:InitCity(sp:GetX(), sp:GetY())
				end
			end
			for c in pl:Cities() do
				if c:GetNumRealBuilding(lm) == 0 then c:SetNumRealBuilding(lm, 1) end
				print("RT_CITY p" .. p .. (pl:IsMinorCiv() and " cs " or " major ") .. cityInfo(c))
				addShot(string.format("p%02d_%s", p, pl:IsMinorCiv() and "cs" or "major"), c:GetX(), c:GetY())
			end
		end
	end
	for k = 0, Map.GetNumPlots() - 1 do Map.GetPlotByIndex(k):SetRevealed(team, true) end
	print("RT_SETUP shots=" .. #shots .. " active=" .. active)
end

local OnInit
Events.LocalMachineAppUpdate.Add(function(tick, dt)
	t = t + (dt or 0)
	if state == "init" then
		if t > 40 then print("RT_FALLBACK init"); OnInit() end
		return
	elseif state == "start" then
		if t >= WAIT_START then state, t, i = "move", 0, 0 end
	elseif state == "move" then
		i = i + 1
		local s = shots[i]
		if not s then print("RT_DONE"); state = "done"; return end
		if s.action then
			local ok, err = pcall(s.action)
			if not ok then print("RT_ERROR action " .. tostring(err)) end
		end
		UI.LookAt(Map.GetPlot(s.x, s.y), 0)
		state, t = "settle", 0
	elseif state == "settle" then
		if t >= WAIT_MOVE then
			local s = shots[i]
			local c = Map.GetPlot(s.x, s.y):GetPlotCity()
			print(string.format("RT_SHOT %d %s %s", i, s.tag, c and cityInfo(c) or "nocity"))
			state, t = "shot", 0
		end
	elseif state == "shot" then
		if t >= WAIT_SHOT then state = "move" end
	end
end)

OnInit = function()
	if state ~= "init" then return end
	local ok, err = pcall(Setup)
	if not ok then print("RT_ERROR setup " .. tostring(err)) end
	state, t = "start", 0
end
Events.SequenceGameInitComplete.Add(OnInit)

-- METSL_InGame
-- Middle-earth True Start Location, in-game part (multiplayer compatible rewrite).
-- Original: Gedemon / FramedArchitecture, edited by Yenyang.
--
-- Runs on every client. Everything here is deterministic and depends only on synchronised game
-- state (players, map options, Game.Rand), so all clients apply exactly the same changes.
--------------------------------------------------------------
include("METSL_MapDefs")

local g_Def = METSL_GetCurrentMapDef()
if not g_Def then
	print("METSL_InGame: not a METSL map, nothing to do")
	return
end

local g_Opt = METSL_ReadOptions(g_Def, PreGame.GetMapOption)
print("METSL_InGame: map " .. g_Def.Key .. ", CS placement " .. g_Opt.MinorPlacement .. ", DCN " .. tostring(g_Opt.DynamicCityNaming) .. ", extra settler " .. tostring(g_Opt.ExtraSettler))

--------------------------------------------------------------
-- "Only TSL" city-states: remove the ones without a True Start Location on turn 0
--------------------------------------------------------------
local function RemoveCityStatesWithoutTSL()
	if g_Opt.MinorPlacement ~= METSL_MINOR_TSL_ONLY then return end
	if Game.GetElapsedGameTurns() > 0 then return end
	for playerID = GameDefines.MAX_MAJOR_CIVS, GameDefines.MAX_CIV_PLAYERS - 1 do
		local player = Players[playerID]
		if player and player:IsAlive() and player:IsMinorCiv() and player:GetNumCities() == 0 then
			local minor = GameInfo.MinorCivilizations[player:GetMinorCivType()]
			if minor and not METSL_MinorHasTSL(g_Def, minor.Type) then
				local units = {}
				for unit in player:Units() do
					table.insert(units, unit)
				end
				for _, unit in ipairs(units) do
					unit:Kill(false, -1)
				end
				print("METSL_InGame: removed city-state without TSL: " .. minor.Type .. " (" .. #units .. " units)")
			end
		end
	end
end
local ok, err = pcall(RemoveCityStatesWithoutTSL)
if not ok then print("METSL_InGame: ERROR in RemoveCityStatesWithoutTSL: " .. tostring(err)) end

--------------------------------------------------------------
-- "Extra Starting Settler": give every major civ a second settler on turn 0, on the same tile
-- as its free one (same unit type, so unique settlers stay unique). A civ that already has a
-- city or more than one settler is skipped, so reloading a turn-0 save doesn't add another.
--------------------------------------------------------------
local function GiveExtraSettlers()
	if not g_Opt.ExtraSettler then return end
	-- (the UnitAITypes enum doesn't exist in this UI context; -1 = the unit's default AI)
	local aiRow = GameInfo.UnitAIInfos and GameInfo.UnitAIInfos.UNITAI_SETTLE
	local SETTLE_AI = aiRow and aiRow.ID or -1
	if Game.GetElapsedGameTurns() > 0 then return end
	for playerID = 0, GameDefines.MAX_MAJOR_CIVS - 1 do
		local player = Players[playerID]
		if player and player:IsAlive() and not player:IsMinorCiv() and not player:IsBarbarian()
				and player:GetNumCities() == 0 then
			local settlers = {}
			for unit in player:Units() do
				if unit:IsFound() then table.insert(settlers, unit) end
			end
			if #settlers == 1 then
				local s = settlers[1]
				player:InitUnit(s:GetUnitType(), s:GetX(), s:GetY(), SETTLE_AI)
				print("METSL_InGame: extra settler for player " .. playerID .. " at " .. s:GetX() .. "," .. s:GetY())
			end
		end
	end
end
local ok, err = pcall(GiveExtraSettlers)
if not ok then print("METSL_InGame: ERROR in GiveExtraSettlers: " .. tostring(err)) end

--------------------------------------------------------------
-- Dynamic City Naming (FramedArchitecture, edited by Yenyang)
--------------------------------------------------------------
local function CityNameInUse(nameKey, exceptCity)
	local name = Locale.ConvertTextKey(nameKey)
	for playerID = 0, GameDefines.MAX_CIV_PLAYERS - 1 do
		local player = Players[playerID]
		if player and player:IsAlive() then
			for city in player:Cities() do
				local isSelf = exceptCity and city:GetOwner() == exceptCity:GetOwner() and city:GetID() == exceptCity:GetID()
				if not isSelf and city:GetName() == name then
					return true
				end
			end
		end
	end
	return false
end

local function GetDynamicCityTxtKey(playerID, x, y, city)
	local player = Players[playerID]
	if not player or player:IsMinorCiv() or player:IsBarbarian() then return nil end
	local civ = GameInfo.Civilizations[player:GetCivilizationType()]
	if not civ then return nil end
	if civ.UseScenarioNames == false or civ.UseScenarioNames == 0 then return nil end
	if g_Opt.DCNDwarvesAndGoblins and (civ.Type == "CIVILIZATION_MEC_DWARVES" or civ.Type == "CIVILIZATION_MEC_GOBLINS") then
		return nil
	end
	local tbl = GameInfo[METSL_DCNTable(g_Def)]
	if not tbl then return nil end

	local candidates = {}
	for row in tbl() do
		if (not g_Opt.DCNSpecificCivilization) or row.CivilizationType == civ.Type then
			local dist = Map.PlotDistance(x, y, row.CityX, row.CityY)
			if dist <= row.CityRadius and not CityNameInUse(row.CityName, city) then
				table.insert(candidates, { dist = dist, name = row.CityName, civ = row.CivilizationType })
			end
		end
	end
	if #candidates == 0 then return nil end

	-- prefer names that belong to this civilization
	local own = {}
	for _, c in ipairs(candidates) do
		if c.civ == civ.Type then table.insert(own, c) end
	end
	if #own > 0 then candidates = own end

	-- closest names first (deterministic order), random pick among the closest
	table.sort(candidates, function(a, b)
		if a.dist == b.dist then return a.name < b.name end
		return a.dist < b.dist
	end)
	local closest = {}
	for _, c in ipairs(candidates) do
		if c.dist == candidates[1].dist then table.insert(closest, c) end
	end
	local pick = 1
	if #closest > 1 then
		pick = Game.Rand(#closest, "METSL dynamic city name") + 1
	end
	return closest[pick].name
end

local function ApplyDynamicName(playerID, x, y)
	local plot = Map.GetPlot(x, y)
	local city = plot and plot:GetPlotCity()
	if not city then return end
	local nameKey = GetDynamicCityTxtKey(playerID, x, y, city)
	if nameKey then
		-- store the text key: each client displays it in its own language
		city:SetName(nameKey)
		print("METSL DCN: city at " .. x .. "," .. y .. " named " .. nameKey)
	end
end

if g_Opt.DynamicCityNaming then
	GameEvents.PlayerCityFounded.Add(function(playerID, x, y)
		ApplyDynamicName(playerID, x, y)
	end)
	GameEvents.CityCaptureComplete.Add(function(oldOwner, isCapital, x, y, newOwner, pop, conquest)
		ApplyDynamicName(newOwner, x, y)
	end)
	print("METSL_InGame: dynamic city naming active")
end

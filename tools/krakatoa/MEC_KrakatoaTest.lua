-- MEC_KrakatoaTest: harness for the Krakatoa experiment (build_dlc.py --krakatoa-cities --krakatoa-test).
-- Founds a city at every player's start (majors + city-states), gives them sizes 1..30, removes the fog of war for
-- the active team (whole map revealed AND visible), then points the camera at each city and prints
-- "RT_SHOT <n> <tag> ..." (tools/rendertest/rendertest.py captures the window). Leaves the game running.
print("RT_LOADED krakatoa")

local shots, state, t, i = {}, "init", 0, 0
local WAIT_START, WAIT_MOVE, WAIT_SHOT = 10.0, 3.0, 1.0
local SIZES = {1, 3, 6, 10, 15, 20, 30}

-- never index GameInfo tables directly (wrong rows in game, 2026-11-23): map by iterating
local g_FeatureType = {}
for row in GameInfo.Features() do g_FeatureType[row.ID] = row.Type end

local function cityInfo(c)
	local pl = c:Plot()
	return string.format("name=%s xy=%d,%d feature=%s pop=%d", tostring(c:GetName()), c:GetX(), c:GetY(),
		g_FeatureType[pl:GetFeatureType()] or tostring(pl:GetFeatureType()), c:GetPopulation())
end

local function Setup()
	Events.LoadScreenClose()
	UI.SetDontShowPopups(true)
	local active = Game.GetActivePlayer()
	local me = Players[active]
	local team = me:GetTeam()
	for p = 0, GameDefines.MAX_CIV_PLAYERS - 1 do
		local pl = Players[p]
		if pl and pl:IsAlive() and not pl:IsBarbarian() and pl:GetNumCities() == 0 then
			local sp = pl:GetStartingPlot()
			if sp and not sp:IsCity() then
				for u in pl:Units() do if u:IsFound() then u:Kill(false, -1) end end
				pl:InitCity(sp:GetX(), sp:GetY())
			end
		end
	end
	-- different city sizes: the model must be Krakatoa at every size
	local k = 0
	for p = 0, GameDefines.MAX_CIV_PLAYERS - 1 do
		local pl = Players[p]
		if pl and pl:IsAlive() then
			for c in pl:Cities() do
				k = k + 1
				c:SetPopulation(SIZES[(k - 1) % #SIZES + 1], true)
			end
		end
	end
	-- no fog of war: every plot revealed and currently visible for the active team
	for k = 0, Map.GetNumPlots() - 1 do
		local plot = Map.GetPlotByIndex(k)
		plot:SetRevealed(team, true)
		plot:ChangeVisibilityCount(team, 1, -1, true, true)
	end
	for p = 0, GameDefines.MAX_CIV_PLAYERS - 1 do
		local pl = Players[p]
		if pl and pl:IsAlive() then
			for c in pl:Cities() do
				print("RT_CITY p" .. p .. (pl:IsMinorCiv() and " cs " or " major ") .. cityInfo(c))
				table.insert(shots, {tag = string.format("p%02d_%s", p, pl:IsMinorCiv() and "cs" or "major"),
					x = c:GetX(), y = c:GetY()})
			end
		end
	end
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
		if not s then
			if shots[1] then UI.LookAt(Map.GetPlot(shots[1].x, shots[1].y), 0) end
			print("RT_DONE"); state = "done"; return
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

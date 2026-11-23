-- MEC_RedrawCities
-- DEBUG tool for the "empty city tile" bug (docs/CITY_MODELS.md §8): a button that forces the renderer
-- to rebuild every city's 3D art.
--
-- The game has no "redraw" API, but the renderer listens to the same Events.SerialEventCity* messages
-- that the game core sends, and Lua may fire them too (stock UI/InGame/DebugMode.lua does exactly this).
--
--   Left click  (hard): SerialEventCityDestroyed + SerialEventCityCreated for each city -> the engine
--                       throws the city's model group away and builds a new one (houses). The created
--                       event carries no buildings, so in single player each landmark building is then
--                       removed and re-added (SetNumRealBuilding 0 -> 1) to send its art to the new group.
--                       In multiplayer that step is skipped (game state, would desync).
--                       Side effect: other building art (stock wonders) may stay missing until a reload.
--   Right click (soft): re-send population / culture / continent for each city to its existing group.
--
-- Art events are local to this client: nothing here (except the single-player landmark re-add) touches
-- game state.
--------------------------------------------------------------

include("FLuaVector")    -- Vector2 / Vector3 (not global in a UI context)

local TAG = "MEC_Redraw: "
local BLACK_FOG, WHITE_FOG = 0, 2

-- Building lookups by iterating the rows: GameInfo.Buildings["TYPE"] returned the WRONG row in game for some of
-- our buildings (2026-11-23: "..._P32" gave "..._LOOSE"), so never index GameInfo.Buildings directly.
local g_BuildingID, g_BuildingType = {}, {}
for row in GameInfo.Buildings() do
	g_BuildingID[row.Type] = row.ID
	g_BuildingType[row.ID] = row.Type
end

local g_LandmarkIDs = {}
for row in GameInfo.Buildings() do
	if string.find(row.Type, "^BUILDING_MEC_LM_") then table.insert(g_LandmarkIDs, row.ID) end
end

local function IsMultiplayer()
	return (Game.IsNetworkMultiPlayer and Game.IsNetworkMultiPlayer())
		or (PreGame.IsMultiplayerGame and PreGame.IsMultiplayerGame()) or false
end

local function ArtStyleOf(player)
	local t
	if player:IsMinorCiv() then
		local m = GameInfo.MinorCivilizations[player:GetMinorCivType()]
		t = m and m.ArtStyleType
	else
		local c = GameInfo.Civilizations[player:GetCivilizationType()]
		t = c and c.ArtStyleType
	end
	return (t and GameInfoTypes[t]) or 0
end

-- every city whose tile the active team has seen, with what the art events need
local function KnownCities()
	local team = Game.GetActiveTeam()
	local debug = Game.IsDebugMode and Game.IsDebugMode()
	local out = {}
	for playerID = 0, GameDefines.MAX_PLAYERS - 1 do
		local player = Players[playerID]
		if player and player:IsAlive() then
			for city in player:Cities() do
				local plot = city:Plot()
				local fow = BLACK_FOG
				if debug or plot:IsVisible(team, false) then fow = WHITE_FOG
				elseif plot:IsRevealed(team, false) then fow = 1 end
				if fow ~= BLACK_FOG then
					local h = ToHexFromGrid(Vector2(city:GetX(), city:GetY()))
					local hex = Vector3(h.x, h.y, 0)
					table.insert(out, { player = player, city = city, plot = plot, hex = hex, fow = fow })
				end
			end
		end
	end
	return out
end

local function Describe(c)
	return tostring(c.city:GetNameKey()) .. " (" .. c.city:GetX() .. "," .. c.city:GetY() .. ")"
end

-- fire one art event; a failure is logged and does not stop the other events/cities
local g_Fails = 0
local function Fire(name, ...)
	local ev = Events[name]
	if not ev then g_Fails = g_Fails + 1; print(TAG .. "  Events." .. name .. " does not exist"); return end
	local ok, err = pcall(ev, ...)
	if not ok then g_Fails = g_Fails + 1; print(TAG .. "  Events." .. name .. " FAILED: " .. tostring(err)) end
end

local function SoftRefresh()
	local cities = KnownCities()
	for _, c in ipairs(cities) do
		local pop = c.city:GetPopulation()
		Fire("SerialEventCityCultureChanged", c.hex.x, c.hex.y, ArtStyleOf(c.player))
		Fire("SerialEventCityContinentChanged", c.hex.x, c.hex.y, c.plot:GetContinentArtType())
		Fire("SerialEventCityPopulationChanged", c.hex.x, c.hex.y, pop, Game.GetVariableCitySizeFromPopulation(pop))
		print(TAG .. "soft " .. Describe(c))
	end
	print(TAG .. "soft refresh done, " .. #cities .. " cities")
end

local function HardRedrawCity(c, readd)
		local player, city = c.player, c.city
		local playerID, cityID = player:GetID(), city:GetID()
		local pop = city:GetPopulation()
		Fire("SerialEventCityDestroyed", c.hex, playerID, cityID, -1)
		Fire("SerialEventCityCreated", c.hex, playerID, cityID, ArtStyleOf(player), player:GetCurrentEra(),
			c.plot:GetContinentArtType(), pop, Game.GetVariableCitySizeFromPopulation(pop), c.fow)
		local lm = ""
		for _, id in ipairs(g_LandmarkIDs) do
			if city:GetNumRealBuilding(id) > 0 then
				if readd then
					city:SetNumRealBuilding(id, 0)
					city:SetNumRealBuilding(id, 1)
					lm = lm .. " re-added " .. g_BuildingType[id]
				else
					lm = lm .. " has " .. g_BuildingType[id] .. " (not re-added: multiplayer)"
				end
			end
		end
		print(TAG .. "hard " .. Describe(c) .. " fow=" .. c.fow .. lm)
end

local function HardRedraw()
	local readd = not IsMultiplayer()
	local cities = KnownCities()
	for _, c in ipairs(cities) do HardRedrawCity(c, readd) end
	print(TAG .. "hard redraw done, " .. #cities .. " cities")
end

--------------------------------------------------------------
-- Cycle landmark (single player only: swaps buildings = game state).
-- For every city of the active player that has (or had) a landmark, steps through
--   full -> T1 static -> T1 at 90% / 75% / 50% / 25% size
--   -> T2 +animated -> T3 +fire -> STOCK (small stock mesh, .fpk)
--   -> BIG (Colossus: big stock mesh, .fpk) -> LOOSE (the small stock mesh as a loose file) -> none -> full
-- and hard-redraws it, so one bad launch can show which layer fails.
-- MEC_Landmarks puts the proper landmark back at the start of the next turn.
local VARIANTS = { "", "_T1", "_S90", "_S75", "_S50", "_S25", "_T2", "_T3", "_STOCK", "_BIG", "_LOOSE", "NONE" }
local VARIANT_NAMES = { [""] = "full", _T1 = "T1", _S90 = "T1 90%", _S75 = "T1 75%",
	_S50 = "T1 50%", _S25 = "T1 25%", _T2 = "T2 Eye", _T3 = "T3 fire", _STOCK = "stock small",
	_BIG = "stock Colossus", _LOOSE = "stock loose", NONE = "none" }
local g_Base = {}      -- plot index -> landmark base type ("BUILDING_MEC_LM_BARAD_DUR")
local g_Step = {}      -- plot index -> index into VARIANTS

local function BaseOf(t)
	for _, v in ipairs(VARIANTS) do
		if v ~= "" and v ~= "NONE" and string.sub(t, -#v) == v then return string.sub(t, 1, -#v - 1), v end
	end
	return t, ""
end

-- which = "capital" (left click) or "others" (right click): cycle one city independently of the other
local g_Labels = {}
local function Cycle(which)
	if IsMultiplayer() then print(TAG .. "cycle: not available in multiplayer (would desync)"); return end
	local me = Game.GetActivePlayer()
	local label, n = nil, 0
	for _, c in ipairs(KnownCities()) do
		if c.player:GetID() == me and (c.city:IsCapital() == (which == "capital")) then
			local city, idx = c.city, c.plot:GetPlotIndex()
			local cur
			for _, id in ipairs(g_LandmarkIDs) do
				if city:GetNumRealBuilding(id) > 0 then
					local base, v = BaseOf(g_BuildingType[id])
					g_Base[idx] = base
					for i, vv in ipairs(VARIANTS) do if vv == v then cur = i end end
				end
			end
			if not cur and g_Base[idx] then cur = g_Step[idx] or #VARIANTS end     -- currently "none"
			if cur and g_Base[idx] then
				local nxt = cur % #VARIANTS + 1
				local want = VARIANTS[nxt]
				local wantID = -1
				if want ~= "NONE" then
					local id = g_BuildingID[g_Base[idx] .. want]
					if id then wantID = id else print(TAG .. "cycle: " .. g_Base[idx] .. want .. " missing") end
				end
				for _, id in ipairs(g_LandmarkIDs) do
					if city:GetNumRealBuilding(id) > 0 then city:SetNumRealBuilding(id, 0) end
				end
				g_Step[idx] = nxt
				HardRedrawCity(c, false)          -- new city art first (houses) ...
				if wantID >= 0 then               -- ... then the variant, so its art goes to the new group
					city:SetNumRealBuilding(wantID, 1)
				end
				print(TAG .. "cycle " .. Describe(c) .. " -> " .. VARIANT_NAMES[want])
				label = VARIANT_NAMES[want]
				n = n + 1
			end
		end
	end
	if n == 0 then print(TAG .. "cycle: none of your cities has a landmark") end
	if label then g_Labels[which] = label end
	Controls.CycleLabel:SetText("Cap: " .. (g_Labels.capital or "-") .. " | Other: " .. (g_Labels.others or "-"))
end

local function Run(fn, name)
	g_Fails = 0
	local ok, err = pcall(fn)
	if not ok then print(TAG .. name .. " FAILED: " .. tostring(err))
	elseif g_Fails > 0 then print(TAG .. name .. ": " .. g_Fails .. " event call(s) failed (see above)") end
end

Controls.RedrawButton:RegisterCallback(Mouse.eLClick, function() Run(HardRedraw, "hard redraw") end)
Controls.RedrawButton:RegisterCallback(Mouse.eRClick, function() Run(SoftRefresh, "soft refresh") end)
Controls.CycleButton:RegisterCallback(Mouse.eLClick, function() Run(function() Cycle("capital") end, "cycle capital") end)
Controls.CycleButton:RegisterCallback(Mouse.eRClick, function() Run(function() Cycle("others") end, "cycle others") end)

--------------------------------------------------------------
-- Reveal area (single player only: changes visibility = game state). Fog-of-war test: reveals and makes
-- visible every plot within REVEAL_RADIUS of each of your cities, then rebuilds those cities' art.
-- If a landmark that was empty now draws, the model was hidden because its bounds reached fogged plots.
local REVEAL_RADIUS = 3
local function RevealArea()
	if IsMultiplayer() then print(TAG .. "reveal: not available in multiplayer (would desync)"); return end
	local me, team = Game.GetActivePlayer(), Game.GetActiveTeam()
	local mine = {}
	for _, c in ipairs(KnownCities()) do
		if c.player:GetID() == me then table.insert(mine, c) end
	end
	local revealed, lit = 0, 0
	for i = 0, Map.GetNumPlots() - 1 do
		local plot = Map.GetPlotByIndex(i)
		for _, c in ipairs(mine) do
			if Map.PlotDistance(plot:GetX(), plot:GetY(), c.city:GetX(), c.city:GetY()) <= REVEAL_RADIUS then
				if not plot:IsRevealed(team, false) then
					plot:SetRevealed(team, true)
					revealed = revealed + 1
				end
				if not plot:IsVisible(team, false) then
					plot:ChangeVisibilityCount(team, 1, -1, true, true)
					lit = lit + 1
				end
				break
			end
		end
	end
	for _, c in ipairs(mine) do HardRedrawCity(c, true) end
	print(TAG .. "reveal: radius " .. REVEAL_RADIUS .. " around " .. #mine .. " cities: " .. revealed
		.. " plots newly revealed, " .. lit .. " plots made visible")
	Controls.RevealLabel:SetText("Revealed (" .. revealed .. "/" .. lit .. ")")
end
Controls.RevealButton:RegisterCallback(Mouse.eLClick, function() Run(RevealArea, "reveal") end)

Controls.RedrawButton:SetToolTipString("[COLOR_POSITIVE_TEXT]Debug: redraw cities[ENDCOLOR][NEWLINE]"
	.. "Left click: destroy and re-create every city's 3D art (houses)"
	.. (IsMultiplayer()
		and ".[NEWLINE][COLOR_NEGATIVE_TEXT]Multiplayer game: landmarks are NOT re-added (that changes game state and would desync).[ENDCOLOR]"
		or ", then remove and re-add each landmark building so its art is sent again.")
	.. "[NEWLINE]Right click: soft refresh (re-send population / culture / continent).[NEWLINE]Log: Logs/Lua.log, prefix MEC_Redraw.")

if IsMultiplayer() then
	Controls.RevealButton:SetDisabled(true)
	Controls.RevealButton:SetToolTipString("[COLOR_NEGATIVE_TEXT]Reveal area: single player only[ENDCOLOR] (changes visibility, which would desync a multiplayer game).")
	Controls.CycleButton:SetDisabled(true)
	Controls.CycleButton:SetToolTipString("[COLOR_NEGATIVE_TEXT]Cycle landmark: single player only[ENDCOLOR] (it swaps buildings, which would desync a multiplayer game).")
else
	Controls.RevealButton:SetToolTipString("[COLOR_POSITIVE_TEXT]Debug: reveal area[ENDCOLOR][NEWLINE]Reveals and lights up every tile within "
		.. REVEAL_RADIUS .. " tiles of each of your cities, then rebuilds their art (fog-of-war test).[NEWLINE]Log prefix MEC_Redraw.")
	Controls.CycleButton:SetToolTipString("[COLOR_POSITIVE_TEXT]Debug: cycle landmark variant[ENDCOLOR][NEWLINE]"
		.. "LEFT click: your CAPITAL only.  RIGHT click: your OTHER cities only.[NEWLINE]"
		.. "full -> T1 static -> T1 90% -> 75% -> 50% -> 25%"
		.. " -> T2 +animated Eye -> T3 +fire"
		.. " -> stock small -> stock Colossus"
		.. " -> stock small loose file -> none (houses only) -> full[NEWLINE]"
		.. "Each click swaps the building and rebuilds the city art. The proper landmark comes back next turn.[NEWLINE]Log prefix MEC_Redraw.")
end

print(TAG .. "button ready (" .. (IsMultiplayer() and "multiplayer" or "single player") .. "), " .. #g_LandmarkIDs .. " landmark building(s) known")

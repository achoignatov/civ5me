-- Wood_Elves_Units_Promotions
-- Author: TJ
-- Original Author and Special Thanks be to LastSword in Kyrat Mod
-- DateCreated: 1/16/2016 8:49:01 AM
-- Multiplayer pack fixes: undefined range variable (r -> radius), nil unit guard, removed per-move logging.
-- Runs from GameEvents on every client with synchronised state, so it is multiplayer safe.
--------------------------------------------------------------
local PROMO_ON = GameInfoTypes.PROMOTION_MEC_WOOD_ELF_INVISIBLE_ON
local PROMO_OFF = GameInfoTypes.PROMOTION_MEC_WOOD_ELF_INVISIBLE_OFF
local FOREST = GameInfoTypes.FEATURE_FOREST

local function nearUnfriendlyCity(player, radius, x, y)
	for dx = -radius, radius do
		for dy = -radius, radius do
			local currentPlot = Map.PlotXYWithRangeCheck(x, y, dx, dy, radius)
			if currentPlot then
				local city = currentPlot:GetPlotCity()
				if city and currentPlot:GetOwner() ~= player then
					return true
				end
			end
		end
	end
	return false
end

local function SetVisible(unit, invisible)
	unit:SetHasPromotion(PROMO_ON, invisible)
	unit:SetHasPromotion(PROMO_OFF, not invisible)
end

function UpdateWoodElfVisibility(player, unitID, x, y)
	if PROMO_ON == nil or PROMO_OFF == nil then return end
	local pPlayer = Players[player]
	if not pPlayer then return end
	local cUnit = pPlayer:GetUnitByID(unitID)
	if not cUnit then return end
	if not (cUnit:IsHasPromotion(PROMO_OFF) or cUnit:IsHasPromotion(PROMO_ON)) then return end
	local cPlot = Map.GetPlot(x, y)
	if not cPlot then return end
	local cityVisibilityRange = 3
	if cPlot:GetFeatureType() == FOREST then
		if (cPlot:IsOwned() and not cPlot:IsFriendlyTerritory(player)) or nearUnfriendlyCity(player, cityVisibilityRange, x, y) then
			if cUnit:IsHasPromotion(PROMO_ON) then SetVisible(cUnit, false) end
		else
			if not cUnit:IsHasPromotion(PROMO_ON) then SetVisible(cUnit, true) end
		end
	else
		if cUnit:IsHasPromotion(PROMO_ON) then SetVisible(cUnit, false) end
	end
end

GameEvents.UnitSetXY.Add(UpdateWoodElfVisibility)

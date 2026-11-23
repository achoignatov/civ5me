-- Lua METSL_Functions
-- Original Author: Gedemon Edited by Yenyang
-- DateCreated: 9/12/2014 8:26:51 PM
--------------------------------------------------------------

include("METSL_Defines")

function MinorCivExist ( minorCivilizationType )
	local civExist = false
	for row in GameInfo.MinorCivilizations() do
		if row.Type == minorCivilizationType then
			civExist = true
		end
	end
	return civExist
end

function MajorCivExist ( civilizationType )
	local civExist = false
	for row in GameInfo.Civilizations() do
		if row.Type == civilizationType then
			civExist = true
		end
	end
	return civExist
end

function MinorCivHasTSL ( minorCivID )
	local minorCivilizationType = GameInfo["MinorCivilizations"][minorCivID]["Type"]
	local civHasTSL = false
	local mapID = modUserData.GetValue ("MapID")
	tableName = "MinorCiv_" .. g_MapList[mapID].TablePrefix .. "StartPosition"
	for row in GameInfo[tableName]() do
		if row.Type == minorCivilizationType then
			civHasTSL = true
		end
	end
	return civHasTSL
end

function CivHasTSL(civID)
	local mapID = modUserData.GetValue ("MapID")
	tableName = "Civilizations_" .. g_MapList[mapID].TablePrefix .. "StartPosition"
	for row in GameInfo[tableName]() do
		if MajorCivExist ( row.Type ) then
			if civID == GameInfo["Civilizations"][row.Type]["ID"] then
				return true
			end
		end
	end
	return false
end

--[[for i = 0, GameDefines.MAX_MAJOR_CIVS - 1 do
		local player = Players[i]
		local civID = player:GetCivilizationType() 
		print("-------------------------------")
		print ("Search starting position for Civ : " .. civID )
		print(CivHasTSL(civID))
end]]


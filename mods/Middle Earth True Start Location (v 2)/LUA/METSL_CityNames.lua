-- Dynamic Scenario City Names
-- Original Author: FramedArchitecture
-- Edited for METSL by Yenyang
-- DateCreated: 1/2013
--------------------------------------------------------------
include( "METSL_Defines" )

function OnDynamicCityCreated( iPlayer, iX, iY )
	print("City Founded!")
    if IsDynamicCityNamingOn() == 0 then return end

	print("Passed DCN check")
    local city = Map.GetPlot(iX, iY):GetPlotCity()
    local nameKey = GetDynamicCityTxtKey(iPlayer, iX, iY)

    if nameKey then
	   print("Set city name to " .. nameKey)
       city:SetName(Locale.ConvertTextKey(nameKey))
    else
		print("Not setting city name")
	end
		
end
GameEvents.PlayerCityFounded.Add( OnDynamicCityCreated )
--------------------------------------------------------------
function OnDynamicCityCaptured (iOldOwner, bIsCapital, iX, iY, iNewOwner, iPop, bConquest)
	print("City Captured!")
    if not IsDynamicCityNamingOn() == 0 then return end

	print("Passed DNC check")
    local city = Map.GetPlot(iX, iY):GetPlotCity()
    local nameKey = GetDynamicCityTxtKey(iNewOwner, iX, iY)

    if nameKey then
		print("Set city name to " .. nameKey)
        city:SetName(Locale.ConvertTextKey(nameKey))
    else
		print("Not setting city name")
	end
end
GameEvents.CityCaptureComplete.Add( OnDynamicCityCaptured )
--------------------------------------------------------------
function GetDynamicCityTxtKey(iPlayer, iX, iY)
    local cityNameKey = nil
    local CityNames = {}
	local mapID = modUserData.GetValue ("MapID")
	local tableName =  g_MapList[mapID].TablePrefix .. "_DynamicCityNames"
	print (mapID)
	print (g_MapList[mapID].TablePrefix)
	local bUseNames = GameInfo.Civilizations[Players[iPlayer]:GetCivilizationType()].UseScenarioNames
	print ("Getting City Name")
	local player = Players[iPlayer]
	local playerCivID = player:GetCivilizationType()
	local cityBelongsToCivilization = false
	if modUserData.GetValue("DCNDwarvesAndGoblins") == 1 and (CivilizationIDtoType(playerCivID) == "CIVILIZATION_MEC_DWARVES" or CivilizationIDtoType(playerCivID) == "CIVILIZATION_MEC_GOBLINS") then
		print("No DCN for " .. CivilizationIDtoType(playerCivID))
		bUseNames = false
	end
    if bUseNames then
		print ("Using Names is true")
		print(modUserData.GetValue("DCNSpecificCivilization"))
		if modUserData.GetValue("DCNSpecificCivilization") == 0 then
			for row in GameInfo[tableName]() do
				local plotDistance = Map.PlotDistance(iX, iY, row.CityX, row.CityY)
				--print(plotDistance)
				--print(row.CivilizationType)
				--print(row.CityName)
				--print(row.CityRadius)
				if ( plotDistance <= row.CityRadius ) then
					local cNameKey = row.CityName
					print(row.CityName .. " is in range")
					if IsValidCityName(cNameKey) then
						table.insert(CityNames, {dist = plotDistance, name = cNameKey, civ = row.CivilizationType})
					end
				end
			end
		else
			--print(player:GetCivilizationType())
			if playerCivID then
				local civType = CivilizationIDtoType(playerCivID)
				print("CivilizationType='" .. civType .. "'")
				for row in GameInfo[tableName]("CivilizationType='" .. civType .. "'") do
					local plotDistance = Map.PlotDistance(iX, iY, row.CityX, row.CityY)
					--print(plotDistance)
					--print(row.CivilizationType)
					--print(row.CityName)
					--print(row.CityRadius)
					if ( plotDistance <= row.CityRadius ) then
						local cNameKey = row.CityName
						print(row.CityName .. " is in range")
						if IsValidCityName(cNameKey) then
							table.insert(CityNames, {dist = plotDistance, name = cNameKey, civ = row.CivilizationType})
						end
					end
				end
			else
				print("Civtype failed")
			end
		end
	else
		print("Using Names failed")
	end

	print (#CityNames .. " available city names")
	if (#CityNames == 1) then
		print ("Only one city name use" .. CityNames[1].name)
        cityNameKey = CityNames[1].name
    elseif (#CityNames > 1) then
		
		local civType = CivilizationIDtoType(playerCivID)
		print("Checking if any of the " .. #CityNames .. " cities belong to " .. civType .. " civilization...")
		 for _,cn in ipairs(CityNames) do
			if cn.civ then
				print(cn.civ)
			else
				print("No cn.civ")
			end
			if civType then
				print(civType)
			else 
				print("No civ type")
			end
			if cn.civ == civType then
				cityBelongsToCivilization = true
				break
			end
		end
		if cityBelongsToCivilization then 
			 for row,cn in ipairs(CityNames) do
				if cn.civ ~= civType then
					table.remove(CityNames, row)
				end
			end
			print (#CityNames .. " cities belong to " .. civType  .. " civilization...")
		else
			print ("No cities belong to " .. civType  .. " civilization...")
		end
		
		print ("Multiple city names. sorting ...")
        table.sort(CityNames, function(x,y) if (x.dist == y.dist) then return (x.name < y.name) else return (x.dist < y.dist) end end)
 
        local possibleCities = 0
        local minDist = CityNames[1].dist
		print ("Min Distance = " .. minDist)
        for _,cn in ipairs(CityNames) do
            if cn.dist == minDist then
                possibleCities = possibleCities + 1
            else
                break
            end
        end
		print ("Possible cities = " .. possibleCities)
		--to do add in multiple civilization names
		--to do make DCN always chose civs city first
        cityNameKey = CityNames[math.random(possibleCities)].name
		if cityNameKey then
			print("Randomly decided to use " .. cityNameKey)
		else
			print("City Name is nil")
		end
    end
	if cityNameKey then
		print("Last chance to check city name is" .. cityNameKey)
	else
		print("City Name is nil")
	end
    return cityNameKey
end
--------------------------------------------------------------
function IsValidCityName(nameKey)
    local nameKey = Locale.ConvertTextKey(nameKey)
	print ("Checking Valid City Name")
    for iPlayerLoop = 0, GameDefines.MAX_MAJOR_CIVS-1, 1 do
        local player = Players[iPlayerLoop]
        if player:IsAlive() then
            for city in player:Cities() do
                if nameKey == city:GetName() and player:GetNumCities() > 1 then
					print("Invalid City Name" .. city:GetName() .. " aleady used")
                    return false
                end
            end
        end
    end
	if nameKey then
		print ("Valid City Name " .. nameKey)
	end
    return true
end
--------------------------------------------------------------
--[[
function GetCivType(x, y)
	print("Getting Civilization Type")
	local tableName =  g_MapList[mapID].TablePrefix .. "_DynamicCityNames"
	if GameInfo[tableName]() then
		for row in GameInfo[tableName]() do
			if (row.Type) then
				print (row.Type)
				return row.Type
			else
				print("No Row Type")
			end
		end
	else
		print("Dynamic City Names Table Doesn't Exist for map" .. mapID)
	end
	print("No Civilization type ??")
	return nil;
end
]]
--------------------------------------------------------------

function IsDynamicCityNamingOn()
	local mapID = modUserData.GetValue ("MapID")
	local tableName =  g_MapList[mapID].TablePrefix .. "_DynamicCityNames"
	if GameInfo[tableName] then
		return modUserData.GetValue("DynamicCityNaming")
	end
	return 0
end

function CivilizationIDtoType(civID)
	local id = 0
	local type = 0	
	print("Looking for ID " .. civID)
	for key, civ in pairs(MiddleEarthCivilizations) do
		--print(civ.ID)
		--print(civ.Type)
		if civID == civ.ID then
			print("Found type " .. civ.Type)
			return civ.Type
		end
	end
	return false
end
--------------------------------------------------------------
print("City names initialized")
-- Lua METSL_Utils
-- Original Author: Gedemon Edited by Yenyang
-- DateCreated: 9/12/2014 8:50:48 PM
--------------------------------------------------------------

function GetPlot (x,y)
	local plot = Map:GetPlotXY(y,x)
	return plot
end

function ListAllCivs()
	print ("+++++++++++++++++++")
	print ("---- civ list -----")
	for iPlayer = 0, GameDefines.MAX_PLAYERS do
		local player = Players[iPlayer]
		if player ~= nil then
			local str = "- " .. iPlayer .. " - "
			if player:IsMinorCiv() then
				local minorCivType = player:GetMinorCivType();
				local civInfo = GameInfo.MinorCivilizations[minorCivType];
				local minorName = Locale.ConvertTextKey( civInfo.Description ) 
				str = str .. "Minor civ " .. minorName .. " (" .. minorCivType ..") - "
			else
				local majorCivType = player:GetCivilizationType();
				local civInfo = GameInfo.Civilizations[majorCivType];
				if (majorCivType > 0) then
					local minorName = Locale.ConvertTextKey( civInfo.Description )
					str = str .. "Major civ " .. minorName .. " (" .. majorCivType ..") - "
				end
			end
			if player:IsAlive() then
				str = str .. " alive - "
			end
			print (str)
		end
	end
	print ("+++++++++++++++++++")
end
--ListAllCivs()
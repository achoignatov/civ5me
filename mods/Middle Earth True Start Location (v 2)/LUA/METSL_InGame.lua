-- Lua METSL_InGame
-- Original Author: Gedemon Edited by Yenyang
-- DateCreated: 9/12/2014 9:09:38 PM
--------------------------------------------------------------


include( "METSL_Defines" )
include( "METSL_Utils" )
include( "METSL_Functions" )
include( "METSL_CityNames" )

--------------------------------------------------------------

-- dont start configuration sooner than needed
local WaitBeforeInitialize = true

--[[function UpdateNaturalWonderName()
	print("-------------------------------")
	print ("MetslP is updating natural wonders name...")
	local savedData = Modding.OpenSaveData()
	local mapID = savedData.GetValue("MapID")
	if (mapID) then
		local table = g_NaturalWonderName[mapID]
		for tag, str in pairs (table) do
			print(tag .." = " .. str)
			SetText ( str, tag )
		end
	end
	Locale.SetCurrentLanguage( Locale.GetCurrentLanguage().Type )
	print("-------------------------------")
end]]

function MetslRemoveCiv (playerID)
	local player = Players[playerID]
	-- kill all units
	for v in player:Units() do
		v:Kill()
	end
end

function GetPlayerBy (key, value)
	--print ("key = " .. key)
	--print ("value = " .. value)
	-- warning, could be more than one, but will return first found
	for player_num = 0, GameDefines.MAX_CIV_PLAYERS - 1 do
		local player = Players[player_num]
		local checkValue
		if key == "civID" then checkValue = player:GetCivilizationType() end
		if key == "minorCivID" then checkValue = player:GetMinorCivType() end
		if checkValue == value then
			print ("player_num = " .. player_num)
			return player_num
		end
	end
end

function FinalizeCityState(numMinorCivs)
	-- tab for playerID
	local MetslSelection = {}
	for playerID = GameDefines.MAX_MAJOR_CIVS, GameDefines.MAX_CIV_PLAYERS - 1 do
		local player = Players[playerID]
		local minorCivID = player:GetMinorCivType()
		-- Does this civ exist ?
		if minorCivID ~= -1 then
			-- keep only TSL ?
			if (not MinorCivHasTSL(minorCivID) and PreGame.GetMapOption(MINOR_PLACEMENT) == MINOR_TSL_ONLY) then
				MetslRemoveCiv (playerID)
			-- was marked for removing ?
			elseif string.find(modUserData.GetValue("ToRemove"), "minor"..minorCivID.."tr") then
				MetslRemoveCiv (playerID)
				print ("kill marked civ : " .. minorCivID)
			else
				table.insert(MetslSelection, playerID)
			end
		end
	end

	print ("Actual Number of City States = " .. #MetslSelection )
		
	if #MetslSelection > numMinorCivs then
		print ("Ok, exterminating a few settlers discretly..." )
		-- remove excedent
		-- but first shuffle selection
		-- so we can't be accused of deliberate ethnic cleaning
		for i = #MetslSelection, 2, -1 do
			local r = math.random(i)
			MetslSelection[i], MetslSelection[r] = MetslSelection[r], MetslSelection[i]
		end
		-- keep only the requested number
		for i = numMinorCivs + 1 , #MetslSelection do
			MetslRemoveCiv (MetslSelection[i])
		end		
	end
end

function FinalizeMetsl ()
	
	print("-------------------------------")
	print("Metslp script started")
	print("-------------------------------")

	

		local reqNumMinor = modUserData.GetValue("NumMinorCivs")
		
		print("Loaded map : " .. PreGame.GetMapScript() )
		print("Finalize setup now")
		print("-------------------------------")
		print("To remove : " .. modUserData.GetValue("ToRemove"))
		print("Requested City States = ".. reqNumMinor)

		FinalizeCityState( reqNumMinor )

		print("City States placement finished")
		print("-------------------------------")
		

		local savedData = Modding.OpenSaveData()
		print ("MetslP initialization finished, saving MapID")
		savedData.SetValue("MetslPInitDone", 1)
		savedData.SetValue("MapID", modUserData.GetValue ("MapID"))

		print("-------------------------------")
	
end


-- functions to call at first turn
function OnFirstTurn ()
	FinalizeMetsl ()
	--UpdateNaturalWonderName()
end

-- functions to call when loading game
function OnLoading ()
	--UpdateNaturalWonderName()
end

-- Initialize when MetslpInGame is loaded
if ( WaitBeforeInitialize ) then
	WaitBeforeInitialize = false
	local savedData = Modding.OpenSaveData()
	local iValue = savedData.GetValue("MetslPInitDone")
	if (iValue ~= 1) then
		OnFirstTurn()
	else
		OnLoading()
	end
end
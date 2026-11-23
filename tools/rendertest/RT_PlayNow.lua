-- render test only: force exactly @@N@@ major civs (Mordor + the next ME civs) on a Huge world
function RT_SetupPlayers()
	local N = @@N@@
	PreGame.SetRandomWorldSize(false)
	PreGame.SetWorldSize(GameInfo.Worlds["WORLDSIZE_HUGE"].ID)
	local civs = {}
	for row in GameInfo.Civilizations() do
		if string.find(row.Type, "CIVILIZATION_MEC_", 1, true) == 1 and row.Playable and row.Type ~= "CIVILIZATION_MEC_MORDOR" then
			table.insert(civs, row.ID)
		end
	end
	table.sort(civs)
	PreGame.SetCivilization(0, GameInfo.Civilizations.CIVILIZATION_MEC_MORDOR.ID)
	for i = 1, GameDefines.MAX_MAJOR_CIVS - 1 do
		if i < N and civs[i] then
			PreGame.SetSlotStatus(i, SlotStatus.SS_COMPUTER)
			PreGame.SetCivilization(i, civs[i])
		else
			PreGame.SetSlotStatus(i, SlotStatus.SS_CLOSED)
		end
	end
	print("RT_PLAYNOW majors=" .. N)
end

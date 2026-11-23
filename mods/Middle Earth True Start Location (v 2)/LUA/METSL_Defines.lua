-- Lua METSL_Defines
-- Original Author: Gedemon Edited by Yenyang
-- DateCreated: 9/12/2014 8:06:08 PM
--------------------------------------------------------------
MetslModId = "9f1a1884-17be-4f9f-bbbf-37143a130eb3"
MetslModVersion = Modding.GetActivatedModVersion(MetslModId)
modUserData = Modding.OpenUserData("METSL", MetslModVersion)


--print("Hello World 6")
--print(modUserData)
--map type


TA_HUGE_RND_WW = 1
--TA_HUGE_RND_NWW = 2
--TA_LRG_RND_WW = 3 
TA_LRG_RND_NWW = 2 --4
--TA_STD_RND_WW = 5
--TA_STD_RND_NWW = 6

g_MapList = {
	[TA_HUGE_RND_WW] = { ID = TA_HUGE_RND_WW, File = "METSL_TA_HUGE_RND_WW.Civ5Map", Name = "Third Age-Huge-RR-WW", Description = "100 x 80 Middle Earth during the Third Age with Random Resources and World Wrap (inc Rhun)", Size = "WORLDSIZE_HUGE", Civs = 14, Minors = 26, TablePrefix = "TaHugeRndWw" },	
	--[TA_HUGE_RND_NWW] = { ID = TA_HUGE_RND_NWW, File = "METSL_TA_HUGE_RND_NWW.Civ5Map", Name = "Third Age-Huge-RR-NWW", Description = "75 x 80 Middle Earth during the Third Age with Random Resources without World Wrap (no Rhun)", Size = "WORLDSIZE_HUGE", Civs = 14, Minors = 26, TablePrefix = "TaHugeRndNww" },
	--[TA_LRG_RND_WW] = { ID = TA_LRG_RND_WW, File = "METSL_TA_LRG_RND_WW.Civ5Map", Name = "Third Age-Large-RR-WW", Description = "80 x 64 Middle Earth during the Third Age with Random Resources and World Wrap (inc Rhun)", Size = "WORLDSIZE_LARGE", Civs = 10, Minors = 26, TablePrefix = "TaLrgRndWw" },
	[TA_LRG_RND_NWW] = { ID = TA_LRG_RND_NWW, File = "METSL_TA_LRG_RND_NWW.Civ5Map", Name = "Third Age-Large-RR-NWW", Description = "60 x 64 Middle Earth during the Third Age with Random Resources without World Wrap (no Rhun)", Size = "WORLDSIZE_LARGE", Civs = 10, Minors = 20, TablePrefix = "TaLrgRndNww" },
	--[TA_STD_RND_WW] = { ID = TA_STD_RND_WW, File = "METSL_TA_STD_RND_WW.Civ5Map", Name = "Third Age-Standard-RR-WW", Description = "65 x 52 Middle Earth during the Third Age with Random Resources and World Wrap (inc Rhun)", Size = "WORLDSIZE_STANDARD", Civs = 8, Minors = 16, TablePrefix = "TaStdRndWw" },
	--[TA_STD_RND_NWW] = { ID = TA_STD_RND_NWW, File = "METSL_TA_STD_RND_NWW.Civ5Map", Name = "Third Age-Standard-RR-NWW", Description = "49 x 52 Middle Earth during the Third Age with Random Resources without World Wrap (no Rhun)", Size = "WORLDSIZE_STANDARD", Civs = 8, Minors = 16, TablePrefix = "TaStdRndNww" },
}

MiddleEarthCivilizations = {
		[1] = {ID = GameInfo.Civilizations{Type="CIVILIZATION_MEC_ANGMAR"}().ID, Type = "CIVILIZATION_MEC_ANGMAR"},
		[2] = {ID = GameInfo.Civilizations{Type="CIVILIZATION_MEC_HOBBITS"}().ID, Type = "CIVILIZATION_MEC_HOBBITS"},
		[3] = {ID = GameInfo.Civilizations{Type="CIVILIZATION_MEC_ARNOR"}().ID, Type = "CIVILIZATION_MEC_ARNOR"},
		[4] = {ID = GameInfo.Civilizations{Type="CIVILIZATION_MEC_DWARVES"}().ID, Type = "CIVILIZATION_MEC_DWARVES"},
		[5] = {ID = GameInfo.Civilizations{Type="CIVILIZATION_MEC_EASTERLINGS"}().ID, Type = "CIVILIZATION_MEC_EASTERLINGS"},
		[6] = {ID = GameInfo.Civilizations{Type="CIVILIZATION_MEC_GOBLINS"}().ID, Type = "CIVILIZATION_MEC_GOBLINS"},
		[7] = {ID = GameInfo.Civilizations{Type="CIVILIZATION_MEC_GONDOR"}().ID, Type = "CIVILIZATION_MEC_GONDOR"},
		[8] = {ID = GameInfo.Civilizations{Type="CIVILIZATION_MEC_HIGH_ELVES"}().ID, Type = "CIVILIZATION_MEC_HIGH_ELVES"},
		[9] = {ID = GameInfo.Civilizations{Type="CIVILIZATION_MEC_ISENGARD"}().ID, Type = "CIVILIZATION_MEC_ISENGARD"},
		[10] = {ID = GameInfo.Civilizations{Type="CIVILIZATION_MEC_MORDOR"}().ID, Type = "CIVILIZATION_MEC_MORDOR"},
		[11] = {ID = GameInfo.Civilizations{Type="CIVILIZATION_MEC_ROHAN"}().ID, Type = "CIVILIZATION_MEC_ROHAN"},
		[12] = {ID = GameInfo.Civilizations{Type="CIVILIZATION_MEC_SOUTHRONS"}().ID, Type = "CIVILIZATION_MEC_SOUTHRONS"},
		[13] = {ID = GameInfo.Civilizations{Type="CIVILIZATION_MEC_UMBAR"}().ID, Type = "CIVILIZATION_MEC_UMBAR"},
		[14] = {ID = GameInfo.Civilizations{Type="CIVILIZATION_MEC_WOOD_ELVES"}().ID, Type = "CIVILIZATION_MEC_WOOD_ELVES"},
}

-- Natural Wonder renaming for METSL is done in XML
--[[
g_NaturalWonderName = { 
	[TA_HUGE_RND_WW] = { 
		TXT_KEY_FEATURE_VOLCANO = "Mount Doom",
		TXT_KEY_CIV5_FEATURES_KRAKATOA_TEXT = "Mount Doom, also known as Orodruin and Amon Amarth, was a volcano in Mordor where the One Ring was forged. It was the ultimate destination for Frodo's Quest of the Ring. When Sauron chose the land of Mordor as his dwelling-place in the Second Age, Mount Doom was the reason for his choice. Having been originally a Maiar disciple of Aulë the smith (before he decided to follow the evil Morgoth), he used the fire that welled there from the heart of the earth in his sorceries and his forging. The most famous result of his forging, and in fact the only one we know of for sure, was the One Ring. Mount Doom was much more than just any volcano; Sauron seems to have extended his own power into it, just as his former master Melkor had extended his own power into the flesh of Arda as his means of corrupting the Valar's shaping of the world. In Sauron's case, it was probably due to his use of it as a foundry for the forging of the Ring, as he was able to control its fires. It seems to have lain dormant when Sauron was away from Mordor, and sprung into life when his power grew. With the destruction of the Ring, Mount Doom had a massive eruption, sending massive lava flows down its sides and scattering the area with volcanic debris. The fiery eruption destroyed the Nazgûl and their mounts as they tried to reach Frodo on their Fell Beasts to reclaim the Ring.",
		TXT_KEY_FEATURE_CRATER = "Echoriath",
		TXT_KEY_CIV5_FEATURES_BARRINGER_TEXT = "The Echoriath or Encircling Mountains was a range of mountains in the north of Beleriand, next to Dorthonion, during the First Age. The Echoriath formed a natural circle of rock enclosing the valley later called Tumladen, within which lay the Elven city of Gondolin. A hidden ravine provided the only access through the Echoriath a way guarded by seven gates. The Eagles led by Thorondor took residence in a southern part of the mountains called the Crissaegrim and for long kept the spies of Morgoth from discovering the location of Gondolin. Fingolfin, a High King of the Ñoldor, was buried in the Echoriath north of Gondolin in a great cairn, his body having been taken there by the eagle Thorondor after he was slain in his duel with Morgoth.",
		TXT_KEY_FEATURE_MT_FUJI = "Caradhras",
		TXT_KEY_CIV5_FEATURES_FUJI_TEXT = "Caradhras, also called the Redhorn, and Baranzibar was one of the mightiest peaks in the Misty Mountains. On their quest to Mount Doom, the Nine Walkers attempted to cross the Redhorn Pass, lying beneath the slopes of Caradhras, and linking the former Ñoldorin realm of Eregion (Hollin) in the west to the Dimrill Dale and hence the Vale of Anduin in the east. After the fall of Khazad-Dum, this pass was predominantly used by elves travelling between Lothlórien and Rivendell. Caradhras was one of the Mountains of Moria, the three mountains under which the great Dwarf palace of Khazad-dûm was built. Caradhras was also the only site in Middle-earth where Mithril could be mined. But mining ever deeper into the roots of the mountain in search of mithril, the dwarf miners also unwittingly awakened the Balrog of Moria. Caradhras was called the Cruel by the Dwarves and had long had a bad reputation. The Redhorn Pass (also called the Redhorn Gate) was known to be treacherous and was used by hobbits migrating from Gladden Fields into Eriador. Because of its proximity to the Gladden Fields, it is possible that the River-folk may have passed through the Redhorn Pass. And it was here that Celebrian, the wife of Elrond, was captured by orcs, making it doubly significant to the trilogy.",
		TXT_KEY_FEATURE_MESA = "Weathertop",
		TXT_KEY_CIV5_FEATURES_GRANDMESA_TEXT = "Weathertop, known as also Amon Súl, was a hill in the Eriador region of Middle-earth, the southernmost and highest summit of the Weather Hills. The watch tower at its top overlooked the Great East Road in central Eriador, east of Bree, about halfway between the Shire and Rivendell. As represented in the The Atlas of Middle-earth, the hill rose a thousand feet (approximately 300 meters) above the relatively level lands round about, and with only the lower Weather Hills stretching away northwards, offered a commanding view in every direction. A path led from the north side of Weathertop northward to the other Weather Hills. The elevation of Weathertop itself above sea level was likely in the order of 1500-2000 feet (around 450-600 meters)",
		TXT_KEY_FEATURE_GIBRALTAR = "Tolfalas",
		TXT_KEY_CIV5_FEATURES_GIBRALTER_TEXT = "Tolfalas was a small, rocky island located in the Bay of Belfalas between the land of Belfalas and Southern Gondor, about twenty-five miles from the Mouths of Anduin. It is unknown whether anyone lived there or not or if it was used as a harbor for Gondor's ships.",
		TXT_KEY_FEATURE_MT_SINAI = "Lonely Mountain",
		TXT_KEY_CIV5_FEATURES_MT_SINAI_TEXT = "The Lonely Mountain, or Erebor, was a mountain northeast of Rhovanion. It was also the source of the River Running. For many ages of Middle-earth, it had been inhabited by the Dwarves of Durin's Folk up until the later half of the Third Age and then again in its closing years and into the Fourth Age.",
		TXT_KEY_FEATURE_MT_KAILASH = "

	 },
	[TA_HUGE_RND_NWW] = { },
	[TA_LRG_RND_WW] = {},
	[TA_LRG_RND_NWW] = {},
	[TA_STD_RND_WW] = {},
	[TA_STD_RND_NWW] = {},
}
]]

g_NaturalWonderPlacement = { 
	
	[TA_HUGE_RND_WW] = {
		["FEATURE_CRATER"] = {X=8, Y=69},
		["FEATURE_MESA"] = {X=41, Y=59},
		["FEATURE_GIBRALTAR"] = {X=43, Y=10},
		["FEATURE_MT_KAILASH"] = {X=41, Y=21},
		["FEATURE_FOUNTAIN_YOUTH"] = {X=55, Y=35},
		["FEATURE_LAKE_VICTORIA"] = {X=68, Y=64},
		["FEATURE_MT_SINAI"] = {X=2, Y=2},
	},
	--[[
	[TA_HUGE_RND_NWW] = {
		["FEATURE_CRATER"] = {X=8, Y=69},
		["FEATURE_MESA"] = {X=41, Y=59},
		["FEATURE_GIBRALTAR"] = {X=43, Y=10},
		["FEATURE_MT_KAILASH"] = {X=41, Y=21},
		["FEATURE_FOUNTAIN_YOUTH"] = {X=55, Y=35},
		["FEATURE_LAKE_VICTORIA"] = {X=68, Y=64},
		["FEATURE_MT_SINAI"] = {X=2, Y=2},
	},
	[TA_LRG_RND_WW] = {
	},
	]]
	[TA_LRG_RND_NWW] = {
		["FEATURE_CRATER"] = {X=7, Y=55},
		["FEATURE_MESA"] = {X=33, Y=47},
		["FEATURE_GIBRALTAR"] = {X=33, Y=7},
		["FEATURE_MT_KAILASH"] = {X=32, Y=17},
		--["FEATURE_FOUNTAIN_YOUTH"] = {X=44, Y=28}, overpowered unless i change it to a different effect
		--["FEATURE_LAKE_VICTORIA"] = {X=54, Y=49},
		["FEATURE_MT_SINAI"] = {X=1, Y=1},
	},
	--[[
	[TA_STD_RND_WW] = {
	},
	[TA_STD_RND_NWW] = {
	},
	]]
}

-- max number of resource tiles around civ starting position (see CivilizationsStartTable.xml)
MAX_REQUESTED_RESOURCE = 6

if (not modUserData.GetValue("MapID")) then
	modUserData.SetValue ("MapID", TA_HUGE_RND_WW)
	print("New MapID - " .. TA_HUGE_RND_WW)
end
if (not modUserData.GetValue("File")) then
	modUserData.SetValue ("File", g_MapList[TA_HUGE_RND_WW].File)
	print("New File - " .. g_MapList[TA_HUGE_RND_WW].File)
end
if (not modUserData.GetValue("NumMajorCivs")) then
	modUserData.SetValue ("NumMajorCivs", g_MapList[TA_HUGE_RND_WW].Civs)
	print("New Num Major Civs - " .. g_MapList[TA_HUGE_RND_WW].Civs)
end
if (not modUserData.GetValue("NumMinorCivs")) then
	modUserData.SetValue ("NumMinorCivs", g_MapList[TA_HUGE_RND_WW].Minors)
	print("New Num Minor Civs - " .. g_MapList[TA_HUGE_RND_WW].Minors)
end
--print(modUserData.GetValue("MapID"))
--print(modUserData.GetValue("File"))
--print(modUserData.GetValue("NumMajorCivs"))
--print(modUserData.GetValue("NumMinorCivs"))

-- City States placement
MINOR_PLACEMENT = 1
-- City States minimum distance
MINOR_DISTANCE = 2
-- Resources option
RESOURCE_QUANTITY = 3
NATURAL_WONDERS = 4
DYNAMIC_CITY_NAMING = 5
DCN_SPECIFIC_CIVILIZATION = 6
DCN_DWARVES_AND_GOBLINS = 7
RESOURCE_GEO = 8
RESOURCE_REQUESTED = 9
RESOURCE_SCALE = 10
RESOURCE_DEPOSIT = 11


-- Map option : City States placement
MINOR_TSL_ONLY = 1
MINOR_TSL_RANDOM = 2
MINOR_ALL_RANDOM = 3
--[[
-- Map option : City States minimum distance
g_MinorDistanceValue = {0,2,4,6,9}
MINOR_DISTANCE_NO = 1
MINOR_DISTANCE_MINI = 2
MINOR_DISTANCE_CLOSE = 3
MINOR_DISTANCE_MEDIUM = 4
MINOR_DISTANCE_AWAY = 5
]]
--Map option : Resources quantity
g_ResourceQuantityCoeff = {0.25,0.5,1,2,4}
RESOURCE_POOR = 1
RESOURCE_SPARSE = 2
RESOURCE_STANDARD = 3
RESOURCE_ABUNDANT = 4
RESOURCE_RICHE = 5

RESOURCE_RANDOM = 1
RESOURCE_FIXED = 2

MinorPlacementValues = { 
			{ Name	= "Only TSL", ToolTip = "Only City States with True Starting Location will be in game", Value = MINOR_TSL_ONLY,},
			{ Name	= "Random and TSL", ToolTip = "City States with no TSL get random placement", Value = MINOR_TSL_RANDOM,},
			{ Name	= "Totally random", ToolTip = "All City States get random placement", Value = MINOR_ALL_RANDOM,},
}
--------------------
-- Map option : Value
--------------------





g_MapPulldownOptions = {
[TA_HUGE_RND_WW] = {
	[MINOR_PLACEMENT] = {
		ID = MINOR_PLACEMENT,
		Name = "CS Placement",
		ToolTip = "Placement for City States",
		Disabled = false,
		DefaultValue = MINOR_TSL_ONLY,
		SortPriority = 2,
		Values = MinorPlacementValues -- mod dependancy for these values, see the MOD Dependancy section above
	},
	--[[
	[MINOR_DISTANCE] = {
			ID = MINOR_DISTANCE,
			Name = "CS Separation",
			ToolTip = "City States minimum separation distance: a city that starts under the minimum distance will be removed from the game",
			Disabled = false,
			DefaultValue = 1,
			SortPriority = 2,
			Values = { 
				{ Name	= "Don't check", ToolTip = "Allow City States starting positions to overlap. Not recommanded", Value = MINOR_DISTANCE_NO,},
				{ Name	= "Minimum", ToolTip = "3 tiles", Value = MINOR_DISTANCE_MINI,},
				{ Name	= "Close", ToolTip = "~ 5 tiles", Value = MINOR_DISTANCE_CLOSE,},
				{ Name	= "Medium", ToolTip = "~ 7 tiles", Value = MINOR_DISTANCE_MEDIUM,},
				{ Name	= "Away", ToolTip = "~ 9 tiles", Value = MINOR_DISTANCE_AWAY,},
			},
	},]]
	[RESOURCE_QUANTITY] = {
			ID = RESOURCE_QUANTITY,
			Name = "Resources",
			ToolTip = "Resources quantity",
			Disabled = false,
			DefaultValue = 3,
			SortPriority = 3,
			Values = { 
				{ Name	= "Poor", ToolTip = "Resources are extremly rare", Value = RESOURCE_POOR,},
				{ Name	= "Sparse", ToolTip = "Less resources", Value = RESOURCE_SPARSE,},
				{ Name	= "Standard", ToolTip = "Standard value", Value = RESOURCE_STANDARD,},
				{ Name	= "Abundant", ToolTip = "More resources", Value = RESOURCE_ABUNDANT,},
				{ Name	= "Riche", ToolTip = "I've said : Give me more resources !!!", Value = RESOURCE_RICHE,},
			},
	},
	
},
--[[
[TA_HUGE_RND_NWW] = {
	[MINOR_PLACEMENT] = {
		ID = MINOR_PLACEMENT,
		Name = "CS Placement",
		ToolTip = "Placement for City States",
		Disabled = false,
		DefaultValue = 1,
		SortPriority = 2,
		Values = MinorPlacementValues -- mod dependancy for these values, see the MOD Dependancy section above
	},
	[RESOURCE_QUANTITY] = {
			ID = RESOURCE_QUANTITY,
			Name = "Resources",
			ToolTip = "Resources quantity",
			Disabled = true,
			DefaultValue = RESOURCE_RANDOM,
			SortPriority = 3,
			Values = { 
				{ Name	= "Random", ToolTip = "Resources are randomly assigned using Firaxis Scrips", Value = RESOURCE_RANDOM,},
				{ Name	= "Fixed", ToolTip = "Hand picked resources", Value = RESOURCE_FIXED,},
			},
	},
	
},
[TA_LRG_RND_WW] = {
	[MINOR_PLACEMENT] = {
		ID = MINOR_PLACEMENT,
		Name = "CS Placement",
		ToolTip = "Placement for City States",
		Disabled = false,
		DefaultValue = 1,
		SortPriority = 2,
		Values = MinorPlacementValues -- mod dependancy for these values, see the MOD Dependancy section above
	},
	[RESOURCE_QUANTITY] = {
			ID = RESOURCE_QUANTITY,
			Name = "Resources",
			ToolTip = "Resources quantity",
			Disabled = true,
			DefaultValue = RESOURCE_RANDOM,
			SortPriority = 3,
			Values = { 
				{ Name	= "Random", ToolTip = "Resources are randomly assigned using Firaxis Scrips", Value = RESOURCE_RANDOM,},
				{ Name	= "Fixed", ToolTip = "Hand picked resources", Value = RESOURCE_FIXED,},
			},
	},

},
]]
[TA_LRG_RND_NWW] = {
	[MINOR_PLACEMENT] = {
		ID = MINOR_PLACEMENT,
		Name = "CS Placement",
		ToolTip = "Placement for City States",
		Disabled = false,
		DefaultValue = 1,
		SortPriority = 2,
		Values = MinorPlacementValues -- mod dependancy for these values, see the MOD Dependancy section above
	},
	[RESOURCE_QUANTITY] = {
			ID = RESOURCE_QUANTITY,
			Name = "Resources",
			ToolTip = "Resources quantity",
			Disabled = false,
			DefaultValue = 3,
			SortPriority = 3,
			Values = { 
				{ Name	= "Poor", ToolTip = "Resources are extremly rare", Value = RESOURCE_POOR,},
				{ Name	= "Sparse", ToolTip = "Less resources", Value = RESOURCE_SPARSE,},
				{ Name	= "Standard", ToolTip = "Standard value", Value = RESOURCE_STANDARD,},
				{ Name	= "Abundant", ToolTip = "More resources", Value = RESOURCE_ABUNDANT,},
				{ Name	= "Riche", ToolTip = "I've said : Give me more resources !!!", Value = RESOURCE_RICHE,},
			},
	},
	
},
--[[
[TA_STD_RND_WW] = {
	[MINOR_PLACEMENT] = {
		ID = MINOR_PLACEMENT,
		Name = "CS Placement",
		ToolTip = "Placement for City States",
		Disabled = false,
		DefaultValue = 1,
		SortPriority = 2,
		Values = MinorPlacementValues -- mod dependancy for these values, see the MOD Dependancy section above
	},
	[RESOURCE_QUANTITY] = {
			ID = RESOURCE_QUANTITY,
			Name = "Resources",
			ToolTip = "Resources quantity",
			Disabled = true,
			DefaultValue = RESOURCE_RANDOM,
			SortPriority = 3,
			Values = { 
				{ Name	= "Random", ToolTip = "Resources are randomly assigned using Firaxis Scrips", Value = RESOURCE_RANDOM,},
				{ Name	= "Fixed", ToolTip = "Hand picked resources", Value = RESOURCE_FIXED,},
			},
	},
	
},
[TA_STD_RND_NWW] = {
	[MINOR_PLACEMENT] = {
		ID = MINOR_PLACEMENT,
		Name = "CS Placement",
		ToolTip = "Placement for City States",
		Disabled = false,
		DefaultValue = 1,
		SortPriority = 2,
		Values = MinorPlacementValues -- mod dependancy for these values, see the MOD Dependancy section above
	},
	[RESOURCE_QUANTITY] = {
			ID = RESOURCE_QUANTITY,
			Name = "Resources",
			ToolTip = "Resources quantity",
			Disabled = true,
			DefaultValue = RESOURCE_RANDOM,
			SortPriority = 3,
			Values = { 
				{ Name	= "Random", ToolTip = "Resources are randomly assigned using Firaxis Scrips", Value = RESOURCE_RANDOM,},
				{ Name	= "Fixed", ToolTip = "Hand picked resources", Value = RESOURCE_FIXED,},
			},
	},

},
]]
}
g_MapCheckboxOptions = {
	[TA_HUGE_RND_WW] = {
		{
		ID = NATURAL_WONDERS,
		Name = "Natural Wonders",
		ToolTip = "Include Natural Wonders?",
		Disabled = false,
		GameOption = false,
		SortPriority = 0,
		},
		{
		ID = DYNAMIC_CITY_NAMING,
		Name = "Dynamic City Naming",
		ToolTip = "If applicable a city will be named by it's location rather than Civilization/City Order. City names may also change upon being conquered. (IE Anyone can found the city of Mount Doom if the city is next to Mount Doom [and the city of Mount Doom does not already exist]) Not all locations will have DCNs",
		Disabled = false,
		GameOption = false,
		SortPriority = 1,
		},
		{
		ID = DCN_SPECIFIC_CIVILIZATION,
		Name = "DCN: Specific Civilization",
		ToolTip = "Restricts Dynamic City Naming to each Civilizations City List. (IE Only Mordor can found the city of Mount Doom.) Not all locations will have DCNs",
		Disabled = false,
		GameOption = false,
		SortPriority = 2,
		},
		{
		ID = DCN_DWARVES_AND_GOBLINS,
		Name = "DCN: Not for Dwarves & Goblins",
		ToolTip = "The Dwarf and Goblin DCN are spread thoughout ME and are difficult for the civ to settle. For these Civilization's city names will work as usual.",
		Disabled = false,
		GameOption = false,
		SortPriority = 3,
		},
		{
		ID = RESOURCE_GEO,
		Name = "Use canonical geographic resource placement",
		ToolTip = "Force resources to be placed in the correct geographic region (Important for Role Playing)",
		Disabled = false,
		GameOption = false,
		SortPriority = 4,
		},	
		{
		ID = RESOURCE_REQUESTED,
		Name = "Add specific resources at starting positions",
		ToolTip = "Place canonical resources for each civilization (Important for Game Balance and Role Playing)",
		Disabled = false,
		GameOption = false,
		SortPriority = 5,
		},
		
		--}
		--ID = RESOURCE_DEPOSIT,
		--Name = "Add major deposits of resources",
		--ToolTip = "Place some heavy deposits in specified regions (Important for Game Balance and Role Playing)",
		--Disabled = false,
		--GameOption = false,
		--SortPriority = 6,
		--},	
		--{
		--ID = RESOURCE_SCALE,
		--Name = "Don't scale resources with players",
		--ToolTip = "The number of resources won't be scaled depending of the number of players (Bad for Game Balance)",
		--Disabled = false,
		--GameOption = false,
		--SortPriority =7,
		--},	
		

	},
	--[[
	[TA_HUGE_RND_NWW] = {
		{
		ID = NATURAL_WONDERS,
		Name = "Natural Wonders",
		ToolTip = "Include Natural Wonders?",
		Disabled = false,
		GameOption = false,
		SortPriority = 0,
		},
	},
	[TA_LRG_RND_WW] = {
	{
		ID = NATURAL_WONDERS,
		Name = "Natural Wonders",
		ToolTip = "Include Natural Wonders?",
		Disabled = false,
		GameOption = false,
		SortPriority = 0,
		},
	},
	]]
	[TA_LRG_RND_NWW] = {
	{
		ID = NATURAL_WONDERS,
		Name = "Natural Wonders",
		ToolTip = "Include Natural Wonders?",
		Disabled = false,
		GameOption = false,
		SortPriority = 0,
		},
		{
		ID = DYNAMIC_CITY_NAMING,
		Name = "Dynamic City Naming",
		ToolTip = "If applicable a city will be named by it's location rather than Civilization/City Order. City names may also change upon being conquered. (IE Anyone can found the city of Mount Doom if the city is next to Mount Doom [and the city of Mount Doom does not already exist]) Not all locations will have DCNs",
		Disabled = false,
		GameOption = false,
		SortPriority = 1,
		},
		{
		ID = DCN_SPECIFIC_CIVILIZATION,
		Name = "DCN: Specific Civilization",
		ToolTip = "Restricts Dynamic City Naming to each Civilizations City List. (IE Only Mordor can found the city of Mount Doom.) Not all locations will have DCNs",
		Disabled = false,
		GameOption = false,
		SortPriority = 2,
		},
		{
		ID = DCN_DWARVES_AND_GOBLINS,
		Name = "DCN: Not for Dwarves & Goblins",
		ToolTip = "The Dwarf and Goblin DCN are spread thoughout ME and are difficult for the civ to settle. For these Civilization's city names will work as usual.",
		Disabled = false,
		GameOption = false,
		SortPriority = 3,
		},
		{
		ID = RESOURCE_GEO,
		Name = "Use canonical geographic resource placement",
		ToolTip = "Force resources to be placed in the correct geographic region (Important for Role Playing)",
		Disabled = false,
		GameOption = false,
		SortPriority = 4,
		},	
		{
		ID = RESOURCE_REQUESTED,
		Name = "Add specific resources at starting positions",
		ToolTip = "Place canonical resources for each civilization (Important for Game Balance and Role Playing)",
		Disabled = false,
		GameOption = false,
		SortPriority = 5,
		},
	},
	--[[
	[TA_STD_RND_WW] = {
	{
		ID = NATURAL_WONDERS,
		Name = "Natural Wonders",
		ToolTip = "Include Natural Wonders?",
		Disabled = false,
		GameOption = false,
		SortPriority = 0,
		},
	},
	[TA_STD_RND_NWW] = {
	{
		ID = NATURAL_WONDERS,
		Name = "Natural Wonders",
		ToolTip = "Include Natural Wonders?",
		Disabled = false,
		GameOption = false,
		SortPriority = 0,
		},
	},
	]]
}
--[[
y_existingRoads = {
	[TA_HUGE_RND_WW] = {
		{
			            
			X = {20,21,22,23,24,25,25,26,  27,27,28,29,30,31,32,33,34,35,36,36,37,  37,37,37,38,37}
			Y = {56,56,56,56,56,56,55,55,  54,54,55,55,55,55,55,55,55,55,56,57,58,  59,60,61,62,63}
			Key
			  1		Mithlond
			  2		Michel Delving
			  3		Bree
			
		},
	},
	[TA_HUGE_RND_NWW] = {
		{
			X = {}
			Y = {}
		},
	},
	[TA_LRG_RND_WW] = {
		{
			X = {}
			Y = {}
		},
	},
	[TA_LRG_RND_NWW] = {
		{
			X = {}
			Y = {}
		},
	},
	[TA_STD_RND_WW] = {
		{
			X = {}
			Y = {}
		},
	},
	[TA_STD_RND_NWW] = {
		{
			X = {}
			Y = {}
		},
	},
}
]]

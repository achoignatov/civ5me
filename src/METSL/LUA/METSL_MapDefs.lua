-- METSL_MapDefs
-- Shared definitions for the Middle-earth True Start Location map scripts.
-- Used both by the map scripts (map generation) and by the in-game script.
--
-- Multiplayer rewrite: the original mod stored its settings in a per-PC user database
-- (Modding.OpenUserData) written by a single-player-only setup screen. Here every setting is a
-- regular map-script option, which the game synchronises to all players through PreGame.
--------------------------------------------------------------

-- Option catalogue. Boolean options use Values {Yes, No}, i.e. value 1 = enabled.
METSL_OptionDefs = {
	MinorPlacement = {
		Name = "City-State Placement",
		Description = "How city-states are placed on the map",
		Values = {
			{"Only TSL", "Only city-states with a True Start Location are kept in the game (others are removed on turn 0)"},
			{"TSL + random", "City-states without a True Start Location get a random location"},
			{"Totally random", "All city-states get a random location"},
		},
		DefaultValue = 1,
		SortPriority = 1,
	},
	ResourceQuantity = {
		Name = "Resources",
		Description = "Resource quantity",
		Values = {
			{"Poor", "Resources are extremely rare"},
			{"Sparse", "Less resources"},
			{"Standard", "Standard value"},
			{"Abundant", "More resources"},
			{"Rich", "Give me more resources!"},
		},
		DefaultValue = 3,
		SortPriority = 2,
	},
	NaturalWonders = {
		Name = "Natural Wonders",
		Description = "Place the Middle-earth natural wonders (Amon Sul, Tolfalas, Stone of Erech, Lonely Mountain...)",
		Values = { {"Yes", "Place natural wonders"}, {"No", "No natural wonders"} },
		DefaultValue = 1,
		SortPriority = 3,
	},
	ResourceGeo = {
		Name = "Canonical Resource Regions",
		Description = "Force resources to be placed in the correct geographic region (important for role playing)",
		Values = { {"Yes", ""}, {"No", ""} },
		DefaultValue = 1,
		SortPriority = 4,
	},
	ResourceRequested = {
		Name = "Civilization Start Resources",
		Description = "Place canonical resources near each civilization's start (important for game balance and role playing)",
		Values = { {"Yes", ""}, {"No", ""} },
		DefaultValue = 1,
		SortPriority = 5,
	},
	DynamicCityNaming = {
		Name = "Dynamic City Naming",
		Description = "Cities are named after their location rather than the civilization's city list, and may be renamed when conquered (e.g. anyone founding a city next to Mount Doom names it Mount Doom)",
		Values = { {"Yes", ""}, {"No", ""} },
		DefaultValue = 1,
		SortPriority = 6,
	},
	DCNSpecificCivilization = {
		Name = "Dynamic City Naming: Own Civilization Only",
		Description = "Restrict dynamic city names to each civilization's own city list (e.g. only Mordor can found Mount Doom)",
		Values = { {"Yes", ""}, {"No", ""} },
		DefaultValue = 2,
		SortPriority = 7,
	},
	DCNDwarvesAndGoblins = {
		Name = "Dynamic City Naming: Not for Dwarves & Goblins",
		Description = "Dwarf and Goblin dynamic names are spread throughout Middle-earth; with this on those two civilizations use their normal city lists",
		Values = { {"Yes", ""}, {"No", ""} },
		DefaultValue = 2,
		SortPriority = 8,
	},
	ExtraSettler = {
		Name = "Extra Starting Settler",
		Description = "Every civilization starts with 2 Settlers instead of 1 (the second one is ready to found a second city right away)",
		Values = { {"Yes", "Start with 2 Settlers"}, {"No", "Start with 1 Settler"} },
		DefaultValue = 1,
		SortPriority = 9,
	},
}

local FULL_OPTIONS = { "MinorPlacement", "ResourceQuantity", "NaturalWonders", "ResourceGeo", "ResourceRequested",
	"DynamicCityNaming", "DCNSpecificCivilization", "DCNDwarvesAndGoblins", "ExtraSettler" }
local BASIC_OPTIONS = { "MinorPlacement", "ResourceQuantity", "ExtraSettler" }
-- New options go at the END of these lists: an option's ID is its position in the list.

-- Natural wonder positions (true map coordinates), from the original METSL_Defines.lua
local NW_HUGE = {
	{ Feature = "FEATURE_CRATER", X = 8, Y = 69 },
	{ Feature = "FEATURE_MESA", X = 41, Y = 59 },
	{ Feature = "FEATURE_GIBRALTAR", X = 43, Y = 10 },
	{ Feature = "FEATURE_MT_KAILASH", X = 41, Y = 21 },
	{ Feature = "FEATURE_FOUNTAIN_YOUTH", X = 55, Y = 35 },
	{ Feature = "FEATURE_LAKE_VICTORIA", X = 68, Y = 64 },
	{ Feature = "FEATURE_MT_SINAI", X = 2, Y = 2 },
}
local NW_LARGE = {
	{ Feature = "FEATURE_CRATER", X = 7, Y = 55 },
	{ Feature = "FEATURE_MESA", X = 33, Y = 47 },
	{ Feature = "FEATURE_GIBRALTAR", X = 33, Y = 7 },
	{ Feature = "FEATURE_MT_KAILASH", X = 32, Y = 17 },
	{ Feature = "FEATURE_MT_SINAI", X = 1, Y = 1 },
}

-- Ordered list (index order matters only for display)
METSL_MapList = {
	{
		Key = "TaHugeRndWw", Script = "METSL_TaHugeRndWw",
		Name = "Middle-earth TSL: Third Age (Huge, World Wrap)",
		Description = "100x80 Middle-earth during the Third Age, incl. Rhun. True start locations, semi-random resources, dynamic city naming. Recommended size: Huge.",
		Options = FULL_OPTIONS, NaturalWonders = NW_HUGE,
		HasRegions = true, HasRequested = true, HasDCN = true,
	},
	{
		Key = "TaLrgRndNww", Script = "METSL_TaLrgRndNww",
		Name = "Middle-earth TSL: Third Age (Large)",
		Description = "60x64 Middle-earth during the Third Age without world wrap (no Rhun). True start locations, semi-random resources, dynamic city naming. Recommended size: Large.",
		Options = FULL_OPTIONS, NaturalWonders = NW_LARGE,
		HasRegions = true, HasRequested = true, HasDCN = true,
	},
	{
		Key = "TaHugeRndNww", Script = "METSL_TaHugeRndNww",
		Name = "Middle-earth TSL: Huge, No Wrap (basic)",
		Description = "75x80 Middle-earth without world wrap (no Rhun). True start locations and random resources only.",
		Options = BASIC_OPTIONS,
	},
	{
		Key = "TaLrgRndWw", Script = "METSL_TaLrgRndWw",
		Name = "Middle-earth TSL: Large, World Wrap (basic)",
		Description = "80x64 Middle-earth with world wrap (incl. Rhun). True start locations and random resources only.",
		Options = BASIC_OPTIONS,
	},
	{
		Key = "TaStdRndWw", Script = "METSL_TaStdRndWw",
		Name = "Middle-earth TSL: Standard, World Wrap (basic)",
		Description = "65x52 Middle-earth with world wrap (incl. Rhun). True start locations and random resources only.",
		Options = BASIC_OPTIONS,
	},
	{
		Key = "TaStdRndNww", Script = "METSL_TaStdRndNww",
		Name = "Middle-earth TSL: Standard, No Wrap (basic)",
		Description = "49x52 Middle-earth without world wrap (no Rhun). True start locations and random resources only.",
		Options = BASIC_OPTIONS,
	},
}

METSL_Maps = {}
for _, def in ipairs(METSL_MapList) do
	METSL_Maps[def.Key] = def
	def.OptionIDs = {}
	for id, optKey in ipairs(def.Options) do
		def.OptionIDs[optKey] = id
	end
end

-- table names in the database
function METSL_CivStartTable(def) return "Civilizations_" .. def.Key .. "StartPosition" end
function METSL_MinorStartTable(def) return "MinorCiv_" .. def.Key .. "StartPosition" end
function METSL_RequestedTable(def) return "Civilizations_" .. def.Key .. "RequestedResource" end
function METSL_RegionPosTable(def) return "Resource_" .. def.Key .. "RegionPosition" end
function METSL_RegionExcTable(def) return "Resource_" .. def.Key .. "RegionExclude" end
function METSL_DCNTable(def) return def.Key .. "_DynamicCityNames" end

-- Build CustomOptions for GetMapScriptInfo
function METSL_BuildCustomOptions(def)
	local options = {}
	for _, optKey in ipairs(def.Options) do
		local o = METSL_OptionDefs[optKey]
		table.insert(options, {
			Name = o.Name,
			Description = o.Description,
			Values = o.Values,
			DefaultValue = o.DefaultValue,
			SortPriority = o.SortPriority,
		})
	end
	return options
end

-- Read all options. getter = Map.GetCustomOption (map generation) or PreGame.GetMapOption (in game).
-- Unset / invalid values fall back to the option default; options a map doesn't have get their default
-- for booleans that are map features (so they simply have no effect when the map lacks the data).
function METSL_ReadOptions(def, getter)
	local values = {}
	for optKey, o in pairs(METSL_OptionDefs) do
		local v = nil
		local id = def.OptionIDs[optKey]
		if id and getter then
			local ok, res = pcall(getter, id)
			if ok and type(res) == "number" and res >= 1 and res <= #o.Values then
				v = res
			end
		end
		values[optKey] = v or o.DefaultValue
	end
	local opt = {
		MinorPlacement = values.MinorPlacement,                -- 1 TSL only, 2 TSL+random, 3 all random
		ResourceQuantity = values.ResourceQuantity,            -- 1..5
		NaturalWonders = (values.NaturalWonders == 1) and def.NaturalWonders ~= nil,
		ResourceGeo = (values.ResourceGeo == 1) and def.HasRegions == true,
		ResourceRequested = (values.ResourceRequested == 1) and def.HasRequested == true,
		DynamicCityNaming = (values.DynamicCityNaming == 1) and def.HasDCN == true,
		DCNSpecificCivilization = (values.DCNSpecificCivilization == 1),
		DCNDwarvesAndGoblins = (values.DCNDwarvesAndGoblins == 1),
		ExtraSettler = (values.ExtraSettler == 1),
	}
	return opt
end

METSL_MINOR_TSL_ONLY = 1
METSL_MINOR_TSL_RANDOM = 2
METSL_MINOR_ALL_RANDOM = 3
METSL_ResourceQuantityCoeff = { 0.25, 0.5, 1, 2, 4 }

-- Identify the METSL map of the running game from the map script path (in game only)
function METSL_GetCurrentMapDef()
	local script = PreGame.GetMapScript and PreGame.GetMapScript() or nil
	if not script then return nil end
	script = string.lower(script)
	for _, def in ipairs(METSL_MapList) do
		if string.find(script, string.lower(def.Script) .. ".lua", 1, true) then
			return def
		end
	end
	return nil
end

-- Does this minor civ type have a TSL on this map?
function METSL_MinorHasTSL(def, minorCivType)
	local tbl = GameInfo[METSL_MinorStartTable(def)]
	if not tbl then return false end
	for row in tbl() do
		if row.Type == minorCivType then return true end
	end
	return false
end

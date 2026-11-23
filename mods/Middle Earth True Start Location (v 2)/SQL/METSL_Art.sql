-- Used with permission by Orignial Author Framed Architect
-- For Faerun for BNW
-- Edited by [SSU]yenyang

--------------------------------------------------------------------------------------------------
--Font Textures
-------------------------------------------------------------------------------------------------- 
INSERT INTO IconFontTextures (IconFontTexture,	IconFontTextureFile)
SELECT 'ICON_FONT_TEXTURE_RESOURCES',			'Resources-FontIcons';

--------------------------------------------------------------------------------------------------
--Font Mapping
--------------------------------------------------------------------------------------------------
INSERT INTO IconFontMapping (IconName,	IconFontTexture,					IconMapping)
SELECT 'ICON_RES_MITHRAL',				'ICON_FONT_TEXTURE_RESOURCES',		1 UNION ALL
SELECT 'ICON_RES_TIMBER',				'ICON_FONT_TEXTURE_RESOURCES',		3;

--------------------------------------------------------------------------------------------------
--SV Icons
--------------------------------------------------------------------------------------------------
INSERT INTO ArtDefine_StrategicView (StrategicViewType, TileType,			Asset)
SELECT 'ART_DEF_RESOURCE_TIMBER',						'Resource',			'SV_Timber.dds' UNION ALL
SELECT 'ART_DEF_RESOURCE_MITHRAL',						'Resource',			'SV_Mithral.dds' UNION ALL
SELECT 'ART_DEF_RESOURCE_MUSHROOMS',					'Resource',			'SV_Mushrooms.dds';

INSERT INTO ArtDefine_Landmarks (ResourceType,	ImprovementType,					Model,									Era,			State,					Scale,	LayoutHandler,	TerrainContour)
SELECT 'ART_DEF_RESOURCE_TIMBER',				'ART_DEF_IMPROVEMENT_NONE',			'Resource_Spice.fxsxml',				'Any',			'Any',					0.96,	'SNAPSHOT',		1 UNION ALL
SELECT 'ART_DEF_RESOURCE_MITHRAL',				'ART_DEF_IMPROVEMENT_NONE',			'Aluminum.fxsxml',						'Any',			'Any',					1,		'SNAPSHOT',		1 UNION ALL
SELECT 'ART_DEF_RESOURCE_MITHRAL',				'ART_DEF_IMPROVEMENT_MINE',			'HB_MED_Mine_Aluminum.fxsxml',			'Ancient',		'UnderConstruction',	1,		'SNAPSHOT',		1 UNION ALL
SELECT 'ART_DEF_RESOURCE_MITHRAL',				'ART_DEF_IMPROVEMENT_MINE',			'MED_Mine_Aluminum.fxsxml',				'Ancient',		'Constructed',			1,		'SNAPSHOT',		1 UNION ALL
SELECT 'ART_DEF_RESOURCE_MITHRAL',				'ART_DEF_IMPROVEMENT_MINE',			'PL_MED_Mine_Aluminum.fxsxml',			'Ancient',		'Pillaged',				1,		'SNAPSHOT',		1 UNION ALL
SELECT 'ART_DEF_RESOURCE_MITHRAL',				'ART_DEF_IMPROVEMENT_MINE',			'HB_IND_Mine_Aluminum.fxsxml',			'Industrial',	'UnderConstruction',	1,		'SNAPSHOT',		1 UNION ALL
SELECT 'ART_DEF_RESOURCE_MITHRAL',				'ART_DEF_IMPROVEMENT_MINE',			'IND_Mine_Aluminum.fxsxml',				'Industrial',	'Constructed',			1,		'SNAPSHOT',		1 UNION ALL
SELECT 'ART_DEF_RESOURCE_MITHRAL',				'ART_DEF_IMPROVEMENT_MINE',			'PL_IND_Mine_Aluminum.fxsxml',			'Industrial',	'Pillaged',				1,		'SNAPSHOT',		1 UNION ALL
SELECT 'ART_DEF_RESOURCE_MUSHROOMS',			'ART_DEF_IMPROVEMENT_NONE',			'resource_mushrooms.fxsxml',			'Any',			'Any',					0.65,	'SNAPSHOT',		1 UNION ALL
SELECT 'ART_DEF_RESOURCE_MUSHROOMS',			'ART_DEF_IMPROVEMENT_PLANTATION',	'hb_plantation_mid_mushrooms.fxsxml',	'Ancient',		'UnderConstruction',	0.65,	'SNAPSHOT',		1 UNION ALL
SELECT 'ART_DEF_RESOURCE_MUSHROOMS',			'ART_DEF_IMPROVEMENT_PLANTATION',	'plantation_mid_mushrooms.fxsxml',		'Ancient',		'Constructed',			0.65,	'SNAPSHOT',		1 UNION ALL
SELECT 'ART_DEF_RESOURCE_MUSHROOMS',			'ART_DEF_IMPROVEMENT_PLANTATION',	'PL_Plantation_MID_Cotton.fxsxml',		'Ancient',		'Pillaged',				0.65,	'SNAPSHOT',		1 UNION ALL
SELECT 'ART_DEF_RESOURCE_MUSHROOMS',			'ART_DEF_IMPROVEMENT_PLANTATION',	'hb_plantation_mid_mushrooms.fxsxml',	'Industrial',	'UnderConstruction',	0.65,	'SNAPSHOT',		1 UNION ALL
SELECT 'ART_DEF_RESOURCE_MUSHROOMS',			'ART_DEF_IMPROVEMENT_PLANTATION',	'plantation_mid_mushrooms.fxsxml',		'Industrial',	'Constructed',			0.65,	'SNAPSHOT',		1 UNION ALL
SELECT 'ART_DEF_RESOURCE_MUSHROOMS',			'ART_DEF_IMPROVEMENT_PLANTATION',	'PL_Plantation_MID_Cotton.fxsxml',		'Industrial',	'Pillaged',				0.65,	'SNAPSHOT',		1;

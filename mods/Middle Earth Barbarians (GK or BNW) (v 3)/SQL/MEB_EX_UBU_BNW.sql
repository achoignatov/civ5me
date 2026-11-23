
-- Barbarian Axman into Dunlendings
UPDATE Units SET 'Description'='TXT_KEY_UNIT_BARBARIAN_DUNLENDINGS' WHERE Type = 'UNIT_BARBARIAN_AXMAN';
UPDATE Units SET 'Help'='TXT_KEY_UNIT_BARBARIAN_DUNLENDINGS' WHERE Type = 'UNIT_BARBARIAN_AXMAN';
-- Delete Barbarian Horsemen from BNW (Will be added later to accomodate players without BNW)
DELETE From Civilization_UnitClassOverrides WHERE UnitType = 'UNIT_BARBARIAN_HORSEMAN';
DELETE FROM Units WHERE Type = 'UNIT_BARBARIAN_HORSEMAN'; 
-- Set New Unique Barbarian Units as UUs in the Barbarian Civilization
INSERT INTO Civilization_UnitClassOverrides (CivilizationType, UnitClassType, UnitType) VALUES('CIVILIZATION_BARBARIAN','UNITCLASS_COMPOSITE_BOWMAN','UNIT_BARBARIAN_COMPOSITE_BOWMAN');
INSERT INTO Civilization_UnitClassOverrides (CivilizationType, UnitClassType, UnitType) VALUES('CIVILIZATION_BARBARIAN','UNITCLASS_CROSSBOWMAN','UNIT_BARBARIAN_CROSSBOWMAN');
INSERT INTO Civilization_UnitClassOverrides (CivilizationType, UnitClassType, UnitType) VALUES('CIVILIZATION_BARBARIAN','UNITCLASS_MUSKETMAN','UNIT_BARBARIAN_MUSKETMAN');
INSERT INTO Civilization_UnitClassOverrides (CivilizationType, UnitClassType, UnitType) VALUES('CIVILIZATION_BARBARIAN','UNITCLASS_HORSEMAN','UNIT_BARBARIAN_HORSEMAN');
INSERT INTO Civilization_UnitClassOverrides (CivilizationType, UnitClassType, UnitType) VALUES('CIVILIZATION_BARBARIAN','UNITCLASS_LONGSWORDSMAN','UNIT_BARBARIAN_LONGSWORDSMAN');
UPDATE Civilization_UnitClassOverrides SET 'UnitType'='UNIT_BARBARIAN_KNIGHT' WHERE CivilizationType = 'CIVILIZATION_BARBARIAN' and UnitClassType = 'UNITCLASS_KNIGHT';

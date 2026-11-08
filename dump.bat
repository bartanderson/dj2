@echo off
set GIT_PAGER=cat
if not exist _queries mkdir _queries

git --no-pager show feat/import-check:og_system/01_core.json       > _queries\01_core.json
git --no-pager show feat/import-check:og_system/02_classes.json    > _queries\02_classes.json
git --no-pager show feat/import-check:og_system/03_races.json      > _queries\03_races.json
git --no-pager show feat/import-check:og_system/04_magic.json      > _queries\04_magic.json
git --no-pager show feat/import-check:og_system/08_exploration.json > _queries\08_exploration.json
git --no-pager show feat/import-check:og_system/09_social.json     > _queries\09_social.json
git --no-pager show feat/import-check:og_system/12_engine.json     > _queries\12_engine.json
git --no-pager show feat/import-check:world/character.py           > _queries\character.py
git --no-pager show feat/import-check:world/dnd_data.py            > _queries\dnd_data.py
git --no-pager show feat/import-check:world/character_generator.py > _queries\character_generator.py
git --no-pager show feat/import-check:world/character_builder.py   > _queries\character_builder.py
git --no-pager show feat/import-check:world/character_manager.py   > _queries\character_manager.py
git --no-pager show feat/import-check:world/authority_system.py    > _queries\authority_system.py
git --no-pager show feat/import-check:tests/test_character_builder.py > _queries\test_character_builder.py

REM Extract just the ability/race sections of the two large files
git --no-pager show feat/import-check:world/narrative_system.py | findstr /N /I /C:"race" /C:"attribute" /C:"ability" /C:"bonus" > _queries\narrative_hits.txt
git --no-pager show feat/import-check:og_system/06_monsters.json | findstr /N /I /C:"brawn" /C:"wits" /C:"finesse" /C:"will" /C:"save" > _queries\monsters_hits.txt

echo Done. Files are in _queries\
pause
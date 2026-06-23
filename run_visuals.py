"""Run visual asset downloads."""
from pathlib import Path
from world.visuals.catalog import AssetCatalog
from world.visuals.sources import register_sources
from world.visuals.character_sources import register_character_sources

assets_dir = Path("assets/visuals")
db_path = assets_dir / "visual_assets.db"
bases_dir = assets_dir / "bases"
portraits_dir = assets_dir / "characters" / "portraits"

catalog = AssetCatalog(db_path)

print("=== Downloading scene backgrounds ===")
result = register_sources(catalog, bases_dir)
print(result)

print("\n=== Downloading character portraits ===")
result = register_character_sources(catalog, portraits_dir)
print(result)

catalog.close()
print("\nDone.")

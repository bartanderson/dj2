"""
Curated public-domain portrait sources for character archetypes.

All images are public domain (artists deceased 100+ years).
Sources: Dutch Golden Age masters (Hals, Rembrandt, Vermeer),
         Howard Pyle illustrations, Gustave Dore engravings.

Each entry maps to a character archetype id and provides a real
portrait as the inpainting/img2img base for identity-consistent generation.

Run register_character_sources(catalog, download_dir) to fetch and catalog.
Archetypes marked "generate" have no good portrait match and should be
built entirely from text-to-image using character_generator.py.
"""

from pathlib import Path
from typing import List, Dict, Optional

# ---------------------------------------------------------------------------
# Confirmed portrait sources — all URLs verified
# ---------------------------------------------------------------------------
# Fields:
#   archetype_id  — matches archetypes.py id
#   id            — unique source id
#   url           — confirmed upload.wikimedia.org direct URL
#   artist        — attribution
#   credit        — full public domain credit string
#   fit           — how well this matches the archetype ("perfect", "good", "loose")
#   notes         — what inpainting should change to fit the archetype

CHARACTER_SOURCES: List[Dict] = [

    # -----------------------------------------------------------------------
    # NPC: INNKEEPER (female) — Frans Hals "Malle Babbe"
    # Expressive middle-aged woman, powerful characterful face
    # -----------------------------------------------------------------------
    {
        "archetype_id": "innkeeper_female",
        "id": "hals_malle_babbe",
        "url": "https://upload.wikimedia.org/wikipedia/commons/d/d1/Hals%2C_Frans_-_Malle_Babbe.jpg",
        "artist": "Frans Hals",
        "credit": "Frans Hals, Malle Babbe, c.1633-1635. Gemäldegalerie Berlin. Public domain.",
        "fit": "perfect",
        "notes": "Strong expressive face, warm coloring. Inpaint to add apron, soften expression slightly for innkeeper rather than wild woman.",
    },

    # -----------------------------------------------------------------------
    # NPC: INNKEEPER (male) — Frans Hals "Verdonck"
    # Bearded middle-aged man with intense direct expression
    # -----------------------------------------------------------------------
    {
        "archetype_id": "innkeeper_male",
        "id": "hals_verdonck",
        "url": "https://upload.wikimedia.org/wikipedia/commons/7/75/Frans_Hals_040.jpg",
        "artist": "Frans Hals",
        "credit": "Frans Hals, Pieter Verdonck, c.1627. Scottish National Gallery. Public domain.",
        "fit": "perfect",
        "notes": "Bearded middle-aged man, direct gaze. Good innkeeper energy. Inpaint to add apron/tavern context.",
    },

    # -----------------------------------------------------------------------
    # NPC: MERCHANT (male) — Frans Hals "Isaac Massa"
    # Well-dressed merchant, fur hat, relaxed confident pose
    # -----------------------------------------------------------------------
    {
        "archetype_id": "merchant_male",
        "id": "hals_isaac_massa",
        "url": "https://upload.wikimedia.org/wikipedia/commons/c/c4/Portrait_of_Isaac_Abrahamsz._Massa_by_Frans_Hals.png",
        "artist": "Frans Hals",
        "credit": "Frans Hals, Portrait of Isaac Abrahamsz. Massa, 1626. Art Gallery of Ontario. Public domain.",
        "fit": "perfect",
        "notes": "Merchant with fur hat, relaxed pose, wealthy trader energy. Keep as-is or inpaint hat to fantasy style.",
    },

    # -----------------------------------------------------------------------
    # NPC: MERCHANT (female) — Frans Hals "Portrait of a Woman"
    # Composed 37-year-old woman in formal dress
    # -----------------------------------------------------------------------
    {
        "archetype_id": "merchant_female",
        "id": "hals_woman_standing",
        "url": "https://upload.wikimedia.org/wikipedia/commons/d/da/Frans_Hals_-_Portrait_of_a_woman.jpg",
        "artist": "Frans Hals",
        "credit": "Frans Hals, Portrait of a Woman, c.1630-35. Chatsworth House. Public domain.",
        "fit": "good",
        "notes": "Formal standing woman. Inpaint to replace formal lace collar with simpler practical merchant clothing.",
    },

    # -----------------------------------------------------------------------
    # NPC: SAGE / SCHOLAR — Rembrandt "Portrait of an Old Man in Red"
    # Magnificent elder male, wise face, red robes — perfect scholar/priest/sage
    # -----------------------------------------------------------------------
    {
        "archetype_id": "sage_elder",
        "id": "rembrandt_old_man_red",
        "url": "https://upload.wikimedia.org/wikipedia/commons/c/c8/Rembrandt_Harmensz._van_Rijn_-_Portrait_of_an_Old_Man_in_Red.jpg",
        "artist": "Rembrandt van Rijn",
        "credit": "Rembrandt van Rijn, Portrait of an Old Man in Red, c.1652-54. Hermitage Museum. Public domain.",
        "fit": "perfect",
        "notes": "Magnificent elder face, red robes suit scholar/sage directly. Inpaint to add books, scrolls in background.",
    },

    # -----------------------------------------------------------------------
    # NPC: BEGGAR / INFORMANT — Frans Hals "Man Holding a Skull"
    # Older man, intense expression, memento mori subject
    # -----------------------------------------------------------------------
    {
        "archetype_id": "beggar_informant",
        "id": "hals_man_skull",
        "url": "https://upload.wikimedia.org/wikipedia/commons/c/cd/Frans_Hals_052.jpg",
        "artist": "Frans Hals",
        "credit": "Frans Hals, Portrait of a Man Holding a Skull, c.1616. Barber Institute, Birmingham. Public domain.",
        "fit": "good",
        "notes": "~60 year old man, intense look. Remove skull, inpaint ragged cloak, add hood. Knowing expression already there.",
    },

    # -----------------------------------------------------------------------
    # NPC: NOBLE — Frans Hals "Portrait of a Woman" (elder, formal)
    # Dignified 72-year-old woman — noble elder matriarch
    # -----------------------------------------------------------------------
    {
        "archetype_id": "noble",
        "id": "hals_elder_noblewoman",
        "url": "https://upload.wikimedia.org/wikipedia/commons/0/06/Frans_Hals_-_An_Old_Lady_-_1957.18.4_-_Yale_University_Art_Gallery.jpg",
        "artist": "Frans Hals",
        "credit": "Frans Hals, An Old Lady, 1628. Yale University Art Gallery. Public domain.",
        "fit": "good",
        "notes": "Elder woman, formal and dignified. Inpaint to add jewels, richer fabric, warmer coloring for fantasy noble.",
    },

    # -----------------------------------------------------------------------
    # CLASS: PRIEST — Rembrandt self-portrait (mature, 53 years)
    # Contemplative, wise, layered clothing
    # -----------------------------------------------------------------------
    {
        "archetype_id": "priest_human_male",
        "id": "rembrandt_self_portrait_1659",
        "url": "https://upload.wikimedia.org/wikipedia/commons/b/bd/Rembrandt_van_Rijn_-_Self-Portrait_-_Google_Art_Project.jpg",
        "artist": "Rembrandt van Rijn",
        "credit": "Rembrandt van Rijn, Self-Portrait, 1659. National Gallery of Art, Washington. Public domain.",
        "fit": "good",
        "notes": "~53 year old man, beret and coat, introspective expression. Inpaint to add holy symbol, medium armor underneath.",
    },

    # -----------------------------------------------------------------------
    # CLASS: MAGE — Howard Pyle "The Enchanter Merlin"
    # Elder wizard, robes, staff — archetypal mage figure
    # -----------------------------------------------------------------------
    {
        "archetype_id": "mage_human_female",
        "id": "pyle_merlin",
        "url": "https://upload.wikimedia.org/wikipedia/commons/7/79/Arthur-Pyle_The_Enchanter_Merlin.JPG",
        "artist": "Howard Pyle",
        "credit": "Howard Pyle, The Enchanter Merlin, from 'The Story of King Arthur and His Knights', 1903. Public domain.",
        "fit": "loose",
        "notes": "Elder male wizard — this is a loose base only. Use for composition and lighting. Inpaint to female face, younger, darker robes. Good staff/arcane atmosphere to preserve.",
    },

    # -----------------------------------------------------------------------
    # CLASS: ROGUE / BARD — Howard Pyle "The Buccaneer"
    # Well-dressed swashbuckler, confident pose, period clothing
    # -----------------------------------------------------------------------
    {
        "archetype_id": "rogue_elf_female",
        "id": "pyle_buccaneer",
        "url": "https://upload.wikimedia.org/wikipedia/commons/d/db/Pyle_pirate_handsome.jpg",
        "artist": "Howard Pyle",
        "credit": "Howard Pyle, The Buccaneer was a Picturesque Fellow, 1905. Delaware Art Museum. Public domain.",
        "fit": "loose",
        "notes": "Confident swashbuckler pose, elaborate period clothing. Inpaint to elven female face, pointed ears, leather armor replacing coat.",
    },
    {
        "archetype_id": "bard_halfling_female",
        "id": "hals_singing_girl",
        "url": "https://upload.wikimedia.org/wikipedia/commons/d/d5/Hals%2C_Frans_-_Singing_Girl_-_1626-30.jpg",
        "artist": "Frans Hals",
        "credit": "Frans Hals, Singing Girl, 1626-30. Virginia Museum of Fine Arts. Public domain.",
        "fit": "good",
        "notes": "Young woman mid-song, expressive open face. Note: small original (917x910px). Upscale before inpainting. Add lute, colorful clothing, halfling height implied by crop.",
    },

    # -----------------------------------------------------------------------
    # CLASS: WARRIOR — Howard Pyle "Captain Keitt" (pirate captain)
    # Commanding figure in period clothing with weapon
    # -----------------------------------------------------------------------
    {
        "archetype_id": "warrior_human_male",
        "id": "pyle_pirate_captain",
        "url": "https://upload.wikimedia.org/wikipedia/commons/b/b9/Pyle_pirate_captain.jpg",
        "artist": "Howard Pyle",
        "credit": "Howard Pyle, Captain Keitt, from 'Book of Pirates', 1921. Public domain.",
        "fit": "loose",
        "notes": "Commanding figure on deck, tricorne and period coat. Inpaint to chainmail armor, sword replacing pistol, remove nautical background for stone wall/battleground.",
    },
]

# ---------------------------------------------------------------------------
# Archetypes without good portrait matches — generate from scratch
# These need character_generator.py text-to-image, not a base portrait
# ---------------------------------------------------------------------------
GENERATE_FROM_SCRATCH = [
    "warrior_dwarf_female",    # no dwarf portraits exist in period art
    "rogue_goblin_ambiguous",  # fantasy creature
    "mage_construct",          # mechanical being
    "ranger_elf_male",         # elvish fantasy figure
    "monk_human_ambiguous",    # generate monk pose
    "warlock_faetouched_female", # supernatural female
    "warlock_trollblooded_male", # monstrous humanoid
    "blacksmith",              # generate broad figure at forge
    "town_guard",              # generate armored guard
    # Enemies — all generate from scratch (fantasy creatures)
    "goblin_scout",
    "orc_warrior",
    "skeleton",
    "zombie",
    "gnoll",
    "redcap",
    "hollow_man",
    "wraith_knight",
    "vampire_lord",
    "mind_flayer",
    "medusa",
    "dire_wolf",
    "moon_beast",
]

SOURCE_BY_ARCHETYPE = {s["archetype_id"]: s for s in CHARACTER_SOURCES}


def register_character_sources(catalog, download_dir: Path) -> Dict[str, int]:
    """
    Download all source portraits and register them as character base images.
    Returns {"registered": n, "failed": n, "skipped_generate": n}.
    """
    import urllib.request
    import time

    download_dir.mkdir(parents=True, exist_ok=True)
    registered = 0
    failed = 0

    def _fetch(url, dest, max_retries=4):
        import urllib.request, urllib.error
        headers = {"User-Agent": "Mozilla/5.0 dj2-asset-curator/1.0 (bartleeanderson@gmail.com)"}
        wait = 15
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    dest.write_bytes(resp.read())
                return True
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    print(f"    rate-limited, waiting {wait}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(wait)
                    wait *= 2
                else:
                    print(f"    HTTP {e.code}")
                    return False
            except Exception as e:
                print(f"    error: {e}")
                return False
        return False

    for i, src in enumerate(CHARACTER_SOURCES):
        ext = Path(src["url"]).suffix.lower() or ".jpg"
        dest = download_dir / f"{src['id']}{ext}"

        if not dest.exists():
            print(f"Downloading {src['id']} ...")
            if _fetch(src["url"], dest):
                print(f"  -> {dest.name} ({dest.stat().st_size // 1024}KB)")
                if i < len(CHARACTER_SOURCES) - 1:
                    time.sleep(8)
            else:
                print(f"  FAILED: {src['id']}")
                failed += 1
                continue
        else:
            print(f"  Already have {src['id']}, skipping download.")

        # Register as character base in catalog
        from world.visuals.archetypes import get_archetype
        arch = get_archetype(src["archetype_id"])
        tags = arch.tags if arch else []

        catalog.register_character(
            id=f"base_{src['id']}",
            path=dest,
            char_type="base_portrait",
            tags=tags + ["portrait_base", src["artist"].replace(" ", "_").lower()],
            anchor={},
        )
        registered += 1

    print(f"\nPortraits: {registered} registered, {failed} failed.")
    print(f"Generate-from-scratch archetypes: {len(GENERATE_FROM_SCRATCH)}")
    print("  Run character_generator.py for those.")

    return {"registered": registered, "failed": failed,
            "skipped_generate": len(GENERATE_FROM_SCRATCH)}


if __name__ == "__main__":
    from pathlib import Path
    from world.visuals.catalog import AssetCatalog

    assets_dir = Path("assets/visuals")
    db_path = assets_dir / "visual_assets.db"
    portraits_dir = assets_dir / "characters" / "portraits"

    catalog = AssetCatalog(db_path)
    register_character_sources(catalog, portraits_dir)
    catalog.close()

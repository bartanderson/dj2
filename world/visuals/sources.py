"""
Curated public-domain source images for the D&D visual library.

All entries are public domain (Gustave Dore 1832-1883, Howard Pyle 1853-1911).
URLs are confirmed Wikimedia Commons direct links using verified hash paths.

Run register_sources(catalog, download_dir) to fetch and catalog.
"""

from pathlib import Path
from typing import List, Dict
import time

SOURCES: List[Dict] = [

    # --- FOREST / DARK WOOD ---
    {
        "id": "dore_dark_wood",
        "url": "https://upload.wikimedia.org/wikipedia/commons/d/dd/Gustave_Dore_Inferno1.jpg",
        "terrain": "forest",
        "structure": "wilderness",
        "tags": ["dark forest", "lone figure", "gothic", "dense trees"],
        "prompt_hint": "dark fantasy forest, lone figure lost among towering trees, dramatic light",
        "credit": "Gustave Doré, Inferno Canto I (Dante lost in the wood), 1861. Public domain.",
    },

    # --- CAVERN / DUNGEON (figures in ice/stone) ---
    {
        "id": "dore_cavern_figures",
        "url": "https://upload.wikimedia.org/wikipedia/commons/1/1f/Gustave_Dore_Inferno32.jpg",
        "terrain": "underground",
        "structure": "dungeon",
        "tags": ["cavern", "dark", "dramatic", "figures", "stone"],
        "prompt_hint": "stone dungeon cavern, dramatic figures, dark fantasy underground",
        "credit": "Gustave Doré, Inferno Canto XXXII, 1861. Public domain.",
    },

    # --- INFERNO CAVERN (Lucifer, deep dungeon) ---
    {
        "id": "dore_deep_dungeon",
        "url": "https://upload.wikimedia.org/wikipedia/commons/4/44/Gustave_Dore_Inferno34.jpg",
        "terrain": "underground",
        "structure": "dungeon",
        "tags": ["deep cavern", "dark", "infernal", "epic scale"],
        "prompt_hint": "vast underground cavern, titanic scale, dark fantasy dungeon, dramatic",
        "credit": "Gustave Doré, Inferno Canto XXXIV (Lucifer), 1861. Public domain.",
    },

    # --- OPEN LANDSCAPE / HILLS (Sermon on the Mount — crowd on hillside) ---
    {
        "id": "dore_open_hillside",
        "url": "https://upload.wikimedia.org/wikipedia/commons/b/b5/Dore_Bible_Sermon_on_the_Mount.jpg",
        "terrain": "hills",
        "structure": "wilderness",
        "tags": ["hillside", "open", "crowd", "dramatic sky", "figures"],
        "prompt_hint": "rolling hillside, gathered figures, open sky, fantasy landscape",
        "credit": "Gustave Doré, Sermon on the Mount (Bible illustrations), c.1866. Public domain.",
    },

    # --- MOUNTAIN ASCENT (Purgatorio rocky cliffs) ---
    {
        "id": "dore_mountain_cliff",
        "url": "https://upload.wikimedia.org/wikipedia/commons/0/07/Pur_03.jpg",
        "terrain": "mountains",
        "structure": "wilderness",
        "tags": ["cliff", "rocky", "figures ascending", "dramatic", "mountain"],
        "prompt_hint": "rocky mountain cliff face, figures climbing, dramatic fantasy landscape",
        "credit": "Gustave Doré, Purgatorio Canto III, 1868. Public domain.",
    },

    # --- COASTAL / RIVER CROSSING ---
    {
        "id": "dore_river_crossing",
        "url": "https://upload.wikimedia.org/wikipedia/commons/6/68/Gustave_Dore_Inferno23.jpg",
        "terrain": "coastal",
        "structure": "wilderness",
        "tags": ["river", "dark", "figures", "atmospheric"],
        "prompt_hint": "dark river, atmospheric mist, fantasy figures crossing water",
        "credit": "Gustave Doré, Inferno Canto XXIII, 1861. Public domain.",
    },

    # --- VILLAGE / CROWD SCENE (Howard Pyle) ---
    {
        "id": "pyle_village_crowd",
        "url": "https://upload.wikimedia.org/wikipedia/commons/d/db/Pyle_pirate_handsome.jpg",
        "terrain": "plains",
        "structure": "village",
        "tags": ["period figure", "street", "medieval", "atmospheric"],
        "prompt_hint": "medieval village street, period figures, fantasy settlement",
        "credit": "Howard Pyle, The Buccaneer, 1905. Delaware Art Museum. Public domain.",
    },

    # --- TAVERN INTERIOR (Frans Hals tavern painting reuse as background) ---
    {
        "id": "hals_tavern_interior",
        "url": "https://upload.wikimedia.org/wikipedia/commons/d/d1/Hals%2C_Frans_-_Malle_Babbe.jpg",
        "terrain": "interior",
        "structure": "tavern_interior",
        "tags": ["interior", "warm", "period", "dark background"],
        "prompt_hint": "medieval tavern interior, stone and wood, firelight, fantasy inn",
        "credit": "Frans Hals, Malle Babbe, c.1633-35. Gemäldegalerie Berlin. Public domain.",
    },
]


def _download_with_retry(url: str, dest: Path, max_retries: int = 4) -> bool:
    """Download a file with exponential backoff on 429."""
    import urllib.request
    import urllib.error

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
                print(f"    HTTP {e.code}: {e.reason}")
                return False
        except Exception as e:
            print(f"    error: {e}")
            return False
    return False


def register_sources(catalog, download_dir: Path) -> Dict[str, int]:
    """Download and register background scene sources."""
    download_dir.mkdir(parents=True, exist_ok=True)
    registered = 0
    failed = 0

    for i, src in enumerate(SOURCES):
        ext = Path(src["url"].split("?")[0]).suffix.lower() or ".jpg"
        dest = download_dir / f"{src['id']}{ext}"

        if not dest.exists():
            print(f"Downloading {src['id']} ...")
            if _download_with_retry(src["url"], dest):
                print(f"  -> {dest.name} ({dest.stat().st_size // 1024}KB)")
                if i < len(SOURCES) - 1:
                    time.sleep(8)
            else:
                print(f"  FAILED: {src['id']}")
                failed += 1
                continue
        else:
            print(f"  Already have {src['id']}, skipping.")

        catalog.register_base(
            id=src["id"],
            path=dest,
            terrain=src["terrain"],
            structure=src["structure"],
            tags=src["tags"],
            prompt_hint=src["prompt_hint"],
            source=src["url"],
            license="public_domain",
        )
        registered += 1

    print(f"Scenes: {registered} registered, {failed} failed.")
    return {"registered": registered, "failed": failed}
